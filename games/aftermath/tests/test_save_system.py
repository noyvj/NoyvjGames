"""Shared save widget contract (SAVE-BUTTON-INTEGRATION.md): get_state()/
load_state() cover Aftermath's in-memory *per-run* state (the current
RunState) only. The persistent skill tree, run_history, and legacy_events
are a separate, already-working localStorage-backed persistence mechanism
(see CLAUDE.md's Tech notes) and are deliberately excluded from this
round trip.
"""


def test_get_state_includes_every_expected_key(game_env):
    data = game_env.module.get_state()
    assert set(data.keys()) == {
        "run_number",
        "event_index",
        "resources",
        "resilience_capacity",
        "growth_capacity",
        "damage_taken",
        "event_log",
    }


def test_get_state_deep_copies_event_log(game_env):
    game_env.invest_resilience()
    game_env.resolve_event()
    data = game_env.module.get_state()
    assert data["event_log"] == game_env.run.event_log
    assert data["event_log"] is not game_env.run.event_log

    # Mutating the live run's event log afterward must not retroactively
    # change the already-taken snapshot.
    game_env.run.event_log.append({"type": "flood", "damage": 999.0, "severity": 1.0})
    assert data["event_log"] != game_env.run.event_log


def test_load_state_full_round_trip_restores_every_field(game_env):
    """Save mid-run, diverge significantly, then load — every piece of
    in-memory run state (not just one field) must come back exactly."""
    game_env.invest_resilience()
    game_env.invest_growth()
    game_env.resolve_event()
    game_env.resolve_event()
    snapshot = game_env.module.get_state()
    assert snapshot["event_index"] == 2
    assert len(snapshot["event_log"]) == 2

    # Diverge: resolve more events and invest further so every tracked
    # field differs from the snapshot.
    game_env.invest_resilience()
    game_env.resolve_event()
    diverged_run = game_env.run
    assert diverged_run.event_index == 3
    assert len(diverged_run.event_log) == 3
    assert diverged_run.resilience_capacity == snapshot["resilience_capacity"] + 1

    result = game_env.module.load_state(snapshot)
    assert result is True

    restored = game_env.run
    assert restored.run_number == snapshot["run_number"]
    assert restored.event_index == snapshot["event_index"]
    assert restored.resources == snapshot["resources"]
    assert restored.resilience_capacity == snapshot["resilience_capacity"]
    assert restored.growth_capacity == snapshot["growth_capacity"]
    assert restored.damage_taken == snapshot["damage_taken"]
    assert restored.event_log == snapshot["event_log"]


def test_load_state_updates_the_rendered_display(game_env):
    game_env.invest_resilience()
    game_env.resolve_event()
    snapshot = game_env.module.get_state()

    game_env.resolve_event()
    game_env.resolve_event()
    assert "Event 4" in game_env.elements["progress-display"].innerText

    game_env.module.load_state(snapshot)
    assert "Event 2" in game_env.elements["progress-display"].innerText
    assert game_env.elements["resources-display"].innerText == (
        f"Resources: {snapshot['resources']:.0f}"
    )


def test_load_state_event_log_is_independent_of_the_saved_dict(game_env):
    """Loading must copy event_log rather than alias the passed-in dict,
    so further play doesn't mutate a snapshot the caller might reuse
    (e.g. the shared widget re-POSTing the same dict)."""
    game_env.invest_resilience()
    game_env.resolve_event()
    snapshot = game_env.module.get_state()

    game_env.module.load_state(snapshot)
    game_env.resolve_event()

    assert len(game_env.run.event_log) == 2
    assert len(snapshot["event_log"]) == 1


def test_load_state_on_a_completed_run_round_trips_correctly(game_env):
    """A save taken right as the run completes (skill tree/history already
    updated as a side effect of resolve_next_event) must still restore the
    run itself correctly even though skill tree/history aren't part of the
    save."""
    for _ in range(len(game_env.module.EVENT_SCHEDULE)):
        game_env.resolve_event()
    assert game_env.run.is_complete()
    snapshot = game_env.module.get_state()

    game_env.start_new_run()
    assert game_env.run.run_number == 2
    assert not game_env.run.is_complete()

    game_env.module.load_state(snapshot)
    assert game_env.run.is_complete()
    assert game_env.run.run_number == snapshot["run_number"]
    assert game_env.run.event_log == snapshot["event_log"]


def test_load_state_does_not_touch_the_persistent_skill_tree_or_history(game_env):
    """Scope boundary check: load_state() must only ever replace `run`,
    never the separately-persisted skill_tree/run_history/legacy_events
    globals."""
    game_env.module.skill_tree.knowledge_points = 42
    game_env.module.skill_tree.unlocked.add("community_reserves")
    history_before = list(game_env.run_history)

    game_env.resolve_event()
    snapshot = game_env.module.get_state()
    game_env.module.load_state(snapshot)

    assert game_env.module.skill_tree.knowledge_points == 42
    assert "community_reserves" in game_env.module.skill_tree.unlocked
    assert game_env.run_history == history_before


def test_reloading_a_stale_pre_completion_save_does_not_double_award(game_env):
    """Real exploit this two-persistence-layer setup makes possible: the
    save widget lets a player save mid-run (one event before completion),
    keep playing to a normal completion (awarding knowledge points/history
    once, as usual), and then reload that same still-visible save code
    afterward -- since the save widget only overwrites a remembered code
    when the player saves *again*, an old code stays loadable long after
    the run it snapshotted has since completed for real. Resolving the
    final event a second time off that reloaded snapshot must not award a
    second time -- run completion is a one-time event per run_number, not
    per resolve_next_event() call that happens to cross the finish line."""
    schedule_length = len(game_env.module.EVENT_SCHEDULE)
    for _ in range(schedule_length - 1):
        game_env.resolve_event()
    stale_snapshot = game_env.module.get_state()  # one event left, not complete

    game_env.resolve_event()  # completes the run normally
    assert game_env.run.is_complete()
    knowledge_after_first_completion = game_env.skill_tree.knowledge_points
    history_after_first_completion = list(game_env.run_history)
    legacy_after_first_completion = set(game_env.module.legacy_events)

    game_env.module.load_state(stale_snapshot)
    assert not game_env.run.is_complete()
    game_env.resolve_event()  # "completes" it again from the stale save
    assert game_env.run.is_complete()

    assert game_env.skill_tree.knowledge_points == knowledge_after_first_completion
    assert game_env.run_history == history_after_first_completion
    assert game_env.module.legacy_events == legacy_after_first_completion


def test_completing_further_runs_after_a_stale_reload_still_awards_normally(game_env):
    """The double-award guard must be scoped to "this exact run_number has
    already been awarded," not "no further runs can ever be awarded" --
    starting and completing a genuinely new run afterward must still work."""
    schedule_length = len(game_env.module.EVENT_SCHEDULE)
    for _ in range(schedule_length - 1):
        game_env.resolve_event()
    stale_snapshot = game_env.module.get_state()

    game_env.resolve_event()  # completes run 1 normally
    game_env.module.load_state(stale_snapshot)
    game_env.resolve_event()  # stale re-completion of run 1, must be ignored
    knowledge_before_run_two = game_env.skill_tree.knowledge_points
    history_len_before_run_two = len(game_env.run_history)

    game_env.start_new_run()
    assert game_env.run.run_number == 2
    for _ in range(schedule_length):
        game_env.resolve_event()

    assert game_env.skill_tree.knowledge_points > knowledge_before_run_two
    assert len(game_env.run_history) == history_len_before_run_two + 1


def test_starting_a_new_run_after_a_stale_reload_never_reuses_an_awarded_run_number(game_env):
    """A second, subtler consequence of the same two-persistence-layer setup:
    start_new_run() used to derive the new run_number purely from the
    *current* (possibly reloaded-and-stale) RunState's own run_number + 1.
    Loading an old, still-incomplete save (nothing exploitative -- just
    resuming an earlier snapshot) and then starting a new run from it could
    therefore hand out a run_number that a *later* run had already completed
    and been awarded for in the meantime. That collision silently blocks the
    high-water-mark guard from ever awarding the genuinely new run -- a
    legitimate playthrough that had never been rewarded before completes
    with no payout and no error. start_new_run() must pick a run_number
    that has never been awarded, regardless of what stale snapshot happens
    to be loaded when it's called."""
    schedule_length = len(game_env.module.EVENT_SCHEDULE)

    for _ in range(schedule_length):
        game_env.resolve_event()  # completes run 1

    game_env.start_new_run()  # run 2
    early_run2_snapshot = game_env.module.get_state()  # before any events
    for _ in range(schedule_length):
        game_env.resolve_event()  # completes run 2

    game_env.start_new_run()  # run 3
    for _ in range(schedule_length):
        game_env.resolve_event()  # completes run 3

    knowledge_before = game_env.skill_tree.knowledge_points
    history_len_before = len(game_env.run_history)

    game_env.module.load_state(early_run2_snapshot)  # stale, incomplete run 2
    game_env.start_new_run()  # must not reuse run_number 3 (already awarded)

    for _ in range(schedule_length):
        game_env.resolve_event()  # completes this genuinely new run

    assert game_env.skill_tree.knowledge_points > knowledge_before
    assert len(game_env.run_history) == history_len_before + 1
