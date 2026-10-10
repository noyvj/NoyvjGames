"""Round-7 pass: number format, unit labels and funds-delta arrows (C-6)."""
from .test_career import _play


def _change(game_env, element_id, value):
    el = game_env.elements[element_id]
    el.value = value

    class _E:
        target = el

    el.dispatch("change", _E())


def test_defaults_read_exactly_as_before(game_env):
    game_env.module.render()
    assert game_env.elements["funds-display"].innerText == "Funds: 500"
    assert game_env.elements["capacity-display"].innerText == "Capacity: 0"
    assert game_env.elements["demand-display"].innerText.startswith("Demand: 100 ")
    assert "MW" not in game_env.elements["demand-display"].innerText


def test_format_amount_full_and_compact(game_env):
    g = game_env.module
    assert g.format_amount(1234.6) == "1235" and g.format_amount(-40) == "-40"
    g.prefs["number_format"] = "compact"
    assert g.format_amount(999) == "999" and g.format_amount(1000) == "1k" and g.format_amount(1250) == "1.2k"
    assert g.format_amount(15400) == "15.4k" and g.format_amount(2_000_000) == "2M" and g.format_amount(3_456_789_012) == "3.5B"
    assert g.format_amount(-2500) == "-2.5k"


def test_compact_mode_changes_the_headline_numbers(game_env):
    g = game_env.module
    game_env.state.funds = 12345
    game_env.state.emissions = 2100.0
    game_env.state.plant_counts["nuclear"] = 12  # 1200 capacity
    _change(game_env, "pref-number-format", "compact")
    assert g.prefs["number_format"] == "compact"
    assert game_env.elements["funds-display"].innerText == "Funds: 12.3k"
    assert game_env.elements["capacity-display"].innerText == "Capacity: 1.2k"
    assert game_env.elements["emissions-display"].innerText == "Emissions: 2.1k"
    _change(game_env, "pref-number-format", "full")
    assert game_env.elements["funds-display"].innerText == "Funds: 12345"


def test_mw_labels_demand_and_capacity_only(game_env):
    game_env.state.plant_counts["coal"] = 2
    _change(game_env, "pref-unit", "mw")
    assert game_env.elements["capacity-display"].innerText == "Capacity: 40 MW"
    assert "Demand: 100 MW" in game_env.elements["demand-display"].innerText
    assert "MW" not in game_env.elements["funds-display"].innerText
    assert game_env.elements["pref-unit"].value == "mw"


def test_a_bad_select_value_is_ignored(game_env):
    _change(game_env, "pref-unit", "parsecs")
    assert game_env.module.prefs["unit"] == "units"


def test_funds_delta_is_empty_before_a_round(game_env):
    game_env.module.render()
    assert game_env.elements["funds-delta-display"].hidden is True
    assert game_env.elements["funds-delta-display"].innerText == ""


def test_funds_delta_uses_arrow_and_words(game_env):
    g = game_env.module
    game_env.state.plant_counts["coal"] = 5
    _play(game_env, 1)
    g.render()
    el = game_env.elements["funds-delta-display"]
    assert el.hidden is False
    assert el.innerText.startswith("▲ Funds up ") and el.innerText.endswith(" last round")
    assert "funds-delta--up" in el.className
    game_env.state.last_round_recap["net"] = -35.2
    g.render()
    assert game_env.elements["funds-delta-display"].innerText == "▼ Funds down 35 last round"
    assert "funds-delta--down" in game_env.elements["funds-delta-display"].className
    game_env.state.last_round_recap["net"] = 0.2
    g.render()
    assert game_env.elements["funds-delta-display"].innerText == "◆ Funds unchanged last round"


def test_funds_delta_follows_the_compact_setting(game_env):
    g = game_env.module
    game_env.state.plant_counts["nuclear"] = 40
    game_env.state.demand = 5000
    _play(game_env, 1)
    g.prefs["number_format"] = "compact"
    g.render()
    assert "k last round" in game_env.elements["funds-delta-display"].innerText


def test_number_choices_never_reach_the_save(game_env):
    g = game_env.module
    before = g.get_state()
    g.prefs["number_format"] = "compact"
    g.prefs["unit"] = "mw"
    g.render()
    assert g.get_state() == before
