"""Core logic + save-widget contract + DOM-wiring tests for the Warframe
Build Resource Tracker, following its 2026-09-20 rearchitect from a Flask
app into Python-via-Pyodide (see planning/TODO2.md's "X. Warframe Build
Tracker" section)."""


def _find_row(tbody, attr, value):
    for child in tbody.children:
        if child.attributes.get(attr) == value:
            return child
    raise AssertionError(f"no row with {attr}={value!r} in {len(tbody.children)} rows")


def _reset_to_known_state(module, parts=None, inventory=None):
    """Tests need a deterministic starting point, not the real personal
    migration data game.py boots with. Every part defaults to fully owned
    (owned == target) so it contributes nothing to the resource-need
    calculation -- only parts explicitly passed via `parts=` are made
    incomplete, so resource-aggregation tests aren't polluted by the
    other 32 parts' own requirements."""
    module.state["parts"] = {
        name: {"target": qty, "owned": qty} for name, qty in module.DEFAULT_PARTS
    }
    module.state["inventory"] = {}
    if parts:
        for name, info in parts.items():
            module.state["parts"][name].update(info)
    if inventory:
        for name, info in inventory.items():
            module.state["inventory"][name] = dict(info)


# --- Pure logic -------------------------------------------------------


def test_flatten_recipe_direct_resources(game_env):
    module = game_env.module
    flattened = module.flatten_recipe("Raplak Prism", 2)
    # Raplak Prism: Iradite 40, Murkray Liver 2, Tear Azurite 10, Esher Devar 10
    assert flattened["Iradite"] == 80
    assert flattened["Murkray Liver"] == 4
    assert flattened["Tear Azurite"] == 20
    assert flattened["Esher Devar"] == 20


def test_flatten_recipe_unknown_item_returns_itself(game_env):
    module = game_env.module
    flattened = module.flatten_recipe("Some Raw Ore", 5)
    assert flattened == {"Some Raw Ore": 5}


def test_has_enough_for_one_true_when_built_plus_raw_covers(game_env):
    module = game_env.module
    inventory = {"Iradite": {"built": 10, "raw": 30}}
    assert module.has_enough_for_one({"Iradite": 40}, inventory) is True


def test_has_enough_for_one_false_when_short(game_env):
    module = game_env.module
    inventory = {"Iradite": {"built": 10, "raw": 20}}
    assert module.has_enough_for_one({"Iradite": 40}, inventory) is False


def test_has_enough_for_one_ignores_credits(game_env):
    module = game_env.module
    # No Credits entry in inventory at all -- shouldn't matter.
    assert module.has_enough_for_one({"Credits": 5000}, {}) is True


def test_has_enough_for_one_false_for_empty_ingredients(game_env):
    module = game_env.module
    assert module.has_enough_for_one({}, {}) is False


def test_resource_usage_lists_every_part_that_needs_it(game_env):
    module = game_env.module
    usage = module.resource_usage("Pyrotic Alloy")
    names = {u["name"] for u in usage}
    # Several zaw strikes need Pyrotic Alloy per MANUFACTURING_RECIPES.
    assert "Balla Strike" in names
    assert "Ooltha Strike" in names
    for u in usage:
        assert u["qty"] > 0


# --- calculate() --------------------------------------------------------


def test_calculate_component_status_reflects_target_and_owned(game_env):
    module = game_env.module
    _reset_to_known_state(module, parts={"Raplak Prism": {"target": 3, "owned": 1}})

    components, _resources = module.calculate()
    raplak = next(c for c in components if c["name"] == "Raplak Prism")
    assert raplak["target"] == 3
    assert raplak["owned"] == 1
    assert raplak["remaining"] == 2
    assert raplak["complete"] is False


def test_calculate_component_owned_clamped_to_target(game_env):
    module = game_env.module
    _reset_to_known_state(module, parts={"Raplak Prism": {"target": 1, "owned": 5}})

    components, _resources = module.calculate()
    raplak = next(c for c in components if c["name"] == "Raplak Prism")
    assert raplak["owned"] == 1
    assert raplak["remaining"] == 0
    assert raplak["complete"] is True


def test_calculate_can_build_true_when_resources_sufficient(game_env):
    module = game_env.module
    _reset_to_known_state(
        module,
        parts={"Raplak Prism": {"target": 1, "owned": 0}},
        inventory={
            "Iradite": {"built": 40, "raw": 0},
            "Murkray Liver": {"built": 2, "raw": 0},
            "Tear Azurite": {"built": 10, "raw": 0},
            "Esher Devar": {"built": 10, "raw": 0},
        },
    )
    components, _resources = module.calculate()
    raplak = next(c for c in components if c["name"] == "Raplak Prism")
    assert raplak["can_build"] is True


def test_calculate_can_build_false_when_already_complete(game_env):
    module = game_env.module
    # Fully stocked AND already at target -- can_build requires remaining > 0.
    _reset_to_known_state(
        module,
        parts={"Raplak Prism": {"target": 1, "owned": 1}},
        inventory={
            "Iradite": {"built": 40, "raw": 0},
            "Murkray Liver": {"built": 2, "raw": 0},
            "Tear Azurite": {"built": 10, "raw": 0},
            "Esher Devar": {"built": 10, "raw": 0},
        },
    )
    components, _resources = module.calculate()
    raplak = next(c for c in components if c["name"] == "Raplak Prism")
    assert raplak["can_build"] is False
    assert raplak["complete"] is True


def test_calculate_resource_rows_aggregate_across_parts(game_env):
    module = game_env.module
    # Both Raplak Prism and Rahn Prism need Iradite -- needed should sum.
    _reset_to_known_state(
        module,
        parts={
            "Raplak Prism": {"target": 1, "owned": 0},  # needs 40 Iradite
            "Rahn Prism": {"target": 1, "owned": 0},  # needs 50 Iradite
        },
    )
    _, resources = module.calculate()
    iradite = next(r for r in resources if r["name"] == "Iradite")
    assert iradite["needed"] == 90


def test_calculate_resource_short_amounts(game_env):
    module = game_env.module
    _reset_to_known_state(
        module,
        parts={"Raplak Prism": {"target": 1, "owned": 0}},
        inventory={"Iradite": {"built": 15, "raw": 5}},
    )
    _, resources = module.calculate()
    iradite = next(r for r in resources if r["name"] == "Iradite")
    assert iradite["needed"] == 40
    assert iradite["built_have"] == 15
    assert iradite["built_short"] == 25
    assert iradite["complete"] is False


def test_calculate_resource_complete_when_built_covers_needed(game_env):
    module = game_env.module
    _reset_to_known_state(
        module,
        parts={"Raplak Prism": {"target": 1, "owned": 0}},
        inventory={"Iradite": {"built": 40, "raw": 0}},
    )
    _, resources = module.calculate()
    iradite = next(r for r in resources if r["name"] == "Iradite")
    assert iradite["complete"] is True


def test_calculate_drops_completed_parts_from_resource_need(game_env):
    module = game_env.module
    # A part with remaining==0 shouldn't contribute to raw_need at all.
    _reset_to_known_state(module, parts={"Raplak Prism": {"target": 1, "owned": 1}})
    _, resources = module.calculate()
    assert not any(r["name"] == "Iradite" for r in resources)


def test_calculate_never_lists_credits_as_a_resource_row(game_env):
    module = game_env.module
    _reset_to_known_state(module, parts={"Plague Keewar Strike": {"target": 1, "owned": 0}})
    _, resources = module.calculate()
    assert not any(r["name"] == "Credits" for r in resources)


# --- get_state()/load_state() save-widget contract -----------------------


def test_get_state_returns_deep_copy(game_env):
    module = game_env.module
    _reset_to_known_state(module, parts={"Raplak Prism": {"target": 1, "owned": 1}})
    snapshot = module.get_state()
    snapshot["parts"]["Raplak Prism"]["owned"] = 999
    assert module.state["parts"]["Raplak Prism"]["owned"] == 1


def test_get_state_load_state_roundtrip(game_env):
    module = game_env.module
    _reset_to_known_state(
        module,
        parts={"Raplak Prism": {"target": 2, "owned": 1}},
        inventory={"Iradite": {"built": 5, "raw": 3}},
    )
    saved = module.get_state()

    _reset_to_known_state(module)  # simulate a totally different session
    module.load_state(saved)

    assert module.state["parts"]["Raplak Prism"] == {"target": 2, "owned": 1}
    assert module.state["inventory"]["Iradite"] == {"built": 5, "raw": 3}


def test_load_state_merges_missing_part_keys_without_wiping_others(game_env):
    module = game_env.module
    _reset_to_known_state(
        module,
        parts={
            "Raplak Prism": {"target": 1, "owned": 1},
            "Shwaak Prism": {"target": 1, "owned": 1},
        },
    )
    # A save that only mentions one part shouldn't reset the other back to
    # its DEFAULT_PARTS value -- same defensive-merge shape as every other
    # game's load_state() in this hub.
    module.load_state({"parts": {"Raplak Prism": {"target": 1, "owned": 0}}})

    assert module.state["parts"]["Raplak Prism"]["owned"] == 0
    assert module.state["parts"]["Shwaak Prism"]["owned"] == 1


def test_load_state_with_empty_dict_does_not_crash(game_env):
    module = game_env.module
    _reset_to_known_state(module, parts={"Raplak Prism": {"target": 1, "owned": 1}})
    module.load_state({})
    # Nothing in the (empty) save overrides anything -- live state stands.
    assert module.state["parts"]["Raplak Prism"]["owned"] == 1


def test_load_state_ignores_unknown_resource_gracefully(game_env):
    module = game_env.module
    _reset_to_known_state(module)
    module.load_state({"inventory": {"Totally Made Up Resource": {"raw": 3, "built": 0}}})
    assert module.state["inventory"]["Totally Made Up Resource"] == {"raw": 3, "built": 0}


def test_load_state_calls_render(game_env):
    module = game_env.module
    _reset_to_known_state(module, parts={"Raplak Prism": {"target": 1, "owned": 1}})
    module.load_state({})
    # render() should have populated the progress readout from live state.
    assert "complete" in game_env.elements["component-progress"].textContent


# --- render() / DOM wiring ----------------------------------------------


def test_render_builds_one_row_per_part_plus_category_headers(game_env):
    module = game_env.module
    _reset_to_known_state(module)
    module.render()

    tbody = game_env.elements["components-body"]
    part_rows = [c for c in tbody.children if "data-part" in c.attributes]
    category_rows = [c for c in tbody.children if c.className == "category-row"]

    assert len(part_rows) == len(module.DEFAULT_PARTS)
    assert len(category_rows) == 3  # amp, zaw, kitgun


def test_render_updates_progress_readout(game_env):
    module = game_env.module
    # Every part incomplete (owned 0) except one, which is complete.
    module.state["parts"] = {name: {"target": qty, "owned": 0} for name, qty in module.DEFAULT_PARTS}
    module.state["inventory"] = {}
    complete_name, complete_qty = module.DEFAULT_PARTS[0]
    module.state["parts"][complete_name] = {"target": complete_qty, "owned": complete_qty}
    module.render()

    total = len(module.DEFAULT_PARTS)
    assert game_env.elements["component-progress"].textContent == f"1 / {total} complete"


def test_render_resource_rows_match_calculate_output(game_env):
    module = game_env.module
    _reset_to_known_state(module, parts={"Raplak Prism": {"target": 1, "owned": 0}})
    module.render()

    _components, resources = module.calculate()
    tbody = game_env.elements["resources-body"]
    resource_rows = [c for c in tbody.children if "data-resource" in c.attributes]
    assert len(resource_rows) == len(resources)


def test_render_destroys_previous_render_proxies(game_env):
    module = game_env.module
    _reset_to_known_state(module, parts={"Raplak Prism": {"target": 1, "owned": 0}})
    module.render()
    first_render_proxies = list(module._active_proxies)
    assert first_render_proxies  # sanity: at least one proxy created

    module.render()
    for proxy in first_render_proxies:
        assert proxy.destroyed is True


# --- Interaction handlers -------------------------------------------------


def test_part_change_handler_updates_state_and_clamps_owned(game_env):
    module = game_env.module
    _reset_to_known_state(module, parts={"Raplak Prism": {"target": 1, "owned": 0}})
    module.render()

    row = _find_row(game_env.elements["components-body"], "data-part", "Raplak Prism")
    target_input, owned_input = row.children[1].children[0], row.children[2].children[0]

    target_input.value = "5"
    owned_input.value = "9"  # deliberately over target -- should clamp to 5
    target_input.dispatch("change", None)

    assert module.state["parts"]["Raplak Prism"]["target"] == 5
    assert module.state["parts"]["Raplak Prism"]["owned"] == 5


def test_resource_change_handler_updates_inventory(game_env):
    module = game_env.module
    _reset_to_known_state(module, parts={"Raplak Prism": {"target": 1, "owned": 0}})
    module.render()

    row = _find_row(game_env.elements["resources-body"], "data-resource", "Iradite")
    built_input, raw_input = row.children[2].children[0], row.children[3].children[0]

    built_input.value = "12"
    raw_input.value = "8"
    built_input.dispatch("change", None)

    assert module.state["inventory"]["Iradite"] == {"raw": 8, "built": 12}


def test_build_button_succeeds_when_resources_sufficient(game_env):
    module = game_env.module
    _reset_to_known_state(
        module,
        parts={"Raplak Prism": {"target": 1, "owned": 0}},
        inventory={
            "Iradite": {"built": 40, "raw": 0},
            "Murkray Liver": {"built": 2, "raw": 0},
            "Tear Azurite": {"built": 10, "raw": 0},
            "Esher Devar": {"built": 10, "raw": 0},
        },
    )
    module.render()

    row = _find_row(game_env.elements["components-body"], "data-part", "Raplak Prism")
    build_button = row.children[5].children[0]
    assert build_button.disabled is False

    build_button.dispatch("click", None)

    assert module.state["parts"]["Raplak Prism"]["owned"] == 1
    assert module.state["inventory"]["Iradite"]["built"] == 0
    assert "Built Raplak Prism" in game_env.elements["status-message"].textContent


def test_build_button_consumes_built_stock_before_raw(game_env):
    module = game_env.module
    _reset_to_known_state(
        module,
        parts={"Raplak Prism": {"target": 1, "owned": 0}},
        inventory={
            "Iradite": {"built": 10, "raw": 30},  # 40 needed total
            "Murkray Liver": {"built": 2, "raw": 0},
            "Tear Azurite": {"built": 10, "raw": 0},
            "Esher Devar": {"built": 10, "raw": 0},
        },
    )
    module.render()
    row = _find_row(game_env.elements["components-body"], "data-part", "Raplak Prism")
    row.children[5].children[0].dispatch("click", None)

    iradite = module.state["inventory"]["Iradite"]
    assert iradite["built"] == 0
    assert iradite["raw"] == 0  # 10 built + 30 raw exactly covers 40 needed


def test_build_button_fails_gracefully_when_resources_insufficient(game_env):
    module = game_env.module
    _reset_to_known_state(module, parts={"Raplak Prism": {"target": 1, "owned": 0}})
    module.render()

    row = _find_row(game_env.elements["components-body"], "data-part", "Raplak Prism")
    build_button = row.children[5].children[0]
    assert build_button.disabled is True

    # Directly dispatching anyway (e.g. a stale disabled state in a second
    # tab) should still be re-checked server-side, not trusted blindly.
    build_button.dispatch("click", None)

    assert module.state["parts"]["Raplak Prism"]["owned"] == 0
    assert "Can't build" in game_env.elements["status-message"].textContent


def test_reset_confirmed_clears_all_state(game_env):
    module = game_env.module
    _reset_to_known_state(
        module,
        parts={"Raplak Prism": {"target": 1, "owned": 1}},
        inventory={"Iradite": {"built": 40, "raw": 0}},
    )
    game_env.confirm.next_result = True

    game_env.reset()

    assert module.state["parts"]["Raplak Prism"]["owned"] == 0
    assert module.state["inventory"] == {}
    assert "reset" in game_env.elements["status-message"].textContent.lower()


def test_reset_cancelled_leaves_state_untouched(game_env):
    module = game_env.module
    _reset_to_known_state(module, parts={"Raplak Prism": {"target": 1, "owned": 1}})
    game_env.confirm.next_result = False

    game_env.reset()

    assert module.state["parts"]["Raplak Prism"]["owned"] == 1
