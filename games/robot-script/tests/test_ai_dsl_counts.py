import dsl


def test_counts_with_one_repeat():
    """counts() should return 1 for 'rep' and 0 for others when there is one repeat."""
    prog = {"main": [["rep", 3, ["F"]]]}
    result = dsl.counts(prog)
    assert result == {"rep": 1, "until": 0, "if": 0, "call": 0}


def test_counts_with_multiple_constructs():
    """counts() should correctly tally different constructs across routines."""
    prog = {
        "main": [["if", "part", ["F"], ["L"]], ["call", "A"]],
        "A": [["until", "blocked", ["R"]]]
    }
    result = dsl.counts(prog)
    assert result == {"rep": 0, "until": 1, "if": 1, "call": 1}


def test_counts_with_no_constructs():
    """counts() should return all zeros when the program contains only actions."""
    prog = {"main": ["F", "L", "R"]}
    result = dsl.counts(prog)
    assert result == {"rep": 0, "until": 0, "if": 0, "call": 0}
