#!/usr/bin/env python3
"""Static boot-cost measurement for every game (TODO LZ-1). No browser, no network, no git: it only
READS the repository, so it is safe to run any time and quick (well under a second).

For each `games/<slug>/index.html` it works out what the page pulls in when it boots and how big
that is, so the main session can choose where the lazy content packs (shared/lazy-packs.js, LZ-2)
should be cut:

  * the page itself (index.html bytes, how much of that is inline script/style), its own
    stylesheet and the game's own script files (app.js, ui.js, ...);
  * every Python module the page writes into Pyodide's file system (found from the page's and the
    game scripts' string literals: ENGINE_MODULES-style lists, `fetch("x.py")` lines), with line
    and byte counts, game.py singled out;
  * every JSON data file fetched at boot (levels, catalogues, content, achievements, changelog);
  * shared/ files the page includes (scripts, styles, shared Python modules);
  * scripts loaded from a CDN other than Pyodide (listed, not sized);
  * packs that a `modules.json` already defers (subtracted from the boot figures, listed apart);
  * the biggest candidates for a lazy pack: Python modules and JSON files, grouped by family
    (rooms_*.py, cases_3.py, story_2.py ... share a family) so a whole level set shows up as one
    line with a total.

How a reference is found: any quoted string ending in .py/.json/.js/.css in the page or the game's
own scripts that names a real file, looked up relative to the game folder first and the repo's
shared/ folder second (so `"seed.py"` in a list that is fetched from ../../shared/ is still
found). It can over-count a file that is only named in a comment or fetched later than boot; the
table says "referenced", not "proven fetched at boot". A live check of the real transfer is the
job of scripts/measure-perf.py.

Usage:
    python3 scripts/measure-boot-cost.py                 # sorted table, heaviest first
    python3 scripts/measure-boot-cost.py continuum tide  # only these games
    python3 scripts/measure-boot-cost.py --json          # machine-readable JSON on stdout
    python3 scripts/measure-boot-cost.py --detail        # also print each game's candidate packs
    python3 scripts/measure-boot-cost.py --top 8         # candidates per game in --detail/--json (default 12)

`wire_kb` is an estimate of the compressed transfer (zlib level 6 over every counted file); the real
host gzips text, so it lands close. Pyodide itself (about 14 MB decoded, cached by the service
worker in its own cache) is NOT in these figures: it is the same for every game.
"""
import gzip
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GAMES = ROOT / "games"
SHARED = ROOT / "shared"

STRING_RE = re.compile(r"""["'`]([A-Za-z0-9_./-]+\.(?:py|json|js|css))["'`]""")
SCRIPT_RE = re.compile(r"""<script\b[^>]*?\bsrc\s*=\s*["']([^"']+)["']""", re.I)
LINK_RE = re.compile(r"""<link\b[^>]*?\bhref\s*=\s*["']([^"']+)["']""", re.I)
INLINE_SCRIPT_RE = re.compile(r"<script\b(?![^>]*\bsrc\s*=)[^>]*>(.*?)</script>", re.I | re.S)
INLINE_STYLE_RE = re.compile(r"<style\b[^>]*>(.*?)</style>", re.I | re.S)
COMMENT_LINE_RE = re.compile(r"^\s*(//|#|\*|/\*)")

# A file is only worth deferring when it is at least this big (bytes).
CANDIDATE_MIN_BYTES = 6 * 1024
# Files every game fetches that are never worth a pack.
ALWAYS_CORE = {"achievements.json", "changelog.json", "game.py", "sources.json", "pc-config.json"}
PLUMBING_WORDS = {"render", "update", "load", "save", "state", "build", "make", "apply", "reset", "show", "hide", "toggle",
                  "click", "handle", "compute", "format", "default", "text", "html", "panel", "button", "view", "display",
                  "list", "count", "data", "game", "player", "with", "from", "into", "that", "this", "value", "item",
                  "name", "label", "total", "current", "refresh", "init", "setup", "start", "stop", "close", "open",
                  "mark", "check", "clear", "draw", "line", "step", "index", "result", "event", "param", "number",
                  "string", "entry", "section", "status", "summary", "select", "choose", "change", "settings"}
SKIP_DIRS = {"tests", "tools", "icons", "__pycache__", "node_modules", ".pytest_cache"}


def gz_len(data: bytes) -> int:
    return len(gzip.compress(data, 6))


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def resolve_ref(ref: str, game_dir: Path):
    """The real file a string literal names, or None. Game folder first, then shared/."""
    if re.match(r"^[a-z]+:|^//", ref) or len(ref) > 120:
        return None
    for base in (game_dir, SHARED):
        try:
            target = (base / ref).resolve()
            target.relative_to(ROOT)
        except (ValueError, OSError):
            continue
        if target.is_file():
            return target
    return None


def strip_comments(text: str) -> str:
    """Drop whole-line comments so a file named only in a comment is not counted."""
    return "\n".join(l for l in text.splitlines() if not COMMENT_LINE_RE.match(l))


def family_of(name: str) -> str:
    """Group files of one family: rooms_loops.py -> rooms, cases_3.py -> cases, story_2.py -> story,
    boards_dock.py -> boards. A file with no family-mate keeps its own name (decided later)."""
    stem = Path(name).stem
    m = re.match(r"^(.*?)(?:_[A-Za-z0-9]+)$", stem)
    return m.group(1) if m else stem


def line_count(path: Path) -> int:
    try:
        return len(path.read_text(encoding="utf-8", errors="replace").splitlines())
    except OSError:
        return 0


def anatomy(path: Path, top: int = 8):
    """Where the bytes of a big single-file game (game.py) sit: the biggest top-level blocks and
    the biggest groups of blocks sharing a name prefix (challenge_*, scenario_*). This is what
    tells us whether a monolith can be cut into packs at all. Empty dict if it does not parse."""
    import ast
    try:
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)
    except (OSError, SyntaxError, ValueError):
        return {}
    lines = text.splitlines(keepends=True)
    blocks, groups, words = [], {}, {}
    for node in tree.body:
        start = getattr(node, "lineno", None)
        end = getattr(node, "end_lineno", None)
        if start is None or end is None:
            continue
        if getattr(node, "decorator_list", None):
            start = min(start, *(d.lineno for d in node.decorator_list))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            name = node.name
            kind = "class" if isinstance(node, ast.ClassDef) else "def"
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            name = ", ".join(t.id for t in targets if isinstance(t, ast.Name)) or "<assign>"
            kind = "data"
        else:
            continue
        size = sum(len(l.encode()) for l in lines[start - 1:end])
        blocks.append({"name": name, "kind": kind, "lines": end - start + 1, "bytes": size})
        prefix = name.lstrip("_").split("_", 1)[0] if "_" in name.lstrip("_") else name.lstrip("_")
        g = groups.setdefault(prefix, {"prefix": prefix, "blocks": 0, "lines": 0, "bytes": 0})
        g["blocks"] += 1
        g["lines"] += end - start + 1
        g["bytes"] += size
        # Topic words: every word of the name except the plumbing words, so "scenario" gathers
        # scenario_menu, apply_scenario, SCENARIOS... Overlapping on purpose (a block counts under each of its words).
        for word in set(re.split(r"[_\W]+|(?<=[a-z])(?=[A-Z])", name.lower() if "_" in name or name.islower() else name)):
            word = word.lower()
            if len(word) > 4 and word.endswith("s") and not word.endswith(("ss", "us", "is")):
                word = word[:-1]
            if len(word) < 4 or word in PLUMBING_WORDS:
                continue
            w = words.setdefault(word, {"word": word, "blocks": 0, "bytes": 0})
            w["blocks"] += 1
            w["bytes"] += size
    data_bytes = sum(b["bytes"] for b in blocks if b["kind"] == "data")
    blocks.sort(key=lambda b: -b["bytes"])
    glist = sorted((g for g in groups.values() if g["blocks"] > 1), key=lambda g: -g["bytes"])
    wlist = sorted((w for w in words.values() if w["blocks"] > 1), key=lambda w: -w["bytes"])
    return {"top_blocks": blocks[:top], "top_prefix_groups": glist[:top], "top_topic_words": wlist[:top + 6],
            "top_level_blocks": len(blocks), "data_constant_bytes": data_bytes}


def load_modules_json(game_dir: Path):
    """Packs a game already defers (shared/lazy-packs.js's modules.json): list of dicts, [] if none."""
    path = game_dir / "modules.json"
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    packs = data.get("packs") if isinstance(data, dict) else data
    return [p for p in packs if isinstance(p, dict) and isinstance(p.get("url"), str)] if isinstance(packs, list) else []


def measure_game(slug: str, top: int = 12):
    game_dir = GAMES / slug
    page = game_dir / "index.html"
    html = page.read_text(encoding="utf-8")
    deferred_paths = set()
    deferred = []
    for pack in load_modules_json(game_dir):
        target = (game_dir / pack["url"]).resolve()
        if target.is_file():
            deferred_paths.add(target)
            deferred.append({"id": pack.get("id"), "path": rel(target), "bytes": target.stat().st_size})

    own_scripts, own_styles, shared_scripts, shared_styles, other_root = [], [], [], [], []
    seen = set()

    def classify_asset(ref: str, kind: str):
        if re.match(r"^[a-z]+:|^//", ref):
            return
        target = (page.parent / ref.split("?")[0].split("#")[0]).resolve()
        try:
            target.relative_to(ROOT)
        except ValueError:
            return
        if not target.is_file() or target in seen:
            return
        seen.add(target)
        entry = {"path": rel(target), "bytes": target.stat().st_size}
        if game_dir in target.parents:
            (own_scripts if kind == "script" else own_styles).append(entry)
        elif SHARED in target.parents:
            (shared_scripts if kind == "script" else shared_styles).append(entry)
        else:
            other_root.append(entry)

    for ref in SCRIPT_RE.findall(html):
        classify_asset(ref, "script")
    for ref in LINK_RE.findall(html):
        if ref.split("?")[0].endswith(".css"):
            classify_asset(ref, "style")

    # Scripts the page loads from a CDN (not counted in the byte figures: the sizes live on the CDN). Pyodide is the
    # same for every game and the ad script is not game content, so both are left out; anything else (Three.js for Continuum) is a lazy-loading candidate.
    cdn_scripts = sorted({u for u in SCRIPT_RE.findall(html) if re.match(r"^https?://", u) and "/pyodide/" not in u and "googlesyndication" not in u})

    inline_script = sum(len(m.encode()) for m in INLINE_SCRIPT_RE.findall(html))
    inline_style = sum(len(m.encode()) for m in INLINE_STYLE_RE.findall(html))

    # Text to search for module/data references: the page and the game's own scripts.
    sources = [("index.html", strip_comments(html))]
    for entry in own_scripts:
        p = ROOT / entry["path"]
        sources.append((p.name, strip_comments(p.read_text(encoding="utf-8", errors="replace"))))

    py_files, json_files, extra_js, extra_css = {}, {}, {}, {}
    for _name, text in sources:
        for ref in STRING_RE.findall(text):
            target = resolve_ref(ref, game_dir)
            if target is None or target == page.resolve():
                continue
            if target in deferred_paths:
                continue
            if target.suffix == ".py":
                py_files[target] = _name
            elif target.suffix == ".json":
                json_files[target] = _name
            elif target.suffix == ".js" and target not in seen:
                extra_js[target] = _name
            elif target.suffix == ".css" and target not in seen:
                extra_css[target] = _name
    # Skip things that are not a game's own data (other games' folders, tools, tests).
    def keep(p: Path):
        if p.name in {"modules.json"}:
            return False
        parts = p.relative_to(ROOT).parts
        if parts[0] == "games" and parts[1] != slug:
            return False
        return not ({"tests", "tools"} & set(parts))

    # A content folder named as a path prefix ("content/" + name, "sets/...") loads every data file in it.
    for sub in sorted(p for p in game_dir.iterdir() if p.is_dir() and p.name not in SKIP_DIRS and not p.name.startswith(".")):
        prefix = re.compile(r"""["'`]""" + re.escape(sub.name) + r"/")
        if any(prefix.search(text) for _n, text in sources):
            for f in sorted(sub.rglob("*")):
                if f.is_file() and f.resolve() not in deferred_paths:
                    if f.suffix == ".json":
                        json_files[f.resolve()] = "folder:" + sub.name
                    elif f.suffix == ".py":
                        py_files[f.resolve()] = "folder:" + sub.name

    py_files = {p: v for p, v in py_files.items() if keep(p)}
    json_files = {p: v for p, v in json_files.items() if keep(p)}
    game_py_path = (game_dir / "game.py").resolve()
    py_files.pop(game_py_path, None)   # game.py is reported on its own line

    def mod_entry(p: Path):
        is_shared = SHARED in p.parents
        return {"path": rel(p), "name": p.name, "bytes": p.stat().st_size, "lines": line_count(p),
                "shared": is_shared, "family": family_of(p.name)}

    py_list = sorted((mod_entry(p) for p in py_files), key=lambda e: -e["bytes"])
    json_list = sorted(({"path": rel(p), "name": p.name, "bytes": p.stat().st_size,
                         "shared": SHARED in p.parents, "family": family_of(p.name)} for p in json_files),
                       key=lambda e: -e["bytes"])

    # Files the page itself loads from the game folder that are scripts referenced by string only (ui.js loaded dynamically).
    for p in extra_js:
        if keep(p):
            (own_scripts if game_dir in p.parents else shared_scripts).append({"path": rel(p), "bytes": p.stat().st_size})
    for p in extra_css:
        if keep(p):
            (own_styles if game_dir in p.parents else shared_styles).append({"path": rel(p), "bytes": p.stat().st_size})

    game_py = game_dir / "game.py"
    own_py = [e for e in py_list if not e["shared"]]
    shared_py = [e for e in py_list if e["shared"]]
    own_json = [e for e in json_list if not e["shared"]]

    # Unreferenced .py files in the game folder (not a boot cost: either lazy already, a test helper or dead).
    referenced = {ROOT / e["path"] for e in py_list}
    unreferenced = sorted(p.name for p in game_dir.glob("*.py") if p not in referenced and p.name != "game.py")

    # Candidate packs: python and json files at least CANDIDATE_MIN_BYTES, grouped by family.
    families = {}
    for e in own_py + own_json:
        if e["name"] in ALWAYS_CORE:
            continue
        kind = "python" if e["name"].endswith(".py") else "json"
        # Content subfolders group by folder name (content/*.json -> content).
        in_subfolder = (ROOT / e["path"]).parent != game_dir
        fam = (ROOT / e["path"]).parent.name if in_subfolder else e["family"]
        key = (kind, fam)
        fam_entry = families.setdefault(key, {"kind": kind, "family": fam, "files": [], "bytes": 0, "lines": 0, "folder": in_subfolder})
        fam_entry["files"].append(e["name"])
        fam_entry["bytes"] += e["bytes"]
        fam_entry["lines"] += e.get("lines", 0)
    candidates = []
    for fam_entry in families.values():
        singles = len(fam_entry["files"]) == 1
        label = fam_entry["files"][0] if singles else (f"{fam_entry['family']}/ ({len(fam_entry['files'])} files)" if fam_entry["folder"] else f"{fam_entry['family']}_* ({len(fam_entry['files'])} files)")
        if fam_entry["bytes"] >= CANDIDATE_MIN_BYTES:
            candidates.append({"candidate": label, "kind": fam_entry["kind"], "bytes": fam_entry["bytes"],
                               "lines": fam_entry["lines"], "files": sorted(fam_entry["files"])})
    candidates.sort(key=lambda c: -c["bytes"])

    # Totals.
    counted_files = [page, *[ROOT / e["path"] for e in own_scripts + own_styles + shared_scripts + shared_styles + other_root],
                     *[ROOT / e["path"] for e in py_list + json_list]]
    counted_unique = {}
    for p in counted_files:
        counted_unique[p.resolve()] = p
    if game_py.is_file():
        counted_unique[game_py.resolve()] = game_py
    total_bytes = sum(p.stat().st_size for p in counted_unique.values())
    wire = sum(gz_len(p.read_bytes()) for p in counted_unique.values())

    result = {
        "slug": slug,
        "index_html_bytes": page.stat().st_size,
        "inline_script_bytes": inline_script,
        "inline_style_bytes": inline_style,
        "game_py_bytes": game_py.stat().st_size if game_py.is_file() else 0,
        "game_py_lines": line_count(game_py) if game_py.is_file() else 0,
        "own_style_bytes": sum(e["bytes"] for e in own_styles),
        "own_script_bytes": sum(e["bytes"] for e in own_scripts),
        "python_modules": len(own_py),
        "python_module_bytes": sum(e["bytes"] for e in own_py),
        "python_module_lines": sum(e["lines"] for e in own_py),
        "shared_python_bytes": sum(e["bytes"] for e in shared_py),
        "json_files": len(own_json),
        "json_bytes": sum(e["bytes"] for e in own_json),
        "shared_script_bytes": sum(e["bytes"] for e in shared_scripts),
        "shared_style_bytes": sum(e["bytes"] for e in shared_styles),
        "shared_json_bytes": sum(e["bytes"] for e in json_list if e["shared"]),
        "shared_files": len(shared_scripts) + len(shared_styles) + len(shared_py),
        "total_bytes": total_bytes,
        "wire_bytes_est": wire,
        "deferred_pack_bytes": sum(d["bytes"] for d in deferred),
        "deferred_packs": deferred,
        "unreferenced_py": unreferenced,
        "python_module_list": own_py,
        "json_list": own_json,
        "own_scripts": own_scripts,
        "candidates": candidates[:top],
        "candidate_bytes": sum(c["bytes"] for c in candidates),
        "cdn_scripts": cdn_scripts,
        "has_pc_html": (game_dir / "pc.html").is_file(),
        "game_py_anatomy": anatomy(game_py, top) if game_py.is_file() else {},
    }
    return result


def game_slugs():
    return sorted(p.parent.name for p in GAMES.glob("*/index.html"))


def kb(n):
    return f"{n / 1024:.0f}" if n >= 10240 else f"{n / 1024:.1f}"


def table(rows):
    cols = [
        ("game", lambda r: r["slug"]),
        ("total KB", lambda r: kb(r["total_bytes"])),
        ("wire KB", lambda r: kb(r["wire_bytes_est"])),
        ("html", lambda r: kb(r["index_html_bytes"])),
        ("game.py KB", lambda r: kb(r["game_py_bytes"])),
        ("game.py lines", lambda r: str(r["game_py_lines"])),
        ("py mods", lambda r: str(r["python_modules"])),
        ("mods KB", lambda r: kb(r["python_module_bytes"])),
        ("json", lambda r: str(r["json_files"])),
        ("json KB", lambda r: kb(r["json_bytes"])),
        ("own js KB", lambda r: kb(r["own_script_bytes"])),
        ("shared KB", lambda r: kb(r["shared_script_bytes"] + r["shared_style_bytes"] + r["shared_python_bytes"] + r["shared_json_bytes"])),
        ("candidates KB", lambda r: kb(r["candidate_bytes"])),
        ("deferred KB", lambda r: kb(r["deferred_pack_bytes"])),
    ]
    widths = [max(len(name), *(len(fn(r)) for r in rows)) for name, fn in cols]
    lines = ["  ".join(name.ljust(w) if i == 0 else name.rjust(w) for i, ((name, _), w) in enumerate(zip(cols, widths)))]
    lines.append("  ".join("-" * w for w in widths))
    for r in rows:
        lines.append("  ".join(fn(r).ljust(w) if i == 0 else fn(r).rjust(w) for i, ((_, fn), w) in enumerate(zip(cols, widths))))
    return "\n".join(lines)


def detail(rows):
    out = []
    for r in rows:
        out.append(f"\n{r['slug']}  (game.py {r['game_py_lines']} lines, {kb(r['game_py_bytes'])} KB; "
                   f"{r['python_modules']} Python modules, {r['json_files']} JSON files)")
        if not r["candidates"]:
            out.append("  no candidate of 6 KB or more")
        for c in r["candidates"]:
            out.append(f"  {kb(c['bytes']):>6} KB  {c['kind']:<6} {c['candidate']}")
        for url in r.get("cdn_scripts", []):
            out.append(f"  (CDN script, not counted above) {url}")
        an = r.get("game_py_anatomy") or {}
        if an and r["game_py_bytes"] >= 100 * 1024:
            out.append(f"  game.py: {an['top_level_blocks']} top-level blocks, {kb(an['data_constant_bytes'])} KB of data constants")
            for b in an["top_blocks"][:6]:
                out.append(f"    {kb(b['bytes']):>6} KB  {b['kind']:<5} {b['name']} ({b['lines']} lines)")
            out.append("    biggest topic words (overlapping): " + ", ".join(f"{w['word']} {kb(w['bytes'])} KB" for w in an["top_topic_words"][:10]))
            out.append("    biggest prefix groups: " + ", ".join(f"{g['prefix']}_* {kb(g['bytes'])} KB" for g in an["top_prefix_groups"][:6]))
    return "\n".join(out)


def main(argv):
    as_json = "--json" in argv
    show_detail = "--detail" in argv
    top = 12
    args = []
    skip = False
    for i, a in enumerate(argv):
        if skip:
            skip = False
            continue
        if a == "--top" and i + 1 < len(argv):
            top = int(argv[i + 1])
            skip = True
        elif not a.startswith("--"):
            args.append(a)
    slugs = args or game_slugs()
    unknown = [s for s in slugs if not (GAMES / s / "index.html").is_file()]
    if unknown:
        print("unknown game(s): " + ", ".join(unknown), file=sys.stderr)
        return 2
    rows = [measure_game(s, top) for s in slugs]
    rows.sort(key=lambda r: -r["total_bytes"])
    if as_json:
        print(json.dumps({"version": 1, "games": rows}, indent=1))
        return 0
    print(table(rows))
    if show_detail:
        print(detail(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
