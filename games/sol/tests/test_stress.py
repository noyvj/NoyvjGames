"""A-27 / A-28: the Ecology Stress Test (a headless run on a copy) and its per-world strips."""

import copy
import json


def _texts(element):
    out = [element.innerText]
    for child in element.children:
        out.extend(_texts(child))
    return out


def _win(env):
    for p in env.module.PLANETS:
        env.module.planet_state[p]["terraform_progress"] = env.module.TERRAFORM_MAX
    env.module.update_win_display()


def _numbers(m):
    return (copy.deepcopy(m.planet_state), m.total_ticks, m.current_planet, m.sandbox_mode, m._active_anomaly,
            m.governor_purchase_count, m.governor_tick_count, m.lifetime_generators_built,
            m.lifetime_recyclers_built, m.lifetime_trade_routes_built,
            m.lifetime_resources_generated_by_automation, dict(m._doctrine_fired_counts),
            dict(m._stress_factors), list(m.achievement_ids_earned()))


def _healthy(m):
    for p in m.PLANETS:
        m.planet_state[p].update(generator_count=3, recycler_count=40, ecology_health=100.0)


def _doomed(m):
    for p in m.PLANETS:
        m.planet_state[p].update(generator_count=60, recycler_count=0, ecology_health=100.0)


def test_locked_until_every_world_is_terraformed(game_env):
    m = game_env.module
    assert m.run_stress_test() is None
    game_env.elements["charter-toggle-button"].dispatch("click")
    buttons = [e for e in game_env.elements["charter-panel"].descendants() if getattr(e, "tagName", "") == "BUTTON"
               and "Opens when every world is terraformed" in e.innerText]
    assert buttons and buttons[0].disabled is True


def test_a_run_changes_nothing_real(game_env):
    m = game_env.module
    _win(game_env)
    _healthy(m)
    before = _numbers(m)
    result = m.run_stress_test()
    assert result is not None
    assert _numbers(m) == before
    assert m._dry_run is False and m._stress_factors == {}


def test_a_well_built_system_holds_the_line_and_a_doomed_one_does_not(game_env):
    m = game_env.module
    _win(game_env)
    _healthy(m)
    good = m.run_stress_test()
    assert good["margin"] > 0
    _doomed(m)
    bad = m.run_stress_test()
    assert bad["margin"] < 0 < good["margin"]
    assert bad["margin"] < good["margin"]


def test_every_world_is_governed_during_the_run(game_env):
    m = game_env.module
    _win(game_env)
    m.current_planet = "Mars"
    for p in m.PLANETS:
        m.planet_state[p].update(generator_count=2, recycler_count=0, resource_count=500.0)
    m.governor_priority = "ecology"
    m.governor_budget_pct = 100.0
    seen = {}

    original = m.governor_step

    def spy():
        seen["current"] = m.current_planet
        original()

    m.governor_step = spy
    m.run_stress_test()
    assert seen["current"] == "Deep space"
    assert m.current_planet == "Mars"


def test_the_cascade_gets_harsher_in_phases(game_env):
    m = game_env.module
    factors = [f for _, f in m.STRESS_PHASES]
    assert [f["decay"] for f in factors] == sorted(f["decay"] for f in factors) and len(factors) == 3


def test_strip_per_world_has_twelve_blocks_and_text_marks(game_env):
    m = game_env.module
    _win(game_env)
    _doomed(m)
    result = m.run_stress_test()
    for planet in m.PLANETS:
        assert len(result["rows"][planet]) == m.STRESS_TICKS // m.STRESS_SAMPLE_EVERY == 12
    assert m.stress_block(0) == "x" and m.stress_block(5) == "!" and m.stress_block(100) == m.STRESS_BLOCKS[-1]
    assert m.stress_block(10) == m.STRESS_BLOCKS[0] and m.stress_block(55) == m.STRESS_BLOCKS[4]


def test_panel_shows_verdict_strips_and_legend_in_words(game_env):
    m = game_env.module
    _win(game_env)
    _healthy(m)
    game_env.elements["charter-toggle-button"].dispatch("click")
    game_env.panel_click("charter-panel", action="stress")
    text = "\n".join(_texts(game_env.elements["charter-panel"]))
    assert "Result: held the line." in text and "points from the line" in text
    assert "! is under 10%" in text and "x is 0%" in text
    assert "Earth: " in text and "lowest " in text
    assert "Best so far:" in text
    _doomed(m)
    game_env.panel_click("charter-panel", action="stress")
    assert "dipped under the line" in "\n".join(_texts(game_env.elements["charter-panel"]))


def test_best_margin_only_goes_up_and_is_saved(game_env):
    m = game_env.module
    _win(game_env)
    assert "stress_best_margin" not in m.serialize_state()
    _healthy(m)
    good = m.run_stress_test()["margin"]
    _doomed(m)
    m.run_stress_test()
    assert m.stress_best_margin == good
    state = json.loads(json.dumps(m.serialize_state()))
    assert state["stress_best_margin"] == good
    m.stress_best_margin = None
    m.deserialize_state(state)
    assert m.stress_best_margin == good


def test_bad_saved_margins_are_dropped(game_env):
    m = game_env.module
    for bad in ("x", None, True, 1e9, float("nan"), [3], {"a": 1}):
        m.stress_best_margin = 5.0
        m.deserialize_state({"stress_best_margin": bad})
        assert m.stress_best_margin is None


def test_state_is_restored_even_if_the_run_errors(game_env):
    m = game_env.module
    _win(game_env)
    _healthy(m)
    before = _numbers(m)
    original = m.governor_step

    def boom():
        m.planet_state["Mars"]["resource_count"] += 999999
        raise RuntimeError("boom")

    m.governor_step = boom
    try:
        m.run_stress_test()
    except RuntimeError:
        pass
    m.governor_step = original
    assert _numbers(m) == before and m._dry_run is False


def test_sandbox_does_not_hide_the_governor_in_the_test(game_env):
    m = game_env.module
    _win(game_env)
    _healthy(m)
    m.sandbox_mode = True
    m.run_stress_test()
    assert m.sandbox_mode is True  # put back afterwards
