"""The 14 achievements: manifest in step with the code, each a have-of-need number, all reachable, none timed or hidden."""

import json
from pathlib import Path

import achievements
import state
from tests.helpers import build, call, fresh, solve, solve_all

GAME_DIR = Path(__file__).resolve().parent.parent


def test_the_manifest_matches_the_code_exactly():
    manifest = json.loads((GAME_DIR / "achievements.json").read_text(encoding="utf-8"))["achievements"]
    assert manifest == [{"id": i, "label": label, "description": desc} for i, label, desc, _n in achievements.ACHIEVEMENTS]
    assert len(manifest) == 14 and len({a["id"] for a in manifest}) == 14


def test_a_new_player_has_none_and_sees_three_goals():
    meta = state.new_meta()
    assert achievements.earned(meta) == []
    goals = achievements.goals(meta)
    assert len(goals) == 3 and all(g["have"] == 0 and not g["earned"] for g in goals)


def test_goals_are_the_closest_unearned_and_shrink_only_when_nearly_all_are_earned():
    meta = state.new_meta()
    meta["levels"]["straight-through"] = dict(state.new_record(), solved=True, chips=0, par=True)
    goals = [g["id"] for g in achievements.goals(meta)]
    assert goals[0] == "gate_keeper" and "first_light" not in goals           # 1 of 8 beats 0 of the rest
    assert "first_light" in achievements.earned(meta)


def test_every_achievement_can_be_earned_in_one_ordinary_game():
    solve_all()
    call("start", level="invert")
    for _ in range(50):
        call("flip", name="A")
        call("flip", name="A")
    call("hint")
    call("start", level="sandbox")
    for code in range(16):
        call("clear")
        circuit = {"chips": [], "wires": {}}

        def chip(t):
            circuit["chips"].append({"id": len(circuit["chips"]) + 1, "type": t})
            return len(circuit["chips"])
        na, nb = chip("not"), chip("not")
        circuit["wires"][f"{na}.A"] = "in:A"
        circuit["wires"][f"{nb}.A"] = "in:B"
        outs = []
        for k in range(4):
            if (code >> (3 - k)) & 1:
                c = chip("and")
                circuit["wires"][f"{c}.A"] = f"{na}.Y" if k < 2 else "in:A"
                circuit["wires"][f"{c}.B"] = f"{nb}.Y" if k % 2 == 0 else "in:B"
                outs.append(f"{c}.Y")
        if not outs:
            circuit["wires"]["out:X"] = "const:0"
        else:
            acc = outs[0]
            for o in outs[1:]:
                c = chip("or")
                circuit["wires"][f"{c}.A"] = acc
                circuit["wires"][f"{c}.B"] = o
                acc = f"{c}.Y"
            circuit["wires"]["out:X"] = acc
        build(circuit)
    v = call("open")
    assert [a["id"] for a in v["achievements"] if not a["earned"]] == [], v["achievements"]
    assert len(json.dumps(__import__("game").get_state())) < 60000
    assert len(__import__("game").get_state()["achievements_earned"]) == 14


def test_reaching_par_and_using_hints_are_tracked_separately():
    fresh()
    solve("straight-through")
    meta = __import__("game").meta
    assert meta["levels"]["straight-through"]["par"] and achievements.progress(meta)["on_your_own"] == 1
    call("hint")
    assert achievements.progress(meta)["asked_nicely"] == 1
    assert achievements.progress(meta)["on_your_own"] == 0          # a hint on that level means it no longer counts as unaided


def test_the_save_never_trusts_a_stored_achievement_list():
    import game
    fresh()
    game.load_state({"schema": 1, "achievements_earned": ["forty_for_forty", "full_par"], "meta": {}})
    assert call("open")["stats"]["solved"] == 0
    assert game.get_state() == {"schema": 1}


def test_no_achievement_needs_a_clock_a_day_or_a_leaderboard():
    text = " ".join(d for _i, _l, d, _n in achievements.ACHIEVEMENTS).lower()
    for word in ("day", "week", "second", "minute", "leaderboard", "daily", "streak"):
        assert word not in text, word
