"""Tests for the config flow."""

from __future__ import annotations

from aiohttp import ClientError
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
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .conftest import APP_KEY, BIBLE_ID, BSB, KJV

BIBLES_URL = f"{API_BASE_URL}/v1/bibles"


async def test_full_flow(hass: HomeAssistant, mock_api: AiohttpClientMocker) -> None:
    """App key, then Bible picker, creates an entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_APP_KEY: f" {APP_KEY} ", CONF_LANGUAGE: "en"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "bible"
    # The BSB is preselected when the key can read it.
    schema_default = next(
        key.default() for key in result["data_schema"].schema if key == CONF_BIBLE_ID
    )
    assert schema_default == str(BIBLE_ID)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_BIBLE_ID: str(BIBLE_ID)}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "YouVersion BSB"
    assert result["data"] == {
        CONF_APP_KEY: APP_KEY,
        CONF_BIBLE_ID: BIBLE_ID,
        CONF_LANGUAGE: "en",
    }
    assert result["result"].unique_id == str(BIBLE_ID)


async def test_bibles_are_paginated(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Every page of /v1/bibles is offered in the picker."""
    aioclient_mock.get(
        BIBLES_URL,
        params={"page_token": "next"},
        json={"data": [BSB], "next_page_token": None},
    )
    aioclient_mock.get(BIBLES_URL, json={"data": [KJV], "next_page_token": "next"})

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_APP_KEY: APP_KEY, CONF_LANGUAGE: "en"}
    )
    assert result["step_id"] == "bible"
    selector = result["data_schema"].schema[CONF_BIBLE_ID]
    assert [option["value"] for option in selector.config["options"]] == ["3034", "1"]


@pytest.mark.parametrize(
    ("mock_kwargs", "error"),
    [
        ({"status": 401}, {"base": "invalid_auth"}),
        ({"status": 500}, {"base": "cannot_connect"}),
        ({"exc": ClientError()}, {"base": "cannot_connect"}),
        ({"json": {"data": [], "next_page_token": None}}, {CONF_LANGUAGE: "no_bibles"}),
    ],
)
async def test_user_step_errors(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_kwargs: dict,
    error: dict[str, str],
) -> None:
    """Errors are shown on the form, and the user can recover."""
    aioclient_mock.get(BIBLES_URL, **mock_kwargs)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_APP_KEY: APP_KEY, CONF_LANGUAGE: "en"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == error

    aioclient_mock.clear_requests()
    aioclient_mock.get(BIBLES_URL, json={"data": [BSB], "next_page_token": None})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_APP_KEY: APP_KEY, CONF_LANGUAGE: "en"}
    )
    assert result["step_id"] == "bible"


async def test_already_configured(
    hass: HomeAssistant,
    mock_api: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """The same Bible version cannot be added twice."""
    mock_config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_APP_KEY: APP_KEY, CONF_LANGUAGE: "en"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_BIBLE_ID: str(BIBLE_ID)}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """A rejected key can be replaced; a bad replacement shows an error first."""
    mock_config_entry.add_to_hass(hass)
    result = await mock_config_entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"

    aioclient_mock.get(f"{BIBLES_URL}/{BIBLE_ID}", status=401)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_APP_KEY: "still-bad"}
    )
    assert result["errors"] == {"base": "invalid_auth"}

    aioclient_mock.clear_requests()
    aioclient_mock.get(f"{BIBLES_URL}/{BIBLE_ID}", status=404)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_APP_KEY: "wrong-license"}
    )
    assert result["errors"] == {"base": "bible_unavailable"}

    aioclient_mock.clear_requests()
    aioclient_mock.get(f"{BIBLES_URL}/{BIBLE_ID}", json=BSB)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_APP_KEY: "new-key"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert mock_config_entry.data[CONF_APP_KEY] == "new-key"
