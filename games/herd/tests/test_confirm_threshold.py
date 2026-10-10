"""F-18: an optional "ask before a big purchase" setting. The select in Settings stores a share of
current funds in localStorage ("herd-confirm-percent"); a purchase that costs more than that share
goes through the shared confirm dialog (no "don't ask again" box), anything smaller buys at once."""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent


class _FakeConfirmDialog:
    def __init__(self):
        self.calls = []
        self._pending = None

    def ask(self, id, message, confirmLabel, onConfirm, allowSkip=True):  # noqa: A002
        self.calls.append({"id": id, "message": message, "confirmLabel": confirmLabel, "allowSkip": allowSkip})
        self._pending = onConfirm

    def confirm(self):
        pending, self._pending = self._pending, None
        pending()


class _FakeWindow:
    def __init__(self):
        self.ConfirmDialog = _FakeConfirmDialog()


def _setup(game_env, percent):
    window = _FakeWindow()
    sys.modules["js"].window = window
    game_env.local_storage.setItem("herd-confirm-percent", str(percent))
    return window.ConfirmDialog


def test_default_is_off_and_buying_is_immediate(game_env):
    assert game_env.module.confirm_threshold_percent() == 0
    dialog = _setup(game_env, 0)
    game_env.grow_herd()
    assert game_env.farm.herd_size == 1 and dialog.calls == []


def test_a_purchase_over_the_threshold_asks_first(game_env):
    dialog = _setup(game_env, 25)
    game_env.farm.funds = 60.0  # Grow Herd costs 20: 33% of the funds
    game_env.grow_herd()
    assert game_env.farm.herd_size == 0 and game_env.farm.funds == 60.0
    assert len(dialog.calls) == 1
    call = dialog.calls[0]
    assert call["id"] == "herd-big-purchase" and call["allowSkip"] is False
    assert "Grow Herd costs 20 funds" in call["message"] and "25%" in call["message"]
    dialog.confirm()
    assert game_env.farm.herd_size == 1 and game_env.farm.funds == 40.0


def test_a_purchase_at_or_under_the_threshold_does_not_ask(game_env):
    dialog = _setup(game_env, 25)
    game_env.farm.funds = 80.0  # exactly 25%: not over
    game_env.grow_herd()
    assert game_env.farm.herd_size == 1 and dialog.calls == []


def test_a_bulk_purchase_is_judged_by_its_total(game_env):
    dialog = _setup(game_env, 50)
    game_env.farm.funds = 300.0
    game_env.set_bulk(5)  # 20+22+24+26+28 = 120, 40% of the funds: no dialog
    game_env.grow_herd()
    assert dialog.calls == [] and game_env.farm.herd_size == 5
    game_env.farm.funds = 200.0
    game_env.set_bulk("max")  # the rest of the funds: way over 50%
    game_env.grow_herd()
    assert len(dialog.calls) == 1
    assert "funds, " in dialog.calls[0]["message"]


def test_cancelling_leaves_the_farm_alone(game_env):
    dialog = _setup(game_env, 25)
    game_env.farm.funds = 40.0
    game_env.invest_decoupling("feed")
    assert game_env.farm.decoupling_investment["feed"] == 0 and len(dialog.calls) == 1
    # never confirmed: nothing was bought, funds untouched
    assert game_env.farm.funds == 40.0


def test_levers_and_extras_are_guarded_too(game_env):
    dialog = _setup(game_env, 25)
    game_env.farm.funds = 100.0  # genetics 30, supply chain 30: both over 25%
    game_env.elements["genetics-invest-button"].dispatch("click", None)
    game_env.elements["supply-chain-invest-button"].dispatch("click", None)
    assert len(dialog.calls) == 2
    assert game_env.farm.genetics_pending == []


def test_the_pivot_asks_every_time_when_the_setting_says_big(game_env):
    dialog = _setup(game_env, 25)
    game_env.farm.funds = 80.0  # the pivot costs 25: 31%
    game_env.invest_plant_pivot()
    assert dialog.calls[0]["id"] == "herd-big-purchase" and dialog.calls[0]["allowSkip"] is False
    assert "plant-based" in dialog.calls[0]["message"].lower()
    dialog.confirm()
    assert game_env.farm.plant_pivot_investment == 1


def test_a_small_pivot_keeps_its_own_dialog(game_env):
    dialog = _setup(game_env, 50)
    game_env.farm.funds = 300.0
    game_env.invest_plant_pivot()
    assert dialog.calls[0]["id"] == "herd-plant-pivot-invest"


def test_junk_in_storage_means_off(game_env):
    game_env.local_storage.setItem("herd-confirm-percent", "37")
    assert game_env.module.confirm_threshold_percent() == 0
    game_env.local_storage.setItem("herd-confirm-percent", "lots")
    assert game_env.module.confirm_threshold_percent() == 0


def test_settings_select_is_wired_on_both_pages_and_resets():
    js = (HERE / "settings.js").read_text(encoding="utf-8")
    assert '"herd-confirm-percent"' in js and "resetConfirmThreshold();" in js
    for page in ("index.html", "pc.html"):
        html = (HERE / page).read_text(encoding="utf-8")
        assert 'id="confirm-threshold-select"' in html
        for value in ("0", "25", "50", "75"):
            assert f'<option value="{value}">' in html
