import dsl


def test_routines_used_returns_a_when_present():
    """routines_used() should list 'A' when it contains instructions."""
    prog = {"main": ["F"], "A": ["L"]}
    assert dsl.routines_used(prog) == ["A"]


def test_routines_used_returns_multiple_routines():
    """routines_used() should list all non-empty routines in order."""
    prog = {"main": ["F"], "A": ["L"], "B": ["R"]}
    assert dsl.routines_used(prog) == ["A", "B"]


def test_routines_used_ignores_empty_routine():
    """routines_used() should not list a routine that exists but is empty."""
    prog = {"main": ["F"], "A": []}
    assert dsl.routines_used(prog) == []
