#!/usr/bin/env python3
"""Add the site-wide shared includes (lite mode, a11y, touch targets, error boundary, perf marks,
debug overlay, info footer) to every game's index.html and to the hub pages. Idempotent: a page
that already has an include is left alone, so it is safe to run again after adding a new game.

    python3 scripts/wire-shared-includes.py            # edit the pages
    python3 scripts/wire-shared-includes.py --check    # exit 1 if any page is missing an include

Run `python3 scripts/generate-pc-pages.py` afterwards: each game's Desktop page (pc.html) is
generated from its index.html, so it picks the new tags up from there.

Where the tags go (see planning/SHARED-COMPONENTS.md, "Site-wide includes"):
  * scripts: right after the page's shared/theme.js tag, so they run in <head> before first
    paint and before shared/site-settings.js (which needs window.NoyvjLite);
  * stylesheets: last thing in <head>, after the game's own CSS, so they win ties.
The test shared/tests/test_site_includes.py is the source of truth for which pages need what.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Games another session is editing right now: wired later, listed here and in the test.
EXCLUDE_GAMES = set()
# Hub pages that load shared/theme.js and are public (owner pages and the 404 shell are left out).
HUB_PAGES = ["index.html", "settings.html", "help.html", "credits.html", "achievements.html",
             "whats-new.html", "roadmap.html", "sources.html", "terms.html"]

THEME_TAG = re.compile(r'^([ \t]*)<script src="((?:\.\./\.\./)?shared/)theme\.js"[^>]*></script>[ \t]*\n', re.M)


def game_scripts(prefix, slug):
    return [
        f'<script src="{prefix}lite-mode.js"></script>',
        f'<script src="{prefix}error-boundary.js" data-game-id="{slug}"></script>',
        f'<script src="{prefix}perf-mark.js" data-game-id="{slug}"></script>',
        f'<script src="{prefix}debug-overlay.js"></script>',
        f'<script src="{prefix}info-footer.js" data-game-id="{slug}"></script>',
    ]


def game_styles(prefix):
    return [f'<link rel="stylesheet" href="{prefix}{name}">' for name in ("a11y.css", "touch-targets.css", "lite-mode.css")]


def hub_scripts(prefix):
    return [f'<script src="{prefix}lite-mode.js"></script>']


def hub_styles(prefix):
    return [f'<link rel="stylesheet" href="{prefix}{name}">' for name in ("a11y.css", "lite-mode.css")]


def wire(path, scripts_for, styles_for, slug=None):
    """Returns the new text, or None if the page cannot be wired (no theme.js tag / no </head>)."""
    text = path.read_text(encoding="utf-8")
    match = THEME_TAG.search(text)
    if not match or "</head>" not in text:
        return None
    indent, prefix = match.group(1), match.group(2)
    scripts = [s for s in (scripts_for(prefix, slug) if slug else scripts_for(prefix)) if s not in text]
    styles = [s for s in styles_for(prefix) if s not in text]
    if scripts:
        block = "".join(f"{indent}{line}\n" for line in scripts)
        text = text[: match.end()] + block + text[match.end():]
    if styles:
        text = text.replace("</head>", "".join(f"{line}\n" for line in styles) + "</head>", 1)
    return text


def targets():
    for page in HUB_PAGES:
        yield ROOT / page, lambda p, s=None: hub_scripts(p), hub_styles, None
    for folder in sorted((ROOT / "games").iterdir()):
        page = folder / "index.html"
        if folder.name in EXCLUDE_GAMES or not page.exists():
            continue
        yield page, game_scripts, game_styles, folder.name


def main():
    check = "--check" in sys.argv
    stale = []
    for path, scripts_for, styles_for, slug in targets():
        new = wire(path, scripts_for, styles_for, slug)
        if new is None:
            print(f"cannot wire {path.relative_to(ROOT)}: no shared/theme.js tag or no </head>")
            stale.append(path)
            continue
        if new != path.read_text(encoding="utf-8"):
            stale.append(path)
            if not check:
                path.write_text(new, encoding="utf-8")
                print(f"wired {path.relative_to(ROOT)}")
    if check and stale:
        for path in stale:
            print(f"missing shared includes: {path.relative_to(ROOT)}")
        sys.exit(1)
    if not stale:
        print("every page already has the shared includes")


if __name__ == "__main__":
    main()
