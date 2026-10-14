"""R4-SMPC-5: the 'undo' action behind the Z key (step back one action, free, never on a finished shift)."""

import json

import game
import progress


def call(**req):
    return json.loads(game.handle(json.dumps(req)))


def fresh():
    game.game.__init__()
    return call(action="open")


def _first_open_scan():
    """Some (shift, patient, scan) where a scan is available on a fresh shift."""
    for sid in progress.ORDER:
        game.game.__init__()
        v = call(action="pick", shift=sid)
        for p in v["patients"]:
            for a in p["actions"]["scan"]:
                if a["ok"]:
                    return sid, p["i"], a["t"]
    raise AssertionError("no shift offers a scan")


def test_undo_with_nothing_to_undo_is_refused_and_changes_nothing():
    v = fresh()
    before = json.dumps(game.get_state(), sort_keys=True)
    r = call(action="undo")
    assert r["ok"] is False and r["message"]
    assert json.dumps(game.get_state(), sort_keys=True) == before
    assert r["shift"]["id"] == v["shift"]["id"]


def test_undo_takes_back_the_last_scan_and_frees_the_reading():
    sid, p, t = _first_open_scan()
    game.game.__init__()
    call(action="pick", shift=sid)
    after_scan = call(action="scan", p=p, t=t)
    assert after_scan["ok"] and after_scan["patients"][p]["readings"][t]["state"] != "unknown"
    assert after_scan["patients"][p]["actions"]["scan"][t]["ok"] is False      # already run
    assert "run" in game.get_state()
    undone = call(action="undo")
    assert undone["ok"] and undone["message"] == "Stepped back one action."
    assert undone["patients"][p]["readings"][t]["state"] == "unknown"
    assert undone["patients"][p]["actions"]["scan"][t]["ok"] is True
    assert "run" not in game.get_state()
    assert not undone["log"] and undone["shift"]["cost"] == 0


def test_undo_keeps_the_lifetime_tally_and_the_record():
    sid, p, t = _first_open_scan()
    game.game.__init__()
    call(action="pick", shift=sid)
    call(action="scan", p=p, t=t)
    v = call(action="undo")
    assert v["tally"]["scans"] == 1 and game.get_state().get("tests")


def test_undo_is_refused_once_the_shift_is_finished():
    fresh()
    done = call(action="treat", p=0, x=0)
    assert done["result"] is not None
    r = call(action="undo")
    assert r["ok"] is False and "finished" in r["message"]
    assert r["result"] is not None and r["totals"]["done"] == 1


def test_undo_twice_walks_back_two_actions_then_stops():
    sid, p, t = _first_open_scan()
    game.game.__init__()
    call(action="pick", shift=sid)
    call(action="scan", p=p, t=t)
    borrowed = call(action="borrow", item=0)
    assert borrowed["ok"] and borrowed["shift"]["cost"] == 1
    first = call(action="undo")
    assert first["ok"] and first["shift"]["cost"] == 0 and first["patients"][p]["readings"][t]["state"] != "unknown"
    second = call(action="undo")
    assert second["ok"] and second["patients"][p]["readings"][t]["state"] == "unknown"
    assert call(action="undo")["ok"] is False
