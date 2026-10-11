"""G-20: one custom preset slot shared by Regions B and C."""


def _fund(region, funds):
    region.funds = funds


def test_slot_starts_empty_and_button_is_disabled(game_env):
    m = game_env.module
    assert m.custom_preset is None
    for prefix in "bc":
        button = game_env.elements[f"{prefix}-preset-custom-button"]
        assert button.disabled is True
        assert "empty" in button.innerText
        assert "Empty" in button.title


def test_save_button_needs_something_built(game_env):
    assert game_env.elements["b-preset-save-button"].disabled is True
    game_env.invest_secondary("b", "preserve")
    assert game_env.elements["b-preset-save-button"].disabled is False


def test_save_copies_the_units_the_region_has_built(game_env):
    m = game_env.module
    m.region_b.funds = 1000
    for _ in range(3):
        game_env.invest_secondary("b", "preserve")
    game_env.invest_secondary("b", "monitor")
    game_env.elements["b-preset-save-button"].dispatch("click", None)
    assert m.custom_preset == {"preserve": 3, "monitor": 1}
    button = game_env.elements["c-preset-custom-button"]  # the slot is shared, so Region C sees it too
    assert button.disabled is False
    assert "3" in button.innerText and "1" in button.innerText


def test_saving_an_empty_region_does_nothing(game_env):
    m = game_env.module
    assert m.save_custom_preset(m.region_b) is False
    assert m.custom_preset is None


def test_custom_preset_spends_toward_the_saved_ratio(game_env):
    m = game_env.module
    m.custom_preset = {"preserve": 3, "monitor": 1}
    m.region_c.funds = 400
    game_env.elements["c-preset-custom-button"].dispatch("click", None)
    cap = m.region_c.capacity
    assert cap["output"] == 0
    assert cap["preserve"] > cap["monitor"] >= 1
    assert m.region_c.funds < 25  # it spent what it could afford
    assert m.preset_used_ever is True


def test_custom_preset_is_one_shared_slot_not_per_region(game_env):
    m = game_env.module
    m.region_b.funds = 500
    for _ in range(2):
        game_env.invest_secondary("b", "output")
    game_env.elements["b-preset-save-button"].dispatch("click", None)
    m.region_c.funds = 300
    game_env.elements["c-preset-save-button"].dispatch("click", None)  # nothing built in C yet: no-op
    assert m.custom_preset == {"output": 2}
    game_env.invest_secondary("c", "monitor")
    game_env.elements["c-preset-save-button"].dispatch("click", None)  # now C replaces the slot
    assert m.custom_preset == {"monitor": 1}


def test_tooltip_lists_percentages_and_a_preview(game_env):
    m = game_env.module
    m.custom_preset = {"preserve": 1, "monitor": 1}
    m.region_b.funds = 300
    m.render()
    title = game_env.elements["b-preset-custom-button"].title
    assert "50%" in title and "one-time action" in title
    assert "Right now this would buy" in title


def test_no_preview_in_the_tooltip_in_hard_mode(game_env):
    m = game_env.module
    m.custom_preset = {"preserve": 1}
    assert m.set_hard_mode(True)
    m.render()
    assert "Right now this would buy" not in game_env.elements["b-preset-custom-button"].title


def test_slot_round_trips_through_the_save(game_env):
    m = game_env.module
    m.custom_preset = {"output": 2, "preserve": 5}
    state = m.get_state()
    assert state["custom_preset"] == {"output": 2, "preserve": 5}
    m.custom_preset = None
    assert m.load_state(state)
    assert m.custom_preset == {"output": 2, "preserve": 5}


def test_empty_slot_is_not_written_to_the_save(game_env):
    assert "custom_preset" not in game_env.module.get_state()


def test_loading_clears_a_slot_the_save_does_not_have(game_env):
    m = game_env.module
    m.custom_preset = {"output": 1}
    state = m.get_state()
    del state["custom_preset"]
    m.load_state(state)
    assert m.custom_preset is None


def test_bad_slots_load_as_empty_and_are_named(game_env):
    m = game_env.module
    base = m.get_state()
    for bad in ({"output": 0}, {"output": True}, {"wood": 2}, {"output": 100}, {"output": 1.5}, {}, "x", [1]):
        state = dict(base, custom_preset=bad)
        assert m.load_state(state)
        assert m.custom_preset is None, bad
    state = dict(base, custom_preset={"output": 0})
    m.load_state(state)
    assert "custom preset" in m.load_problems
