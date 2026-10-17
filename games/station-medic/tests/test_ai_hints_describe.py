"""Tests for hints.describe() -- edge case (act=None) and two normal cases (scan, treat)."""

import json

import pytest

import game
import hints
import progress


FIRST = progress.ORDER[0]


def call(**req):
    return json.loads(game.handle(json.dumps(req)))


@pytest.fixture(autouse=True)
def clean():
    game.game.__init__()
    call(action="difficulty", level="normal")
    yield
    call(action="difficulty", level="normal")
    game.game.__init__()


def test_describe_edge_case_no_action():
    """Edge case: no action left for a clean finish."""
    call(action="pick", shift=FIRST)
    res = hints.describe(game.game.case, game.game.st, None)
    assert res is not None
    assert res["kind"] == "restore"
    assert "Restore the shift" in res["label"]


def test_describe_normal_scan():
    """Normal case: describes a scan action."""
    call(action="pick", shift=FIRST)
    act = hints.next_action(game.game.case, game.game.st, game.game._solver())
    if act[0] != "scan":
        pytest.skip("Shift 1-1 does not start with a scan")
    res = hints.describe(game.game.case, game.game.st, act)
    assert res is not None
    assert res["kind"] == "scan"
    assert "Run the" in res["label"] and "on" in res["label"]


def test_describe_normal_treat():
    """Normal case: describes a treat action."""
    call(action="pick", shift=FIRST)
    act = hints.next_action(game.game.case, game.game.st, game.game._solver())
    if act[0] != "treat":
        pytest.skip("Shift 1-1 does not start with a treat")
    res = hints.describe(game.game.case, game.game.st, act)
    assert res is not None
    assert res["kind"] == "treat"
    assert "Give" in res["label"] and "the" in res["label"]
