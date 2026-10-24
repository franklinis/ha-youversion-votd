"""Tests for the config and reconfigure flows."""

from __future__ import annotations

from aiohttp import ClientError
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.youversion_votd.const import BIBLE_API_URL, DOMAIN
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .conftest import entry_data


def _default(result: dict, field: str) -> str:
    """The value a form field starts with."""
    return next(k for k in result["data_schema"].schema if str(k) == field).default()


async def _start(hass: HomeAssistant) -> dict:
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )


async def test_full_flow(hass: HomeAssistant, mock_api: AiohttpClientMocker) -> None:
    """Pick a language, then a translation; no key is asked for."""
    hass.config.language = "de"
    result = await _start(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert (
        _default(result, "language") == "deu"
    )  # suggested from Home Assistant's language

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"language": "deu"}
    )
    assert result["step_id"] == "translation"
    assert _default(result, "translation") == "deu_l12"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"translation": "deu_l12"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Bible L12"
    assert result["data"] == entry_data("deu_l12")
    assert result["result"].unique_id == "deu_l12"


async def test_unknown_ha_language_suggests_english(
    hass: HomeAssistant, mock_api: AiohttpClientMocker
) -> None:
    hass.config.language = "eo"
    result = await _start(hass)
    assert _default(result, "language") == "eng"


async def test_cannot_connect(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(
        f"{BIBLE_API_URL}/available_translations.json", exc=ClientError()
    )
    result = await _start(hass)
    assert result["errors"] == {"base": "cannot_connect"}


async def test_already_configured(
    hass: HomeAssistant,
    mock_api: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    mock_config_entry.add_to_hass(hass)
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"language": "eng"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"translation": "BSB"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reconfigure(
    hass: HomeAssistant,
    mock_api: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Change the language and translation later."""
    mock_config_entry.add_to_hass(hass)
    result = await mock_config_entry.start_reconfigure_flow(hass)
    assert _default(result, "language") == "eng"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"language": "tam"}
    )
    assert _default(result, "translation") == "tam_irv"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"translation": "tam_irv"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert mock_config_entry.data == entry_data("tam_irv")
    assert mock_config_entry.unique_id == "tam_irv"
    assert mock_config_entry.title == "Bible IRV"


async def test_reconfigure_to_a_translation_set_up_elsewhere(
    hass: HomeAssistant,
    mock_api: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    mock_config_entry.add_to_hass(hass)
    MockConfigEntry(
        domain=DOMAIN, unique_id="deu_l12", version=2, data=entry_data("deu_l12")
    ).add_to_hass(hass)
    result = await mock_config_entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"language": "deu"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"translation": "deu_l12"}
    )
    assert result["reason"] == "already_configured"
    assert mock_config_entry.unique_id == "BSB"
