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

__all__: list[str] = ["CallbackSig", "CallbackSigT", "WebSocketClient"]

import abc
import typing
from collections import abc as collections

from . import event_manager

_T = typing.TypeVar("_T")
CallbackSig: typing.TypeAlias = event_manager.CallbackSig[event_manager.RawEventT]
CallbackSigT = typing.TypeVar("CallbackSigT", bound=CallbackSig)


class WebSocketClient(abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    def stream(self, name: str, /) -> event_manager.Stream[event_manager.RawEventT]:
        raise NotImplementedError

    @abc.abstractmethod
    def add_raw_listener(self: _T, event_name: str, callback: CallbackSig, /) -> _T:
        raise NotImplementedError

    @abc.abstractmethod
    def with_raw_listener(self, name: str, /) -> collections.Callable[[CallbackSigT], CallbackSigT]:
        raise NotImplementedError

    @abc.abstractmethod
    def remove_raw_listener(self, event_name: str, callback: CallbackSig, /) -> None:
        raise NotImplementedError
