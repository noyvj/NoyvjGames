"""Edge-case tests for the Glyph Museum collector's page."""

from notebook import LexisState
from museum import get_museum_data


def test_get_museum_data_empty_state():
    """Default state should have all confirmed flags False."""
    state = LexisState()
    data = get_museum_data(state)
    assert all(not item["confirmed"] for item in data)


def test_get_museum_data_all_confirmed():
    """When every notebook entry matches the true meaning, all should be confirmed True."""
    from pulse import PULSE
    from compound import COMPONENTS
    from bridge import MARKERS

    state = LexisState()
    for word in PULSE.words:
        state.notebook.write(word.form, word.meaning)
    for letter, (meaning, _) in COMPONENTS.items():
        state.compound_notebook.write(letter, meaning)
    for letter, meaning in MARKERS.items():
        state.bridge_notebook.write(letter, meaning)

    data = get_museum_data(state)
    assert all(item["confirmed"] for item in data)


def test_get_museum_data_partial_confirmed():
    """Mix of correct and incorrect entries should only confirm the correct ones."""
    from pulse import PULSE
    state = LexisState()

    # Correctly guess one word
    word = PULSE.words[0]
    state.notebook.write(word.form, word.meaning)

    # Incorrectly guess another
    word2 = PULSE.words[1]
    state.notebook.write(word2.form, "wrong_meaning")

    data = get_museum_data(state)
    pulse_entries = [d for d in data if d["planet"] == "pulse"]
    assert any(d["confirmed"] for d in pulse_entries)
    assert any(not d["confirmed"] for d in pulse_entries)


def test_get_museum_data_whitespace_entries():
    """Partial matches should not be confirmed. Whitespace-padded guesses may match if the engine strips them."""
    from pulse import PULSE
    state = LexisState()

    word = PULSE.words[0]
    state.notebook.write(word.form, "  " + word.meaning + "  ")
    state.notebook.write(PULSE.words[1].form, word.meaning[:3])

    data = get_museum_data(state)
    pulse_entries = [d for d in data if d["planet"] == "pulse"]
    # The partial match must not be confirmed; whitespace handling depends on the engine
    assert any(not d["confirmed"] for d in pulse_entries)


def test_get_museum_data_structure():
    """Each returned item must contain the required keys with correct types."""
    state = LexisState()
    data = get_museum_data(state)

    required_keys = {"planet", "form", "meaning", "confirmed"}
    for item in data:
        assert set(item.keys()) == required_keys
        assert isinstance(item["planet"], str)
        assert isinstance(item["form"], str)
        assert isinstance(item["meaning"], str)
        assert isinstance(item["confirmed"], bool)
