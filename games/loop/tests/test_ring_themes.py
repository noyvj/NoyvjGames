"""GH-23: cosmetic ring themes unlocked through the career, chosen in Settings."""

import pathlib
import sys
import types

HERE = pathlib.Path(__file__).resolve().parent.parent
CSS = (HERE / "style.css").read_text(encoding="utf-8")
JS = (HERE / "settings.js").read_text(encoding="utf-8")


def test_a_new_career_has_only_the_standard_theme(game_env):
    m = game_env.module
    assert m.ring_theme_unlocked("standard") and m.ring_theme_count() == 0
    for theme in ("neon", "blueprint", "paper"):
        assert not m.ring_theme_unlocked(theme)
        el = game_env.elements[f"ring-theme-{theme}"]
        assert el.disabled is True and "locked:" in el.innerText
    assert game_env.elements["ring-theme-standard"].disabled is False
    assert "0 of 3 themes unlocked" in game_env.elements["ring-theme-status"].innerText


def test_neon_opens_with_the_first_close(game_env):
    game_env.chain.funds = 5000.0
    for _ in range(11):
        game_env.invest_circularity("recycle")
    game_env.advance_cycle()
    m = game_env.module
    assert m.ring_theme_unlocked("neon") and not m.ring_theme_unlocked("blueprint")
    el = game_env.elements["ring-theme-neon"]
    assert el.disabled is False and el.innerText == "Neon"


def test_blueprint_opens_with_the_secret_yard_and_paper_with_three_plates(game_env):
    m = game_env.module
    m.career_closed_categories.update({"electronics", "clothing", "furniture"})
    m.career_plates.update({"scrapper", "fixer", "swapper"})
    m.render()
    assert m.ring_theme_unlocked("blueprint") and m.ring_theme_unlocked("paper")
    assert game_env.elements["ring-theme-paper"].innerText == "Paper cut-out"
    assert "3 of 3 themes unlocked" in game_env.elements["ring-theme-status"].innerText


def test_two_plates_are_not_enough_for_paper(game_env):
    m = game_env.module
    m.career_plates.update({"scrapper", "fixer"})
    assert not m.ring_theme_unlocked("paper")


def test_an_unknown_theme_is_never_unlocked(game_env):
    assert game_env.module.ring_theme_unlocked("rainbow") is False


def test_a_chosen_theme_that_is_locked_falls_back_to_standard(game_env):
    applied = []
    settings = types.SimpleNamespace(ringTheme=lambda: "neon", applyRingTheme=applied.append)
    sys.modules["js"].window = types.SimpleNamespace(LoopSettings=settings)
    try:
        game_env.module.render()
        assert applied == ["standard"]
        applied.clear()
        game_env.module.career_closed_categories.add("electronics")
        game_env.module.render()
        assert applied == []  # now open: left alone
    finally:
        del sys.modules["js"].window


def test_a_broken_bridge_never_breaks_rendering(game_env):
    def boom():
        raise RuntimeError("no storage")
    sys.modules["js"].window = types.SimpleNamespace(LoopSettings=types.SimpleNamespace(ringTheme=boom))
    try:
        game_env.module.render()
    finally:
        del sys.modules["js"].window


def test_themes_change_nothing_in_a_save(game_env):
    assert "ring_theme" not in game_env.module.get_state()


def test_css_and_settings_cover_every_theme():
    for theme in ("neon", "blueprint", "paper"):
        assert f'html[data-ring-theme="{theme}"] .loop-ring-node' in CSS
        assert f'"{theme}"' in JS
    assert "loop-ring-theme" in JS and 'applyRingTheme("standard")' in JS.split('"settings-reset-button"')[1]


def test_both_pages_have_the_picker():
    for name in ("index.html", "pc.html"):
        text = (HERE / name).read_text(encoding="utf-8")
        for ident in ("ring-theme-select", "ring-theme-neon", "ring-theme-status"):
            assert f'id="{ident}"' in text
