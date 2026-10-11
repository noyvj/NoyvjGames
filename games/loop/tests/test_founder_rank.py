"""H-12: the Founder rank ladder (a badge only; nothing in the game reads it)."""

import json

import pytest


def finish_chain(env, cycles, closed=False):
    """Runs a chain for `cycles` cycles (optionally closing the loop on the first) and resets."""
    chain = env.chain
    if closed:
        chain.funds = 5000.0
        for _ in range(11):
            env.invest_circularity("recycle")
    for _ in range(cycles):
        env.advance_cycle()
    env.reset_chain()


def test_a_new_player_is_an_apprentice_with_zero_points(game_env):
    m = game_env.module
    assert m.founder_points() == 0
    assert m.founder_rank()[:3] == (0, "Apprentice", 0)
    assert game_env.elements["rank-badge"].innerText.endswith("Apprentice")
    assert "0 points" in game_env.elements["rank-detail"].innerText
    assert "Next rank: Fitter at 15 points (15 to go)" in game_env.elements["rank-detail"].innerText


def test_points_are_cycles_plus_closed_chains_plus_goods_mastered(game_env):
    m = game_env.module
    game_env.chain.funds = 5000.0
    for _ in range(11):
        game_env.invest_circularity("recycle")
    for _ in range(4):
        game_env.advance_cycle()
    # 4 cycles + 15 for a closed chain + 30 for the one good mastered
    assert m.founder_stats() == (4, 1, 1)
    assert m.founder_points() == 4 + 15 + 30


def test_ranks_advance_at_their_thresholds(game_env):
    m = game_env.module
    for points, name in ((0, "Apprentice"), (14, "Apprentice"), (15, "Fitter"), (40, "Technician"),
                         (80, "Engineer"), (140, "Lead Engineer"), (220, "Director"),
                         (330, "Chief Circularity Officer"), (480, "Founder"), (5000, "Founder")):
        m.career_counts["cycles"] = points
        assert m.founder_rank()[1] == name, points
    assert "top rank" in m.founder_text()


def test_the_career_keeps_the_totals_through_new_chains(game_env):
    m = game_env.module
    finish_chain(game_env, 5)
    finish_chain(game_env, 3, closed=True)
    assert m.career_counts == {"cycles": 8, "chains_closed": 1}
    assert game_env.chain.cycle_number == 1
    assert m.founder_stats()[:2] == (8, 1)


def test_a_chain_that_never_ran_adds_nothing(game_env):
    m = game_env.module
    game_env.reset_chain()
    assert m.career_counts == {"cycles": 0, "chains_closed": 0}


def test_a_rewind_cannot_inflate_the_totals(game_env):
    m = game_env.module
    game_env.advance_cycle()
    game_env.advance_cycle()
    before = m.founder_points()
    assert game_env.chain.rewind()
    assert m.founder_points() == before - 1
    game_env.advance_cycle()
    assert m.founder_points() == before


def test_the_live_chain_is_counted_before_it_is_archived(game_env):
    m = game_env.module
    for _ in range(6):
        game_env.advance_cycle()
    assert m.founder_stats()[0] == 6
    game_env.reset_chain()
    assert m.founder_stats()[0] == 6  # not counted twice


def test_the_badge_follows_the_points_on_screen(game_env):
    m = game_env.module
    m.career_counts["cycles"] = 100
    m.render()
    assert game_env.elements["rank-badge"].innerText.endswith("Engineer")
    assert "Founder rank: Engineer." in game_env.elements["rank-detail"].innerText


def test_totals_round_trip_in_the_career(game_env):
    m = game_env.module
    finish_chain(game_env, 4, closed=True)
    state = json.loads(json.dumps(m.get_state()))
    assert state["career"]["counts"] == {"cycles": 4, "chains_closed": 1}
    m.career_counts.update({"cycles": 0, "chains_closed": 0})
    m.load_state(state)
    assert m.career_counts == {"cycles": 4, "chains_closed": 1}


def test_a_fresh_save_has_no_counts_key(game_env):
    assert "career" not in game_env.module.get_state()


def test_a_save_without_counts_loads_as_zero(game_env):
    m = game_env.module
    m.career_counts["cycles"] = 9
    state = m.get_state()
    state["career"].pop("counts")
    m.load_state(state)
    assert m.career_counts == {"cycles": 0, "chains_closed": 0}


@pytest.mark.parametrize("bad", ["x", 5, None, [], {"cycles": -3}, {"cycles": 2.5}, {"cycles": True},
                                 {"cycles": "9"}, {"cycles": 10**9}, {"zzz": 4}])
def test_malformed_counts_load_as_zero(game_env, bad):
    m = game_env.module
    m.career_counts["cycles"] = 9
    state = m.get_state()
    state["career"]["counts"] = bad
    m.load_state(state)
    assert m.career_counts == {"cycles": 0, "chains_closed": 0}


def test_one_bad_count_does_not_drop_the_good_one(game_env):
    m = game_env.module
    m.career_counts["cycles"] = 9
    state = m.get_state()
    state["career"]["counts"] = {"cycles": 12, "chains_closed": "many"}
    m.load_state(state)
    assert m.career_counts == {"cycles": 12, "chains_closed": 0}


def test_nothing_in_the_game_reads_the_rank():
    from pathlib import Path
    source = (Path(__file__).resolve().parent.parent / "game.py").read_text(encoding="utf-8")
    for banned in ("def score", "def invest_", "def advance_cycle"):
        body = source.split(banned)[1].split("\n    def ")[0]
        assert "founder" not in body
    for gameplay in ("def exportable_surplus", "def new_extraction_needed", "def imported_supply"):
        assert "founder" not in source.split(gameplay)[1].split("\n    def ")[0]
