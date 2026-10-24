"""The Bible Verse of the Day integration."""

from __future__ import annotations

from datetime import datetime
import logging

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_change

from .api import BibleClient, BibleError
from .const import (
    CONF_LANGUAGE,
    CONF_LICENSE_URL,
    CONF_SHORT_NAME,
    CONF_TRANSLATION,
    CONF_TRANSLATION_NAME,
    FALLBACK_TRANSLATION,
    HA_LANGUAGES,
)
from .coordinator import BibleConfigEntry, BibleCoordinator
from .translations_list import default_translation

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: BibleConfigEntry) -> bool:
    """Set up Bible Verse of the Day from a config entry."""
    coordinator = BibleCoordinator(
        hass, entry, BibleClient(async_get_clientsession(hass))
    )
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    async def _refresh_after_midnight(_now: datetime) -> None:
        await coordinator.async_request_refresh()

    entry.async_on_unload(
        async_track_time_change(
            hass, _refresh_after_midnight, hour=0, minute=0, second=5
        )
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: BibleConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(hass: HomeAssistant, entry: BibleConfigEntry) -> bool:
    """Version 1 used YouVersion (app key and YouVersion Bible id); move to a free translation."""
    if entry.version > 2:
        return False
    if entry.version == 1:
        language = HA_LANGUAGES.get(
            str(entry.data.get(CONF_LANGUAGE, "en"))[:2].lower(), "eng"
        )
        chosen = dict(FALLBACK_TRANSLATION)
        try:
            translations = await BibleClient(
                async_get_clientsession(hass)
            ).get_translations()
        except BibleError:
            translations = []
        if translation := default_translation(translations, language):
            chosen = {
                CONF_TRANSLATION: translation.id,
                CONF_TRANSLATION_NAME: translation.name,
                CONF_SHORT_NAME: translation.short_name,
                CONF_LANGUAGE: translation.language,
                CONF_LICENSE_URL: translation.license_url,
            }
        hass.config_entries.async_update_entry(
            entry,
            data=chosen,
            title=f"Bible {chosen[CONF_SHORT_NAME]}",
            unique_id=chosen[CONF_TRANSLATION],
            version=2,
        )
        _LOGGER.info(
            "Moved from YouVersion to %s; choose another translation with Reconfigure",
            chosen[CONF_TRANSLATION],
        )
    return True
