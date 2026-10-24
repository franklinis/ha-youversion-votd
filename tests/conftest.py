"""Fixtures for Bible Verse of the Day tests."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.youversion_votd.const import (
    BIBLE_API_URL,
    CONF_LANGUAGE,
    CONF_LICENSE_URL,
    CONF_SHORT_NAME,
    CONF_TRANSLATION,
    CONF_TRANSLATION_NAME,
    DAILYVERSES_WIDGET_URL,
    DOMAIN,
)

# Noon on 2026-10-13 in the test suite's US/Pacific time zone.
FROZEN_TIME = "2026-10-13T19:00:00+00:00"

WIDGET = (
    'document.getElementById("dailyVersesWrapper").innerHTML = \'\\u003cdiv class=\\"dailyVerses '
    'bibleText\\"\\u003eDo not be anxious about anything...\\u003c/div\\u003e\\u003cdiv '
    'class=\\"dailyVerses bibleVerse\\"\\u003e\\u003ca href=\\"https://dailyverses.net/2026/10/13\\" '
    'rel=\\"noopener\\" target=\\"_blank\\"\\u003ePhilippians 4:6-7\\u003c/a\\u003e\\u003c/div\\u003e\';'
)


def translation(
    id_: str,
    name: str,
    short: str,
    lang: str,
    english: str,
    native: str,
    books: int = 66,
) -> dict[str, Any]:
    return {
        "id": id_, "name": name, "englishName": name, "shortName": short, "language": lang,
        "languageName": native, "languageEnglishName": english, "licenseUrl": f"https://example.org/{id_}",
        "numberOfBooks": books, "totalNumberOfVerses": books * 470,
    }  # fmt: skip


TRANSLATIONS = {
    "translations": [
        translation("BSB", "Berean Standard Bible", "BSB", "eng", "English", "English"),
        translation(
            "ENGWEBP", "World English Bible", "WEB", "eng", "English", "English"
        ),
        translation("deu_l12", "Lutherbibel 1912", "L12", "deu", "German", "Deutsch"),
        translation("tam_irv", "Tamil IRV", "IRV", "tam", "Tamil", "தமிழ்"),
        translation(
            "xyz_nt",
            "Example New Testament",
            "ENT",
            "xyz",
            "Example",
            "Exampleish",
            books=27,
        ),
    ]
}


def books(names: dict[str, str]) -> dict[str, Any]:
    return {"books": [{"id": k, "name": v} for k, v in names.items()]}


def chapter(verses: dict[int, list[Any]]) -> dict[str, Any]:
    return {
        "chapter": {
            "number": 4,
            "content": [{"type": "heading", "content": ["Rejoice"]}]
            + [{"type": "verse", "number": n, "content": c} for n, c in verses.items()],
        }
    }


BSB_PHP_4 = chapter(
    {
        5: ["Let your gentleness be known."],
        6: [
            {"text": "Be anxious for nothing,", "poem": 1},
            {"noteId": 3},
            "but in everything, by prayer and petition, with thanksgiving, present your requests to God.",
        ],
        7: ["And the peace of God,", {"lineBreak": True}, "will guard your hearts."],
    }
)
DEU_PHP_4 = chapter({6: ["Sorget nichts!"], 7: ["Und der Friede Gottes ..."]})


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Load the integration from custom_components/."""


def entry_data(id_: str = "BSB") -> dict[str, Any]:
    item = next(t for t in TRANSLATIONS["translations"] if t["id"] == id_)
    return {
        CONF_TRANSLATION: id_,
        CONF_TRANSLATION_NAME: item["name"],
        CONF_SHORT_NAME: item["shortName"],
        CONF_LANGUAGE: item["language"],
        CONF_LICENSE_URL: item["licenseUrl"],
    }


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """A configured entry for the BSB."""
    return MockConfigEntry(
        domain=DOMAIN, title="Bible BSB", unique_id="BSB", version=2, data=entry_data()
    )


@pytest.fixture
def mock_api(aioclient_mock: AiohttpClientMocker) -> Generator[AiohttpClientMocker]:
    """Mock DailyVerses.net and the Free Use Bible API."""
    aioclient_mock.get(DAILYVERSES_WIDGET_URL, text=WIDGET)
    aioclient_mock.get(
        f"{BIBLE_API_URL}/available_translations.json", json=TRANSLATIONS
    )
    aioclient_mock.get(
        f"{BIBLE_API_URL}/BSB/books.json", json=books({"PHP": "Philippians"})
    )
    aioclient_mock.get(f"{BIBLE_API_URL}/BSB/PHP/4.json", json=BSB_PHP_4)
    aioclient_mock.get(
        f"{BIBLE_API_URL}/deu_l12/books.json", json=books({"PHP": "Philipper"})
    )
    aioclient_mock.get(f"{BIBLE_API_URL}/deu_l12/PHP/4.json", json=DEU_PHP_4)
    aioclient_mock.get(f"{BIBLE_API_URL}/xyz_nt/books.json", json=books({"MAT": "Mat"}))
    yield aioclient_mock
