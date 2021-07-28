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

__all__: list[str] = ["MessageEvent", "MessageCreatedEvent", "MessageUpdatedEvent", "MessageDeletedEvent"]

import abc
import dataclasses
import typing

from . import BaseEvent

if typing.TYPE_CHECKING:
    import datetime
    import uuid

    from .. import messages


class MessageEvent(BaseEvent, abc.ABC):
    __slots__ = ()

    @property
    @abc.abstractmethod
    def channel_id(self) -> uuid.UUID:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def message_id(self) -> uuid.UUID:
        raise NotImplementedError


@dataclasses.dataclass(eq=True, init=True, unsafe_hash=True)
class MessageCreatedEvent(MessageEvent):
    message: messages.Message = dataclasses.field(compare=True, hash=True)

    @property
    def channel_id(self) -> uuid.UUID:
        return self.message.channel_id

    @property
    def message_id(self) -> uuid.UUID:
        return self.message.id


@dataclasses.dataclass(eq=True, init=True, unsafe_hash=True)
class MessageUpdatedEvent(MessageEvent):
    message: messages.Message = dataclasses.field(compare=True, hash=True)

    @property
    def channel_id(self) -> uuid.UUID:
        return self.message.channel_id

    @property
    def message_id(self) -> uuid.UUID:
        return self.message.id


@dataclasses.dataclass(eq=True, init=True, unsafe_hash=True)
class MessageDeletedEvent(MessageEvent):
    _message_id: uuid.UUID = dataclasses.field(compare=True, hash=True)
    _channel_id: uuid.UUID = dataclasses.field(compare=False, hash=False)
    deleted_at: datetime.datetime = dataclasses.field(compare=False, hash=False)

    @property
    def channel_id(self) -> uuid.UUID:
        return self._channel_id

    @property
    def message_id(self) -> uuid.UUID:
        return self._message_id
