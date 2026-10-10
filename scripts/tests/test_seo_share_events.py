"""Static checks for Y-7 (share cards + OG/Twitter meta), Y-8 (sitemap, robots, JSON-LD), Y-12 (events page)
and Y-28 (achievements print).

Run from the repo root:  python3 -m pytest -q scripts/tests
"""

import importlib.util
import json
import re
import struct
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import sitedata  # noqa: E402

OWNER_WORDS = ["admin", "ideas", "warframe", "leaderboards", "owner-gate", "owner-links"]
META_PAGES = ["index.html", "achievements.html", "whats-new.html", "roadmap.html", "sources.html",
              "credits.html", "help.html", "events.html"]
GAMES = sitedata.load_games()


def local_path(url):
    """Map a site URL to the file GitHub Pages would serve for it."""
    assert url.startswith(sitedata.BASE_URL), url
    rel = urlparse(url).path[len(urlparse(sitedata.BASE_URL).path):]
    if rel == "" or rel.endswith("/"):
        rel += "index.html"
    return ROOT / rel


def png_size(path):
    data = path.read_bytes()[:24]
    assert data[:8] == b"\x89PNG\r\n\x1a\n", f"{path} is not a PNG"
    return struct.unpack(">II", data[16:24])


# ---- Y-8: sitemap, robots, JSON-LD ----

def test_game_list_matches_lobby_and_manifest():
    slugs = [g["slug"] for g in GAMES]
    manifest = json.loads((ROOT / "game-manifest.json").read_text(encoding="utf-8"))["achievements"]
    assert len(slugs) == 21 and set(slugs) <= set(manifest)


def test_sitemap_lists_existing_files_only():
    text = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
    locs = re.findall(r"<loc>([^<]+)</loc>", text)
    assert len(locs) == len(set(locs))
    for url in locs:
        assert local_path(url).is_file(), f"{url} has no file"
    for game in GAMES:
        assert sitedata.game_url(game["slug"]) in locs
    for page in META_PAGES + ["terms.html"]:
        assert sitedata.page_url(page) in locs
    for url in locs:
        assert not any(word in url for word in OWNER_WORDS), f"owner page in sitemap: {url}"
    for lastmod in re.findall(r"<lastmod>([^<]+)</lastmod>", text):
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", lastmod)


def test_robots_points_at_sitemap_and_names_no_owner_page():
    text = (ROOT / "robots.txt").read_text(encoding="utf-8")
    assert f"Sitemap: {sitedata.BASE_URL}sitemap.xml" in text
    assert "User-agent: *" in text
    for line in text.splitlines():
        if line.startswith("#"):
            continue
        assert not any(word in line.lower() for word in OWNER_WORDS), line
    assert "Disallow: /admin" not in text


def test_no_search_console_token_is_invented():
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "google-site-verification" not in index
    assert not list(ROOT.glob("google*.html"))


def test_per_game_jsonld_is_valid_and_points_at_real_things():
    for game in GAMES:
        data = json.loads((ROOT / "share" / "jsonld" / f"{game['slug']}.json").read_text(encoding="utf-8"))
        assert data["@context"] == "https://schema.org"
        assert "VideoGame" in data["@type"] and "WebApplication" in data["@type"]
        assert data["name"] == game["name"]
        assert local_path(data["url"]).is_file()
        assert local_path(data["image"]).is_file()
        assert "aggregateRating" not in data  # never copy a live rating into static markup


def test_index_embeds_valid_hub_jsonld():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    match = re.search(r'<script type="application/ld\+json" id="hub-jsonld">\n(.*?)\n</script>', html, re.S)
    graph = json.loads(match.group(1))["@graph"]
    kinds = {node["@type"] for node in graph}
    assert kinds == {"WebSite", "ItemList"}
    items = next(n for n in graph if n["@type"] == "ItemList")["itemListElement"]
    assert [i["item"]["name"] for i in items] == [g["name"] for g in GAMES]


@pytest.mark.parametrize("script", ["generate-seo.py", "generate-share-cards.py"])
def test_generated_text_files_are_up_to_date(script):
    result = subprocess.run([sys.executable, str(ROOT / "scripts" / script), "--check"], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


# ---- Y-7: cards and meta ----

@pytest.mark.parametrize("name", ["hub"] + [g["slug"] for g in GAMES])
def test_share_card_is_1200_by_630(name):
    path = ROOT / "share" / f"{name}.png"
    assert path.is_file()
    assert png_size(path) == (1200, 630)
    assert path.stat().st_size > 20_000, "suspiciously small card"


@pytest.mark.parametrize("slug", [g["slug"] for g in GAMES])
def test_per_game_meta_snippet(slug):
    text = (ROOT / "share" / "meta" / f"{slug}.html").read_text(encoding="utf-8")
    for needle in ("<title>", 'property="og:title"', 'property="og:image"', 'name="twitter:card" content="summary_large_image"',
                   'rel="canonical"', 'property="og:image:width" content="1200"'):
        assert needle in text, needle
    assert f"{sitedata.BASE_URL}share/{slug}.png" in text
    assert f"{sitedata.BASE_URL}games/{slug}/" in text


@pytest.mark.parametrize("page", META_PAGES)
def test_public_pages_carry_open_graph_and_twitter_meta(page):
    html = (ROOT / page).read_text(encoding="utf-8")
    head = html[: html.index("</head>")]
    for needle in ('property="og:title"', 'property="og:description"', 'property="og:image"', 'property="og:url"',
                   'name="twitter:card"', 'name="twitter:image"', 'name="description"', 'rel="canonical"'):
        assert needle in head, f"{page}: {needle}"
    assert head.count('property="og:title"') == 1
    assert 'content="' + sitedata.BASE_URL + 'share/hub.png"' in head
    # The shared includes must stay last in <head> (shared/tests/test_site_includes.py).
    if "shared/lite-mode.css" in head:
        assert head.rstrip().endswith('lite-mode.css">')
    assert head.index("share-meta:start") < head.index("shared/theme.js")


def test_card_generator_draws_in_code_and_fetches_nothing():
    source = (ROOT / "scripts" / "generate-share-cards.py").read_text(encoding="utf-8")
    assert "urlopen" not in source and "requests" not in source and "Image.open" not in source


# ---- Y-12: events ----

def load_events_json():
    return json.loads((ROOT / "events.json").read_text(encoding="utf-8"))


def seasonal_module():
    spec = importlib.util.spec_from_file_location("seasonal_events", ROOT / "shared" / "seasonal_events.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_events_json_matches_the_shared_event_table():
    data = load_events_json()
    ids = [e["id"] for e in data["events"]]
    assert ids == [e["id"] for e in seasonal_module().DEFAULT_EVENTS]
    names = {e["id"]: e["name"] for e in seasonal_module().DEFAULT_EVENTS}
    games = {p.name for p in (ROOT / "games").iterdir() if p.is_dir()}
    for event in data["events"]:
        assert event["name"] == names[event["id"]]
        assert event["host"]["slug"] in games
        assert event["host"]["status"] in ("coming", "live")
        assert re.fullmatch(r"#[0-9a-f]{6}", event["accent"])
        assert event["task"] and event["about"]
        assert 1 <= len(event["mark"]) <= 3
        assert "when" not in event, "dates must come from shared/seasonal-events.js, not events.json"


def test_events_page_is_honest_and_self_consistent():
    html = (ROOT / "events.html").read_text(encoding="utf-8")
    data = load_events_json()
    live = [e for e in data["events"] if e["host"]["status"] == "live"]
    if not live:
        assert "No game hosts a seasonal event yet" in html
    assert "returns next year" in html.lower() or "Returns next year" in html
    for needle in ("shared/seasonal-events.js", "shared/seasonal-dates.json", "events.json", "prefers-reduced-motion",
                   'data-theme="light"', "max-width: 420px", "skip-link", 'tabindex="-1"', "textContent"):
        assert needle in html, needle
    assert "innerHTML" not in html, "all text is written with textContent"


def test_events_page_links_no_owner_only_page():
    html = (ROOT / "events.html").read_text(encoding="utf-8").lower()
    hrefs = re.findall(r'href="([^"]+)"', html)
    for href in hrefs:
        assert not any(word in href for word in OWNER_WORDS), href
    assert "owner" not in html


def test_events_page_is_linked_from_the_hub():
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    assert index.count('href="events.html"') >= 2  # nav and footer


# ---- Y-28: achievements print ----

def test_achievements_print_stylesheet_is_wired():
    html = (ROOT / "achievements.html").read_text(encoding="utf-8")
    assert '<link rel="stylesheet" href="shared/print-summary.css" media="print">' in html
    assert re.search(r'<main id="achievements-main"[^>]*class="[^"]*\bprint-summary\b', html)
    assert 'id="ach-print"' in html and "window.print()" in html
    assert "ach-bar-fill" in html
    css = (ROOT / "style.css").read_text(encoding="utf-8")
    assert "@media print" in css and ".print-summary .ach-bar .ach-bar-fill" in css
    assert (ROOT / "shared" / "print-summary.css").is_file()
