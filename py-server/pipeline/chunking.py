"""Streaming text chunking for speech synthesis.

Speech rendering policy
-----------------------
Chunks are emitted at real sentence boundaries so playback starts with low
latency while still sounding natural. The policy is explicit and chunk-local:

- A boundary is sentence-ending punctuation (``. ! ? …``) followed by
  whitespace, optionally with closing quotes/brackets. Periods inside
  decimals (``3.14``) or domains (``example.com``) are not boundaries because
  they are not followed by whitespace.
- Common abbreviations and initials (``Dr.``, ``e.g.``, ``J. Smith``) are not
  boundaries.
- To bound latency, a buffer without any boundary is flushed at a whitespace
  break once it exceeds ``HARD_FLUSH_CHARS``.
- Markdown formatting markers are removed but their words are kept, so
  nothing is dropped because a delimiter happened to fall in another chunk.
  Links keep their text; bare URLs are omitted.
- Empty deltas/finish events and chunks that become empty after rendering are
  skipped without producing empty synthesis input.
"""
from __future__ import annotations

import re
from typing import Iterable, Iterator

# Flush unpunctuated text at the last whitespace before this many characters.
HARD_FLUSH_CHARS = 400

_SENTENCE_BOUNDARY = re.compile(r"[.!?…]+[)\"'\]”’]*(?=\s)")
_WORD_BEFORE_PERIOD = re.compile(r"([A-Za-z]+(?:\.[A-Za-z]+)*)\.$")

_ABBREVIATIONS = {
    "mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st", "mt", "vs", "etc",
    "eg", "ie", "no", "vol", "fig", "approx", "dept", "est", "inc", "ltd",
    "co", "corp", "gov", "sen", "rep", "gen", "col", "capt", "lt", "sgt",
    "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "sept", "oct",
    "nov", "dec", "mon", "tue", "wed", "thu", "fri", "sat", "sun",
    "uk", "us", "am", "pm",
}

_MD_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_BARE_URL = re.compile(r"https?://\S+|www\.\S+")
_MD_MARKERS = re.compile(r"[*_~`#]+")
_WHITESPACE = re.compile(r"\s+")


def find_sentence_boundary(buffer: str) -> int | None:
    """Return the index just past the first real sentence boundary, if any."""
    for match in _SENTENCE_BOUNDARY.finditer(buffer):
        end = match.end()
        if match.group()[0] == "." and _is_abbreviation(buffer[:end]):
            continue
        return _skip_trailing_space(buffer, end)
    return None


def _is_abbreviation(prefix: str) -> bool:
    word_match = _WORD_BEFORE_PERIOD.search(prefix)
    if word_match is None:
        return False
    word = word_match.group(1)
    if word.replace(".", "").lower() in _ABBREVIATIONS:
        return True
    # A single-letter initial like "J." in "J. Smith" is not a boundary.
    return len(word) == 1 and word.isupper()


def _skip_trailing_space(buffer: str, index: int) -> int:
    while index < len(buffer) and buffer[index].isspace():
        index += 1
    return index


def render_for_speech(text: str) -> str:
    """Convert a text chunk into speakable text without dropping content."""
    text = _MD_LINK.sub(r"\1", text)
    text = _BARE_URL.sub("", text)
    text = _MD_MARKERS.sub("", text)
    return _WHITESPACE.sub(" ", text).strip()


def chunk_text(text_deltas: Iterable[str]) -> Iterator[str]:
    """Yield speakable chunks from a stream of LLM text deltas."""
    buffer = ""
    for content in text_deltas:
        if not content:
            continue
        buffer += content

        while True:
            boundary = find_sentence_boundary(buffer)
            if boundary is not None:
                spoken = render_for_speech(buffer[:boundary])
                buffer = buffer[boundary:]
                if spoken:
                    yield spoken
                continue

            if len(buffer) >= HARD_FLUSH_CHARS:
                cut = buffer.rfind(" ", 0, HARD_FLUSH_CHARS)
                cut = cut if cut > 0 else HARD_FLUSH_CHARS
                spoken = render_for_speech(buffer[:cut])
                buffer = buffer[cut:]
                if spoken:
                    yield spoken
                continue

            break

    final = render_for_speech(buffer)
    if final:
        yield final


if __name__ == "__main__":
    for item in chunk_text(["Hello, ", "world. ", "Dr. Smith ", "arrived at 3.14 p.m. today"]):
        print(repr(item))
