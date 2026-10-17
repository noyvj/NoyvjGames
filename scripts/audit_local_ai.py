#!/usr/bin/env python3
"""The default way to audit the local AI's work, cheapest checks first.

    python3 scripts/audit_local_ai.py intake                 what is waiting (read-only, after a fetch)
    python3 scripts/audit_local_ai.py prepare <slug>         audit branch + worktree, cherry-pick, automatic gates
    python3 scripts/audit_local_ai.py live <slug>            one generic browser pass on the audit worktree
    python3 scripts/audit_local_ai.py finish <slug> --accepted R4-AB-1,R4-AB-2 [--partial R4-AB-3] [--delete-remote]
    python3 scripts/audit_local_ai.py --self-test            not needed: the tests are in scripts/tests

The order is the point (see local-ai/AUDIT.md): everything that costs no model time runs first and decides what
the reviewer has to read; the browser is opened once per game, at the end, for the survivors.

  intake    (free)   fetch --prune, list unmerged local-ai/* branches, de-duplicate stacked branches into the
                     list of idea commits, say which are tooling-only, already ticked, or out of scope
  prepare   (free)   worktree .claude/worktrees/audit-<slug> on branch audit/<slug> from main, cherry-pick the
                     game's commits one by one, after EACH run local-ai/static_check.py (only new findings count)
                     and a scope check, then the game's pytest + flake8 + pc-page check and the list of new files
                     the pages load that sw.js does not precache. Prints a report for the reviewer
  (review)  (tokens) the reviewer reads only the flagged diffs, fixes small things, reverts what is not small
  live      (cheap)  one headless pass over index.html and pc.html at 1440x900 and 360x740: page errors, console
                     errors, horizontal overflow, ids added by the diff present, small tap targets
  finish    (free)   merge the audit branch, add missing precache entries to sw.js, regenerate the offline
                     manifest, tick the accepted ids in planning/TODO-NEXT.md, commit, remove the worktree and
                     branch, and (with --delete-remote) delete the remote branches whose idea commits are all handled
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("NOYVJ_ROOT") or Path(__file__).resolve().parent.parent)
IDEA = re.compile(r"^local-ai: (R4-[A-Z]+-\d+|[A-Z]{1,4}-\d+[a-z]?\d*)\b")
TOOLING_PATHS = ("local-ai/", "BCM206-DEV-LOG.md", "BCM114-DEV-LOG.md")
LOCAL_REF = re.compile(r"""(?:src|href)=["']([^"'#?:]+\.(?:js|css|py|json|svg))["']""")
GH = ["git", "-c", "credential.helper=!gh auth git-credential"]


def git(*args, cwd=None, check=True):
    result = subprocess.run(["git", *args], cwd=cwd or ROOT, capture_output=True, text=True)
    if check and result.returncode:
        raise SystemExit("git %s failed: %s" % (" ".join(args), result.stderr.strip()))
    return result.stdout


def run(cmd, cwd=None, env=None, timeout=900):
    full_env = dict(os.environ, **(env or {}))
    r = subprocess.run(cmd, cwd=cwd or ROOT, capture_output=True, text=True, env=full_env, timeout=timeout)
    return r.returncode, (r.stdout + r.stderr)


# ---------------------------------------------------------------- pure helpers (tested in scripts/tests)

def parse_subject(subject):
    """'local-ai: R4-LHMO-9: Round 4 idea ...' -> 'R4-LHMO-9'; tooling and merge subjects -> None."""
    m = IDEA.match(subject)
    return m.group(1) if m else None


def game_of(paths):
    """The single games/<slug>/ a commit touches, '' if none, '*' if several."""
    slugs = {p.split("/")[1] for p in paths if p.startswith("games/") and p.count("/") >= 2}
    if not slugs:
        return ""
    return slugs.pop() if len(slugs) == 1 else "*"


def outside_scope(paths, slug):
    return [p for p in paths if not p.startswith("games/%s/" % slug)]


def is_tooling(paths):
    return bool(paths) and all(p.startswith(TOOLING_PATHS) for p in paths)


def ticked_ids(todo_text):
    return set(re.findall(r"^\s*- \[x\] (R4-[A-Z]+-\d+):", todo_text, re.M))


def missing_precache(html_text, slug, sw_text, exists):
    """Files a game page loads that sw.js does not list. `exists(path)` says whether the repo has the file."""
    missing = []
    for ref in LOCAL_REF.findall(html_text):
        if ref.startswith("http") or ref.startswith("//"):
            continue
        parts = []
        for piece in ("games/%s/%s" % (slug, ref)).split("/"):
            if piece == "..":
                if parts:
                    parts.pop()
            elif piece and piece != ".":
                parts.append(piece)
        path = "/".join(parts)
        if not path.startswith("games/%s/" % slug):
            continue   # shared and hub files are covered by the offline manifest, which `finish` regenerates
        if path.endswith("index.html") or path.endswith("pc.html"):
            continue
        if exists(path) and ('"%s"' % path) not in sw_text and path not in missing:
            missing.append(path)
    return missing


def new_findings(after_lines, before_lines):
    before = {re.sub(r":\d+ ", " ", line) for line in before_lines}
    return [line for line in after_lines if re.sub(r":\d+ ", " ", line) not in before and "no findings" not in line]


# ---------------------------------------------------------------- intake

def collect_ideas():
    """Idea commits (oldest first) on unmerged local-ai/* branches, de-duplicated by sha."""
    branches = [b.strip() for b in git("branch", "-r").splitlines() if "/local-ai/" in b]
    seen, ideas, tooling = {}, [], []
    for branch in branches:
        for line in git("log", "--no-merges", "--reverse", "--format=%H|%ct|%s", "main.." + branch).splitlines():
            sha, stamp, subject = line.split("|", 2)
            if sha in seen:
                seen[sha]["branches"].append(branch)
                continue
            paths = git("show", "--name-only", "--format=", sha).split()
            item = {"sha": sha, "short": sha[:8], "subject": subject, "id": parse_subject(subject), "paths": paths, "time": int(stamp),
                    "game": game_of(paths), "branches": [branch]}
            seen[sha] = item
            (ideas if item["id"] else tooling).append(item)
    ideas.sort(key=lambda i: i["time"])
    tooling.sort(key=lambda i: i["time"])
    return branches, ideas, tooling


def cmd_intake(_args):
    git("fetch", "-q", "--prune")
    branches, ideas, tooling = collect_ideas()
    done = ticked_ids((ROOT / "planning" / "TODO-NEXT.md").read_text())
    by_game = {}
    for item in ideas:
        by_game.setdefault(item["game"] or "(none)", []).append(item)
    print("remote local-ai branches: %d; idea commits waiting: %d; tooling commits: %d\n" % (len(branches), len(ideas), len(tooling)))
    for game in sorted(by_game):
        print("== %s" % game)
        for item in by_game[game]:
            notes = []
            if item["id"] in done:
                notes.append("ID ALREADY TICKED (duplicate or re-run)")
            bad = outside_scope(item["paths"], game) if game not in ("", "*") else item["paths"]
            if bad:
                notes.append("OUTSIDE GAME FOLDER: " + ", ".join(bad[:3]))
            print("  %s %s%s" % (item["short"], item["id"], ("   <- " + "; ".join(notes)) if notes else ""))
    if tooling:
        print("\ntooling commits (should only touch local-ai/ and the dev logs):")
        for item in tooling:
            flag = "ok" if is_tooling(item["paths"]) else "TOUCHES: " + ", ".join(p for p in item["paths"] if not p.startswith(TOOLING_PATHS))[:120]
            print("  %s %s  [%s]" % (item["short"], item["subject"][:70], flag))
    print("\nnext: prepare <slug> for each game above (one agent per game, never two on the same game).")
    return 0


# ---------------------------------------------------------------- prepare

def worktree_path(slug):
    return ROOT / ".claude" / "worktrees" / ("audit-" + slug)


def static_lines(slug, root):
    code, out = run([sys.executable, str(ROOT / "local-ai" / "static_check.py"), slug], env={"NOYVJ_ROOT": str(root)})
    return [line for line in out.splitlines() if line.strip()]


def cmd_prepare(args):
    slug = args.slug
    git("fetch", "-q", "--prune")
    _, ideas, _ = collect_ideas()
    commits = [i for i in ideas if i["game"] == slug]
    if not commits:
        print("nothing waiting for %s" % slug)
        return 0
    wt = worktree_path(slug)
    if wt.exists():
        raise SystemExit("%s already exists: finish or remove it first" % wt)
    git("worktree", "add", "-q", "-b", "audit/" + slug, str(wt), "main")
    baseline = static_lines(slug, ROOT)
    print("# Audit report for %s (%d commits)\nworktree: %s   branch: audit/%s\n" % (slug, len(commits), wt, slug))
    for item in commits:
        res = subprocess.run(["git", "cherry-pick", item["sha"]], cwd=wt, capture_output=True, text=True)
        if res.returncode:
            subprocess.run(["git", "cherry-pick", "--abort"], cwd=wt, capture_output=True)
            print("## %s %s: CONFLICT with main, not applied (reviewer decides whether to redo it by hand)" % (item["short"], item["id"]))
            continue
        bad = outside_scope(item["paths"], slug)
        findings = new_findings(static_lines(slug, wt), baseline)
        tests = [p for p in item["paths"] if "/tests/" in p]
        print("## %s %s" % (item["short"], item["id"]))
        print("  files: %s" % ", ".join(p.replace("games/%s/" % slug, "") for p in item["paths"]))
        print("  scope: %s" % ("OUTSIDE FOLDER " + ", ".join(bad) if bad else "ok"))
        print("  tests added: %s" % (", ".join(Path(t).name for t in tests) if tests else "NONE"))
        print("  static findings: %s" % ("none" if not findings else ""))
        for line in findings:
            print("    " + line)
        baseline = baseline + findings
    print("\n## whole-branch gates")
    code, out = run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"], cwd=wt / "games" / slug)
    print("  pytest: %s" % (out.strip().splitlines()[-1] if out.strip() else "no output"))
    code, out = run([sys.executable, "-m", "flake8", "--extend-ignore=E501", "games/" + slug], cwd=wt)
    print("  flake8: %s" % ("clean" if not out.strip() else "\n    " + "\n    ".join(out.strip().splitlines()[:8])))
    code, out = run([sys.executable, "scripts/generate-pc-pages.py", "--check"], cwd=wt)
    print("  pc pages: %s" % ("up to date" if code == 0 else "STALE: regenerate this game's pc.html only (importlib build)"))
    sw = (ROOT / "sw.js").read_text()
    miss = []
    for page in ("index.html", "pc.html"):
        p = wt / "games" / slug / page
        if p.exists():
            miss += missing_precache(p.read_text(), slug, sw, lambda rel: (wt / rel).exists())
    print("  not precached (sw.js): %s" % (", ".join(sorted(set(miss))) if miss else "none"))
    print("\nnext: review the flagged items (fix small, revert big), commit on audit/%s, then `live %s`, then `finish %s`." % (slug, slug, slug))
    return 0


# ---------------------------------------------------------------- live

def live_pass(root, slug, new_ids):
    """One headless pass over index.html and pc.html at desktop and phone size; returns {tag: [problems]}."""
    from playwright.sync_api import sync_playwright
    import functools
    import http.server
    import threading

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a, **k):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(root)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = "http://127.0.0.1:%d/games/%s/" % (server.server_address[1], slug)
    results = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for page_name in ("index.html", "pc.html"):
            for size in ((1440, 900), (360, 740)):
                ctx = browser.new_context(viewport={"width": size[0], "height": size[1]}, service_workers="block")
                page = ctx.new_page()
                errors = []
                page.on("pageerror", lambda e: errors.append("pageerror: %s" % e))
                page.on("console", lambda m: errors.append("console: %s" % m.text) if m.type == "error" else None)
                page.route("**/*", lambda route: route.abort() if not route.request.url.startswith("http://127.0.0.1") and "cdn" not in route.request.url else route.continue_())
                try:
                    page.goto(base + page_name, wait_until="load", timeout=30000)
                    page.wait_for_timeout(4000)
                    for sel in ("#play", "#opening-new-game", "#opening-continue"):
                        if page.locator(sel).count() and page.locator(sel).first.is_visible():
                            page.locator(sel).first.click()
                            page.wait_for_timeout(500)
                            break
                    overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
                    absent = [i for i in sorted(new_ids) if page.locator("#" + i).count() == 0]
                    small = page.evaluate("""() => [...document.querySelectorAll('button, [role=button]')]
                        .filter(b => b.offsetParent && b.getBoundingClientRect().height > 0 && b.getBoundingClientRect().height < 40 && innerWidth < 600).length""")
                except Exception as exc:  # a page that will not load is the finding
                    errors.append("load failed: %s" % exc)
                    overflow, absent, small = 0, [], 0
                errors = [e for e in errors if "fastapicloud" not in e and "adsbygoogle" not in e and "Failed to load resource" not in e and "CORS" not in e]
                status = []
                if errors:
                    status.append("ERRORS %s" % errors[:3])
                if overflow > 0:
                    status.append("horizontal overflow %dpx" % overflow)
                if absent and page_name == "index.html":
                    status.append("ids from the diff not in the page: %s" % absent)
                if small and size[0] < 600:
                    status.append("%d buttons under 40px tall" % small)
                results["%s %dx%d" % (page_name, size[0], size[1])] = status
                ctx.close()
        browser.close()
    server.shutdown()
    return results


def cmd_live(args):
    slug = args.slug
    wt = worktree_path(slug)
    root = wt if wt.exists() else ROOT
    new_ids = set()
    for line in git("diff", "main", "--", "games/%s/index.html" % slug, cwd=root, check=False).splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            new_ids.update(re.findall(r"""\bid=["']([\w-]+)""", line))
    after = live_pass(root, slug, new_ids)
    before = live_pass(ROOT, slug, set()) if root != ROOT else {}
    problems = 0
    for tag, status in after.items():
        base = before.get(tag, [])
        fresh = [s for s in status if s not in base]
        problems += bool(fresh)
        note = "ok" if not status else ("; ".join(fresh) + ("   (same as main: %s)" % "; ".join(s for s in status if s in base) if any(s in base for s in status) else "")) if fresh else "only what main already has: " + "; ".join(status)
        print("%-24s %s" % (tag, note))
    return 1 if problems else 0


# ---------------------------------------------------------------- finish

def tick(todo_path, ids):
    text = todo_path.read_text()
    for rid in ids:
        text, n = re.subn(r"^(\s*)- \[ \] (%s):" % re.escape(rid), r"\1- [x] \2:", text, flags=re.M)
        if not n:
            print("  note: %s not found as an open item (already ticked?)" % rid)
    todo_path.write_text(text)


def cmd_finish(args):
    slug = args.slug
    accepted = [i for i in (args.accepted or "").split(",") if i]
    partial = [i for i in (args.partial or "").split(",") if i]
    wt = worktree_path(slug)
    branch = "audit/" + slug
    if wt.exists() and git("status", "--porcelain", "--untracked-files=no", cwd=wt).strip():
        raise SystemExit("the audit worktree has uncommitted changes: commit or discard them first")
    git("merge", "--no-ff", "-q", "-m", "Merge audited local-ai: %s (audit by Noyvj)" % slug, branch)
    sw_path = ROOT / "sw.js"
    sw = sw_path.read_text()
    miss = []
    for page in ("index.html", "pc.html"):
        p = ROOT / "games" / slug / page
        if p.exists():
            miss += missing_precache(p.read_text(), slug, sw, lambda rel: (ROOT / rel).exists())
    miss = sorted(set(miss))
    if miss:
        anchor = '  "games/%s/' % slug
        pos = sw.find(anchor)
        if pos >= 0:
            end = sw.find("\n", pos) + 1
            sw = sw[:end] + "".join('  "%s",\n' % m for m in miss) + sw[end:]
            sw_path.write_text(sw)
            print("precached: " + ", ".join(miss))
        else:
            print("could not find a place in sw.js for: " + ", ".join(miss))
    run([sys.executable, "scripts/generate-offline-manifest.py"])
    tick(ROOT / "planning" / "TODO-NEXT.md", accepted)
    code, out = run([sys.executable, "scripts/todo-progress.py", "planning/TODO-NEXT.md"])
    print(out.strip().splitlines()[-1] if out.strip() else "")
    git("add", "sw.js", "offline-manifest.json", "planning/TODO-NEXT.md")
    git("commit", "-q", "-m", "Audited %s: tick %s%s; precache check\n\nCo-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>" % (
        slug, ", ".join(accepted) or "nothing", ("; partial: " + ", ".join(partial)) if partial else ""),
        "--", "sw.js", "offline-manifest.json", "planning/TODO-NEXT.md", check=False)
    if wt.exists():
        git("worktree", "remove", "-f", "-f", str(wt))
    git("branch", "-D", branch, check=False)
    print("merged %s, ticked %d, worktree and branch closed" % (slug, len(accepted)))
    if args.delete_remote:
        git("fetch", "-q", "--prune")
        handled = set(accepted) | set(partial)
        victims = []
        for b in [x.strip() for x in git("branch", "-r").splitlines() if "/local-ai/" in x]:
            ids = {parse_subject(s) for s in git("log", "--no-merges", "--format=%s", "main.." + b).splitlines()} - {None}
            games = {game_of(git("show", "--name-only", "--format=", s).split()) for s in git("log", "--no-merges", "--format=%H", "main.." + b).split()}
            if not git("log", "--no-merges", "--format=%H", "main.." + b).split() or (ids and ids <= handled and games <= {slug}):
                victims.append(b.replace("origin/", "", 1))
        if victims:
            subprocess.run([*GH, "push", "origin", "--delete", *victims], cwd=ROOT)
        print("remote branches deleted: %d" % len(victims))
    return 0


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("intake")
    for name in ("prepare", "live", "finish"):
        p = sub.add_parser(name)
        p.add_argument("slug")
        if name == "finish":
            p.add_argument("--accepted", default="")
            p.add_argument("--partial", default="")
            p.add_argument("--delete-remote", action="store_true")
    args = ap.parse_args(argv)
    return {"intake": cmd_intake, "prepare": cmd_prepare, "live": cmd_live, "finish": cmd_finish}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
