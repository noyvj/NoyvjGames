"""J-17 / J-18 -- Market Weather: opt-in booms and slumps with cascades, leading indicators in the Almanac
and a text-only ticker on the map. Deterministic from the founding seed and the event number."""

import json

import pytest


def _on(game_env):
    m = game_env.module
    m.weather_enabled = True
    game_env.tick(1)
    return m


def _force(m, **fields):
    ev = {"good": m.ORE, "kind": "boom", "style": 0, "wait": 0, "left": 30, "dur": 30}
    ev.update(fields)
    m.weather_enabled = True
    m.weather_event = ev
    return ev


# ---------------------------------------------------------------- defaults

def test_off_by_default_changes_nothing(game_env):
    m = game_env.module
    assert m.weather_enabled is False and m.weather_active_event() is None
    assert m.weather_multiplier(m.ORE) == 1.0
    game_env.tick(100)
    assert m.weather_event is None and m.weather_n == 0
    assert "weather" not in m.get_state() and "records" not in m.get_state()
    assert game_env.elements["news-ticker"].hidden is True
    assert game_env.elements["weather-toggle-button"].innerText == "Market weather: off"


def test_toggle_button_switches_it_on_and_shows_the_ticker(game_env):
    game_env.elements["weather-toggle-button"].dispatch("click", None)
    m = game_env.module
    assert m.weather_enabled and game_env.elements["news-ticker"].hidden is False
    assert game_env.elements["weather-toggle-button"].innerText == "Market weather: on"
    assert game_env.elements["weather-toggle-button"].attributes["aria-pressed"] == "true"


# ------------------------------------------------------------ generation

def test_the_event_is_a_pure_function_of_seed_and_number(game_env):
    m = game_env.module
    a = [m._weather_make(n) for n in range(6)]
    assert a == [m._weather_make(n) for n in range(6)]
    m.founding_seed = 12345
    assert a != [m._weather_make(n) for n in range(6)]


def test_events_stay_inside_their_documented_ranges(game_env):
    m = game_env.module
    kinds = set()
    for n in range(200):
        ev = m._weather_make(n)
        assert m.WEATHER_GAP[0] <= ev["wait"] <= m.WEATHER_GAP[1]
        assert m.WEATHER_DURATION[0] <= ev["dur"] <= m.WEATHER_DURATION[1] and ev["left"] == ev["dur"]
        assert ev["good"] in m.seasonal_reachable_goods() and ev["style"] in (0, 1)
        kinds.add(ev["kind"])
    assert kinds == {"boom", "slump"}


def test_only_reachable_goods_are_chosen(game_env):
    m = game_env.module
    home = set(m.seasonal_reachable_goods())
    assert all(m._weather_make(n)["good"] in home for n in range(100))
    assert home <= {m.ORE, m.GRAIN, m.MACHINERY, m.WATER, m.ENERGY}


def test_first_tick_rolls_an_event_and_it_counts_down_then_ends(game_env):
    m = _on(game_env)
    ev = m.weather_event
    assert ev is not None and m.weather_n == 1
    wait0 = ev["wait"] + 1  # one tick has already run
    assert m.weather_active_event() is None
    game_env.tick(ev["wait"])
    assert m.weather_active_event() is not None and m.weather_event["wait"] == 0
    dur = m.weather_event["dur"]
    game_env.tick(dur - 1)
    assert m.weather_active_event() is not None and m.weather_event["left"] == 1
    game_env.tick(1)
    assert m.weather_event is None and m.records["weather_events"] == 1
    game_env.tick(1)
    assert m.weather_n == 2 and m.weather_event is not None
    assert wait0 >= m.WEATHER_GAP[0]


def test_the_clock_only_runs_while_the_mode_is_on(game_env):
    m = game_env.module
    _force(m, wait=10)
    m.weather_enabled = False
    game_env.tick(5)
    assert m.weather_event["wait"] == 10


# ---------------------------------------------------------------- effects

def test_a_boom_raises_the_good_and_the_cascade_follows_at_half(game_env):
    m = game_env.module
    base = m.current_sell_price(m.ORE)
    _force(m, good=m.ORE, kind="boom")
    assert m.weather_multiplier(m.ORE) == pytest.approx(1.30)
    follow = m.weather_cascade_good(m.ORE)
    assert follow is not None and m.weather_multiplier(follow) == pytest.approx(1.15)
    assert m.current_sell_price(m.ORE) > base
    others = [g for g in m.SELL_PRICE if g not in (m.ORE, follow)]
    assert all(m.weather_multiplier(g) == 1.0 for g in others)


def test_a_slump_lowers_but_never_below_one_credit(game_env):
    m = game_env.module
    base = m.current_sell_price(m.WATER)
    _force(m, good=m.WATER, kind="slump")
    assert m.weather_multiplier(m.WATER) == pytest.approx(0.75)
    assert 1 <= m.current_sell_price(m.WATER) <= base
    m.market_multiplier[m.WATER] = m.MIN_PRICE_MULTIPLIER
    assert m.current_sell_price(m.WATER) >= 1


def test_the_cascade_good_is_made_where_the_event_good_is_needed(game_env):
    m = game_env.module
    for good in (m.ORE, m.GRAIN, m.MACHINERY, m.WATER, m.ENERGY):
        follow = m.weather_cascade_good(good)
        consumer = m.colony_needing(good)
        assert m.ALL_COLONIES[consumer]["produces"] == follow


def test_no_effect_before_it_starts_or_when_off(game_env):
    m = game_env.module
    _force(m, wait=3)
    assert m.weather_multiplier(m.ORE) == 1.0
    _force(m, wait=0)
    m.weather_enabled = False
    assert m.weather_multiplier(m.ORE) == 1.0


def test_a_ship_sale_uses_the_weather_price(game_env):
    m = game_env.module
    m.weather_enabled = True
    m.weather_event = {"good": m.ORE, "kind": "boom", "style": 0, "wait": 0, "left": 30, "dur": 30}
    game_env.load()
    game_env.depart("ferrum")
    before = m.total_profit
    game_env.tick(m.TRAVEL_TICKS)
    boom_gain = m.total_profit - before
    m2 = game_env.module
    assert boom_gain > 0 and m2.weather_active_event() is not None


def test_the_market_row_names_the_weather(game_env):
    m = game_env.module
    _force(m, good=m.ORE, kind="boom")
    m.render()
    assert "boom (+30%" in game_env.elements["market-ore-display"].innerText


def test_a_stockpile_sells_for_more_in_a_boom(game_env):
    m = game_env.module
    m.stockpile[m.ORE] = 10
    plain = m.stockpile_sale_value(m.ORE)
    _force(m, good=m.ORE, kind="boom")
    assert m.stockpile_sale_value(m.ORE) > plain


# -------------------------------------------------- leading indicators / ticker

def test_dock_gossip_appears_twelve_ticks_ahead_and_names_the_colony_only(game_env):
    m = game_env.module
    _force(m, wait=m.WEATHER_RUMOUR_TICKS + 1)
    assert m.weather_rumour() == ""
    m.weather_event["wait"] = m.WEATHER_RUMOUR_TICKS
    text = m.weather_rumour()
    assert "something is brewing" in text and m._weather_colony_name(m.ORE) in text
    assert "boom" not in text and "slump" not in text


def test_five_ticks_ahead_it_says_boom_or_slump(game_env):
    m = game_env.module
    _force(m, wait=m.WEATHER_DIRECTION_TICKS, kind="slump")
    assert "a slump looks likely" in m.weather_rumour()
    m.weather_event["kind"] = "boom"
    assert "a boom looks likely" in m.weather_rumour()


def test_ticker_states_each_phase_in_words(game_env):
    m = game_env.module
    m.weather_enabled = True
    m.weather_event = None
    assert m.weather_ticker_text().startswith("Quiet markets")
    _force(m, wait=0, kind="slump", style=1)
    text = m.weather_ticker_text()
    assert "Port backlog" in text and "-25%" in text and "tick(s) left" in text
    _force(m, wait=0, kind="boom", style=0)
    assert "Festival" in m.weather_ticker_text() and "+30%" in m.weather_ticker_text()


def test_ticker_is_hidden_when_off_and_updates_in_place(game_env):
    m = game_env.module
    m.render()
    assert game_env.elements["news-ticker"].hidden is True
    _force(m)
    m.render()
    el = game_env.elements["news-ticker"]
    assert el.hidden is False and "Festival" in el.innerText
    first = el.innerText
    m.render()
    assert el.innerText == first


def test_almanac_explains_the_leading_indicators_only_when_on(game_env):
    m = game_env.module
    m.render()
    assert "Leading indicators" not in game_env.elements["almanac-body"].innerHTML
    m.weather_enabled = True
    m.render()
    assert "Leading indicators" in game_env.elements["almanac-body"].innerHTML


def test_status_line_explains_it_and_reports_progress(game_env):
    m = game_env.module
    m.render()
    assert "Nothing is permanent" in game_env.elements["weather-status"].innerText
    _force(m)
    m.records["weather_events"] = 3
    m.render()
    text = game_env.elements["weather-status"].innerText
    assert "Events weathered so far: 3" in text and "follows at half strength" in text


# ------------------------------------------------------------- achievement

def test_five_events_earn_storm_watcher(game_env):
    m = game_env.module
    assert "storm_watcher" not in m.achievement_ids_earned()
    m.records["weather_events"] = 4
    assert "storm_watcher" not in m.achievement_ids_earned()
    m.records["weather_events"] = 5
    assert "storm_watcher" in m.achievement_ids_earned()
    progress = {a["id"]: a["progress"] for a in m.achievements_summary()}
    assert progress["storm_watcher"] == (5, 5)


def test_running_events_to_their_end_counts_them(game_env):
    m = game_env.module
    m.weather_enabled = True
    game_env.tick(5 * 90)
    assert m.records["weather_events"] >= 5


# ------------------------------------------------------------------- saves

def test_state_round_trips_mid_event(game_env):
    m = _on(game_env)
    game_env.tick(45)
    state = json.loads(json.dumps(m.get_state()))
    saved = dict(state["weather"])
    assert saved["enabled"] is True and saved["n"] == m.weather_n
    m.weather_enabled, m.weather_n, m.weather_event = False, 0, None
    m.load_state(state)
    assert m.weather_enabled and m.weather_n == saved["n"] and m.weather_event == saved["event"]


def test_a_save_without_weather_turns_it_off(game_env):
    m = _on(game_env)
    m.load_state(json.loads(json.dumps(m._fresh_state)))
    assert not m.weather_enabled and m.weather_event is None and m.weather_n == 0


@pytest.mark.parametrize("event", [
    "x", 3, [], {"good": "nope", "kind": "boom", "style": 0, "wait": 1, "left": 25, "dur": 30},
    {"good": "ore", "kind": "hail", "style": 0, "wait": 1, "left": 25, "dur": 30},
    {"good": "ore", "kind": "boom", "style": 2, "wait": 1, "left": 25, "dur": 30},
    {"good": "ore", "kind": "boom", "style": True, "wait": 1, "left": 25, "dur": 30},
    {"good": "ore", "kind": "boom", "style": 0, "wait": -1, "left": 25, "dur": 30},
    {"good": "ore", "kind": "boom", "style": 0, "wait": 1, "left": 31, "dur": 30},
    {"good": "ore", "kind": "boom", "style": 0, "wait": 1, "left": 0, "dur": 30},
    {"good": "ore", "kind": "boom", "style": 0, "wait": 1, "left": 25, "dur": 5},
    {"good": "ore", "kind": "boom", "style": 0, "wait": 1.5, "left": 25, "dur": 30},
    {"good": "kepler_goods", "kind": "boom", "style": 0, "wait": 1, "left": 25, "dur": 30},
    {"good": ["ore"], "kind": "boom", "style": 0, "wait": 1, "left": 25, "dur": 30},
])
def test_tampered_events_are_dropped_and_a_new_one_rolls(game_env, event):
    m = game_env.module
    state = json.loads(json.dumps(m._fresh_state))
    state["weather"] = {"enabled": True, "n": 4, "event": event}
    assert m.load_state(state) is True
    assert m.weather_event is None and m.weather_enabled and m.weather_n == 4
    game_env.tick(1)
    assert m.weather_event is not None


def test_locked_cluster_goods_in_a_saved_event_are_dropped(game_env):
    m = game_env.module
    state = json.loads(json.dumps(m._fresh_state))
    state["weather"] = {"enabled": True, "n": 1, "event": {
        "good": m.ISOTOPES, "kind": "boom", "style": 0, "wait": 1, "left": 25, "dur": 30}}
    m.load_state(state)
    assert m.weather_event is None  # Kepler is not unlocked in this save


@pytest.mark.parametrize("raw", ["x", 5, [], {"enabled": "yes", "n": "3"}, {"n": True}, {"n": 10 ** 12}])
def test_tampered_weather_values_fall_back(game_env, raw):
    m = game_env.module
    state = json.loads(json.dumps(m._fresh_state))
    state["weather"] = raw
    assert m.load_state(state) is True
    assert m.weather_enabled is False and m.weather_n == 0 and m.weather_event is None


def test_a_renewal_switches_weather_off_and_keeps_the_count(game_env):
    m = _on(game_env)
    m.records["weather_events"] = 4
    m.endgame_reached = True
    m.found_new_corporation()
    assert not m.weather_enabled and m.weather_event is None and m.records["weather_events"] == 4


def test_sandbox_round_trip_restores_the_real_weather(game_env):
    m = _on(game_env)
    game_env.tick(10)
    before = json.dumps(m.get_state(), sort_keys=True)
    m.sandbox_enter()
    assert not m.weather_enabled
    m.sandbox_leave()
    assert json.dumps(m.get_state(), sort_keys=True) == before
