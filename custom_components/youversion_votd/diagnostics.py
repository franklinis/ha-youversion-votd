"""Diagnostics for Bible Verse of the Day."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from .coordinator import BibleConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: BibleConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry (it holds no secrets)."""
    verse = entry.runtime_data.data
    return {
        "entry": entry.as_dict(),
        "verse": None
        if verse is None
        else {
            "date": verse.date.isoformat(),
            "reference_en": verse.daily.reference,
            "passage_id": verse.daily.passage_id,
            "reference": verse.passage.reference,
            "translation": verse.translation.id,
            "fallback": verse.fallback,
        },
    }
