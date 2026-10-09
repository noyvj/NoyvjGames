"""2026-10-09 pass: D-19 affordability and pin, D-20 net-funds chip, GD-19 pinned goal, GD-25 quiet seasons,
GD-26 harbour-name dice."""

import pytest


@pytest.fixture
def storage(game_env, monkeypatch):
    store = {}
    monkeypatch.setattr(game_env.module, "_read_local_storage_item", lambda key: store.get(key))
    monkeypatch.setattr(game_env.module, "_write_local_storage_item", lambda key, value: store.__setitem__(key, value))
    return store


# ---- D-20 net-funds chip ----

def test_preview_shows_funds_after_buying_and_after_upkeep(game_env):
    m = game_env.module
    assert m.net_funds_preview("output")["after_purchase"] == m.STARTING_FUNDS - m.INVEST_COST["output"]
    assert m.net_funds_preview("output")["upkeep"] == 0
    m.state.heritage["lighthouse"] = m.HERITAGE_PROTECTED
    p = m.net_funds_preview("output")
    assert p["upkeep"] == m.HERITAGE_UPKEEP and p["after_upkeep"] == p["after_purchase"] - m.HERITAGE_UPKEEP
    assert "after this season's upkeep of 6" in m.net_funds_text("output")


def test_preview_says_what_is_missing_when_unaffordable(game_env):
    m = game_env.module
    m.state.funds = 10
    p = m.net_funds_preview("adaptation")
    assert p["affordable"] is False
    assert "20 more funds are needed" in m.net_funds_text("adaptation")
    assert m.net_funds_text("nonsense") == ""


def test_chip_follows_hover_and_clears_on_leave(game_env):
    chip = game_env.elements["net-funds-chip"]
    game_env.elements["output-invest-button"].dispatch("mouseenter", None)
    assert "Output" in chip.innerText and "after buying" in chip.innerText
    game_env.elements["output-invest-button"].dispatch("mouseleave", None)
    assert chip.innerText == ""
    game_env.elements["reduction-invest-button"].dispatch("focus", None)
    assert "Acidity Reduction" in chip.innerText
    game_env.elements["reduction-invest-button"].dispatch("blur", None)
    assert chip.innerText == ""


# ---- D-19 affordability ----

def test_seasons_to_afford(game_env):
    m = game_env.module
    assert m.seasons_to_afford(100, funds=150, income=5) == 0
    assert m.seasons_to_afford(100, funds=40, income=20) == 3
    assert m.seasons_to_afford(100, funds=40, income=0) is None
    assert m.seasons_to_afford(100, funds=40, income=-3) is None


def test_net_income_uses_output_diversification_and_upkeep(game_env):
    m = game_env.module
    assert m.season_net_income() == 0
    m.state.capacity["output"] = 5
    income = m.season_net_income()
    assert income == pytest.approx(5 * m.OUTPUT_INCOME_PER_UNIT * m.state.fish_yield_multiplier())
    m.state.heritage["lighthouse"] = m.HERITAGE_PROTECTED
    assert m.season_net_income() == pytest.approx(income - m.HERITAGE_UPKEEP)


def test_targets_list_the_tiers_ahead_and_open_diversification(game_env):
    m = game_env.module
    ids = [t[0] for t in m.afford_targets()]
    assert ids[:4] == ["tier1", "tier2", "tier3", "tier4"] and "div-tourism" in ids and "div-aquaculture" in ids
    cost_tier1 = dict((t[0], t[2]) for t in m.afford_targets())["tier1"]
    assert cost_tier1 == 3 * m.INVEST_COST["adaptation"]
    m.state.capacity["adaptation"] = 6
    assert [t[0] for t in m.afford_targets()][0] == "tier3"
    m.state.diversification["tourism"] = m.DIVERSIFY_MAX_LEVEL
    assert "div-tourism" not in [t[0] for t in m.afford_targets()]


def test_lines_say_when_and_mark_the_pinned_target(game_env, storage):
    m = game_env.module
    m.state.funds = 1000
    assert any("tier 1" in l and "affordable now" in l for l in m.afford_lines())
    m.state.funds = 0
    assert any("not affordable at current income" in l for l in m.afford_lines())
    m.state.capacity["output"] = 10
    assert any("affordable in" in l and "season" in l for l in m.afford_lines())


def test_pin_is_remembered_and_shown(game_env, storage):
    m = game_env.module
    game_env.elements["afford-pin-select"].value = "tier2"
    m.on_afford_pin_change()
    assert storage[m.AFFORD_PIN_KEY] == "tier2"
    assert any(l.startswith("\U0001F4CC") for l in m.afford_lines())
    assert "Seawalls" in game_env.elements["afford-pinned"].innerText
    m.load_afford_pin()
    assert m.afford_pin == "tier2"
    m.state.capacity["adaptation"] = 6  # the pinned tier is reached: the pin quietly drops from the list
    m.render_afford()
    assert game_env.elements["afford-pinned"].innerText == ""


# ---- GD-25 quiet seasons ----

def test_quiet_seasons_count_back_from_the_latest(game_env):
    m = game_env.module
    s = m.state
    assert s.quiet_seasons() == 0
    s.acidity_history = [0.0, 0.0, 0.0]
    assert s.quiet_seasons() == 3
    s.acidity_history = [1.0, 2.0, 2.0, 1.5, 1.5]
    assert s.quiet_seasons() == 3
    s.acidity_history = [1.0, 2.0, 3.0]
    assert s.quiet_seasons() == 0


def test_quiet_display_gets_a_star_frame_at_five_and_ten(game_env):
    m = game_env.module
    el = game_env.elements["quiet-seasons-display"]
    m.state.acidity_history = [0.0] * 4
    m.render_quiet()
    assert "quiet-glow" not in el.className and "★" not in el.innerText
    m.state.acidity_history = [0.0] * 5
    m.render_quiet()
    assert "quiet-glow-5" in el.className and el.innerText.endswith("★")
    m.state.acidity_history = [0.0] * 10
    m.render_quiet()
    assert "quiet-glow-10" in el.className and el.innerText.endswith("★★")


# ---- GD-19 pinned goal ----

def test_pinning_and_progress(game_env):
    m = game_env.module
    assert m.goal_progress() is None
    assert m.pin_goal("nope") is False
    assert m.pin_goal("rows4") is True
    label, current, target, reached = m.goal_progress()
    assert label == "Keep 4 rows dry" and target == 4 and reached == (current >= 4)
    assert m.pin_goal("") is True and m.goal_progress() is None


def test_the_ping_fires_once_when_the_goal_is_reached(game_env):
    m = game_env.module
    m.pin_goal("funds500")
    assert m.check_pinned_goal() is False
    m.state.funds = 600
    assert m.check_pinned_goal() is True
    assert any("Goal reached" in line for line in m.state.ticker_log)
    assert any("Goal reached" in e["text"] for e in m.state.chronicle)
    assert m.check_pinned_goal() is False  # once only


def test_pinning_a_goal_already_met_does_not_ping(game_env):
    m = game_env.module
    m.state.funds = 900
    m.pin_goal("funds500")
    assert m.state.pinned_goal_reached is True and m.check_pinned_goal() is False


def test_goal_is_checked_after_investing_and_advancing(game_env):
    m = game_env.module
    m.state.capacity["adaptation"] = 2
    m.pin_goal("tier3")
    m.state.funds = 1000
    for _ in range(4):
        game_env.invest("adaptation")
    assert not m.state.pinned_goal_reached  # tier 3 needs 10
    m.state.capacity["adaptation"] = 9
    game_env.invest("adaptation")
    assert m.state.pinned_goal_reached is True


def test_goal_ui_and_save(game_env):
    m = game_env.module
    game_env.elements["goal-select"].value = "pop200"
    m.on_goal_change()
    assert m.state.pinned_goal == "pop200"
    assert "Pinned goal" not in game_env.elements["goal-text"].innerText and "Reach 200 population" in game_env.elements["goal-text"].innerText
    assert "pinned_goal" in m.get_state() and m.get_state()["pinned_goal"]["id"] == "pop200"
    state = m.get_state()
    m.pin_goal("")
    assert "pinned_goal" not in m.get_state()
    m.load_state(state)
    assert m.state.pinned_goal == "pop200"
    state["pinned_goal"] = {"id": "nonsense", "reached": True}
    m.load_state(state)
    assert m.state.pinned_goal == "" and m.state.pinned_goal_reached is False
    state["pinned_goal"] = "oops"
    m.load_state(state)
    assert m.state.pinned_goal == ""


# ---- GD-26 name dice ----

def test_names_walk_the_list_and_never_repeat_the_current_one(game_env):
    m = game_env.module
    seen = [m.roll_harbor_name() for _ in range(len(m.HARBOR_NAMES))]
    assert all(n in m.HARBOR_NAMES for n in seen) and len(set(seen)) > len(seen) // 2
    m.state.settlement_name = seen[0]
    assert all(m.roll_harbor_name() != seen[0] for _ in range(40))


def test_rolling_sets_the_name_the_input_and_the_chronicle(game_env):
    m = game_env.module
    game_env.elements["roll-name-button"].dispatch("click", None)
    name = m.state.settlement_name
    assert name in m.HARBOR_NAMES and game_env.elements["settlement-name-input"].value == name
    assert any(e["text"] == f"Founded as {name}." for e in m.state.chronicle)
    game_env.elements["roll-name-button"].dispatch("click", None)
    second = m.state.settlement_name
    assert second != name and any(e["text"] == f"The harbour came to be called {second}." for e in m.state.chronicle)
    assert len(m.state.settlement_name) <= m.SETTLEMENT_NAME_MAX
    assert all(len(n) <= m.SETTLEMENT_NAME_MAX for n in m.HARBOR_NAMES)


# ---- GD-14 balanced seasons ----

def _invest_all(env):
    for category in ("output", "reduction", "adaptation"):
        env.invest(category)


def test_investing_in_all_three_pays_a_bonus_and_builds_a_streak(game_env):
    m = game_env.module
    s = m.state
    s.funds = 1000
    s.capacity["output"] = 10
    _invest_all(game_env)
    funds_before = s.funds
    s.advance_season()
    assert s.balance_streak == 1
    assert s.funds > funds_before
    for expected in (2, 3, 4):
        _invest_all(game_env)
        s.advance_season()
        assert s.balance_streak == expected


def test_the_multiplier_steps_up_and_caps(game_env):
    m = game_env.module
    s = m.state
    s.funds = 100000
    seen = []
    for _ in range(5):
        _invest_all(game_env)
        seen.append(s.balance_multiplier())
        s.advance_season()
    assert seen == [1.1, 1.2, 1.3, 1.3, 1.3]


def test_skipping_a_category_breaks_the_streak(game_env):
    m = game_env.module
    s = m.state
    s.funds = 100000
    for _ in range(2):
        _invest_all(game_env)
        s.advance_season()
    assert s.balance_streak == 2
    game_env.invest("output")
    game_env.invest("reduction")
    s.advance_season()
    assert s.balance_streak == 0 and s.season_invested == set()


def test_the_bonus_is_exactly_the_multiplier_on_income(game_env):
    m = game_env.module
    s = m.state
    s.capacity["output"] = 10
    s.funds = 1000
    plain = m.copy.deepcopy(s)
    m.state = plain
    plain.advance_season()
    plain_gain = plain.funds - 1000
    m.state = s
    for category in ("output", "reduction", "adaptation"):
        s.season_invested.add(category)  # as if invested, without changing capacity or funds
    s.advance_season()
    assert s.funds - 1000 == pytest.approx(plain_gain * 1.1)


def test_balance_text_and_save(game_env):
    m = game_env.module
    s = m.state
    assert "balanced income bonus" in m.balance_text()
    s.funds = 1000
    game_env.invest("output")
    assert "Acidity Reduction" in m.balance_text() and "Adaptation" in m.balance_text()
    assert "balance" in m.get_state()
    state = m.get_state()
    s.season_invested, s.balance_streak = set(), 0
    assert "balance" not in m.get_state()
    m.load_state(state)
    assert s.season_invested == {"output"}
    state["balance"] = {"streak": -4, "invested": ["output", "bogus", 5]}
    m.load_state(state)
    assert s.balance_streak == 0 and s.season_invested == {"output"}


# ---- GD-28 domino season ----

def test_three_rows_flooding_at_once_starts_a_comeback_discount(game_env):
    m = game_env.module
    s = m.state
    s.sea_level = m.row_flood_threshold(m.COASTLINE_ROWS - 1) - 0.01  # the lowest row is about to flood
    rows_before = m.flooded_row_count(s.sea_level)
    s.sea_rise_per_season = lambda: 3 * m.ROW_FLOOD_STEP  # a big rise in one season
    s.advance_season()
    assert m.flooded_row_count(s.sea_level) - rows_before >= m.DOMINO_MIN_ROWS
    assert s.domino_seasons_left == m.DOMINO_DISCOUNT_SEASONS and s.domino_count == 1
    assert any("Domino season" in line for line in s.ticker_log)
    assert s.invest_cost("adaptation") == 23  # 30 less 25%, rounded up
    assert s.invest_cost("output") == m.INVEST_COST["output"]


def test_the_discount_runs_out_and_buttons_show_the_price(game_env):
    m = game_env.module
    s = m.state
    s.domino_seasons_left = 2
    m.render()
    assert game_env.elements["adaptation-invest-button"].innerText == f"Invest ({s.invest_cost('adaptation')})"
    assert s.invest_cost("adaptation") < m.INVEST_COST["adaptation"]
    assert "Domino comeback" in game_env.elements["domino-display"].innerText
    s.advance_season()
    s.advance_season()
    assert s.domino_seasons_left == 0 and s.invest_cost("adaptation") == m.INVEST_COST["adaptation"]
    m.render()
    assert game_env.elements["domino-display"].hidden is True


def test_a_small_rise_is_not_a_domino_and_domino_state_saves(game_env):
    m = game_env.module
    s = m.state
    s.advance_season()
    assert s.domino_count == 0 and "domino" not in m.get_state()
    s.domino_seasons_left, s.domino_count = 1, 2
    state = m.get_state()
    s.domino_seasons_left, s.domino_count = 0, 0
    m.load_state(state)
    assert (s.domino_seasons_left, s.domino_count) == (1, 2)
    state["domino"] = {"left": 99, "count": "x"}
    m.load_state(state)
    assert s.domino_seasons_left == m.DOMINO_DISCOUNT_SEASONS and s.domino_count == 0


# ---- GD-27 heritage rescue ----

def test_protecting_a_site_at_the_last_second_is_a_rescue(game_env):
    m = game_env.module
    s = m.state
    site = m.HERITAGE_SITES[0]
    s.funds = 1000
    s.sea_level = m.row_flood_threshold(site["row"]) - 0.5 * s.sea_rise_per_season()
    assert s.seasons_until_flood(site["row"]) <= 1
    assert s.protect_heritage(site["id"]) is True
    assert s.last_rescue == site["id"]
    assert any("SAVED" in line for line in s.ticker_log) and any("last second" in e["text"] for e in s.chronicle)
    m.render()
    assert game_env.elements["rescue-burst"].hidden is False and "SAVED" in game_env.elements["rescue-burst"].innerText
    assert s.last_rescue is None  # shown once


def test_an_early_protection_is_not_a_rescue(game_env):
    m = game_env.module
    s = m.state
    s.funds = 1000
    assert m.state.seasons_until_flood(m.HERITAGE_SITES[0]["row"]) > 1
    s.protect_heritage(m.HERITAGE_SITES[0]["id"])
    assert s.last_rescue is None and not any("SAVED" in line for line in s.ticker_log)


# ---- GD-30 season report card ----

def test_report_chips_use_arrows_and_words_not_just_colour(game_env):
    m = game_env.module
    chips = m.season_report_chips({"funds": 100, "acidity": 1.0, "fish": 0.9}, {"funds": 130, "acidity": 1.8, "fish": 0.81})
    texts = [c[0] for c in chips]
    assert texts[0].startswith("▲ Funds +30") and "good" in texts[0]
    assert texts[1].startswith("▲ Acidity +0.8") and "watch" in texts[1]
    assert texts[2].startswith("▼ Fish -9%") and "watch" in texts[2]
    steady = m.season_report_chips({"funds": 5, "acidity": 1, "fish": 1}, {"funds": 5, "acidity": 1, "fish": 1})
    assert all("unchanged" in c[0] for c in steady)


def test_the_overlay_shows_after_advancing_and_not_with_reduced_motion(game_env, monkeypatch):
    m = game_env.module
    card = game_env.elements["season-report-card"]
    monkeypatch.setattr(m, "_reduced_motion", lambda: False)
    m.on_advance_season()
    assert card.hidden is False and card.innerHTML.count("report-chip") >= 3
    card.hidden = True
    monkeypatch.setattr(m, "_reduced_motion", lambda: True)
    m.on_advance_season()
    assert card.hidden is True


# ---- GD-20 rewind ----

def test_rewind_is_unavailable_until_a_season_has_been_advanced(game_env):
    m = game_env.module
    assert m.can_rewind() is False
    m.on_rewind()
    assert m.state.season == 1 and m.state.rewind_used is False


def test_rewind_retracts_the_last_advance_once_and_marks_the_run(game_env):
    m = game_env.module
    s = m.state
    game_env.invest("output")
    m.on_advance_season()
    funds_after_first = s.funds
    season_after_first = s.season
    m.on_advance_season()
    assert s.season == season_after_first + 1
    assert m.can_rewind() is True and game_env.elements["rewind-button"].disabled is False
    game_env.elements["rewind-button"].dispatch("click", None)
    s = m.state  # load_state keeps the same object, but be explicit
    assert s.season == season_after_first and s.funds == pytest.approx(funds_after_first)
    assert s.rewind_used is True and m.can_rewind() is False
    assert game_env.elements["tin-hat-badge"].hidden is False and game_env.elements["rewind-button"].disabled is True
    assert "Rewound once" in s.session_summary_text()
    assert any("Rewound" in line for line in s.ticker_log) and any("turned back the clock" in e["text"] for e in s.chronicle)
    m.on_rewind()
    assert s.season == season_after_first  # a second try does nothing


def test_rewinding_an_x5_run_retracts_the_whole_click(game_env):
    m = game_env.module
    m.on_advance_x5()
    assert m.state.season > 1
    m.on_rewind()
    assert m.state.season == 1


def test_rewind_use_is_saved_and_a_new_snapshot_does_not_restore_the_charge(game_env):
    m = game_env.module
    m.on_advance_season()
    m.on_advance_season()
    m.on_rewind()
    saved = m.get_state()
    assert saved["run_stats"]["rewind_used"] is True
    m.on_advance_season()
    assert m.can_rewind() is False


# ---- GD-24 ironman ----

def _advance_many(m, n):
    for _ in range(n):
        m.state.advance_season()


def test_twenty_hard_lag_seasons_without_rewind_earn_the_anchor(game_env):
    m = game_env.module
    m.state.set_hard_lag_mode(True)
    _advance_many(m, m.IRONMAN_SEASONS - 1)
    assert m.state.ironman_earned is False
    m.state.advance_season()
    assert m.state.ironman_earned is True
    assert any("Ironman" in line for line in m.state.ticker_log)
    m.render()
    assert game_env.elements["ironman-badge"].hidden is False and "Hard-lag ironman" in m.state.session_summary_text()


def test_turning_hard_lag_off_rewinding_or_replaying_forfeits_it(game_env):
    m = game_env.module
    m.state.set_hard_lag_mode(True)
    _advance_many(m, 5)
    m.state.set_hard_lag_mode(False)
    m.state.advance_season()
    m.state.set_hard_lag_mode(True)
    _advance_many(m, 25)
    assert m.state.ironman_earned is False

    m2 = game_env.module
    m2.state.__init__()
    m2.state.set_hard_lag_mode(True)
    m2.state.rewind_used = True
    _advance_many(m2, 22)
    assert m2.state.ironman_earned is False

    m2.state.__init__()
    m2.state.set_hard_lag_mode(True)
    m2.state.replay_count = 1
    _advance_many(m2, 22)
    assert m2.state.ironman_earned is False


# ---- GD-23 speedrun trackers ----

def test_clicks_and_active_seconds_are_counted_with_an_idle_cap(game_env, monkeypatch):
    m = game_env.module
    clock = [1000.0]
    monkeypatch.setattr(m.time, "time", lambda: clock[0])
    m.note_action()
    clock[0] += 5
    m.note_action()
    clock[0] += 600  # walked away
    m.note_action()
    assert m.state.actions_count == 3
    assert m.state.active_seconds == pytest.approx(5 + m.IDLE_CAP_SECONDS)


def test_reaching_the_top_tier_records_the_totals_and_the_personal_best(game_env, storage, monkeypatch):
    m = game_env.module
    s = m.state
    s.funds = 100000
    clock = [0.0]
    monkeypatch.setattr(m.time, "time", lambda: clock[0])
    handler = m._make_invest_handler("adaptation")
    for _ in range(m.ADAPTATION_TIERS[-1]["threshold"]):
        clock[0] += 2
        handler()
    assert s.maxtier_actions == m.ADAPTATION_TIERS[-1]["threshold"]
    assert s.maxtier_seconds == pytest.approx(2 * (s.maxtier_actions - 1))
    best = m.load_speedrun_best()
    assert best["actions"] == s.maxtier_actions
    # a slower later run does not replace it, a faster one does
    s.maxtier_actions, s.maxtier_seconds = 99, 500.0
    assert m.record_speedrun() is False
    s.maxtier_actions, s.maxtier_seconds = 5, 3.0
    assert m.record_speedrun() is True and m.load_speedrun_best() == {"actions": 5.0, "seconds": 3.0}
    assert "Best: 5 clicks, 3 s" in m.speedrun_text()


def test_speedrun_text_before_the_top_tier_and_bad_storage(game_env, storage):
    m = game_env.module
    assert "not reached yet" in m.speedrun_text() and "No speedrun best yet" in m.speedrun_text()
    storage[m.SPEEDRUN_KEY] = "garbage"
    assert m.load_speedrun_best() == {}
    storage[m.SPEEDRUN_KEY] = '{"actions": -3, "seconds": "x"}'
    assert m.load_speedrun_best() == {}


def test_run_stats_round_trip_and_validate(game_env):
    m = game_env.module
    s = m.state
    assert "run_stats" not in m.get_state()
    s.actions_count, s.active_seconds, s.maxtier_actions, s.maxtier_seconds = 12, 34.5, 10, 20.0
    s.ironman_earned = True
    saved = m.get_state()
    s.__init__()
    m.load_state(saved)
    assert (s.actions_count, s.active_seconds, s.maxtier_actions, s.maxtier_seconds, s.ironman_earned) == (12, 34.5, 10, 20.0, True)
    saved["run_stats"] = {"actions": -5, "seconds": "x", "maxtier_actions": "a", "maxtier_seconds": 1, "ironman": "yes", "hard_lag_all_run": False}
    m.load_state(saved)
    assert s.actions_count == 0 and s.active_seconds == 0.0 and s.maxtier_actions is None
    assert s.ironman_earned is False and s.hard_lag_all_run is False


# ---- GD-21 storm forecast range ----

def test_range_is_plus_minus_fifteen_percent(game_env):
    m = game_env.module
    low, high = m.storm_range()
    surge = m.state.storm_surge_strength()
    assert low == pytest.approx(surge * 0.85) and high == pytest.approx(surge * 1.15)


def test_overtop_chance_follows_the_tier_and_the_range(game_env):
    m = game_env.module
    s = m.state
    assert m.overtop_chance() == 1.0  # no adaptation turns back nothing
    s.capacity["adaptation"] = 6  # seawalls, capacity 22 against an 18 surge (15.3 to 20.7)
    assert m.overtop_chance() == 0.0
    s.storm_log = [1] * 6  # a surge of 36 (30.6 to 41.4) against capacity 22
    assert m.overtop_chance() == 1.0
    s.capacity["adaptation"] = 10  # reinforced, capacity 34
    chance = m.overtop_chance()
    assert 0.0 < chance < 1.0
    low, high = m.storm_range()
    assert chance == pytest.approx((high - 34.0) / (high - low))


def test_chance_only_falls_as_adaptation_grows(game_env):
    m = game_env.module
    s = m.state
    s.storm_log = [1] * 4
    chances = []
    for threshold in (0, 3, 6, 10, 15):
        s.capacity["adaptation"] = threshold
        chances.append(m.overtop_chance())
    assert chances == sorted(chances, reverse=True)


def test_forecast_text_and_bell_show_the_range_and_a_label(game_env):
    import xml.etree.ElementTree as ET
    m = game_env.module
    s = m.state
    assert "off" in m.storm_forecast_text()
    s.set_storm_mode(True)
    text = m.storm_forecast_text()
    assert "surge of" in text and "chance to overtop" in text and "%" in text
    svg = m.storm_bell_svg()
    ET.fromstring(svg)
    assert "chance to overtop your seawalls" in svg and "wall " in svg
    m.render()
    assert "<svg" in game_env.elements["storm-bell"].innerHTML
    s.set_storm_mode(False)
    m.render()
    assert game_env.elements["storm-bell"].innerHTML == ""


# ---- D-29 plain labels, D-30 animation pause (file checks for the browser-only part) ----

def test_plain_text_replaces_jargon_only_when_on(game_env, storage):
    m = game_env.module
    original = "Adaptation tier: Seawalls (60% damage dampening) after lag"
    assert m.plain(original) == original
    storage[m.PLAIN_LABELS_KEY] = "true"
    out = m.plain(original)
    assert "Sea defences tier" in out and "damage protection" in out and "delay" in out
    assert "dampening" not in out and "Adaptation" not in out
    assert m.plain("Harder Lag: Off (turn on)") == "Slower fish effects: Off (turn on)"
    assert m.plain(5) == 5


def test_render_uses_the_plain_words(game_env, storage):
    m = game_env.module
    storage[m.PLAIN_LABELS_KEY] = "true"
    m.render()
    assert "protection" in game_env.elements["adaptation-tier-display"].innerText
    assert "dampening" not in game_env.elements["adaptation-tier-display"].innerText
    assert "Sea defences" in game_env.elements["adaptation-invest-button"].getAttribute("aria-label")
    assert game_env.elements["hard-lag-toggle-button"].innerText.startswith("Slower fish effects")
    storage[m.PLAIN_LABELS_KEY] = "false"
    m.render()
    assert "dampening" in game_env.elements["adaptation-tier-display"].innerText


def test_settings_and_page_carry_the_plain_label_pieces():
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    html = (root / "index.html").read_text(encoding="utf-8")
    js = (root / "settings.js").read_text(encoding="utf-8")
    assert 'id="plain-labels-checkbox"' in html and html.count('data-plain="') == 3
    assert "tide-plain-labels" in js and 'globals.get("render")' in js


def test_ui_and_css_pause_animations_when_hidden_or_low_power():
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    js = (root / "ui.js").read_text(encoding="utf-8")
    css = (root / "style.css").read_text(encoding="utf-8")
    assert 'visibilityState === "hidden"' in js and "data-anim-paused" in js and "getBattery" in js
    assert 'html[data-anim-paused="true"] *' in css and "animation-play-state: paused" in css


# ---- GD-17 quips ----

def test_quip_follows_real_state_and_never_repeats_back_to_back(game_env, storage):
    m = game_env.module
    s = m.state
    s.funds = 10
    first = m.speak_quip()
    assert first == "Purse is nearly empty, boss. We make do."
    assert m.speak_quip() == ""  # nothing else applies, and the same line is not repeated
    s.capacity["adaptation"] = 6
    assert "Wall's holding" in m.speak_quip()


def test_a_flooded_row_and_a_rescue_take_priority(game_env, storage):
    m = game_env.module
    assert "lower yard" in m.speak_quip(new_rows=1)
    m._quip["last"] = ""
    assert "lamp stays lit" in m.speak_quip(new_rows=1, rescued=True)


def test_muting_silences_quips_and_clears_the_line(game_env, storage):
    m = game_env.module
    m.state.funds = 10
    assert m.speak_quip()
    storage[m.QUIPS_MUTED_KEY] = "true"
    assert m.speak_quip() == "" and m._quip["text"] == ""
    m.render()
    assert game_env.elements["harbor-quip"].hidden is True


def test_the_quip_shows_after_advancing_and_is_covered_by_the_story_toggle(game_env, storage):
    from pathlib import Path
    m = game_env.module
    m.state.funds = 0
    m.state.advance_season = lambda: None  # no real season, only the quip path
    m.on_advance_season()
    assert "Harbour master:" in game_env.elements["harbor-quip"].innerText and game_env.elements["harbor-quip"].hidden is False
    html = (Path(__file__).resolve().parent.parent / "index.html").read_text(encoding="utf-8")
    assert "#harbor-quip" in html.split("story-toggle.js")[1].split(">")[0]


# ---- GD-18 critters ----

def test_the_seal_needs_five_low_acidity_seasons(game_env):
    m = game_env.module
    s = m.state
    s.acidity_history = [0.5] * 4
    assert m.critter_available("seal") is False
    s.acidity_history = [0.5] * 5
    assert m.critter_available("seal") is True
    s.acidity_history = [0.5] * 4 + [m.CRITTER_LOW_ACIDITY + 1]
    assert m.critter_available("seal") is False


def test_the_whale_needs_a_protected_site_and_a_storm(game_env):
    m = game_env.module
    s = m.state
    s.heritage["lighthouse"] = m.HERITAGE_PROTECTED
    assert m.critter_available("whale") is False
    s.storm_log = [1]
    assert m.critter_available("whale") is True
    s.heritage["lighthouse"] = m.HERITAGE_LOST
    assert m.critter_available("whale") is False


def test_clicking_a_critter_logs_it_once_and_the_list_shows_it(game_env):
    m = game_env.module
    s = m.state
    s.acidity_history = [0.5] * 5
    m.render()
    button = game_env.elements["critter-seal"]
    assert button.hidden is False and "grey seal" in button.innerText
    assert "Unseen" in game_env.elements["sightings-list"].innerText
    button.dispatch("click", None)
    assert s.sightings == ["seal"] and button.hidden is True
    assert "Grey seal: seen" in game_env.elements["sightings-list"].innerText
    assert any("Sightings list" in line for line in s.ticker_log) and any("sighted off the harbour" in e["text"] for e in s.chronicle)
    assert m.log_sighting("seal") is False and s.sightings == ["seal"]
    assert m.log_sighting("dragon") is False


def test_sightings_save_and_load_safely(game_env):
    m = game_env.module
    s = m.state
    assert "sightings" not in m.get_state()
    s.sightings = ["seal"]
    saved = m.get_state()
    s.sightings = []
    m.load_state(saved)
    assert s.sightings == ["seal"]
    saved["sightings"] = ["whale", "whale", "kraken", 7]
    m.load_state(saved)
    assert s.sightings == ["whale"]
    saved["sightings"] = "oops"
    m.load_state(saved)
    assert s.sightings == []


# ---- GD-22 scene themes, D-31 achievement cards ----

def test_themes_unlock_with_their_achievements(game_env, storage):
    m = game_env.module
    assert m.theme_unlocked("default") is True and m.theme_unlocked("dusk") is False
    m.state.fortified_in_time_earned = True
    assert "fortified_in_time" in m.achievement_ids_earned()
    assert m.theme_unlocked("dusk") is True and m.theme_unlocked("coral_sand") is False
    assert m.theme_unlocked("nope") is False


def test_a_locked_or_unknown_choice_falls_back_to_the_default(game_env, storage):
    m = game_env.module
    storage[m.SCENE_THEME_KEY] = "dusk"
    assert m.chosen_scene_theme() == "default"
    m.state.fortified_in_time_earned = True
    assert m.chosen_scene_theme() == "dusk"
    storage[m.SCENE_THEME_KEY] = "kraken"
    assert m.chosen_scene_theme() == "default"


def test_selecting_a_theme_stores_it_and_sets_the_page_attribute(game_env, storage):
    m = game_env.module
    m.state.fortified_in_time_earned = True
    select = game_env.elements["scene-theme-select"]
    select.value = "dusk"
    m.on_scene_theme_change()
    assert storage[m.SCENE_THEME_KEY] == "dusk"
    root = getattr(m.document, "documentElement", None)
    if root is not None:
        assert root.getAttribute("data-scene-theme") == "dusk"
    select.value = "storm_glass"  # locked: refused
    m.on_scene_theme_change()
    assert storage[m.SCENE_THEME_KEY] == "dusk"


def test_locked_options_are_disabled_and_name_their_unlock(game_env, storage):
    m = game_env.module
    m.render_scene_theme()
    options = {o.value: o for o in game_env.elements["scene-theme-select"].children}
    assert options["default"].disabled is False
    assert options["dusk"].disabled is True and "Fortified In Time" in options["dusk"].innerText


def test_achievement_cards_carry_a_coral_or_a_hollow_wave(game_env):
    m = game_env.module
    m.achievements_open = True
    m.update_achievements_display()
    cards = [c for c in game_env.elements["achievements-panel"].children if "achievement-card" in (c.className or "")]
    assert cards
    for card in cards:
        glyph = card.children[0]
        earned = "achievement-card--earned" in card.className
        assert glyph.innerText == (m.ACHIEVEMENT_GLYPH_EARNED if earned else m.ACHIEVEMENT_GLYPH_LOCKED)
        assert ("--locked" in glyph.className) == (not earned)


def test_the_ripple_class_is_added_and_css_stops_it_for_reduced_motion():
    from pathlib import Path
    css = (Path(__file__).resolve().parent.parent / "style.css").read_text(encoding="utf-8")
    assert "achievement-toast--ripple" in css and 'html[data-reduced-motion="true"] .achievement-toast--ripple' in css


# ---- D-28 delta breakdown ----

def test_no_breakdown_before_the_first_season(game_env):
    m = game_env.module
    assert "No season has been resolved yet" in m.delta_breakdown_text("funds")
    assert "No season has been resolved yet" in m.delta_breakdown_text("acidity")


def test_acidity_parts_add_up_to_the_change(game_env):
    m = game_env.module
    s = m.state
    s.capacity["output"], s.capacity["reduction"] = 6, 2
    s.advance_season()
    data = s.last_breakdown["acidity"]
    assert sum(v for _l, v in data["parts"]) == pytest.approx(data["to"] - data["from"])
    text = m.delta_breakdown_text("acidity")
    assert "Output pushing acidity up" in text and "Reduction pulling it down" in text and "(" in text.splitlines()[0]


def test_funds_parts_add_up_with_upkeep_and_the_balanced_bonus(game_env):
    m = game_env.module
    s = m.state
    s.funds = 1000
    s.capacity["output"] = 8
    s.heritage["lighthouse"] = m.HERITAGE_PROTECTED
    for category in ("output", "reduction", "adaptation"):
        s.season_invested.add(category)
    s.advance_season()
    data = s.last_breakdown["funds"]
    assert sum(v for _l, v in data["parts"]) == pytest.approx(data["to"] - data["from"])
    parts = dict(data["parts"])
    assert parts["Heritage upkeep"] == pytest.approx(-m.HERITAGE_UPKEEP)
    assert parts["Output income"] > 0
    text = m.delta_breakdown_text("funds")
    assert "Heritage upkeep" in text and "Output income" in text


def test_acidity_held_at_zero_is_explained(game_env):
    m = game_env.module
    s = m.state
    s.capacity["reduction"] = 3
    s.advance_season()
    assert s.last_breakdown["acidity"]["to"] == 0.0
    assert "acidity cannot go below 0" in m.delta_breakdown_text("acidity")


def test_buttons_toggle_the_popover(game_env):
    m = game_env.module
    m.state.advance_season()
    box = game_env.elements["delta-popover"]
    game_env.elements["why-funds-button"].dispatch("click", None)
    assert box.hidden is False and "Funds last season" in box.innerText
    assert game_env.elements["why-funds-button"].getAttribute("aria-expanded") == "true"
    game_env.elements["why-acidity-button"].dispatch("click", None)
    assert "Acidity last season" in box.innerText
    game_env.elements["why-acidity-button"].dispatch("click", None)
    assert box.hidden is True


def test_the_breakdown_is_not_saved(game_env):
    m = game_env.module
    m.state.advance_season()
    assert "last_breakdown" not in str(m.get_state().keys())
    m.load_state(m.get_state())


# ---- GD-8 Trade Winds ----

def _to_season(s, n):
    while s.season < n:
        s.advance_season()
        s.market_event = None if s.season != n else s.market_event


def test_a_deal_is_offered_every_fourth_season_and_telegraphed_before(game_env):
    m = game_env.module
    s = m.state
    for _ in range(2):
        s.advance_season()
    assert s.season == 3 and s.market_event is None and "next season" in s.market_telegraph_text()
    s.advance_season()
    assert s.season == m.MARKET_EVERY and s.market_event is not None
    assert s.market_event["kind"] in m.MARKET_KINDS
    assert "Trade Winds" in s.market_offer_text() and any("Trade Winds" in line for line in s.ticker_log)
    assert s.market_telegraph_text() == ""


def test_an_unanswered_deal_lapses_when_the_next_season_resolves(game_env):
    m = game_env.module
    s = m.state
    for _ in range(m.MARKET_EVERY - 1):
        s.advance_season()
    assert s.market_event is not None
    s.advance_season()
    assert s.market_event is None and any("lapsed" in line for line in s.ticker_log)


def test_insurance_is_only_offered_when_a_row_has_flooded(game_env):
    m = game_env.module
    s = m.state
    s.sea_level = 0.0
    assert all(s._market_kind_for(season) != "insurance" for season in range(4, 80, 4))
    s.sea_level = m.row_flood_threshold(m.COASTLINE_ROWS - 1) + 1
    assert any(s._market_kind_for(season) == "insurance" for season in range(4, 80, 4))


def test_gains_scale_with_diversification(game_env):
    m = game_env.module
    s = m.state
    base_export, base_tour = s._market_gain("export"), s._market_gain("tourism")
    s.diversification["aquaculture"] = 2
    s.diversification["tourism"] = 2
    assert s._market_gain("export") > base_export and s._market_gain("tourism") == base_tour + 50


def test_accepting_pays_and_charges_the_price_declining_does_neither(game_env):
    m = game_env.module
    s = m.state
    s.market_event = {"kind": "export", "gain": 40.0, "season": 4}
    funds, acid = s.funds, s.acidity
    assert s.answer_market(True) is True
    assert s.funds == funds + 40 and s.acidity == pytest.approx(acid + 0.6) and s.market_accepted == 1 and s.market_event is None
    s.market_event = {"kind": "tourism", "gain": 25.0, "season": 8}
    s.answer_market(True)
    assert s.income_dip_seasons == 1
    s.market_event = {"kind": "insurance", "gain": 20.0, "season": 12}
    s.answer_market(True)
    assert s.income_dip_seasons == 2
    s.market_event = {"kind": "export", "gain": 99.0, "season": 16}
    funds = s.funds
    s.answer_market(False)
    assert s.funds == funds and s.market_accepted == 3
    assert s.answer_market(True) is False  # nothing on the table


def test_the_dip_trims_income_for_that_many_seasons(game_env):
    m = game_env.module
    s = m.state
    s.capacity["output"] = 10
    s.funds = 100
    s.income_dip_seasons = 1
    s.advance_season()
    dipped = s.funds - 100
    s.funds = 100
    s.advance_season()
    normal = s.funds - 100
    assert dipped == pytest.approx(normal * m.MARKET_DIP_FACTOR, rel=0.05) and s.income_dip_seasons == 0


def test_panel_and_buttons(game_env):
    m = game_env.module
    s = m.state
    m.render()
    assert game_env.elements["market-panel"].hidden is True
    s.season = 3
    m.render()
    assert game_env.elements["market-panel"].hidden is False and game_env.elements["market-accept-button"].hidden is True
    s.market_event = {"kind": "tourism", "gain": 50.0, "season": 4}
    s.season = 4
    m.render()
    assert game_env.elements["market-accept-button"].hidden is False and "tourism boom" in game_env.elements["market-text"].innerText
    funds = s.funds
    game_env.elements["market-accept-button"].dispatch("click", None)
    assert s.funds == funds + 50 and game_env.elements["market-accept-button"].hidden is True


def test_market_state_saves_and_validates(game_env):
    m = game_env.module
    s = m.state
    assert "market" not in m.get_state()
    s.market_event = {"kind": "export", "gain": 33.0, "season": 4}
    s.market_accepted, s.income_dip_seasons = 2, 1
    saved = m.get_state()
    s.market_event, s.market_accepted, s.income_dip_seasons = None, 0, 0
    m.load_state(saved)
    assert s.market_event == {"kind": "export", "gain": 33.0, "season": 4} and (s.market_accepted, s.income_dip_seasons) == (2, 1)
    saved["market"] = {"event": {"kind": "piracy", "gain": 5, "season": 4}, "accepted": -3, "dip": 99}
    m.load_state(saved)
    assert s.market_event is None and s.market_accepted == 0 and s.income_dip_seasons == 2


# ---- GD-11 crew ----

def test_hiring_costs_a_fee_and_respects_the_cap_and_funds(game_env):
    m = game_env.module
    s = m.state
    s.funds = 1000
    assert s.hire("biologist") is True and s.funds == 1000 - m.CREW_HIRE_COST
    assert s.hire("biologist") is False and s.hire("pirate") is False
    s.hire("engineer")
    s.hire("broker")
    assert len(s.crew) == m.CREW_MAX
    s.crew.remove("broker")
    s.funds = m.CREW_HIRE_COST - 1
    assert s.hire("broker") is False
    assert s.dismiss("engineer") is True and s.dismiss("engineer") is False


def test_the_biologist_shortens_the_fish_lag_by_one_season(game_env):
    m = game_env.module
    s = m.state
    assert s._effective_fish_lag() == m.FISH_LAG_SEASONS
    s.crew = ["biologist"]
    assert s._effective_fish_lag() == m.FISH_LAG_SEASONS - 1
    s.hard_lag_mode = True
    assert s._effective_fish_lag() == m.FISH_LAG_SEASONS_HARD - 1


def test_the_engineer_cuts_adaptation_costs_and_stacks_with_the_domino_discount(game_env):
    m = game_env.module
    s = m.state
    assert s.invest_cost("adaptation") == 30
    s.crew = ["engineer"]
    assert s.invest_cost("adaptation") == 26  # 30 less 15%, rounded up
    assert s.invest_cost("output") == m.INVEST_COST["output"]
    s.domino_seasons_left = 1
    assert s.invest_cost("adaptation") == 20  # 30 x 0.75 x 0.85, rounded up


def test_wages_are_paid_each_season_and_shown_in_the_breakdown(game_env):
    m = game_env.module
    s = m.state
    s.funds = 100
    s.crew = ["engineer", "broker"]
    s.advance_season()
    assert s.funds == pytest.approx(100 - 2 * m.CREW_WAGE)
    assert dict(s.last_breakdown["funds"]["parts"])["Crew wages"] == pytest.approx(-2 * m.CREW_WAGE)
    s.funds = 3
    s.advance_season()
    assert s.funds >= 0


def test_the_broker_improves_deals_and_the_offer_text_says_so(game_env):
    m = game_env.module
    s = m.state
    s.market_event = {"kind": "tourism", "gain": 100.0, "season": 4}
    plain_text = s.market_offer_text()
    assert "100 funds" in plain_text and "10%" in plain_text
    s.crew = ["broker"]
    assert "130 funds" in s.market_offer_text() and "no income dip" in s.market_offer_text()
    funds = s.funds
    s.answer_market(True)
    assert s.funds == pytest.approx(funds + 130) and s.income_dip_seasons == 0
    s.market_event = {"kind": "insurance", "gain": 10.0, "season": 8}
    s.answer_market(True)
    assert s.income_dip_seasons == 1


def test_crew_buttons_and_status(game_env):
    m = game_env.module
    s = m.state
    s.funds = 500
    m.render()
    assert "No crew hired" in game_env.elements["crew-text"].innerText
    assert game_env.elements["crew-biologist-button"].innerText.startswith("Hire a Marine Biologist")
    game_env.elements["crew-biologist-button"].dispatch("click", None)
    assert s.crew == ["biologist"] and "Dismiss the Marine Biologist" in game_env.elements["crew-biologist-button"].innerText
    assert "Crew: Marine Biologist" in game_env.elements["crew-text"].innerText
    s.funds = 10
    m.render()
    assert game_env.elements["crew-engineer-button"].disabled is True
    assert game_env.elements["crew-biologist-button"].disabled is False  # dismissing is always possible


def test_crew_saves_and_validates(game_env):
    m = game_env.module
    s = m.state
    assert "crew" not in m.get_state()
    s.crew = ["engineer", "broker"]
    saved = m.get_state()
    s.crew = []
    m.load_state(saved)
    assert s.crew == ["engineer", "broker"]
    saved["crew"] = ["broker", "broker", "pirate", "biologist", "engineer", 4]
    m.load_state(saved)
    assert s.crew == ["broker", "biologist", "engineer"]
    saved["crew"] = "oops"
    m.load_state(saved)
    assert s.crew == []


# ---- D-11 autosave history ----

def test_each_season_keeps_a_slot_and_only_the_last_three(game_env, storage):
    m = game_env.module
    for _ in range(5):
        m.on_advance_season()
    slots = m.load_autosaves()
    assert [s["season"] for s in slots] == [4, 5, 6]
    assert all(isinstance(s["state"], dict) and "funds" in s["state"] for s in slots)


def test_x5_stores_one_slot_for_the_end_state(game_env, storage):
    m = game_env.module
    m.on_advance_x5()
    slots = m.load_autosaves()
    assert len(slots) == 1 and slots[0]["season"] == m.state.season


def test_restoring_goes_back_and_clears_the_failed_flag(game_env, storage):
    m = game_env.module
    for _ in range(4):
        m.on_advance_season()
    target = m.load_autosaves()[0]
    m._autosave_info["load_failed"] = True
    assert m.restore_autosave(0) is True
    assert m.state.season == target["season"] and m._autosave_info["load_failed"] is False
    assert any("Restored the autosave" in line for line in m.state.ticker_log)
    assert m.restore_autosave(9) is False and m.restore_autosave(-1) is False


def test_an_unreadable_load_opens_the_panel_and_explains(game_env, storage):
    m = game_env.module
    m.on_advance_season()
    assert m.load_state("not a dict") is False
    m.render()
    assert game_env.elements["autosave-panel"].open is True
    assert "could not be read" in game_env.elements["autosave-note"].innerText
    assert game_env.elements["autosave-list"].children and "Restore Season" in game_env.elements["autosave-list"].children[0].innerText


def test_buttons_restore_the_slot_they_name(game_env, storage):
    m = game_env.module
    for _ in range(3):
        m.on_advance_season()
    m.render()
    buttons = game_env.elements["autosave-list"].children
    assert [b.getAttribute("data-slot") for b in buttons][0] == str(len(buttons) - 1)  # newest first
    oldest = buttons[-1]

    class _Event:
        target = oldest

    m.on_autosave_click(_Event())
    assert m.state.season == m.load_autosaves()[int(oldest.getAttribute("data-slot"))]["season"]


def test_bad_or_oversized_slots_are_ignored(game_env, storage, monkeypatch):
    m = game_env.module
    storage[m.AUTOSAVE_KEY] = "garbage"
    assert m.load_autosaves() == []
    storage[m.AUTOSAVE_KEY] = '[{"season": "x", "funds": 1, "state": {}}, {"season": 3, "funds": 5.5, "state": {"a": 1}}, 7]'
    assert [s["season"] for s in m.load_autosaves()] == [3]
    monkeypatch.setattr(m, "AUTOSAVE_MAX_BYTES", 10)
    assert m.record_autosave() is False


def test_empty_state_says_so(game_env, storage):
    m = game_env.module
    m.render()
    assert "No autosaves yet" in game_env.elements["autosave-list"].innerText


# ---- D-5 Workshop ----

def test_defaults_change_nothing(game_env):
    m = game_env.module
    s = m.state
    assert s.workshop_active() is False and s.workshop == m.WORKSHOP_DEFAULTS
    assert s.sea_rise_per_season() == m.SEA_SCENARIOS[s.sea_scenario]["rise"]
    assert s._effective_fish_lag() == m.FISH_LAG_SEASONS
    assert m.workshop_rating(m.WORKSHOP_DEFAULTS)[1] == "Standard"


def test_each_dial_changes_its_own_rule(game_env):
    m = game_env.module
    s = m.state
    base_rise = s.sea_rise_per_season()
    base_surge = s.storm_surge_strength()
    s.workshop.update(rise=2.0, surge=1.5, lag=5)
    assert s.sea_rise_per_season() == pytest.approx(2 * base_rise)
    assert s.storm_surge_strength() == pytest.approx(1.5 * base_surge)
    assert s._effective_fish_lag() == 5
    s.hard_lag_mode = True
    assert s._effective_fish_lag() == 5  # a chosen lag replaces both presets
    s.workshop.update(lag=0)
    s.hard_lag_mode = False
    s.acidity_history = [10.0, 0.0, 0.0]
    normal = s.fish_yield_multiplier()
    s.workshop["fish"] = 2.0
    assert s.fish_yield_multiplier() < normal


def test_values_are_snapped_clamped_and_cleaned(game_env):
    m = game_env.module
    assert m.clean_workshop_value("funds", 333) == 350 and m.clean_workshop_value("funds", 9999) == 600
    assert m.clean_workshop_value("lag", 3.4) == 3 and m.clean_workshop_value("rise", 1.1) == 1.0
    assert m.clean_workshop_value("rise", "x") == 1.0 and m.clean_workshop_value("lag", True) == 0


def test_rating_goes_up_with_harder_dials_and_has_labels(game_env):
    m = game_env.module
    easy = dict(m.WORKSHOP_DEFAULTS, rise=0.5, surge=0.5, fish=0.5, funds=600)
    hard = dict(m.WORKSHOP_DEFAULTS, rise=2.0, surge=2.0, fish=2.0, funds=100, lag=8)
    assert m.workshop_rating(easy)[0] < m.workshop_rating(m.WORKSHOP_DEFAULTS)[0] < m.workshop_rating(hard)[0]
    assert m.workshop_rating(easy)[1] == "Gentle" and m.workshop_rating(hard)[1] == "Brutal"


def test_apply_starts_a_new_run_with_the_funds_and_rules(game_env):
    m = game_env.module
    old = m.state
    m.on_advance_season()
    m.workshop_pending.update(funds=450, rise=1.5)
    m.on_workshop_apply()
    assert m.state is not old and m.state.funds == 450 and m.state.season == 1
    assert m.state.workshop_active() and m.state.workshop["rise"] == 1.5
    assert game_env.elements["custom-rules-badge"].hidden is False
    m.on_workshop_reset()
    assert m.workshop_pending == m.WORKSHOP_DEFAULTS
    m.on_workshop_apply()
    assert m.state.workshop_active() is False and m.state.funds == m.STARTING_FUNDS


def test_custom_rule_runs_stay_out_of_best_almanac_and_library(game_env, storage):
    m = game_env.module
    m.workshop_pending.update(rise=0.5)
    m.on_workshop_apply()
    s = m.state
    s.capacity["adaptation"] = 10
    for _ in range(6):
        s.advance_season()
    m.render()
    assert m.BEST_COASTLINE_STORAGE_KEY not in storage
    assert m.almanac["seasons"] == 0
    assert m.library_save_current() is False and "custom Workshop rules" in m._library_status


def test_slider_events_stage_values_and_the_status_text(game_env):
    m = game_env.module
    game_env.elements["workshop-surge"].value = "2"
    m.on_workshop_slider("surge")()
    assert m.workshop_pending["surge"] == 2.0
    text = game_env.elements["workshop-status"].innerText
    assert "custom rules" in text and "Apply starts a new run" in text and "standard rules" in text


def test_workshop_saves_only_when_custom_and_validates(game_env):
    m = game_env.module
    s = m.state
    assert "workshop" not in m.get_state()
    s.workshop.update(rise=1.5, funds=400)
    saved = m.get_state()
    s.workshop = dict(m.WORKSHOP_DEFAULTS)
    m.load_state(saved)
    assert s.workshop["rise"] == 1.5 and s.workshop["funds"] == 400
    saved["workshop"] = {"rise": 99, "lag": "x", "funds": -5, "surge": None}
    m.load_state(saved)
    assert s.workshop == dict(m.WORKSHOP_DEFAULTS, rise=2.0, funds=100)
    saved["workshop"] = "nope"
    m.load_state(saved)
    assert s.workshop == m.WORKSHOP_DEFAULTS


# ---- GD-9 postcard ----

def test_grade_follows_how_the_harbour_did(game_env):
    m = game_env.module
    s = m.state
    s.population = s.peak_population = 100
    best = m.postcard_score()
    assert m.postcard_grade(best) == "S"
    s.sea_level = m.row_flood_threshold(0) + 1  # everything flooded
    s.population = 20
    assert m.postcard_score() < best and m.postcard_grade() != "S"
    s.fish_yield_multiplier = lambda: 0.2
    s.population = 0
    s.undampened_damage_total, s.cumulative_damage = 100.0, 100.0
    assert m.postcard_grade() in ("D", "E")
    assert [m.postcard_grade(x) for x in (0.95, 0.8, 0.65, 0.5, 0.35, 0.1)] == list(m.POSTCARD_GRADES)


def test_nicknames_come_from_the_real_state(game_env):
    m = game_env.module
    s = m.state
    assert m.postcard_nickname() == "The Stubborn Harbour"
    s.crew = ["engineer", "broker"]
    assert m.postcard_nickname() == "The Busy Harbour"
    for site in m.HERITAGE_SITES:
        s.heritage[site["id"]] = m.HERITAGE_PROTECTED
    assert m.postcard_nickname() == "Keeper of Lights"
    s.capacity["adaptation"] = 10
    assert m.postcard_nickname() == "The Unflooded"
    s.ironman_earned = True
    assert m.postcard_nickname() == "The Anchor That Held"
    s.ironman_earned = False
    s.sea_level = m.row_flood_threshold(0) + 1
    assert m.postcard_nickname() == "The Drowned Quay"
    assert set(m.postcard_nickname() for _ in range(1)) <= set(m.POSTCARD_NICKNAMES)


def test_the_svg_is_valid_and_shows_flooded_rows_as_sunken_roofs(game_env):
    import xml.etree.ElementTree as ET
    m = game_env.module
    s = m.state
    dry = m.postcard_svg()
    ET.fromstring(dry)
    s.sea_level = m.row_flood_threshold(m.COASTLINE_ROWS - 1) + 1
    s.settlement_name = "Port <Regret>"
    wet = m.postcard_svg()
    ET.fromstring(wet)
    assert "#1a5876" in wet and "#1a5876" not in dry and "Port &lt;Regret&gt;" in wet
    assert f"grade {m.postcard_grade()}" in wet


def test_the_gallery_collects_each_variant_once_and_needs_a_few_seasons(game_env, storage):
    m = game_env.module
    assert m.collect_postcard() == "early"
    for _ in range(4):
        m.state.advance_season()
    assert m.collect_postcard() == "new"
    assert m.collect_postcard() == "seen"
    assert len(m.load_postcards()) == 1 and "1 of 42" in m.gallery_text()
    m.state.sea_level = m.row_flood_threshold(0) + 1
    assert m.collect_postcard() == "new" and len(m.load_postcards()) == 2


def test_custom_rule_runs_do_not_fill_the_gallery(game_env, storage):
    m = game_env.module
    for _ in range(4):
        m.state.advance_season()
    m.state.workshop["rise"] = 0.5
    assert m.collect_postcard() == "early"


def test_bad_gallery_data_is_ignored(game_env, storage):
    m = game_env.module
    storage[m.POSTCARD_KEY] = "junk"
    assert m.load_postcards() == []
    storage[m.POSTCARD_KEY] = '[{"grade": "Z", "nickname": "The Stubborn Harbour"}, {"grade": "A", "nickname": "Made Up"}, {"grade": "B", "nickname": "The Quiet Nets", "season": 7}, 5]'
    cards = m.load_postcards()
    assert len(cards) == 1 and cards[0]["season"] == 7


def test_button_and_panel(game_env, storage):
    m = game_env.module
    m.session_summary_open = True
    m.render()
    assert "<svg" in game_env.elements["postcard-view"].innerHTML and "0 of 42" in game_env.elements["postcard-gallery"].innerText
    game_env.elements["postcard-button"].dispatch("click", None)
    assert "Play at least" in game_env.elements["postcard-status"].innerText
    for _ in range(4):
        m.state.advance_season()
    game_env.elements["postcard-button"].dispatch("click", None)
    assert "new postcard variant" in game_env.elements["postcard-status"].innerText
    game_env.elements["postcard-button"].dispatch("click", None)
    assert "already have" in game_env.elements["postcard-status"].innerText
    m.session_summary_open = False
    m.render()
    assert game_env.elements["postcard-view"].innerHTML == ""
