# -*- coding: utf-8 -*-
# cython: language_level=3
# BSD 3-Clause License
#
# Copyright (c) 2021, Faster Speeding
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of the copyright holder nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
from __future__ import annotations

__all__: list[str] = ["WebsocketClient", "DEFAULT_URL"]

import json
import logging
import types
import typing

import anyio
import asyncwebsockets  # type: ignore
import wsproto

from ..api import event_manager as event_manager_api
from . import event_manager as event_manager_impl

if typing.TYPE_CHECKING:
    import ssl
    from collections import abc as collections

    from anyio import abc as anyio_abc

    from ..api import gateway as gateway_api

    _WebsocketClientT = typing.TypeVar("_WebsocketClientT", bound="WebsocketClient")


_AUTHORIZATION_HEADER_KEY: typing.Final[str] = "Authorization"
DEFAULT_URL: typing.Final[str] = "wss://api.guilded.gg/v1/websocket"
_LOGGER: typing.Final[logging.Logger] = logging.getLogger("seitokai.gateway")
_PING: typing.Final[wsproto.events.Ping] = wsproto.events.Ping()
_PONG: typing.Final[wsproto.events.Pong] = wsproto.events.Pong()


class _Disconnect(Exception):
    __slots__: tuple[str, ...] = ()


class WebsocketClient:
    __slots__: tuple[str, ...] = (
        "_client",
        "_join_event",
        "_last_message_id",
        "_raw_dispatchers",
        "_task_group",
        "_token",
        "_url",
    )

    def __init__(self, token: str, /, *, url: str = DEFAULT_URL) -> None:
        self._client: asyncwebsockets.Websocket | None = None
        self._join_event: anyio.Event | None = None
        self._last_message_id: str | None = None
        self._raw_dispatchers: dict[str, event_manager_impl.Dispatchable[event_manager_api.RawEventT]] = {}
        self._task_group: anyio_abc.TaskGroup | None = None
        self._token = f"Bearer {token}"
        self._url = url

    def _get_task_group(self) -> anyio_abc.TaskGroup:
        if self._task_group:
            return self._task_group

        raise RuntimeError("Websocket client is inactive")

    def _get_ws(self) -> asyncwebsockets.Websocket:
        if self._client:
            return self._client

        raise RuntimeError("Websocket client is inactive")

    async def send_json(self, data: dict[str, typing.Any], /) -> None:
        await self._get_ws().send(json.dumps(data))

    @staticmethod
    async def _send_raw_event(ws: asyncwebsockets.Websocket, event: wsproto.events.Event) -> None:
        # https://github.com/Fuyukai/asyncwebsockets/issues/18
        async with ws._send_lock:
            data = ws._connection.send(_PING)
            await ws._sock.send(data)

    async def _heartbeat(self, ws: asyncwebsockets.Websocket, delay: float, cancel: anyio.CancelScope) -> None:
        with cancel:
            _LOGGER.debug("Sending heartbeat ping")
            await self._send_raw_event(ws, _PING)
            await anyio.sleep(delay)

    async def _keep_alive(self, ws: asyncwebsockets.Websocket, task_group: anyio_abc.TaskGroup) -> None:
        cancel_heartbeat = anyio.CancelScope()
        await self._wait_for_hello(ws, task_group, cancel_heartbeat)

        # while True:  # TODO: reconnect logic
        try:
            await self._receive_events(ws, task_group)

        except _Disconnect:
            cancel_heartbeat.cancel()
            return

    async def _receive_events(self, ws: asyncwebsockets.Websocket, task_group: anyio_abc.TaskGroup) -> None:
        stream = aiter(ws)
        while True:
            try:
                event = await anext(stream)

            except anyio.EndOfStream:
                print("end of stream")
                return  # Connection was closed unexpected, we should reconnect

            except StopAsyncIteration:
                print("was closed")
                return  # Client.close was called, we should shutdown

            match event:  # CloseConnection is translated to StopAsyncIteration
                case wsproto.events.TextMessage(data):
                    await self._handle_message(ws, task_group, data)
                case wsproto.events.BytesMessage():
                    _LOGGER.info(
                        "Skipping bytes event as byte messages aren't implemeneted"
                    )
                case wsproto.events.Ping():
                    _LOGGER.debug("Received ping and sending pong response")
                    await self._send_raw_event(ws, _PONG)
                case wsproto.events.Pong():
                    _LOGGER.debug("Received pong")  # TODO: reconnect logic
                case _:
                    _LOGGER.warning("Unexpected event type", event)

    async def _wait_for_hello(
        self, ws: asyncwebsockets.Websocket, task_group: anyio_abc.TaskGroup, cancel_heartbeat: anyio.CancelScope
    ) -> None:
        event = await anext(aiter(ws), None)

        if not event:
            raise RuntimeError("Failed to connect")

        # this doesn't have an opcode(?)
        data: dict[str, typing.Any] = json.loads(event.data)["d"]
        self._last_message_id = data["lastMessageId"]
        heartbeat_interval: int = data["heartbeatIntervalMs"]
        task_group.start_soon(self._heartbeat, ws, heartbeat_interval / 1000, cancel_heartbeat)

    async def _handle_message(
        self, ws: asyncwebsockets.Websocket, task_group: anyio_abc.TaskGroup, message: str, /
    ) -> None:
        try:
            payload = json.loads(message)

        except (json.JSONDecodeError, ValueError) as exc:
            _LOGGER.error(
                "Ignoring event which couldn't be parsed as JSON with the following payload:\n %r",
                message,
                exc_info=exc,
            )
            return

        if last_message_id := payload.get("s"):
            self._last_message_id = last_message_id

        opcode = payload.get("op")

        if opcode == 0 and (dispatcher := self._raw_dispatchers.get(payload["t"])):
            dispatcher.dispatch(task_group, types.MappingProxyType(payload))

        else:
            _LOGGER.warning("Ignoring unexpected opcode %s for event payload %r", payload, message)

    async def close(self) -> None:
        client = self._get_ws()
        self._client = None
        await client.close()

    async def run(self, *, ssl_context: bool | ssl.SSLContext = True) -> None:
        if self._client:
            raise RuntimeError("Websocket client already running")

        self._client = client = await asyncwebsockets.create_websocket(
            self._url, ssl=ssl_context, headers=[(_AUTHORIZATION_HEADER_KEY, self._token)]
        )
        self._task_group = task_group = anyio.create_task_group()
        async with task_group:
            await self._keep_alive(client, task_group)

            if self._join_event:
                self._join_event.set()

            task_group.cancel_scope.cancel()
            self._task_group = None

    async def join(self) -> None:
        if not self._client:
            raise RuntimeError("Websocket client isn't running")

        if not self._join_event:
            self._join_event = anyio.Event()

        await self._join_event.wait()

    def _get_or_create_dispatchable(
        self, event_name: str
    ) -> event_manager_impl.Dispatchable[event_manager_api.RawEventT]:
        try:
            return self._raw_dispatchers[event_name]

        except KeyError:
            dispatcher = self._raw_dispatchers[event_name] = event_manager_impl.Dispatchable()
            return dispatcher

    def stream(
        self, event_name: str, /, *, buffer_size: int = 100
    ) -> event_manager_api.Stream[event_manager_api.RawEventT]:
        return self._get_or_create_dispatchable(event_name).stream_abstract(buffer_size=buffer_size)

    def add_raw_listener(
        self: _WebsocketClientT, event_name: str, callback: gateway_api.CallbackSig, /
    ) -> _WebsocketClientT:
        self._get_or_create_dispatchable(event_name).add_callback(callback)
        return self

    def with_raw_listener(
        self, event_name: str, /
    ) -> collections.Callable[[gateway_api.CallbackSigT], gateway_api.CallbackSigT]:
        def decorator(callback: gateway_api.CallbackSigT, /) -> gateway_api.CallbackSigT:
            self.add_raw_listener(event_name, callback)
            return callback

        return decorator

    def remove_raw_listener(self, event_name: str, callback: gateway_api.CallbackSig, /) -> None:
        dispatcher = self._raw_dispatchers[event_name]
        dispatcher.remove_callback(callback)
        if dispatcher.is_empty:
            del self._raw_dispatchers[event_name]
