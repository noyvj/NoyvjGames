"""J19 (planning/TODO.md's shared confirmation-dialog goal): both
research-node unlocks and ship automation route through
shared/confirm-dialog.js's ConfirmDialog.ask() instead of spending
immediately. Per the task's own frequency caveat, this was checked before
wiring anything in -- see CLAUDE.md's "shared confirmation-dialog
integration" note. Both actions are rare/one-time-per-target across an
entire playthrough (automation capped at max_automated_ships(), research
capped at RESEARCH_NODES' fixed 6 entries, each unlockable exactly once),
not part of the repeated Load/Depart core loop, so gating was applied
rather than skipped or softened.

Every other existing automate/research test in this suite never sees
this gate at all -- it only fires when `js.window.ConfirmDialog` actually
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


def _install_fake_confirm_dialog():
    fake_window = _FakeWindow()
    sys.modules["js"].window = fake_window
    return fake_window


def test_automating_a_ship_is_gated_behind_a_confirm_dialog(game_env):
    game_env.module.total_profit = 1000
    fake_window = _install_fake_confirm_dialog()

    game_env.automate(ship_id="1")

    # Not automated yet -- the dialog is pending confirmation.
    assert game_env.ship("1").automated is False
    assert game_env.module.total_profit == 1000
    assert len(fake_window.ConfirmDialog.calls) == 1
    call = fake_window.ConfirmDialog.calls[0]
    assert call["id"] == "trade-empire-automate-ship-1"
    assert str(game_env.module.AUTOMATION_COST) in call["message"]

    fake_window.ConfirmDialog.confirm()

    assert game_env.ship("1").automated is True
    assert game_env.module.total_profit == 1000 - game_env.module.AUTOMATION_COST


def test_cancelling_the_automate_dialog_leaves_the_ship_manual(game_env):
    game_env.module.total_profit = 1000
    _install_fake_confirm_dialog()

    game_env.automate(ship_id="1")

    assert game_env.ship("1").automated is False
    assert game_env.module.total_profit == 1000


def test_unlocking_research_is_gated_behind_a_confirm_dialog(game_env):
    game_env.module.research_points = 100
    fake_window = _install_fake_confirm_dialog()

    game_env.unlock_research("fast_ships")

    # Not unlocked yet -- the dialog is pending confirmation.
    assert "fast_ships" not in game_env.module.unlocked_research
    assert game_env.module.research_points == 100
    assert len(fake_window.ConfirmDialog.calls) == 1
    call = fake_window.ConfirmDialog.calls[0]
    assert call["id"] == "trade-empire-research-fast_ships"
    assert "fast ships" in call["message"].lower()

    fake_window.ConfirmDialog.confirm()

    assert "fast_ships" in game_env.module.unlocked_research
    assert game_env.module.research_points == 100 - game_env.module.RESEARCH_NODES["fast_ships"]["cost"]


def test_cancelling_the_research_dialog_leaves_it_unspent(game_env):
    game_env.module.research_points = 100
    _install_fake_confirm_dialog()

    game_env.unlock_research("fast_ships")

    assert "fast_ships" not in game_env.module.unlocked_research
    assert game_env.module.research_points == 100


def test_each_research_node_and_ship_gets_its_own_unique_confirm_id(game_env):
    game_env.module.total_profit = 1000
    game_env.module.research_points = 100
    fake_window = _install_fake_confirm_dialog()

    game_env.automate(ship_id="1")
    fake_window.ConfirmDialog.confirm()
    game_env.automate(ship_id="2")
    fake_window.ConfirmDialog.confirm()
    game_env.unlock_research("fast_ships")
    fake_window.ConfirmDialog.confirm()

    ids = {call["id"] for call in fake_window.ConfirmDialog.calls}
    assert ids == {
        "trade-empire-automate-ship-1",
        "trade-empire-automate-ship-2",
        "trade-empire-research-fast_ships",
    }
