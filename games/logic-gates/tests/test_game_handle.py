"""The whole game through handle(): solving, unlocking, editing rules, undo and restore, hints, the sandbox and the save contract."""

import json

import achievements
import game
import levels
import state
from tests.helpers import build, call, fresh, solve, solve_all


def test_a_fresh_game_opens_level_one_with_nothing_unlocked():
    v = fresh()
    assert v["level"]["id"] == "straight-through" and v["level"]["index"] == 1
    assert v["palette"] == [] and v["stats"]["solved"] == 0
    assert len(v["goals"]) == 3 and v["board"]["cap"] == 8


def test_wiring_the_switch_to_the_lamp_solves_level_one_and_unlocks_not():
    fresh()
    v = call("wire", dest="out:Y", src="in:A")
    assert v["table"]["ok"] and v["stats"]["solved"] == 1
    assert "NOT" in v["note"]
    assert [p["type"] for p in v["palette"]] == []        # level 1 hands out NOT but never offers it
    v = call("start", level="invert")
    assert [p["type"] for p in v["palette"]] == ["not"]


def test_a_locked_level_refuses_with_the_chips_it_waits_for():
    fresh()
    v = call("start", level="full-adder")
    assert v["level"]["id"] == "straight-through" and "waiting for" in v["note"]


def test_chips_come_only_from_the_shelf_and_the_board_has_a_cap():
    fresh()
    call("wire", dest="out:Y", src="in:A")
    call("start", level="invert")
    assert "shelf" in call("add", type="xor")["note"]
    for _ in range(8):
        call("add", type="not")
    v = call("add", type="not")
    assert "full" in v["note"] and v["board"]["count"] == 8


def test_counters_count_every_chip_wire_and_flip():
    fresh()
    call("wire", dest="out:Y", src="in:A")
    call("start", level="invert")
    call("add", type="not")
    call("wire", dest="1.A", src="in:A")
    call("wire", dest="out:Y", src="1.Y")
    v = call("flip", name="A")
    s = v["stats"]
    assert (s["chips"], s["wires"], s["flips"]) == (1, 3, 1)
    assert v["probe"]["inputs"] == {"A": 1}


def test_a_probe_flip_shows_the_signals_without_changing_the_result():
    fresh()
    call("wire", dest="out:Y", src="in:A")
    v = call("flip", name="A")
    assert v["board"]["lamps"][0]["value"] == 1 and v["table"]["ok"]
    assert "lg-w1" in v["svg"]


def test_loops_are_refused_in_a_combinational_level_and_allowed_in_memory():
    fresh()
    solve("straight-through")
    call("start", level="invert")
    call("add", type="not")
    v = call("wire", dest="1.A", src="1.Y")
    assert "loop" in v["note"] and v["board"]["chips"][0]["ins"][0]["src"] == ""
    # in memory levels (after the gates are unlocked) a NOR loop is fine
    for lid in ("invert", "both", "either", "odd-one-out", "not-both", "neither"):
        solve(lid)
    call("start", level="latch-up")
    call("add", type="nor")
    v = call("wire", dest="1.A", src="1.Y")
    assert "loop" not in v["note"] and v["board"]["chips"][0]["ins"][0]["src"] == "1.Y"


def test_undo_clear_and_restore_never_lose_work():
    fresh()
    solve("straight-through")
    call("start", level="invert")
    call("add", type="not")
    call("wire", dest="1.A", src="in:A")
    v = call("undo")
    assert v["board"]["chips"][0]["ins"][0]["src"] == ""
    assert call("undo")["board"]["count"] == 0
    assert "Nothing to undo" in call("undo")["note"]
    build({"chips": [{"id": 1, "type": "not"}], "wires": {"1.A": "in:A"}})
    v = call("clear")
    assert v["board"]["count"] == 0 and v["can_restore"]
    v = call("restore")
    assert v["board"]["count"] == 1 and v["board"]["chips"][0]["ins"][0]["src"] == "in:A"


def test_removing_a_chip_removes_its_wires():
    fresh()
    solve("straight-through")
    call("start", level="invert")
    build({"chips": [{"id": 1, "type": "not"}], "wires": {"1.A": "in:A", "out:Y": "1.Y"}})
    v = call("remove", id=1)
    assert v["board"]["count"] == 0 and v["board"]["lamps"][0]["src"] == ""


def test_tap_to_wire_works_in_either_order():
    fresh()
    solve("straight-through")
    call("start", level="invert")
    call("add", type="not")
    v = call("pick", pin="s:in:A")
    assert v["armed"] == "in:A"
    v = call("pick", pin="d:1.A")
    assert v["board"]["chips"][0]["ins"][0]["src"] == "in:A"
    call("cancel")
    call("pick", pin="d:out:Y")
    v = call("pick", pin="s:1.Y")
    assert v["board"]["lamps"][0]["src"] == "1.Y" and v["table"]["ok"]


def test_the_hint_ladder_is_three_rungs_and_the_answer_solves_without_par():
    fresh()
    solve("straight-through")
    call("start", level="invert")
    v = call("hint")
    assert v["hints"]["nudge"] and not v["hints"]["hint"]
    assert "hints first" in call("answer")["note"]
    call("hint")
    v = call("hint")
    assert v["hints"]["hint"] and v["hints"]["answer"] and v["hints"]["rung"] == 3
    assert "every hint" in call("hint")["note"]
    v = call("answer")
    assert v["table"]["ok"] and v["hints"]["answer_used"]
    assert v["stats"]["par"] == 1                      # only level 1; the answer does not earn par
    assert v["picker"][0]["levels"][1]["par"] is False and v["picker"][0]["levels"][1]["solved"]


def test_par_needs_no_more_chips_than_the_reference_and_improves_when_you_find_fewer():
    fresh()
    solve("straight-through")
    call("start", level="odd-one-out")      # needs and, or, not: solve prerequisites first
    for lid in ("invert", "both", "either"):
        solve(lid)
    v = solve("odd-one-out")
    rec = next(lv for lv in v["picker"][0]["levels"] if lv["id"] == "odd-one-out")
    assert rec["solved"] and rec["par"]


def test_the_whole_game_can_be_played_through_to_one_hundred_percent():
    v = solve_all()
    assert v["stats"]["solved"] == 40 and v["stats"]["par"] == 40
    assert all(a["id"] in ("hundred_chips", "switch_flipper", "the_sixteen", "asked_nicely", "on_your_own") or a["earned"] for a in v["achievements"])
    assert len(levels.unlocked(game._solved_ids())) >= 30


def test_solved_levels_stay_solved_and_their_board_is_kept():
    fresh()
    solve("straight-through")
    solve("invert")
    v = call("start", level="invert")
    assert v["board"]["count"] == 1 and v["table"]["ok"]


def test_the_sandbox_logs_every_new_truth_table_and_names_the_sixteen():
    fresh()
    for lid in ("straight-through", "invert", "both", "either"):
        solve(lid)
    v = call("start", level="sandbox")
    assert v["level"]["sandbox"] and v["sandbox"]["found"] == 0
    v = call("wire", dest="out:X", src="in:A")
    assert "A" in v["note"] and v["sandbox"]["found"] == 1
    call("add", type="and")
    call("wire", dest="1.A", src="in:A")
    v = call("wire", dest="1.B", src="in:B")
    v = call("wire", dest="out:Y", src="1.Y")
    assert "A AND B" in v["note"]
    names = {s["name"] for s in v["sandbox"]["sixteen"] if s["found"]}
    assert names == {"A", "A AND B"}
    v = call("wire", dest="out:Y", src="1.Y")
    assert v["sandbox"]["found"] == 2          # nothing new the second time


def test_the_sixteen_are_all_reachable_in_the_sandbox():
    solve_all()
    call("start", level="sandbox")
    for code in range(16):
        # build an output with truth table `code` over A, B using only AND/OR/NOT of minterms
        call("clear")
        terms = []
        for k in range(4):
            if (code >> (3 - k)) & 1:
                terms.append(k)
        circuit = {"chips": [], "wires": {}}

        def chip(t):
            circuit["chips"].append({"id": len(circuit["chips"]) + 1, "type": t})
            return len(circuit["chips"])
        na, nb = chip("not"), chip("not")
        circuit["wires"][f"{na}.A"] = "in:A"
        circuit["wires"][f"{nb}.A"] = "in:B"
        outs = []
        for k in terms:
            a = f"{na}.Y" if k < 2 else "in:A"
            b = f"{nb}.Y" if k % 2 == 0 else "in:B"
            c = chip("and")
            circuit["wires"][f"{c}.A"] = a
            circuit["wires"][f"{c}.B"] = b
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
    assert v["stats"]["sixteen"] == 16 and next(a for a in v["achievements"] if a["id"] == "the_sixteen")["earned"]


def test_save_round_trip_keeps_progress_boards_and_counters():
    fresh()
    solve("straight-through")
    solve("invert")
    call("flip", name="A")
    saved = json.loads(json.dumps(game.get_state()))
    assert saved["schema"] == 1 and saved["achievements_earned"] == ["first_light"]
    fresh()
    game.load_state(saved)
    v = call("open")
    assert v["stats"]["solved"] == 2 and v["stats"]["flips"] == 1 and v["level"]["id"] == "invert" and v["board"]["count"] == 1


def test_a_default_game_saves_almost_nothing():
    fresh()
    assert game.get_state() == {"schema": 1}


def test_loading_garbage_keeps_the_good_parts_and_never_raises():
    fresh()
    bad = {"schema": 1, "meta": {"levels": {"invert": {"solved": True, "chips": "many", "hints": 99}, "nope": {"solved": True}, "both": 5},
                                 "stats": {"chips": -4, "wires": "x", "flips": 7}, "found": [3, 300, "x", True, 3],
                                 "current": "wake-the-station",
                                 "work": {"invert": {"chips": [{"id": 1, "type": "xor"}, {"id": 1, "type": "not"}, {"id": "z", "type": "not"}, 4],
                                                     "wires": {"1.A": "in:A", "1.B": "in:Z", "9.A": "in:A", "out:Y": "1.Y", "out:Q": "1.Y"}}}}}
    game.load_state(bad)
    v = call("open")
    assert v["stats"]["flips"] == 7 and v["stats"]["chips"] == 0
    assert v["picker"][0]["levels"][1]["solved"]
    assert v["level"]["id"] != "wake-the-station"          # locked, so the game falls back to the first open unsolved level
    for junk in (None, 5, "x", [], {"meta": 3}, {"meta": {"levels": []}}):
        game.load_state(junk)
    assert call("open")["stats"]["solved"] >= 1


def test_loading_a_save_never_gives_a_chip_the_levels_have_not_unlocked():
    fresh()
    data = {"schema": 1, "meta": {"current": "invert", "work": {"invert": {"chips": [{"id": 1, "type": "xor"}, {"id": 2, "type": "not"}], "wires": {}}}}}
    game.load_state(data)
    v = call("open")
    assert [c["type"] for c in v["board"]["chips"]] == []      # not unlocked yet either: level 1 not solved


def test_loading_merges_with_progress_already_made():
    fresh()
    solve("straight-through")
    call("flip", name="A")
    other = {"schema": 1, "meta": {"levels": {"invert": {"solved": True, "chips": 1}}, "stats": {"flips": 5}}}
    game.load_state(other)
    v = call("open")
    assert v["stats"]["solved"] == 2 and v["stats"]["flips"] == 5


def test_every_action_is_deterministic():
    runs = []
    for _ in range(2):
        fresh()
        solve("straight-through")
        solve("invert")
        runs.append(json.dumps(game.get_state(), sort_keys=True))
    assert runs[0] == runs[1]


def test_unknown_and_malformed_requests_are_answered_not_raised():
    assert json.loads(game.handle("not json"))["error"]
    assert json.loads(game.handle(json.dumps({"action": "nope"})))["error"]
    fresh()
    assert call("add", type=5)["note"]
    assert call("wire", dest="x", src="y")["note"]
    assert call("remove", id=99)["note"]
    assert call("flip", name="Q")["note"]
    assert call("script", step=0)["note"]


def test_sequence_levels_offer_a_script_and_a_step_through():
    solve_all()
    v = call("start", level="latch-up")
    assert v["level"]["steps"] == 7
    v = call("script", step=1)
    assert v["probe"]["step"] == 1 and v["probe"]["inputs"] == {"S": 1, "R": 0}
    assert v["board"]["lamps"][0]["value"] == 1
    v = call("flip", name="S")
    assert v["probe"]["step"] is None


def test_goals_are_always_three_until_nearly_everything_is_earned():
    v = fresh()
    assert len(v["goals"]) == 3
    v = solve_all()
    assert len(v["goals"]) <= 3
    assert state.new_meta()["current"] == levels.LEVELS[0]["id"]
    assert len(achievements.ACHIEVEMENTS) == 14
