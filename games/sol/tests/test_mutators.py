"""A-3 / A-4 / FY-49: prestige mutators (opt-in rule twists paid in prestige points)."""

import json


def _win(env):
    for p in env.module.PLANETS:
        env.module.planet_state[p]["terraform_progress"] = env.module.TERRAFORM_MAX
    env.module.update_win_display()


def _pick(env, mutator_id):
    env.panel_click("prestige-tree-panel", action="mutator", mutator=mutator_id)


def _ecology_after_one_tick(m, planet="Earth"):
    m.planet_state[planet]["ecology_health"] = 100.0
    m.planet_state[planet]["generator_count"] = 10
    m._simulate_planet(planet, 0.0)
    return 100.0 - m.planet_state[planet]["ecology_health"]


def test_no_mutators_by_default_and_nothing_changes(game_env):
    m = game_env.module
    assert m.mutators_next == [] and m.mutators_run == []
    assert m.mutator_points(m.mutators_run) == 0
    assert m.mutator_glyphs([]) == ""
    assert m.generator_cost("Earth") == 10


def test_thin_atmosphere_makes_ecology_decay_forty_percent_faster(game_env):
    m = game_env.module
    base = _ecology_after_one_tick(m)
    m.mutators_run[:] = ["thin_atmosphere"]
    assert abs(_ecology_after_one_tick(m) / base - 1.4) < 1e-9


def test_one_way_trade_halves_trade_restore(game_env):
    m = game_env.module
    m.planet_state["Mars"]["trade_routes"] = {"Earth": 2}
    full = m._incoming_trade_restore("Earth")
    m.mutators_run[:] = ["one_way_trade"]
    assert abs(m._incoming_trade_restore("Earth") - full / 2) < 1e-12


def test_costly_machinery_raises_generator_and_recycler_cost(game_env):
    m = game_env.module
    base_gen, base_rec = m.generator_cost("Earth"), m.recycler_cost("Earth")
    m.mutators_run[:] = ["costly_machinery"]
    assert m.generator_cost("Earth") > base_gen and m.recycler_cost("Earth") > base_rec
    assert m.generator_cost("Earth") == 12  # ceil(10 * 1.15)


def test_blind_governor_ignores_priority_and_caps_the_budget(game_env):
    m = game_env.module
    m.unlocked_bodies.add("Mars")
    m.current_planet = "Earth"
    m.governor_priority = "growth"
    m.governor_budget_pct = 100.0
    m.planet_state["Mars"]["resource_count"] = 1000.0
    m.mutators_run[:] = ["blind_governor"]
    m.governor_tick_count = 1  # next step is turn 2: a "balance" generator turn
    m.governor_step()
    spent = 1000.0 - m.planet_state["Mars"]["resource_count"]
    assert spent <= 250.0
    assert m.planet_state["Mars"]["generator_count"] + m.planet_state["Mars"]["recycler_count"] >= 1


def test_picks_toggle_and_stop_at_three(game_env):
    m = game_env.module
    _win(game_env)
    _pick(game_env, "thin_atmosphere")
    _pick(game_env, "one_way_trade")
    _pick(game_env, "blind_governor")
    _pick(game_env, "costly_machinery")  # a fourth is refused
    assert m.mutators_next == ["thin_atmosphere", "one_way_trade", "blind_governor"]
    _pick(game_env, "one_way_trade")  # toggles off
    assert "one_way_trade" not in m.mutators_next
    _pick(game_env, "costly_machinery")
    assert len(m.mutators_next) == 3
    _pick(game_env, "not_a_mutator")
    assert len(m.mutators_next) == 3


def test_tree_button_appears_when_a_prestige_is_available(game_env):
    assert game_env.elements["prestige-tree-toggle-button"].hidden is True
    _win(game_env)
    assert game_env.elements["prestige-tree-toggle-button"].hidden is False


def test_picks_are_locked_in_at_prestige_and_paid_at_the_next_one(game_env):
    m = game_env.module
    _win(game_env)
    _pick(game_env, "thin_atmosphere")
    _pick(game_env, "costly_machinery")
    game_env.prestige()
    assert m.prestige_points_earned == 1  # the first run had no twists
    assert m.mutators_run == ["thin_atmosphere", "costly_machinery"]
    # Changing the picks mid-run does not change the rules this run plays under.
    _pick(game_env, "thin_atmosphere")
    assert m.mutators_run == ["thin_atmosphere", "costly_machinery"]
    _win(game_env)
    game_env.prestige()
    assert m.prestige_points_earned == 1 + 1 + 2  # base point plus two twists
    assert m.mutators_run == ["costly_machinery"]


def test_unchosen_run_pays_the_plain_point(game_env):
    m = game_env.module
    _win(game_env)
    game_env.prestige()
    _win(game_env)
    game_env.prestige()
    assert m.prestige_points_earned == 2


def test_badge_and_share_text_show_the_rules(game_env):
    m = game_env.module
    _win(game_env)
    _pick(game_env, "thin_atmosphere")
    game_env.prestige()
    badge = game_env.elements["prestige-badge"]
    assert badge.innerText.startswith("Prestige 1") and "☁" in badge.innerText
    assert "Thin Atmosphere" in badge.title
    card = m.build_share_card_text()
    assert "Run rules:" in card and "Thin Atmosphere" in card
    assert any("Thin Atmosphere" in s for s in m.copy_result_fields()["stats"])


def test_panel_lists_every_mutator_with_a_text_button(game_env):
    m = game_env.module
    _win(game_env)
    game_env.elements["prestige-tree-toggle-button"].dispatch("click")
    texts = []

    def walk(el):
        texts.append(el.innerText)
        for c in el.children:
            walk(c)

    walk(game_env.elements["prestige-tree-panel"])
    joined = "\n".join(texts)
    for entry in m.MUTATORS:
        assert entry["label"] in joined
    assert "Pick for next run" in joined


def test_save_round_trip_and_validation(game_env):
    m = game_env.module
    state = m.serialize_state()
    assert "mutators_next" not in state and "mutators_run" not in state  # default: no new keys
    m.mutators_next[:] = ["blind_governor"]
    m.mutators_run[:] = ["thin_atmosphere", "costly_machinery"]
    state = json.loads(json.dumps(m.serialize_state()))
    m.mutators_next.clear()
    m.mutators_run.clear()
    m.deserialize_state(state)
    assert m.mutators_next == ["blind_governor"]
    assert m.mutators_run == ["thin_atmosphere", "costly_machinery"]


def test_bad_save_values_are_dropped(game_env):
    m = game_env.module
    for bad in ("thin_atmosphere", 5, None, {"a": 1}, [1, None, "nope"]):
        m.deserialize_state({"mutators_next": bad, "mutators_run": bad})
        assert m.mutators_next == [] or m.mutators_next == (["thin_atmosphere"] if bad == "thin_atmosphere" else [])
        assert m.mutators_run == []
    m.deserialize_state({"mutators_next": ["thin_atmosphere"] * 3 + ["one_way_trade", "blind_governor", "costly_machinery"]})
    assert m.mutators_next == ["thin_atmosphere", "one_way_trade", "blind_governor"]


def test_old_saves_load_without_the_keys(game_env):
    m = game_env.module
    m.mutators_run[:] = ["thin_atmosphere"]
    m.deserialize_state({"prestige_level": 2})
    assert m.mutators_run == [] and m.mutators_next == []


def test_prestige_confirm_message_mentions_the_picks(game_env):
    from .test_confirm_dialog import install_fake_confirm_dialog

    m = game_env.module
    dialog = install_fake_confirm_dialog().ConfirmDialog
    _win(game_env)
    _pick(game_env, "one_way_trade")
    game_env.prestige()
    assert dialog.calls and "One-Way Trade" in dialog.calls[0]["message"]
    assert m.prestige_level == 0  # nothing happens until it is confirmed
    dialog.confirm()
    assert m.prestige_level == 1 and m.mutators_run == ["one_way_trade"]
