"""F16 (planning/TODO.md's shared confirmation-dialog goal): investing in
the Plant-Based Pivot -- the pricier of the two decoupling investments --
routes through shared/confirm-dialog.js's ConfirmDialog.ask() instead of
investing immediately. Every other existing plant-pivot test in this
suite never sees this gate at all -- it only fires when
`js.window.ConfirmDialog` actually exists, which the fake-DOM harness's
`js` module never provides by default (see conftest.py's
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


def test_investing_in_the_plant_pivot_is_gated_behind_a_confirm_dialog(game_env):
    fake_window = _install_fake_confirm_dialog()
    starting_funds = game_env.farm.funds

    game_env.invest_plant_pivot()

    # Not invested yet -- the dialog is pending confirmation.
    assert game_env.farm.plant_pivot_investment == 0
    assert game_env.farm.funds == starting_funds
    assert len(fake_window.ConfirmDialog.calls) == 1
    call = fake_window.ConfirmDialog.calls[0]
    assert call["id"] == "herd-plant-pivot-invest"
    assert "plant-based pivot" in call["message"].lower()

    fake_window.ConfirmDialog.confirm()

    assert game_env.farm.plant_pivot_investment == 1
    assert game_env.farm.funds == starting_funds - game_env.module.PLANT_PIVOT_COST


def test_cancelling_the_dialog_leaves_the_investment_unspent(game_env):
    _install_fake_confirm_dialog()
    starting_funds = game_env.farm.funds

    game_env.invest_plant_pivot()

    # Cancelling in the real widget just never calls onConfirm -- nothing
    # else to simulate here beyond confirming nothing moved.
    assert game_env.farm.plant_pivot_investment == 0
    assert game_env.farm.funds == starting_funds


def test_repeated_investments_are_each_gated_independently(game_env):
    fake_window = _install_fake_confirm_dialog()

    game_env.invest_plant_pivot()
    fake_window.ConfirmDialog.confirm()
    game_env.invest_plant_pivot()
    fake_window.ConfirmDialog.confirm()

    assert game_env.farm.plant_pivot_investment == 2
    assert len(fake_window.ConfirmDialog.calls) == 2
    assert all(call["id"] == "herd-plant-pivot-invest" for call in fake_window.ConfirmDialog.calls)
