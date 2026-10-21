"""The farm achievement glyph (the crop drawn before each earned achievement) looks different in each visual style.

The glyph span is the one champ_achievements.py draws; the CSS in style-2-panels.css and visual-styles.css is what
this checks, by putting one such span on the real page and switching data-visual-style the way visual-style.js does.
"""
import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402

from browser_helpers import open_game  # noqa: E402

GLYPH = "document.querySelector('.achievement-glyph')"


def _style(page, prop, pseudo=None):
    return page.evaluate("() => getComputedStyle(%s, %s).getPropertyValue('%s')"
                         % (GLYPH, "'%s'" % pseudo if pseudo else "null", prop))


def test_achievement_glyph_looks_different_in_each_visual_style_and_raises_no_page_errors(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        page.evaluate("""() => {
            const line = document.createElement('p');
            line.className = 'achievement-earned';
            line.innerHTML = '<span class="achievement-glyph" data-glyph-word="sprout" aria-hidden="true">🌱</span>';
            document.body.appendChild(line);
        }""")
        page.evaluate("document.documentElement.setAttribute('data-visual-style', 'highdef')")
        assert _style(page, "clip-path") == "none"
        assert _style(page, "border-top-width") == "0px"
        page.evaluate("document.documentElement.setAttribute('data-visual-style', 'lowpoly')")
        assert _style(page, "clip-path").startswith("polygon(")
        page.evaluate("document.documentElement.setAttribute('data-visual-style', 'cartoon')")
        assert _style(page, "border-top-width") == "2px"
        page.evaluate("document.documentElement.setAttribute('data-visual-style', 'textbased')")
        assert _style(page, "font-size") == "0px"
        assert _style(page, "content", "::after") == '"[sprout] "'
        assert page.errors == []
        browser.close()
