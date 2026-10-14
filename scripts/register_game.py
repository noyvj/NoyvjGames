"""Register a finished game on the hub in one command (the "register in the hub" TODO items).

    python3 scripts/register_game.py <slug>             make every hub change, run the generators and the hub tests
    python3 scripts/register_game.py <slug> --dry-run   only list what would change

The game's own design choices live in games/<slug>/register.json (written with the game, so the local AI
can do it); everything else is mechanical and done here, following the Evidence Hunt registration
(eaeb33e2) step by step. Every step is idempotent: a game already present in a file is left alone.

register.json:
    {
      "name": "Zero-G Shift",                       # title card, menus, labels
      "working_title": true,                        # adds "(working title)" in the root CLAUDE.md table
      "blurb": "One or two sentences for the title card.",
      "tags": ["puzzle"],                           # data-tags on the title card (the hub's tag ids)
      "tag_labels": ["Puzzle"],                     # the pills shown on the card
      "glow": "#7fd1ff", "bg": ["#14223a", "#0a1020"],   # thumbnail and share-card colours
      "status": "All 7 folder milestones complete: ...",  # the root CLAUDE.md "Current games" row
      "smoke_actions": [{"action": "reset"}, {"action": "open", "level": 1}],   # requests the smoke fuzzer may send
      "smoke_steps": 300
    }
"""
import json
import re
import shutil
import socket
import subprocess
import sys
import threading
import http.server
import functools
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
changes = []


def rel(path):
    return path.relative_to(ROOT).as_posix()


def read(path):
    return path.read_text(encoding="utf-8")


def write(path, text, what, dry):
    changes.append(f"{rel(path)}: {what}")
    if not dry:
        newline = "\r\n" if b"\r\n" in path.read_bytes() else "\n"
        path.write_bytes(text.replace("\r\n", "\n").replace("\n", newline).encode("utf-8"))


def insert_after_line(text, needle, new_line, path):
    """Insert new_line (same indentation as the anchor) after the LAST line containing needle."""
    lines = text.split("\n")
    idx = max((i for i, ln in enumerate(lines) if needle in ln), default=None)
    if idx is None:
        raise SystemExit(f"{rel(path)}: anchor not found: {needle!r}")
    indent = re.match(r"\s*", lines[idx]).group(0)
    lines.insert(idx + 1, indent + new_line.lstrip())
    return "\n".join(lines)


def last_registered():
    ids = re.search(r"const FALLBACK_IDS = \[(.*?)\];", read(ROOT / "achievements.html"), re.S).group(1)
    return re.findall(r'"([a-z0-9-]+)"', ids)


def game_files(slug):
    """What the service worker precaches for the game: its page, code and data, minus tests, tools and lazy packs."""
    gdir = ROOT / "games" / slug
    packs = set()
    if (gdir / "modules.json").exists():
        packs = {p["url"] for p in json.loads(read(gdir / "modules.json")).get("packs", [])}
    first = [n for n in ("index.html", "style.css", "game.py", "app.js", "settings.js", "changelog.json", "achievements.json")
             if (gdir / n).exists()]
    py = sorted(p.name for p in gdir.glob("*.py") if p.name not in first and p.name not in packs)
    data = sorted(p.name for p in gdir.glob("*.json") if p.name not in first and p.name not in packs
                  and p.name not in ("register.json", "pc-config.json"))
    pc = [n for n in ("pc.html", "pc.css", "pc.js") if (gdir / n).exists()]
    return [f"games/{slug}/{n}" for n in first + py + data + pc]


def bump_counts(text, old, new, patterns):
    for pat in patterns:
        text = re.sub(pat.format(n=old), lambda m: m.group(0).replace(str(old), str(new)), text)
    return text


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def run(cmd, label):
    print(f"--- {label}")
    out = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    tail = (out.stdout + out.stderr).strip().splitlines()[-3:]
    for t in tail:
        print("    " + t[:200])
    return out.returncode == 0


def main(argv):
    if not argv or argv[0].startswith("-"):
        print(__doc__)
        return 2
    slug, dry = argv[0], "--dry-run" in argv
    gdir = ROOT / "games" / slug
    cfg_path = gdir / "register.json"
    if not gdir.is_dir():
        raise SystemExit(f"no game folder games/{slug}")
    if not cfg_path.exists():
        raise SystemExit(f"write games/{slug}/register.json first (see this script's docstring)")
    cfg = json.loads(read(cfg_path))
    name, glow, bg = cfg["name"], cfg["glow"], cfg["bg"]
    ids = last_registered()
    if slug in ids:
        print(f"{slug} is already in achievements.html FALLBACK_IDS; continuing to fill any gaps")
        ids = [i for i in ids if i != slug]
    last = ids[-1]
    names = dict(re.findall(r'"([a-z0-9-]+)": "([^"]+)",', read(ROOT / "profile.js")))
    last_name = names.get(last, last)
    count_old = len(ids)
    count_new = count_old + 1

    # 1. index.html: counts, the menu link and the title card
    p = ROOT / "index.html"
    t = read(p)
    if f'href="games/{slug}/index.html"' not in t:
        t = re.sub(rf"\b{count_old}( small AI-assisted game demos)", rf"{count_new}\1", t)
        t = insert_after_line(t, f'<li><a href="games/{last}/index.html">', f'<li><a href="games/{slug}/index.html">{name}</a></li>', p)
        pills = "".join(f'<span class="tag-pill">{lab}</span>' for lab in cfg.get("tag_labels", []))
        stars = "\n".join(f'          <button type="button" class="star" data-value="{v}">&#9733;</button>' for v in range(1, 6))
        card = (f'    <article class="title-card" data-tags="{" ".join(cfg.get("tags", []))}">\n'
                f'      <a class="title-card-link" href="games/{slug}/index.html">\n'
                f'        <div class="title-card-thumb title-card-thumb--{slug}"></div>\n'
                f'        <h2 class="title-card-name">{name}</h2>\n'
                f'        <p class="title-card-blurb">{cfg["blurb"]}</p>\n'
                f'        <div class="title-card-tags">{pills}</div>\n'
                f'      </a>\n\n'
                f'      <div class="review-widget" data-game-slug="{slug}">\n'
                f'        <p class="ratings-summary is-loading" aria-busy="true">Loading reviews&hellip;</p>\n'
                f'        <div class="star-rating" data-rating="0">\n{stars}\n        </div>\n'
                f'        <textarea class="comment-box" placeholder="Leave a comment..."></textarea>\n'
                f'        <button type="button" class="comment-submit">Submit</button>\n'
                f'      </div>\n'
                f'    </article>\n')
        anchor = t.index(f'<div class="review-widget" data-game-slug="{last}">')
        end = t.index("</article>", anchor) + len("</article>\n")
        t = t[:end] + "\n" + card + t[end:]
        write(p, t, f"games {count_old} -> {count_new}, menu link, title card", dry)

    # 2. style.css: the title-card thumbnail
    p = ROOT / "style.css"
    t = read(p)
    if f".title-card-thumb--{slug}" not in t:
        initial = name[0].upper()
        block = (f"\n/* {name}: registered by scripts/register_game.py; colours from games/{slug}/register.json. */\n"
                 f".title-card-thumb--{slug} {{\n  --thumb-glow: {glow};\n"
                 f"  background: radial-gradient(circle at 50% 45%, {glow}33 0 30%, transparent 31%), linear-gradient(160deg, {bg[0]} 0%, {bg[1]} 100%);\n}}\n"
                 f".title-card-thumb--{slug}::before {{\n  content: \"{initial}\";\n  inset: 50% auto auto 50%;\n"
                 f"  transform: translate(-50%, -50%);\n  font: 700 44px/1 system-ui, sans-serif;\n  color: {glow};\n}}\n")
        write(p, t.rstrip("\n") + "\n" + block, "thumbnail", dry)

    # 3-7. the hub's lists and name maps
    p = ROOT / "achievements.html"
    t = read(p)
    if f'"{slug}"' not in t:
        t = t.replace(f'"{last}"]', f'"{last}", "{slug}"]', 1)
        t = insert_after_line(t, f'"{last}": "{last_name}",', f'"{slug}": "{name}",', p)
        write(p, t, "FALLBACK_IDS and label", dry)
    p = ROOT / "admin.html"
    t = read(p)
    if f'"{slug}"' not in t:
        t = insert_after_line(t, f'  "{last}",', f'"{slug}",', p)
        t = insert_after_line(t, f'"{last}": "{last_name}",', f'"{slug}": "{name}",', p)
        write(p, t, "game list and label", dry)
    p = ROOT / "profile.js"
    t = read(p)
    if f'"{slug}"' not in t:
        write(p, insert_after_line(t, f'"{last}": "{last_name}",', f'"{slug}": "{name}",', p), "label", dry)
    p = ROOT / "script.js"
    t = read(p)
    if f'"{slug}"' not in t:
        t = re.sub(rf'"{re.escape(last)}",(\s*\n\s*\])', rf'"{last}", "{slug}",\1', t, count=1) if re.search(rf'"{re.escape(last)}",\s*\n\s*\]', t) \
            else t.replace(f'"{last}",\n', f'"{last}", "{slug}",\n', 1)
        t = insert_after_line(t, f'"{last}": "{last_name}",', f'"{slug}": "{name}",', p)
        write(p, t, "game list and label", dry)
    p = ROOT / "shared" / "site-settings.js"
    t = read(p)
    if f'"{slug}"' not in t:
        write(p, insert_after_line(t, f'"{last}": {{ scale:', f'"{slug}": {{ scale: "{slug}-text-scale", motion: "{slug}-reduced-motion" }},', p),
              "settings keys", dry)

    # 8. service worker: precache the game, bump the version
    p = ROOT / "sw.js"
    t = read(p)
    if f'"games/{slug}/index.html"' not in t:
        lines = t.split("\n")
        at = max(i for i, ln in enumerate(lines) if f'"games/{last}/' in ln)
        indent = re.match(r"\s*", lines[at]).group(0)
        existing = set(ln.strip().strip(",").strip('"') for ln in lines)
        new = [indent + f'"{f}",' for f in game_files(slug) if f not in existing]
        lines[at + 1:at + 1] = new
        t = "\n".join(lines)
        t = re.sub(r"const SW_VERSION = (\d+);", lambda m: f"const SW_VERSION = {int(m.group(1)) + 1};", t, count=1)
        write(p, t, f"precache {len(game_files(slug))} files, SW_VERSION + 1", dry)

    # 9. root CLAUDE.md: the Current games row
    p = ROOT / "CLAUDE.md"
    t = read(p)
    if f"| {slug} |" not in t:
        title = name + (" (working title)" if cfg.get("working_title") else "")
        row = f"| {slug} | {title} | {cfg.get('status', 'Registered on the hub')}. Hub-linked, no BCM tag |"
        write(p, insert_after_line(t, f"| {last} |", row, p), "Current games row", dry)

    # 10. share cards: the game's theme (its initial on its colours)
    p = ROOT / "scripts" / "generate-share-cards.py"
    t = read(p)
    if f'"{slug}":' not in t:
        theme = f'"{slug}": (["{bg[0]}", "{bg[1]}"], "stars", "{glow}", "#141a24", ("letter", "{name[0].upper()}", "#ffffff")),'
        write(p, insert_after_line(t, f'    "{last}": ([', theme, p), "share-card theme", dry)

    # 11. hub tests that count the games
    for rp, pats in {
        "scripts/tests/test_hub_shell.py": [r"len\(linked\) == {n}\b"],
        "scripts/tests/test_seo_share_events.py": [r"len\(slugs\) == {n}\b"],
        "scripts/tests/test_hub_regressions_browser.py": [r"length === {n}\b"],
        "scripts/tests/test_hub_today_foryou_offline_shell.py": [
            r"\.offline-button'\)\.length >= {n}\b", r"1 of {n} games downloaded",
            r"filter\(c => !c\.hidden\)\.length\"\) == {n}\b"],
    }.items():
        p = ROOT / rp
        t = read(p)
        t2 = bump_counts(t, count_old, count_new, pats)
        if rp.endswith("regressions_browser.py") and f'"{slug}"' not in t2:
            t2 = t2.replace(f'"{last}")', f'"{last}", "{slug}")', 1)
        if t2 != t:
            write(p, t2, f"game count {count_old} -> {count_new}", dry)

    # 12. smoke fuzzer: the game joins the engine games with a request generator from register.json
    p = ROOT / "shared" / "tests" / "smoke_support.py"
    t = read(p)
    fn = slug.replace("-", "_") + "_request"
    if f'"{slug}"' not in t.split("ENGINE_GAMES = [")[1].split("]")[0]:
        actions = json.dumps(cfg.get("smoke_actions") or [{"action": "reset"}])
        func = (f"def {fn}(rng, last):\n"
                f"    \"\"\"{name}: one of the requests listed in games/{slug}/register.json (scripts/register_game.py).\"\"\"\n"
                f"    return dict(rng.choice({actions}))\n\n\n")
        t = t.replace("# Which games the harness drives how", func + "# Which games the harness drives how", 1)
        branch = (f'        elif slug == "{slug}":\n'
                  f'            load_conftest(slug)\n'
                  f'            import game as module                    # noqa: PLC0415 -- resolved through that path\n'
                  f'            module.handle(json.dumps({{"action": "reset"}}))\n'
                  f'            yield (lambda req: json.loads(module.handle(json.dumps(req)))), module.get_state, {fn}\n')
        t = t.replace("        else:\n            raise KeyError(slug)", branch + "        else:\n            raise KeyError(slug)", 1)
        t = re.sub(r'(ENGINE_GAMES = \[[^\]]*)\]', lambda m: m.group(1) + f', "{slug}"]', t, count=1)
        write(p, t, "smoke harness: engine game + request generator", dry)
    p = ROOT / "shared" / "tests" / "test_smoke_everything.py"
    t = read(p)
    if f'"{slug}":' not in t:
        steps = int(cfg.get("smoke_steps", 300))
        t = re.sub(r'(STEPS = \{.*?)(\})', lambda m: m.group(1).rstrip() + f', "{slug}": {steps}' + m.group(2), t, count=1, flags=re.S)
        write(p, t, "smoke steps", dry)

    # 13. favicon: the game's own SVG, its initial on its colours
    icon = ROOT / "icons" / f"favicon-{slug}.svg"
    if not icon.exists():
        changes.append(f"{rel(icon)}: created")
        if not dry:
            icon.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="{bg[0]}"/>'
                            f'<text x="32" y="44" font-family="system-ui,sans-serif" font-size="34" font-weight="700" fill="{glow}" '
                            f'text-anchor="middle">{name[0].upper()}</text></svg>\n', encoding="utf-8")
    for page in ("index.html", "pc.html"):
        gp = gdir / page
        if gp.exists() and f'href="icons/favicon-{slug}.svg"' in read(gp):
            write(gp, read(gp).replace(f'href="icons/favicon-{slug}.svg"', f'href="../../icons/favicon-{slug}.svg"'), "favicon path", dry)

    print("\n".join(["Changes:"] + ["  " + c for c in changes] or ["  (none: already registered)"]))
    if dry:
        return 0

    # 14. the generated files, then the hub's own checks
    ok = True
    ok &= run([PY, "scripts/generate-last-updated.py"], "game-last-updated / game-manifest / game-added")
    ok &= run([PY, "scripts/generate-roadmap-data.py"], "roadmap data")
    ok &= run([PY, "scripts/generate-seo.py"], "sitemap, robots, JSON-LD, meta")
    ok &= run([PY, "scripts/generate-share-cards.py"], "share cards")
    ok &= run([PY, "scripts/generate-save-fixtures.py", slug], "save fixtures")
    ok &= run([PY, "scripts/generate-offline-manifest.py"], "offline manifest")
    port = free_port()
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT)))
    server.RequestHandlerClass.log_message = lambda *a: None
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        ok &= run([PY, "scripts/measure-perf.py", slug, "--base", f"http://127.0.0.1:{port}"], "performance budget")
    finally:
        server.shutdown()
    ok &= run([PY, "-m", "pytest", "-q", "-p", "no:cacheprovider", "scripts/tests"], "hub tests")
    ok &= run([PY, "-m", "pytest", "-q", "-p", "no:cacheprovider", "shared/tests/test_smoke_everything.py", "-k", slug], "smoke tests for the game")
    print("\nRegistered." if ok else "\nRegistered, but a step above failed: fix it before committing.")
    if shutil.which("git"):
        print("Changed files:\n" + subprocess.run(["git", "status", "--short"], cwd=ROOT, capture_output=True, text=True).stdout)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
