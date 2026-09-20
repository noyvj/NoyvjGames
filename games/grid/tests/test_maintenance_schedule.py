"""C23 (planning/TODO.md "Per-game: Grid"): a per-plant-type auto-maintain
cadence <select>, sitting alongside each plant row's own Build/Retire/
Maintain buttons. The GridState methods themselves (`set_maintenance_
schedule()`/`_run_scheduled_maintenance()`, wired into `advance_round()`)
landed in the C7/C17/C19 round-3 pass as backend-only; this pass adds the
missing UI and its own first test coverage -- neither the backend methods
nor the UI existed in any test file before this one."""


def test_schedule_select_disabled_until_a_plant_of_that_type_exists(game_env):
    select = game_env.elements["solar-maintenance-schedule-select"]
    assert select.disabled is True

    game_env.build("solar")
    game_env.module.render()
    assert select.disabled is False


def test_selecting_an_interval_updates_state_and_is_rejected_when_invalid(game_env):
    state = game_env.state
    game_env.build("solar")

    game_env.set_maintenance_schedule("solar", 5)
    assert state.maintenance_schedule["solar"] == 5

    # An interval outside MAINTENANCE_SCHEDULE_OPTIONS is rejected outright
    # rather than silently clamped -- the <select> only ever offers valid
    # options, so this only matters for a direct/malformed call.
    assert state.set_maintenance_schedule("solar", 4) is False
    assert state.maintenance_schedule["solar"] == 5


def test_select_value_stays_in_sync_with_state_after_a_change(game_env):
    game_env.build("solar")
    game_env.set_maintenance_schedule("solar", 8)
    assert game_env.elements["solar-maintenance-schedule-select"].value == "8"


def test_manual_only_is_the_default_and_never_auto_maintains(game_env):
    state = game_env.state
    game_env.build("coal")
    baseline_age = state.plant_age["coal"]
    for _ in range(10):
        state.plant_age["coal"] += 1
        game_env.advance_round()

    # Manual-only (the default, interval 0): nothing in advance_round's
    # own aging path ever calls maintain_plant() on its own.
    assert state.maintenance_actions_count == 0
    assert state.plant_age["coal"] > baseline_age


def test_scheduled_maintenance_fires_on_the_configured_interval(game_env):
    state = game_env.state
    state.funds = 100_000
    game_env.build("coal")
    game_env.set_maintenance_schedule("coal", 3)

    for _ in range(2):
        game_env.advance_round()
    assert state.maintenance_actions_count == 0

    game_env.advance_round()
    assert state.maintenance_actions_count == 1


def test_scheduled_maintenance_is_skipped_when_unaffordable(game_env):
    """_run_scheduled_maintenance() is documented as best-effort -- a type
    whose schedule fires but can't afford it this round is silently
    skipped, same as a manual Maintain click would be."""
    state = game_env.state
    game_env.build("coal")
    game_env.set_maintenance_schedule("coal", 3)

    for _ in range(3):
        # Pinned to 0 every round (rather than once, before the loop) so
        # rounds 1-2's own revenue can't quietly refill it before the
        # interval-3 schedule actually fires on round 3.
        state.funds = 0.0
        game_env.advance_round()

    assert state.maintenance_actions_count == 0


def test_retiring_the_last_plant_of_a_type_does_not_crash_a_pending_schedule(game_env):
    """A schedule survives a plant type dropping to zero -- _run_scheduled_
    maintenance() already guards on plant_counts[plant_type] <= 0, so this
    pins that a stale non-zero schedule on an empty type is inert, not an
    error."""
    state = game_env.state
    game_env.build("coal")
    game_env.set_maintenance_schedule("coal", 3)
    game_env.retire("coal")

    for _ in range(3):
        game_env.advance_round()

    assert state.maintenance_actions_count == 0
    assert state.maintenance_schedule["coal"] == 3
