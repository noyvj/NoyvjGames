"""Tests for kit.parse_line()."""

import kit


def test_plain_text_returns_none_condition():
    cond, text = kit.parse_line("Hello, Ines.")
    assert cond is None
    assert text == "Hello, Ines."


def test_flagged_text_parses_condition_and_body():
    cond, text = kit.parse_line("?bit|Thanks for the battery.")
    assert cond == {"all": ["bit"], "none": [], "min": {}, "max": {}}
    assert text == "Thanks for the battery."


def test_empty_body_after_pipe_returns_empty_string():
    cond, text = kit.parse_line("?bit|")
    assert cond == {"all": ["bit"], "none": [], "min": {}, "max": {}}
    assert text == ""
