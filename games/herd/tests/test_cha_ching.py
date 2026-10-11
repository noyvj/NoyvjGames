"""GF-14 round celebration: Python hands the round's income to the page's HerdFx hook."""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent


class _Fx:
    def __init__(self):
        self.calls = []

    def roundGain(self, earned, beat):
        self.calls.append((earned, beat))


class _Window:
    def __init__(self):
        self.HerdFx = _Fx()


def _with_window():
    window = _Window()
    sys.modules["js"].window = window
    return window.HerdFx


def test_the_round_income_reaches_the_hook(game_env):
    fx = _with_window()
    game_env.farm.funds = 500.0
    game_env.grow_herd()
    expected = game_env.farm.income_breakdown()["total"]
    game_env.advance_round()
    assert fx.calls == [(expected, False)]  # the first round has nothing to beat


def test_a_bigger_round_than_the_last_is_a_beat(game_env):
    fx = _with_window()
    game_env.farm.funds = 2000.0
    game_env.grow_herd()
    game_env.advance_round()
    game_env.advance_round()  # same herd: same income, not a beat
    game_env.grow_herd()
    game_env.advance_round()  # a bigger herd: a beat
    assert [beat for _earned, beat in fx.calls] == [False, False, True]
    game_env.invest_plant_pivot()
    game_env.advance_round()  # income fell a little (plant-based output earns less): not a beat
    assert fx.calls[-1][1] is False


def test_no_hook_is_a_silent_no_op(game_env):
    m = game_env.module
    sys.modules["js"].window = type("W", (), {})()
    assert m.celebrate_round(10, True) is False
    game_env.advance_round()  # must not raise


def test_the_hook_is_never_fed_nan(game_env):
    fx = _with_window()
    game_env.module.celebrate_round(25.5, False)
    assert fx.calls == [(25.5, False)]


def test_settings_js_defaults_on_respects_motion_and_has_a_checkbox():
    js = (HERE / "settings.js").read_text(encoding="utf-8")
    assert 'getItem(CHA_KEY) !== "false"' in js
    assert 'data-reduced-motion' in js and 'data-lite' in js and "prefers-reduced-motion" in js
    assert 'setAttribute("aria-hidden", "true")' in js
    assert "window.HerdFx" in js
    for page in ("index.html", "pc.html"):
        assert 'id="cha-ching-checkbox"' in (HERE / page).read_text(encoding="utf-8")
    css = (HERE / "style.css").read_text(encoding="utf-8")
    assert 'html[data-reduced-motion="true"] .cha-confetti' in css
