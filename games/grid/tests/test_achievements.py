"""Tests for the ACHIEVEMENTS-SYSTEM-DESIGN.md rollout to Grid: the
achievements.json catalog, the checkers/progress readouts in game.py, the
in-game toggle/panel, and the unlock toast + hub-dashboard link (the
site-wide "on top of the base rollout" requirements from
planning/TODO.md). Every achievement's earned status is meant to be a pure
function of state that already exists elsewhere in this module -- these
tests exercise that by driving the real game systems (building, retiring,
maintaining, advancing rounds) rather than poking an `_earned` flag that
doesn't exist.
"""


def NEVER_TRIGGER():
    return 0.999999


# --- the catalog itself -----------------------------------------------

def test_achievements_catalog_loads_from_json_with_a_reasonable_count(game_env):
    module = game_env.module
    assert 5 <= len(module.ACHIEVEMENTS) <= 30
    ids = [entry["id"] for entry in module.ACHIEVEMENTS]
    assert len(ids) == len(set(ids))  # no duplicate ids


def test_every_catalog_entry_has_a_matching_checker(game_env):
    module = game_env.module
    for entry in module.ACHIEVEMENTS:
        assert entry["id"] in module.ACHIEVEMENT_CHECKS
        assert callable(module.ACHIEVEMENT_CHECKS[entry["id"]])


def test_every_progress_entry_refers_to_a_real_achievement(game_env):
    module = game_env.module
    catalog_ids = {entry["id"] for entry in module.ACHIEVEMENTS}
    assert set(module.ACHIEVEMENT_PROGRESS).issubset(catalog_ids)


# --- nothing earned on a fresh game ------------------------------------

def test_nothing_is_earned_on_a_fresh_game(game_env):
    assert game_env.module.achievement_ids_earned() == []


def test_summary_shows_every_entry_as_not_earned_initially(game_env):
    summary = game_env.module.achievements_summary()
    assert len(summary) == len(game_env.module.ACHIEVEMENTS)
    assert all(entry["earned"] is False for entry in summary)


# --- individual achievements, driven through real game systems --------

def test_first_watt_earned_after_the_first_plant(game_env):
    assert "first_watt" not in game_env.module.achievement_ids_earned()
    game_env.build("coal")
    assert "first_watt" in game_env.module.achievement_ids_earned()


def test_renewable_pioneer_requires_a_renewable_specifically(game_env):
    game_env.build("coal")
    assert "renewable_pioneer" not in game_env.module.achievement_ids_earned()
    game_env.build("solar")
    assert "renewable_pioneer" in game_env.module.achievement_ids_earned()


def test_first_storage_earned_only_by_a_battery(game_env):
    game_env.build("coal")
    assert "first_storage" not in game_env.module.achievement_ids_earned()
    game_env.build("battery")
    assert "first_storage" in game_env.module.achievement_ids_earned()


def test_clean_capacity_share_milestones(game_env):
    module = game_env.module
    game_env.state.funds = 10_000
    # Coal (20 cap) + solar/wind/hydro (10+12+40=62 cap) -> renewable
    # share = 62/82 ~= 0.756, clearing all three thresholds at once.
    game_env.build("coal")
    game_env.build("solar")
    game_env.build("wind")
    game_env.build("hydro")
    earned = module.achievement_ids_earned()
    assert "clean_quarter" in earned
    assert "clean_half" in earned
    assert "clean_three_quarters" in earned


def test_fully_renewable_requires_zero_fossil_share(game_env):
    module = game_env.module
    game_env.build("coal")
    game_env.build("solar")
    assert "fully_renewable" not in module.achievement_ids_earned()
    game_env.retire("coal")
    assert "fully_renewable" in module.achievement_ids_earned()


def test_fully_renewable_is_false_on_an_empty_grid(game_env):
    # total_capacity() == 0 must not read as "fully renewable" by default.
    assert "fully_renewable" not in game_env.module.achievement_ids_earned()


def test_learning_curve_floored_once_a_renewable_hits_the_cost_floor(game_env):
    module = game_env.module
    assert "learning_curve_floored" not in module.achievement_ids_earned()
    # 0.95 ** 18 < 0.4 -- enough cumulative builds to hit the floor.
    game_env.state.cumulative_built["solar"] = 18
    assert "learning_curve_floored" in module.achievement_ids_earned()


def test_diverse_grid_requires_every_plant_type_standing_at_once(game_env):
    module = game_env.module
    game_env.state.funds = 10_000
    for plant_type in module.PLANT_TYPES[:-1]:
        game_env.build(plant_type)
    assert "diverse_grid" not in module.achievement_ids_earned()
    game_env.build(module.PLANT_TYPES[-1])
    assert "diverse_grid" in module.achievement_ids_earned()


def test_fossil_phase_out_requires_building_then_fully_retiring(game_env):
    module = game_env.module
    game_env.build("solar")  # replacement capacity -- a phase-out, not a teardown
    game_env.build("coal")
    game_env.build("coal")
    game_env.build("coal")
    assert "fossil_phase_out" not in module.achievement_ids_earned()  # still standing
    game_env.retire("coal")
    game_env.retire("coal")
    game_env.retire("coal")
    assert "fossil_phase_out" in module.achievement_ids_earned()


def test_fossil_phase_out_is_false_if_the_grid_is_abandoned_entirely(game_env):
    module = game_env.module
    game_env.build("coal")
    game_env.build("coal")
    game_env.build("coal")
    game_env.retire("coal")
    game_env.retire("coal")
    game_env.retire("coal")
    # No replacement capacity was ever built -- this is grid abandonment,
    # not a genuine renewable phase-out, so it shouldn't count.
    assert game_env.state.total_capacity() == 0
    assert "fossil_phase_out" not in module.achievement_ids_earned()


def test_fossil_phase_out_requires_a_meaningful_amount_built_first(game_env):
    module = game_env.module
    game_env.build("coal")
    game_env.retire("coal")
    # Only 1 ever built -- below the "meaningful" threshold of 3.
    assert "fossil_phase_out" not in module.achievement_ids_earned()


def test_clean_streak_15_tracks_best_streak_across_advance_round(game_env):
    module = game_env.module
    state = game_env.state
    for _ in range(15):
        state.advance_round(rng=NEVER_TRIGGER)
    assert state.current_clean_streak == 15
    assert state.best_clean_streak == 15
    assert "clean_streak_15" in module.achievement_ids_earned()


def test_clean_streak_resets_on_a_disruption_but_best_streak_is_sticky(game_env):
    module = game_env.module
    state = game_env.state
    for _ in range(15):
        state.advance_round(rng=NEVER_TRIGGER)
    # A high-emissions disruption resets the *current* streak...
    state.emissions = 999_999.0
    state.advance_round(rng=lambda: 0.0)
    assert state.current_clean_streak == 0
    assert state.best_clean_streak == 15
    # ...but the achievement (keyed off best_clean_streak) stays earned.
    assert "clean_streak_15" in module.achievement_ids_earned()


def test_no_damage_20_requires_reaching_round_21_undamaged(game_env):
    module = game_env.module
    state = game_env.state
    for _ in range(20):
        state.advance_round(rng=NEVER_TRIGGER)
    assert state.round_number == 21
    assert "no_damage_20" in module.achievement_ids_earned()


def test_no_damage_20_is_never_earned_after_a_real_damage_event(game_env):
    module = game_env.module
    state = game_env.state
    game_env.build("coal")
    state.emissions = 2000.0  # severity well above the damage threshold
    state.advance_round(rng=lambda: 0.0)
    assert state.last_event["type"] == "damage"
    for _ in range(25):
        state.advance_round(rng=NEVER_TRIGGER)
    assert state.round_number > 21
    assert "no_damage_20" not in module.achievement_ids_earned()


def test_score_achievements_after_enough_clean_rounds(game_env):
    module = game_env.module
    state = game_env.state
    for _ in range(20):
        state.advance_round(rng=NEVER_TRIGGER)
    assert state.score() == 100
    assert "score_50" in module.achievement_ids_earned()
    assert "score_80" in module.achievement_ids_earned()


def test_score_achievements_need_the_minimum_round_count_too(game_env):
    module = game_env.module
    state = game_env.state
    for _ in range(5):
        state.advance_round(rng=NEVER_TRIGGER)
    assert state.score() == 100  # a perfect score this early still shouldn't count
    assert "score_50" not in module.achievement_ids_earned()


def test_well_maintained_after_five_maintain_actions(game_env):
    module = game_env.module
    game_env.build("coal")
    for _ in range(4):
        game_env.maintain("coal")
    assert "well_maintained" not in module.achievement_ids_earned()
    game_env.maintain("coal")
    assert "well_maintained" in module.achievement_ids_earned()


def test_ahead_of_the_curve_needs_a_clean_grid_and_enough_rounds(game_env):
    module = game_env.module
    state = game_env.state
    game_env.build("nuclear")  # capacity with zero emissions
    for _ in range(10):
        state.advance_round(rng=NEVER_TRIGGER)
    assert state.round_number == 11
    assert state.emissions < state.global_reference_emissions
    assert "ahead_of_the_curve" in module.achievement_ids_earned()


def test_grid_at_scale_at_300_capacity(game_env):
    module = game_env.module
    game_env.state.funds = 10_000
    game_env.build("nuclear")
    game_env.build("nuclear")
    assert "grid_at_scale" not in module.achievement_ids_earned()  # 200
    game_env.build("nuclear")
    assert game_env.state.total_capacity() == 300
    assert "grid_at_scale" in module.achievement_ids_earned()


# --- progress readouts --------------------------------------------------

def test_progress_readout_shape_for_a_percentage_style_achievement(game_env):
    module = game_env.module
    game_env.state.funds = 10_000
    game_env.build("coal")
    game_env.build("solar")
    current, target = module.ACHIEVEMENT_PROGRESS["clean_quarter"]()
    assert target == 25
    assert 0 <= current <= 100


def test_progress_readout_for_diverse_grid_counts_standing_types(game_env):
    module = game_env.module
    game_env.build("coal")
    game_env.build("gas")
    current, target = module.ACHIEVEMENT_PROGRESS["diverse_grid"]()
    assert current == 2
    assert target == len(module.PLANT_TYPES)


def test_progress_readout_for_well_maintained_caps_at_target(game_env):
    module = game_env.module
    game_env.build("coal")
    for _ in range(8):  # more than the target of 5
        game_env.maintain("coal")
    current, target = module.ACHIEVEMENT_PROGRESS["well_maintained"]()
    assert current == target == 5


# --- no mutation as a side effect ---------------------------------------

def test_checking_achievements_never_mutates_other_state(game_env):
    module = game_env.module
    game_env.build("coal")
    game_env.build("solar")
    before = module.get_state()
    module.achievement_ids_earned()
    module.achievement_ids_earned()
    module.achievements_summary()
    after = module.get_state()
    before.pop("achievements_earned")
    after.pop("achievements_earned")
    assert before == after


# --- toggle / panel ------------------------------------------------------

def _all_texts(element):
    texts = [element.innerText]
    for child in element.children:
        texts.extend(_all_texts(child))
    return texts


def test_achievements_panel_is_hidden_by_default(game_env):
    assert game_env.elements["achievements-panel"].hidden is True


def test_toggle_opens_and_closes_the_panel(game_env):
    game_env.toggle_achievements()
    assert game_env.elements["achievements-panel"].hidden is False
    game_env.toggle_achievements()
    assert game_env.elements["achievements-panel"].hidden is True


def test_toggle_button_shows_earned_over_total_count(game_env):
    module = game_env.module
    game_env.build("coal")  # earns first_watt
    game_env.toggle_achievements()
    text = game_env.elements["achievements-toggle-button"].innerText
    assert f"1/{len(module.ACHIEVEMENTS)}" in text or f"({1}/{len(module.ACHIEVEMENTS)})" in text


def test_panel_renders_every_catalog_entrys_label_and_description(game_env):
    module = game_env.module
    game_env.toggle_achievements()
    panel = game_env.elements["achievements-panel"]
    rendered = " ".join(text for card in panel.children for text in _all_texts(card))
    for entry in module.ACHIEVEMENTS:
        assert entry["label"] in rendered
        assert entry["description"] in rendered


def test_earned_card_is_marked_distinctly(game_env):
    game_env.build("coal")
    game_env.toggle_achievements()
    panel = game_env.elements["achievements-panel"]
    earned_cards = [c for c in panel.children if "achievement-card--earned" in c.className]
    assert len(earned_cards) == 1


def test_panel_includes_a_link_to_the_hub_dashboard(game_env):
    game_env.toggle_achievements()
    panel = game_env.elements["achievements-panel"]
    links = [c for c in panel.children if getattr(c, "className", "") == "achievements-hub-link"]
    assert len(links) == 1
    assert "index.html#account-achievements-dashboard" in links[0].href


def test_panel_stays_live_across_advance_round(game_env):
    game_env.toggle_achievements()
    game_env.build("coal")
    game_env.advance_round()
    text = game_env.elements["achievements-toggle-button"].innerText
    assert "1/" in text


# --- unlock toast --------------------------------------------------------

def test_toast_shows_on_a_newly_earned_achievement(game_env):
    toast = game_env.elements["achievement-toast"]
    assert toast.hidden is True
    game_env.build("coal")  # earns first_watt
    assert toast.hidden is False
    assert "First Watt" in game_env.elements["achievement-toast-text"].innerText


def test_toast_auto_hides_after_its_timer_fires(game_env):
    game_env.build("coal")
    assert game_env.elements["achievement-toast"].hidden is False
    game_env.timers.flush()
    assert game_env.elements["achievement-toast"].hidden is True


def test_toast_does_not_refire_for_an_already_earned_achievement(game_env):
    game_env.build("coal")
    game_env.timers.flush()
    game_env.elements["achievement-toast"].hidden = True  # simulate it having closed
    game_env.build("coal")  # first_watt already earned; nothing new
    assert game_env.elements["achievement-toast"].hidden is True


def test_loading_a_save_with_earned_achievements_does_not_flood_toasts(game_env):
    module = game_env.module
    game_env.build("coal")
    game_env.build("solar")
    snapshot = module.get_state()
    game_env.elements["achievement-toast"].hidden = True  # reset from the builds above

    module.load_state(snapshot)

    assert game_env.elements["achievement-toast"].hidden is True
