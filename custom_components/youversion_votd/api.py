"""Async clients for the two free, key-less services the integration uses.

- DailyVerses.net picks the verse of the day. Its official website widget
  (https://dailyverses.net/get/verse.js) gives today's reference.
- The Free Use Bible API (https://bible.helloao.org) serves the text in about
  1,250 public-domain and openly licensed translations, in about 1,000 languages.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date
import html
import re
from typing import Any

import aiohttp

from .const import API_TIMEOUT, BIBLE_API_URL, DAILYVERSES_WIDGET_URL

# USFM book ids, keyed by the English names DailyVerses.net uses.
BOOKS: dict[str, str] = {
    "Genesis": "GEN", "Exodus": "EXO", "Leviticus": "LEV", "Numbers": "NUM",
    "Deuteronomy": "DEU", "Joshua": "JOS", "Judges": "JDG", "Ruth": "RUT",
    "1 Samuel": "1SA", "2 Samuel": "2SA", "1 Kings": "1KI", "2 Kings": "2KI",
    "1 Chronicles": "1CH", "2 Chronicles": "2CH", "Ezra": "EZR", "Nehemiah": "NEH",
    "Esther": "EST", "Job": "JOB", "Psalm": "PSA", "Psalms": "PSA", "Proverbs": "PRO",
    "Ecclesiastes": "ECC", "Song of Solomon": "SNG", "Song of Songs": "SNG",
    "Isaiah": "ISA", "Jeremiah": "JER", "Lamentations": "LAM", "Ezekiel": "EZK",
    "Daniel": "DAN", "Hosea": "HOS", "Joel": "JOL", "Amos": "AMO", "Obadiah": "OBA",
    "Jonah": "JON", "Micah": "MIC", "Nahum": "NAM", "Habakkuk": "HAB",
    "Zephaniah": "ZEP", "Haggai": "HAG", "Zechariah": "ZEC", "Malachi": "MAL",
    "Matthew": "MAT", "Mark": "MRK", "Luke": "LUK", "John": "JHN", "Acts": "ACT",
    "Romans": "ROM", "1 Corinthians": "1CO", "2 Corinthians": "2CO",
    "Galatians": "GAL", "Ephesians": "EPH", "Philippians": "PHP", "Colossians": "COL",
    "1 Thessalonians": "1TH", "2 Thessalonians": "2TH", "1 Timothy": "1TI",
    "2 Timothy": "2TI", "Titus": "TIT", "Philemon": "PHM", "Hebrews": "HEB",
    "James": "JAS", "1 Peter": "1PE", "2 Peter": "2PE", "1 John": "1JN",
    "2 John": "2JN", "3 John": "3JN", "Jude": "JUD", "Revelation": "REV",
}  # fmt: skip
_BOOKS_FOLDED = {name.casefold(): usfm for name, usfm in BOOKS.items()}

_REFERENCE = re.compile(
    r"^(?P<book>.+?)\s+(?P<chapter>\d+):(?P<first>\d+)(?:\s*[-\u2013]\s*(?P<last>\d+))?$"
)
_WIDGET_TEXT = re.compile(r"innerHTML\s*=\s*'(?P<html>.*)'", re.S)
_WIDGET_LINK = re.compile(
    r'<a href="(?P<url>https://dailyverses\.net/(?P<y>\d{4})/(?P<m>\d{1,2})/(?P<d>\d{1,2})[^"]*)"[^>]*>(?P<ref>[^<]+)</a>'
)
_JS_UNICODE = re.compile(r"\\u([0-9a-fA-F]{4})")
_WHITESPACE = re.compile(r"\s+")

# Languages that write "Psalm 51,10" rather than "Psalm 51:10".
COMMA_LANGUAGES = {"deu", "nld", "dan", "nob", "swe", "fin", "pol", "ces", "hun"}


class BibleError(Exception):
    """A service returned something unexpected."""


class BibleConnectionError(BibleError):
    """A service could not be reached."""


class BibleNotFoundError(BibleError):
    """The translation, book or verse does not exist."""


@dataclass(frozen=True, slots=True)
class Translation:
    """A Bible translation from the Free Use Bible API."""

    id: str
    name: str
    short_name: str
    language: str
    language_name: str
    language_english_name: str
    license_url: str | None
    books: int
    verses: int

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Translation:
        """Build from an available_translations.json item."""
        return cls(
            id=str(data["id"]),
            name=str(data.get("name") or data.get("englishName") or data["id"]),
            short_name=str(data.get("shortName") or data["id"]),
            language=str(data.get("language") or ""),
            language_name=str(data.get("languageName") or ""),
            language_english_name=str(
                data.get("languageEnglishName") or data.get("language") or ""
            ),
            license_url=data.get("licenseUrl") or None,
            books=int(data.get("numberOfBooks") or 0),
            verses=int(data.get("totalNumberOfVerses") or 0),
        )

    @property
    def label(self) -> str:
        """e.g. "Berean Standard Bible (BSB)"."""
        if self.short_name and self.short_name not in self.name:
            return f"{self.name} ({self.short_name})"
        return self.name


@dataclass(frozen=True, slots=True)
class DailyVerse:
    """Today's pick from DailyVerses.net, in English verse numbering."""

    date: date
    reference: str
    book: str
    chapter: int
    first: int
    last: int
    url: str

    @property
    def passage_id(self) -> str:
        """USFM id, e.g. "PHP.4.6-7"."""
        return f"{self.book}.{self.chapter}.{_verses(self)}"


@dataclass(frozen=True, slots=True)
class Passage:
    """Text of a passage in one translation, with the reference in that language."""

    reference: str
    text: str


def _book_name(name: str) -> str:
    """Some translations write book names in capitals ("ISAÍAS"); show "Isaías"."""
    return name.title() if name.isupper() else name


def _verses(verse: DailyVerse) -> str:
    return (
        str(verse.first) if verse.first == verse.last else f"{verse.first}-{verse.last}"
    )


def parse_reference(reference: str) -> tuple[str, int, int, int]:
    """Split "1 Corinthians 13:4-7" into ("1CO", 13, 4, 7)."""
    match = _REFERENCE.match(reference.strip())
    if not match:
        raise BibleError(f"Unexpected reference {reference!r}")
    book = _BOOKS_FOLDED.get(match["book"].casefold())
    if book is None:
        raise BibleError(f"Unknown book in {reference!r}")
    first = int(match["first"])
    return book, int(match["chapter"]), first, int(match["last"] or first)


def parse_widget(script: str) -> DailyVerse:
    """Read today's reference from the DailyVerses.net widget script."""
    found = _WIDGET_TEXT.search(script)
    if not found:
        raise BibleError("DailyVerses.net widget changed: no verse found")
    markup = _JS_UNICODE.sub(lambda m: chr(int(m[1], 16)), found["html"])
    markup = markup.replace('\\"', '"').replace("\\'", "'").replace("\\/", "/")
    link = _WIDGET_LINK.search(markup)
    if not link:
        raise BibleError("DailyVerses.net widget changed: no reference found")
    reference = html.unescape(link["ref"]).strip()
    book, chapter, first, last = parse_reference(reference)
    return DailyVerse(
        date=date(int(link["y"]), int(link["m"]), int(link["d"])),
        reference=reference,
        book=book,
        chapter=chapter,
        first=first,
        last=last,
        url=link["url"],
    )


def _flatten(content: list[Any]) -> str:
    parts: list[str] = []
    for item in content:
        if isinstance(item, str):
            parts.append(item)
        elif isinstance(item, dict) and isinstance(item.get("text"), str):
            parts.append(item["text"])
    return _WHITESPACE.sub(" ", " ".join(parts)).strip()


def verse_text(chapter: dict[str, Any], first: int, last: int) -> str:
    """The plain text of verses first..last from a chapter document."""
    verses = {
        item.get("number"): _flatten(item.get("content") or [])
        for item in (chapter.get("chapter") or {}).get("content") or []
        if isinstance(item, dict) and item.get("type") == "verse"
    }
    missing = [n for n in range(first, last + 1) if not verses.get(n)]
    if missing:
        raise BibleNotFoundError(f"Verse {missing[0]} is not in this translation")
    return " ".join(verses[n] for n in range(first, last + 1))


def local_reference(book_name: str, verse: DailyVerse, language: str) -> str:
    """ "Psalm 51:10" with the translation's own book name and number style."""
    separator = "," if language in COMMA_LANGUAGES else ":"
    return f"{book_name} {verse.chapter}{separator}{_verses(verse)}"


class BibleClient:
    """Fetches the day's pick and its text; no account or key needed."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        bible_url: str = BIBLE_API_URL,
        widget_url: str = DAILYVERSES_WIDGET_URL,
    ) -> None:
        """Initialize the client."""
        self._session = session
        self._bible_url = bible_url.rstrip("/")
        self._widget_url = widget_url

    async def _request(self, url: str, *, as_json: bool) -> Any:
        try:
            async with asyncio.timeout(API_TIMEOUT), self._session.get(url) as resp:
                if resp.status == 404:
                    raise BibleNotFoundError(f"{url} was not found")
                if resp.status >= 400:
                    raise BibleError(f"{url} returned HTTP {resp.status}")
                if as_json:
                    return await resp.json(content_type=None)
                return await resp.text()
        except TimeoutError as err:
            raise BibleConnectionError(f"Timed out requesting {url}") from err
        except aiohttp.ClientError as err:
            raise BibleConnectionError(f"Error requesting {url}: {err}") from err
        except ValueError as err:
            raise BibleError(f"{url} returned invalid JSON") from err

    async def get_daily_verse(self) -> DailyVerse:
        """Today's verse reference from DailyVerses.net."""
        return parse_widget(await self._request(self._widget_url, as_json=False))

    async def get_translations(self) -> list[Translation]:
        """Every translation the Free Use Bible API offers."""
        data = await self._request(
            f"{self._bible_url}/available_translations.json", as_json=True
        )
        try:
            return [Translation.from_api(item) for item in data["translations"]]
        except (KeyError, TypeError) as err:
            raise BibleError("Unexpected list of translations") from err

    async def get_book_names(self, translation: str) -> dict[str, str]:
        """USFM id -> the book's name in the translation's language."""
        data = await self._request(
            f"{self._bible_url}/{translation}/books.json", as_json=True
        )
        try:
            return {
                book["id"]: _book_name(book.get("name") or book["id"])
                for book in data["books"]
            }
        except (KeyError, TypeError) as err:
            raise BibleError("Unexpected list of books") from err

    async def get_passage(
        self, translation: Translation, verse: DailyVerse, book_names: dict[str, str]
    ) -> Passage:
        """The verse in a translation; BibleNotFoundError if it lacks that book or verse."""
        if verse.book not in book_names:
            raise BibleNotFoundError(f"{translation.id} has no {verse.book}")
        chapter = await self._request(
            f"{self._bible_url}/{translation.id}/{verse.book}/{verse.chapter}.json",
            as_json=True,
        )
        return Passage(
            reference=local_reference(
                book_names[verse.book], verse, translation.language
            ),
            text=verse_text(chapter, verse.first, verse.last),
        )
