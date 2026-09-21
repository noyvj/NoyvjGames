"""Z22 (planning/TODO.md's shared-ConfirmDialog audit): reset-this-world
(A18) and prestige/New Game+ (A1) both used to gate their irreversible
action behind a real browser confirm() dialog (`_confirm()`, a lazy
`import js` per call) -- one of the two games the audit explicitly flagged
as predating shared/confirm-dialog.js (Aftermath's skill-tree reset is the
other). Migrated both to the shared ConfirmDialog via `_confirm_dialog_ask()`
in game.py, same helper shape as Grid's/Herd's/Loop's/Trade Empire's own
copies.

Every other existing reset-world/prestige test in this suite never sees
this gate at all -- it only fires when `js.window.ConfirmDialog` actually
exists, which the fake-DOM harness's `js` module never provides by default
(see conftest.py's `_install_pyodide_fakes`) -- so those tests exercise the
"no dialog available, run immediately" fallback path. These tests install a
fake `window.ConfirmDialog` directly to exercise the real gating branch."""

import sys


class _FakeConfirmDialog:
    def __init__(self):
        self.calls = []
        self._pending_confirm = None

    def ask(self, id, message, confirmLabel, onConfirm):  # noqa: A002 -- matches JS's own `id` kwarg name
        self.calls.append({"id": id, "message": message, "confirmLabel": confirmLabel})
        self._pending_confirm = onConfirm

    def confirm(self):
        assert self._pending_confirm is not None, "no pending confirm to trigger"
        pending, self._pending_confirm = self._pending_confirm, None
        pending()


class _FakeWindow:
    def __init__(self):
        self.ConfirmDialog = _FakeConfirmDialog()


def install_fake_confirm_dialog():
    fake_window = _FakeWindow()
    sys.modules["js"].window = fake_window
    return fake_window


def _win_the_game(game_env):
    module = game_env.module
    for planet in module.PLANETS:
        module.planet_state[planet]["terraform_progress"] = module.TERRAFORM_MAX
    module.update_win_display()


# --- reset-this-world (A18) -----------------------------------------------

def test_reset_world_is_gated_behind_a_confirm_dialog(game_env):
    game_env.earth["resource_count"] = 500
    fake_window = install_fake_confirm_dialog()

    game_env.reset_world("Earth")

    # Not reset yet -- the dialog is pending confirmation.
    assert game_env.earth["resource_count"] == 500
    assert len(fake_window.ConfirmDialog.calls) == 1
    call = fake_window.ConfirmDialog.calls[0]
    assert call["id"] == "sol-reset-world-Earth"
    assert "reset" in call["message"].lower()
    assert "earth" in call["message"].lower()

    fake_window.ConfirmDialog.confirm()

    assert game_env.earth["resource_count"] == 0.0


def test_cancelling_reset_world_leaves_the_planet_untouched(game_env):
    game_env.earth["resource_count"] = 500
    game_env.earth["generator_count"] = 3
    install_fake_confirm_dialog()

    game_env.reset_world("Earth")

    # Cancelling in the real widget just never calls onConfirm -- nothing
    # else to simulate here beyond confirming state didn't move.
    assert game_env.earth["resource_count"] == 500
    assert game_env.earth["generator_count"] == 3


def test_each_planet_gets_its_own_unique_reset_confirm_id(game_env):
    module = game_env.module
    module.unlocked_bodies.add("Mars")
    fake_window = install_fake_confirm_dialog()

    game_env.reset_world("Earth")
    game_env.reset_world("Mars")

    ids = {call["id"] for call in fake_window.ConfirmDialog.calls}
    assert ids == {"sol-reset-world-Earth", "sol-reset-world-Mars"}


# --- prestige / New Game+ (A1) --------------------------------------------

def test_prestige_is_gated_behind_a_confirm_dialog(game_env):
    _win_the_game(game_env)
    fake_window = install_fake_confirm_dialog()

    game_env.prestige()

    # Not prestiged yet -- the dialog is pending confirmation.
    assert game_env.module.prestige_level == 0
    assert len(fake_window.ConfirmDialog.calls) == 1
    call = fake_window.ConfirmDialog.calls[0]
    assert call["id"] == "sol-prestige"
    assert "new game+" in call["message"].lower()

    fake_window.ConfirmDialog.confirm()

    assert game_env.module.prestige_level == 1


def test_cancelling_prestige_leaves_progress_untouched(game_env):
    _win_the_game(game_env)
    install_fake_confirm_dialog()

    game_env.prestige()

    assert game_env.module.prestige_level == 0
    assert game_env.earth["terraform_progress"] == game_env.module.TERRAFORM_MAX


def test_prestige_never_gated_before_the_win_state(game_env):
    """`_prestige_available()` short-circuits before the confirm dialog is
    ever reached, so no dialog is asked for at all -- matching the existing
    (pre-Z22) test_prestige_unavailable_before_the_win_state expectation."""
    fake_window = install_fake_confirm_dialog()

    game_env.prestige()

    assert game_env.module.prestige_level == 0
    assert fake_window.ConfirmDialog.calls == []
