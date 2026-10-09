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
