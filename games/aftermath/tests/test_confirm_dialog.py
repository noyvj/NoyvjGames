"""Z22 (planning/TODO.md's shared-ConfirmDialog audit): resetting the
skill tree (E13) used to gate on an in-UI two-click confirmation (click
once to arm, click again to actually reset) rather than
shared/confirm-dialog.js -- one of the two games the audit explicitly
flagged as predating it (SOL's reset-world/prestige is the other).
Migrated to the shared ConfirmDialog via `_confirm_dialog_ask()` in
game.py, same helper shape as Grid's/Herd's/Loop's/Trade Empire's/SOL's
own copies.

Every other existing reset-skill-tree test in this suite never sees this
gate at all -- it only fires when `js.window.ConfirmDialog` actually
exists, which the fake-DOM harness's `js` module never provides by
default (see conftest.py's `_install_pyodide_fakes`) -- so those tests
exercise the "no dialog available, run immediately" fallback path. These
tests install a fake `window.ConfirmDialog` directly to exercise the real
gating branch."""

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


def test_reset_skill_tree_is_gated_behind_a_confirm_dialog(game_env):
    game_env.skill_tree.add_knowledge(20)
    game_env.unlock_skill("early_warning")
    fake_window = install_fake_confirm_dialog()

    game_env.reset_skill_tree_click()

    # Not reset yet -- the dialog is pending confirmation.
    assert game_env.skill_tree.unlocked == {"early_warning"}
    assert len(fake_window.ConfirmDialog.calls) == 1
    call = fake_window.ConfirmDialog.calls[0]
    assert call["id"] == "aftermath-reset-skill-tree"
    assert "20 knowledge points" in call["message"]

    fake_window.ConfirmDialog.confirm()

    assert game_env.skill_tree.unlocked == set()
    assert game_env.skill_tree.knowledge_points == 20  # fully refunded


def test_cancelling_reset_skill_tree_leaves_it_untouched(game_env):
    game_env.skill_tree.add_knowledge(20)
    game_env.unlock_skill("early_warning")
    install_fake_confirm_dialog()

    game_env.reset_skill_tree_click()

    # Cancelling in the real widget just never calls onConfirm -- nothing
    # else to simulate here beyond confirming state didn't move.
    assert game_env.skill_tree.unlocked == {"early_warning"}
    assert game_env.skill_tree.knowledge_points == 15


def test_reset_skill_tree_never_gated_with_nothing_unlocked(game_env):
    """render()'s own disabled-state already guards this, but
    on_reset_skill_tree() itself must not even ask when there's nothing
    to lose -- matching every other game's "no-op, never gated" case for
    an already-empty reset target."""
    fake_window = install_fake_confirm_dialog()

    game_env.reset_skill_tree_click()

    assert fake_window.ConfirmDialog.calls == []
