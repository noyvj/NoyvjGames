import json

import pytest

import game
from tests.helpers import call, fresh, solve, solve_all


@pytest.fixture(autouse=True)
def _timing_back_off():
    """timing_on is a module global (never saved); put it back so it cannot leak into other test files."""
    yield
    game.timing_on = False


def test_timing_is_none_on_a_level_without_steps_even_when_on():
    fresh()
    v = call("timing", on=True)
    assert v["timing"] is None


def test_timing_latch_up():
    solve_all()
    solve("latch-up")
    v = call("timing", on=True)
    assert v["timing"]["steps"] == 7
    rows = v["timing"]["rows"]
    names = [r["name"] for r in rows]
    bits = {r["name"]: r["bits"] for r in rows}
    kinds = {r["name"]: r["kind"] for r in rows}
    assert names == ["S", "R", "Q", "QN"]
    assert bits["S"] == [0, 1, 0, 0, 0, 1, 0]
    assert bits["R"] == [1, 0, 0, 1, 0, 0, 0]
    assert bits["Q"] == [0, 1, 1, 0, 0, 1, 1]
    assert bits["QN"] == [1, 0, 0, 1, 1, 0, 0]
    assert kinds["S"] == "switch"
    assert kinds["R"] == "switch"
    assert kinds["Q"] == "lamp"
    assert kinds["QN"] == "lamp"


def test_timing_on_false():
    solve_all()
    solve("latch-up")
    v = call("timing", on=False)
    assert v["timing"] is None


def test_timing_after_clear():
    solve_all()
    solve("latch-up")
    call("timing", on=True)
    call("clear")
    v = call("timing", on=True)
    q_bits = [r["bits"] for r in v["timing"]["rows"] if r["name"] == "Q"][0]
    qn_bits = [r["bits"] for r in v["timing"]["rows"] if r["name"] == "QN"][0]
    assert q_bits == [0, 0, 0, 0, 0, 0, 0]
    assert qn_bits == [0, 0, 0, 0, 0, 0, 0]


def test_timing_does_not_affect_state():
    solve_all()
    solve("latch-up")
    state_before = json.dumps(game.get_state(), sort_keys=True)
    call("timing", on=True)
    state_after = json.dumps(game.get_state(), sort_keys=True)
    assert state_before == state_after
