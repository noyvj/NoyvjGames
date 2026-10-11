"""J-19 / J-20 -- the Blueprint Lab: a fixed point budget over hold, speed and efficiency, saved hull designs,
a labelled comparison with the average hull, and ships that keep their hull for good."""

import json

import pytest


def _lab(m):
    m.unlocked_research.update({"fast_ships", "hauler"})
    m.total_profit = m.max_profit_ever = 10_000
    return m


def _hull(**kw):
    hull = {"name": "Tester", "hold": 3, "speed": 3, "eff": 3}
    hull.update(kw)
    return hull


def test_locked_until_both_researches(game_env):
    m = game_env.module
    assert not m.blueprint_lab_open()
    assert m.adjust_blueprint("hold", 1) is False and m.save_blueprint("x") is None
    m.unlocked_research.add("fast_ships")
    assert not m.blueprint_lab_open()
    game_env.elements["lab-toggle-button"].dispatch("click", None)
    assert "Locked" in game_env.elements["bp-status"].innerText
    assert game_env.elements["bp-controls"].hidden is True


def test_the_average_hull_equals_the_balanced_type(game_env):
    m = game_env.module
    fx = m.hull_effects(_hull())
    assert fx["cargo"] == pytest.approx(1.0) and fx["ticks"] == 0 and fx["proceeds"] == pytest.approx(1.0)


def test_effects_scale_as_documented(game_env):
    m = game_env.module
    assert m.hull_effects(_hull(hold=6))["cargo"] == pytest.approx(1.18)
    assert m.hull_effects(_hull(hold=1))["cargo"] == pytest.approx(0.88)
    assert [m.hull_effects(_hull(speed=s))["ticks"] for s in range(1, 7)] == [1, 1, 0, 0, -1, -1]
    assert m.hull_effects(_hull(eff=6))["proceeds"] == pytest.approx(1.06)
    assert m.hull_effects(_hull(eff=1))["proceeds"] == pytest.approx(0.96)


def test_the_budget_is_nine_points_and_stats_stay_in_range(game_env):
    m = _lab(game_env.module)
    assert m.blueprint_points_left() == 0
    assert m.adjust_blueprint("hold", 1) is False  # nothing left
    assert m.adjust_blueprint("hold", -1) and m.adjust_blueprint("hold", -1) and m.blueprint_points_left() == 2
    assert m.adjust_blueprint("speed", 1) and m.adjust_blueprint("speed", 1)
    assert m.blueprint_draft["speed"] == 5 and m.blueprint_points_left() == 0
    for _ in range(10):
        m.adjust_blueprint("hold", -1)
    assert m.blueprint_draft["hold"] == m.BLUEPRINT_STAT_MIN
    assert m.adjust_blueprint("nonsense", 1) is False and m.adjust_blueprint("hold", 2) is False


def test_no_design_in_budget_beats_every_tradeoff(game_env):
    m = game_env.module
    import itertools
    for hold, speed, eff in itertools.product(range(1, 7), repeat=3):
        if hold + speed + eff > m.BLUEPRINT_POINTS:
            continue
        fx = m.hull_effects(_hull(hold=hold, speed=speed, eff=eff))
        better_everywhere = fx["cargo"] > 1.0 and fx["ticks"] < 0 and fx["proceeds"] > 1.0
        assert not better_everywhere, (hold, speed, eff)


def test_saving_names_resets_and_caps_at_four(game_env):
    m = _lab(game_env.module)
    m.adjust_blueprint("hold", -1)
    m.adjust_blueprint("speed", 1)
    design = m.save_blueprint("  Long   Hauler  ")
    assert design["name"] == "Long Hauler" and design["hold"] == 2 and design["speed"] == 4
    for _ in range(3):
        assert m.save_blueprint("") is not None
    assert [d["name"] for d in m.blueprints][1:] == ["Design 2", "Design 3", "Design 4"]
    assert m.save_blueprint("fifth") is None and m.can_save_blueprint() is False


def test_long_names_are_trimmed(game_env):
    m = _lab(game_env.module)
    assert len(m.save_blueprint("x" * 80)["name"]) == m.MAX_SHIP_NAME_LENGTH


def test_deleting_a_design_never_changes_a_ship_built_from_it(game_env):
    m = _lab(game_env.module)
    m.blueprint_draft.update(hold=5, speed=2, eff=2)
    m.save_blueprint("Brick")
    assert m.purchase_ship("5", "bp0") is True
    ship = m.ships["5"]
    assert ship.archetype == "custom" and ship.hull["name"] == "Brick"
    assert m.delete_blueprint(0) is True and m.blueprints == []
    assert ship.hull["hold"] == 5 and m.archetype_for(ship)["label"] == "Brick"
    assert m.delete_blueprint(0) is False and m.delete_blueprint(True) is False


def test_the_ship_uses_its_hull_for_cargo_trip_time_and_sales(game_env):
    m = _lab(game_env.module)
    m.blueprint_draft.update(hold=5, speed=2, eff=2)  # +12% cargo, one tick slower, -2% sales
    m.save_blueprint("Brick")
    m.purchase_ship("5", "bp0")
    plain = m.ships["6"]
    m.purchase_ship("6", "balanced")
    brick = m.ships["5"]
    brick.load()
    plain.load()
    assert brick.cargo_qty > plain.cargo_qty
    brick.depart("verdant")
    plain.depart("verdant")
    assert brick.transit_total_ticks == plain.transit_total_ticks + 1
    assert game_env.module.archetype_for(brick)["proceeds"] == pytest.approx(0.98)


def test_a_ship_label_names_the_custom_hull(game_env):
    m = _lab(game_env.module)
    m.save_blueprint("Brick")
    m.purchase_ship("5", "bp0")
    m.render()
    assert "(Brick)" in game_env.elements["ship-5-label"].innerText


def test_an_unknown_or_stale_design_choice_falls_back(game_env):
    m = _lab(game_env.module)
    assert m.purchase_ship("5", "bp3") is True  # no such design
    assert m.ships["5"].archetype == "balanced" and m.ships["5"].hull is None
    assert m._blueprint_for_choice("bp-1") is None and m._blueprint_for_choice(5) is None


def test_the_buy_button_reads_a_design_from_the_picker(game_env):
    m = _lab(game_env.module)
    m.save_blueprint("Brick")
    m.render()
    assert game_env.elements["ship-5-bp0-option"].hidden is False
    assert game_env.elements["ship-5-bp1-option"].hidden is True
    assert "Brick" in game_env.elements["ship-5-bp0-option"].innerText
    game_env.elements["ship-5-archetype-select"].value = "bp0"
    game_env.purchase_ship("5")
    assert m.ships["5"].hull["name"] == "Brick"


# --------------------------------------------------------------- chart / UI

def test_chart_has_a_labelled_bar_and_an_average_marker_for_each_stat(game_env):
    m = game_env.module
    html = m.blueprint_chart_html(_hull(hold=5, speed=2, eff=2))
    assert html.count("bp-bar-avg") == 3 and html.count("average hull") == 3
    assert "Hold 5 (+2 vs average)" in html and "Speed 2 (-1 vs average)" in html
    assert m.blueprint_chart_html(_hull()).count("(same as average)") == 3


def test_ui_adjusts_saves_and_lists_a_design(game_env):
    m = _lab(game_env.module)
    el = game_env.elements
    el["lab-toggle-button"].dispatch("click", None)
    assert el["bp-controls"].hidden is False and "Design points left: 0 of 9" in el["bp-status"].innerText
    assert el["bp-hold-up-button"].disabled is True and el["bp-hold-down-button"].disabled is False
    el["bp-hold-down-button"].dispatch("click", None)
    el["bp-speed-up-button"].dispatch("click", None)
    assert el["bp-hold-value"].innerText == "Hold: 2" and el["bp-speed-value"].innerText == "Speed: 4"
    assert "Hold 2" in el["bp-chart"].innerHTML
    el["bp-name-input"].value = "Sprinter"
    el["bp-save-button"].dispatch("click", None)
    assert [d["name"] for d in m.blueprints] == ["Sprinter"]
    assert el["bp-design-0-row"].hidden is False and "Sprinter" in el["bp-design-0-text"].innerText
    assert el["bp-hold-value"].innerText == "Hold: 3"  # the draft went back to average
    el["bp-design-0-delete-button"].dispatch("click", None)
    assert m.blueprints == [] and el["bp-design-0-row"].hidden is True


def test_reset_button_returns_to_average(game_env):
    m = _lab(game_env.module)
    m.adjust_blueprint("hold", -1)
    game_env.elements["bp-reset-button"].dispatch("click", None)
    assert m.blueprint_draft == {"hold": 3, "speed": 3, "eff": 3, "name": ""}


# ------------------------------------------------------------- achievements

def test_designer_and_custom_fleet_achievements(game_env):
    m = _lab(game_env.module)
    assert "hull_designer" not in m.achievement_ids_earned()
    m.save_blueprint("A")
    assert "hull_designer" in m.achievement_ids_earned() and "custom_fleet" not in m.achievement_ids_earned()
    m.purchase_ship("5", "bp0")
    assert "custom_fleet" in m.achievement_ids_earned()


# --------------------------------------------------------------------- saves

def test_nothing_saved_until_used(game_env):
    m = game_env.module
    state = m.get_state()
    assert "blueprints" not in state and all("hull" not in s for s in state["ships"].values())


def test_designs_and_custom_ship_round_trip(game_env):
    m = _lab(game_env.module)
    m.blueprint_draft.update(hold=5, speed=2, eff=2)
    m.save_blueprint("Brick")
    m.purchase_ship("5", "bp0")
    state = json.loads(json.dumps(m.get_state()))
    assert state["ships"]["5"]["hull"]["name"] == "Brick" and state["blueprints"][0]["hold"] == 5
    m.blueprints.clear()
    m.ships["5"].hull = None
    m.ships["5"].archetype = "balanced"
    m.load_state(state)
    assert m.ships["5"].hull == {"hold": 5, "speed": 2, "eff": 2, "name": "Brick"} and len(m.blueprints) == 1


BAD_HULLS = [
    "x", 3, [], None, {},
    {"name": "A", "hold": 7, "speed": 1, "eff": 1},
    {"name": "A", "hold": 0, "speed": 1, "eff": 1},
    {"name": "A", "hold": 5, "speed": 5, "eff": 5},  # over budget
    {"name": "A", "hold": True, "speed": 1, "eff": 1},
    {"name": "A", "hold": 2.5, "speed": 1, "eff": 1},
    {"name": "A", "hold": "2", "speed": 1, "eff": 1},
    {"name": "", "hold": 2, "speed": 2, "eff": 2},
    {"name": "   ", "hold": 2, "speed": 2, "eff": 2},
    {"name": "x" * 99, "hold": 2, "speed": 2, "eff": 2},
    {"name": ["A"], "hold": 2, "speed": 2, "eff": 2},
]


@pytest.mark.parametrize("hull", BAD_HULLS)
def test_tampered_designs_are_dropped(game_env, hull):
    m = game_env.module
    state = json.loads(json.dumps(m._fresh_state))
    state["blueprints"] = [hull]
    assert m.load_state(state) is True and m.blueprints == []


@pytest.mark.parametrize("hull", BAD_HULLS)
def test_a_tampered_ship_hull_falls_back_to_balanced(game_env, hull):
    m = game_env.module
    state = json.loads(json.dumps(m._fresh_state))
    state["ships"]["5"].update(purchased=True, archetype="custom", hull=hull)
    assert m.load_state(state) is True
    assert m.ships["5"].hull is None and m.ships["5"].archetype == "balanced"


def test_custom_without_a_hull_and_a_hull_without_custom_are_both_ignored(game_env):
    m = game_env.module
    state = json.loads(json.dumps(m._fresh_state))
    state["ships"]["5"].update(purchased=True, archetype="custom")
    m.load_state(state)
    assert m.ships["5"].hull is None
    state["ships"]["5"].update(archetype="fast", hull={"name": "A", "hold": 2, "speed": 2, "eff": 2})
    m.load_state(state)
    assert m.ships["5"].hull is None and m.ships["5"].archetype == "fast"


def test_only_four_designs_load(game_env):
    m = game_env.module
    state = json.loads(json.dumps(m._fresh_state))
    state["blueprints"] = [{"name": f"D{i}", "hold": 3, "speed": 3, "eff": 3} for i in range(9)]
    m.load_state(state)
    assert len(m.blueprints) == 4


def test_a_renewal_clears_designs_and_hulls(game_env):
    m = _lab(game_env.module)
    m.save_blueprint("Brick")
    m.purchase_ship("5", "bp0")
    m.endgame_reached = True
    m.found_new_corporation()
    assert m.blueprints == [] and m.ships["5"].hull is None and "custom_fleet" not in [
        a for a in m.achievement_ids_earned() if a not in m.legacy_achievements]


def test_sandbox_round_trip_keeps_real_designs(game_env):
    m = _lab(game_env.module)
    m.save_blueprint("Brick")
    m.purchase_ship("5", "bp0")
    before = json.dumps(m.get_state(), sort_keys=True)
    m.sandbox_enter()
    assert m.blueprints == [] and m.ships["5"].hull is None
    m.sandbox_leave()
    assert json.dumps(m.get_state(), sort_keys=True) == before
