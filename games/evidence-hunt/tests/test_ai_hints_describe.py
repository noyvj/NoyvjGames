"""Tests for hints.describe()"""

import json
import pytest

import game
import hints
import progress
import lexicon as lx


FIRST = progress.ORDER[0]


@pytest.fixture(autouse=True)
def clean():
    game.game.__init__()
    yield


def test_describe_returns_restore_when_act_is_none():
    """Edge case: act is None returns restore advice with correct keys."""
    game.handle(json.dumps({"action": "open"}))
    game.handle(json.dumps({"action": "pick", "case": FIRST}))
    v = hints.describe(game.game.case, game.game.st, None)
    assert v["kind"] == "restore"
    assert v["label"] == "Restore the case"
    assert "clean finish" in v["nudge"].lower()
    assert v["hint"] and v["answer"]


def test_describe_handles_go_action():
    """Normal case: walking into a room."""
    game.handle(json.dumps({"action": "open"}))
    game.handle(json.dumps({"action": "pick", "case": FIRST}))
    act = hints.next_action(game.game.case, game.game.st)
    assert act is not None and act[0] == "go"
    v = hints.describe(game.game.case, game.game.st, act)
    assert v["kind"] == "go"
    assert "Walk into the" in v["label"]
    assert v["hint"] and v["answer"]


def test_describe_handles_pack_action():
    """Normal case: packing equipment."""
    game.handle(json.dumps({"action": "open"}))
    game.handle(json.dumps({"action": "pick", "case": FIRST}))
    # describe is a pure formatter; we pass a valid pack action tuple directly.
    act = ("pack", 0)
    v = hints.describe(game.game.case, game.game.st, act)
    assert v["kind"] == "pack"
    assert lx.GEAR_NAME[act[1]] in v["label"]


def test_describe_handles_use_action():
    """Normal case: using equipment."""
    game.handle(json.dumps({"action": "open"}))
    game.handle(json.dumps({"action": "pick", "case": FIRST}))
    act = ("use", 0)
    v = hints.describe(game.game.case, game.game.st, act)
    assert v["kind"] == "use"
    assert lx.GEAR_NAME[act[1]] in v["label"]
