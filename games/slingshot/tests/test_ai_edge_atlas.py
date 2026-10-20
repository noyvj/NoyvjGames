"""Edge-case tests for atlas.py: label, order, and card."""

import pytest

import atlas
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent


def test_label_returns_correct_name_for_known_dest():
    for dest in atlas.DESTS:
        assert isinstance(atlas.label(dest), str)
        assert atlas.label(dest) == atlas.DESTS[dest][0]


def test_label_raises_keyerror_for_unknown_dest():
    with pytest.raises(KeyError):
        atlas.label("nonexistent_body")


def test_label_handles_empty_string():
    with pytest.raises(KeyError):
        atlas.label("")


def test_order_returns_all_destinations_sorted_by_priority():
    ordered = atlas.order()
    assert len(ordered) == len(atlas.DESTS)
    priorities = [atlas.DESTS[d][3] for d in ordered]
    assert priorities == sorted(priorities)


def test_card_for_moon_returns_expected_lines_and_source():
    lines, source = atlas.card("moon")
    assert len(lines) > 0
    assert any("Size" in line[0] for line in lines)
    assert "JPL" in source


def test_card_for_planet_returns_expected_lines_and_source():
    lines, source = atlas.card("venus")
    assert len(lines) > 0
    assert any("Size" in line[0] for line in lines)
    assert "JPL" in source


def test_card_for_unknown_dest_falls_back_to_sunward():
    lines, source = atlas.card("unknown_dest")
    assert len(lines) == 1
    assert lines[0][0] == "Sunward"
    assert "JPL" in source


def test_card_for_empty_string_falls_back_to_sunward():
    lines, source = atlas.card("")
    assert len(lines) == 1
    assert lines[0][0] == "Sunward"
