#!/usr/bin/env python3
"""Add a game's new runtime files to sw.js's precache list (used after splitting a game's big files).

    python3 scripts/sw-precache-game.py thaw           # add what is missing, bump SW_VERSION once if anything changed
    python3 scripts/sw-precache-game.py thaw --check   # exit 1 if something is missing (changes nothing)

Runtime files are the .py, .js and .css files directly in games/<slug>/ (not tests/, tools/, data/ or the generated
pc.* files, which sw.js lists in its own Desktop block). They go right after the game's "games/<slug>/game.py" line.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SW = ROOT / "sw.js"
SKIP = {"conftest.py", "requirements-dev.txt", "harness.py"}


def runtime_files(slug):
    out = []
    for p in sorted((ROOT / "games" / slug).iterdir()):
        if not p.is_file() or p.suffix not in {".py", ".js", ".css"} or p.name in SKIP:
            continue
        if p.name.startswith("pc.") or p.name.startswith("test_") or p.name.startswith("layout-pref"):
            continue
        out.append(f"games/{slug}/{p.name}")
    return out


def main():
    slug = next(a for a in sys.argv[1:] if not a.startswith("--"))
    check = "--check" in sys.argv
    text = SW.read_text(encoding="utf-8")
    listed = set(re.findall(r'^\s*"(games/%s/[^"]+)",' % re.escape(slug), text, re.M))
    missing = [f for f in runtime_files(slug) if f not in listed]
    if check:
        for f in missing:
            print("missing from sw.js:", f)
        sys.exit(1 if missing else 0)
    if not missing:
        print("nothing to add")
        return
    anchor = re.search(r'^(\s*)"games/%s/game\.py",\n' % re.escape(slug), text, re.M)
    if not anchor:
        sys.exit(f"no games/{slug}/game.py line in sw.js to anchor on. Continuum, for one, is NOT precached beyond its index, "
                 "style and peers files (its engine files are runtime-cached): add the new stylesheet parts by hand.")
    block = "".join(f'{anchor.group(1)}"{f}",\n' for f in missing)
    text = text[: anchor.end()] + block + text[anchor.end():]
    text = re.sub(r"const SW_VERSION = (\d+);", lambda m: f"const SW_VERSION = {int(m.group(1)) + 1};", text, count=1)
    SW.write_text(text, encoding="utf-8")
    print(f"added {len(missing)} files, SW_VERSION bumped")


if __name__ == "__main__":
    main()
