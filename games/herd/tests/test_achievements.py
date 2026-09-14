"""Tests for the ACHIEVEMENTS-SYSTEM-DESIGN.md rollout to Herd: the
achievements.json catalog, the checkers/progress readouts in game.py, the
in-game toggle/panel, and the unlock toast + hub-dashboard link (the
site-wide "on top of the base rollout" requirements from
planning/TODO.md). Every achievement's earned status is meant to be a pure
function of state that already exists elsewhere in this module -- these
tests exercise that by driving the real game systems (growing the herd,
investing, advancing rounds) rather than poking an `_earned` flag that
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

def test_first_herd_earned_after_first_growth(game_env):
    assert "first_herd" not in game_env.module.achievement_ids_earned()
    game_env.grow_herd()
    assert "first_herd" in game_env.module.achievement_ids_earned()


def test_growing_operation_and_major_operation_thresholds(game_env):
    module = game_env.module
    farm = game_env.farm
    farm.funds = 10_000
    for _ in range(9):
        game_env.grow_herd()
    assert "growing_operation" not in module.achievement_ids_earned()
    game_env.grow_herd()  # herd_size == 10
    assert "growing_operation" in module.achievement_ids_earned()
    assert "major_operation" not in module.achievement_ids_earned()
    for _ in range(15):
        game_env.grow_herd()  # herd_size == 25
    assert "major_operation" in module.achievement_ids_earned()


def test_first_decoupling_earned_by_any_single_measure(game_env):
    module = game_env.module
    assert "first_decoupling" not in module.achievement_ids_earned()
    game_env.invest_decoupling("feed")
    assert "first_decoupling" in module.achievement_ids_earned()


def test_all_three_measures_requires_each_measure_at_least_once(game_env):
    module = game_env.module
    game_env.invest_decoupling("feed")
    game_env.invest_decoupling("caps")
    assert "all_three_measures" not in module.achievement_ids_earned()
    game_env.invest_decoupling("capture")
    assert "all_three_measures" in module.achievement_ids_earned()


def test_decoupled_fraction_thresholds(game_env):
    module = game_env.module
    farm = game_env.farm
    farm.funds = 10_000
    for _ in range(7):
        game_env.invest_decoupling("capture")  # 7 * 0.10 = 0.70 reduction
    earned = module.achievement_ids_earned()
    assert "quarter_decoupled" in earned
    assert "half_decoupled" in earned
    assert "fully_decoupled" not in earned  # 0.70 < 0.90


def test_fully_decoupled_at_the_floor(game_env):
    module = game_env.module
    farm = game_env.farm
    farm.funds = 10_000
    for _ in range(20):
        game_env.invest_decoupling("capture")
    # ratio floors at MIN_COUPLING_RATIO (0.1), decoupled_fraction -> 0.9
    assert "fully_decoupled" in module.achievement_ids_earned()


def test_plant_pioneer_and_plant_based_thresholds(game_env):
    module = game_env.module
    farm = game_env.farm
    farm.funds = 10_000
    assert "plant_pioneer" not in module.achievement_ids_earned()
    game_env.invest_plant_pivot()
    assert "plant_pioneer" in module.achievement_ids_earned()
    assert "half_plant_based" not in module.achievement_ids_earned()
    for _ in range(5):  # 6 total * 0.05 = 0.30
        game_env.invest_plant_pivot()
    assert "half_plant_based" in module.achievement_ids_earned()
    assert "max_plant_pivot" not in module.achievement_ids_earned()
    for _ in range(6):  # 12 total * 0.05 = 0.60 (capped)
        game_env.invest_plant_pivot()
    assert "max_plant_pivot" in module.achievement_ids_earned()


def test_real_world_match_requires_42_percent_decoupling(game_env):
    module = game_env.module
    farm = game_env.farm
    farm.funds = 10_000
    for _ in range(4):
        game_env.invest_decoupling("capture")  # 4 * 0.10 = 0.40 < 0.42
    assert "real_world_match" not in module.achievement_ids_earned()
    game_env.invest_decoupling("capture")  # 5 * 0.10 = 0.50 >= 0.42
    assert "real_world_match" in module.achievement_ids_earned()


def test_outperforming_baseline_and_decoupling_dividend(game_env):
    module = game_env.module
    farm = game_env.farm
    farm.funds = 10_000
    for _ in range(6):
        game_env.grow_herd()
    for _ in range(5):
        game_env.invest_decoupling("capture")
    for _ in range(10):
        game_env.advance_round()
    earned = module.achievement_ids_earned()
    assert "outperforming_baseline" in earned
    assert farm.score() > farm.counterfactual_score()


def test_outperforming_baseline_false_before_minimum_round(game_env):
    module = game_env.module
    farm = game_env.farm
    farm.funds = 10_000
    for _ in range(6):
        game_env.grow_herd()
    for _ in range(5):
        game_env.invest_decoupling("capture")
    game_env.advance_round()  # round 1 -> 2, below OUTPERFORMING_BASELINE_MIN_ROUND
    assert "outperforming_baseline" not in module.achievement_ids_earned()


def test_clean_operator_requires_staying_below_pressure_cap(game_env):
    module = game_env.module
    farm = game_env.farm
    for _ in range(14):
        game_env.advance_round()
    # no herd at all -> zero pressure ever -> should be earned by round 15
    assert farm.round_number == 15
    assert "clean_operator" in module.achievement_ids_earned()


def test_clean_operator_false_if_pressure_ever_spiked(game_env):
    module = game_env.module
    farm = game_env.farm
    farm.funds = 10_000
    for _ in range(20):
        game_env.grow_herd()
    for _ in range(20):
        game_env.advance_round()  # unmanaged herd -> pressure will exceed 10%
    assert farm.max_pressure_fraction_seen >= module.CLEAN_OPERATOR_MAX_PRESSURE
    assert "clean_operator" not in module.achievement_ids_earned()


def test_long_haul_and_century_farm(game_env):
    module = game_env.module
    farm = game_env.farm
    for _ in range(23):
        game_env.advance_round()  # round_number: 1 -> 24
    assert farm.round_number == 24
    assert "long_haul" not in module.achievement_ids_earned()
    game_env.advance_round()  # round 25
    assert "long_haul" in module.achievement_ids_earned()
    for _ in range(25):
        game_env.advance_round()  # round 50
    assert "century_farm" in module.achievement_ids_earned()


def test_score_400(game_env):
    module = game_env.module
    farm = game_env.farm
    # Starting funds is exactly 300, so score_400 must not be trivially
    # earned on a brand-new farm.
    assert "score_400" not in module.achievement_ids_earned()
    farm.funds = 500
    assert "score_400" in module.achievement_ids_earned()


# --- checking achievements never mutates other game state -------------

def test_checking_achievements_does_not_mutate_state(game_env):
    module = game_env.module
    game_env.grow_herd()
    game_env.invest_decoupling("feed")
    before = module.get_state()
    module.achievement_ids_earned()
    module.achievements_summary()
    after = module.get_state()
    before.pop("achievements_earned", None)
    after.pop("achievements_earned", None)
    assert before == after


# --- progress readouts --------------------------------------------------

def test_progress_readout_for_growing_operation(game_env):
    module = game_env.module
    farm = game_env.farm
    farm.funds = 10_000
    for _ in range(4):
        game_env.grow_herd()
    summary = {entry["id"]: entry for entry in module.achievements_summary()}
    assert summary["growing_operation"]["progress"] == (4, module.GROWING_OPERATION_TARGET)


# --- toggle/panel --------------------------------------------------------

def test_achievements_panel_hidden_by_default(game_env):
    assert game_env.elements["achievements-panel"].hidden is True


def test_toggle_opens_and_closes_panel(game_env):
    game_env.toggle_achievements()
    assert game_env.elements["achievements-panel"].hidden is False
    game_env.toggle_achievements()
    assert game_env.elements["achievements-panel"].hidden is True


def test_panel_renders_every_catalog_entry(game_env):
    module = game_env.module
    game_env.toggle_achievements()
    panel = game_env.elements["achievements-panel"]
    # one card per achievement, plus one hub-link element
    assert len(panel.children) == len(module.ACHIEVEMENTS) + 1


def test_panel_marks_earned_card_distinctly(game_env):
    game_env.grow_herd()
    game_env.toggle_achievements()
    panel = game_env.elements["achievements-panel"]
    earned_cards = [c for c in panel.children if "achievement-card--earned" in c.className]
    assert len(earned_cards) == 1


def test_toggle_button_shows_earned_count(game_env):
    game_env.grow_herd()
    game_env.toggle_achievements()
    text = game_env.elements["achievements-toggle-button"].innerText
    assert "1/" in text


def test_panel_stays_live_across_render(game_env):
    game_env.toggle_achievements()
    game_env.grow_herd()  # render() is called inside on_grow_herd
    text = game_env.elements["achievements-toggle-button"].innerText
    assert "1/" in text


# --- unlock toast --------------------------------------------------------

def test_toast_hidden_before_any_unlock(game_env):
    assert game_env.elements["achievement-toast"].hidden is True


def test_toast_shows_on_first_unlock(game_env):
    game_env.grow_herd()
    toast = game_env.elements["achievement-toast"]
    assert toast.hidden is False
    assert "First Herd" in game_env.elements["achievement-toast-text"].innerText


def test_toast_auto_hides_after_timeout(game_env):
    game_env.grow_herd()
    assert game_env.elements["achievement-toast"].hidden is False
    game_env.timers.flush()
    assert game_env.elements["achievement-toast"].hidden is True


def test_loading_a_save_with_earned_achievements_does_not_flood_toasts(game_env):
    module = game_env.module
    game_env.grow_herd()
    game_env.timers.flush()  # dismiss the first-herd toast
    saved = module.get_state()
    assert "first_herd" in saved["achievements_earned"]

    module.load_state(saved)
    assert game_env.elements["achievement-toast"].hidden is True
