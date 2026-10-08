"""Oct 8 wiring: copy result (Z-20), achievement share (Z-27), share meta (Y-7), JSON-LD (Y-8) and the
Credits link (Y-29) are on Chronicle's pages. Static checks on the page files, plus the result the Copy
button reads."""

import json
import re
from pathlib import Path

import pytest

GAME_DIR = Path(__file__).resolve().parent.parent
SLUG = "chronicle"
NAME = "Chronicle"
PAGES = ["index.html"]


def page(name):
    return (GAME_DIR / name).read_text(encoding="utf-8")


def head(name):
    html = page(name)
    return html[: html.index("</head>")]


@pytest.mark.parametrize("name", PAGES)
def test_share_scripts_are_loaded_with_the_game_id(name):
    html = head(name)
    assert f'<script src="../../shared/copy-result.js" data-game-id="{SLUG}"></script>' in html
    assert f'<script src="../../shared/achievement-share.js" data-game-id="{SLUG}" data-game-name="{NAME}"></script>' in html


@pytest.mark.parametrize("name", PAGES)
def test_credits_link_is_a_plain_keyboard_reachable_link(name):
    assert re.search(r'<a [^>]*href="\.\./\.\./credits\.html"[^>]*>Credits</a>', page(name))


@pytest.mark.parametrize("name", PAGES)
def test_copy_result_container_exists_once(name):
    assert page(name).count('id="archive-copy-result"') == 1


def test_app_js_mounts_the_button_and_marks_achievement_rows():
    app = (GAME_DIR / "app.js").read_text(encoding="utf-8")
    assert 'mountButton("#archive-copy-result"' in app
    assert "data-achievement-id" in app and "data-achievement-label" in app
