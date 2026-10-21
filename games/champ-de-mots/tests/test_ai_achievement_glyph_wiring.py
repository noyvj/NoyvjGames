"""Wiring between the achievement glyph the Python draws and the CSS that styles it (audit of L-31)."""
import re
from pathlib import Path

GAME = Path(__file__).resolve().parents[1]


def test_every_glyph_word_is_a_single_lowercase_word_so_the_text_based_style_can_print_it(game_env):
    # The text-based style prints "[word] " from data-glyph-word, so a word with spaces or capitals would look odd.
    words = [word for _char, word in game_env.module.ACHIEVEMENT_GLYPHS.values()]
    assert all(re.fullmatch(r"[a-z]+", word) for word in words)
    assert game_env.module.DEFAULT_GLYPH[1] == "trophy"


def test_the_css_styles_the_class_and_attribute_the_python_writes(game_env):
    source = (GAME / "champ_achievements.py").read_text(encoding="utf-8")
    visual = (GAME / "visual-styles.css").read_text(encoding="utf-8")
    panels = (GAME / "style-2-panels.css").read_text(encoding="utf-8")
    assert "glyph.className = 'achievement-glyph'" in source
    assert "setAttribute('data-glyph-word'" in source
    assert ".achievement-glyph {" in panels
    for style in ("lowpoly", "cartoon", "textbased"):
        assert 'html[data-visual-style="%s"] .achievement-glyph' % style in visual
    assert 'content: "[" attr(data-glyph-word) "] ";' in visual


def test_the_glyph_is_hidden_from_screen_readers_and_every_earned_line_still_names_its_achievement(game_env):
    # The glyph is decoration (aria-hidden); the label span next to it carries the name for screen readers and for
    # shared/achievement-share.js.
    source = (GAME / "champ_achievements.py").read_text(encoding="utf-8")
    assert "glyph.setAttribute('aria-hidden', 'true')" in source
    assert "achievement-card-label" in source
    assert game_env.module.glyph_for("automated_25")[1] == "sprout"
