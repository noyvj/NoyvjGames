"""I-28 confirm large moves and I-27 the manual-save nudge."""

import sys
import types

from .fakes import FakeStorage


class FakeDialog:
    def __init__(self):
        self.asked = []

    def ask(self, **kwargs):
        self.asked.append(kwargs)


def _dialog():
    dialog = FakeDialog()
    sys.modules["js"].window = types.SimpleNamespace(ConfirmDialog=dialog)
    return dialog


def _storage(initial=None):
    storage = FakeStorage(initial)
    sys.modules["js"].localStorage = storage
    return storage


def _click(env, element_id):
    env.elements[element_id].dispatch("click", None)


def _set_threshold(env, value):
    env.elements["confirm-threshold-select"].value = str(value)
    env.elements["confirm-threshold-select"].dispatch("change", None)


# ---- I-28 ---------------------------------------------------------------------------------------------
def test_default_is_never_and_a_policy_goes_straight_through(game_env):
    dialog = _dialog()
    assert game_env.module.confirm_threshold == 0
    _click(game_env, "policy-credentialing-button")
    assert dialog.asked == [] and game_env.region.policy_level["credentialing"] == 1


def test_setting_is_stored_and_described(game_env):
    storage = _storage()
    _set_threshold(game_env, 50)
    assert game_env.module.confirm_threshold == 50
    assert storage.data["drift_confirm_threshold_v1"] == "50"
    assert "more than 50%" in game_env.elements["confirm-threshold-note"].innerText
    _set_threshold(game_env, 0)
    assert "Never asks" in game_env.elements["confirm-threshold-note"].innerText


def test_unknown_values_fall_back_to_never(game_env):
    _storage()
    _set_threshold(game_env, 33)
    assert game_env.module.confirm_threshold == 0
    _storage({"drift_confirm_threshold_v1": "banana"})
    assert game_env.module._load_confirm_threshold() == 0
    _storage({"drift_confirm_threshold_v1": "75"})
    assert game_env.module._load_confirm_threshold() == 75


def test_a_policy_over_the_threshold_asks_first_and_shows_the_cost(game_env):
    dialog = _dialog()
    _storage()
    region = game_env.region
    region.funds = 100.0  # the 60-fund first level is 60% of funds
    _set_threshold(game_env, 50)
    _click(game_env, "policy-credentialing-button")
    assert len(dialog.asked) == 1
    ask = dialog.asked[0]
    assert "60 of your 100 funds" in ask["message"] and "60%" in ask["message"] and "level 1" in ask["message"]
    assert ask["allowSkip"] is False
    assert region.policy_level["credentialing"] == 0 and region.funds == 100.0  # nothing bought yet
    ask["onConfirm"]()
    assert region.policy_level["credentialing"] == 1 and region.funds == 40.0


def test_a_policy_at_or_under_the_threshold_is_not_asked(game_env):
    dialog = _dialog()
    _storage()
    game_env.region.funds = 120.0  # exactly 50%
    _set_threshold(game_env, 50)
    _click(game_env, "policy-credentialing-button")
    assert dialog.asked == [] and game_env.region.policy_level["credentialing"] == 1


def test_an_unaffordable_or_maxed_policy_is_not_asked(game_env):
    dialog = _dialog()
    _storage()
    game_env.region.funds = 10.0
    _set_threshold(game_env, 25)
    _click(game_env, "policy-credentialing-button")
    assert dialog.asked == [] and game_env.region.policy_level["credentialing"] == 0
    game_env.region.funds = 5000.0
    game_env.region.policy_level["credentialing"] = game_env.module.POLICY_MAX_LEVEL
    _click(game_env, "policy-credentialing-button")
    assert dialog.asked == []


def test_a_capacity_purchase_is_never_asked(game_env):
    dialog = _dialog()
    _storage()
    _set_threshold(game_env, 25)
    _click(game_env, "housing-invest-button")
    assert dialog.asked == []


def test_reallocation_over_the_threshold_asks_with_the_cost_and_the_loss(game_env):
    dialog = _dialog()
    _storage()
    region = game_env.region
    region.capacity["housing"] = 12.0  # moving 10 is 83% of it
    region.funds = 200.0
    game_env.elements["realloc-from"].value = "housing"
    game_env.elements["realloc-to"].value = "services"
    _set_threshold(game_env, 75)
    _click(game_env, "realloc-button")
    assert len(dialog.asked) == 1
    message = dialog.asked[0]["message"]
    assert "Move 10 Housing capacity (of 12)" in message and "costs 10 of your 200 funds" in message
    assert "20% of the moved capacity is lost" in message and "gains 8" in message
    assert region.capacity["housing"] == 12.0
    dialog.asked[0]["onConfirm"]()
    assert region.capacity["housing"] == 2.0 and region.capacity["services"] == 8.0 and region.funds == 190.0


def test_a_small_reallocation_is_not_asked(game_env):
    dialog = _dialog()
    _storage()
    region = game_env.region
    region.capacity["housing"] = 200.0
    region.funds = 300.0
    game_env.elements["realloc-from"].value = "housing"
    game_env.elements["realloc-to"].value = "services"
    _set_threshold(game_env, 25)
    _click(game_env, "realloc-button")
    assert dialog.asked == [] and region.capacity["housing"] == 190.0


def test_a_reallocation_that_cannot_happen_is_not_asked(game_env):
    dialog = _dialog()
    _storage()
    _set_threshold(game_env, 25)
    game_env.elements["realloc-from"].value = "housing"
    game_env.elements["realloc-to"].value = "services"
    _click(game_env, "realloc-button")  # no housing to move
    assert dialog.asked == []


def test_without_a_dialog_on_the_page_the_move_just_happens(game_env):
    sys.modules["js"].window = types.SimpleNamespace()
    _storage()
    game_env.region.funds = 100.0
    _set_threshold(game_env, 25)
    _click(game_env, "policy-credentialing-button")
    assert game_env.region.policy_level["credentialing"] == 1


def test_reset_to_default_clears_the_threshold(game_env):
    storage = _storage()
    _set_threshold(game_env, 75)
    _click(game_env, "settings-reset-button")
    assert game_env.module.confirm_threshold == 0
    assert storage.data["drift_confirm_threshold_v1"] == "0"


# ---- I-27 ---------------------------------------------------------------------------------------------
def _play(env, rounds):
    for _ in range(rounds):
        env.advance_round()


def test_no_nudge_for_the_first_ten_rounds(game_env):
    _storage()
    _play(game_env, 10)
    assert game_env.module.rounds_since_save() == 10
    assert game_env.elements["save-nudge-box"].hidden is True
    assert game_env.module.save_nudge_text() == ""


def test_nudge_appears_after_more_than_ten_unsaved_rounds(game_env):
    _storage()
    _play(game_env, 11)
    text = game_env.elements["save-nudge"].innerText
    assert game_env.elements["save-nudge-box"].hidden is False
    assert "11 rounds" in text and "not saved in this browser yet" in text


def test_nudge_names_how_long_ago_the_last_save_was(game_env):
    m = game_env.module
    storage = _storage()
    m._now_ms = lambda: 10_000_000_000.0
    storage.data["savedat:drift"] = str(int(10_000_000_000 - 12 * 60 * 1000))
    m._last_seen_saved_at = m._saved_at_ms()  # a save that predates this page: it does not restart the count
    _play(game_env, 12)
    assert "saved 12 min ago" in m.save_nudge_text()


def test_a_save_restarts_the_count(game_env):
    m = game_env.module
    storage = _storage()
    _play(game_env, 11)
    assert game_env.elements["save-nudge-box"].hidden is False
    storage.data["savedat:drift"] = "1760000000000"  # the save widget stamps this after a successful save
    m.render()
    assert game_env.elements["save-nudge-box"].hidden is True
    assert m.rounds_since_save() == 0
    _play(game_env, 5)
    assert m.rounds_since_save() == 5 and game_env.elements["save-nudge-box"].hidden is True


def test_a_save_just_before_an_advance_counts_from_that_round(game_env):
    m = game_env.module
    storage = _storage()
    _play(game_env, 4)
    storage.data["savedat:drift"] = "1760000000000"
    game_env.advance_round()  # the stamp is noticed at the start of the advance, before the round moves on
    assert m.save_baseline_round == 5 and m.rounds_since_save() == 1


def test_dismiss_hides_it_for_another_ten_rounds(game_env):
    m = game_env.module
    _storage()
    _play(game_env, 12)
    _click(game_env, "save-nudge-dismiss")
    assert game_env.elements["save-nudge-box"].hidden is True
    _play(game_env, 10)
    assert game_env.elements["save-nudge-box"].hidden is True
    _play(game_env, 1)
    assert game_env.elements["save-nudge-box"].hidden is False
    assert m.rounds_since_save() == 11


def test_loading_a_save_counts_as_saved_at_its_round(game_env):
    m = game_env.module
    _storage()
    _play(game_env, 14)
    state = m.get_state()
    assert game_env.elements["save-nudge-box"].hidden is False
    assert m.load_state(state)
    assert m.rounds_since_save() == 0 and game_env.elements["save-nudge-box"].hidden is True


def test_nudge_reads_plainly_and_never_blocks(game_env):
    _storage()
    _play(game_env, 15)
    text = game_env.module.save_nudge_text()
    assert "!" not in text and "must" not in text.lower() and "lose" not in text.lower()
    assert game_env.elements["advance-round-button"].disabled is False


def test_blocked_storage_never_breaks_the_nudge(game_env):
    class Blocked:
        def getItem(self, key):
            raise RuntimeError("blocked")

    sys.modules["js"].localStorage = Blocked()
    _play(game_env, 12)
    assert "not saved in this browser yet" in game_env.module.save_nudge_text()
