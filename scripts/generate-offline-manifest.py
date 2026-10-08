#!/usr/bin/env python3
"""Regenerate offline-manifest.json (TODO Y-9): the list of files each hub game needs, with sizes.

hub-offline.js reads this file to power the per-card "Download for offline" button. For each game
card on index.html it lists

  * every file in games/<slug>/ that a browser could load (html, css, js, json, py, svg, images,
    fonts), minus tests, markdown and tooling files;
  * every shared/ (and other site-level) file the game's two pages (index.html and the Desktop boot
    pc.html) reference, followed one level into the shared scripts for the data files they fetch;
  * the Python runtime (Pyodide) files from the CDN the pages point at, and any other CDN script a
    page loads (Continuum's Three.js).

and marks the files that sw.js already precaches (the Remove button must never delete those).

Pyodide and CDN sizes cannot be read from disk. They are the decoded byte counts measured by
downloading each file once (the Cache API stores decoded bodies, so decoded size is what the
cache really costs); keep CDN_SIZES below in step with the version the games load. A CDN file
whose version is not in the table gets "bytes": null and the page then says "size unknown"
instead of guessing.

Usage:  python3 scripts/generate-offline-manifest.py [--check]
--check exits 1 when the committed file lists different files than the repo (sizes may drift; used by scripts/tests).
No git, no network. Run it whenever a game gains or loses files, or sw.js's precache list changes.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "offline-manifest.json"

# Decoded bytes, measured 2026-10-08 (curl --compressed ... | wc -c).
CDN_SIZES = {
    "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js": 14761,
    "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.asm.js": 1229099,
    "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.asm.wasm": 10088051,
    "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/python_stdlib.zip": 2341872,
    "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide-lock.json": 106335,
    "https://cdn.jsdelivr.net/npm/three@0.128.0/build/three.min.js": 603445,
}
PYODIDE_RE = re.compile(r"https://cdn\.jsdelivr\.net/pyodide/(v[\d.]+)/full/pyodide\.js")
PYODIDE_RUNTIME = ["pyodide.js", "pyodide.asm.js", "pyodide.asm.wasm", "python_stdlib.zip", "pyodide-lock.json"]
OTHER_CDN_RE = re.compile(r"https://cdn\.jsdelivr\.net/npm/[A-Za-z0-9@._/-]+\.js")

SERVED_EXT = {".html", ".css", ".js", ".json", ".py", ".svg", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".woff", ".woff2", ".ico"}
SKIP_DIRS = {"tests", "__pycache__", "node_modules", ".pytest_cache"}
SKIP_NAMES = {"requirements-dev.txt", "CLAUDE.md"}
ATTR_RE = re.compile(r"""\b(?:src|href|data-[a-z-]+)\s*=\s*["']([^"'#?]+?)(?:\?[^"']*)?["']""")
STRING_RE = re.compile(r"""["'`]([A-Za-z0-9_./-]+\.(?:json|py|js|css|svg|png|webp|woff2?))["'`]""")
SHARED_STRING_RE = re.compile(r"""["'`]((?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_-]+\.(?:json|py|css))["'`]""")


def hub_slugs():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    slugs = re.findall(r'data-game-slug="([a-z0-9-]+)"', html)
    seen = []
    for s in slugs:
        if s not in seen:
            seen.append(s)
    return seen


def sw_precache():
    text = (ROOT / "sw.js").read_text(encoding="utf-8")
    block = re.search(r"PRECACHE_URLS\s*=\s*\[(.*?)\];", text, re.S)
    urls = set()
    body = "\n".join(l for l in (block.group(1) if block else "").splitlines() if not l.lstrip().startswith("//"))
    for item in re.findall(r"""["']([^"']+)["']""", body):
        item = item[2:] if item.startswith("./") else item
        urls.add(item)
    return urls


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def resolve(base_dir: Path, ref: str):
    if len(ref) > 120 or re.search(r"[\s{}\[\]]", ref) or re.match(r"^[a-z]+:|^//", ref) or ref.startswith("/"):
        return None
    try:
        target = (base_dir / ref).resolve()
        target.relative_to(ROOT)
        return target if target.is_file() else None
    except (ValueError, OSError):
        return None


def walk_game(slug: str):
    base = ROOT / "games" / slug
    out = []
    for path in sorted(base.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SERVED_EXT:
            continue
        parts = set(path.relative_to(base).parts[:-1])
        if parts & SKIP_DIRS or path.name in SKIP_NAMES or path.name.startswith("."):
            continue
        out.append(path)
    return out


def referenced(page: Path):
    """Local files a page references plus CDN urls it loads."""
    text = page.read_text(encoding="utf-8")
    files, cdn = set(), set()
    for ref in ATTR_RE.findall(text) + STRING_RE.findall(text):
        target = resolve(page.parent, ref)
        if target and target.suffix.lower() in SERVED_EXT:
            files.add(target)
    for m in PYODIDE_RE.finditer(text):
        cdn.add(m.group(0))
    for m in OTHER_CDN_RE.finditer(text):
        cdn.add(m.group(0))
    return files, cdn


def shared_followups(path: Path):
    """Data/style files a shared script names (seasonal-events.js -> seasonal-dates.json ...)."""
    out = set()
    if path.suffix != ".js" or "shared" not in path.parts:
        return out
    text = path.read_text(encoding="utf-8")
    for ref in SHARED_STRING_RE.findall(text):
        name = ref.split("/")[-1]
        for candidate in (path.parent / name, ROOT / ref):
            if candidate.is_file() and candidate != path:
                out.add(candidate.resolve())
                break
    return out


def cdn_entries(cdn_urls):
    entries = []
    for url in sorted(cdn_urls):
        m = PYODIDE_RE.fullmatch(url)
        if m:
            base = url[: -len("pyodide.js")]
            for name in PYODIDE_RUNTIME:
                entries.append({"url": base + name, "bytes": CDN_SIZES.get(base + name), "kind": "pyodide"})
        else:
            entries.append({"url": url, "bytes": CDN_SIZES.get(url), "kind": "cdn"})
    return entries


def build():
    precached = sw_precache()
    games = {}
    for slug in hub_slugs():
        game_dir = ROOT / "games" / slug
        if not game_dir.is_dir():
            continue
        files = set(walk_game(slug))
        cdn = set()
        for page_name in ("index.html", "pc.html"):
            page = game_dir / page_name
            if not page.is_file():
                continue
            refs, urls = referenced(page)
            files |= refs
            cdn |= urls
        for extra in list(files):
            files |= shared_followups(extra)
        # css files pull their own @import / url() siblings in rare cases; none are used today.
        own, shared = [], []
        for path in sorted(files, key=lambda p: rel(p)):
            r = rel(path)
            if not r.startswith(f"games/{slug}/") and (path.suffix == ".html" or path.name == "sw.js"):
                continue  # navigation links and the worker's own registration, not files the game loads
            entry = {"path": r, "bytes": path.stat().st_size, "precached": r in precached}
            (own if r.startswith(f"games/{slug}/") else shared).append(entry)
        runtime = cdn_entries(cdn)
        total_known = sum(e["bytes"] or 0 for e in own + shared + runtime)
        games[slug] = {
            "files": own,
            "shared": shared,
            "cdn": runtime,
            "bytes": total_known,
            "bytes_complete": all(e["bytes"] is not None for e in runtime),
        }
    return {
        "version": 1,
        "_readme": "Generated by scripts/generate-offline-manifest.py (TODO Y-9). Read by hub-offline.js for the per-card Download for offline button: every file a game needs, which of them sw.js already precaches (never removed), and the Python runtime files with their measured decoded sizes. Do not edit by hand.",
        "cdn_sizes_measured": "2026-10-08",
        "games": games,
    }


def main(argv):
    data = build()
    text = json.dumps(data, indent=1, sort_keys=False) + "\n"
    if "--check" in argv:
        # File SIZES drift on every edit and are only a download estimate, so --check compares the
        # file lists, the precached flags and the CDN entries, not the byte counts of local files.
        def shape(d):
            out = json.loads(json.dumps(d))
            for g in out["games"].values():
                for e in g["files"] + g["shared"]:
                    e.pop("bytes", None)
                g.pop("bytes", None)
            return out
        try:
            current = json.loads(OUTPUT.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            current = None
        if current is None or shape(current) != shape(data):
            print("offline-manifest.json is out of date: run python3 scripts/generate-offline-manifest.py")
            return 1
        return 0
    OUTPUT.write_text(text, encoding="utf-8")
    for slug, g in data["games"].items():
        print(f"{slug}: {len(g['files'])} own + {len(g['shared'])} shared files, {len(g['cdn'])} CDN, ~{g['bytes'] / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
