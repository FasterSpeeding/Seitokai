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
"""Interface of a WebSocket based Guilded bot."""
from __future__ import annotations

__all__: list[str] = ["WebSocketBot"]

import typing

if typing.TYPE_CHECKING:
    from . import event_manager as event_manager_api
    from . import marshaller as marshaller_api
    from . import rest as rest_api
    from . import websocket as websocket_api


@typing.runtime_checkable
class WebSocketBot(typing.Protocol):
    """Interface of a WebSocket based Guilded bot."""

    __slots__ = ()

    @property
    def event_manager(self) -> event_manager_api.EventManager:
        """The event manager instance used by this bot.

        Returns
        -------
        seitokai.api.event_manager.EventManager
            The event manager used by this bot.
        """
        raise NotImplementedError

    @property
    def is_running(self) -> bool:
        """Whether the bot is running.

        Returns
        -------
        bool
            Whether the bot is running.
        """
        raise NotImplementedError

    @property
    def websocket(self) -> websocket_api.WebSocketClient:
        """The websocket client instance used by this bot.

        Returns
        -------
        seitokai.api.websocket.WebSocketClient
            The websocket client used by this bot.
        """
        raise NotImplementedError

    @property
    def marshaller(self) -> marshaller_api.Marshaller:
        """The marshaller instance used by this bot.

        Returns
        -------
        seitokai.api.marshaller.Marshaller
            The marshaller used by this bot.
        """
        raise NotImplementedError

    @property
    def rest(self) -> rest_api.RestClient:
        """The REST client instance used by this bot.

        Returns
        -------
        seitokai.api.rest.RestClient
            The REST client used by this bot.
        """
        raise NotImplementedError
