"""K-1: Standing Orders (if/then rules chosen from menus)."""

import copy
import json

import minutes
import orders
import sim
import techdebt


def known(*nodes):
    return list(nodes)


def rule_with(**changes):
    rule = orders.fresh_rule(1)
    rule.update(changes)
    return rule


# --- validation -----------------------------------------------------------
def test_default_record_is_not_stored():
    ui = {}
    orders.put(ui, orders.fresh())
    assert orders.KEY not in ui
    assert orders.get(ui) == orders.fresh()


def test_clean_survives_junk():
    assert orders.clean(None) == orders.fresh()
    assert orders.clean("x") == orders.fresh()
    junk = {
        "on": "no", "fired": -4, "rules": [
            None, "x", {"id": True}, {"id": 0}, {"id": 1, "trigger": "nonsense"},
            {"id": 2, "trigger": "idle", "op": 9, "value": [1], "action": {}, "n": 99, "to": "nope", "from": ["x"],
             "repeat": 3, "on": 0, "fires": "many", "blocked": 1},
            {"id": 2, "trigger": "idle"},
        ],
    }
    rec = orders.clean(junk)
    assert rec["on"] is True and rec["fired"] == 0
    assert len(rec["rules"]) == 1
    rule = rec["rules"][0]
    assert rule["id"] == 2 and rule["trigger"] == "idle"
    assert rule["op"] == "above" and rule["value"] == orders.TRIGGERS["idle"]["default"]
    assert rule["action"] == "shift" and rule["n"] == orders.MAX_MOVE
    assert rule["to"] == "foragers" and rule["from"] == orders.NO_SOURCE
    assert rule["repeat"] == "every" and rule["fires"] == 0 and rule["blocked"] is False


def test_clean_caps_rules_and_refuses_nan_and_bool_values():
    rules = [dict(orders.fresh_rule(i + 1)) for i in range(9)]
    assert len(orders.clean({"rules": rules})["rules"]) == orders.MAX_RULES
    rule = orders.fresh_rule(1)
    rule["value"] = float("nan")
    assert orders.clean({"rules": [rule]})["rules"][0]["value"] == orders.TRIGGERS[rule["trigger"]]["default"]
    rule["value"] = True
    assert orders.clean({"rules": [rule]})["rules"][0]["value"] == orders.TRIGGERS[rule["trigger"]]["default"]
    # a value not on the menu falls back to the default
    rule["value"] = 7
    assert orders.clean({"rules": [rule]})["rules"][0]["value"] == orders.TRIGGERS["food_seasons"]["default"]


def test_a_rule_cannot_move_people_from_a_job_to_itself():
    rule = orders.fresh_rule(1)
    rule["from"] = rule["to"] = "gatherers"
    assert orders.clean({"rules": [rule]})["rules"][0]["from"] == orders.NO_SOURCE


# --- what research unlocks ------------------------------------------------
def test_slots_open_with_their_discoveries():
    assert orders.slots([]) == 0
    assert orders.slots(["shared_hearth"]) == 1
    assert orders.slots(["shared_hearth", "kinship_custom", "fire_keeping"]) == 2
    assert orders.slots(orders.SLOT_UNLOCKS) == orders.MAX_RULES
    assert orders.next_slot_unlock(["shared_hearth"]) == "kinship_custom"
    assert orders.next_slot_unlock(orders.SLOT_UNLOCKS) is None


def test_every_unlock_names_a_real_discovery():
    import research
    nodes = {n.node_id for n in research.NODE_LIST}
    for node in orders.SLOT_UNLOCKS:
        assert node in nodes
    for spec in list(orders.TRIGGERS.values()) + list(orders.ACTIONS.values()):
        assert spec["unlock"] is None or spec["unlock"] in nodes
        assert spec["era"] in sim.ERA_ORDER


def test_trigger_and_action_availability_follow_research_and_era():
    assert orders.trigger_available("food_seasons", [], "tribal")
    assert not orders.trigger_available("land_health", [], "tribal")
    assert orders.trigger_available("land_health", ["seasonal_rounds"], "tribal")
    assert not orders.trigger_available("pollution", ["smoke_abatement"], "agrarian")
    assert orders.trigger_available("pollution", ["smoke_abatement"], "industrial")
    assert not orders.action_available("refactor", ["smart_utilities"], "industrial")
    assert orders.action_available("refactor", ["smart_utilities"], "digital")
    assert not orders.trigger_available("bogus", [], "tribal")


def test_add_rule_needs_a_free_slot_and_names_what_opens_one():
    ui = {}
    ok, text = orders.add_rule(ui, [], "tribal")
    assert not ok and "Shared Hearth" in text and orders.KEY not in ui
    ok, _ = orders.add_rule(ui, ["shared_hearth"], "tribal")
    assert ok and len(orders.get(ui)["rules"]) == 1
    ok, text = orders.add_rule(ui, ["shared_hearth"], "tribal")
    assert not ok and "Kinship Custom" in text
    ok, _ = orders.add_rule(ui, ["shared_hearth", "kinship_custom"], "tribal")
    assert ok and [r["id"] for r in orders.get(ui)["rules"]] == [1, 2]


def test_update_rule_refuses_locked_choices_and_parses_menu_strings():
    ui = {}
    orders.add_rule(ui, ["shared_hearth"], "tribal")
    researched = ["shared_hearth"]
    assert orders.update_rule(ui, 1, "trigger", "land_health", researched, "tribal") == (False, "That trigger is not unlocked yet.")
    assert orders.update_rule(ui, 1, "trigger", "idle", researched, "tribal")[0]
    rule = orders.get(ui)["rules"][0]
    assert rule["trigger"] == "idle" and rule["op"] == "above" and rule["value"] == 2
    assert orders.update_rule(ui, 1, "value", "5", researched, "tribal")[0]
    assert orders.update_rule(ui, 1, "value", "6", researched, "tribal")[0] is False
    assert orders.update_rule(ui, 1, "value", "abc", researched, "tribal")[0] is False
    assert orders.update_rule(ui, 1, "op", "sideways", researched, "tribal")[0] is False
    assert orders.update_rule(ui, 1, "n", "9", researched, "tribal")[0] is False
    assert orders.update_rule(ui, 1, "to", "farmers", researched, "tribal")[0] is False
    assert orders.update_rule(ui, 1, "to", "gatherers", researched, "tribal")[0]
    assert orders.update_rule(ui, 1, "from", "gatherers", researched, "tribal")[0] is False
    assert orders.update_rule(ui, 1, "action", "refactor", researched, "tribal")[0] is False
    assert orders.update_rule(ui, 9, "op", "below", researched, "tribal")[0] is False
    assert orders.update_rule(ui, 1, "bogus", "x", researched, "tribal")[0] is False


def test_remove_rule_and_master_switch_roundtrip():
    ui = {}
    orders.add_rule(ui, ["shared_hearth"], "tribal")
    assert orders.remove_rule(ui, 1) and orders.KEY not in ui
    assert orders.remove_rule(ui, 1) is False
    assert orders.set_master(ui, False) is False
    assert ui[orders.KEY]["on"] is False
    assert orders.set_master(ui, True) is True and orders.KEY not in ui


# --- running orders -------------------------------------------------------
def food_rule(**extra):
    base = {"id": 1, "trigger": "food_seasons", "op": "below", "value": 2, "action": "shift", "n": 1,
            "to": "foragers", "from": orders.NO_SOURCE, "repeat": "every", "on": True}
    base.update(extra)
    return base


def test_metrics_read_the_state():
    state = sim.CityState()
    assert orders.food_seasons(state) == state.resources["food"] / (state.population * sim.FOOD_PER_PERSON)
    assert orders.metric("idle", state) == state.idle_workers()
    assert orders.metric("land_health", state) == state.land_health * 100
    assert orders.metric("materials", state) == state.resources["materials"]
    assert orders.metric("score", state, 61.5) == 61.5 and orders.metric("score", state, lambda: 40) == 40
    assert orders.metric("tech_debt", state, None, {techdebt.KEY: {"debt": 0.4}}) == 40.0
    assert orders.metric("nonsense", state) is None


def test_a_matching_order_moves_an_idle_person_and_says_so():
    state = sim.CityState()
    state.population = 8          # 5 assigned, 3 idle
    state.resources["food"] = 4.0
    ui = {orders.KEY: {"rules": [food_rule()]}}
    out = orders.run(ui, state, ["shared_hearth"])
    assert len(out) == 1 and out[0]["acted"] is True
    assert state.allocation["foragers"] == 4 and state.idle_workers() == 2
    assert "food stored is below 2 seasons of eating" in out[0]["text"]
    assert "1 person moved from Idle people to Foragers" in out[0]["text"]
    rec = orders.get(ui)
    assert rec["fired"] == 1 and rec["rules"][0]["fires"] == 1


def test_a_rule_that_does_not_match_does_nothing():
    state = sim.CityState()
    state.resources["food"] = 500.0
    ui = {orders.KEY: {"rules": [food_rule()]}}
    assert orders.run(ui, state, ["shared_hearth"]) == []
    assert state.allocation["foragers"] == 3


def test_orders_beyond_the_open_slots_or_locked_do_nothing():
    state = sim.CityState()
    state.population = 8
    state.resources["food"] = 1.0
    second = food_rule(id=2, to="gatherers")
    ui = {orders.KEY: {"rules": [food_rule(on=False), second]}}
    # slot 1 open, but rule 1 is paused; rule 2 sits in slot 2 which is closed
    assert orders.run(ui, state, ["shared_hearth"]) == []
    assert state.allocation["gatherers"] == 2
    locked = {orders.KEY: {"rules": [food_rule(trigger="land_health", op="below", value=90)]}}
    assert orders.run(locked, state, ["shared_hearth"]) == []


def test_the_master_switch_stops_everything():
    state = sim.CityState()
    state.population = 8
    state.resources["food"] = 1.0
    ui = {orders.KEY: {"on": False, "rules": [food_rule()]}}
    assert orders.run(ui, state, ["shared_hearth"]) == []
    assert state.idle_workers() == 3


def test_once_only_rules_switch_themselves_off():
    state = sim.CityState()
    state.population = 9
    state.resources["food"] = 1.0
    ui = {orders.KEY: {"rules": [food_rule(repeat="once")]}}
    assert len(orders.run(ui, state, ["shared_hearth"])) == 1
    assert orders.get(ui)["rules"][0]["on"] is False
    assert orders.run(ui, state, ["shared_hearth"]) == []
    assert state.allocation["foragers"] == 4


def test_a_blocked_rule_speaks_once_then_stays_quiet_until_it_can_act():
    state = sim.CityState()
    state.population = 5          # 5 people, 5 assigned: nobody idle
    state.resources["food"] = 1.0
    ui = {orders.KEY: {"rules": [food_rule()]}}
    first = orders.run(ui, state, ["shared_hearth"])
    assert len(first) == 1 and first[0]["acted"] is False and "nobody was available" in first[0]["text"]
    assert orders.run(ui, state, ["shared_hearth"]) == []
    state.population = 6          # one is idle now
    again = orders.run(ui, state, ["shared_hearth"])
    assert len(again) == 1 and again[0]["acted"] is True


def test_moving_from_another_job_and_from_the_biggest_group():
    state = sim.CityState()
    ui = {orders.KEY: {"rules": [food_rule(trigger="idle", op="below", value=2, **{"from": "gatherers", "n": 2, "to": "keepers"})]}}
    out = orders.run(ui, state, ["shared_hearth"])
    assert state.allocation["gatherers"] == 0 and state.allocation["keepers"] == 2
    assert out[0]["acted"] and "2 people moved from Gatherers to Keepers" in out[0]["text"]
    state2 = sim.CityState()
    ui2 = {orders.KEY: {"rules": [food_rule(trigger="idle", op="below", value=2, **{"from": orders.LARGEST, "to": "crafters"})]}}
    orders.run(ui2, state2, ["shared_hearth"])
    assert state2.allocation["foragers"] == 2 and state2.allocation["crafters"] == 1


def test_moves_never_exceed_the_people_available():
    state = sim.CityState()
    ui = {orders.KEY: {"rules": [food_rule(trigger="idle", op="below", value=2, **{"from": "gatherers", "n": 3, "to": "keepers"})]}}
    orders.run(ui, state, ["shared_hearth"])
    assert state.allocation["gatherers"] == 0 and state.allocation["keepers"] == 2
    assert state.assigned_workers() == 5 and state.assigned_workers() <= state.population


def test_a_role_from_a_later_era_cannot_be_the_target_yet():
    state = sim.CityState()
    state.population = 8
    state.resources["food"] = 1.0
    ui = {orders.KEY: {"rules": [food_rule(to="farmers")]}}
    out = orders.run(ui, state, ["shared_hearth"])
    assert out and out[0]["acted"] is False and "not a job yet" in out[0]["text"]
    assert state.allocation["farmers"] == 0


def test_digital_actions_schedule_a_refactor_and_stop_quick_builds():
    state = sim.CityState(era="digital")
    state.population = 40
    ui = {techdebt.KEY: {"debt": 0.7, "quick": True}}
    rules = [
        {"id": 1, "trigger": "tech_debt", "op": "above", "value": 50, "action": "refactor"},
        {"id": 2, "trigger": "tech_debt", "op": "above", "value": 50, "action": "quick_off"},
    ]
    ui[orders.KEY] = {"rules": rules}
    known_nodes = ["shared_hearth", "kinship_custom", "smart_utilities"]
    out = orders.run(ui, state, known_nodes)
    assert [o["acted"] for o in out] == [True, True]
    record = techdebt.get(ui)
    assert record["refactor"] is True and record["quick"] is False
    # already scheduled / already off: blocked, once
    again = orders.run(ui, state, known_nodes)
    assert all(o["acted"] is False for o in again) and len(again) == 2
    assert orders.run(ui, state, known_nodes) == []


def test_a_notice_order_only_logs():
    state = sim.CityState()
    state.resources["food"] = 1.0
    ui = {orders.KEY: {"rules": [food_rule(action="notice")]}}
    before = copy.deepcopy(state.allocation)
    out = orders.run(ui, state, ["shared_hearth"])
    assert out[0]["acted"] and state.allocation == before


def test_describe_reads_as_a_sentence():
    text = orders.describe(orders.clean_rule(food_rule(n=2)))
    assert text.startswith("If food stored is below 2 seasons of eating, then move up to 2 people from Idle people to Foragers")
    assert "switched off" in orders.describe(orders.clean_rule(food_rule(on=False)))


# --- the Council Minutes --------------------------------------------------
def test_minutes_accept_the_order_kind_and_keep_decisions_over_chatter():
    ui = {}
    assert minutes.record(ui, "order", "food is low, so 1 person moved.", "tribal", 3)
    assert minutes.entries(ui)[0]["text"].startswith("Standing order: ")
    ui = {}
    minutes.record(ui, "research", "Fire-Keeping", "tribal", 1)
    for i in range(minutes.MAX_ENTRIES + 20):
        minutes.record(ui, "order", f"rule fired {i}", "tribal", i + 2)
    entries = minutes.entries(ui)
    assert len(entries) == minutes.MAX_ENTRIES
    assert entries[0]["kind"] == "research"
    assert entries[-1]["text"].endswith(f"rule fired {minutes.MAX_ENTRIES + 19}")


# --- the game -------------------------------------------------------------
def test_orders_fire_after_a_season_and_are_minuted(game_env):
    module = game_env.module
    module.tree.researched.append("shared_hearth")
    module.state.population = 8
    module.state.resources["food"] = 3.0
    module.campaign.ui[orders.KEY] = {"rules": [food_rule()]}
    game_env.advance_season()
    entries = [e for e in minutes.entries(module.campaign.ui) if e["kind"] == "order"]
    assert entries and "moved from Idle people to Foragers" in entries[0]["text"]
    assert module.state.allocation["foragers"] >= 4


def test_orders_do_not_run_during_a_look_back(game_env):
    module = game_env.module
    module.tree.researched.append("shared_hearth")
    module.state.resources["food"] = 1.0
    module.campaign.ui[orders.KEY] = {"rules": [food_rule()]}
    module.campaign.revisiting = "tribal"
    module._run_standing_orders = module._run_standing_orders  # keep the reference honest
    assert module.orders_set(1, "op", "above") is False
    assert module.on_orders_add() is None
    assert orders.get(module.campaign.ui)["rules"][0]["op"] == "below"
    module.campaign.revisiting = None


def test_the_panel_builds_menus_and_applies_choices(game_env):
    module = game_env.module
    elements = game_env.elements
    module.tree.researched.append("shared_hearth")
    module.on_toggle_orders()
    assert elements["orders-panel"].hidden is False
    assert "No orders yet" in elements["orders-list"].children[0].innerText
    elements["orders-add-button"].dispatch("click", None)
    assert len(orders.get(module.campaign.ui)["rules"]) == 1
    assert elements["orders-add-button"].disabled is True
    trigger = elements["orders-1-trigger"]
    land = [o for o in trigger.children if o.value == "land_health"][0]
    assert land.disabled is True and "Seasonal Rounds" in land.innerText
    elements["orders-1-value"].value = "3"
    elements["orders-1-value"].dispatch("change", None)
    assert orders.get(module.campaign.ui)["rules"][0]["value"] == 3
    elements["orders-1-toggle"].dispatch("click", None)
    assert orders.get(module.campaign.ui)["rules"][0]["on"] is False
    elements["orders-master-button"].dispatch("click", None)
    assert orders.get(module.campaign.ui)["on"] is False
    elements["orders-1-remove"].dispatch("click", None)
    assert orders.get(module.campaign.ui)["rules"] == []


def test_a_slotless_game_explains_what_opens_the_first_slot(game_env):
    module = game_env.module
    elements = game_env.elements
    module.on_toggle_orders()
    assert "Shared Hearth" in elements["orders-summary"].innerText
    assert elements["orders-add-button"].disabled is True


def test_orders_survive_a_save_roundtrip_and_old_saves_load_without_them(game_env):
    module = game_env.module
    module.tree.researched.append("shared_hearth")
    module.campaign.ui[orders.KEY] = {"on": True, "fired": 2, "rules": [food_rule(fires=2)]}
    data = json.loads(json.dumps(module.get_state()))
    assert data["ui"][orders.KEY]["rules"][0]["fires"] == 2
    module.campaign.ui.pop(orders.KEY)
    module.load_state(data)
    assert orders.get(module.campaign.ui)["fired"] == 2
    data["ui"].pop(orders.KEY)
    module.load_state(data)
    assert orders.get(module.campaign.ui) == orders.fresh()
    data["ui"][orders.KEY] = "garbage"
    module.load_state(data)
    assert orders.get(module.campaign.ui) == orders.fresh()


def test_founding_a_new_settlement_drops_the_orders(game_env):
    import founding
    module = game_env.module
    module.campaign.ui[orders.KEY] = {"rules": [food_rule()]}
    assert orders.KEY not in founding.CARRY_KEYS
    assert founding.found_new(module.campaign, module.chronicle, carry=module.campaign.ui)
    assert orders.KEY not in module.campaign.ui
