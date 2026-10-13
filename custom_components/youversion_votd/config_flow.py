"""Config flow for YouVersion Verse of the Day."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import (
    Bible,
    YouVersionAuthError,
    YouVersionClient,
    YouVersionError,
    YouVersionNotFoundError,
)
from .const import (
    CONF_APP_KEY,
    CONF_BIBLE_ID,
    CONF_LANGUAGE,
    DEFAULT_BIBLE_ID,
    DEFAULT_LANGUAGE,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

PLATFORM_URL = "https://platform.youversion.com"

APP_KEY_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_APP_KEY): APP_KEY_SELECTOR,
        vol.Required(CONF_LANGUAGE): str,
    }
)
STEP_REAUTH_SCHEMA = vol.Schema({vol.Required(CONF_APP_KEY): APP_KEY_SELECTOR})


class YouVersionConfigFlow(ConfigFlow, domain=DOMAIN):
    """Ask for an app key, then let the user pick a Bible version it can read."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the flow."""
        self._app_key = ""
        self._language = DEFAULT_LANGUAGE
        self._bibles: dict[str, Bible] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect and validate the app key."""
        errors: dict[str, str] = {}
        if user_input is not None:
            app_key = user_input[CONF_APP_KEY].strip()
            language = user_input[CONF_LANGUAGE].strip()
            client = YouVersionClient(async_get_clientsession(self.hass), app_key)
            try:
                bibles = await client.get_bibles(language)
            except YouVersionAuthError:
                errors["base"] = "invalid_auth"
            except YouVersionError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error listing Bibles")
                errors["base"] = "unknown"
            else:
                if not bibles:
                    errors[CONF_LANGUAGE] = "no_bibles"
                else:
                    self._app_key = app_key
                    self._language = language
                    self._bibles = {str(bible.id): bible for bible in bibles}
                    return await self.async_step_bible()

        suggested = user_input or {CONF_LANGUAGE: self.hass.config.language}
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                STEP_USER_SCHEMA, suggested
            ),
            errors=errors,
            description_placeholders={"platform_url": PLATFORM_URL},
        )

    async def async_step_bible(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pick the Bible version to read the verse in."""
        if user_input is not None:
            bible = self._bibles[user_input[CONF_BIBLE_ID]]
            await self.async_set_unique_id(str(bible.id))
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"YouVersion {bible.abbreviation}",
                data={
                    CONF_APP_KEY: self._app_key,
                    CONF_BIBLE_ID: bible.id,
                    CONF_LANGUAGE: self._language,
                },
            )

        options = [
            SelectOptionDict(value=key, label=f"{bible.title} ({bible.abbreviation})")
            for key, bible in sorted(
                self._bibles.items(), key=lambda item: item[1].title.casefold()
            )
        ]
        default = (
            str(DEFAULT_BIBLE_ID)
            if str(DEFAULT_BIBLE_ID) in self._bibles
            else options[0]["value"]
        )
        return self.async_show_form(
            step_id="bible",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_BIBLE_ID, default=default): SelectSelector(
                        SelectSelectorConfig(
                            options=options, mode=SelectSelectorMode.DROPDOWN
                        )
                    )
                }
            ),
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start re-authentication after YouVersion rejected the app key."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for a new app key and check it can still read the configured Bible."""
        errors: dict[str, str] = {}
        if user_input is not None:
            entry = self._get_reauth_entry()
            app_key = user_input[CONF_APP_KEY].strip()
            client = YouVersionClient(async_get_clientsession(self.hass), app_key)
            try:
                await client.get_bible(entry.data[CONF_BIBLE_ID])
            except YouVersionAuthError:
                errors["base"] = "invalid_auth"
            except YouVersionNotFoundError:
                errors["base"] = "bible_unavailable"
            except YouVersionError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error validating app key")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_APP_KEY: app_key}
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_REAUTH_SCHEMA,
            errors=errors,
            description_placeholders={"platform_url": PLATFORM_URL},
        )
