import game
import json

from tests.helpers import call, fresh, solve, solve_all


def test_timing_off_or_no_steps():
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
