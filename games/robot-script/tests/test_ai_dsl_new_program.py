import dsl


def test_new_program_returns_empty_main_list():
    """new_program() should return a dict with an empty main list."""
    prog = dsl.new_program()
    assert prog == {"main": []}


def test_new_program_returns_fresh_copy():
    """Each call to new_program() should return a new dict, not a shared reference."""
    prog1 = dsl.new_program()
    prog2 = dsl.new_program()
    assert prog1 is not prog2
    assert prog1["main"] is not prog2["main"]


def test_new_program_is_valid_program():
    """The program returned by new_program() should pass dsl.check()."""
    prog = dsl.new_program()
    assert dsl.check(prog) is None
