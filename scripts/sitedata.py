"""Shared facts for the SEO and share-card generators (TODO Y-7, Y-8).

Not a script: `generate-seo.py` and `generate-share-cards.py` import it (the files have hyphens, so they
add scripts/ to sys.path first). It reads the repo's real files so nothing is typed twice:
  * the game list, names, blurbs and tags come from the title cards in index.html (the lobby is the
    single source of truth for what is hub-linked), restricted to slugs in game-manifest.json;
  * dates come from game-added.json / game-last-updated.json; session length from game-sessions.json.
"""

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Confirmed from the git remote (github.com/noyvj/NoyvjGames) and the backend's CORS origin
# (https://noyvj.github.io in app/main.py): GitHub Pages serves the repo under /NoyvjGames/.
BASE_URL = "https://noyvj.github.io/NoyvjGames/"

SITE_NAME = "NoyvjGames"
HUB_DESCRIPTION = (
    "{count} small AI-assisted game demos you play in your browser with nothing to install: "
    "climate, space, economy, language and puzzle games, built one milestone at a time."
)

# Public hub pages: (file, title, description, in_sitemap). Owner-only and thin backend-driven pages
# (admin, ideas, warframe_build_tracker, leaderboards, settings, 404) are deliberately absent.
PUBLIC_PAGES = [
    ("index.html", "NoyvjGames", None, True),
    ("achievements.html", "Achievements - NoyvjGames",
     "Every achievement in every NoyvjGames game in one place, with how many players earned each.", True),
    ("whats-new.html", "What's New - NoyvjGames",
     "A running record of updates across the NoyvjGames hub and every game, pulled from the site's own dev logs.", True),
    ("roadmap.html", "Roadmap - NoyvjGames",
     "What has shipped and what is in progress across the NoyvjGames hub, built from real project history.", True),
    ("events.html", "Seasonal Events - NoyvjGames",
     "The current seasonal event, a countdown to the next one and the badge gallery for every holiday event.", True),
    ("sources.html", "Sources & Credits - NoyvjGames",
     "The real-world research and data behind the games that draw on it, gathered in one place.", True),
    ("credits.html", "Credits & Thanks - NoyvjGames",
     "The tools and services NoyvjGames actually runs on.", True),
    ("help.html", "Help & FAQ - NoyvjGames",
     "Saving, accounts, moving devices and what the site stores. Search it, or pick a topic.", True),
    ("terms.html", "Terms & Privacy - NoyvjGames",
     "What NoyvjGames stores about you, what it does not, and the plain-language terms.", True),
]

# Pages that must never be listed or linked from public pages.
OWNER_ONLY = ["admin.html", "ideas.html", "warframe_build_tracker", "leaderboards.html", "ideas-data.json",
              "ideas-answers.local.json"]


def read_json(name, default=None):
    try:
        return json.loads((ROOT / name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def load_games():
    """Hub-linked games in lobby order: [{slug, name, blurb, tags, href, thumb, added, updated, session}]."""
    page = (ROOT / "index.html").read_text(encoding="utf-8")
    manifest = set((read_json("game-manifest.json", {}) or {}).get("achievements", []))
    added = read_json("game-added.json", {}) or {}
    updated = read_json("game-last-updated.json", {}) or {}
    sessions = (read_json("game-sessions.json", {}) or {}).get("games", {})
    games = []
    for block in re.findall(r'<article class="title-card".*?</article>', page, re.S):
        slug = re.search(r'data-game-slug="([^"]+)"', block).group(1)
        if manifest and slug not in manifest:
            continue
        pick = lambda pattern: html.unescape(re.sub(r"\s+", " ", re.search(pattern, block, re.S).group(1))).strip()
        games.append({
            "slug": slug,
            "name": pick(r'class="title-card-name">([^<]+)<'),
            "blurb": pick(r'class="title-card-blurb">(.*?)</p>'),
            "tags": re.search(r'data-tags="([^"]*)"', block).group(1).split(),
            "href": re.search(r'class="title-card-link" href="([^"]+)"', block).group(1),
            "thumb": re.search(r"title-card-thumb--([\w-]+)", block).group(1),
            "added": added.get(slug),
            "updated": updated.get(slug),
            "session": sessions.get(slug),
        })
    return games


def hub_description(games=None):
    return HUB_DESCRIPTION.format(count=len(games if games is not None else load_games()))


def game_url(slug):
    return f"{BASE_URL}games/{slug}/"


def share_image_url(slug):
    return f"{BASE_URL}share/{slug}.png"


def page_url(filename):
    return BASE_URL if filename == "index.html" else BASE_URL + filename


def esc(text):
    return html.escape(str(text), quote=True)
