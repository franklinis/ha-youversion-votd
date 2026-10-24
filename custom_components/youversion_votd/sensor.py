"""Sensor exposing the Bible verse of the day."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_DATE,
    ATTR_FALLBACK,
    ATTR_LANGUAGE,
    ATTR_LICENSE,
    ATTR_PASSAGE_ID,
    ATTR_REFERENCE,
    ATTR_REFERENCE_EN,
    ATTR_TEXT,
    ATTR_TRANSLATION,
    ATTR_TRANSLATION_NAME,
    ATTR_URL,
    DOMAIN,
)
from .coordinator import BibleConfigEntry, BibleCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BibleConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensor."""
    async_add_entities([VerseOfTheDaySensor(entry.runtime_data)])


class VerseOfTheDaySensor(CoordinatorEntity[BibleCoordinator], SensorEntity):
    """State is the reference (e.g. "John 3:16"); the verse text is an attribute.

    Home Assistant caps states at 255 characters, which a verse can exceed.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "verse_of_the_day"

    def __init__(self, coordinator: BibleCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_verse_of_the_day"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="DailyVerses.net",
            model=coordinator.translation.name,
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://dailyverses.net",
        )

    @property
    def native_value(self) -> str:
        """Return the reference in the translation's language."""
        return self.coordinator.data.passage.reference

    @property
    def attribution(self) -> str:
        """Credit the verse selection and the translation."""
        return (
            "Verse selection: DailyVerses.net. Text: "
            f"{self.coordinator.data.translation.name} via the Free Use Bible API"
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the verse text and its metadata."""
        verse = self.coordinator.data
        return {
            ATTR_TEXT: verse.passage.text,
            ATTR_REFERENCE: verse.passage.reference,
            ATTR_REFERENCE_EN: verse.daily.reference,
            ATTR_PASSAGE_ID: verse.daily.passage_id,
            ATTR_TRANSLATION: verse.translation.short_name,
            ATTR_TRANSLATION_NAME: verse.translation.name,
            ATTR_LANGUAGE: verse.translation.language,
            ATTR_LICENSE: verse.translation.license_url,
            ATTR_FALLBACK: verse.fallback,
            ATTR_DATE: verse.date.isoformat(),
            ATTR_URL: verse.daily.url,
        }
