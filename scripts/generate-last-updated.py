#!/usr/bin/env python3
"""Regenerate game-last-updated.json (hub TODO.md L7).

The hub's title cards show a "last updated" badge per game, sourced from
real git history rather than a hand-maintained date (with ~12 games and
counting, a hand-typed date would go stale immediately). This script is
the "small build/generation step" that produces it — there's no build
step or CI in this repo otherwise, so it's a plain script you re-run by
hand, not something wired into a pipeline.

Usage:
    python3 scripts/generate-last-updated.py

Run this from anywhere inside the repo; it resolves paths relative to
its own location. Regenerate it whenever you want the hub's badges to
reflect the latest commits — at minimum, do it as part of any session
that touches one or more games/<slug>/ folders, same spirit as the
BCM206-DEV-LOG.md / TODO.md session-logging housekeeping in CLAUDE.md.
It's committed alongside index.html (not gitignored) since the hub reads
it as a plain static file at runtime, same pattern as achievements.json
per game.
"""
import json
import subprocess
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
GAMES_DIR = REPO_ROOT / "games"
OUTPUT_PATH = REPO_ROOT / "game-last-updated.json"


def last_commit_date(slug: str) -> Optional[str]:
    result = subprocess.run(
        ["git", "log", "-1", "--format=%ad", "--date=format:%Y-%m-%d", "--", f"games/{slug}/"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    date = result.stdout.strip()
    return date or None


def main() -> None:
    slugs = sorted(p.name for p in GAMES_DIR.iterdir() if p.is_dir())
    dates = {}
    for slug in slugs:
        date = last_commit_date(slug)
        if date:
            dates[slug] = date
        else:
            print(f"warning: no git history found for games/{slug}/ — skipping")

    OUTPUT_PATH.write_text(json.dumps(dates, indent=2, sort_keys=True) + "\n")
    print(f"Wrote {len(dates)} game dates to {OUTPUT_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
