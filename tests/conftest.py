"""Fixtures for YouVersion Verse of the Day tests."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.youversion_votd.const import (
    API_BASE_URL,
    CONF_APP_KEY,
    CONF_BIBLE_ID,
    CONF_LANGUAGE,
    DOMAIN,
)

APP_KEY = "test-app-key"
BIBLE_ID = 3034
# 2026-10-13 is day 286 of the year; noon in the test suite's US/Pacific time zone.
FROZEN_TIME = "2026-10-13T19:00:00+00:00"
DAY = 286

BSB: dict[str, Any] = {
    "id": 3034,
    "abbreviation": "BSB",
    "localized_abbreviation": "BSB",
    "title": "Berean Standard Bible",
    "localized_title": "Berean Standard Bible",
    "language_tag": "en",
    "copyright": "The Berean Bible and Majority Bible texts are officially placed into the public domain.",
}
KJV: dict[str, Any] = {
    "id": 1,
    "abbreviation": "KJV",
    "localized_abbreviation": "KJV",
    "title": "King James Version",
    "localized_title": "King James Version",
    "language_tag": "en",
    "copyright": None,
}
VOTD = {"day": DAY, "passage_id": "PHP.4.6-7"}
PASSAGE = {
    "id": "PHP.4.6-7",
    "reference": "Philippians 4:6-7",
    "content": (
        "Be anxious for nothing, but in everything, by prayer and petition, with "
        "thanksgiving, present your requests to God.\n  And the peace of God, which "
        "surpasses all understanding, will guard your hearts and your minds in "
        "Christ Jesus. "
    ),
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Load the integration from custom_components/."""


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """A configured entry for the BSB."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="YouVersion BSB",
        unique_id=str(BIBLE_ID),
        data={CONF_APP_KEY: APP_KEY, CONF_BIBLE_ID: BIBLE_ID, CONF_LANGUAGE: "en"},
    )


@pytest.fixture
def mock_api(aioclient_mock: AiohttpClientMocker) -> Generator[AiohttpClientMocker]:
    """Mock every YouVersion endpoint the integration calls."""
    aioclient_mock.get(f"{API_BASE_URL}/v1/verse_of_the_days/{DAY}", json=VOTD)
    aioclient_mock.get(
        f"{API_BASE_URL}/v1/bibles/{BIBLE_ID}/passages/PHP.4.6-7", json=PASSAGE
    )
    aioclient_mock.get(f"{API_BASE_URL}/v1/bibles/{BIBLE_ID}", json=BSB)
    aioclient_mock.get(
        f"{API_BASE_URL}/v1/bibles",
        json={"data": [KJV, BSB], "next_page_token": None},
    )
    yield aioclient_mock
