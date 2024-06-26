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

__all__: list[str] = ["WebSocketBot"]

import typing

import anyio
import httpx

from ..api import bot as bot_api
from ..api import event_manager as event_manager_api
from ..impl import event_manager as event_manager_impl
from ..impl import marshaller as marshaler_impl
from ..impl import rest as rest_impl
from ..impl import websocket as websocket_impl

if typing.TYPE_CHECKING:
    import ssl
    from collections import abc as collections

    from anyio import abc as anyio_abc

    from .. import events
    from ..api import marshaller as marshaller_api
    from ..api import rest as rest_api
    from ..api import websocket as websocket_api

    _WebSocketBotT = typing.TypeVar("_WebSocketBotT", bound="WebSocketBot")


class WebSocketBot(bot_api.WebSocketBot, event_manager_api.EventManager):
    """Standard implementation of `seitokai.api.bot.WebSocketBot`.

    Parameters
    ----------
    token: str
        The bot's token.

    Other Parameters
    ----------------
    rest_url: str | None
        The base URL to use in the REST client.
    websocket_url: str | None
        The base URL to use in the websocket client.
    """

    __slots__ = (
        "_close_scope",
        "_event_manager",
        "_is_closing",
        "_join_event",
        "_marshaller",
        "_rest",
        "_websocket",
    )

    def __init__(self, token: str, /, *, rest_url: str | None = None, websocket_url: str | None = None) -> None:
        self._close_scope: anyio_abc.CancelScope | None = None
        self._is_closing = False
        self._join_event: anyio.Event | None = None
        self._marshaller = marshaler_impl.Marshaller()
        self._event_manager = event_manager_impl.EventManager(self._marshaller)
        self._rest = rest_impl.RestClient(token, marshaller=self._marshaller, base_url=rest_url)
        self._websocket = websocket_impl.WebSocketClient(token, event_manager=self._event_manager, url=websocket_url)

    @property
    def event_manager(self) -> event_manager_api.EventManager:
        return self._event_manager

    @property
    def is_running(self) -> bool:
        return self._close_scope is not None

    @property
    def marshaller(self) -> marshaller_api.Marshaller:
        return self._marshaller

    @property
    def rest(self) -> rest_api.RestClient:
        return self._rest

    @property
    def websocket(self) -> websocket_api.WebSocketClient:
        return self._websocket

    async def join(self) -> None:
        """Wait until the bot's closed."""
        if self._join_event:
            await self._join_event.wait()

        raise RuntimeError("Bot is not running")

    async def close(self) -> None:
        """Instruct the bot to close and wait until it's finished closing."""
        if self._is_closing:
            return await self.join()

        join_event = self._join_event
        if self._close_scope and join_event:
            self._is_closing = True
            await self._websocket.close()
            self._event_manager.close()
            await self._rest.close()
            await join_event.wait()  # TODO: after a timeout we should just cancel the scope

        raise RuntimeError("Bot is not running")

    async def run(
        self,
        *,
        verify: str | bool | ssl.SSLContext = True,
        http1: bool = True,
        http2: bool = True,
        timeout: float | httpx.Timeout = httpx.Timeout(timeout=0.5),
        limits: httpx.Limits = httpx.Limits(max_connections=100, max_keepalive_connections=20),
        max_redirects: int = 20,
        trust_env: bool = True,
    ) -> None:
        """Run the bot and its components asynhcronously.

        !!! note
            This won't return until the bot has closed.

        Arguments
        ---------
        verify: str | bool
            Whether to verify the SSL certificate in the REST client.

            If a string is passed, it will be used as a path to a CA bundle to use.
            If a bool is passed, the underlying library will attempt to use the system
            CA bundle or, if that fails, the bundled one.
        http1: bool
            Whether to use HTTP/1.0 or HTTP/1.1 in the REST client.
        http2: bool
            Whether to use HTTP/2 in the REST client.
        timeout: float | httpx.Timeout
            The request timeout to use within the REST client.
        limits: httpx.Limits
            The request limits to use within the REST client.
        max_redirects: int
            The maximum number of redirects to follow within the REST client.
        trust_env: bool
            Whether to trust the environment variables for configuring the REST client.

        See Also
        --------
        WebSocketBot.run_blocking :
            For how to run the bot as the entry point for the async
            loop while blocking the current thread.
        """
        if self._close_scope:
            raise RuntimeError("Bot is already running")

        self._join_event = anyio.Event()

        try:
            self._rest.start(
                verify=verify,
                http1=http1,
                http2=http2,
                timeout=timeout,
                limits=limits,
                max_redirects=max_redirects,
                trust_env=trust_env,
            )

            async with anyio.create_task_group() as task_group:
                self._close_scope = task_group.cancel_scope
                task_group.start_soon(self._event_manager.run)
                task_group.start_soon(self._websocket.run)

        finally:
            self._join_event.set()
            self._close_scope = None
            self._join_event = None
            self._is_closing = False

    def run_blocking(
        self,
        *,
        backend: str = "asyncio",
        verify: str | bool | ssl.SSLContext = True,
        http1: bool = True,
        http2: bool = True,
        timeout: float | httpx.Timeout = httpx.Timeout(timeout=0.5),
        limits: httpx.Limits = httpx.Limits(max_connections=100, max_keepalive_connections=20),
        max_redirects: int = 20,
        trust_env: bool = True,
    ) -> None:
        """Run the bot and its components and block the current thread until it's closed.

        !!! warning
            The current thread must not be already running an event loop.

        Arguments
        ---------
        backend: str
            Name of the asynchronous event loop implementation to use.

            For more information about this see Anyio's documentation.

            Defaults to asyncio.
        verify: str | bool
            Whether to verify the SSL certificate in the REST client.

            If a string is passed, it will be used as a path to a CA bundle to use.
            If a bool is passed, the underlying library will attempt to use the system
            CA bundle or, if that fails, the bundled one.
        http1: bool
            Whether to use HTTP/1.0 or HTTP/1.1 in the REST client.
        http2: bool
            Whether to use HTTP/2 in the REST client.
        timeout: float | httpx.Timeout
            The request timeout to use within the REST client.
        limits: httpx.Limits
            The request limits to use within the REST client.
        max_redirects: int
            The maximum number of redirects to follow within the REST client.
        trust_env: bool
            Whether to trust the environment variables for configuring the REST client.

        See Also
        --------
        WebSocketBot.run :
            For how to run the bot asynchronously.
        """
        if self._close_scope:
            raise RuntimeError("Bot is already running")

        async def run() -> None:
            await self.run(
                verify=verify,
                http1=http1,
                http2=http2,
                timeout=timeout,
                limits=limits,
                max_redirects=max_redirects,
                trust_env=trust_env,
            )

        anyio.run(run, backend=backend)

    def dispatch(self, event: events.BaseEvent, /) -> None:
        return self._event_manager.dispatch(event)

    def dispatch_raw(self, event_name: str, payload: event_manager_api.RawEventT, /) -> None:
        return self._event_manager.dispatch_raw(event_name, payload)

    def stream(
        self, event_type: type[event_manager_api.EventT], /, *, buffer_size: int = 100
    ) -> event_manager_api.Stream[event_manager_api.EventT]:
        return self._event_manager.stream(event_type, buffer_size=buffer_size)

    def add_listener(
        self: _WebSocketBotT,
        event_type: type[event_manager_api.EventT],
        callback: event_manager_api.CallbackSig[event_manager_api.EventT],
        /,
    ) -> _WebSocketBotT:
        self._event_manager.add_listener(event_type, callback)
        return self

    def with_listener(
        self, event_type: type[events.BaseEvent], /
    ) -> collections.Callable[
        [event_manager_api.CallbackSig[event_manager_api.EventT]],
        event_manager_api.CallbackSig[event_manager_api.EventT],
    ]:
        return self._event_manager.with_listener(event_type)

    def remove_listener(
        self,
        event_type: type[event_manager_api.EventT],
        callback: event_manager_api.CallbackSig[event_manager_api.EventT],
        /,
    ) -> None:
        self._event_manager.remove_listener(event_type, callback)
