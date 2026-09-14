"""Tests for the ACHIEVEMENTS-SYSTEM-DESIGN.md rollout to Drift: the
achievements.json catalog, the checkers/progress readouts in game.py, the
in-game toggle/panel, and the unlock toast + hub-dashboard link (the
site-wide "on top of the base rollout" requirements from
planning/TODO.md). Every achievement's earned status is meant to be a pure
function of state that already exists elsewhere in this module -- these
tests exercise that by driving the real game systems (investing, advancing
rounds, opening the coda) rather than poking an `_earned` flag that
doesn't exist.
"""


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

def test_first_investment_earned_after_the_first_investment(game_env):
    assert "first_investment" not in game_env.module.achievement_ids_earned()
    game_env.region.invest("housing")
    assert "first_investment" in game_env.module.achievement_ids_earned()


def test_full_capacity_portfolio_requires_all_three_types(game_env):
    module = game_env.module
    region = game_env.region
    region.invest("housing")
    region.invest("services")
    assert "full_capacity_portfolio" not in module.achievement_ids_earned()
    region.invest("infrastructure")
    assert "full_capacity_portfolio" in module.achievement_ids_earned()


def test_services_backbone_after_five_services_investments(game_env):
    module = game_env.module
    region = game_env.region
    for _ in range(4):
        region.invest("services")
    assert "services_backbone" not in module.achievement_ids_earned()
    region.invest("services")
    assert "services_backbone" in module.achievement_ids_earned()


def test_built_to_scale_at_200_total_capacity(game_env):
    module = game_env.module
    region = game_env.region
    region.funds = 10_000
    # Housing is +10 capacity per investment -- 20 investments -> 200.
    for _ in range(19):
        region.invest("housing")
    assert "built_to_scale" not in module.achievement_ids_earned()
    region.invest("housing")
    assert region.total_capacity() == 200
    assert "built_to_scale" in module.achievement_ids_earned()


def test_century_arrivals_at_100_lifetime_arrivals(game_env):
    module = game_env.module
    region = game_env.region
    region.total_arrivals = 99.0
    assert "century_arrivals" not in module.achievement_ids_earned()
    region.total_arrivals = 100.0
    assert "century_arrivals" in module.achievement_ids_earned()


def test_crisis_averted_requires_round_21_with_no_critical_strain(game_env):
    module = game_env.module
    region = game_env.region
    region.funds = 10_000
    # Enough up-front housing capacity to keep strain well clear of the
    # 0.6 critical threshold across the whole 20-round run -- arrivals
    # accumulate to 385 people by round 21, so 300 capacity comfortably
    # covers it (worst-case ratio ~0.22, below even the 0.25 "strained"
    # boundary, let alone critical).
    for _ in range(30):
        region.invest("housing")
    for _ in range(20):
        region.advance_round()
    assert region.round_number == 21
    assert "crisis_averted" in module.achievement_ids_earned()


def test_crisis_averted_is_false_once_strain_has_gone_critical(game_env):
    module = game_env.module
    region = game_env.region
    # No capacity investment at all -- strain climbs unchecked toward
    # critical (>= 0.6) well before round 21.
    for _ in range(20):
        region.advance_round()
    assert region.round_number == 21
    assert any(s >= 0.6 for s in region.strain_log)
    assert "crisis_averted" not in module.achievement_ids_earned()


def test_full_recovery_requires_having_been_critical_then_returning_to_stable(game_env):
    module = game_env.module
    region = game_env.region
    # Let strain run up to critical with no investment...
    for _ in range(6):
        region.advance_round()
    assert any(s >= 0.6 for s in region.strain_log)
    assert "full_recovery" not in module.achievement_ids_earned()
    # ...then pour in enough capacity to bring strain back down to stable.
    region.funds = 10_000
    for _ in range(20):
        region.invest("housing")
        region.invest("infrastructure")
    region.advance_round()
    assert region.strain_level() == "stable"
    assert "full_recovery" in module.achievement_ids_earned()


def test_turning_point_reached_mirrors_has_crossed_to_net_positive(game_env):
    module = game_env.module
    region = game_env.region
    region.funds = 10_000
    region.invest("services")
    for _ in range(30):
        region.advance_round()
    assert region.has_crossed_to_net_positive()
    assert "turning_point_reached" in module.achievement_ids_earned()


def test_ahead_of_schedule_requires_the_turning_point_by_round_15(game_env):
    module = game_env.module
    region = game_env.region
    region.net_positive_round = 15
    assert "ahead_of_schedule" in module.achievement_ids_earned()
    region.net_positive_round = 16
    assert "ahead_of_schedule" not in module.achievement_ids_earned()
    region.net_positive_round = None
    assert "ahead_of_schedule" not in module.achievement_ids_earned()


def test_century_integrated_at_100_integrated_people(game_env):
    module = game_env.module
    region = game_env.region
    region.integrated_population = 99.0
    assert "century_integrated" not in module.achievement_ids_earned()
    region.integrated_population = 100.0
    assert "century_integrated" in module.achievement_ids_earned()


def test_backlog_cleared_requires_meaningful_arrivals_and_zero_pending(game_env):
    module = game_env.module
    region = game_env.region
    region.total_arrivals = 60.0
    region.integrated_population = 60.0
    assert region.pending_population() == 0.0
    assert "backlog_cleared" in module.achievement_ids_earned()


def test_backlog_cleared_is_false_below_the_arrivals_floor(game_env):
    module = game_env.module
    region = game_env.region
    region.total_arrivals = 10.0
    region.integrated_population = 10.0
    assert "backlog_cleared" not in module.achievement_ids_earned()


def test_balanced_region_requires_all_three_sub_scores_at_fifty(game_env):
    module = game_env.module
    region = game_env.region
    region.funds = 500.0  # economic_health -> 50
    region.total_arrivals = 10.0
    region.integrated_population = 5.0  # social_cohesion -> 50
    region.strain_log = [0.5]  # service_quality -> 50
    assert "balanced_region" in module.achievement_ids_earned()


def test_thriving_and_model_region_wellbeing_thresholds(game_env):
    module = game_env.module
    region = game_env.region
    region.funds = 700.0
    region.total_arrivals = 10.0
    region.integrated_population = 7.0
    region.strain_log = [0.0]
    assert region.wellbeing_score() >= 70
    assert "thriving_region" in module.achievement_ids_earned()
    assert "model_region" not in module.achievement_ids_earned()

    region.funds = 900.0
    region.integrated_population = 9.0
    assert region.wellbeing_score() >= 90
    assert "model_region" in module.achievement_ids_earned()


def test_economic_engine_requires_double_payback(game_env):
    module = game_env.module
    region = game_env.region
    region.cumulative_services_investment = 20.0
    region.cumulative_integration_contribution = 39.0
    assert "economic_engine" not in module.achievement_ids_earned()
    region.cumulative_integration_contribution = 40.0
    assert "economic_engine" in module.achievement_ids_earned()


def test_steady_ground_tracks_best_streak_across_advance_round(game_env):
    module = game_env.module
    region = game_env.region
    region.funds = 10_000
    # 20 housing investments -> 200 capacity, comfortably keeping strain
    # under the 0.25 "stable" boundary for all 15 rounds below.
    for _ in range(20):
        region.invest("housing")
    for _ in range(15):
        region.advance_round()
    assert region.best_stable_streak >= 15
    assert "steady_ground" in module.achievement_ids_earned()


def test_steady_ground_best_streak_is_sticky_after_a_break(game_env):
    module = game_env.module
    region = game_env.region
    region.funds = 10_000
    for _ in range(20):
        region.invest("housing")
    for _ in range(15):
        region.advance_round()
    assert region.best_stable_streak == 15
    # Force a break in the streak: strain is computed at the *start* of
    # advance_round() off the arrivals backlog already on the books, so
    # inflating total_arrivals directly (rather than just next round's
    # incoming arrivals) is what actually breaks this round's streak.
    region.total_arrivals = 100_000.0
    region.advance_round()
    assert region.current_stable_streak == 0
    assert region.best_stable_streak == 15
    assert "steady_ground" in module.achievement_ids_earned()


def test_long_horizon_reached_requires_actually_opening_the_coda(game_env):
    module = game_env.module
    region = game_env.region
    region.integrated_population = 5.0  # unlocks the coda button
    assert "long_horizon_reached" not in module.achievement_ids_earned()
    game_env.toggle_coda()
    assert region.coda_ever_viewed is True
    assert "long_horizon_reached" in module.achievement_ids_earned()


def test_sustained_transition_requires_round_40_and_score_60(game_env):
    module = game_env.module
    region = game_env.region
    region.round_number = 40
    region.funds = 900.0
    region.total_arrivals = 10.0
    region.integrated_population = 9.0
    region.strain_log = [0.0]
    assert region.wellbeing_score() >= 60
    assert "sustained_transition" in module.achievement_ids_earned()
    region.round_number = 39
    assert "sustained_transition" not in module.achievement_ids_earned()


# --- progress readouts --------------------------------------------------

def test_progress_readout_for_full_capacity_portfolio_counts_standing_types(game_env):
    module = game_env.module
    region = game_env.region
    region.invest("housing")
    region.invest("services")
    current, target = module.ACHIEVEMENT_PROGRESS["full_capacity_portfolio"]()
    assert current == 2
    assert target == len(module.CAPACITY_TYPES)


def test_progress_readout_for_services_backbone_caps_at_target(game_env):
    module = game_env.module
    region = game_env.region
    for _ in range(8):  # more than the target of 5
        region.invest("services")
    current, target = module.ACHIEVEMENT_PROGRESS["services_backbone"]()
    assert current == target == 5


def test_progress_readout_for_thriving_region(game_env):
    module = game_env.module
    region = game_env.region
    region.funds = 300.0
    current, target = module.ACHIEVEMENT_PROGRESS["thriving_region"]()
    assert target == 70
    assert 0 <= current <= 70


# --- no mutation as a side effect ---------------------------------------

def test_checking_achievements_never_mutates_other_state(game_env):
    module = game_env.module
    region = game_env.region
    region.invest("housing")
    region.invest("services")
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
    game_env.invest("housing")  # earns first_investment
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
    game_env.invest("housing")
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
    game_env.invest("housing")
    game_env.advance_round()
    text = game_env.elements["achievements-toggle-button"].innerText
    assert "1/" in text


# --- unlock toast --------------------------------------------------------

def test_toast_shows_on_a_newly_earned_achievement(game_env):
    toast = game_env.elements["achievement-toast"]
    assert toast.hidden is True
    game_env.invest("housing")  # earns first_investment
    assert toast.hidden is False
    assert "First Investment" in game_env.elements["achievement-toast-text"].innerText


def test_toast_auto_hides_after_its_timer_fires(game_env):
    game_env.invest("housing")
    assert game_env.elements["achievement-toast"].hidden is False
    game_env.timers.flush()
    assert game_env.elements["achievement-toast"].hidden is True


def test_toast_does_not_refire_for_an_already_earned_achievement(game_env):
    game_env.invest("housing")
    game_env.timers.flush()
    game_env.elements["achievement-toast"].hidden = True  # simulate it having closed
    game_env.invest("housing")  # first_investment already earned; nothing new
    assert game_env.elements["achievement-toast"].hidden is True


def test_loading_a_save_with_earned_achievements_does_not_flood_toasts(game_env):
    module = game_env.module
    game_env.invest("housing")
    game_env.invest("services")
    snapshot = module.get_state()
    game_env.elements["achievement-toast"].hidden = True  # reset from the investments above

    module.load_state(snapshot)

    assert game_env.elements["achievement-toast"].hidden is True
