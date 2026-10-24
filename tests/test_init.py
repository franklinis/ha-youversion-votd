"""Tests for setup, the sensor, the daily refresh and migration from YouVersion."""

from __future__ import annotations

from datetime import timedelta

from aiohttp import ClientError
from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.youversion_votd.const import (
    BIBLE_API_URL,
    DAILYVERSES_WIDGET_URL,
    DOMAIN,
)
from custom_components.youversion_votd.diagnostics import (
    async_get_config_entry_diagnostics,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_ATTRIBUTION, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant

from .conftest import FROZEN_TIME, WIDGET, entry_data

ENTITY_ID = "sensor.bible_bsb_verse_of_the_day"


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def _calls(aioclient_mock: AiohttpClientMocker, url: str) -> int:
    return sum(1 for call in aioclient_mock.mock_calls if str(call[1]) == url)


@pytest.mark.freeze_time(FROZEN_TIME)
async def test_sensor(
    hass: HomeAssistant,
    mock_api: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """The sensor shows the reference, with the text and credits attached."""
    await _setup(hass, mock_config_entry)
    assert mock_config_entry.state is ConfigEntryState.LOADED
    state = hass.states.get(ENTITY_ID)
    assert state.state == "Philippians 4:6-7"
    assert state.attributes["text"].startswith(
        "Be anxious for nothing, but in everything"
    )
    assert state.attributes["reference_en"] == "Philippians 4:6-7"
    assert state.attributes["passage_id"] == "PHP.4.6-7"
    assert state.attributes["translation"] == "BSB"
    assert state.attributes["translation_name"] == "Berean Standard Bible"
    assert state.attributes["language"] == "eng"
    assert state.attributes["license"] == "https://example.org/BSB"
    assert state.attributes["fallback"] is False
    assert state.attributes["date"] == "2026-10-13"
    assert state.attributes["url"] == "https://dailyverses.net/2026/10/13"
    assert "DailyVerses.net" in state.attributes[ATTR_ATTRIBUTION]

    diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)
    assert diagnostics["verse"]["translation"] == "BSB"


@pytest.mark.freeze_time(FROZEN_TIME)
async def test_german_reference_uses_its_own_book_name(
    hass: HomeAssistant, mock_api: AiohttpClientMocker
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Bible L12",
        unique_id="deu_l12",
        version=2,
        data=entry_data("deu_l12"),
    )
    await _setup(hass, entry)
    state = hass.states.get("sensor.bible_l12_verse_of_the_day")
    assert state.state == "Philipper 4,6-7"
    assert state.attributes["text"] == "Sorget nichts! Und der Friede Gottes ..."


@pytest.mark.freeze_time(FROZEN_TIME)
async def test_falls_back_when_the_translation_lacks_the_book(
    hass: HomeAssistant, mock_api: AiohttpClientMocker
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Bible ENT",
        unique_id="xyz_nt",
        version=2,
        data=entry_data("xyz_nt"),
    )
    await _setup(hass, entry)
    state = hass.states.get("sensor.bible_ent_verse_of_the_day")
    assert state.state == "Philippians 4:6-7"
    assert state.attributes["fallback"] is True
    assert state.attributes["translation"] == "BSB"


@pytest.mark.freeze_time(FROZEN_TIME)
async def test_fetches_once_per_day(
    hass: HomeAssistant,
    mock_api: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Hourly updates on the same day use the cached verse; the next day asks again."""
    await _setup(hass, mock_config_entry)
    assert _calls(mock_api, DAILYVERSES_WIDGET_URL) == 1
    freezer.tick(timedelta(hours=3))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert _calls(mock_api, DAILYVERSES_WIDGET_URL) == 1

    freezer.tick(timedelta(days=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    # A new local day asks DailyVerses.net again; it still shows the 13th (it keeps
    # being asked hourly until it moves on), so the text isn't fetched again.
    assert _calls(mock_api, DAILYVERSES_WIDGET_URL) >= 2
    assert _calls(mock_api, f"{BIBLE_API_URL}/BSB/PHP/4.json") == 1


@pytest.mark.freeze_time(FROZEN_TIME)
async def test_setup_retries_when_offline(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    aioclient_mock.get(DAILYVERSES_WIDGET_URL, exc=ClientError())
    await _setup(hass, mock_config_entry)
    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


@pytest.mark.freeze_time(FROZEN_TIME)
async def test_unavailable_after_a_failed_new_day(
    hass: HomeAssistant,
    mock_api: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    await _setup(hass, mock_config_entry)
    mock_api.clear_requests()
    mock_api.get(DAILYVERSES_WIDGET_URL, exc=ClientError())
    freezer.tick(timedelta(days=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY_ID).state == STATE_UNAVAILABLE


async def test_unload(
    hass: HomeAssistant,
    mock_api: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    await _setup(hass, mock_config_entry)
    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED


@pytest.mark.freeze_time(FROZEN_TIME)
@pytest.mark.parametrize(
    ("language", "translation", "title"),
    [
        ("en", "BSB", "Bible BSB"),
        ("de", "deu_l12", "Bible L12"),
        ("eo", "BSB", "Bible BSB"),
    ],
)
async def test_migrates_youversion_entries(
    hass: HomeAssistant,
    mock_api: AiohttpClientMocker,
    language: str,
    translation: str,
    title: str,
) -> None:
    """Old entries held a YouVersion app key; they move to a free translation in their language."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="YouVersion BSB",
        unique_id="3034",
        version=1,
        data={"app_key": "secret", "bible_id": 3034, "language": language},
    )
    await _setup(hass, entry)
    assert entry.state is ConfigEntryState.LOADED
    assert entry.version == 2
    assert entry.data == entry_data(translation)
    assert "app_key" not in entry.data
    assert entry.unique_id == translation and entry.title == title


async def test_migration_offline_uses_the_fallback(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(
        f"{BIBLE_API_URL}/available_translations.json", exc=ClientError()
    )
    aioclient_mock.get(DAILYVERSES_WIDGET_URL, text=WIDGET)
    entry = MockConfigEntry(
        domain=DOMAIN, version=1, data={"app_key": "x", "bible_id": 1, "language": "de"}
    )
    await _setup(hass, entry)
    assert entry.version == 2 and entry.data["translation"] == "BSB"
