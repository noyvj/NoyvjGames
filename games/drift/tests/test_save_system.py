"""SAVE-BUTTON-INTEGRATION.md contract: get_state()/load_state() package
every module-level mutable global into a JSON-safe dict and back, so the
shared shared/save-widget.js can save/load Drift's progress the same way
it does for every other game. Drift has no bespoke serialize_state()/
deserialize_state() (unlike SOL's pre-existing bridge) -- get_state()/
load_state() are the only save-system functions this game defines.
"""


ALL_STATE_KEYS = {
    "round_number",
    "funds",
    "capacity",
    "background_severity",
    "total_arrivals",
    "arrivals_log",
    "strain_log",
    "wellbeing_log",
    "integrated_population",
    "cumulative_services_investment",
    "cumulative_integration_contribution",
    "net_positive_round",
    "current_stable_streak",
    "best_stable_streak",
    "thriving_round",
    "coda_ever_viewed",
    "last_milestone_round",
    "last_milestone_snapshot",
    "accelerated_severity_enabled",
    "coda_visible",
    "info_page_open",
    "achievements_earned",
    "subscore_log",
    "region_name",
    "coda_legacy_choice",
    "crisis_start_enabled",
}


def test_get_state_includes_every_expected_key(game_env):
    data = game_env.module.get_state()
    assert set(data.keys()) == ALL_STATE_KEYS


def test_get_state_matches_live_region_values(game_env):
    game_env.region.invest("housing")
    game_env.advance_round()
    data = game_env.module.get_state()
    assert data["round_number"] == game_env.region.round_number
    assert data["funds"] == game_env.region.funds
    assert data["capacity"] == game_env.region.capacity
    assert data["total_arrivals"] == game_env.region.total_arrivals


def test_get_state_deep_copies_capacity_so_saved_snapshot_is_not_aliased(game_env):
    data = game_env.module.get_state()
    data["capacity"]["housing"] = 9999.0
    assert game_env.region.capacity["housing"] != 9999.0


def test_get_state_deep_copies_logs_so_saved_snapshot_is_not_aliased(game_env):
    game_env.advance_round()
    data = game_env.module.get_state()
    data["arrivals_log"].append(9999.0)
    data["strain_log"].append(9999.0)
    assert 9999.0 not in game_env.region.arrivals_log
    assert 9999.0 not in game_env.region.strain_log


def test_load_state_full_round_trip_restores_every_tracked_field(game_env):
    """Save -> diverge -> load must restore every piece of state, not
    just one field -- including the Iteration Pass 3 turning-point
    tracking fields (cumulative_services_investment,
    cumulative_integration_contribution, net_positive_round)."""
    game_env.region.invest("services")  # cumulative_services_investment = 20
    game_env.region.total_arrivals = 50.0
    for _ in range(4):
        game_env.advance_round()
    # By here the region has crossed to net-positive (see
    # test_iteration_pass_3.py's equivalent scenario).
    assert game_env.region.has_crossed_to_net_positive() is True

    game_env.region.invest("housing")
    game_env.module.on_toggle_coda()
    game_env.module.on_toggle_info_page()

    snapshot = game_env.module.get_state()

    # Diverge from the snapshot in every dimension it covers.
    game_env.region.invest("infrastructure")
    game_env.advance_round()
    game_env.module.on_toggle_coda()
    game_env.module.on_toggle_info_page()
    assert game_env.module.get_state() != snapshot

    result = game_env.module.load_state(snapshot)
    assert result is True

    restored = game_env.module.get_state()
    assert restored == snapshot
    assert game_env.region.round_number == snapshot["round_number"]
    assert game_env.region.funds == snapshot["funds"]
    assert game_env.region.capacity == snapshot["capacity"]
    assert game_env.region.background_severity == snapshot["background_severity"]
    assert game_env.region.total_arrivals == snapshot["total_arrivals"]
    assert game_env.region.arrivals_log == snapshot["arrivals_log"]
    assert game_env.region.strain_log == snapshot["strain_log"]
    assert game_env.region.integrated_population == snapshot["integrated_population"]
    assert (
        game_env.region.cumulative_services_investment
        == snapshot["cumulative_services_investment"]
    )
    assert (
        game_env.region.cumulative_integration_contribution
        == snapshot["cumulative_integration_contribution"]
    )
    assert game_env.region.net_positive_round == snapshot["net_positive_round"]
    assert game_env.module.coda_visible == snapshot["coda_visible"]
    assert game_env.module.info_page_open == snapshot["info_page_open"]


def test_load_state_restores_pre_turning_point_snapshot_as_not_net_positive(game_env):
    """The inverse case: loading a snapshot taken *before* the turning
    point must not leave the region incorrectly marked net-positive."""
    game_env.region.invest("housing")
    snapshot = game_env.module.get_state()
    assert snapshot["net_positive_round"] is None

    game_env.region.invest("services")
    game_env.region.total_arrivals = 50.0
    for _ in range(4):
        game_env.advance_round()
    assert game_env.region.has_crossed_to_net_positive() is True

    game_env.module.load_state(snapshot)
    assert game_env.region.net_positive_round is None
    assert game_env.region.has_crossed_to_net_positive() is False


def test_load_state_deep_copies_capacity_so_live_state_is_not_aliased(game_env):
    snapshot = game_env.module.get_state()
    game_env.module.load_state(snapshot)
    game_env.region.capacity["housing"] = 9999.0
    assert snapshot["capacity"]["housing"] != 9999.0


def test_load_state_re_renders_the_ui(game_env):
    game_env.region.invest("housing")
    game_env.advance_round()
    snapshot = game_env.module.get_state()

    game_env.region.invest("housing")
    game_env.advance_round()

    game_env.module.load_state(snapshot)
    assert game_env.elements["round-display"].innerText == (
        f"Round {snapshot['round_number']}"
    )
    assert game_env.elements["funds-display"].innerText == (
        f"Funds: {snapshot['funds']:.0f}"
    )


def test_load_state_returns_true(game_env):
    snapshot = game_env.module.get_state()
    assert game_env.module.load_state(snapshot) is True


def test_load_state_with_capacity_missing_a_key_does_not_crash_next_render(game_env):
    """capacity's key set (housing/services/infrastructure) belongs to
    CAPACITY_TYPES in game.py, not to the save -- a save missing one of
    those keys (an older save format from before a capacity type existed,
    or a hand-edited/corrupted payload) must not wipe that type out of
    the live dict entirely. total_capacity() and render() both do
    `region.capacity[t]` for every `t in CAPACITY_TYPES` unconditionally,
    so a wholesale dict replace would crash on the very next render."""
    game_env.region.invest("infrastructure")
    snapshot = game_env.module.get_state()
    del snapshot["capacity"]["infrastructure"]

    result = game_env.module.load_state(snapshot)

    assert result is True
    assert game_env.region.capacity["infrastructure"] == 6.0
    assert game_env.region.total_capacity() == 6.0


def test_load_state_missing_top_level_key_does_not_crash(game_env):
    """Every non-capacity field in load_state() used bare `data["key"]`
    indexing -- a save from an older version of the game missing any one
    of those fields entirely (e.g. a save written before Iteration Pass
    3 added cumulative_services_investment/
    cumulative_integration_contribution/net_positive_round, or before
    the info-page feature added info_page_open) would KeyError
    immediately instead of loading gracefully, the same bug shape the
    capacity dict already had to be protected from above."""
    game_env.region.invest("housing")
    snapshot = game_env.module.get_state()
    del snapshot["cumulative_services_investment"]
    del snapshot["net_positive_round"]
    del snapshot["info_page_open"]

    result = game_env.module.load_state(snapshot)

    assert result is True
    # Every other field from the still-mostly-intact snapshot still
    # restores normally.
    assert game_env.region.round_number == snapshot["round_number"]
    assert game_env.region.funds == snapshot["funds"]
    assert game_env.region.capacity == snapshot["capacity"]


def test_load_state_missing_net_positive_round_falls_back_to_live_value(game_env):
    """A missing top-level key should fall back to whatever the live
    region already has, not silently reset to some hardcoded default --
    the same graceful-degradation contract capacity's per-key merge
    already provides."""
    game_env.region.invest("services")
    game_env.region.total_arrivals = 50.0
    for _ in range(4):
        game_env.advance_round()
    assert game_env.region.has_crossed_to_net_positive() is True
    live_net_positive_round = game_env.region.net_positive_round

    snapshot = game_env.module.get_state()
    del snapshot["net_positive_round"]

    result = game_env.module.load_state(snapshot)

    assert result is True
    assert game_env.region.net_positive_round == live_net_positive_round


def test_load_state_rejects_non_dict_payload(game_env):
    """A corrupted/malformed save payload (not even a dict) must not
    crash load_state() -- it should fail gracefully instead."""
    assert game_env.module.load_state("not a dict") is False
    assert game_env.module.load_state(None) is False
