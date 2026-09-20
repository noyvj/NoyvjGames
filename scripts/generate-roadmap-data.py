#!/usr/bin/env python3
"""Regenerate game-roadmap-data.json (hub TODO.md L19).

roadmap.html pulls its qualitative "what shipped" text straight from the
root CLAUDE.md's `## Current games` / `## Site-level milestones` tables
at runtime (a plain fetch + regex parse, same pattern whats-new.html
already uses for the two dev logs) — that part needs no precomputed
data. What it can't get at runtime is real git history (a static site
has no git binary in the browser), which is the whole point of this
script per the TODO note: milestone tables alone undersell how much
shipped, since plenty of real work (ideas-round passes, ad-hoc fixes)
never gets its own milestone-table row. This script is the "small
build/generation step" that fills that gap with real commit counts and
recent commit subjects per game, plus a repo-wide total.

Usage:
    python3 scripts/generate-roadmap-data.py

No CI/build step in this repo otherwise — run by hand, same as
generate-last-updated.py. Regenerate whenever you want roadmap.html's
velocity numbers to reflect the latest commits (same "at minimum, as
part of any session touching games/<slug>/" guidance as that script).
"""
import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GAMES_DIR = REPO_ROOT / "games"
OUTPUT_PATH = REPO_ROOT / "game-roadmap-data.json"

RECENT_COMMITS_PER_GAME = 3


def run_git(args):
    result = subprocess.run(["git"] + args, cwd=REPO_ROOT, capture_output=True, text=True, check=True)
    return result.stdout.strip()


def commit_count(slug: str) -> int:
    out = run_git(["rev-list", "--count", "HEAD", "--", f"games/{slug}/"])
    return int(out) if out else 0


def last_updated(slug: str):
    out = run_git(["log", "-1", "--format=%ad", "--date=format:%Y-%m-%d", "--", f"games/{slug}/"])
    return out or None


def recent_commit_subjects(slug: str):
    out = run_git(
        ["log", f"-{RECENT_COMMITS_PER_GAME}", "--format=%s", "--", f"games/{slug}/"]
    )
    return [line for line in out.split("\n") if line] if out else []


def main() -> None:
    slugs = sorted(p.name for p in GAMES_DIR.iterdir() if p.is_dir())
    games = {}
    for slug in slugs:
        count = commit_count(slug)
        if not count:
            print(f"warning: no git history found for games/{slug}/ — skipping")
            continue
        games[slug] = {
            "commit_count": count,
            "last_updated": last_updated(slug),
            "recent_commits": recent_commit_subjects(slug),
        }

    total_commits = int(run_git(["rev-list", "--count", "HEAD"]))
    generated_at = run_git(["log", "-1", "--format=%ad", "--date=format:%Y-%m-%d"])

    data = {
        "generated_at": generated_at,
        "total_commits": total_commits,
        "games": games,
    }
    OUTPUT_PATH.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    print(f"Wrote roadmap data for {len(games)} games to {OUTPUT_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
