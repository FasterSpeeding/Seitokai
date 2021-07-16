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

__all__: list[str] = ["Listener"]

import dataclasses
import typing

import anyio
import anyio.abc as anyio_abc

if typing.TYPE_CHECKING:
    from collections import abc as collections

    from ..api import dispatch


_T = typing.TypeVar("_T")
_IdentifierT = typing.TypeVar("_IdentifierT")


@dataclasses.dataclass(eq=True, slots=True, unsafe_hash=True)
class Listener(typing.Generic[_IdentifierT, _T]):
    identifier: _IdentifierT = dataclasses.field(compare=False, hash=False)
    callback: collections.Callable[[_T], collections.Coroutine[typing.Any, typing.Any, None]] = dataclasses.field(
        compare=True, hash=True
    )
    _task_group: anyio_abc.TaskGroup | None = dataclasses.field(compare=False, default=None, hash=False, init=False)

    async def _stream(self, stream: dispatch.Stream[_T], task_group: anyio_abc.TaskGroup) -> None:
        with stream:
            async for event in stream:
                task_group.start_soon(self.callback, event)

    async def activate(self, stream: dispatch.Stream[_T]) -> None:
        self._task_group = anyio.create_task_group()
        await self._task_group.__aenter__()
        self._task_group.start_soon(self._stream, stream, self._task_group)

    async def deactivate(self):
        if not self._task_group:
            raise RuntimeError("Listener isn't active")

        self._task_group.cancel_scope.cancel()
        task_group = self._task_group
        self._task_group = None
        await task_group.__aexit__(None, None, None)
