"""Coordinator that fetches the verse of the day once per day."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import (
    BibleClient,
    BibleError,
    BibleNotFoundError,
    DailyVerse,
    Passage,
    Translation,
)
from .const import (
    CONF_LANGUAGE,
    CONF_LICENSE_URL,
    CONF_SHORT_NAME,
    CONF_TRANSLATION,
    CONF_TRANSLATION_NAME,
    DOMAIN,
    FALLBACK_TRANSLATION,
    UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

type BibleConfigEntry = ConfigEntry[BibleCoordinator]


def translation_from(data: dict[str, Any]) -> Translation:
    """The translation saved in a config entry."""
    return Translation(
        id=data[CONF_TRANSLATION],
        name=data.get(CONF_TRANSLATION_NAME) or data[CONF_TRANSLATION],
        short_name=data.get(CONF_SHORT_NAME) or data[CONF_TRANSLATION],
        language=data.get(CONF_LANGUAGE) or "",
        language_name="",
        language_english_name="",
        license_url=data.get(CONF_LICENSE_URL),
        books=0,
        verses=0,
    )


@dataclass(frozen=True, slots=True)
class VerseOfTheDay:
    """Today's verse, ready to display."""

    daily: DailyVerse
    passage: Passage
    translation: Translation
    fallback: bool

    @property
    def date(self) -> date:
        """The DailyVerses.net date of the verse."""
        return self.daily.date


class BibleCoordinator(DataUpdateCoordinator[VerseOfTheDay]):
    """Fetches the verse when the local date changes and serves it from memory otherwise."""

    config_entry: BibleConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: BibleConfigEntry, client: BibleClient
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
            always_update=False,
        )
        self.client = client
        self.translation = translation_from(dict(entry.data))
        self._book_names: dict[str, dict[str, str]] = {}

    async def _names(self, translation: str) -> dict[str, str]:
        if translation not in self._book_names:
            self._book_names[translation] = await self.client.get_book_names(
                translation
            )
        return self._book_names[translation]

    async def _async_update_data(self) -> VerseOfTheDay:
        # DailyVerses.net follows European time, so its date can be a little behind
        # or ahead of the local one; ask again only once the local date passes it.
        today = dt_util.now().date()
        if self.data is not None and self.data.date >= today:
            return self.data
        try:
            daily = await self.client.get_daily_verse()
            if self.data is not None and self.data.daily == daily:
                return self.data
            try:
                passage = await self.client.get_passage(
                    self.translation, daily, await self._names(self.translation.id)
                )
                translation, fallback = self.translation, False
            except BibleNotFoundError:
                translation = translation_from(FALLBACK_TRANSLATION)
                _LOGGER.info(
                    "%s is not in %s; showing it in %s",
                    daily.reference,
                    self.translation.id,
                    translation.id,
                )
                passage = await self.client.get_passage(
                    translation, daily, await self._names(translation.id)
                )
                fallback = True
        except BibleError as err:
            raise UpdateFailed(str(err)) from err
        return VerseOfTheDay(daily, passage, translation, fallback)
