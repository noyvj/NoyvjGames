"""Edge-case tests for orders.py."""

import orders
import sim


def test_clean_rule_clamps_n_and_rejects_junk():
    # Junk inputs return None
    assert orders.clean_rule(None) is None
    assert orders.clean_rule("x") is None
    assert orders.clean_rule({"id": True}) is None
    assert orders.clean_rule({"id": 0}) is None
    assert orders.clean_rule({"id": -1}) is None

    # Invalid trigger returns None (junk)
    assert orders.clean_rule({"id": 5, "trigger": "bogus"}) is None

    # n clamped to [1, MAX_MOVE]
    base = {"id": 1, "trigger": "idle"}
    assert orders.clean_rule({**base, "n": -10})["n"] == 1
    assert orders.clean_rule({**base, "n": 0})["n"] == 1
    assert orders.clean_rule({**base, "n": 100})["n"] == orders.MAX_MOVE

    # Invalid op/action falls back to defaults
    rule = orders.clean_rule({**base, "op": "sideways", "action": "teleport"})
    assert rule["op"] == "above"
    assert rule["action"] == "shift"


def test_clean_enforces_max_rules_and_ignores_duplicates():
    # Non-dict raw returns fresh record
    assert orders.clean(None) == orders.fresh()
    assert orders.clean([]) == orders.fresh()

    # Exactly MAX_RULES accepted
    rules = [orders.fresh_rule(i + 1) for i in range(orders.MAX_RULES)]
    rec = orders.clean({"rules": rules})
    assert len(rec["rules"]) == orders.MAX_RULES

    # Duplicates are skipped, extra items dropped
    dupes = [orders.fresh_rule(1), orders.fresh_rule(1), orders.fresh_rule(3)]
    rec = orders.clean({"rules": dupes})
    assert len(rec["rules"]) == 2


def test_update_rule_rejects_out_of_bounds_n_and_invalid_fields():
    ui = {}
    orders.add_rule(ui, ["shared_hearth"], "tribal")
    researched = ["shared_hearth"]

    # Invalid field name rejected
    ok, _ = orders.update_rule(ui, 1, "bogus_field", "x", researched, "tribal")
    assert not ok

    # n out of [1, MAX_MOVE] rejected
    ok, _ = orders.update_rule(ui, 1, "n", "0", researched, "tribal")
    assert not ok
    ok, _ = orders.update_rule(ui, 1, "n", str(orders.MAX_MOVE + 1), researched, "tribal")
    assert not ok

    # Boundary values accepted
    ok, _ = orders.update_rule(ui, 1, "n", "1", researched, "tribal")
    assert ok
    ok, _ = orders.update_rule(ui, 1, "n", str(orders.MAX_MOVE), researched, "tribal")
    assert ok


def test_metric_handles_zero_population_and_negative_land_health():
    state = sim.CityState()

    # Zero population division in food_seasons uses max(1.0, ...) to avoid div-by-zero
    state.population = 0
    state.resources["food"] = 0
    assert orders.food_seasons(state) == 0.0

    # Negative land health passes through
    state.land_health = -0.5
    assert orders.metric("land_health", state) == -50.0

    # Zero idle workers returns 0.0
    state.allocation = {"foragers": 5}
    assert orders.metric("idle", state) == 0.0


def test_describe_formats_default_and_extreme_values():
    rule = orders.fresh_rule(1, "food_seasons")

    # Default values format correctly
    assert "below 2 seasons of eating" in orders.describe(rule)

    # Extreme value on the menu
    rule["value"] = 6
    assert "below 6 seasons of eating" in orders.describe(rule)

    # Switched off state appends suffix
    rule["on"] = False
    assert "(switched off)" in orders.describe(rule)


def test_add_rule_respects_empty_research_and_full_slots():
    ui = {}

    # No research -> no slots open
    ok, msg = orders.add_rule(ui, [], "tribal")
    assert not ok and "No free slot" in msg

    # One slot opens with shared_hearth
    ok, _ = orders.add_rule(ui, ["shared_hearth"], "tribal")
    assert ok

    # Fill remaining slots up to MAX_RULES
    researched = ["shared_hearth"]
    for node in orders.SLOT_UNLOCKS[1:]:
        if len(orders.get(ui)["rules"]) < orders.MAX_RULES:
            researched.append(node)
            orders.add_rule(ui, researched, "tribal")

    # Now full -> rejected
    ok, msg = orders.add_rule(ui, researched, "tribal")
    assert not ok and "Every slot is in use" in msg
