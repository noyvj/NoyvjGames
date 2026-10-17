"""J-9 / J-10 -- Trade Crises: three handcrafted boards run inside the sandbox machinery, with par-tick medals,
a best-medal chip on each card and a restart key. The real corporation is set aside and never touched."""

import json

import pytest

CRISES = ("grain_famine", "isotope_glut", "broken_network")


def _bot_step(m, to_kepler=False, seen=None):
    """A plain greedy player: loads whatever helps a colony and delivers it where it is needed."""
    for ship in m.ships.values():
        if not ship.purchased or ship.automated or not ship.docked:
            continue
        if to_kepler and ship.location in m.COLONIES and ship.id not in seen:
            if not ship.loaded:
                ship.load()
            ship.depart("kepler_a")
            seen.add(ship.id)
            continue
        if not ship.loaded:
            dest = m.colony_needing(m.ALL_COLONIES[ship.location]["produces"])
            if dest in m.colony_states and dest != ship.location:
                ship.load()
        else:
            dest = m.colony_needing(ship.cargo_good)
            if dest != ship.location:
                ship.depart(dest)


def _solve(game_env, crisis_id, limit=400):
    m = game_env.module
    m.crisis_enter(crisis_id)
    seen = set()
    for _ in range(limit):
        if m.crisis_done is not None:
            break
        _bot_step(m, to_kepler=crisis_id == "isotope_glut", seen=seen)
        game_env.tick(1)
    return m.crisis_done


def test_three_crises_each_with_a_name_a_goal_and_ordered_pars(game_env):
    m = game_env.module
    assert set(m.CRISES) == set(CRISES)
    for c in m.CRISES.values():
        assert c["name"] and c["blurb"] and c["par"][0] < c["par"][1] < c["par"][2]


def test_starting_a_crisis_sets_the_real_game_aside_and_loads_the_board(game_env):
    m = game_env.module
    m.total_profit = 777
    m.crisis_enter("grain_famine")
    assert m.sandbox_is_active() and m.crisis_active == "grain_famine"
    assert m.total_profit == 300 and m.colony_states["aurum"].need_satisfaction == 0.0
    assert m.get_state()["total_profit"] == 777  # a save while it runs is the real game


def test_leaving_puts_the_real_game_back_byte_for_byte(game_env):
    m = game_env.module
    m.total_profit = 5000
    m.unlocked_research.add("fast_ships")
    game_env.tick(30)
    before = json.dumps(m.get_state(), sort_keys=True)
    m.crisis_enter("broken_network")
    game_env.tick(10)
    m.sandbox_leave()
    assert json.dumps(m.get_state(), sort_keys=True) == before and m.crisis_active is None and not m.sandbox_is_active()


def test_the_real_game_does_not_tick_while_a_crisis_runs(game_env):
    m = game_env.module
    real_points = m.research_points
    m.crisis_enter("grain_famine")
    game_env.tick(5)
    assert m.get_state()["research_points"] == real_points


def test_each_board_is_what_its_name_says(game_env):
    m = game_env.module
    m.crisis_enter("isotope_glut")
    assert "galaxy_expansion" in m.unlocked_research and m.market_multiplier["isotopes"] == 0.35
    assert "kepler_a" in m.colony_states
    m.crisis_enter("broken_network")
    assert m.ships["1"].automated and m.ships["2"].automated and not m.ships["3"].automated
    assert m.colony_states["ferrum"].need_satisfaction == 0.0
    assert "kepler_a" not in m.colony_states


def test_restart_resets_the_board_and_the_clock(game_env):
    m = game_env.module
    m.crisis_enter("grain_famine")
    game_env.tick(7)
    assert m.crisis_ticks == 7
    m.crisis_restart()
    assert m.crisis_ticks == 0 and m.colony_states["aurum"].need_satisfaction == 0.0 and m.crisis_done is None
    assert m.get_state()["total_profit"] == 0  # still the same real game underneath


def test_switching_crisis_keeps_one_snapshot_of_the_real_game(game_env):
    m = game_env.module
    m.total_profit = 1234
    m.crisis_enter("grain_famine")
    m.crisis_enter("broken_network")
    m.sandbox_leave()
    assert m.total_profit == 1234


def test_starting_a_crisis_from_the_practice_sandbox_goes_through_the_real_game(game_env):
    m = game_env.module
    m.total_profit = 321
    m.sandbox_enter()
    m.crisis_enter("grain_famine")
    assert m.crisis_active == "grain_famine" and m.get_state()["total_profit"] == 321
    m.sandbox_leave()
    assert m.total_profit == 321


def test_starting_the_sandbox_from_a_crisis_leaves_the_crisis(game_env):
    m = game_env.module
    m.crisis_enter("grain_famine")
    assert m.sandbox_enter() is True
    assert m.crisis_active is None and m.sandbox_is_active() and m.total_profit >= m.SANDBOX_CREDITS
    m.sandbox_leave()


def test_a_crisis_has_its_own_purse_not_unlimited_credits(game_env):
    m = game_env.module
    m.crisis_enter("grain_famine")
    m.total_profit = 5
    m.render()
    assert m.total_profit == 5
    assert "unlimited" not in game_env.elements["profit-display-text"].innerText


def test_a_plain_player_solves_every_crisis_and_earns_a_medal(game_env):
    for crisis_id in CRISES:
        done = _solve(game_env, crisis_id)
        assert done is not None, crisis_id
        assert done["medal"] in ("gold", "silver", "bronze"), (crisis_id, done)
        game_env.module.sandbox_leave()


def test_nothing_is_lost_and_nothing_fails_when_you_do_nothing(game_env):
    m = game_env.module
    m.crisis_enter("grain_famine")
    game_env.tick(400)
    assert m.crisis_done is None and m.crisis_active == "grain_famine"
    m.sandbox_leave()


def test_the_medal_follows_the_par_ticks(game_env):
    m = game_env.module
    gold, silver, bronze = m.CRISES["grain_famine"]["par"]
    assert [m.crisis_medal_for("grain_famine", t) for t in (gold, gold + 1, silver, silver + 1, bronze, bronze + 1)] == [
        "gold", "silver", "silver", "bronze", "bronze", "done"]


def test_solving_writes_the_best_medal_into_the_real_game_and_survives_leaving(game_env):
    m = game_env.module
    done = _solve(game_env, "grain_famine")
    assert m.get_state()["records"]["crisis_best"]["grain_famine"] == done
    m.sandbox_leave()
    assert m.records["crisis_best"]["grain_famine"]["ticks"] == done["ticks"]
    assert "crisis_averted" in m.achievement_ids_earned()


def test_a_slower_second_run_does_not_replace_the_best(game_env):
    m = game_env.module
    m.crisis_enter("grain_famine")
    m._sandbox_real["snapshot"]["records"] = {"crisis_best": {"grain_famine": {"medal": "gold", "ticks": 1}}}
    for state in m.colony_states.values():
        state.need_satisfaction = 1.0
    game_env.tick(1)
    assert m._sandbox_real["snapshot"]["records"]["crisis_best"]["grain_famine"] == {"medal": "gold", "ticks": 1}


def test_a_faster_run_replaces_it_and_a_better_medal_beats_a_faster_worse_one(game_env):
    m = game_env.module
    m.crisis_enter("grain_famine")
    m._sandbox_real["snapshot"]["records"] = {"crisis_best": {"grain_famine": {"medal": "bronze", "ticks": 5}}}
    m.colony_states["aurum"].need_satisfaction = 1.0
    game_env.tick(1)
    assert m._sandbox_real["snapshot"]["records"]["crisis_best"]["grain_famine"] == {"medal": "gold", "ticks": 1}


def test_no_achievement_or_record_changes_inside_the_crisis(game_env):
    m = game_env.module
    m.crisis_enter("grain_famine")
    game_env.tick(5)
    assert m.achievement_ids_earned() == []
    assert m.can_found_new_corporation() is False


def test_the_solved_toast_names_the_medal(game_env):
    m = game_env.module
    m.crisis_enter("grain_famine")
    m.colony_states["aurum"].need_satisfaction = 1.0
    game_env.tick(1)
    text = game_env.elements["notice-toast"].innerText
    assert "Grain Famine at Aurum solved in 1 tick(s)" in text and "Gold" in text and "Crisis Averted" in text


def test_gold_standard_needs_all_three_gold(game_env):
    m = game_env.module
    m.records["crisis_best"] = {c: {"medal": "gold", "ticks": 9} for c in CRISES[:2]}
    assert "gold_standard" not in m.achievement_ids_earned() and "crisis_averted" in m.achievement_ids_earned()
    m.records["crisis_best"]["broken_network"] = {"medal": "silver", "ticks": 90}
    assert "gold_standard" not in m.achievement_ids_earned()
    m.records["crisis_best"]["broken_network"]["medal"] = "gold"
    assert "gold_standard" in m.achievement_ids_earned()
    assert {a["id"]: a["progress"] for a in m.achievements_summary()}["gold_standard"] == (3, 3)


# --------------------------------------------------------------------- UI

def test_the_cards_show_pars_and_the_best_medal_as_shape_and_word(game_env):
    m = game_env.module
    game_env.elements["lab-toggle-button"].dispatch("click", None)
    text = game_env.elements["crisis-grain_famine-text"].innerText
    assert "Par: gold 40, silver 65, bronze 100 tick(s)" in text and "Best: not solved yet" in text
    m.records["crisis_best"]["grain_famine"] = {"medal": "silver", "ticks": 60}
    m.render()
    assert "Best: ◆ Silver in 60 tick(s)" in game_env.elements["crisis-grain_famine-text"].innerText


def test_buttons_start_restart_and_leave(game_env):
    m = game_env.module
    el = game_env.elements
    el["lab-toggle-button"].dispatch("click", None)
    assert el["crisis-restart-button"].hidden is True and el["crisis-leave-button"].hidden is True
    el["crisis-broken_network-start-button"].dispatch("click", None)
    assert m.crisis_active == "broken_network" and el["crisis-restart-button"].hidden is False
    assert el["crisis-broken_network-start-button"].innerText == "Restart"
    assert "tick 0" in el["crisis-status"].innerText and "Par: gold 80" in el["crisis-status"].innerText
    game_env.tick(3)
    el["crisis-restart-button"].dispatch("click", None)
    assert m.crisis_ticks == 0
    el["crisis-leave-button"].dispatch("click", None)
    assert m.crisis_active is None and el["crisis-restart-button"].hidden is True


def test_the_restart_hotkey_is_listed_in_the_help_and_wired_on_both_pages():
    from .pagefiles import page_text
    for page in ("index.html", "pc.html"):
        html = page_text(page)
        assert "R — restart the Trade Crisis you are playing" in html, page
        assert 'getElementById("crisis-restart-button")' in html and 'e.key !== "r"' in html, page


# ------------------------------------------------------------------- saves

def test_nothing_saved_until_a_crisis_is_solved(game_env):
    assert "records" not in game_env.module.get_state()


def test_the_medals_round_trip_through_a_save(game_env):
    m = game_env.module
    m.records["crisis_best"] = {"grain_famine": {"medal": "gold", "ticks": 30}}
    state = json.loads(json.dumps(m.get_state()))
    m.records["crisis_best"] = {}
    m.load_state(state)
    assert m.records["crisis_best"] == {"grain_famine": {"medal": "gold", "ticks": 30}}


@pytest.mark.parametrize("raw", [
    "x", 3, [], {"nope": {"medal": "gold", "ticks": 3}},
    {"grain_famine": "gold"}, {"grain_famine": {"medal": "platinum", "ticks": 3}},
    {"grain_famine": {"medal": "gold", "ticks": 0}}, {"grain_famine": {"medal": "gold", "ticks": True}},
    {"grain_famine": {"medal": "gold", "ticks": "3"}}, {"grain_famine": {"medal": ["gold"], "ticks": 3}},
    {"grain_famine": {"medal": "gold", "ticks": 10 ** 9}}, {5: {"medal": "gold", "ticks": 3}},
])
def test_tampered_medals_are_dropped(game_env, raw):
    m = game_env.module
    state = json.loads(json.dumps(m._fresh_state))
    state["records"] = {"crisis_best": raw}
    assert m.load_state(state) is True
    assert m.records["crisis_best"] == {}


def test_medals_survive_a_renewal(game_env):
    m = game_env.module
    m.records["crisis_best"] = {"grain_famine": {"medal": "gold", "ticks": 30}}
    m.endgame_reached = True
    m.found_new_corporation()
    assert m.records["crisis_best"]["grain_famine"]["medal"] == "gold"


def test_loading_a_save_while_a_crisis_runs_leaves_the_crisis(game_env):
    m = game_env.module
    saved = json.loads(json.dumps(m.get_state()))
    m.crisis_enter("grain_famine")
    m.load_state(saved)
    assert m.crisis_active is None and not m.sandbox_is_active()
