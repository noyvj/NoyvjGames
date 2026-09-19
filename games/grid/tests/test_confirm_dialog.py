"""C14 (planning/TODO.md's shared confirmation-dialog goal): retiring a
plant type's very last unit routes through shared/confirm-dialog.js's
ConfirmDialog.ask() instead of retiring immediately. Every other existing
retire test in this suite never sees this gate at all -- it only fires
when `js.window.ConfirmDialog` actually exists, which the fake-DOM
harness's `js` module never provides by default (see conftest.py's
`_install_pyodide_fakes`) -- so those tests exercise the "no dialog
available, run immediately" fallback path. These tests install a fake
`window.ConfirmDialog` directly to exercise the real gating branch."""

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


def _install_fake_confirm_dialog():
    fake_window = _FakeWindow()
    sys.modules["js"].window = fake_window
    return fake_window


def test_retiring_the_last_unit_of_a_type_is_gated_behind_a_confirm_dialog(game_env):
    game_env.build("coal")
    fake_window = _install_fake_confirm_dialog()

    game_env.retire("coal")

    # Not retired yet -- the dialog is pending confirmation.
    assert game_env.state.plant_counts["coal"] == 1
    assert len(fake_window.ConfirmDialog.calls) == 1
    call = fake_window.ConfirmDialog.calls[0]
    assert call["id"] == "grid-retire-last-coal"
    assert "coal" in call["message"].lower()

    fake_window.ConfirmDialog.confirm()

    assert game_env.state.plant_counts["coal"] == 0


def test_cancelling_the_dialog_leaves_the_plant_in_place(game_env):
    game_env.build("coal")
    _install_fake_confirm_dialog()

    game_env.retire("coal")

    # Cancelling in the real widget just never calls onConfirm -- nothing
    # else to simulate here beyond confirming the count didn't move.
    assert game_env.state.plant_counts["coal"] == 1


def test_retiring_a_non_last_unit_is_never_gated(game_env):
    game_env.build("coal")
    game_env.build("coal")
    fake_window = _install_fake_confirm_dialog()

    game_env.retire("coal")

    assert game_env.state.plant_counts["coal"] == 1
    assert fake_window.ConfirmDialog.calls == []


def test_retiring_an_already_empty_type_is_a_no_op_and_never_gated(game_env):
    fake_window = _install_fake_confirm_dialog()

    game_env.retire("coal")

    assert game_env.state.plant_counts["coal"] == 0
    assert fake_window.ConfirmDialog.calls == []


def test_each_plant_type_gets_its_own_unique_confirm_id(game_env):
    game_env.build("coal")
    game_env.build("gas")
    fake_window = _install_fake_confirm_dialog()

    game_env.retire("coal")
    game_env.retire("gas")

    ids = {call["id"] for call in fake_window.ConfirmDialog.calls}
    assert ids == {"grid-retire-last-coal", "grid-retire-last-gas"}
