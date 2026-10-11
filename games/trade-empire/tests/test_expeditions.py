"""J-23 / J-24 -- Expeditions: one idle ship away for 12 ticks, a visible odds table with bad-luck guarantees,
a 12-piece curio cabinet and a count that survives renewals."""

import json
import sys
import types

import pytest


def _go(game_env, ship_id="1"):
    assert game_env.module.send_expedition(ship_id) is True


def _finish(game_env):
    game_env.tick(game_env.module.EXPEDITION_TICKS)


# ---------------------------------------------------------------- eligibility

def test_a_docked_empty_manual_ship_can_go(game_env):
    m = game_env.module
    assert m.can_send_expedition("1")
    assert not m.can_send_expedition("5")  # not bought yet
    assert not m.can_send_expedition("nope")


def test_a_loaded_or_automated_or_travelling_ship_cannot(game_env):
    m = game_env.module
    game_env.load("1")
    assert not m.can_send_expedition("1")
    game_env.depart("verdant", "1")
    assert not m.can_send_expedition("1")
    m.total_profit = 1000
    game_env.automate("2")
    assert not m.can_send_expedition("2")


def test_only_one_expedition_at_a_time(game_env):
    m = game_env.module
    _go(game_env, "1")
    assert not m.can_send_expedition("2") and m.send_expedition("2") is False


# ------------------------------------------------------------------ away

def test_the_ship_cannot_trade_while_away_and_says_so(game_env):
    m = game_env.module
    _go(game_env)
    ship = m.ships["1"]
    assert ship.on_expedition and not ship.docked
    assert ship.load() is False
    m.render()
    assert "expedition" in game_env.elements["ship-1-status"].innerText
    assert game_env.elements["ship-1-load-button"].disabled is True
    assert all(game_env.elements[f"ship-1-depart-{c}-button"].hidden for c in m.COLONIES)


def test_it_is_not_drawn_on_the_map_and_other_ships_still_trade(game_env):
    m = game_env.module
    _go(game_env, "1")
    game_env.tick(2)
    game_env.load("2")
    game_env.depart("ferrum", "2")
    game_env.tick(m.TRAVEL_TICKS)
    assert m.ships["2"].location == "ferrum" and m.total_sales_count == 1


def test_it_comes_back_after_twelve_ticks_docked_where_it_left(game_env):
    m = game_env.module
    _go(game_env)
    game_env.tick(m.EXPEDITION_TICKS - 1)
    assert m.expedition is not None and m.expedition["left"] == 1
    game_env.tick(1)
    assert m.expedition is None and m.ships["1"].docked and m.ships["1"].location == "aurum"
    assert m.records["expeditions"] == 1


def test_idle_counter_does_not_run_while_away(game_env):
    m = game_env.module
    _go(game_env)
    game_env.tick(5)
    assert m.ships["1"].idle_ticks == 0


def test_fleet_priority_and_automation_ignore_the_absent_ship(game_env):
    m = game_env.module
    _go(game_env)
    m.ships["1"].automated = True  # bought elsewhere; it must not load while away
    game_env.tick(3)
    assert not m.ships["1"].loaded


# ------------------------------------------------------------------ rewards

def test_the_roll_is_deterministic_and_covers_every_outcome(game_env):
    m = game_env.module
    seen = {m.expedition_roll(n, 0, 0, []) for n in range(200)}
    assert seen == {"windfall", "research", "curio", "nothing"}
    assert [m.expedition_roll(n, 0, 0, []) for n in range(20)] == [m.expedition_roll(n, 0, 0, []) for n in range(20)]


def test_the_odds_sum_to_one_hundred(game_env):
    assert sum(weight for _o, weight in game_env.module.EXPEDITION_ODDS) == 100


def test_two_empty_trips_guarantee_the_third_is_not_empty(game_env):
    m = game_env.module
    for n in range(300):
        assert m.expedition_roll(n, m.EXPEDITION_NOTHING_GUARANTEE, 0, []) != "nothing"


def test_a_trip_without_a_curio_streak_guarantees_a_curio(game_env):
    m = game_env.module
    for n in range(100):
        assert m.expedition_roll(n, 0, m.EXPEDITION_CURIO_GUARANTEE - 1, []) == "curio"


def test_no_curio_outcome_once_the_cabinet_is_full(game_env):
    m = game_env.module
    full = list(m.CURIO_IDS)
    for n in range(300):
        assert m.expedition_roll(n, 0, 99, full) != "curio"


def test_windfall_pays_and_scales_with_systems_open(game_env):
    m = game_env.module
    assert m.expedition_windfall() == 150
    m.unlocked_research.add("galaxy_expansion")
    assert m.expedition_windfall() == 225


def _force_outcome(m, outcome):
    m.expedition_roll = lambda n, a, b, c: outcome


def test_a_windfall_adds_credits(game_env):
    m = game_env.module
    _force_outcome(m, "windfall")
    before = m.total_profit
    _go(game_env)
    _finish(game_env)
    assert m.total_profit == before + 150
    assert "credits" in m.expedition_log and m.records["expedition_nothing_streak"] == 0


def test_research_adds_points(game_env):
    m = game_env.module
    _force_outcome(m, "research")
    before = m.research_points
    _go(game_env)
    _finish(game_env)
    # the research clock also ran for twelve ticks
    assert m.research_points >= before + m.EXPEDITION_RESEARCH


def test_a_curio_joins_the_cabinet_and_is_not_repeated(game_env):
    m = game_env.module
    _force_outcome(m, "curio")
    for _ in range(3):
        _go(game_env)
        _finish(game_env)
    assert len(m.records["curios"]) == 3 and len(set(m.records["curios"])) == 3
    assert m.records["expedition_since_curio"] == 0


def test_nothing_still_counts_and_builds_the_streak(game_env):
    m = game_env.module
    _force_outcome(m, "nothing")
    _go(game_env)
    _finish(game_env)
    assert m.records["expeditions"] == 1 and m.records["expedition_nothing_streak"] == 1
    assert "view" in m.expedition_log


def test_real_rolls_never_leave_a_long_empty_streak(game_env):
    m = game_env.module
    worst = 0
    for _ in range(40):
        _go(game_env)
        _finish(game_env)
        worst = max(worst, m.records["expedition_nothing_streak"])
    assert worst <= m.EXPEDITION_NOTHING_GUARANTEE
    assert len(m.records["curios"]) >= 40 // m.EXPEDITION_CURIO_GUARANTEE - 1


def test_all_twelve_curios_are_collectable_and_earn_the_cabinet(game_env):
    m = game_env.module
    for _ in range(80):
        if len(m.records["curios"]) == len(m.CURIO_IDS):
            break
        _go(game_env)
        _finish(game_env)
    assert len(m.records["curios"]) == 12
    assert "curio_cabinet" in m.achievement_ids_earned() and "first_expedition" in m.achievement_ids_earned()
    progress = {a["id"]: a["progress"] for a in m.achievements_summary()}
    assert progress["curio_cabinet"] == (12, 12)


def test_the_result_toast_says_what_was_found(game_env):
    m = game_env.module
    _force_outcome(m, "windfall")
    _go(game_env)
    _finish(game_env)
    assert "returned from expedition number 1" in game_env.elements["notice-toast"].innerText


# --------------------------------------------------------------------- UI

def test_the_lab_toggle_opens_the_panel_and_lists_the_odds(game_env):
    el = game_env.elements
    assert el["lab-panel"].hidden is True
    el["lab-toggle-button"].dispatch("click", None)
    assert el["lab-panel"].hidden is False and el["lab-toggle-button"].attributes["aria-expanded"] == "true"
    assert "35% a windfall of credits" in el["expedition-odds"].innerText
    assert "Never unlucky twice running" in el["expedition-odds"].innerText
    assert "20% nothing but the view" in el["expedition-odds"].innerText


def test_the_send_button_carries_the_odds_as_a_tooltip_and_is_gated(game_env):
    m = game_env.module
    el = game_env.elements
    el["lab-toggle-button"].dispatch("click", None)
    button = el["expedition-ship-1-button"]
    assert button.disabled is False and "Odds:" in button.title
    assert "after 2 empty trips" in button.title
    assert el["expedition-ship-5-button"].hidden is True  # not bought
    game_env.load("1")
    m.render()
    assert button.disabled is True


def test_clicking_send_asks_then_sends(game_env):
    m = game_env.module
    asked = []

    class Dialog:
        def ask(self, **options):
            asked.append(options)
            options["onConfirm"]()

    sys.modules["js"].window = types.SimpleNamespace(ConfirmDialog=Dialog())
    game_env.elements["lab-toggle-button"].dispatch("click", None)
    game_env.elements["expedition-ship-1-button"].dispatch("click", None)
    assert asked and "cannot trade for 12 ticks" in asked[0]["message"]
    assert m.expedition == {"ship": "1", "left": 12}
    assert "away" in game_env.elements["expedition-status"].innerText


def test_clicking_a_disabled_ship_does_nothing(game_env):
    game_env.load("1")
    game_env.elements["expedition-ship-1-button"].dispatch("click", None)
    assert game_env.module.expedition is None


def test_the_cabinet_shows_found_curios_and_hides_the_rest(game_env):
    m = game_env.module
    m.records["curios"] = ["tin_cup"]
    game_env.elements["lab-toggle-button"].dispatch("click", None)
    html = game_env.elements["expedition-curios"].innerHTML
    assert "Tin cup" in html and html.count("Not found yet") == 11
    assert "1/12" in game_env.elements["expedition-status"].innerText


# ------------------------------------------------------------------- saves

def test_nothing_is_saved_until_used(game_env):
    state = game_env.module.get_state()
    assert "expedition" not in state and "records" not in state


def test_state_round_trips_mid_expedition_and_records(game_env):
    m = game_env.module
    _force_outcome(m, "curio")
    _go(game_env)
    _finish(game_env)
    del m.expedition_roll
    _go(game_env, "2")
    game_env.tick(4)
    state = json.loads(json.dumps(m.get_state()))
    assert state["expedition"] == {"ship": "2", "left": 8}
    assert state["records"]["expeditions"] == 1 and len(state["records"]["curios"]) == 1
    m.expedition = None
    m.records.update(m._fresh_records())
    m.load_state(state)
    assert m.expedition == {"ship": "2", "left": 8} and m.ships["2"].on_expedition
    assert m.records["expeditions"] == 1 and len(m.records["curios"]) == 1


@pytest.mark.parametrize("raw", [
    "x", 3, [], {"ship": "9", "left": 5}, {"ship": "5", "left": 5}, {"ship": "1", "left": 0}, {"ship": "1", "left": 13},
    {"ship": "1", "left": True}, {"ship": 1, "left": 5}, {"ship": ["1"], "left": 5}, {"ship": "1", "left": 2.5},
])
def test_tampered_expeditions_are_dropped(game_env, raw):
    m = game_env.module
    state = json.loads(json.dumps(m._fresh_state))
    state["expedition"] = raw
    assert m.load_state(state) is True
    assert m.expedition is None


def test_an_expedition_on_a_loaded_ship_is_dropped(game_env):
    m = game_env.module
    state = json.loads(json.dumps(m._fresh_state))
    state["ships"]["1"]["cargo_good"], state["ships"]["1"]["cargo_qty"] = "ore", 5
    state["expedition"] = {"ship": "1", "left": 5}
    m.load_state(state)
    assert m.expedition is None


def test_an_expedition_on_a_ship_in_transit_is_dropped(game_env):
    m = game_env.module
    game_env.load("1")
    game_env.depart("verdant", "1")
    state = json.loads(json.dumps(m.get_state()))
    state["expedition"] = {"ship": "1", "left": 5}
    m.load_state(state)
    assert m.expedition is None and m.ships["1"].in_transit


@pytest.mark.parametrize("raw", [
    {"curios": "tin_cup"}, {"curios": [["x"], 3, None, "nope"]}, {"curios": ["tin_cup", "tin_cup", "spare_moon"]},
    {"expeditions": True}, {"expeditions": -4}, {"expedition_nothing_streak": "2"},
])
def test_tampered_curios_and_counters_are_cleaned(game_env, raw):
    m = game_env.module
    state = json.loads(json.dumps(m._fresh_state))
    state["records"] = raw
    m.load_state(state)
    assert all(c in m.CURIO_IDS for c in m.records["curios"])
    assert len(m.records["curios"]) == len(set(m.records["curios"]))
    assert all(isinstance(v, int) and v >= 0 for k, v in m.records.items() if k != "curios")


def test_the_cabinet_and_count_survive_a_renewal_but_a_trip_in_progress_does_not(game_env):
    m = game_env.module
    m.records["curios"] = ["tin_cup", "spare_moon"]
    m.records["expeditions"] = 7
    _go(game_env)
    m.endgame_reached = True
    m.found_new_corporation()
    assert m.records["curios"] == ["tin_cup", "spare_moon"] and m.records["expeditions"] == 7
    assert m.expedition is None and m.ships["1"].docked


def test_sandbox_round_trip_keeps_the_real_expedition(game_env):
    m = game_env.module
    _go(game_env)
    game_env.tick(3)
    before = json.dumps(m.get_state(), sort_keys=True)
    m.sandbox_enter()
    assert m.expedition is None
    m.sandbox_leave()
    assert json.dumps(m.get_state(), sort_keys=True) == before and m.expedition is not None


def test_curio_names_are_unique_and_invented(game_env):
    m = game_env.module
    assert len(m.CURIO_IDS) == 12 and len(set(m.CURIO_LABEL.values())) == 12
