#!/usr/bin/env python3
"""Performance budget for every game (TODO Z-12): Pyodide boot time, first-interactive time and
payload size, measured in headless Chromium (Playwright) against the local dev server, written to
planning/PERF-BUDGET.md, and compared with scripts/perf-budget.json.

Usage:
    python3 scripts/measure-perf.py                 # measure every game, write planning/PERF-BUDGET.md,
                                                    #   create budget entries for games that have none
    python3 scripts/measure-perf.py grid tide       # only these games (the md keeps the other rows)
    python3 scripts/measure-perf.py --check         # measure, change nothing, exit 1 if any metric is
                                                    #   more than 20% over its budget (or a game cannot be measured)
    python3 scripts/measure-perf.py --rebaseline    # overwrite the budgets with what was just measured
    options: --runs N (cold loads per game, median taken, default 3), --base URL (default
    http://localhost:8073; start it with `python3 -m http.server 8073` from the repo root or
    preview_start hub-dev-server), --timeout SECONDS (per page load, default 90)

What is measured, per game page (`games/<slug>/index.html`), with an empty browser cache ("cold",
a first visit) `--runs` times, then once more in the same browser context ("warm", a repeat visit
with the HTTP cache filled):
    pyodide_ms          page start -> window.pyodide exists (Pyodide itself downloaded and started)
    setup_ms            pyodide -> the game's Python defined get_state() (the game's code ran)
    first_interactive_ms   page start -> first painted frame after that (shared/perf-mark.js marks)
    own_kb              bytes over the wire from the dev server itself (HTML, JS, CSS, game.py, JSON...)
    total_kb            all bytes over the wire, own + the Pyodide CDN (the full first-visit download)
`warm_first_interactive_ms` and `warm_total_kb` are the repeat-visit figures. Only localhost and
cdn.jsdelivr.net (where Pyodide lives) are allowed through (Chromium's host resolver refuses every
other host); ads, fonts, analytics and the live backend are refused so nothing is sent anywhere and the numbers do not depend on them. The boot
timings include downloading Pyodide from the CDN, so they move with the network: that is what the
20% margin in --check is for. Run it on a quiet machine; a failure should be re-run before it is
believed.

The budget file maps game -> metric -> allowed value. A budget is the baseline measured when it was
created. Raise one deliberately with --rebaseline (all games) after a change you accept, and say why
in the commit.
"""
import json
import statistics
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
BUDGET_FILE = ROOT / "scripts" / "perf-budget.json"
REPORT_FILE = ROOT / "planning" / "PERF-BUDGET.md"
TOLERANCE = 0.20
ALLOWED_EXTERNAL = {"cdn.jsdelivr.net"}

METRICS = [  # key, label, unit
    ("pyodide_ms", "Pyodide ready", "ms"),
    ("setup_ms", "Game setup", "ms"),
    ("first_interactive_ms", "First interactive", "ms"),
    ("own_kb", "Own files", "KB"),
    ("total_kb", "Total download", "KB"),
    ("warm_first_interactive_ms", "Repeat visit: first interactive", "ms"),
    ("warm_total_kb", "Repeat visit: download", "KB"),
]
# Metrics that get a budget. The repeat-visit figures are reported only (one load, dominated by
# WebAssembly compile time, so too noisy to gate on), and "Game setup" is a part of first interactive.
BUDGETED = ["pyodide_ms", "first_interactive_ms", "own_kb", "total_kb"]
# Below these a +20% rule is just noise (a 90 ms figure moving to 110 ms is not a regression).
FLOOR = {"ms": 500, "KB": 20}


def game_slugs():
    return sorted(p.parent.name for p in (ROOT / "games").glob("*/index.html"))


def load_one(browser_context, url, origin_host, timeout_s):
    """Open the page in a new tab of the context; return (marks_summary or None, bytes_by_group)."""
    page = browser_context.new_page()
    sizes = {"own": 0, "cdn": 0}
    pending = []

    def on_response(resp):
        pending.append(resp)

    page.on("response", on_response)
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_s * 1000)
        page.wait_for_function(
            "window.NoyvjPerf && window.NoyvjPerf.marks()['first-interactive'] !== undefined",
            timeout=timeout_s * 1000)
        page.wait_for_timeout(600)       # let late small requests (json, achievements) land
        summary = page.evaluate("window.NoyvjPerf.summary()")
    except Exception as exc:  # noqa: BLE001 -- a game that cannot be measured is reported, not fatal
        page.close()
        return None, sizes, "%s: %s" % (type(exc).__name__, str(exc).splitlines()[0][:160])
    for resp in pending:
        try:
            req_sizes = resp.request.sizes()
            wire = (req_sizes.get("responseBodySize") or 0) + (req_sizes.get("responseHeadersSize") or 0)
        except Exception:  # noqa: BLE001
            wire = 0
        host = urlparse(resp.url).netloc
        if host == origin_host:
            sizes["own"] += wire
        elif host in ALLOWED_EXTERNAL:
            sizes["cdn"] += wire
    page.close()
    return summary, sizes, None


def measure_game(playwright, slug, base, runs, timeout_s):
    """Return (metrics dict, note). metrics is None when the game could not be measured."""
    url = "%s/games/%s/index.html" % (base, slug)
    origin_host = urlparse(base).netloc
    cold, warm, note = [], None, None

    # Refuse every host but the dev server and the Pyodide CDN at DNS level. (Playwright's
    # route interception would do it too, but it switches Chromium's HTTP cache off, and the
    # repeat-visit figure needs the cache.)
    allowed = ", ".join("EXCLUDE " + h.split(":")[0] for h in {origin_host} | ALLOWED_EXTERNAL)
    launch_args = ["--host-resolver-rules=MAP * ~NOTFOUND, " + allowed]

    for i in range(runs):
        browser = playwright.chromium.launch(args=launch_args)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        summary, sizes, err = load_one(context, url, origin_host, timeout_s)
        if err:
            note = err
            browser.close()
            break
        cold.append((summary, sizes))
        if i == runs - 1:      # warm visit in the last context only
            summary2, sizes2, err2 = load_one(context, url, origin_host, timeout_s)
            if not err2:
                warm = (summary2, sizes2)
        browser.close()
    if note or not cold:
        return None, note or "no measurement"
    med = statistics.median
    gaps = [c[0]["gaps"] for c in cold]
    marks = [c[0]["marks"] for c in cold]
    metrics = {
        "pyodide_ms": int(med(m["pyodide-loaded"] for m in marks)),
        "setup_ms": int(med(g.get("game-setup-done", 0) for g in gaps)),
        "first_interactive_ms": int(med(m["first-interactive"] for m in marks)),
        "own_kb": round(med(c[1]["own"] for c in cold) / 1024, 1),
        "total_kb": round(med(c[1]["own"] + c[1]["cdn"] for c in cold) / 1024, 1),
    }
    if warm:
        metrics["warm_first_interactive_ms"] = int(warm[0]["marks"]["first-interactive"])
        metrics["warm_total_kb"] = round((warm[1]["own"] + warm[1]["cdn"]) / 1024, 1)
    return metrics, None


def over_budget(metrics, budget):
    """List (metric, measured, allowed, unit) for every budgeted metric more than 20% over."""
    out = []
    units = {k: u for k, _, u in METRICS}
    for key in BUDGETED:
        if key not in metrics or key not in budget:
            continue
        allowed = budget[key] * (1 + TOLERANCE)
        if metrics[key] > allowed and metrics[key] - budget[key] > FLOOR[units[key]] * TOLERANCE:
            out.append((key, metrics[key], round(allowed, 1), units[key]))
    return out


def fmt(value, unit):
    if value is None:
        return "-"
    return ("%d" % value if unit == "ms" else "%.0f" % value)


def write_report(results, budgets, notes, base, runs):
    lines = [
        "# Performance budget",
        "",
        "Generated by `python3 scripts/measure-perf.py` (Z-12); do not edit by hand. Measured in headless",
        "Chromium against `%s`, cold cache, median of %d loads per game; the repeat-visit columns are one" % (base, runs),
        "extra load with the browser cache filled. Boot timings include downloading Pyodide from its CDN, so they",
        "move with the network. Last run: %s." % time.strftime("%Y-%m-%d %H:%M"),
        "",
        "`python3 scripts/measure-perf.py --check` fails when a budgeted figure is more than 20% over the",
        "number in `scripts/perf-budget.json` (the baseline taken when the budget was created). Raise a",
        "budget deliberately with `--rebaseline` and say why in the commit.",
        "",
        "| Game | Pyodide ready (ms) | First interactive (ms) | Own files (KB) | Total download (KB) | Repeat visit (ms) | Budget: first interactive / total |",
        "|---|---|---|---|---|---|---|",
    ]
    for slug in sorted(results):
        m = results[slug]
        b = budgets.get(slug, {})
        if m is None:
            lines.append("| %s | not measured | | | | | |" % slug)
            continue
        lines.append("| %s | %s | %s | %s | %s | %s | %s / %s |" % (
            slug, fmt(m["pyodide_ms"], "ms"), fmt(m["first_interactive_ms"], "ms"), fmt(m["own_kb"], "KB"),
            fmt(m["total_kb"], "KB"), fmt(m.get("warm_first_interactive_ms"), "ms"),
            fmt(b.get("first_interactive_ms"), "ms"), fmt(b.get("total_kb"), "KB")))
    failed = {s: n for s, n in notes.items() if n}
    if failed:
        lines += ["", "## Games that could not be measured", ""]
        lines += ["- `%s`: %s" % (s, n) for s, n in sorted(failed.items())]
    lines += [
        "",
        "## How to read it",
        "",
        "- *Pyodide ready*: page start until `window.pyodide` exists. This is mostly the Pyodide download",
        "  and start-up, the same for every game, so it is the floor the other columns sit on.",
        "- *First interactive*: page start until the game's Python has defined `get_state()` and a frame has",
        "  been painted (the `noyvj:first-interactive` mark from `shared/perf-mark.js`).",
        "- *Own files*: bytes over the wire from the site itself. *Total download*: that plus the Pyodide CDN",
        "  files, i.e. a first visit. Wire size, so compressed when the server compresses (the local",
        "  `http.server` does not, so these are upper bounds for GitHub Pages).",
        "- *Repeat visit*: first-interactive time of a second load in the same browser, so the cached Pyodide",
        "  is reused. The service worker's Pyodide caching (TODO Z-12, second half) is not measured here yet.",
        "",
    ]
    REPORT_FILE.write_text("\n".join(lines), encoding="utf8")


def parse_args(argv):
    opts = {"check": False, "rebaseline": False, "runs": 3, "base": "http://localhost:8073", "timeout": 90, "games": []}
    it = iter(argv)
    for arg in it:
        if arg == "--check":
            opts["check"] = True
        elif arg == "--rebaseline":
            opts["rebaseline"] = True
        elif arg == "--runs":
            opts["runs"] = int(next(it))
        elif arg == "--base":
            opts["base"] = next(it).rstrip("/")
        elif arg == "--timeout":
            opts["timeout"] = int(next(it))
        elif arg.startswith("--"):
            raise SystemExit("unknown option " + arg)
        else:
            opts["games"].append(arg)
    return opts


def main(argv):
    opts = parse_args(argv)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise SystemExit("Playwright is not installed (pip install playwright && playwright install chromium)")
    slugs = opts["games"] or game_slugs()
    unknown = [s for s in slugs if s not in game_slugs()]
    if unknown:
        raise SystemExit("no such game: " + ", ".join(unknown))
    budgets = json.loads(BUDGET_FILE.read_text(encoding="utf8")) if BUDGET_FILE.exists() else {}
    budgets.setdefault("games", {})
    results, notes = {}, {}
    with sync_playwright() as p:
        for slug in slugs:
            started = time.time()
            metrics, note = measure_game(p, slug, opts["base"], opts["runs"], opts["timeout"])
            results[slug], notes[slug] = metrics, note
            if metrics is None:
                print("%-14s NOT MEASURED  %s" % (slug, note))
            else:
                print("%-14s pyodide %5d ms  interactive %5d ms  own %7.1f KB  total %8.1f KB  repeat %s ms   (%.0fs)" % (
                    slug, metrics["pyodide_ms"], metrics["first_interactive_ms"], metrics["own_kb"],
                    metrics["total_kb"], metrics.get("warm_first_interactive_ms", "-"), time.time() - started))
                print("               repeat visit download: %s KB" % metrics.get("warm_total_kb", "-"))
    problems = []
    for slug in slugs:
        if results[slug] is None:
            problems.append("%s: could not be measured (%s)" % (slug, notes[slug]))
            continue
        budget = budgets["games"].get(slug)
        if budget and not opts["rebaseline"]:
            for key, value, allowed, unit in over_budget(results[slug], budget):
                problems.append("%s: %s is %s %s, over the budget of %s %s by more than 20%% (limit %s)" % (
                    slug, key, value, unit, budget[key], unit, allowed))
    if opts["check"]:
        if problems:
            print("\nPERFORMANCE BUDGET EXCEEDED")
            for line in problems:
                print("  - " + line)
            return 1
        missing = [s for s in slugs if s not in budgets["games"]]
        print("\nAll measured games are within 120%% of their budgets.%s" % (
            " (No budget yet for: %s)" % ", ".join(missing) if missing else ""))
        return 0
    for slug in slugs:
        if results[slug] is None:
            continue
        if opts["rebaseline"] or slug not in budgets["games"]:
            budgets["games"][slug] = {k: results[slug][k] for k in BUDGETED if k in results[slug]}
    budgets["_note"] = ("Allowed values per game; scripts/measure-perf.py --check fails when a measurement is more than "
                        "20% over. Baselines taken in headless Chromium against the local dev server. Update only with "
                        "--rebaseline, deliberately.")
    BUDGET_FILE.write_text(json.dumps(budgets, indent=1, sort_keys=True) + "\n", encoding="utf8")
    # The report always shows every game; keep rows for games not measured this time from the budget baseline.
    all_results = {s: results.get(s) for s in slugs}
    if opts["games"]:
        for s in game_slugs():
            if s not in all_results and s in budgets["games"]:
                all_results[s] = dict(budgets["games"][s], setup_ms=None)
    write_report(all_results, budgets["games"], notes, opts["base"], opts["runs"])
    print("\nWrote %s and %s" % (REPORT_FILE.relative_to(ROOT), BUDGET_FILE.relative_to(ROOT)))
    if problems:
        print("Over budget or unmeasured:")
        for line in problems:
            print("  - " + line)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
