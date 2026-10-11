"""G-23: an optional confirmation for big one-click spends (presets, the emergency rescue)."""

import sys
import types

from .fakes import FakeStorage


class FakeDialog:
    def __init__(self):
        self.asked = []

    def ask(self, **kwargs):
        self.asked.append(kwargs)


def _install_dialog():
    dialog = FakeDialog()
    sys.modules["js"].window = types.SimpleNamespace(ConfirmDialog=dialog)
    return dialog


def test_default_is_never_and_big_spends_go_straight_through(game_env):
    m = game_env.module
    dialog = _install_dialog()
    assert m.confirm_threshold == 0
    game_env.apply_preset("b", "growth")
    assert dialog.asked == []
    assert m.region_b.capacity["output"] > 0


def test_preset_over_the_threshold_asks_first_and_waits(game_env):
    m = game_env.module
    dialog = _install_dialog()
    m.set_confirm_threshold(100)
    game_env.apply_preset("b", "growth")
    assert len(dialog.asked) == 1
    ask = dialog.asked[0]
    assert "300 funds" in ask["message"] and "Region B" in ask["message"]
    assert ask["allowSkip"] is False
    assert m.region_b.capacity["output"] == 0  # nothing bought yet
    ask["onConfirm"]()
    assert m.region_b.capacity["output"] == 15  # 300 / 20
    assert m.region_b.funds == 0


def test_a_spend_at_or_under_the_threshold_is_not_asked(game_env):
    m = game_env.module
    dialog = _install_dialog()
    m.set_confirm_threshold(250)
    m.region_b.funds = 250
    game_env.apply_preset("b", "growth")
    assert dialog.asked == []
    assert m.region_b.capacity["output"] > 0


def test_a_single_unit_is_never_asked(game_env):
    m = game_env.module
    dialog = _install_dialog()
    m.set_confirm_threshold(100)
    game_env.invest_secondary("b", "preserve")
    game_env.invest("monitor")
    assert dialog.asked == []


def test_rescue_asks_when_over_the_threshold(game_env):
    m = game_env.module
    dialog = _install_dialog()
    m.set_confirm_threshold(100)
    m.region.temperature = 20.0
    m.region.melt_started_round = 3
    m.region.counterfactual_temperature = 24.0
    m.region.funds = 400
    assert m.region.is_critical()
    game_env.elements["rescue-button"].dispatch("click", None)
    assert len(dialog.asked) == 1 and "200 funds" in dialog.asked[0]["message"]
    assert m.region.rescue_used is False
    dialog.asked[0]["onConfirm"]()
    assert m.region.rescue_used is True


def test_the_focus_view_rescue_asks_too(game_env):
    m = game_env.module
    dialog = _install_dialog()
    m.set_confirm_threshold(150)
    m.region.temperature = 20.0
    m.region.melt_started_round = 3
    m.region.counterfactual_temperature = 24.0
    m.region.funds = 400
    game_env.elements["focus-rescue-button"].dispatch("click", None)
    assert len(dialog.asked) == 1
    dialog.asked[0]["onConfirm"]()
    assert m.region.rescue_used is True


def test_custom_preset_asks_too(game_env):
    m = game_env.module
    dialog = _install_dialog()
    m.set_confirm_threshold(100)
    m.custom_preset = {"preserve": 1}
    game_env.elements["c-preset-custom-button"].dispatch("click", None)
    assert len(dialog.asked) == 1
    assert m.region_c.capacity["preserve"] == 0
    dialog.asked[0]["onConfirm"]()
    assert m.region_c.capacity["preserve"] > 0


def test_without_a_dialog_on_the_page_it_goes_ahead(game_env):
    m = game_env.module
    m.set_confirm_threshold(100)  # no window at all in the test harness
    game_env.apply_preset("b", "growth")
    assert m.region_b.capacity["output"] > 0


def test_choice_is_stored_and_unknown_values_become_never(game_env):
    m = game_env.module
    storage = FakeStorage()
    sys.modules["js"].localStorage = storage
    assert m.set_confirm_threshold("150") == 150
    assert storage.data[m.CONFIRM_THRESHOLD_KEY] == "150"
    assert m.load_confirm_threshold() == 150
    for bad in ("77", "abc", None, -5, "", 1e9):
        assert m.set_confirm_threshold(bad) == 0, bad
    storage.data[m.CONFIRM_THRESHOLD_KEY] = "999"
    assert m.load_confirm_threshold() == 0


def test_select_change_updates_the_setting_and_the_note(game_env):
    m = game_env.module
    select = game_env.elements["confirm-threshold-select"]
    select.value = "100"
    select.dispatch("change", None)
    assert m.confirm_threshold == 100
    assert "more than 100 funds" in game_env.elements["confirm-threshold-note"].innerText
    select.value = "0"
    select.dispatch("change", None)
    assert "one click" in game_env.elements["confirm-threshold-note"].innerText


def test_reset_to_default_clears_the_threshold(game_env):
    m = game_env.module
    m.set_confirm_threshold(250)
    game_env.elements["settings-reset-button"].dispatch("click", None)
    assert m.confirm_threshold == 0
    assert game_env.elements["confirm-threshold-select"].value == "0"
