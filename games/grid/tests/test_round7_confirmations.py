"""Round-7 pass: re-enable skipped confirmations (C-22), retire asks only for the last unit (FY-24)."""
from .test_career import _install_storage

PREFIX = "confirm-dialog:skip:"


def test_nothing_skipped_by_default(game_env):
    _install_storage()
    game_env.module.render()
    assert game_env.module.skipped_confirmations() == []
    assert game_env.elements["confirm-reset-button"].disabled is True
    assert "Nothing is switched off" in game_env.elements["confirm-reset-status"].innerText


def test_skipped_questions_are_listed_in_words(game_env):
    storage = _install_storage({PREFIX + "grid-retire-last-coal": "true", PREFIX + "grid-finish-run": "true",
                                PREFIX + "grid-retire-last-gas": "false", PREFIX + "other-game": "true"})
    g = game_env.module
    assert g.skipped_confirmations() == ["finishing a run", "retiring the last Coal unit"]
    g.render()
    status = game_env.elements["confirm-reset-status"].innerText
    assert "finishing a run" in status and "last Coal unit" in status and "Gas" not in status
    assert game_env.elements["confirm-reset-button"].disabled is False
    assert storage.data[PREFIX + "other-game"] == "true"


def test_ask_me_again_clears_only_grid_flags(game_env):
    storage = _install_storage({PREFIX + "grid-retire-last-solar": "true", PREFIX + "grid-finish-run": "true",
                                PREFIX + "trade-empire-reset": "true"})
    g = game_env.module
    g.render()
    game_env.elements["confirm-reset-button"].dispatch("click", None)
    assert PREFIX + "grid-retire-last-solar" not in storage.data and PREFIX + "grid-finish-run" not in storage.data
    assert storage.data[PREFIX + "trade-empire-reset"] == "true"
    assert g.skipped_confirmations() == []
    assert game_env.elements["confirm-reset-button"].disabled is True
    assert game_env.elements["sr-announcer"].innerText.startswith("Done: 2 question(s)")


def test_without_storage_nothing_breaks(game_env):
    import sys
    sys.modules["js"].localStorage = None
    g = game_env.module
    assert g.skipped_confirmations() == [] and g.reset_skipped_confirmations() == 0
    g.render()


def test_career_questions_can_never_be_skipped_so_are_not_listed(game_env):
    ids = {action for action, _ in game_env.module.SKIPPABLE_CONFIRMATIONS}
    assert "grid-import-career" not in ids and "grid-reset-career" not in ids
    assert len(ids) == 8


def test_retire_asks_only_for_the_last_unit(game_env):
    """FY-24: any retire from two or more units is instant; the last unit asks."""
    g = game_env.module
    asked = []
    g._confirm_dialog_ask = lambda action_id, message, confirm_label, on_confirm, allow_skip=True: asked.append(action_id)
    game_env.state.plant_counts["coal"] = 3
    game_env.state.funds = 1000
    game_env.retire("coal")
    game_env.retire("coal")
    assert asked == [] and game_env.state.plant_counts["coal"] == 1
    game_env.retire("coal")
    assert asked == ["grid-retire-last-coal"] and game_env.state.plant_counts["coal"] == 1
