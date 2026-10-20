"""Edge-case tests for notebook.py."""

from notebook import is_message, Notebook, LexisState


def test_is_message_empty_and_max_length():
    """is_message rejects empty strings, accepts length 1, and clamps at 60 characters."""
    assert is_message("") is False
    assert is_message("a") is True
    assert is_message("a" * 60) is True
    assert is_message("a" * 61) is False


def test_is_message_invalid_characters():
    """is_message rejects values containing newlines or punctuation."""
    assert is_message("hello\nworld") is False
    assert is_message("hello world!") is False
    assert is_message("hello world") is True


def test_notebook_write_empty_gloss_removes_entry():
    """Writing an empty or whitespace-only gloss removes the form from the notebook."""
    nb = Notebook()
    nb.write("lamp", "light")
    assert "lamp" in nb.entries

    nb.write("lamp", "")
    assert "lamp" not in nb.entries

    nb.write("lamp", "   ")
    assert "lamp" not in nb.entries


def test_notebook_confirm_empty_and_missing_forms():
    """confirm returns 0 for empty lists or forms that were never written."""
    nb = Notebook()
    assert nb.confirm([]) == 0
    assert nb.confirm(["nonexistent"]) == 0


def test_lexis_state_from_dict_clamps_counts():
    """from_dict clamps negative or huge float counts to 0 using _count."""
    state = LexisState.from_dict({"scenes_seen": -5})
    assert state.scenes_seen == 0

    state = LexisState.from_dict({"scenes_seen": float('inf')})
    assert state.scenes_seen == 0


def test_lexis_state_from_dict_missing_keys_uses_defaults():
    """from_dict handles a completely empty dict without raising and applies defaults."""
    state = LexisState.from_dict({})
    assert state.contact == {"pulse": False, "compound": False, "bridge": False}
    assert state.flags == {}
    assert state.notebook.entries == {}
