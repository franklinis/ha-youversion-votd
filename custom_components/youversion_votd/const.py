"""Constants for the YouVersion Verse of the Day integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "youversion_votd"

CONF_APP_KEY: Final = "app_key"
CONF_BIBLE_ID: Final = "bible_id"
CONF_LANGUAGE: Final = "language"

# Berean Standard Bible: the license-free default used by YouVersion's own SDKs.
DEFAULT_BIBLE_ID: Final = 3034
DEFAULT_LANGUAGE: Final = "en"

API_BASE_URL: Final = "https://api.youversion.com"
API_TIMEOUT: Final = 15

# The verse only changes at midnight; this interval is just a retry backstop.
# Updates within the same day are served from memory without calling the API.
UPDATE_INTERVAL: Final = timedelta(hours=1)

ATTR_TEXT: Final = "text"
ATTR_REFERENCE: Final = "reference"
ATTR_PASSAGE_ID: Final = "passage_id"
ATTR_BIBLE_ID: Final = "bible_id"
ATTR_VERSION: Final = "version"
ATTR_VERSION_NAME: Final = "version_name"
ATTR_COPYRIGHT: Final = "copyright"
ATTR_DAY_OF_YEAR: Final = "day_of_year"
ATTR_DATE: Final = "date"
ATTR_URL: Final = "url"
