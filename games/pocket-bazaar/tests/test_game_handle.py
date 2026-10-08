import json

import pytest

import game
from board import Board


@pytest.fixture(autouse=True)
def fresh():
    game.stall.__init__()
    yield
    game.stall.__init__()


def call(**request):
    return json.loads(game.handle(json.dumps(request)))


def set_board(text):
    game.stall.board = Board.from_text(text)


def test_open_describes_an_empty_counter_and_three_crates():
    v = call(action="open")
    assert v["ok"] and v["board"]["w"] == 5 and v["board"]["h"] == 6
    assert len(v["board"]["cells"]) == 30 and all(c is None for c in v["board"]["cells"])
    assert [c["family"] for c in v["crates"]] == ["produce", "textiles", "ceramics"]
    assert v["coins"] == 0 and v["partners"] == {} and v["full"] is False


def test_a_crate_puts_a_tier_one_good_on_the_first_free_cell_and_counts():
    v = call(action="crate", family="textiles")
    assert v["board"]["cells"][0]["code"] == "T1" and v["tally"]["crates"] == 1
    assert v["event"] == {"kind": "crate", "at": 0}
    v = call(action="crate", family="produce")
    assert v["board"]["cells"][1]["code"] == "P1" and v["tally"]["crates"] == 2


def test_a_crate_not_open_yet_is_refused_without_changing_anything():
    v = call(action="crate", family="sweets")
    assert v["ok"] is False and v["tally"]["crates"] == 0
    assert call(action="crate", family=5)["ok"] is False


def test_crates_are_unlimited_until_the_counter_is_full_and_then_say_so():
    for _ in range(30):
        assert call(action="crate", family="produce")["ok"]
    v = call(action="crate", family="produce")
    assert v["ok"] is False and "full" in v["message"] and v["tally"]["crates"] == 30 and v["full"] is True


def test_dropping_a_good_on_its_twin_merges_and_updates_the_tally():
    set_board("P1 P1 .. .. ..")
    v = call(action="drop", **{"from": 0, "to": 1})
    assert v["ok"] and v["board"]["cells"][1]["code"] == "P2" and v["board"]["cells"][0] is None
    assert v["tally"]["merges"] == 1 and v["best_chain"] == 1
    assert v["event"]["kind"] == "merge" and v["event"]["dst"] == 1
    assert "Plum" in v["message"]


def test_a_chain_and_a_three_way_bonus_are_reported_and_counted():
    set_board(".. P2 .. .. ..\nP3 P1 P4 .. ..\n.. P1 .. .. ..")
    v = call(action="drop", **{"from": 11, "to": 6})
    assert v["best_chain"] == 4 and v["tally"]["merges"] == 4 and "4-link chain" in v["message"]
    set_board("P1 P1 P1 .. ..")
    v = call(action="drop", **{"from": 0, "to": 1})
    assert v["tally"]["triples"] == 1 and "Three-way" in v["message"]


def test_a_refused_merge_changes_nothing_and_says_why():
    set_board("P1 T1 .. .. ..")
    v = call(action="drop", **{"from": 0, "to": 3})                 # to an empty cell: a move, not a refusal
    assert v["ok"] and v["message"] == "Moved."
    v = call(action="drop", **{"from": 5, "to": 6})
    assert v["ok"] is False and "nothing" in v["message"].lower()


def test_dropping_on_a_different_good_swaps_them():
    set_board("P1 T2 .. .. ..")
    v = call(action="drop", **{"from": 0, "to": 1})
    assert v["message"] == "Swapped them." and v["board"]["cells"][0]["code"] == "T2" and v["tally"]["merges"] == 0


def test_selling_pays_the_sell_price_and_counts():
    set_board("P1 C4 .. .. ..")
    v = call(action="sell", at=1)
    assert v["coins"] == 14 and v["tally"]["sold"] == 1 and v["board"]["cells"][1] is None
    assert call(action="sell", at=1)["ok"] is False and game.stall.coins == 14
    assert call(action="sell", at=0)["coins"] == 15


def test_the_broom_sweeps_for_free_and_counts():
    set_board("P1 .. .. .. ..")
    v = call(action="broom", at=0)
    assert v["ok"] and v["coins"] == 0 and v["tally"]["swept"] == 1
    assert call(action="broom", at=0)["ok"] is False


def test_a_full_jammed_counter_is_always_escapable():
    game.stall.board = Board(5, 6)
    game.stall.board.cells = [("textiles", 5)] * 30
    v = call(action="open")
    assert v["full"] and v["partners"] == {}
    assert call(action="crate", family="produce")["ok"] is False
    assert call(action="sell", at=0)["ok"]
    assert call(action="crate", family="produce")["ok"]


def test_partners_lists_every_match_for_each_good():
    set_board("P1 P1 T1 .. P1")
    v = call(action="open")
    assert v["partners"] == {"0": [1, 4], "1": [0, 4], "4": [0, 1]}


def test_junk_requests_never_crash_the_engine():
    assert "error" in json.loads(game.handle("not json"))
    assert "error" in json.loads(game.handle("[]"))
    assert "error" in call(action="dance")
    for junk in ("x", -1, 99, True, None, 1.5, [1]):
        for act in ("sell", "broom"):
            assert call(action=act, at=junk)["ok"] is False
        assert call(action="drop", **{"from": junk, "to": 0})["ok"] is False
        assert call(action="drop", **{"from": 0, "to": junk})["ok"] is False


def test_clear_and_reset():
    call(action="crate", family="produce")
    assert call(action="clear")["board"]["cells"][0] is None
    set_board("P1 .. .. .. ..")
    call(action="sell", at=0)
    v = call(action="reset")
    assert v["coins"] == 0 and v["tally"]["sold"] == 0


# ---- the save contract -----------------------------------------------------------------------------------
def test_a_fresh_game_saves_nothing_and_only_non_default_keys_appear():
    assert game.get_state() == {}
    call(action="crate", family="produce")
    assert set(game.get_state()) == {"board", "tally"}
    set_board("P1 .. .. .. ..")
    call(action="sell", at=0)
    assert set(game.get_state()) == {"coins", "tally"}


def test_save_round_trip_is_exact_and_json_safe():
    set_board("P1 P1 T1 C5 ..")
    call(action="drop", **{"from": 0, "to": 1})
    call(action="sell", at=3)
    data = json.loads(json.dumps(game.get_state()))
    snapshot = (game.stall.board.render(), game.stall.coins, dict(game.stall.tally), game.stall.best_chain)
    game.stall.__init__()
    game.load_state(data)
    assert (game.stall.board.render(), game.stall.coins, dict(game.stall.tally), game.stall.best_chain) == snapshot


@pytest.mark.parametrize("junk", [None, [], "x", 5, {}, {"board": 5}, {"board": {"w": 5}}, {"coins": -5}, {"coins": "9"},
                                  {"coins": True}, {"coins": 10 ** 12}, {"tally": []}, {"tally": {"merges": -1, "sold": "x"}},
                                  {"best_chain": 99}, {"board": {"w": 5, "h": 6, "cells": [None] * 29}}])
def test_load_state_survives_any_junk_with_safe_defaults(junk):
    call(action="crate", family="produce")
    game.load_state(junk)
    v = call(action="open")
    assert v["ok"] and 0 <= v["coins"] <= game.MAX_COINS and v["best_chain"] <= 5
    assert all(n >= 0 for n in v["tally"].values()) and len(v["board"]["cells"]) in (30, 31)


def test_one_bad_field_does_not_cost_the_good_ones():
    game.load_state({"board": {"w": 1}, "coins": 77, "tally": {"merges": 3}})
    assert game.stall.coins == 77 and game.stall.tally["merges"] == 3 and game.stall.board.count() == 0
