"""Read a game's page code and list the mistakes the local AI keeps making, without opening a browser.

    python local-ai/static_check.py <game>              check the whole game folder
    python local-ai/static_check.py <game> --changed    also require a test when game code changed (uses git)

Prints one line per finding and exits 1 if there are any. Every check here comes from a real mistake found
by the 2026-10-13/15 audits of the local AI's Round 4 work (about 100 ideas, almost none worked as pushed):

  missing-id        JS looks up an element id that no HTML, JS or Python writes
  head-lookup       pc.js or a new script looks up elements at the top level, before the page has built them
  event-target      an event is sent on window but only listened for on document (or the reverse)
  data-never-set    JS reads a data-* attribute that nothing ever writes
  hidden-dialog     a keyboard guard treats any [role=dialog] as open, but the Desktop page keeps every hidden
                    window frame as a role=dialog (use [role='dialog']:not([hidden]))
  unknown-action    JS sends an engine action that game.py never mentions
  no-test           game code changed but no test was added or changed (--changed only)

These are heuristics: a finding means "look here", not always a bug. Fix it or explain it in the report.
"""
import re
import subprocess
import sys
from pathlib import Path

import os
ROOT = Path(os.environ.get("NOYVJ_ROOT") or Path(__file__).resolve().parent.parent)

LOOKUP = re.compile(r"""(?:getElementById|\$|byId)\(\s*["']([A-Za-z][\w-]*)["']\s*\)""")
SELECT_ID = re.compile(r"""querySelector(?:All)?\(\s*["']#([A-Za-z][\w-]*)""")
ID_WRITTEN = re.compile(r"""\bid\s*=\s*\\?["']([A-Za-z][\w-]*)|setAttribute\(\s*["']id["']\s*,\s*["']([A-Za-z][\w-]*)|\.id\s*=\s*["']([A-Za-z][\w-]*)|[{,]\s*id\s*:\s*["']([A-Za-z][\w-]*)""")
TEMPLATE_ID = re.compile(r"""\bid=\\?["']([A-Za-z][\w-]*)""")
DISPATCH = re.compile(r"""(window|document)\.dispatchEvent\(\s*new\s+(?:Custom)?Event\(\s*["']([\w:.-]+)""")
LISTEN = re.compile(r"""(window|document)\.addEventListener\(\s*["']([\w:.-]+)""")
DATA_READ = re.compile(r"""dataset\.([A-Za-z]\w*)|getAttribute\(\s*["']data-([\w-]+)|\[data-([\w-]+)""")
ACTION = re.compile(r"""\baction\s*:\s*["']([a-z_][\w]*)["']""")
DIALOG_BAD = re.compile(r"""\[role\s*=\s*["']?dialog["']?\](?!:not)""")
TOP_LOOKUP = re.compile(r"""^(?!\s)(?!//)(?!/\*)(?!\*).*\b(?:document\.(?:getElementById|querySelector|querySelectorAll|body)|\$\()""")


def camel_to_dash(name):
    return re.sub(r"([A-Z])", lambda m: "-" + m.group(1).lower(), name)


def read(path):
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def game_files(game_dir):
    js = sorted(p for p in game_dir.glob("*.js") if p.name not in ("sw.js",))
    py = sorted(game_dir.glob("*.py"))
    html = [p for p in (game_dir / "index.html",) if p.exists()]
    return js, py, html


def shared_text():
    return "\n".join(read(p) for p in sorted((ROOT / "shared").glob("*.js")))


def built_dynamically(ident, text):
    """An id like task-garden-button can be built as "task-" + name + "-button": accept any quoted piece of it."""
    parts = ident.split("-")
    for i in range(1, len(parts)):
        prefix = "-".join(parts[:i]) + "-"
        suffix = "-" + "-".join(parts[i:])
        if re.search(r"""["']%s["']\s*\+""" % re.escape(prefix), text) or re.search(r"""\+\s*["']%s["']""" % re.escape(suffix), text):
            return True
    return False


def check_game(game, changed=False):
    game_dir = ROOT / "games" / game
    findings = []
    js_files, py_files, html_files = game_files(game_dir)
    js_text = {p: read(p) for p in js_files}
    html_text = "\n".join(read(p) for p in html_files) + "\n" + read(game_dir / "pc-config.json")
    py_text = "\n".join(read(p) for p in py_files)
    shared = shared_text()
    everything = "\n".join(js_text.values()) + "\n" + html_text + "\n" + py_text + "\n" + shared

    written = {"kb-shortcuts-panel"}   # the default id shared/keyboard-shortcuts.js builds
    for m in ID_WRITTEN.finditer(everything):
        written.update(g for g in m.groups() if g)
    for m in TEMPLATE_ID.finditer(everything):
        written.add(m.group(1))

    for path, text in js_text.items():
        rel = path.relative_to(ROOT)
        for n, line in enumerate(text.split("\n"), 1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("*"):
                continue
            for m in list(LOOKUP.finditer(line)) + list(SELECT_ID.finditer(line)):
                ident = m.group(1)
                if ident not in written and not ident.startswith(("pc-", "shell-")) and not built_dynamically(ident, everything):
                    findings.append("%s:%d missing-id: no HTML, JS or Python writes id \"%s\"" % (rel, n, ident))
            if DIALOG_BAD.search(line) and "hidden" not in "\n".join(text.split("\n")[n - 1:n + 6]):
                findings.append("%s:%d hidden-dialog: use [role='dialog']:not([hidden]) so hidden Desktop window frames do not count as open" % (rel, n))
            if path.name == "pc.js" or path.name not in ("app.js", "settings.js"):
                if TOP_LOOKUP.match(line) and "addEventListener" not in line:
                    findings.append("%s:%d head-lookup: top-level element lookup runs before the page is built; move it inside window.addEventListener(\"load\", ...)" % (rel, n))

    # events: sent on one target, heard on the other
    sent, heard = {}, {}
    for text in list(js_text.values()) + [shared]:
        for m in DISPATCH.finditer(text):
            sent.setdefault(m.group(2), set()).add(m.group(1))
        for m in LISTEN.finditer(text):
            heard.setdefault(m.group(2), set()).add(m.group(1))
    own_text = "\n".join(js_text.values())
    for name, targets in sent.items():
        if name not in own_text:
            continue
        listeners = heard.get(name, set())
        if listeners and not (targets & listeners):
            findings.append("event-target: \"%s\" is sent on %s but only heard on %s" % (name, "/".join(sorted(targets)), "/".join(sorted(listeners))))

    # data attributes read but never written
    written_data = set(re.findall(r"""data-([\w-]+)""", html_text + py_text + shared + own_text))
    written_data |= {camel_to_dash(m) for m in re.findall(r"""dataset\.([A-Za-z]\w*)\s*=""", everything)}
    written_data |= set(re.findall(r"""setAttribute\(\s*["']data-([\w-]+)""", everything))
    for path, text in js_text.items():
        rel = path.relative_to(ROOT)
        for m in DATA_READ.finditer(text):
            raw = m.group(1) or m.group(2) or m.group(3)
            name = camel_to_dash(raw) if m.group(1) else raw
            setters = re.findall(r"""data-%s\b|dataset\.%s\s*=|setAttribute\(\s*["']data-%s""" % (re.escape(name), re.escape(raw), re.escape(name)), html_text + py_text + shared + "\n".join(t for p, t in js_text.items()))
            plain_reads = len(re.findall(r"""dataset\.%s\b|getAttribute\(\s*["']data-%s|\[data-%s""" % (re.escape(raw), re.escape(name), re.escape(name)), text))
            if not setters or (len(setters) <= plain_reads and name not in written_data):
                findings.append("%s data-never-set: reads data-%s but nothing writes it" % (rel, name))
                break

    # engine actions that the game never mentions
    for path, text in js_text.items():
        rel = path.relative_to(ROOT)
        for m in ACTION.finditer(text):
            act = m.group(1)
            if py_text and ('"%s"' % act) not in py_text and ("'%s'" % act) not in py_text:
                findings.append("%s unknown-action: sends engine action \"%s\" but no .py file in the game mentions it" % (rel, act))

    if changed:
        findings.extend(check_tests_added(game))
    return sorted(set(findings))


def check_tests_added(game):
    try:
        out = subprocess.run(["git", "status", "--porcelain", "--", "games/" + game], cwd=ROOT,
                             capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return []
    files = [line[3:].strip().strip('"') for line in out.splitlines() if line.strip()]
    code = [f for f in files if re.search(r"\.(py|js|html|css)$", f) and "/tests/" not in f and not f.endswith("pc.html")]
    tests = [f for f in files if "/tests/" in f and f.endswith(".py")]
    if code and not tests:
        return ["no-test: %d game file(s) changed (%s) but no file in games/%s/tests/ was added or changed" % (len(code), ", ".join(code[:3]), game)]
    return []


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    if len(args) != 1 or not (ROOT / "games" / args[0]).is_dir():
        print(__doc__)
        return 2
    findings = check_game(args[0], changed="--changed" in argv)
    for line in findings:
        print(line)
    if not findings:
        print("static_check: no findings for %s" % args[0])
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
