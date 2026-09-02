"""Shared save widget integration (SAVE-BUTTON-INTEGRATION.md): get_state()
packages every piece of SettlementState into a plain JSON-safe dict, and
load_state() is its exact inverse. Tide has no old bespoke save bridge to
stay backward-compatible with (unlike SOL) — get_state()/load_state() are
the only save/load functions this game has ever had. load_state() still
has to tolerate a malformed payload gracefully, though (a hand-edited save
code, a partial/corrupted one, or simply a future field this build
doesn't know about) rather than crash mid-assignment with the live state
already half-overwritten.
"""


def test_get_state_includes_every_expected_key(game_env):
    data = game_env.module.get_state()
    assert set(data.keys()) == {
        "season",
        "funds",
        "capacity",
        "acidity",
        "acidity_history",
        "sea_level",
        "cumulative_damage",
        "undampened_damage_total",
        "damage_log",
        "ticker_log",
        "trend_flattening_announced",
    }


def test_get_state_deep_copies_capacity_so_a_live_reference_is_not_leaked(game_env):
    data = game_env.module.get_state()
    data["capacity"]["output"] = 999
    assert game_env.state.capacity["output"] == 0


def test_get_state_deep_copies_log_lists_so_a_live_reference_is_not_leaked(game_env):
    game_env.invest("adaptation")  # unlocks nothing yet, but seeds ticker later
    for _ in range(4):
        game_env.advance_season()
    data = game_env.module.get_state()
    assert data["ticker_log"] == game_env.state.ticker_log
    data["ticker_log"].append("tampered")
    data["damage_log"].append(-1)
    data["acidity_history"].append(-1)
    assert "tampered" not in game_env.state.ticker_log
    assert -1 not in game_env.state.damage_log
    assert -1 not in game_env.state.acidity_history


def _play_several_seasons(game_env):
    """Drives enough real play to populate every tracked field: capacity
    in all three categories, acidity history long enough for the fish-
    stock lag to land, an adaptation tier unlock, sea-level damage, and
    ticker entries."""
    for _ in range(4):
        game_env.invest("output")
    for _ in range(3):
        game_env.invest("reduction")
    for _ in range(6):  # crosses the "Seawalls" tier threshold (6)
        game_env.invest("adaptation")
    for _ in range(6):
        game_env.advance_season()


def test_save_diverge_load_round_trip_restores_every_tracked_field(game_env):
    """Full save -> diverge -> load round trip: every piece of state
    get_state() reports must come back exactly as it was at save time,
    not just one field."""
    _play_several_seasons(game_env)
    snapshot = game_env.module.get_state()

    saved_season = game_env.state.season
    saved_funds = game_env.state.funds
    saved_capacity = dict(game_env.state.capacity)
    saved_acidity = game_env.state.acidity
    saved_acidity_history = list(game_env.state.acidity_history)
    saved_sea_level = game_env.state.sea_level
    saved_cumulative_damage = game_env.state.cumulative_damage
    saved_undampened_damage_total = game_env.state.undampened_damage_total
    saved_damage_log = list(game_env.state.damage_log)
    saved_ticker_log = list(game_env.state.ticker_log)
    saved_trend_flag = game_env.state.trend_flattening_announced

    # Diverge significantly from the snapshot.
    game_env.invest("output")
    game_env.invest("reduction")
    for _ in range(3):
        game_env.advance_season()
    assert game_env.state.season != saved_season
    assert game_env.state.capacity != saved_capacity

    result = game_env.module.load_state(snapshot)
    assert result is True

    assert game_env.state.season == saved_season
    assert game_env.state.funds == saved_funds
    assert game_env.state.capacity == saved_capacity
    assert game_env.state.acidity == saved_acidity
    assert game_env.state.acidity_history == saved_acidity_history
    assert game_env.state.sea_level == saved_sea_level
    assert game_env.state.cumulative_damage == saved_cumulative_damage
    assert game_env.state.undampened_damage_total == saved_undampened_damage_total
    assert game_env.state.damage_log == saved_damage_log
    assert game_env.state.ticker_log == saved_ticker_log
    assert game_env.state.trend_flattening_announced == saved_trend_flag


def test_load_state_re_renders_so_the_ui_reflects_the_loaded_state(game_env):
    _play_several_seasons(game_env)
    snapshot = game_env.module.get_state()
    saved_season_text = game_env.elements["season-display"].innerText

    game_env.advance_season()
    assert game_env.elements["season-display"].innerText != saved_season_text

    game_env.module.load_state(snapshot)
    assert game_env.elements["season-display"].innerText == saved_season_text


def test_load_state_restores_capacity_as_a_plain_dict_not_a_shared_reference(game_env):
    _play_several_seasons(game_env)
    snapshot = game_env.module.get_state()

    game_env.module.load_state(snapshot)
    game_env.state.capacity["output"] += 1
    assert snapshot["capacity"]["output"] != game_env.state.capacity["output"]


def test_load_state_restores_ticker_log_as_a_plain_list_not_a_shared_reference(game_env):
    _play_several_seasons(game_env)
    snapshot = game_env.module.get_state()

    game_env.module.load_state(snapshot)
    game_env.state.ticker_log.append("post-load entry")
    assert "post-load entry" not in snapshot["ticker_log"]


def test_load_state_with_a_missing_field_does_not_half_overwrite_live_state(game_env):
    """A save dict missing one key (hand-edited, truncated in transit, or
    just from a future/older build with a different field set) must not
    take the whole load down partway through — and must especially not
    leave live state with *some* fields already overwritten from the save
    and others still at their pre-load values, which is worse than either
    a clean success or a clean failure."""
    _play_several_seasons(game_env)
    snapshot = game_env.module.get_state()
    del snapshot["trend_flattening_announced"]

    game_env.invest("output")
    game_env.advance_season()
    game_env.advance_season()
    live_season_before = game_env.state.season
    live_funds_before = game_env.state.funds

    game_env.module.load_state(snapshot)

    # Either the load restored everything it could (season/funds moved to
    # the snapshot's values) or it left the pre-load state alone entirely —
    # but it must not do the former for some fields and the latter for
    # others.
    season_was_restored = game_env.state.season == snapshot["season"]
    funds_was_restored = game_env.state.funds == snapshot["funds"]
    assert season_was_restored == funds_was_restored
    if not season_was_restored:
        assert game_env.state.season == live_season_before
        assert game_env.state.funds == live_funds_before


def test_load_state_rejects_non_dict_payload_without_raising(game_env):
    _play_several_seasons(game_env)
    live_season_before = game_env.state.season

    result = game_env.module.load_state("not a dict")

    assert result is False
    assert game_env.state.season == live_season_before


def test_load_state_merges_capacity_key_by_key_rather_than_wholesale_replacing(game_env):
    """capacity's key set belongs to CATEGORIES, not to the save. A save
    missing a category (an older or hand-edited payload) must not wipe
    that category out of the live dict entirely -- render() and every
    invest-cost/capacity lookup index state.capacity[category]
    unconditionally for every category in CATEGORIES, so a missing key
    would crash the next render/investment, not just look wrong."""
    _play_several_seasons(game_env)
    snapshot = game_env.module.get_state()
    del snapshot["capacity"]["adaptation"]

    game_env.module.load_state(snapshot)

    assert "adaptation" in game_env.state.capacity
    assert isinstance(game_env.state.capacity["adaptation"], int)
