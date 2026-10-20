import dsl


def test_cond_text_normal_condition():
    """cond_text() should return the condition as-is for normal conditions."""
    assert dsl.cond_text("blocked") == "blocked"
    assert dsl.cond_text("part") == "part"
    assert dsl.cond_text("socket") == "socket"


def test_cond_text_negated_condition():
    """cond_text() should prepend 'not ' and strip the leading '!' for negated conditions."""
    assert dsl.cond_text("!blocked") == "not blocked"
    assert dsl.cond_text("!part") == "not part"
    assert dsl.cond_text("!socket") == "not socket"


def test_cond_text_edge_case_empty_string():
    """cond_text() should handle edge case of empty string gracefully."""
    assert dsl.cond_text("") == ""
