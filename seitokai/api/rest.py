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

__all__: list[str] = ["RestClient", "UuidIsh"]

import typing
import uuid

if typing.TYPE_CHECKING:
    from .. import forums
    from .. import messages
    from . import paginator


UuidIsh: typing.TypeAlias = str | uuid.UUID


@typing.runtime_checkable
class RestClient(typing.Protocol):
    __slots__ = ()

    @property
    def is_running(self) -> bool:
        """Whether the client is running."""
        raise NotImplementedError

    # Role membership

    async def post_member_role(self, user_id: str, role_id: int, /) -> None:
        raise NotImplementedError

    async def delete_member_role(self, user_id: str, role_id: int, /) -> None:
        raise NotImplementedError

    # Group membership

    async def put_group_member(self, group_id: str, user_id: str, /) -> None:
        raise NotImplementedError

    async def delete_group_member(self, group_id: str, user_id: str, /) -> None:
        raise NotImplementedError

    # Forums

    async def post_channel_forum(self, channel_id: UuidIsh, /, *, title: str, content: str) -> forums.ForumThread:
        raise NotImplementedError

    # Chat

    async def post_channel_message(self, channel_id: UuidIsh, /, content: str) -> messages.Message:
        raise NotImplementedError

    async def iter_channel_messages(self, channel_id: UuidIsh, /) -> paginator.Paginator[messages.Message]:
        raise NotImplementedError

    async def get_channel_message(self, channel_id: UuidIsh, message_id: UuidIsh, /) -> messages.Message:
        raise NotImplementedError

    async def put_channel_message(self, channel_id: UuidIsh, message_id: UuidIsh, /, content: str) -> messages.Message:
        raise NotImplementedError

    async def delete_channel_message(self, channel_id: UuidIsh, message_id: UuidIsh, /) -> None:
        raise NotImplementedError

    # Reactions

    async def put_content_reaction(self, channel_id: UuidIsh, content_id: UuidIsh, emote_id: int, /) -> None:
        raise NotImplementedError

    # List items

    async def post_channel_list(self, channel_id: UuidIsh, /, message: str, *, note: str = ...) -> ...:
        raise NotImplementedError

    # Team XP

    async def post_member_xp(self, user_id: UuidIsh, /, amount: int) -> int:
        raise NotImplementedError

    async def post_role_xp(self, role_id: UuidIsh, /, amount: int) -> None:
        raise NotImplementedError
