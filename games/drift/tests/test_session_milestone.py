"""I11: a periodic (every SESSION_MILESTONE_INTERVAL rounds) session-
milestone summary -- a frozen snapshot of headline stats taken at that
checkpoint, not a live-updating readout.
"""


def test_hidden_before_the_first_interval_completes(game_env):
    for _ in range(19):
        game_env.advance_round()
    assert game_env.region.last_milestone_round is None
    assert game_env.elements["session-milestone-display"].hidden is True


def test_shown_once_the_interval_completes(game_env):
    interval = game_env.module.SESSION_MILESTONE_INTERVAL
    for _ in range(interval):
        game_env.advance_round()
    region = game_env.region
    assert region.last_milestone_round == interval
    display = game_env.elements["session-milestone-display"]
    assert display.hidden is False
    assert f"round {interval}" in display.innerText


def test_pulses_the_moment_a_new_snapshot_lands(game_env):
    interval = game_env.module.SESSION_MILESTONE_INTERVAL
    for _ in range(interval):
        game_env.advance_round()
    display = game_env.elements["session-milestone-display"]
    assert "session-milestone--pulse" in display.classList
    # Consumed -- the transient flag must not still be set after render().
    assert game_env.region.milestone_just_updated is False


def test_snapshot_stays_frozen_between_milestones(game_env):
    interval = game_env.module.SESSION_MILESTONE_INTERVAL
    for _ in range(interval):
        game_env.advance_round()
    first_text = game_env.elements["session-milestone-display"].innerText

    game_env.invest("housing")
    game_env.advance_round()  # one round past the milestone, state keeps changing
    second_text = game_env.elements["session-milestone-display"].innerText
    assert second_text == first_text


def test_snapshot_updates_at_the_next_interval(game_env):
    interval = game_env.module.SESSION_MILESTONE_INTERVAL
    for _ in range(interval * 2):
        game_env.advance_round()
    region = game_env.region
    assert region.last_milestone_round == interval * 2
    assert f"round {interval * 2}" in game_env.elements["session-milestone-display"].innerText


def test_snapshot_round_trips_through_save_and_load(game_env):
    interval = game_env.module.SESSION_MILESTONE_INTERVAL
    for _ in range(interval):
        game_env.advance_round()
    data = game_env.module.get_state()
    assert data["last_milestone_round"] == interval
    assert data["last_milestone_snapshot"] is not None

    game_env.region.last_milestone_round = None
    game_env.region.last_milestone_snapshot = None
    game_env.module.load_state(data)
    assert game_env.region.last_milestone_round == interval
    assert game_env.region.last_milestone_snapshot is not None
