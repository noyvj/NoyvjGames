"""I-31: code-drawn achievement glyphs with a once-only draw-in flourish."""

import xml.etree.ElementTree as ET
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent


def test_every_achievement_has_a_glyph_and_no_glyph_is_orphaned(game_env):
    m = game_env.module
    ids = {entry["id"] for entry in m.ACHIEVEMENTS}
    assert set(m.ACHIEVEMENT_GLYPHS) == ids


def test_every_glyph_is_well_formed_svg_with_only_drawing_tags(game_env):
    m = game_env.module
    for achievement_id in m.ACHIEVEMENT_GLYPHS:
        markup = m.achievement_glyph_svg(achievement_id, earned=True)
        root = ET.fromstring(markup.replace("<svg ", '<svg xmlns="http://www.w3.org/2000/svg" ', 1))
        tags = {element.tag.split("}")[1] for element in root.iter()}
        assert tags <= {"svg", "path", "rect", "circle", "polygon"}, (achievement_id, tags)
        assert root.get("aria-hidden") == "true" and root.get("viewBox") == "0 0 36 36"


def test_glyphs_differ_from_each_other(game_env):
    m = game_env.module
    bodies = list(m.ACHIEVEMENT_GLYPHS.values())
    assert len(set(bodies)) == len(bodies)


def test_earned_and_locked_get_their_own_class(game_env):
    m = game_env.module
    assert "achievement-glyph--earned" in m.achievement_glyph_svg("first_investment", True)
    assert "achievement-glyph--locked" in m.achievement_glyph_svg("first_investment", False)
    assert m.achievement_glyph_svg("nope") == ""


def test_a_locked_badge_never_flourishes(game_env):
    assert "fresh" not in game_env.module.achievement_glyph_svg("first_investment", False, True)
    assert "achievement-glyph--fresh" in game_env.module.achievement_glyph_svg("first_investment", True, True)


def test_the_panel_cards_carry_their_glyph(game_env):
    game_env.toggle_achievements()
    panel = game_env.elements["achievements-panel"]
    cards = [c for c in panel.children if getattr(c, "className", "").startswith("achievement-card")]
    assert len(cards) == len(game_env.module.ACHIEVEMENTS)
    for card in cards:
        slot = card.children[0]
        assert slot.className == "achievement-glyph-slot" and "<svg" in slot.innerHTML


def test_a_new_badge_draws_in_once_while_the_panel_is_open(game_env):
    game_env.toggle_achievements()
    game_env.invest("housing")  # earns First Investment, panel open
    panel = game_env.elements["achievements-panel"]
    first = [c for c in panel.children if getattr(c.dataset, "achievementId", "") == "first_investment"][0]
    assert "achievement-glyph--fresh" in first.children[0].innerHTML
    game_env.invest("housing")  # a later redraw: the flourish is spent
    again = [c for c in panel.children if getattr(c.dataset, "achievementId", "") == "first_investment"][0]
    assert "achievement-glyph--fresh" not in again.children[0].innerHTML


def test_a_badge_earned_with_the_panel_closed_flourishes_when_it_opens(game_env):
    game_env.invest("housing")
    game_env.toggle_achievements()
    panel = game_env.elements["achievements-panel"]
    first = [c for c in panel.children if getattr(c.dataset, "achievementId", "") == "first_investment"][0]
    assert "achievement-glyph--fresh" in first.children[0].innerHTML
    game_env.toggle_achievements()
    game_env.toggle_achievements()
    again = [c for c in panel.children if getattr(c.dataset, "achievementId", "") == "first_investment"][0]
    assert "achievement-glyph--fresh" not in again.children[0].innerHTML


def test_a_loaded_save_does_not_flourish_every_old_badge(game_env):
    game_env.invest("housing")
    state = game_env.module.get_state()
    game_env.module.fresh_glyph_ids.clear()
    game_env.module.load_state(state)
    game_env.toggle_achievements()
    html = "".join(c.children[0].innerHTML for c in game_env.elements["achievements-panel"].children if c.children and getattr(c.children[0], "className", "") == "achievement-glyph-slot")
    assert "achievement-glyph--fresh" not in html


def test_css_stops_the_flourish_for_reduce_motion_and_speed_off():
    css = (GAME_DIR / "style.css").read_text(encoding="utf-8")
    assert "html[data-anim-speed=\"off\"] .achievement-glyph--fresh" in css
    assert "html.reduce-motion .achievement-glyph--fresh" in css
    assert "prefers-reduced-motion: reduce" in css
