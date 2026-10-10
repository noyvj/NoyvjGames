"""GB-17: challenge runs (Pacifist, Scorched Start, Sprint, No-Highland), each with a badge."""

import json

import pytest

from .gb_helpers import advance_to, toast_text


def start(env, challenge, **kwargs):
    assert env.module.reset_session(challenge=challenge, **kwargs) is True
    return env.module


def run_until_done(env, limit=200):
    m = env.module
    for _ in range(limit):
        if m.challenge_complete_tick is not None:
            break
        env.tick()
    return m.challenge_complete_tick


# --- the catalogue --------------------------------------------------------------------------------------------

def test_there_are_exactly_four_challenges_each_with_a_matching_achievement(game_env):
    m = game_env.module
    assert set(m.CHALLENGE_SPECS) == {"pacifist", "scorched", "sprint", "no_highland"}
    ids = {a["id"] for a in m.ACHIEVEMENTS}
    for spec in m.CHALLENGE_SPECS.values():
        assert spec["achievement"] in ids and spec["achievement"] in m.ACHIEVEMENT_CHECKS


def test_unknown_challenge_is_refused_and_leaves_the_session_alone(game_env):
    m = game_env.module
    game_env.tick(3)
    assert m.reset_session(challenge="nonsense") is False
    assert m.current_challenge == m.CHALLENGE_NONE and m.forest_tick == 3


def test_no_challenge_means_no_status_and_no_state(game_env):
    m = game_env.module
    assert m.challenge_state() is None
    assert m.challenge_status_text() == ""
    assert game_env.elements["challenge-status"].hidden is True
    assert "challenge" not in m.get_state()


# --- Pacifist -------------------------------------------------------------------------------------------------

def test_pacifist_is_won_by_leaving_the_forest_alone(game_env):
    m = start(game_env, "pacifist")
    goal, income_goal = m.challenge_goal()
    assert goal == m.CHALLENGE_PACIFIST_STANDING_PER_PLOT * 36 and income_goal == 0
    assert m.challenge_state() == m.CHALLENGE_ACTIVE
    done = run_until_done(game_env)
    assert done is not None and done == m.forest_tick
    assert m.challenge_state() == m.CHALLENGE_COMPLETE
    assert m.standing_forest_value() >= goal


def test_pacifist_fails_on_a_clear_and_a_granted_request_counts_too(game_env):
    m = start(game_env, "pacifist")
    game_env.tick(2)
    game_env.select(5)
    game_env.clear()
    assert m.challenge_state() == m.CHALLENGE_FAILED
    assert "Failed" in m.challenge_status_text()
    # a failed run can never complete, however high the forest grows
    game_env.tick(60)
    assert m.challenge_complete_tick is None

    start(game_env, "pacifist")
    game_env.tick(2)
    m.pending_stakeholder_request = {"plot_index": 3, "reason": "housing", "kind": "clear"}
    game_env.grant_stakeholder()
    assert m.challenge_state() == m.CHALLENGE_FAILED


def test_an_undone_clear_does_not_fail_pacifist(game_env):
    m = start(game_env, "pacifist")
    game_env.tick(2)
    game_env.select(5)
    game_env.clear()
    assert m.challenge_state() == m.CHALLENGE_FAILED
    m.undo_last_clear()
    assert m.challenge_state() == m.CHALLENGE_ACTIVE


def test_pacifist_counts_a_highland_clear_as_failure(game_env):
    m = start(game_env, "pacifist")
    m.highland_plots[0].clear_count = 1
    assert m.challenge_state() == m.CHALLENGE_FAILED


def test_a_completed_pacifist_run_stays_complete_even_if_you_clear_afterwards(game_env):
    m = start(game_env, "pacifist")
    run_until_done(game_env)
    game_env.select(0)
    game_env.clear()
    assert m.challenge_state() == m.CHALLENGE_COMPLETE


# --- Scorched Start -------------------------------------------------------------------------------------------

@pytest.mark.parametrize("size,plots", [("small", 16), ("normal", 36), ("large", 72)])
def test_scorched_start_burns_two_thirds_on_every_grid_size(game_env, size, plots):
    m = start(game_env, "scorched", grid_size=size)
    assert len(m.plots) == plots
    bare = [p for p in m.plots if p.state == m.BARE]
    assert len(bare) == round(plots * 2 / 3)
    assert all(p.value == 0 and p.clear_count == 0 for p in m.plots)  # burned, not cleared: no clear is counted
    assert m._total_clear_count() == 0


def test_scorched_start_is_deterministic_and_does_not_fake_a_clear_achievement(game_env):
    m = start(game_env, "scorched")
    first = [p.state for p in m.plots]
    m.reset_session()
    m.reset_session(challenge="scorched")
    assert [p.state for p in m.plots] == first
    assert "first_clear" not in m.achievement_ids_earned()


def test_scorched_start_can_be_won_by_replanting(game_env):
    m = start(game_env, "scorched")
    for plot in m.plots:
        if plot.state == m.BARE:
            plot.replant()
    done = run_until_done(game_env)
    assert done is not None and m.challenge_state() == m.CHALLENGE_COMPLETE


def test_reset_session_alone_retries_the_same_challenge(game_env):
    m = start(game_env, "scorched")
    game_env.tick(5)
    m.reset_session()
    assert m.current_challenge == "scorched" and m.forest_tick == 0
    assert sum(1 for p in m.plots if p.state == m.BARE) == 24


def test_a_normal_reset_gives_back_an_unburnt_forest(game_env):
    m = start(game_env, "scorched")
    m.reset_session(challenge="none")
    assert all(p.state == m.PRESERVED for p in m.plots) and m.current_challenge == m.CHALLENGE_NONE


# --- Sprint ---------------------------------------------------------------------------------------------------

def test_sprint_needs_income_and_standing_value_inside_the_time_limit(game_env):
    m = start(game_env, "sprint")
    standing, income = m.challenge_goal()
    assert standing == 70 * 36 and income == 28 * 36
    advance_to(game_env, 40)
    for index in range(12):
        game_env.select(index)
        game_env.clear()
    assert m.total_income >= income
    for _ in range(m.CHALLENGE_SPRINT_TICK_LIMIT - 40):
        game_env.tick()
        if m.challenge_complete_tick is not None:
            break
    assert m.challenge_complete_tick is not None and m.challenge_complete_tick <= m.CHALLENGE_SPRINT_TICK_LIMIT
    assert m.challenge_state() == m.CHALLENGE_COMPLETE


def test_sprint_cannot_be_won_by_waiting_and_fails_when_time_runs_out(game_env):
    m = start(game_env, "sprint")
    advance_to(game_env, m.CHALLENGE_SPRINT_TICK_LIMIT)
    assert m.challenge_state() == m.CHALLENGE_ACTIVE
    assert "ticks left" in m.challenge_status_text()
    game_env.tick()
    assert m.challenge_state() == m.CHALLENGE_FAILED
    game_env.tick(30)
    assert m.challenge_complete_tick is None


def test_sprint_goal_scales_with_the_grid(game_env):
    m = start(game_env, "sprint", grid_size="small")
    assert m.challenge_goal() == (70 * 16, 28 * 16)


# --- No-Highland ----------------------------------------------------------------------------------------------

def test_no_highland_keeps_both_regions_sealed_however_high_the_forest_grows(game_env):
    m = start(game_env, "no_highland")
    for plot in m.plots:
        plot.value = 500.0
    game_env.tick(3)
    assert m.highland_unlocked is False and m.wetland_unlocked is False
    assert "sealed" in game_env.elements["highland-lock-banner"].innerText
    assert game_env.elements["highland-section"].hidden is True


def test_no_highland_completes_without_the_second_growth_achievement(game_env):
    m = start(game_env, "no_highland")
    done = run_until_done(game_env)
    assert done is not None
    earned = m.achievement_ids_earned()
    assert "challenge_no_highland" in earned and "second_growth" not in earned


def test_regions_unlock_normally_outside_the_challenge(game_env):
    m = game_env.module
    for plot in m.plots:
        plot.value = 500.0
    game_env.tick()
    assert m.highland_unlocked is True


# --- completion effects ---------------------------------------------------------------------------------------

def test_finishing_a_challenge_logs_toasts_earns_its_achievement_and_records_the_best(game_env):
    m = start(game_env, "pacifist")
    run_until_done(game_env)
    done = m.challenge_complete_tick
    assert any(e["kind"] == "challenge" and "Pacifist" in e["text"] for e in m.forest_log)
    assert "challenge_pacifist" in m.achievement_ids_earned()
    assert "Pacifist" in toast_text(game_env)
    stored = json.loads(game_env.local_storage.getItem(m.CHALLENGE_RECORDS_STORAGE_KEY))
    assert stored == {"pacifist": done}
    assert "badge earned" in m.challenge_status_text()
    assert "challenge-status--complete" in game_env.elements["challenge-status"].classList._classes


def test_the_fastest_finish_is_kept_and_a_slower_one_never_replaces_it(game_env):
    m = game_env.module
    game_env.local_storage.setItem(m.CHALLENGE_RECORDS_STORAGE_KEY, json.dumps({"pacifist": 5}))
    m._challenge_record_cache = None
    start(game_env, "pacifist")
    run_until_done(game_env)
    assert json.loads(game_env.local_storage.getItem(m.CHALLENGE_RECORDS_STORAGE_KEY))["pacifist"] == 5
    assert "fastest finish: 5 ticks" in m.challenge_status_text()


def test_badges_outlive_the_session_and_show_in_the_almanac(game_env):
    m = start(game_env, "pacifist")
    run_until_done(game_env)
    m.reset_session(challenge="none")
    assert m.challenge_badge_earned("pacifist") is True and m.challenge_badge_earned("sprint") is False
    game_env.toggle_almanac()
    panel = game_env.elements["almanac-panel"]
    headings = [c.innerText for c in panel.children if c.className == "almanac-heading"]
    assert "Challenge badges (1/4)" in headings
    assert "challenge_pacifist" in m.achievement_ids_earned()  # GN-1: earned achievements are kept for the whole game


def test_corrupt_challenge_records_are_ignored(game_env):
    m = game_env.module
    for junk in ("not json", "[1, 2]", json.dumps({"pacifist": "fast", "sprint": -4, "bogus": 3, "scorched": True})):
        game_env.local_storage.setItem(m.CHALLENGE_RECORDS_STORAGE_KEY, junk)
        m._challenge_record_cache = None
        assert m.load_challenge_records() == {}


# --- UI wiring and selects -------------------------------------------------------------------------------------

def test_the_challenge_select_resets_the_session_into_the_challenge(game_env):
    m = game_env.module
    game_env.tick(3)
    game_env.select(0)
    game_env.clear()
    game_env.change_challenge("sprint")
    assert m.current_challenge == "sprint" and m.forest_tick == 0 and m._total_clear_count() == 0
    assert game_env.elements["challenge-select"].value == "sprint"
    status = game_env.elements["challenge-status"]
    assert status.hidden is False and "Sprint" in status.innerText and "within 60 ticks" in status.innerText
    game_env.change_challenge("none")
    assert m.current_challenge == m.CHALLENGE_NONE and game_env.elements["challenge-status"].hidden is True


def test_status_text_shows_progress_toward_the_goal(game_env):
    m = start(game_env, "no_highland")
    game_env.tick(3)
    text = m.challenge_status_text()
    assert "In progress: standing" in text and f"/{100 * 36}" in text


# --- saves ------------------------------------------------------------------------------------------------------

def test_a_challenge_run_survives_a_save_and_load(game_env):
    m = start(game_env, "pacifist")
    run_until_done(game_env)
    snapshot = json.loads(json.dumps(m.get_state()))
    assert snapshot["challenge"] == {"id": "pacifist", "done_tick": m.challenge_complete_tick}
    m.reset_session(challenge="none")
    assert m.current_challenge == m.CHALLENGE_NONE
    m.load_state(snapshot)
    assert m.current_challenge == "pacifist" and m.challenge_state() == m.CHALLENGE_COMPLETE
    assert m.challenge_complete_tick == snapshot["challenge"]["done_tick"]


def test_loading_a_normal_save_into_a_challenge_session_drops_the_challenge(game_env):
    m = game_env.module
    game_env.tick(4)
    snapshot = json.loads(json.dumps(m.get_state()))
    start(game_env, "scorched")
    m.load_state(snapshot)
    assert m.current_challenge == m.CHALLENGE_NONE
    assert all(p.state == m.PRESERVED for p in m.plots)


@pytest.mark.parametrize("junk", [
    "pacifist", 7, None, {"id": "nope"}, {"id": 5}, {"id": ["x"]}, {}, [],
])
def test_a_malformed_challenge_key_loads_as_no_challenge(game_env, junk):
    m = game_env.module
    snapshot = json.loads(json.dumps(m.get_state()))
    snapshot["challenge"] = junk
    m.load_state(snapshot)
    assert m.current_challenge == m.CHALLENGE_NONE and m.challenge_complete_tick is None


@pytest.mark.parametrize("done", ["soon", -3, True, None, 1.5, [1]])
def test_a_malformed_done_tick_is_dropped(game_env, done):
    m = game_env.module
    snapshot = json.loads(json.dumps(m.get_state()))
    snapshot["challenge"] = {"id": "sprint", "done_tick": done}
    m.load_state(snapshot)
    assert m.current_challenge == "sprint" and m.challenge_complete_tick is None
