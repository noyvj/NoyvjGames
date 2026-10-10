"""The shared Sources page (SR-1, SR-2): every games/<slug>/sources.json against the schema written at the
top of sources.js, the precache entries, and the page itself in headless Chromium (renders the three
groups, escapes everything, never links a non-https address, friendly message for a game without a
file, the hub-wide index and its filter). Run from the repo root:  python3 -m pytest -q scripts/tests -k sources

The browser tests use the harness shared/tests/conftest.py provides: a fake origin served from disk, the
live backend and every other host refused, so nothing here can reach the network."""

import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from hub_browser_fixtures import _shared, chromium, harness  # noqa: E402,F401

KINDS = {"game", "show", "book", "film", "other"}
GROUPS = ("research", "inspiration", "other")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ORIGIN = "http://harness.test"


# ---- the schema --------------------------------------------------------------------------------

def valid_date(value):
    if not isinstance(value, str) or not DATE_RE.match(value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def problems(data, slug):
    """Every way `data` breaks the schema documented in sources.js (an empty list means valid)."""
    out = []
    if not isinstance(data, dict):
        return ["the file is not a JSON object"]
    extra = set(data) - {"game", "updated", *GROUPS}
    if extra:
        out.append(f"unknown top-level keys {sorted(extra)}")
    if data.get("game") != slug:
        out.append(f'"game" must be "{slug}"')
    if not valid_date(data.get("updated")):
        out.append('"updated" must be a real YYYY-MM-DD date')
    for group in GROUPS:
        entries = data.get(group)
        if not isinstance(entries, list):
            out.append(f'"{group}" must be a list (an empty one is fine)')
            continue
        for i, e in enumerate(entries):
            where = f"{group}[{i}]"
            if not isinstance(e, dict):
                out.append(f"{where} is not an object")
                continue
            allowed = {"title", "by", "url", "note"} | ({"read"} if group == "research" else set()) | ({"kind"} if group == "inspiration" else set())
            if set(e) - allowed:
                out.append(f"{where} has unknown keys {sorted(set(e) - allowed)}")
            required = ["title", "note"] + (["by"] if group != "inspiration" else ["kind"])
            for key in required:
                v = e.get(key)
                if not isinstance(v, str) or not v.strip():
                    out.append(f'{where} needs a non-empty "{key}"')
            for key in ("by", "url", "read"):
                if key in e and not isinstance(e[key], str):
                    out.append(f'{where} "{key}" must be a string')
            if group == "inspiration" and e.get("kind") not in KINDS:
                out.append(f'{where} "kind" must be one of {sorted(KINDS)}')
            if "url" in e:
                u = urlparse(e["url"]) if isinstance(e["url"], str) else None
                if not u or u.scheme != "https" or not u.netloc:
                    out.append(f'{where} "url" must be an https address')
            if "read" in e and not valid_date(e["read"]):
                out.append(f'{where} "read" must be a real YYYY-MM-DD date')
    return out


GOOD = {
    "game": "demo", "updated": "2026-10-10",
    "research": [{"title": "T", "by": "B", "url": "https://example.org/a", "read": "2026-10-01", "note": "n"}],
    "inspiration": [{"title": "T", "kind": "game", "note": "n"}],
    "other": [{"title": "T", "by": "B", "note": "n"}],
}


def test_the_validator_accepts_a_good_file_and_rejects_each_kind_of_mistake():
    assert problems(GOOD, "demo") == []
    bad = json.loads(json.dumps(GOOD))
    bad["game"] = "other"
    bad["updated"] = "2026-02-31"
    bad["research"][0]["url"] = "http://example.org/"
    bad["research"][0]["note"] = "  "
    bad["research"][0]["read"] = "yesterday"
    bad["inspiration"][0]["kind"] = "podcast"
    bad["other"][0].pop("by")
    bad["surprise"] = 1
    found = " | ".join(problems(bad, "demo"))
    for fragment in ("unknown top-level", '"game" must be', '"updated"', "https address", '"note"', '"read"', '"kind"', '"by"'):
        assert fragment in found, (fragment, found)
    assert problems({"game": "demo", "updated": "2026-10-10", "research": [], "inspiration": []}, "demo")


SOURCE_FILES = sorted((ROOT / "games").glob("*/sources.json"))


@pytest.mark.parametrize("path", SOURCE_FILES, ids=[p.parent.name for p in SOURCE_FILES])
def test_every_games_sources_file_matches_the_schema(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    assert problems(data, path.parent.name) == []


def test_the_example_games_exist_on_the_hub():
    hub = (ROOT / "index.html").read_text(encoding="utf-8")
    slugs = set(re.findall(r'data-game-slug="([a-z0-9-]+)"', hub))
    for path in SOURCE_FILES:
        assert path.parent.name in slugs, f"{path} belongs to no game on the hub"


# ---- precache ---------------------------------------------------------------------------------

def test_the_new_files_are_precached_and_exist():
    sw = (ROOT / "sw.js").read_text(encoding="utf-8")
    block = sw[sw.index("const PRECACHE_URLS"):sw.index("];", sw.index("const PRECACHE_URLS"))]
    entries = {re.sub(r"^\./", "", m) for m in re.findall(r'"([^"]+)"', block)}
    for name in ("sources.html", "sources.js", "sources.css"):
        assert name in entries, f"{name} is not in sw.js's PRECACHE_URLS"
        assert (ROOT / name).is_file()
    assert int(re.search(r"const SW_VERSION = (\d+);", sw).group(1)) >= 53


def test_the_page_loads_only_files_that_exist_and_is_public():
    html = (ROOT / "sources.html").read_text(encoding="utf-8")
    for ref in re.findall(r'(?:src|href)="([^"#?:]+\.(?:js|css))"', html):
        assert (ROOT / ref).is_file(), ref
    assert "noindex" not in html
    assert 'href="sources.css"' in html and 'src="sources.js"' in html and 'src="hub-games.js"' in html


# ---- the page in a browser --------------------------------------------------------------------

SAMPLE = {
    "game": "hull-repair", "updated": "2026-10-09",
    "research": [
        {"title": "A report <b>bold</b>", "by": "Some Institute", "url": "https://www.example.org/report?a=1", "read": "2026-10-01",
         "note": "Gave the <i>numbers</i> for the tide table."},
        {"title": "Unsafe link", "by": "Someone", "url": "javascript:alert(1)", "note": "must not become a link"},
    ],
    "inspiration": [{"title": "Some Game", "kind": "game", "by": "A Studio", "note": "The routing idea."},
                    {"title": "Odd kind", "kind": "podcast", "note": "falls back to other"}],
    "other": [],
}


def serve(h, slug, body, status=200):
    h.page.route(f"**/games/{slug}/sources.json",
                 lambda route: route.fulfill(status=status, content_type="application/json", body=json.dumps(body)))


def test_a_game_page_renders_the_three_groups_escapes_text_and_links_safely(harness):
    h = harness()
    serve(h, "hull-repair", SAMPLE)
    h.goto("/sources.html?game=hull-repair")
    h.page.wait_for_selector(".src-group")
    assert h.page.inner_text("h1") == "Sources: Hull Repair"
    groups = h.page.eval_on_selector_all(".src-group", "els => els.map(e => [e.dataset.group, e.querySelector('h2').textContent])")
    assert groups == [["research", "Research (2)"], ["inspiration", "Inspiration (2)"], ["other", "Other credits (0)"]]
    # nothing from the file became markup
    assert h.page.query_selector(".src-item b") is None and h.page.query_selector(".src-item i") is None
    assert "A report <b>bold</b>" in h.page.inner_text(".src-group[data-group=research]")
    # the https link: new tab, no opener, domain shown; the javascript: address is plain text
    links = h.page.eval_on_selector_all(".src-item a", "els => els.map(a => [a.href, a.target, a.rel])")
    assert links == [["https://www.example.org/report?a=1", "_blank", "noopener noreferrer"]]
    assert "example.org" in h.page.inner_text(".src-domain") and "javascript:alert(1)" in h.page.inner_text(".src-group[data-group=research]")
    text = h.page.inner_text(".src-group[data-group=research]")
    assert "read 2026-10-01" in text and "Some Institute" in text
    insp = h.page.inner_text(".src-group[data-group=inspiration]")
    assert "Game · by A Studio" in insp and "Other" in insp
    # the empty group says so in a sentence; back links go to the game and the hub
    assert "No other credits are listed" in h.page.inner_text(".src-group[data-group=other]")
    hrefs = h.page.eval_on_selector_all(".src-back a", "els => els.map(a => a.getAttribute('href'))")
    assert hrefs == ["games/hull-repair/index.html", "sources.html", "index.html"]
    assert "2026-10-09" in h.page.inner_text(".src-summary")
    assert h.errors == []


def test_a_game_without_a_file_gets_a_friendly_message(harness):
    h = harness()
    # every game now has a real file, so simulate a game that has none
    h.page.route("**/games/canopy/sources.json", lambda route: route.fulfill(status=404, body=""))
    h.goto("/sources.html?game=canopy")
    h.page.wait_for_selector(".src-message")
    assert h.page.inner_text("h1") == "Sources: Canopy"
    text = h.page.inner_text(".src-message")
    assert "No sources file yet" in text and "Back to Canopy" in text
    assert h.page.query_selector(".src-group") is None


def test_an_unknown_game_and_a_hostile_parameter_never_load_anything(harness):
    h = harness()
    h.goto("/sources.html?game=no-such-game")
    h.page.wait_for_selector(".src-message")
    assert "No game called that" in h.page.inner_text(".src-message")
    assert h.page.inner_text("h1") == "Sources & Credits"
    h.goto("/sources.html?game=../../app/main")
    h.page.wait_for_selector(".src-message")
    assert "No game called that" in h.page.inner_text(".src-message")
    assert h.page.query_selector(".src-group") is None


def test_a_broken_file_shows_a_message_not_a_blank_page(harness):
    h = harness()
    h.page.route("**/games/hull-repair/sources.json", lambda route: route.fulfill(status=200, content_type="application/json", body="{not json"))
    h.goto("/sources.html?game=hull-repair")
    h.page.wait_for_selector(".src-message")
    assert "could not be read" in h.page.inner_text(".src-message")


def test_the_index_lists_every_game_with_counts_and_filters(harness):
    h = harness()
    serve(h, "hull-repair", SAMPLE)
    h.page.route("**/games/sol/sources.json", lambda route: route.fulfill(status=404, body=""))
    h.goto("/sources.html")
    h.page.wait_for_selector(".src-game")
    cards = h.page.eval_on_selector_all(".src-game", "els => els.map(e => e.dataset.slug)")
    hub = (ROOT / "index.html").read_text(encoding="utf-8")
    assert cards == list(dict.fromkeys(re.findall(r'data-game-slug="([a-z0-9-]+)"', hub)))
    assert len(cards) >= 24
    hull = h.page.query_selector(".src-game[data-slug=hull-repair]")
    assert [c.inner_text() for c in hull.query_selector_all(".src-count")] == ["2 research", "2 inspiration", "0 other credits"]
    assert hull.query_selector("h2 a").get_attribute("href") == "sources.html?game=hull-repair"
    assert "No sources file yet" in h.page.inner_text(".src-game[data-slug=sol]")
    # the legacy hand-written list stays on the index
    assert h.page.is_visible("#src-legacy")
    # filter: by entry text opens the matching game and hides the rest
    h.page.fill("#src-filter", "tide table")
    assert h.page.eval_on_selector_all(".src-game:not([hidden])", "els => els.map(e => e.dataset.slug)") == ["hull-repair"]
    assert h.page.eval_on_selector(".src-game[data-slug=hull-repair] details", "d => d.open")
    assert "Showing 1 of" in h.page.inner_text(".src-status")
    # filter: by game name
    h.page.fill("#src-filter", "canopy")
    assert h.page.eval_on_selector_all(".src-game:not([hidden])", "els => els.map(e => e.dataset.slug)") == ["canopy"]
    h.page.fill("#src-filter", "zzzzqqq")
    assert "No source matches" in h.page.inner_text(".src-nomatch")
    h.page.fill("#src-filter", "")
    assert h.page.query_selector(".src-nomatch") is None
    assert h.api_calls == []


def test_the_page_follows_the_theme_and_fits_a_phone(chromium):
    Harness = _shared.Harness
    for size in ((1440, 900), (360, 740)):
        for scheme in ("light", "dark"):
            h = Harness(chromium, size=size, media={"color_scheme": scheme})
            try:
                serve(h, "hull-repair", SAMPLE)
                h.goto("/sources.html?game=hull-repair")
                h.page.wait_for_selector(".src-group")
                assert h.page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")
                assert h.page.evaluate("document.documentElement.dataset.theme") == scheme
            finally:
                h.close()
