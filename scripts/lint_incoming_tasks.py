#!/usr/bin/env python3
"""Lint queue lines for the local AI (local-ai/incoming-tasks.txt and the per-game drafts in local-ai/incoming/).

    python3 scripts/lint_incoming_tasks.py local-ai/incoming/grid.txt [more files]   exit 1 if any line breaks a rule

A line is `game | ITEM-ID | files | what to do`. ITEM-ID is a TODO id (R4-GR-3, G-6) or a chain step
`chain:NAME:N` (steps of one item, numbered 1, 2, 3 without gaps; each starts from the previous step's branch).
`# replaces: ID, ID` comment lines above a group name the whole items the steps replace.

Rules (LA-9): the game folder exists; `files` is a comma list of paths relative to games/<game>/ and each exists
unless the what-to-do text says "NEW file"; at most 4 files per step; the text is 40 to 1500 characters; the text
names a test ("test" appears); chain numbers are consecutive per NAME; no step says it touches shared/, sw.js,
app/, scripts/ or local-ai/ (the local AI works in one game folder only).
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FORBIDDEN = re.compile(r"\b(shared/|sw\.js|offline-manifest|app/|scripts/|local-ai/|planning/)")


def lint_lines(lines, label="input"):
    problems, chains = [], {}
    for n, line in enumerate(lines, 1):
        raw = line.rstrip("\n")
        if not raw.strip() or raw.startswith("#"):
            continue
        parts = [p.strip() for p in raw.split("|", 3)]
        where = f"{label}:{n}"
        if len(parts) != 4:
            problems.append(f"{where}: needs 4 fields: game | ITEM | files | what to do")
            continue
        game, item, files, text = parts
        gdir = ROOT / "games" / game
        if not gdir.is_dir():
            problems.append(f"{where}: no game folder games/{game}")
            continue
        m = re.fullmatch(r"chain:([A-Za-z0-9-]+):(\d+)", item)
        if m:
            chains.setdefault(m.group(1), []).append(int(m.group(2)))
        elif not re.fullmatch(r"[A-Z0-9][A-Z0-9-]*[A-Z0-9]", item):
            problems.append(f"{where}: bad ITEM id {item!r}")
        flist = [f.strip() for f in files.split(",") if f.strip()]
        if len(flist) > 4:
            problems.append(f"{where}: {len(flist)} files (at most 4 per step)")
        for f in flist:
            if not (gdir / f).exists() and "new file" not in text.lower():
                problems.append(f"{where}: {f} does not exist in games/{game} (say 'NEW file' in the text if the step creates it)")
        if not 40 <= len(text) <= 1500:
            problems.append(f"{where}: text is {len(text)} characters (40 to 1500)")
        if "test" not in text.lower():
            problems.append(f"{where}: the step must name the test that proves it")
        if FORBIDDEN.search(text) or any(FORBIDDEN.search(f) for f in flist):
            problems.append(f"{where}: touches files outside the game folder")
    for name, nums in chains.items():
        if sorted(nums) != list(range(1, len(nums) + 1)):
            problems.append(f"{label}: chain {name} steps are {sorted(nums)}, expected 1..{len(nums)}")
    return problems


def main(argv):
    paths = [Path(a) for a in argv if not a.startswith("--")]
    if not paths:
        sys.exit(__doc__)
    bad = []
    for p in paths:
        bad += lint_lines(p.read_text(encoding="utf-8-sig").splitlines(), p.as_posix())
    for b in bad:
        print(b)
    print(f"{len(bad)} problem(s)")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main(sys.argv[1:])
