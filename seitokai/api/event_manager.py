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

__all__: list[str] = ["EventT", "CallbackSig", "EventCallbackSig", "EventCallbackSigT", "Stream"]

import typing
from collections import abc as collections

from ..events import base_events

if typing.TYPE_CHECKING:
    import types

_T = typing.TypeVar("_T")
T_co = typing.TypeVar("T_co", covariant=True)
RawEventT: typing.TypeAlias = collections.Mapping[str, typing.Any]
CallbackSig: typing.TypeAlias = collections.Callable[[_T], collections.Coroutine[typing.Any, typing.Any, None]]
EventCallbackSig = CallbackSig[base_events.BaseEvent]
EventCallbackSigT = typing.TypeVar("EventCallbackSigT", bound=EventCallbackSig)
EventT = typing.TypeVar("EventT", bound=base_events.BaseEvent)


@typing.runtime_checkable
class Stream(typing.Protocol[T_co]):
    __slots__ = ()

    def __aiter__(self: _T) -> _T:
        raise NotImplementedError

    async def __anext__(self) -> T_co:
        raise NotImplementedError

    def __enter__(self: _T) -> _T:
        raise NotImplementedError

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: types.TracebackType | None,
    ) -> None:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError

    async def receive(self) -> T_co:
        raise NotImplementedError


class EventManager(typing.Protocol):
    __slots__ = ()

    def dispatch(self, event: base_events.BaseEvent, /) -> None:
        raise NotImplementedError

    def stream(self, event_type: type[EventT], /, *, buffer_size: int = 100) -> Stream[EventT]:
        raise NotImplementedError

    def add_listener(self: _T, event_type: type[EventT], callback: CallbackSig[EventT], /) -> _T:
        raise NotImplementedError

    def with_listener(
        self, event_type: type[base_events.BaseEvent], /
    ) -> collections.Callable[[EventCallbackSigT], EventCallbackSigT]:
        raise NotImplementedError

    def remove_listener(self, event_type: type[EventT], callback: CallbackSig[EventT], /) -> None:
        raise NotImplementedError
