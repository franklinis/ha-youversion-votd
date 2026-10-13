"""Minimal async client for the YouVersion Platform API.

Endpoints mirror YouVersion's official SDKs (https://github.com/youversion):
  GET /v1/verse_of_the_days/{day}
  GET /v1/bibles?language_ranges[]=..
  GET /v1/bibles/{bible_id}
  GET /v1/bibles/{bible_id}/passages/{passage_id}
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import re
from typing import Any

import aiohttp

from .const import API_BASE_URL, API_TIMEOUT

_WHITESPACE = re.compile(r"\s+")
_MAX_PAGES = 20


class YouVersionError(Exception):
    """Base error for the YouVersion API."""


class YouVersionConnectionError(YouVersionError):
    """The API could not be reached."""


class YouVersionAuthError(YouVersionError):
    """The app key was rejected."""


class YouVersionNotFoundError(YouVersionError):
    """The requested resource does not exist or is not available to this app key."""


@dataclass(frozen=True, slots=True)
class Bible:
    """A Bible version and the metadata needed to attribute it."""

    id: int
    abbreviation: str
    title: str
    copyright: str | None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Bible:
        """Build from a /v1/bibles item."""
        return cls(
            id=int(data["id"]),
            abbreviation=data.get("localized_abbreviation")
            or data.get("abbreviation")
            or str(data["id"]),
            title=data.get("localized_title") or data.get("title") or "",
            copyright=data.get("copyright") or None,
        )


@dataclass(frozen=True, slots=True)
class Passage:
    """Plain-text scripture for a passage."""

    id: str
    reference: str
    text: str


class YouVersionClient:
    """Talks to api.youversion.com with an app key from platform.youversion.com."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        app_key: str,
        base_url: str = API_BASE_URL,
    ) -> None:
        """Initialize the client."""
        self._session = session
        self._app_key = app_key
        self._base_url = base_url.rstrip("/")

    async def _get(
        self, path: str, params: list[tuple[str, str]] | None = None
    ) -> dict[str, Any]:
        headers = {"Accept": "application/json", "X-YVP-App-Key": self._app_key}
        try:
            async with (
                asyncio.timeout(API_TIMEOUT),
                self._session.get(
                    f"{self._base_url}{path}", params=params, headers=headers
                ) as resp,
            ):
                if resp.status == 401:
                    raise YouVersionAuthError("YouVersion rejected the app key")
                if resp.status == 404:
                    raise YouVersionNotFoundError(f"{path} was not found")
                if resp.status >= 400:
                    raise YouVersionError(f"{path} returned HTTP {resp.status}")
                data = await resp.json(content_type=None)
        except TimeoutError as err:
            raise YouVersionConnectionError(f"Timed out requesting {path}") from err
        except aiohttp.ClientError as err:
            raise YouVersionConnectionError(f"Error requesting {path}: {err}") from err
        except ValueError as err:
            raise YouVersionError(f"{path} returned invalid JSON") from err

        if not isinstance(data, dict):
            raise YouVersionError(f"{path} returned an unexpected response")
        return data

    async def get_verse_of_the_day(self, day: int) -> str:
        """Return the USFM passage id (e.g. "JHN.3.16") for a day of the year (1-366)."""
        if not 1 <= day <= 366:
            raise ValueError(f"day must be between 1 and 366, got {day}")
        data = await self._get(f"/v1/verse_of_the_days/{day}")
        try:
            return str(data["passage_id"])
        except KeyError as err:
            raise YouVersionError(
                "Verse of the day response had no passage_id"
            ) from err

    async def get_passage(self, bible_id: int, passage_id: str) -> Passage:
        """Return the plain text of a passage in the given Bible."""
        data = await self._get(
            f"/v1/bibles/{bible_id}/passages/{passage_id}", [("format", "text")]
        )
        try:
            return Passage(
                id=str(data.get("id") or passage_id),
                reference=str(data["reference"]),
                text=_WHITESPACE.sub(" ", str(data["content"])).strip(),
            )
        except KeyError as err:
            raise YouVersionError("Passage response was missing fields") from err

    async def get_bible(self, bible_id: int) -> Bible:
        """Return metadata (abbreviation, title, copyright) for one Bible."""
        return Bible.from_api(await self._get(f"/v1/bibles/{bible_id}"))

    async def get_bibles(self, language: str) -> list[Bible]:
        """Return every Bible this app key can read for a language (e.g. "en")."""
        params = [("language_ranges[]", language)]
        bibles: list[Bible] = []
        page_token: str | None = None
        for _ in range(_MAX_PAGES):
            page = await self._get(
                "/v1/bibles",
                params + ([("page_token", page_token)] if page_token else []),
            )
            bibles.extend(Bible.from_api(item) for item in page.get("data") or [])
            page_token = page.get("next_page_token")
            if not page_token:
                break
        return bibles
