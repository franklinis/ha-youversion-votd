"""Constants for the Bible Verse of the Day integration.

The domain keeps its original name (youversion_votd) so existing installs keep
working; the integration no longer uses YouVersion.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "youversion_votd"

CONF_LANGUAGE: Final = "language"
CONF_TRANSLATION: Final = "translation"
CONF_TRANSLATION_NAME: Final = "translation_name"
CONF_SHORT_NAME: Final = "short_name"
CONF_LICENSE_URL: Final = "license_url"

DAILYVERSES_WIDGET_URL: Final = "https://dailyverses.net/get/verse.js"
BIBLE_API_URL: Final = "https://bible.helloao.org/api"
API_TIMEOUT: Final = 20

# Used when the chosen translation lacks the day's book (e.g. a New Testament only translation).
FALLBACK_TRANSLATION: Final = {
    CONF_TRANSLATION: "BSB",
    CONF_TRANSLATION_NAME: "Berean Standard Bible",
    CONF_SHORT_NAME: "BSB",
    CONF_LANGUAGE: "eng",
    CONF_LICENSE_URL: "https://berean.bible/",
}

# Preferred translation for a language when several are available.
PREFERRED_TRANSLATIONS: Final = {"eng": "BSB", "deu": "deu_l12", "tam": "tam_irv"}

# Home Assistant language (ISO 639-1) to the API's ISO 639-3 codes, for the default choice.
HA_LANGUAGES: Final = {
    "af": "afr", "ar": "arb", "bg": "bul", "bn": "ben", "cs": "ces", "da": "dan",
    "de": "deu", "el": "ell", "en": "eng", "es": "spa", "et": "est", "fi": "fin",
    "fr": "fra", "gu": "guj", "he": "heb", "hi": "hin", "hr": "hrv", "hu": "hun",
    "id": "ind", "it": "ita", "ja": "jpn", "kn": "kan", "ko": "kor", "lt": "lit",
    "lv": "lvs", "ml": "mal", "mr": "mar", "nb": "nob", "nl": "nld", "pa": "pan",
    "pl": "pol", "pt": "por", "ro": "ron", "ru": "rus", "sk": "slk", "sl": "slv",
    "sr": "srp", "sv": "swe", "sw": "swh", "ta": "tam", "te": "tel", "th": "tha",
    "tl": "tgl", "tr": "tur", "uk": "ukr", "ur": "urd", "vi": "vie", "zh": "cmn",
}  # fmt: skip

# The verse only changes once a day; this interval is a retry backstop.
UPDATE_INTERVAL: Final = timedelta(hours=1)

ATTR_TEXT: Final = "text"
ATTR_REFERENCE: Final = "reference"
ATTR_REFERENCE_EN: Final = "reference_en"
ATTR_PASSAGE_ID: Final = "passage_id"
ATTR_TRANSLATION: Final = "translation"
ATTR_TRANSLATION_NAME: Final = "translation_name"
ATTR_LANGUAGE: Final = "language"
ATTR_LICENSE: Final = "license"
ATTR_FALLBACK: Final = "fallback"
ATTR_DATE: Final = "date"
ATTR_URL: Final = "url"
