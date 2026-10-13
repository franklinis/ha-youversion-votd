"""Tests for setup, the sensor, and the daily refresh."""

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

from custom_components.youversion_votd.const import API_BASE_URL, DOMAIN
from custom_components.youversion_votd.diagnostics import (
    async_get_config_entry_diagnostics,
)
from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntryState
from homeassistant.const import ATTR_ATTRIBUTION, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant

from .conftest import APP_KEY, BIBLE_ID, BSB, DAY, FROZEN_TIME, PASSAGE, VOTD

ENTITY_ID = "sensor.youversion_bsb_verse_of_the_day"
VOTD_URL = f"{API_BASE_URL}/v1/verse_of_the_days/{DAY}"


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


@pytest.mark.freeze_time(FROZEN_TIME)
async def test_sensor(
    hass: HomeAssistant,
    mock_api: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """The sensor shows the reference, with the text and attribution attached."""
    await _setup(hass, mock_config_entry)
    assert mock_config_entry.state is ConfigEntryState.LOADED

    state = hass.states.get(ENTITY_ID)
    assert state is not None
    assert state.state == "Philippians 4:6-7"
    assert state.attributes["text"] == (
        "Be anxious for nothing, but in everything, by prayer and petition, with "
        "thanksgiving, present your requests to God. And the peace of God, which "
        "surpasses all understanding, will guard your hearts and your minds in "
        "Christ Jesus."
    )
    assert state.attributes["reference"] == "Philippians 4:6-7"
    assert state.attributes["passage_id"] == "PHP.4.6-7"
    assert state.attributes["version"] == "BSB"
    assert state.attributes["version_name"] == "Berean Standard Bible"
    assert state.attributes["bible_id"] == BIBLE_ID
    assert state.attributes["copyright"] == BSB["copyright"]
    assert state.attributes["day_of_year"] == DAY
    assert state.attributes["date"] == "2026-10-13"
    assert state.attributes["url"] == "https://www.bible.com/bible/3034/PHP.4.6-7"
    assert state.attributes[ATTR_ATTRIBUTION] == (
        f"Verse of the Day from YouVersion. {BSB['copyright']}"
    )

    # The app key is sent as a header, never in the URL.
    _, url, _, headers = mock_api.mock_calls[0]
    assert APP_KEY not in str(url)
    assert headers["X-YVP-App-Key"] == APP_KEY
    assert ("format", "text") in mock_api.mock_calls[1][1].query.items()

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED


@pytest.mark.freeze_time(FROZEN_TIME)
async def test_fetches_once_per_day(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    mock_api: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Hourly polls reuse today's verse; local midnight fetches tomorrow's."""
    await _setup(hass, mock_config_entry)
    assert mock_api.call_count == 3

    freezer.tick(timedelta(hours=3))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert mock_api.call_count == 3

    mock_api.get(
        f"{API_BASE_URL}/v1/verse_of_the_days/{DAY + 1}",
        json={"day": DAY + 1, "passage_id": "PSA.23.1"},
    )
    mock_api.get(
        f"{API_BASE_URL}/v1/bibles/{BIBLE_ID}/passages/PSA.23.1",
        json={
            "id": "PSA.23.1",
            "reference": "Psalm 23:1",
            "content": "The LORD is my shepherd; I shall not want.",
        },
    )
    # 00:00:05 local on Oct 14 (US/Pacific, UTC-7).
    freezer.move_to("2026-10-14T07:00:05+00:00")
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    state = hass.states.get(ENTITY_ID)
    assert state.state == "Psalm 23:1"
    assert state.attributes["day_of_year"] == DAY + 1
    assert state.attributes["date"] == "2026-10-14"
    # Bible metadata is cached, so only the verse and passage were fetched.
    assert mock_api.call_count == 5


@pytest.mark.freeze_time(FROZEN_TIME)
async def test_setup_retries_when_api_down(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """A network error at startup schedules a retry."""
    aioclient_mock.get(VOTD_URL, exc=ClientError())
    await _setup(hass, mock_config_entry)
    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


@pytest.mark.freeze_time(FROZEN_TIME)
async def test_rejected_key_starts_reauth(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """A 401 stops setup and asks the user for a new key."""
    aioclient_mock.get(VOTD_URL, status=401)
    await _setup(hass, mock_config_entry)
    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR

    flows = hass.config_entries.flow.async_progress()
    assert len(flows) == 1
    assert flows[0]["context"]["source"] == SOURCE_REAUTH
    assert flows[0]["context"]["entry_id"] == mock_config_entry.entry_id


@pytest.mark.freeze_time(FROZEN_TIME)
async def test_unavailable_when_new_day_fails(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Yesterday's verse is not shown as today's when the API is down."""
    aioclient_mock.get(VOTD_URL, json=VOTD)
    aioclient_mock.get(
        f"{API_BASE_URL}/v1/bibles/{BIBLE_ID}/passages/PHP.4.6-7", json=PASSAGE
    )
    aioclient_mock.get(f"{API_BASE_URL}/v1/bibles/{BIBLE_ID}", json=BSB)
    aioclient_mock.get(f"{API_BASE_URL}/v1/verse_of_the_days/{DAY + 1}", status=503)
    await _setup(hass, mock_config_entry)

    freezer.move_to("2026-10-14T07:00:05+00:00")
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY_ID).state == STATE_UNAVAILABLE


@pytest.mark.freeze_time(FROZEN_TIME)
async def test_diagnostics_redact_app_key(
    hass: HomeAssistant,
    mock_api: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Diagnostics never include the app key."""
    await _setup(hass, mock_config_entry)
    diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)
    assert diagnostics["entry"]["data"]["app_key"] == "**REDACTED**"
    assert APP_KEY not in str(diagnostics)
    assert diagnostics["verse"]["passage_id"] == "PHP.4.6-7"
    assert diagnostics["entry"]["domain"] == DOMAIN
