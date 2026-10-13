"""Sensor exposing the YouVersion Verse of the Day."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_BIBLE_ID,
    ATTR_COPYRIGHT,
    ATTR_DATE,
    ATTR_DAY_OF_YEAR,
    ATTR_PASSAGE_ID,
    ATTR_REFERENCE,
    ATTR_TEXT,
    ATTR_URL,
    ATTR_VERSION,
    ATTR_VERSION_NAME,
    DOMAIN,
)
from .coordinator import YouVersionConfigEntry, YouVersionCoordinator

DEFAULT_ATTRIBUTION = "Verse of the Day from YouVersion"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: YouVersionConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensor."""
    async_add_entities([VerseOfTheDaySensor(entry.runtime_data)])


class VerseOfTheDaySensor(CoordinatorEntity[YouVersionCoordinator], SensorEntity):
    """State is the reference (e.g. "John 3:16"); the verse text is an attribute.

    Home Assistant caps states at 255 characters, which a verse can exceed.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "verse_of_the_day"

    def __init__(self, coordinator: YouVersionCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_verse_of_the_day"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="YouVersion",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://www.bible.com/verse-of-the-day",
        )

    @property
    def native_value(self) -> str:
        """Return the passage reference."""
        return self.coordinator.data.reference

    @property
    def attribution(self) -> str:
        """Credit YouVersion and the Bible version's publisher."""
        if copyright_ := self.coordinator.data.bible.copyright:
            return f"{DEFAULT_ATTRIBUTION}. {copyright_}"
        return DEFAULT_ATTRIBUTION

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the verse text and its metadata."""
        verse = self.coordinator.data
        return {
            ATTR_TEXT: verse.text,
            ATTR_REFERENCE: verse.reference,
            ATTR_PASSAGE_ID: verse.passage_id,
            ATTR_VERSION: verse.bible.abbreviation,
            ATTR_VERSION_NAME: verse.bible.title,
            ATTR_BIBLE_ID: verse.bible.id,
            ATTR_COPYRIGHT: verse.bible.copyright,
            ATTR_DAY_OF_YEAR: verse.day_of_year,
            ATTR_DATE: verse.date.isoformat(),
            ATTR_URL: verse.url,
        }
