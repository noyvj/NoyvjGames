"""D-10: Bronze / Silver / Gold ranks. Each rank is a flat achievement id so the hub framework
(`achievements_earned` as a plain id list, planning/ACHIEVEMENTS-SYSTEM-DESIGN.md) keeps working."""

import json
import re
from pathlib import Path

import pytest

GAME_DIR = Path(__file__).resolve().parent.parent
FAMILIES = ["storm", "heritage", "retreat", "diversify", "monitor", "population"]


def _rank_entries(m):
    return [e for e in m.ACHIEVEMENTS if e.get("family")]


def _earned(m):
    return set(m.achievement_ids_earned())


# ---- catalog shape and the framework contract ----

def test_six_families_of_three_ranks_in_bronze_silver_gold_order(game_env):
    m = game_env.module
    ranked = _rank_entries(m)
    assert len(ranked) == 18
    assert [e["family"] for e in ranked[::3]] == FAMILIES
    for index in range(0, 18, 3):
        assert [e["rank"] for e in ranked[index:index + 3]] == ["bronze", "silver", "gold"]
        assert [e["id"] for e in ranked[index:index + 3]] == [f"{ranked[index]['family']}_{r}" for r in ("bronze", "silver", "gold")]


def test_ids_are_flat_snake_case_and_the_original_twenty_are_untouched(game_env):
    m = game_env.module
    for entry in m.ACHIEVEMENTS:
        assert re.fullmatch(r"[a-z][a-z0-9_]*", entry["id"])
        assert set(entry) >= {"id", "label", "description"}
    originals = [e["id"] for e in m.ACHIEVEMENTS if not e.get("family")]
    assert len(originals) == 20 and originals[0] == "underway" and originals[-1] == "fortified_in_time"


def test_labels_name_the_rank_in_words(game_env):
    for entry in _rank_entries(game_env.module):
        assert entry["label"].endswith(": " + entry["rank"].capitalize())


def test_every_rank_has_a_check_and_progress_ids_exist(game_env):
    m = game_env.module
    ids = {e["id"] for e in m.ACHIEVEMENTS}
    for entry in _rank_entries(m):
        assert entry["id"] in m.ACHIEVEMENT_CHECKS
    assert set(m.ACHIEVEMENT_PROGRESS) <= ids


def test_earned_list_stays_a_flat_list_of_catalog_ids_in_the_save(game_env):
    m = game_env.module
    m.state.monitoring_reports = 4
    saved = m.get_state()["achievements_earned"]
    assert isinstance(saved, list) and all(isinstance(i, str) for i in saved)
    assert {"monitor_bronze", "monitor_silver"} <= set(saved)
    json.dumps(saved)


def test_catalog_json_has_no_duplicate_ids_and_ranks_are_additive_fields():
    data = json.loads((GAME_DIR / "achievements.json").read_text(encoding="utf-8"))["achievements"]
    ids = [e["id"] for e in data]
    assert len(ids) == len(set(ids)) == 38
    for entry in data:
        assert ("family" in entry) == ("rank" in entry)


def test_nothing_ranked_is_earned_on_a_fresh_game(game_env):
    m = game_env.module
    assert not any(e["id"] in _earned(m) for e in _rank_entries(m))


# ---- storms ----

def _play_to_storm_season(m, invest_adaptation=0):
    state = m.state
    state.storm_mode = True
    for _ in range(invest_adaptation):
        state.invest("adaptation")
    while not state.storm_this_season():
        state.advance_season()


def test_a_weathered_storm_earns_bronze(game_env):
    m = game_env.module
    state = m.state
    state.funds = 10_000
    _play_to_storm_season(m, invest_adaptation=15)
    state.advance_season()
    assert state.last_storm_result != "Breached"
    assert state.storms_weathered == 1
    assert "storm_bronze" in _earned(m) and "storm_silver" not in _earned(m)


def test_a_breached_storm_counts_for_nothing(game_env):
    m = game_env.module
    state = m.state
    _play_to_storm_season(m)
    state.advance_season()
    assert state.last_storm_result == "Breached"
    assert state.storms_weathered == 0 and "storm_bronze" not in _earned(m)


def test_three_weathered_storms_earn_silver_and_clean_ones_earn_gold(game_env):
    m = game_env.module
    state = m.state
    state.funds = 100_000
    state.storm_mode = True
    for _ in range(15):
        state.invest("adaptation")
    state.sea_level = -10_000  # nothing floods, so every storm is "clean"
    monkey_rise = m.SettlementState.sea_rise_per_season
    try:
        m.SettlementState.sea_rise_per_season = lambda self: 0.0
        while state.storms_weathered < 3:
            state.advance_season()
    finally:
        m.SettlementState.sea_rise_per_season = monkey_rise
    assert state.storms_weathered == 3 and state.storms_clean == 3
    assert {"storm_bronze", "storm_silver", "storm_gold"} <= _earned(m)


def test_a_storm_season_with_a_new_flooded_row_is_not_clean(game_env):
    m = game_env.module
    state = m.state
    state.funds = 100_000
    state.storm_mode = True
    for _ in range(15):
        state.invest("adaptation")
    # Season 5 is a storm season: put the sea just under a row threshold so the rise floods a row that season.
    state.season = 5
    state.sea_level = m.row_flood_threshold(5) - 1.0
    before = m.flooded_row_count(state.sea_level)
    state.advance_season()
    assert m.flooded_row_count(state.sea_level) > before
    assert state.storms_weathered == 1 and state.storms_clean == 0


def test_storm_counters_round_trip_and_bad_values_are_cleaned(game_env):
    m = game_env.module
    state = m.state
    state.storms_weathered, state.storms_clean, state.early_retreats = 4, 2, 1
    saved = m.get_state()
    assert saved["ranks"] == {"storms_weathered": 4, "storms_clean": 2, "early_retreats": 1}
    m.state.storms_weathered = m.state.storms_clean = m.state.early_retreats = 0
    assert m.load_state(saved) is not False
    assert (m.state.storms_weathered, m.state.storms_clean, m.state.early_retreats) == (4, 2, 1)
    saved["ranks"] = {"storms_weathered": 1, "storms_clean": 99, "early_retreats": -5}
    m.load_state(saved)
    assert (m.state.storms_weathered, m.state.storms_clean, m.state.early_retreats) == (1, 1, 0)
    saved["ranks"] = "nonsense"
    m.load_state(saved)
    assert m.state.storms_weathered == 0
    del saved["ranks"]  # a save from before ranks existed
    m.load_state(saved)
    assert m.state.storms_weathered == 0


def test_a_fresh_state_save_omits_the_ranks_block(game_env):
    assert "ranks" not in game_env.module.get_state()


# ---- heritage ----

def test_heritage_ranks(game_env):
    m = game_env.module
    state = m.state
    state.funds = 10_000
    assert state.protect_heritage("lighthouse")
    assert "heritage_bronze" in _earned(m) and "heritage_silver" not in _earned(m)
    assert state.protect_heritage("reef")
    assert "heritage_silver" in _earned(m) and "heritage_gold" not in _earned(m)
    state.season = m.RANK_HERITAGE_GOLD_SEASON
    assert "heritage_gold" in _earned(m)


# ---- retreat ----

def test_retreat_ranks_and_the_ahead_of_the_water_gold(game_env):
    m = game_env.module
    state = m.state
    state.funds = 10_000
    assert state.managed_retreat()
    assert "retreat_bronze" in _earned(m) and "retreat_silver" not in _earned(m)
    assert state.early_retreats == 1 and "retreat_gold" not in _earned(m)
    assert state.managed_retreat()
    assert {"retreat_silver", "retreat_gold"} <= _earned(m)


def test_a_late_retreat_earns_silver_but_not_gold(game_env):
    m = game_env.module
    state = m.state
    state.funds = 10_000
    state.sea_level = 3 * m.ROW_FLOOD_STEP + 1  # three rows already under
    assert state.managed_retreat() and state.managed_retreat()
    assert state.early_retreats == 0
    assert "retreat_silver" in _earned(m) and "retreat_gold" not in _earned(m)


# ---- diversification ----

def test_diversification_ranks(game_env):
    m = game_env.module
    state = m.state
    state.funds = 100_000
    assert state.diversify("tourism")
    assert "diversify_bronze" in _earned(m) and "diversify_silver" not in _earned(m)
    state.diversify("tourism"), state.diversify("tourism")
    assert "diversify_silver" in _earned(m) and "diversify_gold" not in _earned(m)
    for _ in range(3):
        state.diversify("aquaculture")
    assert "diversify_gold" in _earned(m)


# ---- monitoring ----

def test_monitoring_ranks(game_env):
    m = game_env.module
    state = m.state
    state.funds = 100_000
    wanted = {1: {"monitor_bronze"}, 4: {"monitor_bronze", "monitor_silver"}, 8: {"monitor_bronze", "monitor_silver", "monitor_gold"}}
    done = 0
    while done < 8:
        state.season += m.MONITOR_COOLDOWN_SEASONS
        assert state.fund_monitoring()
        done += 1
        if done in wanted:
            assert {i for i in _earned(m) if i.startswith("monitor_")} == wanted[done]


def test_gold_monitoring_means_every_finding(game_env):
    m = game_env.module
    assert m.RANK_MONITOR_REPORTS[2] == len(m.CITIZEN_SCIENCE_FACTS)


# ---- population ----

def test_population_ranks_follow_the_peak_not_the_current_number(game_env):
    m = game_env.module
    state = m.state
    state.peak_population = 112
    assert "population_bronze" in _earned(m) and "population_silver" not in _earned(m)
    state.population = 20  # people leave; the rank stays
    assert "population_bronze" in _earned(m)
    state.peak_population = 130
    assert {"population_silver", "population_gold"} <= _earned(m)


def test_population_gold_is_reachable_by_ordinary_play(game_env):
    m = game_env.module
    state = m.state
    for _ in range(8):
        for category in ("adaptation", "adaptation", "output"):
            state.invest(category)
        state.advance_season()
    assert state.peak_population >= m.RANK_POPULATION[1]


# ---- progress and panel ----

def test_progress_readouts_are_current_and_target(game_env):
    m = game_env.module
    m.state.storms_clean = 2
    assert m.ACHIEVEMENT_PROGRESS["storm_gold"]() == (2, m.RANK_STORMS_CLEAN)
    m.state.protect_heritage  # exists
    assert m.ACHIEVEMENT_PROGRESS["heritage_silver"]() == (0, len(m.HERITAGE_SITES))
    assert m.ACHIEVEMENT_PROGRESS["heritage_gold"]() == (0, m.RANK_HERITAGE_GOLD_SEASON)
    assert m.ACHIEVEMENT_PROGRESS["diversify_gold"]() == (0, 6)


def test_summary_carries_family_and_rank(game_env):
    m = game_env.module
    by_id = {row["id"]: row for row in m.achievements_summary()}
    assert by_id["storm_gold"]["family"] == "storm" and by_id["storm_gold"]["rank"] == "gold"
    assert by_id["underway"]["family"] == "" and by_id["underway"]["rank"] == ""


def test_rank_summary_reports_the_best_rank_per_family(game_env):
    m = game_env.module
    m.state.monitoring_reports = 4
    row = next(r for r in m.rank_summary() if r["family"] == "monitor")
    assert row["best"] == "silver" and row["done"] == 2 and row["total"] == 3
    other = next(r for r in m.rank_summary() if r["family"] == "storm")
    assert other["best"] == "" and other["done"] == 0


def test_panel_spells_out_the_rank_and_summarises_families(game_env):
    m = game_env.module
    m.state.monitoring_reports = 4
    game_env.toggle_achievements()
    panel = game_env.elements["achievements-panel"]
    texts = []

    def walk(node):
        texts.append(node.innerText or "")
        for child in node.children:
            walk(child)

    walk(panel)
    joined = "\n".join(texts)
    assert "Silver rank" in joined and "Gold rank" in joined and "Bronze rank" in joined
    assert "Ranks:" in joined and "Citizen Scientist Silver (2/3)" in joined
    cards = [c for c in panel.children if getattr(getattr(c, "dataset", None), "achievementRank", "")]
    assert len(cards) == 18
    assert all("achievement-card--rank-" in c.className for c in cards)


def test_toast_names_a_newly_earned_rank(game_env):
    m = game_env.module
    m._sync_earned_and_toast()
    m.state.monitoring_reports = 1
    m._sync_earned_and_toast()
    assert "Citizen Scientist: Bronze" in game_env.elements["achievement-toast"].innerText
