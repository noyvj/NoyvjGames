"""K-17: the rewind token."""

import copy

import pytest

import challengerun
import dynasty
import rewind


def test_tokens_come_from_achievements_and_perks_and_used_ones_stay_used():
    ui = {}
    assert rewind.earned_tokens(0) == 0 and rewind.earned_tokens(4) == 0
    assert rewind.earned_tokens(5) == 1 and rewind.earned_tokens(23) == 4
    assert rewind.earned_tokens(5, perk_tokens=2) == 3
    assert rewind.tokens_left(ui, 10) == 2
    rewind.put(ui, {"used": 1})
    assert rewind.tokens_left(ui, 10) == 1
    assert rewind.tokens_left(ui, 0) == 0  # never negative
    assert rewind.earned_tokens("x") == 0 and rewind.earned_tokens(True) == 0


@pytest.mark.parametrize("raw", [None, 3, "x", {"used": -4}, {"used": float("nan")}, {"used": True}, {"used": 10**9}])
def test_hostile_records_clean(raw):
    assert 0 <= rewind.clean(raw)["used"] <= rewind.MAX_USED


def test_the_knowledge_cost_is_a_quarter_with_a_floor_and_never_more_than_you_have():
    assert rewind.knowledge_cost(40) == pytest.approx(10.0)
    assert rewind.knowledge_cost(4) == pytest.approx(2.0)
    assert rewind.knowledge_cost(1) == pytest.approx(1.0)
    assert rewind.knowledge_cost(0) == 0.0
    assert rewind.knowledge_cost(float("nan")) == 0.0 and rewind.knowledge_cost(None) == 0.0


def give_tokens(game_env, n=2):
    game_env.module.campaign.ui[dynasty.KEY] = {
        "earned": 20, "owned": ["hourglass_keepers", "second_hourglass"][:n]
    }


def test_there_is_nothing_to_rewind_before_a_season_has_been_played(game_env):
    give_tokens(game_env)
    button = game_env.elements["rewind-button"]
    game_env.module.render()
    assert button.disabled is True and "play a season first" in button.title
    assert game_env.module.on_rewind() is None
    assert game_env.state.season == 1


def test_rewinding_restores_the_world_and_costs_a_token_and_knowledge(game_env):
    module = game_env.module
    give_tokens(game_env)
    state = game_env.state
    state.resources["knowledge"] = 40.0
    game_env.advance_season()
    before_season = state.season
    state.resources["knowledge"] = 40.0
    module.render()
    button = game_env.elements["rewind-button"]
    assert button.disabled is False and "Rewind (2)" in button.innerText
    assert "Costs 1 token" in button.title
    population_then = module._rewind_snapshot["data"]["current_state"]["city"]["population"]
    button.dispatch("click", None)
    assert state.season == before_season - 1
    assert state.population == population_then
    assert rewind.get(module.campaign.ui)["used"] == 1
    assert "Rewind (1)" in button.innerText
    assert module.sim_speed == 0
    assert any("unwound" in e.text for e in module.chronicle.entries)
    # once only: the snapshot is spent
    assert button.disabled is True


def test_knowledge_is_taken_from_the_restored_store(game_env):
    module = game_env.module
    give_tokens(game_env)
    game_env.state.resources["knowledge"] = 40.0
    game_env.advance_season()
    module.on_rewind()
    # the restored store was 40 (plus nothing made yet); a quarter is gone
    assert game_env.state.resources["knowledge"] == pytest.approx(30.0, abs=0.01)


def test_no_tokens_means_no_rewind(game_env):
    module = game_env.module
    game_env.advance_season()
    module.render()
    assert game_env.elements["rewind-button"].disabled is True
    assert "No rewind tokens" in game_env.elements["rewind-button"].title
    season = game_env.state.season
    module.on_rewind()
    assert game_env.state.season == season


def test_rewind_rests_in_a_challenge_run(game_env):
    module = game_env.module
    give_tokens(game_env)
    module._challenge_utc_today_override = "2026-10-08"
    game_env.elements["challenge-toggle-button"].dispatch("click", None)
    game_env.elements["challenge-daily-start-button"].dispatch("click", None)
    assert challengerun.get(module.campaign.ui) is not None
    game_env.advance_season()
    module.render()
    assert game_env.elements["rewind-button"].disabled is True
    assert "comparable" in game_env.elements["rewind-button"].title


def test_a_rewound_settlement_cannot_bank_the_same_points_twice(game_env):
    module = game_env.module
    give_tokens(game_env)
    state = game_env.state
    state.season = 79
    game_env.advance_season()          # season 80 now; the snapshot is season 79
    state.population = 15
    module.on_dynasty_bank()
    banked = dynasty.get(module.campaign.ui)["earned"]
    run_banked = dynasty.get_run(module.campaign.ui)["banked"]
    assert banked > 20 and run_banked > 0
    module.on_rewind()
    assert state.season == 79
    assert dynasty.get(module.campaign.ui)["earned"] == banked
    assert dynasty.get_run(module.campaign.ui)["banked"] >= run_banked
    module.on_dynasty_bank()
    assert dynasty.get(module.campaign.ui)["earned"] == banked


def test_an_era_change_or_a_load_invalidates_the_snapshot(game_env):
    module = game_env.module
    give_tokens(game_env)
    game_env.advance_season()
    assert module._rewind_snapshot is not None
    module.load_state(module.get_state())
    assert module._rewind_snapshot is None


def test_refusals_never_raise_on_junk():
    class C:
        revisiting = None

        class state:
            era = "tribal"
            season = 3

    assert rewind.refusal(None, C, 1, False)
    assert rewind.refusal({"data": 5}, C, 1, False)
    assert rewind.refusal({"data": {}, "era": "agrarian", "season": 2}, C, 1, False)
    assert rewind.refusal({"data": {}, "era": "tribal", "season": 2}, C, 1, False) == ""
    assert rewind.preview(None, C, 0, False)


def test_a_snapshot_is_a_deep_copy(game_env):
    module = game_env.module
    snap = rewind.capture(module.campaign)
    before = copy.deepcopy(snap)
    game_env.state.resources["food"] += 50
    module.campaign.ui["x"] = 1
    assert snap == before
