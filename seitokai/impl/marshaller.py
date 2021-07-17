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

__all__: list[str] = ["Marshaller"]

import typing
import uuid

import ciso8601

from .. import forums
from .. import lists
from .. import messages
from .. import reactions
from .. import users

if typing.TYPE_CHECKING:
    from ..api import marshaller as marshaller_api


def _get_creator_info(data: marshaller_api.JsonObjectT, /) -> tuple[str, users.CreatorType]:
    if webhook_id := data.get("createdByWebhookId"):
        return (webhook_id, users.CreatorType.WEBHOOK)

    if bot_id := data.get("createdByBotId"):
        return (bot_id, users.CreatorType.BOT)

    return (data["createdBy"], users.CreatorType.USER)


class Marshaller:
    __slots__: tuple[str, ...] = ()

    # fourms

    def unmarshall_fourm_thread(self, data: marshaller_api.JsonObjectT, /) -> forums.ForumThread:
        creator_id, creator_type = _get_creator_info(data)
        return forums.ForumThread(
            id=data["id"],
            created_at=ciso8601.parse_datetime(data["createdAt"]),
            creator_id=creator_id,
            creator_type=creator_type,
        )

    # lists

    def unmarshall_list_item(self, data: marshaller_api.JsonObjectT, /) -> lists.ListItem:
        creator_id, creator_type = _get_creator_info(data)
        return lists.ListItem(
            id=data["id"],
            message=data.get("message"),  # TODO: or None?
            note=data.get("note"),  # TODO: or None?
            created_at=ciso8601.parse_datetime(data["createdAt"]),
            creator_id=creator_id,
            creator_type=creator_type,
        )

    # messages

    def unmarshall_message(self, data: marshaller_api.JsonObjectT, /) -> messages.Message:
        creator_id, creator_type = _get_creator_info(data)
        raw_updated_at = data.get("updatedAt")
        return messages.Message(
            id=uuid.UUID(data["id"]),
            channel_id=uuid.UUID(data["channelId"]),
            content=data["content"],
            created_at=ciso8601.parse_datetime(data["createdAt"]),
            creator_id=creator_id,
            creator_type=creator_type,
            updated_at=ciso8601.parse_datetime(raw_updated_at) if raw_updated_at else None,
        )

    # reactions

    def unmarshall_content_reaction(self, data: marshaller_api.JsonObjectT, /) -> reactions.ContentReaction:
        creator_id, creator_type = _get_creator_info(data)
        return reactions.ContentReaction(
            id=data["id"],
            created_at=ciso8601.parse_datetime(data["createdAt"]),
            creator_id=creator_id,
            creator_type=creator_type,
        )
