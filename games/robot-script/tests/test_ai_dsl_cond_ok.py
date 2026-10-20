import dsl


def test_cond_ok_accepts_valid_conditions():
    """Test that cond_ok accepts valid conditions with and without negation."""
    assert dsl.cond_ok("blocked") is True
    assert dsl.cond_ok("!blocked") is True
    assert dsl.cond_ok("part") is True
    assert dsl.cond_ok("!part") is True
    assert dsl.cond_ok("socket") is True
    assert dsl.cond_ok("!socket") is True
    assert dsl.cond_ok("switch") is True
    assert dsl.cond_ok("!switch") is True
    assert dsl.cond_ok("carrying") is True
    assert dsl.cond_ok("!carrying") is True
    assert dsl.cond_ok("exit") is True
    assert dsl.cond_ok("!exit") is True


def test_cond_ok_rejects_invalid_conditions():
    """Test that cond_ok rejects invalid conditions and non-string inputs."""
    assert dsl.cond_ok("invalid") is False
    assert dsl.cond_ok("!invalid") is False
    assert dsl.cond_ok("") is False
    assert dsl.cond_ok("!!blocked") is False
    assert dsl.cond_ok(123) is False
    assert dsl.cond_ok(None) is False
    assert dsl.cond_ok(["blocked"]) is False


def test_cond_ok_edge_cases():
    """Test edge cases for cond_ok, including whitespace handling."""
    assert dsl.cond_ok(" blocked") is False  # leading space
    assert dsl.cond_ok("blocked ") is False  # trailing space
    assert dsl.cond_ok("! blocked") is False  # space after !
    assert dsl.cond_ok("!blocked!") is False  # multiple ! in different positions
