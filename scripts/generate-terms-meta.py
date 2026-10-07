#!/usr/bin/env python3
"""Regenerate terms-meta.json (Y-30): the "last changed" date and the short "what changed" list
that terms.html shows at the bottom of the page.

Both come from git, not from a hand-typed line: the date is the commit date of the newest commit
that touched terms.html, and the list is the subjects of the newest few such commits. Like
generate-last-updated.py there is no CI; run it by hand AFTER committing a change to terms.html
(the date is the committed one, so running it before the commit shows the previous change):

    python3 scripts/generate-terms-meta.py          # rewrite terms-meta.json
    python3 scripts/generate-terms-meta.py --check  # exit 1 if terms-meta.json is out of date

terms.html falls back to its own printed line when terms-meta.json is missing or unreadable.
Commit subjects are shown as written, so a commit that touches terms.html should have a subject
a visitor can read. Only the page's own history is used; nothing else is read or sent anywhere.
"""
import json
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
PAGE = "terms.html"
OUTPUT_PATH = REPO_ROOT / "terms-meta.json"
MAX_CHANGES = 6
SEPARATOR = "\t"


def parse_log(text: str, limit: int = MAX_CHANGES) -> List[dict]:
    """Turn `git log --format=%cs<TAB>%s` output into [{"date", "subject"}], newest first."""
    changes = []
    for line in text.splitlines():
        day, _, subject = line.partition(SEPARATOR)
        day, subject = day.strip(), subject.strip()
        if len(day) != 10 or not subject:
            continue
        changes.append({"date": day, "subject": subject})
        if len(changes) == limit:
            break
    return changes


def build_meta(changes: List[dict]) -> dict:
    return {
        "file": PAGE,
        "last_changed": changes[0]["date"] if changes else None,
        "changes": changes,
        "generated_by": "scripts/generate-terms-meta.py (from the git history of terms.html)",
    }


def git_log() -> str:
    result = subprocess.run(
        ["git", "log", f"-{MAX_CHANGES}", f"--format=%cs{SEPARATOR}%s", "--", PAGE],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def load_existing() -> Optional[dict]:
    try:
        return json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def main(argv: List[str]) -> int:
    meta = build_meta(parse_log(git_log()))
    if meta["last_changed"] is None:
        print(f"{PAGE} has no commits yet; nothing written.")
        return 1
    if "--check" in argv:
        existing = load_existing() or {}
        same = existing.get("last_changed") == meta["last_changed"] and existing.get("changes") == meta["changes"]
        print("terms-meta.json is up to date." if same else "terms-meta.json is out of date: run scripts/generate-terms-meta.py")
        return 0 if same else 1
    OUTPUT_PATH.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH.name}: last changed {meta['last_changed']}, {len(meta['changes'])} changes listed.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
