from editor import Editor


def ed(allow="F L R G P S rep until if A B"):
    return Editor(None, allow)


def test_default_editor_is_empty():
    """A freshly created editor should report as empty."""
    assert ed().is_empty()


def test_editor_with_actions_is_not_empty():
    """An editor that has received instructions should not be empty."""
    e = ed()
    for a in "FLR":
        e.insert(a)
    assert not e.is_empty()


def test_editor_becomes_empty_after_clear():
    """Clearing an editor should make is_empty return True again."""
    e = ed()
    e.insert("F")
    assert not e.is_empty()
    e.clear()
    assert e.is_empty()
