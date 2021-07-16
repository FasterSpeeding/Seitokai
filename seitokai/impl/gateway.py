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

import itertools
import json
import logging
import types
import typing

import anyio
import asyncwebsockets  # type: ignore
import wsproto
from anyio import abc as anyio_abc
from anyio.streams import memory as memory_streams

from ..api import dispatch as dispatch_api
from . import dispatch

if typing.TYPE_CHECKING:
    import ssl
    from collections import abc as collections

    from ..api import gateway as gateway_api

    WebsocketClientT = typing.TypeVar("WebsocketClientT", bound="WebsocketClient")


_AUTHORIZATION_HEADER_KEY: typing.Final[str] = "Authorization"
DEFAULT_URL: typing.Final[str] = "wss://api.guilded.gg/v1/websocket"
_LOGGER: typing.Final[logging.Logger] = logging.getLogger("seitokai.gateway")
_PING: typing.Final[wsproto.events.Ping] = wsproto.events.Ping()
_PONG: typing.Final[wsproto.events.Pong] = wsproto.events.Pong()


# class _Disconnect(Exception):
#     __slots__: tuple[str, ...] = ()


# class _Reconnect(Exception):
#     __slots__: tuple[str, ...] = ()


class WebsocketClient:
    __slots__: tuple[str, ...] = (
        "_client",
        "_close_event",
        "_last_message_id",
        "_listeners",
        "_streams",
        "_stream_buffer_size",
        "_task_group",
        "_token",
        "_url",
    )

    def __init__(self, token: str, /, *, url: str = DEFAULT_URL, stream_buffer_size: int = 1000) -> None:
        self._client: asyncwebsockets.Websocket | None = None
        self._close_event: anyio.Event | None = None
        self._last_message_id: None | str = None
        self._listeners: dict[str, dict[gateway_api.CallbackSig, dispatch.Listener[str, gateway_api.RawEventT]]] = {}
        self._streams: dict[
            str,
            typing.List[memory_streams.MemoryObjectSendStream[gateway_api.RawEventT]],
        ] = {}
        self._stream_buffer_size = stream_buffer_size
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

    async def _heartbeat(self, delay: float, cancel: anyio.CancelScope) -> None:
        client = self._get_ws()
        with cancel:
            _LOGGER.debug("Sending heartbeat ping")
            await self._send_raw_event(client, _PING)
            await anyio.sleep(delay)

    async def _keep_alive(self) -> None:
        ws = self._get_ws()
        task_group = self._get_task_group()
        cancel_heartbeat = anyio.CancelScope()
        async with task_group:
            await self._wait_for_hello(ws, task_group, cancel_heartbeat)
            await self._receive_events(ws)
            cancel_heartbeat.cancel()

    async def _receive_events(self, ws: asyncwebsockets.Websocket) -> None:
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
                    await self._handle_message(ws, data)
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
        ws = self._get_ws()
        event = await anext(aiter(ws), None)

        if not event:
            raise RuntimeError("Failed to connect")

        # this doesn't have an opcode(?)
        data: dict[str, typing.Any] = json.loads(event.data)["d"]
        self._last_message_id = data["lastMessageId"]
        heartbeat_interval: int = data["heartbeatIntervalMs"]
        task_group.start_soon(self._heartbeat, heartbeat_interval / 1000, cancel_heartbeat)

    def _dispatch(self, event_name: str, payload: gateway_api.RawEventT) -> None:
        payload_proxy = types.MappingProxyType(payload)
        if streams := self._streams.get(event_name):
            for stream in streams.copy():
                try:
                    stream.send_nowait(payload_proxy)

                except (anyio.BrokenResourceError, anyio.ClosedResourceError):
                    streams.remove(stream)

                except anyio.WouldBlock:
                    pass

    async def _handle_message(self, ws: asyncwebsockets.Websocket, message: str, /) -> None:
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

        if opcode == 0:
            event_name: str = payload["t"]
            self._dispatch(event_name, payload)

        else:
            _LOGGER.warning("Ignoring unexpected opcode %s for event payload %r", payload, message)

    async def close(self) -> None:
        client = self._get_ws()
        task_group = self._get_task_group()
        self._client = None
        self._task_group = None
        await client.close()

        for listener in itertools.chain.from_iterable(map(lambda m: m.values(), self._listeners.values())):
            listener.deactivate()

        task_group.cancel_scope.cancel()

    async def start(self, *, ssl_context: bool | ssl.SSLContext = True) -> None:
        if self._client:
            raise RuntimeError("Websocket client already running")

        self._client = await asyncwebsockets.create_websocket(
            self._url, ssl=ssl_context, headers=[(_AUTHORIZATION_HEADER_KEY, self._token)]
        )
        self._task_group = anyio.create_task_group()
        for listener in itertools.chain.from_iterable(map(lambda m: m.values(), self._listeners.values())):
            listener.activate(self.stream(listener.identifier), self._task_group)

        await self._keep_alive()

    def stream(self, name: str, /) -> dispatch_api.Stream[gateway_api.RawEventT]:
        send, recv = anyio.create_memory_object_stream(self._stream_buffer_size)

        try:
            self._streams[name].append(send)

        except KeyError:
            self._streams[name] = [send]

        assert isinstance(recv, dispatch_api.Stream)
        return recv

    def add_raw_listener(self: WebsocketClientT, name: str, callback: gateway_api.CallbackSig, /) -> WebsocketClientT:
        listener = dispatch.Listener(name, callback)
        try:
            if callback in self._listeners[name]:
                return self

            self._listeners[name][callback] = listener

        except KeyError:
            self._listeners[name] = {callback: listener}

        if self._task_group:
            listener.activate(self.stream(name), self._task_group)

        return self

    def with_raw_listener(
        self, name: str, /
    ) -> collections.Callable[[gateway_api.CallbackSigT], gateway_api.CallbackSigT]:
        def decorator(callback: gateway_api.CallbackSigT, /) -> gateway_api.CallbackSigT:
            self.add_raw_listener(name, callback)
            return callback

        return decorator

    def remove_raw_listener(self, name: str, callback: gateway_api.CallbackSig, /) -> None:
        listener = self._listeners[name].pop(callback)
        if self._task_group:
            listener.deactivate()