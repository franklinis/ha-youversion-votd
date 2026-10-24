"""Config flow for Bible Verse of the Day: pick a language, then a translation."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    SOURCE_RECONFIGURE,
    ConfigFlow,
    ConfigFlowResult,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .api import BibleClient, BibleError, Translation
from .const import (
    CONF_LANGUAGE,
    CONF_LICENSE_URL,
    CONF_SHORT_NAME,
    CONF_TRANSLATION,
    CONF_TRANSLATION_NAME,
    DOMAIN,
    HA_LANGUAGES,
)
from .translations_list import default_translation, for_language, languages

_LOGGER = logging.getLogger(__name__)


def _dropdown(options: dict[str, str]) -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(
            options=[SelectOptionDict(value=k, label=v) for k, v in options.items()],
            mode=SelectSelectorMode.DROPDOWN,
            sort=False,
        )
    )


class BibleConfigFlow(ConfigFlow, domain=DOMAIN):
    """No account needed: choose the language and Bible translation to read in."""

    VERSION = 2

    def __init__(self) -> None:
        """Initialize the flow."""
        self._translations: list[Translation] = []
        self._language = ""

    async def _load(self) -> dict[str, str] | None:
        """Fetch the list of translations once; returns form errors if that fails."""
        if self._translations:
            return None
        try:
            self._translations = await BibleClient(
                async_get_clientsession(self.hass)
            ).get_translations()
        except BibleError:
            return {"base": "cannot_connect"}
        except Exception:
            _LOGGER.exception("Unexpected error listing translations")
            return {"base": "unknown"}
        return None

    def _current(self, key: str) -> Any:
        if self.source == SOURCE_RECONFIGURE:
            return self._get_reconfigure_entry().data.get(key)
        return None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose the language."""
        if errors := await self._load():
            return self.async_show_form(
                step_id="user", data_schema=vol.Schema({}), errors=errors
            )
        options = languages(self._translations)
        if user_input is not None:
            self._language = user_input[CONF_LANGUAGE]
            return await self.async_step_translation()

        suggested = self._current(CONF_LANGUAGE) or HA_LANGUAGES.get(
            self.hass.config.language[:2].lower(), "eng"
        )
        if suggested not in options:
            suggested = "eng"
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required(CONF_LANGUAGE, default=suggested): _dropdown(options)}
            ),
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the language or translation later."""
        return await self.async_step_user(user_input)

    async def async_step_translation(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose the translation in that language."""
        choices = {t.id: t for t in for_language(self._translations, self._language)}
        if user_input is not None:
            translation = choices[user_input[CONF_TRANSLATION]]
            data = {
                CONF_TRANSLATION: translation.id,
                CONF_TRANSLATION_NAME: translation.name,
                CONF_SHORT_NAME: translation.short_name,
                CONF_LANGUAGE: translation.language,
                CONF_LICENSE_URL: translation.license_url,
            }
            title = f"Bible {translation.short_name}"
            if self.source == SOURCE_RECONFIGURE:
                entry = self._get_reconfigure_entry()
                if translation.id != entry.unique_id and any(
                    other.unique_id == translation.id
                    for other in self._async_current_entries(include_ignore=False)
                ):
                    return self.async_abort(reason="already_configured")
                return self.async_update_reload_and_abort(
                    entry, unique_id=translation.id, title=title, data=data
                )
            await self.async_set_unique_id(translation.id)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=title, data=data)

        current = self._current(CONF_TRANSLATION)
        default = (
            current
            if current in choices
            else getattr(
                default_translation(self._translations, self._language), "id", None
            )
        )
        return self.async_show_form(
            step_id="translation",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_TRANSLATION, default=default): _dropdown(
                        {key: t.label for key, t in choices.items()}
                    )
                }
            ),
        )
