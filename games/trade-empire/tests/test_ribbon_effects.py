"""J-31 -- the Ledger ribbon of earned-achievement badges (shape plus name),
its unlock flourish, and the Effects toggle that governs the optional
flourishes (the flourish also stays off under Reduce Motion)."""

import types

from .fakes import FakeClassList


def _html(module, *classes):
    html = types.SimpleNamespace(classList=FakeClassList())
    for name in classes:
        html.classList.add(name)
    module.document.documentElement = html
    return html


def test_an_empty_ribbon_invites_the_first_unlock(game_env):
    m = game_env.module
    m.render()
    html = game_env.elements["ledger-ribbon"].innerHTML
    assert f"0 of {len(m.ACHIEVEMENTS)} badges" in html and "Earn an achievement" in html


def test_earned_achievements_become_badges_with_a_shape_and_a_name(game_env):
    m = game_env.module
    m.total_sales_count = 1
    m.render()
    html = game_env.elements["ledger-ribbon"].innerHTML
    assert "First Contract" in html and "ribbon-shape" in html and 'aria-hidden="true">●</span>' in html
    assert f"1 of {len(m.ACHIEVEMENTS)} badges" in html


def test_shapes_cycle_so_neighbouring_badges_differ(game_env):
    m = game_env.module
    badges, _count = (m.ribbon_badges())
    assert badges == []
    m.total_sales_count = 1
    m.max_profit_ever = 200_000
    m.automated_ship_count = lambda: 2
    badges, count = m.ribbon_badges()
    shapes = [shape for shape, _label in badges]
    assert count == len(m.achievement_ids_earned()) and len(set(shapes[:4])) == min(4, len(shapes))


def test_only_the_latest_badges_show_and_the_rest_are_counted(game_env):
    m = game_env.module
    m.legacy_achievements = [e["id"] for e in m.ACHIEVEMENTS]
    m.render()
    html = game_env.elements["ledger-ribbon"].innerHTML
    assert html.count('class="ribbon-badge"') == m.RIBBON_MAX_BADGES
    hidden = len(m.ACHIEVEMENTS) - m.RIBBON_MAX_BADGES
    assert f"+{hidden} more in Achievements" in html


def test_labels_are_escaped(game_env):
    m = game_env.module
    m.ACHIEVEMENTS[0]["label"] = "<b>x</b> & y"
    m.total_sales_count = 1
    m.render()
    assert "&lt;b&gt;x&lt;/b&gt; &amp; y" in game_env.elements["ledger-ribbon"].innerHTML


def test_unlocking_glows_the_ribbon_then_clears_it(game_env):
    m = game_env.module
    _html(m)
    ribbon = game_env.elements["ledger-ribbon"]
    m.total_sales_count = 1
    m.render()
    assert ribbon.classList.contains("ledger-ribbon--flourish")
    game_env.timers.flush()
    assert not ribbon.classList.contains("ledger-ribbon--flourish")


def test_no_flourish_with_effects_off(game_env):
    m = game_env.module
    _html(m, "effects-off")
    m.total_sales_count = 1
    m.render()
    assert not game_env.elements["ledger-ribbon"].classList.contains("ledger-ribbon--flourish")


def test_no_flourish_under_reduced_motion(game_env):
    m = game_env.module
    _html(m, "reduce-motion")
    m.total_sales_count = 1
    m.render()
    assert not game_env.elements["ledger-ribbon"].classList.contains("ledger-ribbon--flourish")


def test_the_effects_switch_also_silences_sparks_and_dock_rings(game_env):
    m = game_env.module
    assert m._effects_on() is True  # no documentElement in the fake: effects stay on
    _html(m, "effects-off")
    assert m._effects_on() is False
    container = game_env.elements["sale-spark-container"]
    container.children = []
    m._spark_burst_high_value_sale()
    assert container.children == []
    ctx = game_env.elements["map-canvas"].getContext("2d")
    m.add_dock_pulse("aurum", "dock")
    ctx.calls.clear()
    m.draw_dock_pulses(ctx)
    assert ctx.calls == []
    _html(m)
    m._spark_burst_high_value_sale()
    assert len(container.children) == m.SALE_SPARK_COUNT


def test_settings_page_has_the_effects_toggle_wired(game_env):
    from pathlib import Path
    base = Path(game_env.module.__file__).parent
    html = (base / "index.html").read_text(encoding="utf-8")
    js = (base / "settings.js").read_text(encoding="utf-8")
    css = (base / "style.css").read_text(encoding="utf-8")
    assert 'id="effects-toggle-button"' in html and 'id="effects-note"' in html
    assert "effects-off" in js and "trade-empire-effects-off" in js and ".effects-off" in css
