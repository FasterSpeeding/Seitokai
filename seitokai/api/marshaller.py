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

__all__: list[str] = ["JsonArrayT", "JsonObjectT", "JsonIsh", "Marshaller", "TopLevelJsonIsh"]

import abc
import typing

if typing.TYPE_CHECKING:
    from .. import forums
    from .. import lists
    from .. import messages
    from .. import reactions

JsonArrayT: typing.TypeAlias = list[typing.Any]
JsonObjectT: typing.TypeAlias = dict[str, typing.Any]
TopLevelJsonIsh: typing.TypeAlias = JsonArrayT | JsonObjectT
JsonIsh: typing.TypeAlias = str | int | float | bool | JsonArrayT | JsonObjectT


class Marshaller(abc.ABC):
    __slots__ = ()

    # fourms

    @abc.abstractmethod
    def unmarshall_fourm_thread(self, data: JsonObjectT, /) -> forums.ForumThread:
        raise NotImplementedError

    # lists

    @abc.abstractmethod
    def unmarshall_list_item(self, data: JsonObjectT, /) -> lists.ListItem:
        raise NotImplementedError

    # messages

    @abc.abstractmethod
    def unmarshall_message(self, data: JsonObjectT, /) -> messages.Message:
        raise NotImplementedError

    # reactions

    @abc.abstractmethod
    def unmarshall_content_reaction(self, data: JsonObjectT, /) -> reactions.ContentReaction:
        raise NotImplementedError
