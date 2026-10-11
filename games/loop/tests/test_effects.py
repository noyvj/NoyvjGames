"""GH-13 purchase juice, GH-16 strain cracks, H-19 shaped particles, GH-29 haptics."""

import pathlib
import sys
import types

import pytest

HERE = pathlib.Path(__file__).resolve().parent.parent
CSS = (HERE / "style.css").read_text(encoding="utf-8")
JS = (HERE / "settings.js").read_text(encoding="utf-8")
HTML = (HERE / "index.html").read_text(encoding="utf-8")


def install_settings(effects=True, buzzes=None):
    """Fakes the settings.js bridge (the pytest `js` module has no window by default)."""
    buzzes = buzzes if buzzes is not None else []
    settings = types.SimpleNamespace(effectsOn=lambda: effects, haptic=buzzes.append)
    sys.modules["js"].window = types.SimpleNamespace(LoopSettings=settings)
    return buzzes


@pytest.fixture(autouse=True)
def _no_window():
    yield
    if hasattr(sys.modules.get("js"), "window"):
        del sys.modules["js"].window


# ------------------------------------------------------------------ GH-13
def test_a_purchase_snaps_the_node_ripples_and_floats_the_saving(game_env):
    install_settings(effects=True)
    node = game_env.elements["loop-ring-node-recycle"]
    game_env.invest_circularity("recycle")  # 5 units of recycling: 5 fewer raw units
    assert node.classList.contains("loop-ring-node--snap")
    assert game_env.elements["invest-ripple"].classList.contains("invest-ripple--go")
    assert game_env.elements["invest-float"].classList.contains("invest-float--go")
    assert game_env.elements["invest-float"].innerText == "-5 raw"
    game_env.timers.flush()
    assert not node.classList.contains("loop-ring-node--snap")
    assert not game_env.elements["invest-float"].classList.contains("invest-float--go")


def test_a_bigger_purchase_floats_the_whole_saving(game_env):
    install_settings(effects=True)
    game_env.elements["buy-x5-button"].dispatch("click", None)
    game_env.invest_circularity("reuse")  # 5 x 4 units
    assert game_env.elements["invest-float"].innerText == "-20 raw"


def test_a_trade_purchase_ripples_without_a_node_snap(game_env):
    install_settings(effects=True)
    game_env.invest_trade_link()
    assert game_env.elements["invest-ripple"].classList.contains("invest-ripple--go")
    assert all(not game_env.elements[f"loop-ring-node-{m}"].classList.contains("loop-ring-node--snap")
               for m in ("repair", "reuse", "recycle"))


def test_no_float_when_the_purchase_saves_nothing(game_env):
    install_settings(effects=True)
    game_env.chain.funds = 5000.0
    for _ in range(11):
        game_env.invest_circularity("recycle")
    game_env.elements["invest-float"].innerText = ""
    game_env.invest_circularity("recycle")  # the loop was already closed
    assert game_env.elements["invest-float"].innerText == ""


def test_switched_off_or_under_reduced_motion_nothing_animates(game_env):
    install_settings(effects=False)  # settings.js reports false for both "off" and reduced motion
    game_env.invest_circularity("recycle")
    assert not game_env.elements["loop-ring-node-recycle"].classList.contains("loop-ring-node--snap")
    assert game_env.elements["invest-float"].innerText == ""


def test_without_the_bridge_the_purchase_still_works(game_env):
    game_env.invest_circularity("recycle")  # no window at all (the pytest default)
    assert game_env.chain.circularity_investment["recycle"] == 1
    assert game_env.elements["invest-float"].innerText == ""


def test_settings_js_decides_effects_from_the_switch_and_reduced_motion():
    block = JS.split("function effectsOn()")[1].split("}")[0] + "}"
    assert 'data-reduced-motion' in block and "prefers-reduced-motion" in block and 'isOn("data-effects")' in block


def test_css_silences_the_juice_for_off_and_for_reduced_motion():
    assert 'html[data-effects="off"] .invest-float' in CSS
    assert 'html[data-reduced-motion="true"] .invest-float' in CSS
    assert "@media (prefers-reduced-motion: reduce)" in CSS.split("GH-13: purchase juice")[1]


# ------------------------------------------------------------------ GH-16
def test_strain_is_damage_times_the_open_part_of_the_loop(game_env):
    chain = game_env.chain
    m = game_env.module
    assert m.damage_strain_tier() == 0
    chain.total_extracted = 500.0  # full damage, straight line: maximum strain
    assert m.damage_strain_tier() == 4
    chain.total_extracted = 150.0  # damage 0.3, straight line
    assert m.damage_strain_tier() == 3
    chain.total_extracted = 25.0  # damage 0.05
    assert m.damage_strain_tier() == 1


def test_the_cracks_ease_back_as_the_loop_closes(game_env):
    chain = game_env.chain
    m = game_env.module
    chain.total_extracted = 500.0
    chain.funds = 5000.0
    assert m.damage_strain_tier() == 4
    for _ in range(11):
        game_env.invest_circularity("recycle")
    assert chain.is_loop_closed()
    assert m.damage_strain_tier() == 0
    assert chain.damage_fraction() == 1.0  # the damage itself never heals


def test_render_puts_the_tier_on_the_game_container(game_env):
    game_env.chain.total_extracted = 500.0
    game_env.module.render()
    assert game_env.elements["game"].attributes["data-damage-tier"] == "4"
    game_env.chain.funds = 5000.0
    for _ in range(11):
        game_env.invest_circularity("recycle")
    assert game_env.elements["game"].attributes["data-damage-tier"] == "0"


def test_cracks_are_pure_css_and_switchable():
    for tier in "1234":
        assert f'#game[data-damage-tier="{tier}"]' in CSS
    assert 'html[data-cracks="off"]' in CSS
    assert "--crack-a" in CSS and "--crack-d" in CSS
    assert 'html[data-theme="light"]' in CSS.split("GH-16: damage cracks")[1]
    assert 'body:has(#game[data-damage-tier="4"]) .ambient-bg' in CSS


# ------------------------------------------------------------------ H-19
def test_shaped_particles_use_squares_for_lines_and_rings_for_loops():
    block = CSS.split("H-19: shape-coded particles")[1]
    assert 'html[data-particle-shapes="on"] .flow-particle { border-radius: 0;' in block
    assert "border-radius: 50%" in block and "border: 2px solid currentColor" in block
    assert ".return-flow-particle" in block and ".import-flow-particle" in block


# ------------------------------------------------------------------ GH-29
def test_a_purchase_buzzes_when_the_bridge_is_there(game_env):
    buzzes = install_settings(effects=False)
    game_env.invest_circularity("repair")
    assert buzzes[0] == 20


def test_reaching_a_25_percent_mark_double_taps(game_env):
    buzzes = install_settings(effects=False)
    game_env.chain.funds = 5000.0
    for _ in range(2):
        game_env.invest_circularity("recycle")  # 10 of 50 units: 20%, below the first mark
    assert [30, 40, 30] not in buzzes
    game_env.invest_circularity("recycle")  # 15 units: 30%, past the 25% mark
    assert [30, 40, 30] in buzzes
    assert buzzes.count([30, 40, 30]) == 1


def test_haptics_are_off_by_default_and_only_through_settings_js():
    line = [ln for ln in JS.splitlines() if 'key: "loop-haptics"' in ln][0]
    assert "fallback: false" in line
    assert "navigator.vibrate" in JS and 'isOn("data-haptics")' in JS


def test_a_failing_bridge_never_breaks_a_purchase(game_env):
    def boom(_pattern):
        raise RuntimeError("no vibration here")
    sys.modules["js"].window = types.SimpleNamespace(
        LoopSettings=types.SimpleNamespace(effectsOn=lambda: False, haptic=boom))
    game_env.invest_circularity("repair")
    assert game_env.chain.circularity_investment["repair"] == 1


# ------------------------------------------------------------------ settings panel
def test_the_four_switches_exist_and_reset_to_their_defaults():
    for box in ("effects-checkbox", "cracks-checkbox", "particle-shapes-checkbox", "haptics-checkbox"):
        assert f'id="{box}"' in HTML
    for key in ("loop-effects", "loop-cracks", "loop-particle-shapes", "loop-haptics"):
        assert key in JS
    reset = JS.split('"settings-reset-button"')[1]
    assert "applyToggle(toggle, toggle.fallback)" in reset
    # purchase effects and cracks default on, shapes and haptics default off
    lines = {key: [ln for ln in JS.splitlines() if f'key: "{key}"' in ln][0]
             for key in ("loop-effects", "loop-cracks", "loop-particle-shapes", "loop-haptics")}
    assert "fallback: true" in lines["loop-effects"] and "fallback: true" in lines["loop-cracks"]
    assert "fallback: false" in lines["loop-particle-shapes"] and "fallback: false" in lines["loop-haptics"]


def test_both_pages_carry_the_new_elements():
    for name in ("index.html", "pc.html"):
        text = (HERE / name).read_text(encoding="utf-8")
        for needed in ("invest-ripple", "invest-float", "effects-checkbox", "cracks-checkbox",
                       "particle-shapes-checkbox", "haptics-checkbox"):
            assert f'id="{needed}"' in text
