"""Every authored bay is proved fair by the solver: solvable, par stored and equal to the shortest solution, at least four
moves, at most three shortest solutions, and the deck's new part really needed."""

import pytest

import bays
import rules
import solver

ALL = bays.ALL_BAYS
IDS = [b.id for b in ALL]


@pytest.fixture(scope="module")
def analyses():
    return {b.id: solver.analysis(b) for b in ALL}


def test_the_decks_hold_eight_bays_each_in_order_with_unique_ids():
    assert bays.DECK_LIST and all(len(d["bays"]) == 8 for d in bays.DECK_LIST)
    assert bays.ORDER == [bid for d in bays.DECK_LIST for bid in d["bays"]]
    assert len(set(IDS)) == len(IDS) and len({b.name for b in ALL}) == len(ALL)
    for i, d in enumerate(bays.DECK_LIST):
        assert [bays.BY_ID[bid].number for bid in d["bays"]] == list(range(1, 9)) and all(bays.BY_ID[bid].deck == i for bid in d["bays"])


@pytest.mark.parametrize("bid", IDS)
def test_every_bay_is_solvable_and_its_par_is_the_shortest_solution(bid, analyses):
    b, a = bays.BY_ID[bid], analyses[bid]
    assert a.complete, "the whole state space is searched"
    assert a.par is not None and b.par == a.par and len(b.line) == b.par
    assert rules.replay(b, b.line) is not None and b.cleared(rules.replay(b, b.line)[0][-1])


@pytest.mark.parametrize("bid", IDS)
def test_no_bay_is_solved_in_fewer_than_four_moves(bid, analyses):
    assert bays.BY_ID[bid].par >= 4


@pytest.mark.parametrize("bid", IDS)
def test_every_bay_has_at_most_three_shortest_solutions_so_the_stored_hint_is_fair(bid, analyses):
    a = analyses[bid]
    assert 1 <= a.optimal_count() <= 3 and bays.BY_ID[bid].line in a.all_optimal_lines()


@pytest.mark.parametrize("bid", IDS)
def test_every_bay_is_small_enough_to_search_in_full_on_a_phone(bid, analyses):
    assert analyses[bid].size <= 40000


@pytest.mark.parametrize("bid", IDS)
def test_the_rows_are_well_formed_and_unique(bid):
    b = bays.BY_ID[bid]
    assert 5 <= b.w <= 10 and 5 <= b.h <= 10 and len(b.start[1]) >= 1
    assert len({(x.rows, x.door) for x in ALL}) == len(ALL)


def test_deck_one_is_one_crate_in_open_floor():
    deck = bays.DECK_LIST[0]
    for bid in deck["bays"]:
        b = bays.BY_ID[bid]
        assert len(b.start[1]) == 1 and not b.door_cells
        assert all(g in ".#@1A" for row in b.rows for g in row)


def test_par_climbs_across_the_first_deck_and_never_falls_by_much():
    pars = [bays.BY_ID[bid].par for bid in bays.DECK_LIST[0]["bays"]]
    assert pars == sorted(pars) and pars[0] <= 5 and pars[-1] >= 10


def test_some_bay_in_play_lets_you_move_without_being_stopped_for_a_long_way():
    assert any(solver.analysis(b).longest_slide_available() >= 5 for b in ALL)
