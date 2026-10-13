"""Coordinator that fetches the YouVersion Verse of the Day once per day."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import Bible, YouVersionAuthError, YouVersionClient, YouVersionError
from .const import CONF_BIBLE_ID, DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

type YouVersionConfigEntry = ConfigEntry[YouVersionCoordinator]


@dataclass(frozen=True, slots=True)
class VerseOfTheDay:
    """Today's verse, ready to display."""

    date: date
    day_of_year: int
    passage_id: str
    reference: str
    text: str
    bible: Bible

    @property
    def url(self) -> str:
        """Link to the passage on bible.com."""
        return f"https://www.bible.com/bible/{self.bible.id}/{self.passage_id}"


class YouVersionCoordinator(DataUpdateCoordinator[VerseOfTheDay]):
    """Fetches the verse when the local date changes and serves it from memory otherwise."""

    config_entry: YouVersionConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: YouVersionConfigEntry,
        client: YouVersionClient,
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
        self.bible_id: int = entry.data[CONF_BIBLE_ID]
        self._bible: Bible | None = None

    async def _async_update_data(self) -> VerseOfTheDay:
        today = dt_util.now().date()
        if self.data is not None and self.data.date == today:
            return self.data

        # Same day numbering as YouVersion's SDKs: Jan 1 is day 1, in local time.
        day = today.timetuple().tm_yday
        try:
            passage_id = await self.client.get_verse_of_the_day(day)
            passage = await self.client.get_passage(self.bible_id, passage_id)
            if self._bible is None:
                self._bible = await self.client.get_bible(self.bible_id)
        except YouVersionAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except YouVersionError as err:
            raise UpdateFailed(str(err)) from err

        return VerseOfTheDay(
            date=today,
            day_of_year=day,
            passage_id=passage_id,
            reference=passage.reference,
            text=passage.text,
            bible=self._bible,
        )
