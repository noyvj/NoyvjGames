"""Edge-case tests for hints.py."""

import json

import cases
import game
import hints


def call(**req):
    return json.loads(game.handle(json.dumps(req)))


def fresh():
    game.game.__init__()


def test_nudge_text_handles_single_clause_case():
    """nudge_text for the smallest allowed rule size (1 clause)."""
    c = cases.BY_ID["latch"]
    text = hints.nudge_text(c)
    assert text.startswith("Look at ") and text.endswith(".")


def test_nudge_text_handles_three_clause_case():
    """nudge_text for the largest allowed rule size (3 clauses)."""
    c3 = next(c for c in cases.ALL_CASES if c.size == 3)
    text = hints.nudge_text(c3)
    assert "The gate looks at 3 things" in text or "looks at 3 things" in text


def test_next_item_returns_first_when_seen_is_empty():
    """next_item with zero input (empty seen set) returns the first shortest-path item."""
    c = cases.BY_ID["latch"]
    key = hints.next_item(c, set())
    assert key == c.shortest[0]


def test_next_item_returns_none_when_all_shortest_path_seen():
    """next_item when the player has seen every item on the shortest path."""
    c = cases.BY_ID["latch"]
    seen = set(c.shortest)
    key = hints.next_item(c, seen)
    assert key is None


def test_hint_view_returns_empty_when_nothing_left():
    """hint_view when the player has already tested all shortest-path items."""
    c = cases.BY_ID["latch"]
    seen = set(c.shortest)
    v = hints.hint_view(c, seen)
    assert v["item"] == "" and "seen enough" in v["text"].lower()


def test_view_rung_0_returns_blank_state():
    """view with rung 0 (zero input) should return empty nudge/hint/answer."""
    c = cases.BY_ID["latch"]
    v = hints.view(c, 0, set())
    assert v["rung"] == 0 and v["nudge"] == "" and v["hint"] is None and v["answer"] is None


def test_view_rung_4_clamps_to_full_answer():
    """view with rung > 3 should behave identically to rung 3."""
    c = cases.BY_ID["latch"]
    v3 = hints.view(c, 3, set())
    v4 = hints.view(c, 4, set())
    assert v3["nudge"] == v4["nudge"] and v3["hint"] == v4["hint"] and v3["answer"] == v4["answer"]


def test_view_rung_2_returns_hint_but_no_answer():
    """view with rung 2 should provide a hint but no answer."""
    c = cases.BY_ID["latch"]
    v = hints.view(c, 2, set())
    assert v["hint"] is not None and v["answer"] is None
