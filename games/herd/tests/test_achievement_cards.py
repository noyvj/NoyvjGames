"""F-31 restyled achievement cards: a glyph per badge, barnyard border, one-off unlock flourish."""

from pathlib import Path
from .pagefiles import game_css

HERE = Path(__file__).resolve().parent.parent


def _cards(env):
    return env.elements["achievements-panel"].children


def test_every_achievement_has_its_own_glyph(game_env):
    m = game_env.module
    ids = [e["id"] for e in m.ACHIEVEMENTS]
    assert set(ids) <= set(m.ACHIEVEMENT_GLYPHS)
    assert len({m.ACHIEVEMENT_GLYPHS[i] for i in ids}) == len(ids)
    assert m.achievement_glyph("bogus") == m.ACHIEVEMENT_GLYPH_DEFAULT


def test_each_card_carries_a_decorative_glyph(game_env):
    game_env.toggle_achievements()
    cards = [c for c in _cards(game_env) if "achievement-card" in c.className]
    assert len(cards) == len(game_env.module.ACHIEVEMENTS)
    for card in cards:
        glyph = card.children[0]
        assert glyph.className == "achievement-card-glyph" and glyph.getAttribute("aria-hidden") == "true"


def test_the_flourish_plays_once_for_a_newly_earned_card(game_env):
    game_env.toggle_achievements()
    game_env.grow_herd()
    first = [c for c in _cards(game_env) if getattr(c.dataset, "achievementId", None) == "first_herd"][0]
    assert "achievement-card--new" in first.className and "achievement-card--earned" in first.className
    game_env.module.render()
    again = [c for c in _cards(game_env) if getattr(c.dataset, "achievementId", None) == "first_herd"][0]
    assert "achievement-card--new" not in again.className


def test_a_loaded_save_does_not_replay_old_flourishes(game_env):
    m = game_env.module
    game_env.farm.herd_size = 12
    m._seed_achievement_toast_baseline()
    game_env.toggle_achievements()
    assert not any("achievement-card--new" in c.className for c in _cards(game_env))


def test_css_has_barnyard_border_and_respects_reduced_motion():
    css = game_css()
    assert "#b5483a" in css and ".achievement-card--new" in css
    for gate in ('html[data-reduced-motion="true"] .achievement-card--new', 'html[data-lite="true"] .achievement-card--new', "prefers-reduced-motion: reduce) { .achievement-card--new"):
        assert gate in css
