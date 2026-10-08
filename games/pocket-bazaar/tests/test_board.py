import random

import pytest

from board import Board, plan_build, Refused
from goods import FAMILIES, MAX_TIER, WILD
from textplay import play


def B(text, **kw):
    return Board.from_text(text, **kw)


def test_a_new_board_is_five_by_six_and_empty():
    b = Board()
    assert (b.width, b.height, b.size) == (5, 6, 30) and len(b.cells) == 30
    assert b.empty_cells() == list(range(30)) and not b.is_full() and b.first_empty() == 0


def test_neighbours_are_orthogonal_and_in_reading_order():
    b = Board()
    assert b.neighbors(0) == [1, 5]
    assert b.neighbors(7) == [2, 6, 8, 12]
    assert b.neighbors(29) == [24, 28]
    assert b.neighbors(4) == [3, 9]               # the right edge does not wrap onto the next row
    assert b.neighbors(5) == [0, 6, 10]           # nor the left edge onto the previous one
    assert b.neighbors(99) == [] and b.neighbors(-1) == []


def test_place_goes_to_the_first_empty_cell_or_the_chosen_one():
    b = Board()
    assert b.place(("produce", 1)) == 0
    assert b.place(("produce", 1)) == 1
    assert b.place(("textiles", 1), at=7) == 7
    assert b.place(("textiles", 1), at=7) is None          # occupied
    assert b.place(("textiles", 1), at=99) is None
    with pytest.raises(ValueError):
        b.place(("produce", 9))


def test_a_pair_merges_into_the_next_tier_on_the_cell_dropped_on():
    b = B("P1 P1 .. .. ..")
    r = b.merge(0, 1)
    assert r.ok and r.dst == 1 and r.good == ("produce", 2) and r.links == 1 and not r.triple
    assert b.render().splitlines()[0] == ".. P2 .. .. .."


def test_different_goods_and_different_tiers_do_not_merge():
    b = B("P1 T1 P2 .. ..")
    assert not b.can_merge(0, 1) and not b.can_merge(0, 2)
    r = b.merge(0, 1)
    assert isinstance(r, Refused) and "identical" in r.reason
    assert b.merge(0, 3).reason == "That spot is empty."
    assert b.merge(3, 0).reason == "There is nothing there to move."
    assert b.merge(0, 0).reason == "That is the same spot."
    assert b.merge(0, 99).reason == "That is not a spot on the board."


def test_showpieces_never_merge():
    b = B("C5 C5 .. .. ..")
    assert not b.can_merge(0, 1)
    assert "showpiece" in b.merge(0, 1).reason


def test_three_way_bonus_jumps_two_tiers():
    b = B("P1 P1 P1 .. ..")                       # drop 0 on 1; 2 is next to 1
    r = b.merge(0, 1)
    assert r.triple and r.good == ("produce", 3) and sorted(r.consumed) == [0, 2]
    assert b.render().splitlines()[0] == ".. P3 .. .. .."


def test_the_bonus_needs_the_third_beside_the_cell_dropped_on():
    b = B("P1 P1 .. .. P1")                       # the third is far away
    r = b.merge(0, 1)
    assert not r.triple and r.good == ("produce", 2)
    assert b.cells[4] == ("produce", 1)


def test_no_bonus_when_it_would_pass_the_showpiece():
    b = B("P4 P4 P4 .. ..")
    r = b.merge(0, 1)
    assert not r.triple and r.good == ("produce", 5) and b.cells[2] == ("produce", 4)


def test_cascade_runs_through_matching_neighbours_and_counts_links():
    b = B("P1 P1 T2 .. ..")
    assert b.merge(0, 1).links == 1                  # the new P2 has no P2 beside it
    c = B("""
        .. P2 .. .. ..
        P3 P1 P4 .. ..
        .. P1 .. .. ..
    """)
    r = c.merge(11, 6)                           # P1+P1 -> P2, joins P2 above -> P3, joins P3 -> P4, joins P4 -> P5
    assert r.links == 4 and r.steps == [2, 3, 4, 5] and r.good == ("produce", 5)
    assert c.cells[6] == ("produce", 5)
    assert c.count() == 1


def test_the_longest_possible_chain_is_four():
    c = B("""
        .. P2 .. .. ..
        P3 P1 P4 .. ..
        .. P1 .. .. ..
    """)
    assert c.merge(11, 6).links == MAX_TIER - 1


def test_cascades_are_deterministic():
    text = ".. P2 .. .. ..\nP3 P1 P4 .. ..\n.. P1 .. .. .."
    a, b = B(text), B(text)
    assert a.merge(11, 6).to_dict() == b.merge(11, 6).to_dict() and a.render() == b.render()


def test_wildcard_merges_with_any_regular_good_below_the_showpiece():
    b = B("** S2 C5 ** ..")
    r = b.merge(0, 1)
    assert r.good == ("spices", 3) and b.cells[0] is None
    assert not b.can_merge(3, 2)                  # a showpiece
    c = B("** ** .. .. ..")
    assert not c.can_merge(0, 1)


def test_twin_rule_spawns_a_free_t1_beside_a_new_t3():
    b = B("P2 P2 .. .. ..")
    r = b.merge(0, 1, {"twin": True})
    assert r.good == ("produce", 3) and len(r.spawned) == 1
    assert b.cells[r.spawned[0]] == ("produce", 1) and r.spawned[0] in b.neighbors(1)
    c = B("P2 P2 .. .. ..")
    assert c.merge(0, 1).spawned == []                              # off without the rule
    d = B("P1 P1 .. .. ..")
    assert d.merge(0, 1, {"twin": True}).spawned == []              # only a new tier 3


def test_drop_merges_moves_or_swaps_and_neither_move_nor_swap_loses_goods():
    b = B("P1 P1 T2 .. ..")
    assert b.drop(0, 1).links == 1
    b = B("P1 T2 .. .. ..")
    r = b.drop(0, 3)
    assert r.ok and r.links == 0 and not r.swapped and b.cells[3] == ("produce", 1) and b.cells[0] is None
    r = b.drop(3, 1)
    assert r.swapped and b.cells[3] == ("textiles", 2) and b.cells[1] == ("produce", 1)
    assert not b.drop(0, 1).ok


def test_sell_pays_something_and_empties_the_cell():
    b = B("P1 T5 .. .. ..")
    assert b.sell(0) == 1 and b.cells[0] is None
    assert b.sell(1) == 32
    assert b.sell(0) is None and b.sell(99) is None


def test_broom_clears_a_cell_for_free_and_refuses_an_empty_one():
    b = B("P1 .. .. .. ..")
    assert b.broom(0) is True and b.broom(0) is False and b.broom(40) is False


def test_the_shelf_is_a_cell_outside_the_grid_that_holds_a_good():
    b = Board(shelf=True)
    assert b.shelf_index == 30 and len(b.cells) == 31
    assert b.first_empty() == 0 and b.place(("produce", 1), at=30) == 30
    assert b.neighbors(30) == []
    b.place(("produce", 1), at=0)
    assert b.merge(0, 30).good == ("produce", 2) and b.cells[30] == ("produce", 2)
    assert "shelf: P2" in b.render()
    for _ in range(30):
        b.place(("textiles", 1))
    assert b.is_full()                                          # the shelf does not count as grid space


def test_text_round_trip():
    text = "P1 T2 C3 S4 D5\n.. ** .. .. P1\n.. .. .. .. ..\nshelf: C2"
    b = B(text, height=3)
    assert b.render() == text and Board.from_text(b.render(), height=3).cells == b.cells


def test_save_round_trip_and_validation():
    b = B("P1 T2 C3 S4 D5\n.. ** .. .. P1\nshelf: C2")
    again = Board.from_dict(b.to_dict())
    assert again.cells == b.cells and (again.width, again.height, again.has_shelf) == (5, 6, True)
    d = b.to_dict()
    bad_cases = [None, [], {}, {**d, "w": 2}, {**d, "w": "5"}, {**d, "h": True}, {**d, "cells": d["cells"][:-1]},
                 {**d, "cells": "x"}, {**d, "cells": [{"f": "produce", "t": 9}] + d["cells"][1:]},
                 {**d, "cells": [5] + d["cells"][1:]}, {**d, "cells": [{"f": WILD, "t": 3}] + d["cells"][1:]}]
    for bad in bad_cases:
        with pytest.raises(ValueError):
            Board.from_dict(bad)


def test_plan_build_reaches_every_good_from_an_empty_board_and_matches_the_cost():
    from goods import crate_beats
    for fam in FAMILIES:
        for tier in range(1, 6):
            actions, board = plan_build(Board(), fam, tier)
            assert (fam, tier) in board.cells
            assert len(actions) <= crate_beats(tier)          # taps + merges; a cascade can save a merge
            if tier <= 2:
                assert len(actions) == crate_beats(tier)
            assert board.count() >= 1


def test_every_good_is_reachable_with_only_five_free_cells():
    b = Board()
    cells = ([("textiles", 5)] * 3 + [("ceramics", 5)] * 3 + [("spices", 5)] * 3 + [("sweets", 5)] * 3
             + [("textiles", 4)] * 7 + [("ceramics", 4)] * 6)          # 25 jammed cells, 5 free
    for i, g in enumerate(cells):
        b.cells[i] = g
    assert len(b.empty_cells()) == 5
    assert plan_build(b, "produce", 5) is not None


def test_plan_build_gives_up_cleanly_when_the_board_is_jammed():
    b = Board(3, 3)
    b.cells = [("textiles", 5)] * 9
    assert plan_build(b, "produce", 3) is None


def test_a_full_board_chain_resolves_quickly():
    import time
    b = Board()
    for i in range(30):
        b.cells[i] = ("textiles", 5)
    b.cells[7] = ("produce", 1)
    b.cells[12] = ("produce", 1)
    b.cells[6] = ("produce", 2)
    b.cells[8] = ("produce", 3)
    b.cells[2] = ("produce", 4)
    start = time.perf_counter()
    for _ in range(200):
        c = b.copy()
        assert c.merge(12, 7).links == 4
    assert time.perf_counter() - start < 1.0


def test_there_is_always_a_legal_move_from_any_reachable_state():
    """Fuzz: random play with unlimited crates never leaves the player without a move, and a jammed board
    (full, no merge) is always cleared by one Sell or Broom."""
    rng = random.Random(2024)
    for run in range(40):
        b = Board(rng.choice([3, 4, 5, 6]), rng.choice([3, 4, 5, 6]), rng.random() < 0.3)
        for _step in range(250):
            assert b.has_legal_move()
            if not b.can_progress():
                before = b.count()
                good_cells = [i for i, _g in b.goods()]
                b.sell(rng.choice(good_cells)) if rng.random() < 0.5 else b.broom(rng.choice(good_cells))
                assert b.count() == before - 1 and b.can_progress()
                continue
            actions = b.legal_actions()
            kind = rng.choice([a[0] for a in actions] + ["crate"] * 3)
            if kind == "crate" and b.first_empty() is not None:
                b.place((rng.choice(FAMILIES), rng.choice([1, 1, 1, 2])))
            elif kind == "merge":
                pairs = b.merge_pairs()
                if pairs:
                    b.merge(*rng.choice(pairs))
            elif kind == "sell":
                b.sell(rng.choice(b.goods())[0]) if b.goods() else None
            elif kind == "broom":
                b.broom(rng.choice(b.goods())[0]) if b.goods() else None
        assert b.has_legal_move()


def test_an_empty_board_and_a_full_board_both_have_a_legal_move():
    assert Board().has_legal_move()
    b = Board(3, 3)
    b.cells = [("textiles", 5)] * 9
    assert not b.can_progress() and b.has_legal_move()
    acts = {a[0] for a in b.legal_actions()}
    assert acts == {"sell", "broom"}


def test_partners_lists_every_match_including_the_shelf():
    b = B("P1 P1 T1 .. P1\nshelf: P1")
    assert b.partners(0) == [1, 4, 30]
    assert b.partners(2) == []


def test_text_harness_plays_a_script_and_reports_each_step():
    board, log = play("""
        crate P      # cell 0
        crate P
        merge 0 1
        crate T
        sell 0
        merge 1 9
        broom 9
        show
    """)
    assert log[0] == "crate P -> cell 0" and log[2] == "merge -> 1 links"
    assert log[4].startswith("sold ") and "total 1" in log[4]
    assert log[5] == "moved" and log[6] == "swept"
    assert board.cells[1] is None and board.count() == 0
    assert play("sell 3")[1] == ["sell refused: nothing there"]
    assert play("merge 0 1")[1] == ["refused: There is nothing there to move."]
    with pytest.raises(ValueError):
        play("dance")
    full, _ = play("crate P\n" * 31)
    assert full.is_full()
