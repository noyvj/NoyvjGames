"""A-23: Blueprint Swap (build plan, Doctrine rules and mutator picks in one local code)."""


def _texts(element):
    out = [element.innerText]
    for child in element.children:
        out.extend(_texts(child))
    return out


def _import(env, code):
    env.elements["blueprint-input"].value = code
    env.elements["blueprint-import-button"].dispatch("click")


def _ghost_click(env, **attrs):
    env.panel_click("blueprint-ghost", **attrs)


def _fill(env):
    m = env.module
    m._add_build_step("5 Auto-Miners")
    m._add_build_step("1 Recycler")
    m.build_plan[0]["done"] = True
    m.doctrine_rules[:] = [{"planet": "Mars", "cond": "ecology_below", "level": 30, "action": "recycler"}]
    m.mutators_next[:] = ["thin_atmosphere", "blind_governor"]


def test_code_round_trips_steps_rules_and_picks_but_not_ticks(game_env):
    m = game_env.module
    _fill(game_env)
    code = m.blueprint_code()
    assert code.startswith("SOLPLAN1:")
    ok, result = m.parse_blueprint(code)
    assert ok
    assert result["steps"] == ["5 Auto-Miners", "1 Recycler"]
    assert result["rules"] == m.doctrine_rules
    assert result["mutators"] == ["thin_atmosphere", "blind_governor"]


def test_make_button_fills_the_box_and_status(game_env):
    m = game_env.module
    _fill(game_env)
    game_env.elements["blueprint-make-button"].dispatch("click")
    out = game_env.elements["blueprint-output"]
    assert out.value == m.blueprint_code() and out.hidden is False
    assert "Blueprint made" in game_env.elements["blueprint-status"].innerText


def test_import_shows_a_ghost_and_changes_nothing(game_env):
    m = game_env.module
    _fill(game_env)
    code = m.blueprint_code()
    m.build_plan.clear()
    m.doctrine_rules.clear()
    m.mutators_next.clear()
    _import(game_env, code)
    ghost = game_env.elements["blueprint-ghost"]
    assert ghost.hidden is False
    text = "\n".join(_texts(ghost))
    assert "5 Auto-Miners" in text and "Rule: On Mars, if ecology is below 30%, buy a Recycler." in text
    assert "Thin Atmosphere" in text
    assert m.build_plan == [] and m.doctrine_rules == [] and m.mutators_next == []


def test_adopting_each_part_is_a_separate_choice(game_env):
    m = game_env.module
    _fill(game_env)
    code = m.blueprint_code()
    m.build_plan.clear()
    m.doctrine_rules.clear()
    m.mutators_next.clear()
    _import(game_env, code)
    _ghost_click(game_env, action="add-step", step="1")
    assert [s["text"] for s in m.build_plan] == ["1 Recycler"]
    _ghost_click(game_env, action="add-all")
    assert [s["text"] for s in m.build_plan] == ["1 Recycler", "5 Auto-Miners"]  # no duplicates
    assert all(s["done"] is False for s in m.build_plan)
    _ghost_click(game_env, action="adopt-rules")
    assert len(m.doctrine_rules) == 1
    _ghost_click(game_env, action="adopt-rules")
    assert len(m.doctrine_rules) == 1  # the same rule is not added twice
    _ghost_click(game_env, action="use-mutators")
    assert m.mutators_next == ["thin_atmosphere", "blind_governor"]
    _ghost_click(game_env, action="clear")
    assert game_env.elements["blueprint-ghost"].hidden is True


def test_added_steps_respect_the_plan_limit(game_env):
    m = game_env.module
    for i in range(m.BUILD_PLAN_MAX_STEPS):
        m._add_build_step(f"step {i}")
    m._ghost["steps"] = ["one more"]
    m.update_blueprint_ghost()
    _ghost_click(game_env, action="add-step", step="0")
    assert len(m.build_plan) == m.BUILD_PLAN_MAX_STEPS


def test_rules_are_added_only_up_to_the_absolute_cap(game_env):
    m = game_env.module
    rule = {"planet": "Mars", "cond": "ecology_below", "level": 30, "action": "pause"}
    m.doctrine_rules[:] = [dict(rule, level=70)] * 4
    m._ghost["rules"] = [dict(rule), dict(rule, level=50)]
    m.update_blueprint_ghost()
    _ghost_click(game_env, action="adopt-rules")
    assert len(m.doctrine_rules) == m.DOCTRINE_MAX_RULES


def test_bad_codes_fail_soft_with_a_message(game_env):
    m = game_env.module
    for bad in ("", "hello", "SOLSTATS1:abcd", "SOLPLAN1:", "SOLPLAN1:!!!!", None):
        ok, message = m.parse_blueprint(bad)
        assert ok is False and isinstance(message, str) and message
    _import(game_env, "SOLPLAN1:@@@")
    assert game_env.elements["blueprint-ghost"].children == []
    assert game_env.elements["blueprint-status"].innerText


def test_hostile_payloads_are_cleaned(game_env):
    import base64
    import json
    m = game_env.module
    payload = {"p": ["ok", "", "   ", 5, None, "x" * 500] + ["s"] * 100,
               "d": ["x", {"planet": "Nope"}, {"planet": "Mars", "cond": "ecology_below", "level": 30, "action": "pause"}],
               "m": ["thin_atmosphere", "bogus", "thin_atmosphere", "one_way_trade", "blind_governor", "costly_machinery"]}
    code = "SOLPLAN1:" + base64.b64encode(json.dumps(payload).encode()).decode()
    ok, result = m.parse_blueprint(code)
    assert ok
    assert len(result["steps"]) <= m.BUILD_PLAN_MAX_STEPS
    assert all(0 < len(t) <= m.BUILD_PLAN_MAX_LEN for t in result["steps"])
    assert len(result["rules"]) == 1
    assert result["mutators"] == ["thin_atmosphere", "one_way_trade", "blind_governor"]


def test_an_empty_blueprint_is_refused(game_env):
    m = game_env.module
    m.build_plan.clear()
    m.doctrine_rules.clear()
    m.mutators_next.clear()
    ok, message = m.parse_blueprint(m.blueprint_code())
    assert ok is False and "empty" in message


def test_the_ghost_is_never_saved(game_env):
    m = game_env.module
    _fill(game_env)
    _import(game_env, m.blueprint_code())
    state = m.serialize_state()
    assert "blueprint" not in str(state.keys()) and "ghost" not in str(state.keys())


def test_clipboard_failure_falls_back_to_the_visible_box(game_env):
    import sys
    _fill(game_env)

    class Boom:
        @property
        def clipboard(self):
            raise AttributeError("no clipboard")

    sys.modules["js"].navigator = Boom()
    game_env.elements["blueprint-make-button"].dispatch("click")
    assert "select the code below" in game_env.elements["blueprint-status"].innerText
    assert game_env.elements["blueprint-output"].hidden is False
