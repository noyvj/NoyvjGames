"""H-14 buy-multiple (x1 / x5 / x10 chips, shift-click) and H-20 spend-confirmation threshold."""

import pathlib
import types

import pytest

HERE = pathlib.Path(__file__).resolve().parent.parent


def click(env, element_id, event=None):
    env.elements[element_id].dispatch("click", event)


def test_invest_many_is_the_same_as_repeated_single_purchases(game_env):
    chain = game_env.chain
    chain.funds = 1000.0
    assert chain.invest_many("recycle", 4) == 4
    assert chain.circularity_investment["recycle"] == 4
    assert chain.funds == pytest.approx(1000.0 - 4 * 30)
    assert chain.lifetime_investment_spend == pytest.approx(120.0)


def test_invest_many_stops_when_the_funds_run_out(game_env):
    chain = game_env.chain
    chain.funds = 70.0
    assert chain.invest_many("recycle", 10) == 2
    assert chain.funds == pytest.approx(10.0)
    assert chain.affordable_count("recycle", 10) == 0


def test_invest_many_covers_every_trade_partner(game_env):
    chain = game_env.chain
    chain.funds = 1000.0
    assert chain.invest_many("trade", 2) == 2
    assert chain.invest_many("regional", 2) == 2
    assert chain.invest_many("overseas", 1) == 1
    assert (chain.trade_link_investment, chain.regional_trade_investment, chain.overseas_trade_investment) == (2, 2, 1)


def test_default_chip_is_x1_and_labels_are_unchanged(game_env):
    assert game_env.module.buy_multiple == 1
    assert game_env.elements["recycle-invest-button"].innerText == "Recycling Loops (30)"
    assert game_env.elements["buy-x1-button"].attributes["aria-pressed"] == "true"


def test_x5_chip_buys_five_and_shows_the_running_total(game_env):
    game_env.chain.funds = 1000.0
    click(game_env, "buy-x5-button")
    assert game_env.module.buy_multiple == 5
    assert game_env.elements["buy-x5-button"].attributes["aria-pressed"] == "true"
    assert game_env.elements["buy-x1-button"].attributes["aria-pressed"] == "false"
    assert game_env.elements["recycle-invest-button"].innerText == "Recycling Loops x5 (150)"
    game_env.invest_circularity("recycle")
    assert game_env.chain.circularity_investment["recycle"] == 5


def test_label_total_follows_the_funds(game_env):
    game_env.chain.funds = 70.0
    click(game_env, "buy-x10-button")
    assert game_env.elements["recycle-invest-button"].innerText == "Recycling Loops x2 (60)"
    game_env.chain.funds = 5.0
    game_env.module.render()
    # nothing affordable: the label shows one at full price, and the button is disabled
    assert game_env.elements["recycle-invest-button"].innerText == "Recycling Loops x1 (30)"
    assert game_env.elements["recycle-invest-button"].disabled is True


def test_x10_buys_what_it_can_afford(game_env):
    click(game_env, "buy-x10-button")  # 300 funds: ten repair networks is 200
    game_env.invest_circularity("repair")
    assert game_env.chain.circularity_investment["repair"] == 10


def test_trade_buttons_follow_the_chip_too(game_env):
    game_env.chain.funds = 1000.0
    click(game_env, "buy-x5-button")
    assert game_env.elements["trade-link-invest-button"].innerText == "Trade Link x5 (125)"
    game_env.invest_trade_link()
    assert game_env.chain.trade_link_investment == 5


def test_shift_click_buys_five_on_the_x1_chip(game_env):
    game_env.chain.funds = 1000.0
    click(game_env, "repair-invest-button", types.SimpleNamespace(shiftKey=True))
    assert game_env.chain.circularity_investment["repair"] == 5
    click(game_env, "repair-invest-button", types.SimpleNamespace(shiftKey=False))
    assert game_env.chain.circularity_investment["repair"] == 6


def test_an_unaffordable_click_buys_nothing(game_env):
    game_env.chain.funds = 5.0
    game_env.invest_circularity("recycle")
    assert game_env.chain.circularity_investment["recycle"] == 0
    assert game_env.chain.funds == 5.0


# ------------------------------------------------------------- H-20 confirmation threshold
def capture_confirms(game_env, monkeypatch, percent):
    asked = []
    module = game_env.module
    monkeypatch.setattr(module, "_setting_number", lambda name, default=0: percent)
    monkeypatch.setattr(module, "_confirm_dialog_ask",
                        lambda action_id, message, confirm_label, on_confirm: asked.append((message, confirm_label, on_confirm)))
    return asked


def test_no_question_when_the_threshold_is_off(game_env, monkeypatch):
    asked = capture_confirms(game_env, monkeypatch, 0)
    game_env.chain.funds = 300.0
    click(game_env, "buy-x10-button")
    game_env.invest_circularity("recycle")
    assert not asked
    assert game_env.chain.circularity_investment["recycle"] == 10


def test_a_big_purchase_asks_first_and_waits(game_env, monkeypatch):
    asked = capture_confirms(game_env, monkeypatch, 50)
    game_env.chain.funds = 300.0
    click(game_env, "buy-x10-button")
    game_env.invest_circularity("recycle")
    assert len(asked) == 1
    message, label, on_confirm = asked[0]
    assert message == "Spend 300 of 300 funds on 10 x Recycling Loops?"
    assert label == "Spend"
    assert game_env.chain.circularity_investment["recycle"] == 0  # nothing happens until confirmed
    on_confirm()
    assert game_env.chain.circularity_investment["recycle"] == 10
    assert game_env.chain.funds == pytest.approx(0.0)


def test_a_small_purchase_does_not_ask(game_env, monkeypatch):
    asked = capture_confirms(game_env, monkeypatch, 50)
    game_env.chain.funds = 300.0
    game_env.invest_circularity("repair")  # 20 of 300
    assert not asked
    assert game_env.chain.circularity_investment["repair"] == 1


def test_exactly_at_the_threshold_does_not_ask(game_env, monkeypatch):
    asked = capture_confirms(game_env, monkeypatch, 50)
    game_env.chain.funds = 300.0
    click(game_env, "buy-x5-button")
    game_env.invest_circularity("recycle")  # 150 of 300 is exactly half
    assert not asked
    assert game_env.chain.circularity_investment["recycle"] == 5


def test_settings_page_offers_the_threshold_and_resets_it():
    js = (HERE / "settings.js").read_text(encoding="utf-8")
    html = (HERE / "index.html").read_text(encoding="utf-8")
    assert "confirmThreshold" in js and "loop-confirm-threshold" in js
    reset = js.split('"settings-reset-button"')[1]
    assert "applyConfirmThreshold(0)" in reset
    assert 'id="confirm-threshold-select"' in html
    for value in ("0", "50", "75", "90"):
        assert f'<option value="{value}">' in html


def test_the_chips_and_the_threshold_exist_on_both_pages():
    for name in ("index.html", "pc.html"):
        text = (HERE / name).read_text(encoding="utf-8")
        for needed in ("buy-x1-button", "buy-x5-button", "buy-x10-button", "confirm-threshold-select"):
            assert f'id="{needed}"' in text
