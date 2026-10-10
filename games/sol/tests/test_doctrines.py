"""A-7 / A-8: Governor Doctrines (per-world if/then rules) and the 30-tick dry run."""

import copy
import json


def _texts(element):
    out = [element.innerText]
    for child in element.children:
        out.extend(_texts(child))
    return out


def _unlock(env):
    env.module.researched_nodes.add("automation_basics")
    env.module.unlocked_bodies.update(["Mars", "Moon"])
    env.module.update_doctrine_display()


def _rule(planet="Mars", cond="ecology_below", level=50, action="recycler"):
    return {"planet": planet, "cond": cond, "level": level, "action": action}


def _add_via_ui(env, **kw):
    r = _rule(**kw)
    env.panel_click("doctrine-panel", action="draft-planet", value=r["planet"])
    env.panel_click("doctrine-panel", action="draft-cond", value=f"{r['cond']}:{r['level']}")
    env.panel_click("doctrine-panel", action="draft-action", value=r["action"])
    env.panel_click("doctrine-panel", action="add")


def test_locked_until_automation_basics(game_env):
    m = game_env.module
    assert game_env.elements["doctrine-toggle-button"].hidden is True
    m.doctrine_rules.append(_rule())
    m.planet_state["Mars"].update(ecology_health=10.0, resource_count=1000.0)
    m.governor_step()
    assert m._doctrine_fired_counts == {}  # rules sleep while locked
    _unlock(game_env)
    assert game_env.elements["doctrine-toggle-button"].hidden is False


def test_ecology_rule_buys_a_recycler_on_a_governed_world(game_env):
    m = game_env.module
    _unlock(game_env)
    m.doctrine_rules.append(_rule("Mars", "ecology_below", 50, "recycler"))
    m.planet_state["Mars"].update(ecology_health=40.0, resource_count=1000.0)
    m.governor_step()
    assert m.planet_state["Mars"]["recycler_count"] >= 1
    assert m._doctrine_fired_counts[0] == 1
    assert "Doctrine fired" in m.doctrine_report_line("Mars")


def test_rule_does_not_fire_when_its_condition_is_false_or_you_stand_there(game_env):
    m = game_env.module
    _unlock(game_env)
    m.doctrine_rules.append(_rule("Mars", "ecology_below", 30, "recycler"))
    m.planet_state["Mars"].update(ecology_health=80.0, resource_count=1000.0)
    m.governor_step()
    assert m._doctrine_fired_counts == {}
    m.planet_state["Mars"]["ecology_health"] = 10.0
    m.current_planet = "Mars"  # the Governor only runs worlds you are not on
    m.governor_step()
    assert m._doctrine_fired_counts == {}


def test_pause_rule_stops_the_governors_own_buying(game_env):
    m = game_env.module
    _unlock(game_env)
    m.governor_priority = "growth"
    m.governor_budget_pct = 100.0
    m.planet_state["Mars"].update(ecology_health=20.0, resource_count=1000.0)
    m.governor_step()
    assert m.planet_state["Mars"]["generator_count"] >= 1  # the plain Governor buys
    m.planet_state["Mars"].update(generator_count=0, resource_count=1000.0)
    m.doctrine_rules.append(_rule("Mars", "ecology_below", 30, "pause"))
    m.governor_step()
    assert m.planet_state["Mars"]["generator_count"] == 0 and m.planet_state["Mars"]["resource_count"] == 1000.0
    assert m._doctrine_fired_counts[0] == 1


def test_stock_rule_buys_an_auto_miner(game_env):
    m = game_env.module
    _unlock(game_env)
    m.doctrine_rules.append(_rule("Moon", "stock_above", 500, "generator"))
    m.planet_state["Moon"]["resource_count"] = 800.0
    m.governor_budget_pct = 0.0
    m.governor_step()
    assert m.planet_state["Moon"]["generator_count"] >= 1


def test_relief_ships_ecology_from_the_biggest_other_pile_with_a_cooldown(game_env):
    m = game_env.module
    _unlock(game_env)
    m.governor_budget_pct = 0.0
    m.doctrine_rules.append(_rule("Mars", "ecology_below", 50, "relief"))
    m.planet_state["Mars"].update(ecology_health=20.0, resource_count=0.0)
    m.planet_state["Earth"]["resource_count"] = 500.0
    m.governor_step()
    assert abs(m.planet_state["Mars"]["ecology_health"] - 30.0) < 1e-9
    assert m.planet_state["Earth"]["resource_count"] == 400.0
    m.governor_step()  # cooldown
    assert abs(m.planet_state["Mars"]["ecology_health"] - 30.0) < 1e-9
    m.total_ticks += m.DOCTRINE_RELIEF_COOLDOWN_TICKS
    m.governor_step()
    assert abs(m.planet_state["Mars"]["ecology_health"] - 40.0) < 1e-9


def test_relief_needs_a_pile_to_ship(game_env):
    m = game_env.module
    _unlock(game_env)
    m.governor_budget_pct = 0.0
    m.doctrine_rules.append(_rule("Mars", "ecology_below", 50, "relief"))
    m.planet_state["Mars"].update(ecology_health=20.0, resource_count=0.0)
    m.planet_state["Earth"]["resource_count"] = 99.0
    m.governor_step()
    assert m.planet_state["Mars"]["ecology_health"] == 20.0 and m._doctrine_fired_counts == {}


def test_route_rule_builds_a_trade_route_to_the_neediest_world(game_env):
    m = game_env.module
    _unlock(game_env)
    m.governor_budget_pct = 0.0
    m.doctrine_rules.append(_rule("Moon", "stock_above", 500, "route"))
    m.planet_state["Moon"]["resource_count"] = 900.0
    m.planet_state["Mars"]["ecology_health"] = 30.0
    m.governor_step()
    assert m.planet_state["Moon"]["trade_routes"].get("Mars", 0) == 1
    assert m.lifetime_trade_routes_built >= 1


def test_sandbox_governor_runs_no_rules(game_env):
    m = game_env.module
    _unlock(game_env)
    for p in m.PLANETS:
        m.planet_state[p]["terraform_progress"] = m.TERRAFORM_MAX
    m.sandbox_mode = True
    m.doctrine_rules.append(_rule("Mars", "ecology_below", 70, "pause"))
    m.planet_state["Mars"]["ecology_health"] = 10.0
    m.governor_step()
    assert m._doctrine_fired_counts == {}


def test_rule_limit_three_then_five_with_standing_orders(game_env):
    m = game_env.module
    _unlock(game_env)
    for _ in range(5):
        _add_via_ui(game_env)
    assert len(m.doctrine_rules) == 3
    m.prestige_nodes.add("standing_orders")
    for _ in range(5):
        _add_via_ui(game_env)
    assert len(m.doctrine_rules) == 5
    assert m.doctrine_rule_limit() == 5


def test_only_the_first_rules_within_the_limit_run(game_env):
    m = game_env.module
    _unlock(game_env)
    m.doctrine_rules[:] = [_rule("Mars", "ecology_below", 70, "pause")] * 3 + [_rule("Moon", "stock_above", 500, "generator")]
    m.planet_state["Moon"]["resource_count"] = 900.0
    m.governor_budget_pct = 0.0
    m.governor_step()
    assert m.planet_state["Moon"]["generator_count"] == 0


def test_remove_and_bad_input(game_env):
    m = game_env.module
    _unlock(game_env)
    _add_via_ui(game_env)
    game_env.panel_click("doctrine-panel", action="remove", value="5")
    game_env.panel_click("doctrine-panel", action="remove", value="x")
    game_env.panel_click("doctrine-panel", action="draft-planet", value="Nowhere")
    game_env.panel_click("doctrine-panel", action="draft-cond", value="ecology_below:99")
    game_env.panel_click("doctrine-panel", action="draft-action", value="explode")
    assert len(m.doctrine_rules) == 1
    game_env.panel_click("doctrine-panel", action="remove", value="0")
    assert m.doctrine_rules == []


def test_panel_lists_rules_with_text_and_fired_counts(game_env):
    _unlock(game_env)
    game_env.elements["doctrine-toggle-button"].dispatch("click")
    _add_via_ui(game_env, planet="Mars", cond="ecology_below", level=50, action="recycler")
    text = "\n".join(_texts(game_env.elements["doctrine-panel"]))
    assert "On Mars, if ecology is below 50%, buy a Recycler." in text
    assert "Fired 0 times this session" in text and "Preview:" in text


def test_governor_report_shows_the_rule_that_fired(game_env):
    m = game_env.module
    _unlock(game_env)
    m.doctrine_rules.append(_rule("Mars", "ecology_below", 50, "recycler"))
    m.planet_state["Mars"].update(ecology_health=30.0, resource_count=500.0)
    game_env.toggle_governor_report()
    text = "\n".join(_texts(game_env.elements["governor-report-panel"]))
    assert "Doctrine: no rule has fired here yet." in text
    m.governor_step()
    m.update_governor_report_display()
    text = "\n".join(_texts(game_env.elements["governor-report-panel"]))
    assert "Doctrine fired" in text and "buy a Recycler" in text


# --- A-8 dry run -----------------------------------------------------------------


def _numbers(m):
    return (copy.deepcopy(m.planet_state), m.governor_purchase_count, m.governor_tick_count,
            m.lifetime_generators_built, m.lifetime_recyclers_built, m.lifetime_trade_routes_built,
            m.lifetime_resources_generated_by_automation, m.any_generator_ever_built,
            dict(m._doctrine_fired_counts), dict(m._doctrine_last_fired), m.total_ticks)


def test_dry_run_counts_fires_and_changes_nothing(game_env):
    m = game_env.module
    _unlock(game_env)
    m.doctrine_rules.append(_rule("Mars", "ecology_below", 50, "recycler"))
    m.planet_state["Mars"].update(ecology_health=30.0, resource_count=5000.0, generator_count=3)
    before = _numbers(m)
    total, counts = m.doctrine_dry_run()
    assert total >= 1 and counts[0] == total
    assert _numbers(m) == before
    assert m._dry_run is False


def test_dry_run_of_a_rule_that_never_holds_says_zero(game_env):
    m = game_env.module
    _unlock(game_env)
    m.doctrine_rules.append(_rule("Mars", "stock_above", 5000, "generator"))
    assert m.doctrine_dry_run()[0] == 0


def test_dry_run_button_prints_the_result_and_leaves_the_game_alone(game_env):
    m = game_env.module
    _unlock(game_env)
    game_env.elements["doctrine-toggle-button"].dispatch("click")
    m.doctrine_rules.append(_rule("Mars", "ecology_below", 50, "pause"))
    m.planet_state["Mars"]["ecology_health"] = 20.0
    stock = m.planet_state["Mars"]["resource_count"]
    game_env.panel_click("doctrine-panel", action="dry-run")
    text = "\n".join(_texts(game_env.elements["doctrine-panel"]))
    assert "would have fired 30 times" in text and "Nothing was changed." in text
    assert m.planet_state["Mars"]["resource_count"] == stock and m._doctrine_fired_counts == {}


def test_dry_run_restores_state_even_if_a_rule_errors(game_env):
    m = game_env.module
    _unlock(game_env)
    m.doctrine_rules.append(_rule("Mars", "ecology_below", 50, "pause"))
    m.planet_state["Mars"]["ecology_health"] = 20.0
    original = m._simulate_planet

    def boom(*args):
        m.planet_state["Mars"]["resource_count"] += 123456
        raise RuntimeError("boom")

    m._simulate_planet = boom
    try:
        m.doctrine_dry_run()
    except RuntimeError:
        pass
    m._simulate_planet = original
    assert m.planet_state["Mars"]["resource_count"] < 1000 and m._dry_run is False


# --- save ------------------------------------------------------------------------


def test_save_round_trip_and_validation(game_env):
    m = game_env.module
    assert "doctrine_rules" not in m.serialize_state()
    m.doctrine_rules[:] = [_rule("Mars", "ecology_below", 30, "pause"), _rule("Moon", "stock_above", 2000, "route")]
    state = json.loads(json.dumps(m.serialize_state()))
    m.doctrine_rules.clear()
    m.deserialize_state(state)
    assert m.doctrine_rules == [_rule("Mars", "ecology_below", 30, "pause"), _rule("Moon", "stock_above", 2000, "route")]


def test_bad_saved_rules_are_dropped(game_env):
    m = game_env.module
    good = _rule()
    bad = [
        "x", 5, None, {}, {"planet": "Nope", "cond": "ecology_below", "level": 30, "action": "pause"},
        {"planet": "Mars", "cond": "bogus", "level": 30, "action": "pause"},
        {"planet": "Mars", "cond": "ecology_below", "level": 31, "action": "pause"},
        {"planet": "Mars", "cond": "ecology_below", "level": True, "action": "pause"},
        {"planet": "Mars", "cond": "ecology_below", "level": 30, "action": "explode"},
        {"planet": "Mars", "cond": "ecology_below", "level": "30", "action": "pause"},
    ]
    m.deserialize_state({"doctrine_rules": bad + [good] * 9})
    assert m.doctrine_rules == [good] * 5  # junk dropped, absolute cap of five
    m.deserialize_state({"doctrine_rules": "x"})
    assert m.doctrine_rules == []


def test_prestige_keeps_rules_but_they_sleep_until_researched_again(game_env):
    m = game_env.module
    _unlock(game_env)
    m.doctrine_rules.append(_rule())
    for p in m.PLANETS:
        m.planet_state[p]["terraform_progress"] = m.TERRAFORM_MAX
    game_env.prestige()
    assert m.doctrine_rules == [_rule()] and m.doctrines_unlocked() is False
    assert game_env.elements["doctrine-toggle-button"].hidden is True


def test_standing_orders_is_in_the_prestige_tree(game_env):
    m = game_env.module
    node = m.PRESTIGE_TREE_BY_ID["standing_orders"]
    assert node["tier"] == 2 and node["cost"] == 2 and node["min_level"] == m.PRESTIGE_TIER_2_LEVEL
