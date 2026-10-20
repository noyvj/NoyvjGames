import engine


def test_parse_cell_with_colon():
    """Normal case: splits on colon, returns action and argument."""
    assert engine.parse_cell("standby:noise") == ("standby", "noise")


def test_parse_cell_without_colon():
    """Normal case: no colon means argument is None."""
    assert engine.parse_cell("lookout") == ("lookout", None)


def test_parse_cell_none_input():
    """Edge case: non-string or falsy input returns (None, None)."""
    assert engine.parse_cell(None) == (None, None)
