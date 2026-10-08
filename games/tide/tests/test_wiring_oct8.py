"""2026-10-08 wiring pass: shared Copy result button (Z-20), achievement Share buttons (Z-27),
Open Graph/Twitter meta (Y-7), JSON-LD (Y-8) and a Credits link (Y-29) on both the Classic and the
Desktop page. The browser behaviour of the shared pieces is tested in shared/tests/*_browser.py;
here we check the page carries them, the head still ends the way test_site_includes needs, and
copy_result_fields() (which the Copy result button reads) returns sane headline numbers."""

import json
import re
from pathlib import Path

import pytest

GAME_DIR = Path(__file__).resolve().parent.parent
ROOT = GAME_DIR.parent.parent
SLUG = "tide"
GAME_NAME = "Tide"
PANELS = ['session-summary-panel']
PAGES = ["index.html", "pc.html"]


def page(name):
    return (GAME_DIR / name).read_text(encoding="utf-8")


@pytest.mark.parametrize("name", PAGES)
def test_copy_result_and_achievement_share_are_loaded(name):
    html = page(name)
    assert f'<script src="../../shared/copy-result.js" data-game-id="{SLUG}"></script>' in html
    assert f'<script src="../../shared/achievement-share.js" data-game-id="{SLUG}" data-game-name="{GAME_NAME}"></script>' in html
    assert html.count("NoyvjCopyResult.mountButton") == 1
    assert 'window.pyodide.globals.get("copy_result_fields")' in html
    # the share script finds the rows by #achievements-panel, so that id must exist exactly once
    assert html.count('id="achievements-panel"') == 1


@pytest.mark.parametrize("name", PAGES)
@pytest.mark.parametrize("panel", PANELS)
def test_copy_result_panel_exists_and_is_mounted(name, panel):
    html = page(name)
    assert html.count(f'id="{panel}"') == 1
    assert f'mountCopy("{panel}"' in html


@pytest.mark.parametrize("name", PAGES)
def test_meta_block_matches_the_generated_snippet(name):
    html = page(name)
    snippet = (ROOT / "share" / "meta" / f"{SLUG}.html").read_text(encoding="utf-8")
    title, block = snippet.split("\n", 1)
    assert block in html, "Open Graph/Twitter block differs from share/meta"
    assert title.replace("</title>", " (Desktop)</title>") in html if name == "pc.html" else title in html
    for needle in ('property="og:title"', 'property="og:image"', 'name="twitter:card"', 'rel="canonical"'):
        assert needle in html
    # before the shared includes, which have to stay last in <head>
    head = html[: html.index("</head>")]
    assert head.index("share-meta:end") < head.index("shared/theme.js")
    assert head.rstrip().endswith('lite-mode.css">')


@pytest.mark.parametrize("name", PAGES)
def test_jsonld_matches_the_generated_file(name):
    html = page(name)
    match = re.search(r'<script type="application/ld\+json" id="game-jsonld">\n(.*?)\n</script>', html, re.S)
    assert match, "no JSON-LD block"
    expected = json.loads((ROOT / "share" / "jsonld" / f"{SLUG}.json").read_text(encoding="utf-8"))
    assert json.loads(match.group(1).replace("<\\/", "</")) == expected
    assert html.index("application/ld+json") < html.index("</head>")


@pytest.mark.parametrize("name", PAGES)
def test_credits_link_is_added_to_the_howto_panel(name):
    html = page(name)
    assert 'a.href = "../../credits.html"' in html
    assert 'addCredits("howto-panel")' in html
    assert (ROOT / "credits.html").exists()


def test_desktop_page_is_current():
    import importlib.util
    spec = importlib.util.spec_from_file_location("gpp", ROOT / "scripts" / "generate-pc-pages.py")
    gpp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gpp)
    assert gpp.build(SLUG, gpp.load_configs()[SLUG]) == page("pc.html")


def assert_fields_shape(fields):
    assert fields["game"] == GAME_NAME
    assert isinstance(fields["score"], (int, float)) and not isinstance(fields["score"], bool)
    assert isinstance(fields["unit"], str) and fields["unit"]
    assert fields["stats"], "no extra stats"
    for item in fields["stats"]:
        assert isinstance(item, str) or (isinstance(item, dict) and isinstance(item["n"], (int, float)) and item["one"] and item["many"])
    json.dumps(fields)  # must be plain data so it crosses to JavaScript as-is


def test_copy_result_fields_describe_the_run(game_env):
    game_env.invest("output")
    game_env.advance_season()
    game_env.advance_season()
    fields = game_env.module.copy_result_fields()
    assert_fields_shape(fields)
    assert fields["score"] == 2 and fields["unit"] == "seasons"
    assert not any(isinstance(s, dict) and "storm" in s["one"] for s in fields["stats"])


def test_copy_result_fields_count_storms_only_when_there_were_some(game_env):
    game_env.state.storm_log.append({"season": 4})
    fields = game_env.module.copy_result_fields()
    assert {"n": 1, "one": "storm survived", "many": "storms survived"} in fields["stats"]
