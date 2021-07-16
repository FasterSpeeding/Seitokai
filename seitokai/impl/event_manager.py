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

__all__: list[str] = ["Dispatchable"]

import dataclasses
import inspect
import typing

import anyio

if typing.TYPE_CHECKING:
    from collections import abc as collections

    import anyio.abc as anyio_abc
    from anyio.streams import memory as memory_streams

    from ..api import event_manager as event_manager_api
    from ..api import marshaller as marshaler_api
    from ..events import base_events

    _EventManagerT = typing.TypeVar("_EventManagerT", bound="EventManager")

_T = typing.TypeVar("_T")


@dataclasses.dataclass(slots=True)
class Dispatchable(typing.Generic[_T]):
    _callbacks: list[event_manager_api.CallbackSig[_T]] = dataclasses.field(default_factory=list, init=False)
    _streams: list[memory_streams.MemoryObjectSendStream[_T]] = dataclasses.field(default_factory=list, init=False)

    @property
    def is_empty(self) -> bool:
        return not self._callbacks and not self._streams

    def add_callback(self, callback: event_manager_api.CallbackSig[_T], /) -> None:
        self._callbacks.append(callback)

    def remove_callback(self, callback: event_manager_api.CallbackSig[_T], /) -> None:
        self._callbacks.remove(callback)

    def stream(self, *, buffer_size: int = 100) -> memory_streams.MemoryObjectReceiveStream[_T]:
        send, recv = anyio.create_memory_object_stream(buffer_size)
        self._streams.append(send)
        return recv

    def stream_abstract(self, *, buffer_size: int = 100) -> event_manager_api.Stream[_T]:
        stream = self.stream(buffer_size=buffer_size)
        assert isinstance(stream, event_manager_api.Stream)
        return stream

    def dispatch(self, task_group: anyio_abc.TaskGroup, value: _T) -> None:
        for stream in self._streams.copy():
            try:
                stream.send_nowait(value)

            except (anyio.BrokenResourceError, anyio.ClosedResourceError):
                self._streams.remove(stream)

            except anyio.WouldBlock:
                pass

        for callback in self._callbacks:
            task_group.start_soon(callback, value)


def as_listener(
    event_name: str, /
) -> collections.Callable[[event_manager_api.EventCallbackSigT], event_manager_api.EventCallbackSigT]:
    def decorator(callback: event_manager_api.EventCallbackSigT, /) -> event_manager_api.EventCallbackSigT:
        callback.__event_name__ = event_name  # type: ignore
        assert isinstance(callback, _ListenerProto), "Wrong attributes set for listener proto"
        return callback  # type: ignore

    return decorator


@typing.runtime_checkable
class _ListenerProto(typing.Protocol):
    __slots__ = ()

    def __call__(self) -> event_manager_api.EventCallbackSig:
        raise NotImplementedError

    @property
    def __event_name__(self) -> str:
        raise NotImplementedError


@dataclasses.dataclass(slots=True)
class EventManager:
    marshaller: marshaler_api.Marshaller
    _dispatchers: dict[type[base_events.BaseEvent], Dispatchable[typing.Any]] = dataclasses.field(
        default_factory=dict, init=False
    )
    _listeners: dict[str, _ListenerProto] = dataclasses.field(default_factory=dict, init=False)
    _task_group: anyio_abc.TaskGroup | None = dataclasses.field(default=None, init=False)

    def __attrs_post_init__(self) -> None:
        for _, member in inspect.getmembers(self):
            if isinstance(member, _ListenerProto):
                self._listeners[member.__event_name__] = member

    def _get_or_create_dispatchable(
        self, event_type: type[event_manager_api.EventT]
    ) -> Dispatchable[event_manager_api.EventT]:
        try:
            return self._dispatchers[event_type]

        except KeyError:
            dispatcher = self._dispatchers[event_type] = Dispatchable()
            return dispatcher

    def dispatch(self, event: base_events.BaseEvent, /) -> None:
        if not self._task_group:
            raise RuntimeError("Event manager isn't active")

        if dispatcher := self._dispatchers.get(type(event)):
            dispatcher.dispatch(self._task_group, event)

    def stream(
        self, event_type: type[event_manager_api.EventT], /, *, buffer_size: int = 100
    ) -> event_manager_api.Stream[event_manager_api.EventT]:
        return self._get_or_create_dispatchable(event_type).stream_abstract(buffer_size=buffer_size)

    def add_listener(
        self: _EventManagerT,
        event_type: type[event_manager_api.EventT],
        callback: event_manager_api.CallbackSig[event_manager_api.EventT],
        /,
    ) -> _EventManagerT:
        self._get_or_create_dispatchable(event_type).add_callback(callback)
        return self

    def with_listener(
        self, event_type: type[base_events.BaseEvent], /
    ) -> collections.Callable[[event_manager_api.EventCallbackSigT], event_manager_api.EventCallbackSigT]:
        def decorator(callback: event_manager_api.EventCallbackSigT, /) -> event_manager_api.EventCallbackSigT:
            self.add_listener(event_type, callback)
            return callback

        return decorator

    def remove_listener(
        self,
        event_type: type[event_manager_api.EventT],
        callback: event_manager_api.CallbackSig[event_manager_api.EventT],
        /,
    ) -> None:
        dispatcher = self._dispatchers[event_type]
        dispatcher.remove_callback(callback)
        if dispatcher.is_empty:
            del self._dispatchers[event_type]
