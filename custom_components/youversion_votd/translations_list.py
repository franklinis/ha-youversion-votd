"""Choosing languages and translations from the Free Use Bible API's list."""

from __future__ import annotations

from .api import Translation
from .const import PREFERRED_TRANSLATIONS


def languages(translations: list[Translation]) -> dict[str, str]:
    """ISO 639-3 code -> "Tamil (தமிழ்)", sorted by English name."""
    names: dict[str, str] = {}
    for translation in translations:
        english = translation.language_english_name or translation.language
        native = translation.language_name
        names.setdefault(
            translation.language,
            f"{english} ({native})" if native and native != english else english,
        )
    return dict(sorted(names.items(), key=lambda item: item[1].casefold()))


def for_language(translations: list[Translation], language: str) -> list[Translation]:
    """A language's translations, complete Bibles first."""
    return sorted(
        (t for t in translations if t.language == language),
        key=lambda t: (-t.books, -t.verses, t.name.casefold()),
    )


def default_translation(
    translations: list[Translation], language: str
) -> Translation | None:
    """The translation to suggest for a language."""
    choices = for_language(translations, language)
    preferred = PREFERRED_TRANSLATIONS.get(language)
    return next(
        (t for t in choices if t.id == preferred), choices[0] if choices else None
    )
