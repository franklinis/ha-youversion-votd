"""Tests for parsing DailyVerses.net and the Free Use Bible API (no network)."""

from __future__ import annotations

from datetime import date

import pytest

from custom_components.youversion_votd.api import (
    BibleError,
    BibleNotFoundError,
    Translation,
    parse_reference,
    parse_widget,
    verse_text,
)
from custom_components.youversion_votd.translations_list import (
    default_translation,
    for_language,
    languages,
)

from .conftest import BSB_PHP_4, TRANSLATIONS, WIDGET


def test_parse_widget() -> None:
    verse = parse_widget(WIDGET)
    assert verse.date == date(2026, 10, 13)
    assert verse.reference == "Philippians 4:6-7"
    assert verse.passage_id == "PHP.4.6-7"
    assert verse.url == "https://dailyverses.net/2026/10/13"


def test_parse_widget_layout_change() -> None:
    with pytest.raises(BibleError, match="no verse"):
        parse_widget("document.write('hello')")
    with pytest.raises(BibleError, match="no reference"):
        parse_widget("x.innerHTML = '<div>text</div>';")


@pytest.mark.parametrize(
    ("reference", "expected"),
    [
        ("John 3:16", ("JHN", 3, 16, 16)),
        ("Psalm 23:1-2", ("PSA", 23, 1, 2)),
        ("1 Corinthians 13:4\u20137", ("1CO", 13, 4, 7)),
        ("Song of Songs 8:7", ("SNG", 8, 7, 7)),
    ],
)
def test_parse_reference(reference: str, expected: tuple) -> None:
    assert parse_reference(reference) == expected


def test_parse_reference_rejects_unknown_books() -> None:
    with pytest.raises(BibleError, match="Unknown book"):
        parse_reference("Hezekiah 1:1")
    with pytest.raises(BibleError, match="Unexpected"):
        parse_reference("John 3")


def test_verse_text_skips_notes_and_joins_lines() -> None:
    assert verse_text(BSB_PHP_4, 6, 7) == (
        "Be anxious for nothing, but in everything, by prayer and petition, with "
        "thanksgiving, present your requests to God. And the peace of God, will guard your hearts."
    )
    with pytest.raises(BibleNotFoundError, match="Verse 8"):
        verse_text(BSB_PHP_4, 7, 8)


def test_choosing_languages_and_translations() -> None:
    translations = [Translation.from_api(t) for t in TRANSLATIONS["translations"]]
    names = languages(translations)
    assert list(names) == ["eng", "xyz", "deu", "tam"]
    assert names["tam"] == "Tamil (தமிழ்)" and names["eng"] == "English"
    assert [t.id for t in for_language(translations, "eng")] == ["BSB", "ENGWEBP"]
    assert default_translation(translations, "deu").id == "deu_l12"
    assert default_translation(translations, "none") is None
    assert translations[0].label == "Berean Standard Bible (BSB)"


def test_capitalised_book_names_are_softened() -> None:
    from custom_components.youversion_votd.api import _book_name

    assert _book_name("ISAÍAS") == "Isaías"
    assert _book_name("1 SAMUEL") == "1 Samuel"
    assert _book_name("ஏசாயா") == "ஏசாயா"
