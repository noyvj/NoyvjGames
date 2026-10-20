import hints
import rooms


def test_hint_text_with_few_blocks():
    """hint_text correctly processes a room with minimal reference instructions."""
    r = rooms.BY_ID["wake-up"]
    text = hints.hint_text(r)
    assert "steps" in text
    assert "starts with" in text


def test_hint_text_with_complex_reference():
    """hint_text correctly identifies and lists multiple types of blocks."""
    r = rooms.BY_ID["stair-haul"]
    text = hints.hint_text(r)
    assert "steps" in text
    assert "repeat block" in text


def test_view_clamps_rung_to_limit():
    """view clamps the rung value when it exceeds the limit."""
    r = rooms.BY_ID["wake-up"]
    v = hints.view(r, 10, limit=3)
    assert v["rung"] == 3
    assert v["next"] == ""
    assert v["max"] == 3


def test_view_limit_two_omits_answer():
    """view with limit=2 correctly omits the answer step for Hard mode."""
    r = rooms.BY_ID["wake-up"]
    v = hints.view(r, 3, limit=2)
    assert v["rung"] == 2
    assert v["answer"] is None
    assert "hint" in v and v["hint"]


def test_answer_structure_and_types():
    """answer returns the expected keys with correct types for a room's reference."""
    r = rooms.BY_ID["wake-up"]
    data = hints.answer(r)
    assert isinstance(data["text"], str)
    assert isinstance(data["lines"], list)
    assert isinstance(data["steps"], int)
    assert data["steps"] > 0


def test_view_limit_zero_shows_no_hints():
    """view with limit=0 correctly suppresses all hint steps."""
    r = rooms.BY_ID["wake-up"]
    v = hints.view(r, 1, limit=0)
    assert v["rung"] == 0
    assert v["next"] == ""
    assert v["nudge"] == ""
    assert v["hint"] == ""
    assert v["answer"] is None
