"""Focused tests for text-to-speech chunking.

Run from the py-server directory:

    python -m pytest tests/test_chunking.py
"""

from pipeline.chunking import HARD_FLUSH_CHARS, chunk_text, render_for_speech


def chunks(*pieces):
    return list(chunk_text(pieces))


def test_splits_on_sentence_boundaries():
    assert chunks("Hello there. ", "How are you? ") == ["Hello there.", "How are you?"]


def test_punctuation_split_across_tokens():
    # "." and the following space arrive in separate stream events.
    assert chunks("Hello", ".", " ", "World.") == ["Hello.", "World."]


def test_decimal_is_not_a_boundary():
    assert chunks("The value is 3", ".", "14159 and rising. ") == [
        "The value is 3.14159 and rising."
    ]


def test_abbreviation_is_not_a_boundary():
    assert chunks("Dr. Smith went home. Then he slept. ") == [
        "Dr. Smith went home.",
        "Then he slept.",
    ]


def test_initial_is_not_a_boundary():
    assert chunks("J. Smith arrived. ") == ["J. Smith arrived."]


def test_long_unpunctuated_output_is_bounded():
    text = " ".join(["word"] * 500)  # ~2500 chars, no punctuation
    produced = chunks(text)
    assert len(produced) > 1
    assert all(len(item) <= HARD_FLUSH_CHARS for item in produced)
    assert " ".join(produced).split() == text.split()


def test_empty_deltas_and_finish_events_are_skipped():
    assert list(chunk_text(["", None, "Hi. "])) == ["Hi."]


def test_post_cleaning_empty_chunks_are_skipped():
    # Formatting-only content must not produce empty synthesis input.
    assert chunks("**", "***", "Hello. ") == ["Hello."]


def test_emphasis_keeps_words():
    assert chunks("*smiles warmly* Hello. ") == ["smiles warmly Hello."]


def test_links_keep_text_and_bare_urls_are_dropped():
    assert render_for_speech("See [the docs](https://example.com) now.") == "See the docs now."
    assert render_for_speech("Visit https://example.com now.") == "Visit now."


def test_trailing_text_is_flushed():
    assert chunks("Just some text without punctuation") == ["Just some text without punctuation"]
