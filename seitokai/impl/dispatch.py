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
import typing

import anyio

if typing.TYPE_CHECKING:
    import anyio.abc as anyio_abc
    from anyio.streams import memory as memory_streams

    from ..api import dispatch as dispatch_api

_T = typing.TypeVar("_T")


@dataclasses.dataclass(slots=True)
class Dispatchable(typing.Generic[_T]):
    callbacks: list[dispatch_api.CallbackSig[_T]] = dataclasses.field(default_factory=list, init=False)
    streams: list[memory_streams.MemoryObjectSendStream[_T]] = dataclasses.field(default_factory=list, init=False)

    @property
    def is_empty(self) -> bool:
        return not self.callbacks and not self.streams

    def add_callback(self, callback: dispatch_api.CallbackSig[_T], /) -> None:
        self.callbacks.append(callback)

    def remove_callback(self, callback: dispatch_api.CallbackSig[_T], /) -> None:
        self.callbacks.remove(callback)

    def stream(self, *, buffer_size: int = 100) -> memory_streams.MemoryObjectReceiveStream[_T]:
        send, recv = anyio.create_memory_object_stream(buffer_size)
        self.streams.append(send)
        return recv

    def dispatch(self, task_group: anyio_abc.TaskGroup, value: _T) -> None:
        for stream in self.streams.copy():
            try:
                stream.send_nowait(value)

            except (anyio.BrokenResourceError, anyio.ClosedResourceError):
                self.streams.remove(stream)

            except anyio.WouldBlock:
                pass

        for callback in self.callbacks:
            task_group.start_soon(callback, value)
