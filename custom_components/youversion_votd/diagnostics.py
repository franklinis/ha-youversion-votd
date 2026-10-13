"""Diagnostics for YouVersion Verse of the Day."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .const import CONF_APP_KEY
from .coordinator import YouVersionConfigEntry

TO_REDACT = {CONF_APP_KEY}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: YouVersionConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry, without the app key."""
    verse = entry.runtime_data.data
    return {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "verse": None
        if verse is None
        else {
            "date": verse.date.isoformat(),
            "day_of_year": verse.day_of_year,
            "passage_id": verse.passage_id,
            "reference": verse.reference,
            "bible_id": verse.bible.id,
            "version": verse.bible.abbreviation,
        },
    }
