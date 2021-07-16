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

__all__: list[str] = ["RestClient"]

import types
import typing
import uuid

import httpx

if typing.TYPE_CHECKING:
    # import collections.abc as collections
    import ssl

    from .. import forums
    from .. import messages
    from ..api import marshaller as marshaller_
    from ..api import paginator

    _JsonObjectT_inv = typing.TypeVar("_JsonObjectT_inv", bound=marshaller_.JsonObjectT)

_ValueT = typing.TypeVar("_ValueT")

UuidIsh: typing.TypeAlias = str | uuid.UUID
UndefinedOr: typing.TypeAlias = types.EllipsisType | _ValueT
UndefinedNoneOr: typing.TypeAlias = types.EllipsisType | None | _ValueT


def _put_undefined(json: _JsonObjectT_inv, name: str, value: UndefinedOr[marshaller_.JsonIsh], /) -> _JsonObjectT_inv:
    if value is not ...:
        json[name] = value

    return json


STANDARD_URL: typing.Final[str] = "https://www.guilded.gg/api/v1/"

_AUTHORIZATION_HEADER_KEY: typing.Final[str] = "Authorization"
_CONTENT_TYPE_KEY: typing.Final[str] = "Content-Type"
_JSON_CONTENT_TYPE: typing.Final[str] = "application/json"

_DELETE: typing.Final[str] = "DELETE"
_GET: typing.Final[str] = "GET"
_PATCH: typing.Final[str] = "PATCH"
_POST: typing.Final[str] = "POST"
_PUT: typing.Final[str] = "PUT"


class RestClient:
    __slots__: tuple[str, ...] = ("_base_url", "_client", "_marshaller", "_token")

    def __init__(
        self,
        token: str | None,
        /,
        marshaller: marshaller_.Marshaller,
        *,
        base_url: str = STANDARD_URL,
    ) -> None:
        self._base_url = base_url
        self._client: httpx.AsyncClient | None = None
        self._marshaller = marshaller
        self._token = f"Bearer {token}"

    async def __aenter__(self) -> RestClient:
        await self.start()
        return self

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        exception_traceback: types.TracebackType | None,
    ) -> None:
        await self.close()

    @property
    def is_running(self) -> bool:
        return self._client is not None

    @classmethod
    def spawn(
        cls,
        token: str | None,
        /,
        *,
        marshaller: marshaller_.Marshaller | None = None,
        base_url: str = STANDARD_URL,
        verify: str | bool | ssl.SSLContext = True,
        # cert: str | tuple[str, str | None] | tuple[str, str | None, str | None] | None = None,
        http1: bool = True,
        http2: bool = True,
        # proxy: httpx.URL | str | httpx.Proxy | None = None,
        timeout: float | httpx.Timeout = httpx.Timeout(timeout=0.5),
        limits: httpx.Limits = httpx.Limits(max_connections=100, max_keepalive_connections=20),
        max_redirects: int = 20,
        trust_env: bool = True,
    ) -> RestClient:
        if marshaller is None:
            from ..impl import marshaller as marshaller_impl

            marshaller = marshaller_impl.Marshaller()

        return cls(token, marshaller=marshaller, base_url=base_url)

    async def start(
        self,
        verify: str | bool | ssl.SSLContext = True,
        # cert: str | tuple[str, str | None] | tuple[str, str | None, str | None] | None = None,
        http1: bool = True,
        http2: bool = True,
        # proxy: httpx.URL | str | httpx.Proxy | None = None,
        timeout: float | httpx.Timeout = httpx.Timeout(timeout=0.5),
        limits: httpx.Limits = httpx.Limits(max_connections=100, max_keepalive_connections=20),
        max_redirects: int = 20,
        trust_env: bool = True,
    ) -> None:
        if self._client:
            raise RuntimeError("Client is already running")

        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            verify=verify,
            # cert=cert,
            http1=http1,
            http2=http2,
            # proxies=proxy,
            timeout=timeout,
            limits=limits,
            max_redirects=max_redirects,
            trust_env=trust_env,
        )

    async def close(self) -> None:
        if self._client is None:
            raise RuntimeError("Cannot close RESTClient while it's inactive")

        client = self._client
        self._client = None
        await client.aclose()

    # Role membership

    async def _request(
        self,
        method: str,
        route: str,
        json: marshaller_.JsonArrayT | marshaller_.JsonObjectT | None = None,
        *,
        use_auth: bool = True,
    ) -> marshaller_.JsonArrayT | marshaller_.JsonObjectT | None:
        if self._client is None:
            raise RuntimeError("Cannot use an inactive client")

        headers: dict[str, str] = {}  # TODO: default to None and build dict as neccessary
        if use_auth:
            if not self._token:
                raise RuntimeError("Cannot make this request with a token-less client")

            headers[_AUTHORIZATION_HEADER_KEY] = self._token

        response = await self._client.request(method, route, headers=headers, json=json)
        content_type: str | None = response.headers.get(_CONTENT_TYPE_KEY)

        match response.status_code:
            case 204:
                return None
            case 200 | 201 | 202 | 203 | 206 if content_type == _JSON_CONTENT_TYPE:
                return response.json()
            case _:
                raise NotImplementedError

    async def delete(self, route: str, /, *, use_auth: bool = True) -> None:
        await self._request(_DELETE, route, use_auth=use_auth)

    async def get(self, route: str, /, *, use_auth: bool = True) -> marshaller_.JsonObjectT | marshaller_.JsonArrayT:
        response = await self._request(_GET, route, use_auth=use_auth)
        assert response is not None, "GET shouldn't ever return no body"
        return response

    async def patch(
        self, route: str, /, json: marshaller_.JsonArrayT | marshaller_.JsonObjectT, *, use_auth: bool = True
    ) -> marshaller_.JsonArrayT | marshaller_.JsonObjectT | None:
        return await self._request(_PATCH, route, json=json, use_auth=use_auth)

    async def post(
        self, route: str, /, json: marshaller_.JsonArrayT | marshaller_.JsonObjectT, *, use_auth: bool = True
    ) -> marshaller_.JsonArrayT | marshaller_.JsonObjectT | None:
        return await self._request(_POST, route, json=json, use_auth=use_auth)

    async def put(
        self,
        route: str,
        /,
        json: marshaller_.JsonArrayT | marshaller_.JsonObjectT | None = None,
        *,
        use_auth: bool = True,
    ) -> marshaller_.JsonArrayT | marshaller_.JsonObjectT | None:
        return await self._request(_PUT, route, json=json, use_auth=use_auth)

    async def post_member_role(self, user_id: str, role_id: int, /) -> None:
        await self.put(f"/members/{user_id}/roles/{role_id}")

    async def delete_member_role(self, user_id: str, role_id: int, /) -> None:
        await self.delete(f"/members/{user_id}/roles/{role_id}")

    # Group membership

    async def put_group_member(self, group_id: str, user_id: str, /) -> None:
        await self.put(f"/groups/{group_id}/members/{user_id}")

    async def delete_group_member(self, group_id: str, user_id: str, /) -> None:
        await self.delete(f"/groups/{group_id}/members/{user_id}")

    # Forums

    async def post_channel_forum(self, channel_id: UuidIsh, /, *, title: str, content: str) -> forums.ForumThread:
        payload: marshaller_.JsonObjectT = {"title": title, "content": content}
        response = await self.post(f"/channels/{channel_id}/forum", json=payload)
        assert isinstance(response, dict)
        return self._marshaller.unmarshall_fourm_thread(response["forumThread"])

    # Chat

    def _build_message(self, content: str, /) -> marshaller_.JsonObjectT:
        return {"content": content}

    async def post_channel_message(self, channel_id: UuidIsh, /, content: str) -> messages.Message:
        payload = self._build_message(content)
        response = await self.post(f"/channels/{channel_id}/messages", json=payload)
        assert isinstance(response, dict)
        return self._marshaller.unmarshall_message(response["message"])

    async def iter_channel_messages(self, channel_id: UuidIsh, /) -> paginator.Paginator[messages.Message]:
        raise NotImplementedError

    async def get_channel_message(self, channel_id: UuidIsh, message_id: UuidIsh, /) -> messages.Message:
        response = await self.get(f"/channels/{channel_id}/messages/{message_id}")
        assert isinstance(response, dict)
        return self._marshaller.unmarshall_message(response["message"])

    async def put_channel_message(self, channel_id: UuidIsh, message_id: UuidIsh, /, content: str) -> messages.Message:
        payload = self._build_message(content)
        response = await self.put(f"/channels/{channel_id}/messages/{message_id}", json=payload)
        assert isinstance(response, dict)
        return self._marshaller.unmarshall_message(response["message"])

    async def delete_channel_message(self, channel_id: UuidIsh, message_id: UuidIsh, /) -> None:
        await self.delete(f"/channels/{channel_id}/messages/{message_id}")

    # Reactions

    async def put_content_reaction(self, channel_id: UuidIsh, content_id: UuidIsh, emote_id: int, /) -> None:
        await self.put(f"/channels/{channel_id}/content/{channel_id}/emotes/{emote_id}")

    # List items

    async def post_channel_list(self, channel_id: UuidIsh, /, message: str, *, note: UndefinedOr[str] = ...) -> ...:
        payload: marshaller_.JsonObjectT = {"message": message}
        _put_undefined(payload, "note", note)
        response = await self.post(f"/channels/{channel_id}/list", json=payload)
        assert isinstance(response, dict)
        return self._marshaller.unmarshall_list_item(response["listItem"])

    # Team XP

    async def post_member_xp(self, user_id: UuidIsh, /, amount: int) -> int:
        payload: marshaller_.JsonObjectT = {"amount": amount}
        response = await self.post(f"/members/{user_id}/xp", json=payload)
        assert isinstance(response, dict)
        result = response["amount"]
        assert isinstance(result, int)
        return result

    async def post_role_xp(self, role_id: UuidIsh, /, amount: int) -> None:
        payload: marshaller_.JsonObjectT = {"amount": amount}
        await self.post(f"/roles/{role_id}/xp", json=payload)
