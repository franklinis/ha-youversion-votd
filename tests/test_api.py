"""Tests for the YouVersion API client."""

from __future__ import annotations

import pytest
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.youversion_votd.api import (
    Bible,
    YouVersionClient,
    YouVersionError,
    YouVersionNotFoundError,
)
from custom_components.youversion_votd.const import API_BASE_URL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .conftest import KJV


@pytest.fixture
async def client(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> YouVersionClient:
    """A client using the mocked session."""
    return YouVersionClient(async_get_clientsession(hass), "key")


@pytest.mark.parametrize("day", [0, 367])
async def test_day_out_of_range(client: YouVersionClient, day: int) -> None:
    """Days outside 1-366 are rejected before any request."""
    with pytest.raises(ValueError):
        await client.get_verse_of_the_day(day)


@pytest.mark.parametrize(
    ("mock_kwargs", "error"),
    [
        ({"text": "not json"}, YouVersionError),
        ({"json": ["not", "an", "object"]}, YouVersionError),
        ({"json": {"day": 1}}, YouVersionError),
        ({"status": 404}, YouVersionNotFoundError),
    ],
)
async def test_bad_verse_of_the_day_response(
    client: YouVersionClient,
    aioclient_mock: AiohttpClientMocker,
    mock_kwargs: dict,
    error: type[Exception],
) -> None:
    """Malformed or missing responses raise a typed error."""
    aioclient_mock.get(f"{API_BASE_URL}/v1/verse_of_the_days/1", **mock_kwargs)
    with pytest.raises(error):
        await client.get_verse_of_the_day(1)


async def test_passage_missing_fields(
    client: YouVersionClient, aioclient_mock: AiohttpClientMocker
) -> None:
    """A passage without content raises a typed error."""
    aioclient_mock.get(
        f"{API_BASE_URL}/v1/bibles/1/passages/JHN.3.16", json={"reference": "John 3:16"}
    )
    with pytest.raises(YouVersionError):
        await client.get_passage(1, "JHN.3.16")


def test_bible_falls_back_to_unlocalized_fields() -> None:
    """Bibles without localized fields or copyright still parse."""
    bible = Bible.from_api({"id": "1", "abbreviation": "KJV", "title": "King James"})
    assert bible == Bible(id=1, abbreviation="KJV", title="King James", copyright=None)
    assert Bible.from_api(KJV).copyright is None
