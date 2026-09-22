"""Tide's own achievements catalog (planning/ACHIEVEMENTS-SYSTEM-DESIGN.md,
"roll achievements out everywhere" in planning/TODO.md's per-game Tide
section). SOL is the reference integration; this exercises the same shape
against Tide's real mechanics (output/reduction/adaptation investment, the
adaptation tech tree, the delayed fish-stock crash, and the coastline's own
flood progression) rather than poking synthetic flags wherever a real code
path can drive the same state instead.
"""

import math


def _ids(entries):
    return {entry["id"] for entry in entries}


# --- Catalog sanity -----------------------------------------------------


def test_catalog_loaded_and_nonempty(game_env):
    m = game_env.module
    assert 15 <= len(m.ACHIEVEMENTS) <= 25


def test_every_catalog_id_is_unique(game_env):
    m = game_env.module
    ids = [entry["id"] for entry in m.ACHIEVEMENTS]
    assert len(ids) == len(set(ids))


def test_every_catalog_id_has_a_checker(game_env):
    m = game_env.module
    for entry in m.ACHIEVEMENTS:
        assert entry["id"] in m.ACHIEVEMENT_CHECKS, entry["id"]


def test_every_progress_id_refers_to_a_real_achievement(game_env):
    m = game_env.module
    catalog_ids = _ids(m.ACHIEVEMENTS)
    for progress_id in m.ACHIEVEMENT_PROGRESS:
        assert progress_id in catalog_ids


def test_nothing_earned_on_a_fresh_game(game_env):
    m = game_env.module
    assert m.achievement_ids_earned() == []


# --- Individual achievements, driven through real game actions ----------


def test_underway(game_env):
    m = game_env.module
    game_env.advance_season()
    assert game_env.state.season == 2
    assert "underway" in m.achievement_ids_earned()


def test_first_output(game_env):
    m = game_env.module
    game_env.invest("output")
    assert "first_output" in m.achievement_ids_earned()


def test_first_reduction(game_env):
    m = game_env.module
    game_env.invest("reduction")
    assert "first_reduction" in m.achievement_ids_earned()


def test_first_adaptation(game_env):
    m = game_env.module
    game_env.invest("adaptation")
    assert "first_adaptation" in m.achievement_ids_earned()


def test_tier_sandbags_at_first_threshold(game_env):
    m = game_env.module
    for _ in range(3):
        game_env.invest("adaptation")
    assert "tier_sandbags" in m.achievement_ids_earned()
    assert "tier_seawalls" not in m.achievement_ids_earned()


def test_tier_seawalls_at_second_threshold(game_env):
    m = game_env.module
    for _ in range(6):
        game_env.invest("adaptation")
    assert "tier_seawalls" in m.achievement_ids_earned()
    assert "tier_reinforced" not in m.achievement_ids_earned()


def test_tier_reinforced_at_third_threshold(game_env):
    m = game_env.module
    for _ in range(10):
        game_env.invest("adaptation")
    assert "tier_reinforced" in m.achievement_ids_earned()
    assert "tier_storm_surge" not in m.achievement_ids_earned()


def test_tier_storm_surge_at_final_threshold(game_env):
    m = game_env.module
    game_env.state.funds = 10000  # 15 invests * 30 cost > starting 300 funds
    for _ in range(15):
        game_env.invest("adaptation")
    assert "tier_storm_surge" in m.achievement_ids_earned()


def test_first_flood(game_env):
    m = game_env.module
    threshold = m.row_flood_threshold(m.COASTLINE_ROWS - 1)
    seasons = math.ceil(threshold / m.SEA_LEVEL_RISE_PER_SEASON)
    for _ in range(seasons):
        game_env.advance_season()
    assert m.flooded_row_count(game_env.state.sea_level) >= 1
    assert "first_flood" in m.achievement_ids_earned()


def test_losing_ground_needs_half_the_rows(game_env):
    m = game_env.module
    needed = math.ceil(m.COASTLINE_ROWS * m.LOSING_GROUND_ROW_FRACTION)
    # Advance until at least half the coastline rows are flooded, capped
    # well above the seasons this should realistically take.
    for _ in range(60):
        if m.flooded_row_count(game_env.state.sea_level) >= needed:
            break
        game_env.advance_season()
    assert m.flooded_row_count(game_env.state.sea_level) >= needed
    assert "losing_ground" in m.achievement_ids_earned()


def test_fully_submerged_needs_every_row(game_env):
    m = game_env.module
    for _ in range(60):
        if m.flooded_row_count(game_env.state.sea_level) >= m.COASTLINE_ROWS:
            break
        game_env.advance_season()
    assert m.flooded_row_count(game_env.state.sea_level) == m.COASTLINE_ROWS
    assert "fully_submerged" in m.achievement_ids_earned()


def test_the_lag_arrives_via_a_real_output_binge(game_env):
    m = game_env.module
    game_env.state.funds = 10000
    for _ in range(10):
        game_env.invest("output")  # heavy output -> heavy acidity build-up
    for _ in range(15):
        game_env.advance_season()
    assert game_env.state.min_fish_yield_ever <= 0.5
    assert "the_lag_arrives" in m.achievement_ids_earned()


def test_stocks_rebound_needs_a_real_low_point_first(game_env):
    m = game_env.module
    # A high fish yield alone, with no prior crash, must not qualify.
    game_env.state.acidity_history = [0.0] * 10
    assert game_env.state.fish_yield_multiplier() >= m.STOCKS_REBOUND_RECOVERY_THRESHOLD
    assert "stocks_rebound" not in m.achievement_ids_earned()

    # Once a genuine crash is on record (min_fish_yield_ever below the
    # crash threshold) and the current yield has recovered, it qualifies.
    game_env.state.min_fish_yield_ever = 0.6
    assert "stocks_rebound" in m.achievement_ids_earned()


def test_turning_the_tide_needs_a_real_drop_from_the_peak(game_env):
    m = game_env.module
    game_env.state.max_acidity_ever = 50.0
    game_env.state.acidity = 35.0  # only a 15-point drop
    assert "turning_the_tide" not in m.achievement_ids_earned()
    game_env.state.acidity = 25.0  # a 25-point drop, over the 20 threshold
    assert "turning_the_tide" in m.achievement_ids_earned()


def test_flush_coffers_threshold(game_env):
    m = game_env.module
    game_env.state.max_funds_ever = m.FLUSH_COFFERS_THRESHOLD
    assert "flush_coffers" in m.achievement_ids_earned()
    current, target = m.ACHIEVEMENT_PROGRESS["flush_coffers"]()
    assert current == int(m.FLUSH_COFFERS_THRESHOLD)
    assert target == int(m.FLUSH_COFFERS_THRESHOLD)


def test_time_bought_threshold(game_env):
    m = game_env.module
    game_env.state.undampened_damage_total = 250.0
    game_env.state.cumulative_damage = 100.0  # damage_saved() == 150
    assert game_env.state.damage_saved() >= m.TIME_BOUGHT_THRESHOLD
    assert "time_bought" in m.achievement_ids_earned()


def test_the_long_haul_at_season_20(game_env):
    m = game_env.module
    for _ in range(m.THE_LONG_HAUL_SEASON - 1):
        game_env.advance_season()
    assert game_env.state.season == m.THE_LONG_HAUL_SEASON
    assert "the_long_haul" in m.achievement_ids_earned()


def test_bending_the_curve_mirrors_the_flag(game_env):
    m = game_env.module
    assert "bending_the_curve" not in m.achievement_ids_earned()
    game_env.state.trend_flattening_announced = True
    assert "bending_the_curve" in m.achievement_ids_earned()


def test_well_rounded_needs_all_three_categories(game_env):
    m = game_env.module
    game_env.state.funds = 10000
    for _ in range(m.WELL_ROUNDED_CAPACITY):
        game_env.invest("output")
        game_env.invest("reduction")
    assert "well_rounded" not in m.achievement_ids_earned()
    for _ in range(m.WELL_ROUNDED_CAPACITY):
        game_env.invest("adaptation")
    assert "well_rounded" in m.achievement_ids_earned()


def test_fortified_in_time_needs_max_tier_before_any_flood(game_env):
    m = game_env.module
    game_env.state.funds = 10000
    for _ in range(15):
        game_env.invest("adaptation")
    assert game_env.state.current_tier_index() == m._max_tier_index()
    assert m.flooded_row_count(game_env.state.sea_level) == 0
    assert "fortified_in_time" in m.achievement_ids_earned()


def test_fortified_in_time_not_earned_if_flooded_first(game_env):
    m = game_env.module
    threshold = m.row_flood_threshold(m.COASTLINE_ROWS - 1)
    seasons = math.ceil(threshold / m.SEA_LEVEL_RISE_PER_SEASON)
    for _ in range(seasons):
        game_env.advance_season()
    assert m.flooded_row_count(game_env.state.sea_level) >= 1
    game_env.state.funds = 10000
    for _ in range(15):
        game_env.invest("adaptation")
    assert "fortified_in_time" not in m.achievement_ids_earned()


# --- Progress readouts ----------------------------------------------------


def test_progress_readout_shape(game_env):
    m = game_env.module
    game_env.state.max_funds_ever = 400
    current, target = m.ACHIEVEMENT_PROGRESS["flush_coffers"]()
    assert current == 400
    assert target == int(m.FLUSH_COFFERS_THRESHOLD)


# --- No-mutation guarantee -------------------------------------------------


def test_checking_achievements_never_mutates_other_state(game_env):
    m = game_env.module
    game_env.invest("output")
    game_env.advance_season()
    before = m.get_state()
    m.achievement_ids_earned()
    m.achievements_summary()
    after = m.get_state()
    before.pop("achievements_earned")
    after.pop("achievements_earned")
    assert before == after


# --- Panel toggle/render ---------------------------------------------------


def test_achievements_panel_hidden_by_default(game_env):
    assert game_env.elements["achievements-panel"].hidden is True


def test_achievements_panel_toggle_opens_and_closes(game_env):
    game_env.toggle_achievements()
    assert game_env.elements["achievements-panel"].hidden is False
    game_env.toggle_achievements()
    assert game_env.elements["achievements-panel"].hidden is True


def test_achievements_toggle_button_shows_earned_count(game_env):
    m = game_env.module
    game_env.invest("output")
    game_env.toggle_achievements()
    text = game_env.elements["achievements-toggle-button"].innerText
    assert f"1/{len(m.ACHIEVEMENTS)}" in text


def test_achievements_panel_renders_every_catalog_entry(game_env):
    m = game_env.module
    game_env.toggle_achievements()
    panel = game_env.elements["achievements-panel"]
    assert len(panel.children) == len(m.ACHIEVEMENTS) + 1  # +1 for the hub-dashboard link


def test_achievements_panel_marks_an_earned_card_distinctly(game_env):
    game_env.invest("output")
    game_env.toggle_achievements()
    panel = game_env.elements["achievements-panel"]
    earned_cards = [c for c in panel.children if "achievement-card--earned" in c.className]
    assert len(earned_cards) == 1


def test_achievements_panel_includes_hub_dashboard_link(game_env):
    game_env.toggle_achievements()
    panel = game_env.elements["achievements-panel"]
    assert any(getattr(child, "href", None) == "../../index.html#account-achievements-dashboard" for child in panel.children)


def test_achievements_panel_stays_live_across_a_season_advance(game_env):
    m = game_env.module
    game_env.toggle_achievements()
    game_env.advance_season()
    text = game_env.elements["achievements-toggle-button"].innerText
    earned = len(m.achievement_ids_earned())
    assert f"{earned}/{len(m.ACHIEVEMENTS)}" in text


# --- Unlock toast -----------------------------------------------------------


def test_toast_fires_on_a_fresh_unlock(game_env):
    game_env.invest("output")
    toast = game_env.elements["achievement-toast"]
    assert toast.hidden is False
    assert "Open For Business" in toast.innerText


def test_toast_does_not_fire_for_already_earned_achievements(game_env):
    m = game_env.module
    game_env.invest("output")
    assert len(game_env.timers.pending) == 1  # the one auto-hide timeout from this real unlock

    # A second, unrelated render must not re-toast first_output -- only
    # genuinely *new* unlocks should show up, so no second auto-hide
    # timeout should get scheduled. (Not advance_season() here -- that
    # would also earn "underway" at season 2, a second real new unlock.)
    m.render()
    assert len(game_env.timers.pending) == 1


def test_no_toast_on_a_freshly_booted_game(game_env):
    # setup() itself calls render() once; that alone must never fire a
    # toast (there is nothing "new" about a fresh game's own zero
    # achievements).
    assert game_env.elements["achievement-toast"].hidden is True


def test_multiple_simultaneous_unlocks_batch_into_one_toast(game_env):
    # Investing in output for the first time at the same moment funds
    # cross into flush-coffers range would batch -- simpler and just as
    # real: invest in two different categories back to back is two
    # separate renders, so instead drive a render that satisfies two
    # checks at once via a direct state nudge that a real save/session
    # could produce (max_funds_ever crossing the threshold right as
    # output is first invested).
    game_env.state.max_funds_ever = game_env.module.FLUSH_COFFERS_THRESHOLD
    game_env.invest("output")
    toast = game_env.elements["achievement-toast"]
    assert toast.hidden is False
    assert "2 achievements unlocked" in toast.innerText
    assert "Open For Business" in toast.innerText
    assert "Flush Coffers" in toast.innerText


def test_load_state_resets_toast_baseline_so_earned_saves_do_not_spam(game_env):
    m = game_env.module
    game_env.invest("output")
    data = m.get_state()
    assert "first_output" in data["achievements_earned"]

    # Loading a save whose achievements_earned already includes
    # "first_output" must not toast it again -- it's not a *new* unlock in
    # this render cycle, it's already-true state being restored. The one
    # real unlock (the invest() above) already scheduled exactly one
    # auto-hide timeout; load_state() must not schedule a second.
    assert len(game_env.timers.pending) == 1
    m.load_state(data)
    assert len(game_env.timers.pending) == 1


# --- Save/load round-trip of achievements' own new tracked state ----------


def test_new_tracked_fields_round_trip_through_save_load(game_env):
    m = game_env.module
    game_env.state.funds = 10000
    for _ in range(10):
        game_env.invest("output")
    for _ in range(15):
        game_env.advance_season()

    data = m.get_state()
    m.load_state(data)

    assert game_env.state.min_fish_yield_ever == data["min_fish_yield_ever"]
    assert game_env.state.max_acidity_ever == data["max_acidity_ever"]
    assert game_env.state.max_funds_ever == data["max_funds_ever"]
    assert game_env.state.fortified_in_time_earned == data["fortified_in_time_earned"]


def test_old_save_missing_achievement_fields_does_not_crash(game_env):
    """A save written before this feature shipped lacks every new key --
    load_state() must fall back to current live values instead of
    KeyError-ing, same defensive convention as every other field here."""
    m = game_env.module
    old_save = {
        "season": 3,
        "funds": 250.0,
        "capacity": {"output": 2, "reduction": 1, "adaptation": 0},
        "acidity": 10.0,
        "acidity_history": [4.0, 8.0, 10.0],
        "sea_level": 10.0,
        "cumulative_damage": 20.0,
        "undampened_damage_total": 20.0,
        "damage_log": [10.0, 10.0],
        "ticker_log": [],
        "trend_flattening_announced": False,
    }
    assert m.load_state(old_save) is True
    assert game_env.state.min_fish_yield_ever <= 1.0
    assert game_env.state.max_acidity_ever >= game_env.state.acidity
    assert game_env.state.max_funds_ever >= game_env.state.funds
    assert game_env.state.fortified_in_time_earned is False


def test_achievements_earned_is_never_read_back_on_load(game_env):
    m = game_env.module
    save_claiming_everything_earned = m.get_state()
    save_claiming_everything_earned["achievements_earned"] = [
        entry["id"] for entry in m.ACHIEVEMENTS
    ]
    m.load_state(save_claiming_everything_earned)
    # Nothing about the fresh game's real state changed, so the freshly
    # recomputed earned list must still be empty regardless of what the
    # (fabricated) save's achievements_earned claimed.
    assert m.achievement_ids_earned() == []
