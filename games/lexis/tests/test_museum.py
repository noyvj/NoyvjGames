"""Tests for the Glyph Museum collector's page."""

from museum import get_museum_data
from notebook import LexisState


def test_museum_empty_state():
    state = LexisState()
    data = get_museum_data(state)
    assert len(data) == 13  # 5 pulse + 5 compound + 3 bridge
    for item in data:
        assert "planet" in item
        assert "form" in item
        assert "meaning" in item
        assert "confirmed" in item
        assert item["confirmed"] is False


def test_museum_confirmed_pulse():
    from pulse import PULSE
    state = LexisState()
    word = PULSE.words[0]
    state.notebook.write(word.form, word.meaning)

    data = get_museum_data(state)
    found = [d for d in data if d["form"] == word.form][0]
    assert found["confirmed"] is True


def test_museum_confirmed_compound():
    from compound import COMPONENTS
    state = LexisState()
    letter = list(COMPONENTS.keys())[0]
    state.compound_notebook.write(letter, COMPONENTS[letter][0])

    data = get_museum_data(state)
    found = [d for d in data if d["form"] == letter][0]
    assert found["confirmed"] is True


def test_museum_confirmed_bridge():
    from bridge import MARKERS
    state = LexisState()
    letter = list(MARKERS.keys())[0]
    state.bridge_notebook.write(letter, MARKERS[letter])

    data = get_museum_data(state)
    found = [d for d in data if d["form"] == letter][0]
    assert found["confirmed"] is True
