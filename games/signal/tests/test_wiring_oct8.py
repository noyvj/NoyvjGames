"""Oct 8 wiring: copy result (Z-20), achievement share (Z-27), share meta (Y-7), JSON-LD (Y-8) and the
Credits link (Y-29) are on Signal's pages. Static checks on the page files, plus the result the Copy
button reads."""

import json
import re
from pathlib import Path

import pytest

GAME_DIR = Path(__file__).resolve().parent.parent
SLUG = "signal"
NAME = "Signal"
PAGES = ["index.html", "pc.html"]


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
def test_open_graph_twitter_and_canonical_block_is_in_the_head(name):
    html = head(name)
    snippet = (GAME_DIR.parent.parent / "share" / "meta" / f"{SLUG}.html").read_text(encoding="utf-8")
    assert snippet.split("\n", 1)[1] in html   # the meta block; the Desktop page adds "(Desktop)" to the title
    assert "<title>" + NAME in html
    assert html.count('property="og:title"') == 1
    assert f"games/{SLUG}/" in html and f"share/{SLUG}.png" in html
    # the shared includes keep the head's last link
    assert html.rstrip().endswith('lite-mode.css">')


@pytest.mark.parametrize("name", PAGES)
def test_json_ld_is_inlined_and_valid(name):
    html = head(name)
    match = re.search(r'<script type="application/ld\+json">\n(.*?)\n</script>', html, re.S)
    assert match, "no JSON-LD block"
    data = json.loads(match.group(1).replace("<\\/", "</"))
    expected = json.loads((GAME_DIR.parent.parent / "share" / "jsonld" / f"{SLUG}.json").read_text(encoding="utf-8"))
    assert data == expected
    assert data["name"] == NAME


def test_signal_keeps_its_own_share_text_and_does_not_use_copy_result():
    app = (GAME_DIR / "app.js").read_text(encoding="utf-8")
    assert "lastShareText" in app
    assert "NoyvjCopyResult" not in app
    assert "data-achievement-id" in app
