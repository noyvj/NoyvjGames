"""Edge-case tests for citizens.py: limits, clamping, and rejected inputs."""

import citizens
import sim


def test_clean_name_rejects_invalid_types_and_names():
    assert citizens.clean_name("") == ""
    assert citizens.clean_name(123) == ""
    assert citizens.clean_name(["Maren"]) == ""
    assert citizens.clean_name("Maren Hearthwick") == "Maren Hearthwick"
    assert citizens.clean_name("Unknown Hearthwick") == ""
    assert citizens.clean_name("Maren Unknown") == ""


def test_clean_spot_clamps_and_validates_fields():
    valid = {"name": "A B", "line": "x", "season": 3, "event": "calm"}
    assert citizens.clean_spot(valid) is not None
    assert citizens.clean_spot({"name": "A" * 100, "line": "x", "season": 3, "event": "calm"})["name"] == "A" * 60
    assert citizens.clean_spot({"name": "A B", "line": "x", "season": 10**7 + 1, "event": "calm"})["season"] == 10**7
    assert citizens.clean_spot({"name": "A B", "line": "x", "season": 0, "event": "calm"}) is None
    assert citizens.clean_spot({"name": "A B", "line": "x", "season": True, "event": "calm"}) is None
    assert citizens.clean_spot({"name": "A B", "line": "x", "season": 3, "event": "missing"}) is None


def test_clean_limits_roster_and_spots():
    roster = [
        {"name": f"{citizens.FIRST_NAMES[i % len(citizens.FIRST_NAMES)]} {citizens.LAST_NAMES[i % len(citizens.LAST_NAMES)]}", "born": sim.ERA_ORDER[i]}
        for i in range(len(sim.ERA_ORDER))
    ]
    raw = {"seed": 100, "roster": roster * 2, "spots": [{"name": "X", "line": "Y", "season": i + 1, "event": "calm"} for i in range(10)]}
    out = citizens.clean(raw)
    assert len(out["roster"]) == len(sim.ERA_ORDER)
    assert len(out["spots"]) == citizens.MAX_SPOTS


def test_ensure_roster_handles_missing_seed_and_invalid_era():
    ui = {"citizens": citizens.default()}
    assert citizens.ensure_roster(ui, "nonexistent") == []
    ui["citizens"]["seed"] = 0
    added = citizens.ensure_roster(ui, sim.ERA_ORDER[0])
    assert len(added) == 1
    assert ui["citizens"]["seed"] > 0


def test_make_spotlight_refuses_off_or_invalid_inputs():
    ui = {"citizens": citizens.default()}
    ui["citizens"]["off"] = True
    assert citizens.make_spotlight(ui, sim.ERA_ORDER[0], 1, {}, []) is None

    ui["citizens"]["off"] = False
    assert citizens.make_spotlight(ui, "bad_era", 1, {}, {}) is None
    assert citizens.make_spotlight(ui, sim.ERA_ORDER[0], True, {}, []) is None
    assert citizens.make_spotlight(ui, sim.ERA_ORDER[0], 0, {}, []) is None

    ui["citizens"]["seed"] = 42
    result = citizens.make_spotlight(ui, sim.ERA_ORDER[0], 1, {"deaths": 0}, [])
    assert result is not None
    assert result["season"] == 1
