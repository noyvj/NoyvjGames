"""LC-1: the computed-style contrast scan for Le Champ de Mots, run by hand in a real browser.

Not collected by pytest (no test_ prefix, needs Playwright and the dev server). Usage, from the
repo root with `python3 -m http.server 8073` running:

    python3 games/champ-de-mots/tests/tools/contrast_scan.py index.html lowpoly dark
    python3 games/champ-de-mots/tests/tools/contrast_scan.py pc.html cartoon light --base http://localhost:8073

How it measures: every visible text node's colour is compared with the pixels actually painted behind
it. It collects the text boxes, makes all text transparent, screenshots, and samples the screenshot
under each box (so gradients, translucent glass, the sky and overlapping panels are all measured as
rendered, not guessed from CSS). WCAG AA: 4.5:1, or 3:1 for large text (24px, or 18.66px bold).
Disabled controls and text inside a closed <details> are skipped. It walks the opening screen, the
farm, every panel, a few questions of each kind and each arcade game (including the Cafe Rush twist),
then force-shows every hidden element. It never touches the live backend: any non-GET request outside
localhost is aborted. Exit status 1 if any pair fails. Prints one line per failing selector group.
"""

import io
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = (HERE / "contrast_scan.js").read_text(encoding="utf-8")


def _lin(v):
    v /= 255
    return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4


def _lum(c):
    return 0.2126 * _lin(c[0]) + 0.7152 * _lin(c[1]) + 0.0722 * _lin(c[2])


def ratio(a, b):
    la, lb = _lum(a), _lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def _measure(page, item, Image, io):
    """Worst contrast of one collected item against the pixels painted behind it right now."""
    page.evaluate("(ids) => window.__cs.markClip(ids)", [item["id"]] if item["clip"] else [])
    page.evaluate("window.__cs.hide(true)")
    png = page.screenshot()
    page.evaluate("window.__cs.hide(false); window.__cs.unmarkClip()")
    img = Image.open(io.BytesIO(png)).convert("RGB")
    width, height = img.size
    samples = set()
    for r in item["rects"]:
        w, h = r["r"] - r["l"] - 2, r["b"] - r["t"] - 2
        nx, ny = max(2, min(24, int(w / 4))), max(2, min(4, int(h / 4)))
        for i in range(nx):
            for j in range(ny):
                x, y = int(r["l"] + 1 + (i + 0.5) * w / nx), int(r["t"] + 1 + (j + 0.5) * h / ny)
                if 0 <= x < width and 0 <= y < height:
                    samples.add(img.getpixel((x, y)))
    return _worst(item, samples)


def _worst(item, samples):
    worst, worst_fg, worst_bg = 999, None, None
    for f in item["fg"]:
        alpha = f["a"] * item["op"]
        for bg in samples:
            fo = tuple(f[k] * alpha + bg[n] * (1 - alpha) for n, k in enumerate("rgb"))
            value = ratio(fo, bg)
            if value < worst:
                worst, worst_fg, worst_bg = value, fo, bg
    return worst, worst_fg, worst_bg


def scan(page, per_sig=3, max_rounds=6):
    """Contrast failures on the page as it is right now: {"counted": n, "fails": [...]}.

    Every failing item is measured a second time on its own (scrolled into view, settled, fresh
    rectangles) and only kept if it still fails, so a layout that moved between collecting the
    boxes and taking the screenshot cannot report a pair that is not on screen."""
    from PIL import Image

    page.evaluate(SRC)
    tried, seen, counts, fails = set(), {}, {}, []
    measured = 0
    origin = page.evaluate("[scrollX, scrollY]")
    for _ in range(max_rounds):
        res = page.evaluate("(s) => window.__cs.collect(s)", seen)
        items = [i for i in res["items"] if counts.get(i["sig"], 0) < per_sig]
        page.evaluate("(ids) => window.__cs.markClip(ids)", [i["id"] for i in items if i["clip"]])
        page.evaluate("window.__cs.hide(true)")
        png = page.screenshot()
        page.evaluate("window.__cs.hide(false); window.__cs.unmarkClip()")
        img = Image.open(io.BytesIO(png)).convert("RGB")
        width, height = img.size
        for item in items:
            seen[item["id"]] = 1
            counts[item["sig"]] = counts.get(item["sig"], 0) + 1
            samples = set()
            for r in item["rects"]:
                w, h = r["r"] - r["l"] - 2, r["b"] - r["t"] - 2
                nx, ny = max(2, min(24, int(w / 4))), max(2, min(4, int(h / 4)))
                for i in range(nx):
                    for j in range(ny):
                        x, y = int(r["l"] + 1 + (i + 0.5) * w / nx), int(r["t"] + 1 + (j + 0.5) * h / ny)
                        if 0 <= x < width and 0 <= y < height:
                            samples.add(img.getpixel((x, y)))
            if not samples:
                continue
            measured += 1
            worst, worst_fg, worst_bg = _worst(item, samples)
            need = 3 if item["large"] else 4.5
            if worst < need - 0.001:
                fails.append({"id": item["id"], "sel": item["sel"], "text": item["text"], "ratio": round(worst, 2), "need": need,
                              "fg": ",".join(str(round(v)) for v in worst_fg), "bg": ",".join(str(v) for v in worst_bg)})
        pending = [p for p in res["pending"] if counts.get(p["sig"], 0) < per_sig and not seen.get(p["id"]) and p["id"] not in tried]
        if not pending:
            break
        tried.add(pending[0]["id"])
        page.evaluate("(id) => window.__cs.scrollTo(id)", pending[0]["id"])
        page.wait_for_timeout(250)
    # second look at each failure, one at a time
    confirmed = []
    for f in fails[:60]:
        page.evaluate("(id) => window.__cs.scrollTo(id)", f["id"])
        page.wait_for_timeout(350)
        res = page.evaluate("(s) => window.__cs.collect(s)", {})
        item = next((i for i in res["items"] if i["id"] == f["id"]), None)
        if item is None:
            continue  # no longer on screen: not a failure
        worst, worst_fg, worst_bg = _measure(page, item, Image, io)
        if worst < f["need"] - 0.001:
            f.update(ratio=round(worst, 2), fg=",".join(str(round(v)) for v in worst_fg), bg=",".join(str(v) for v in worst_bg))
            confirmed.append(f)
    page.evaluate("(p) => scrollTo(p[0], p[1])", origin)
    return {"counted": measured, "fails": confirmed}


def run(page_name, style, theme, base="http://localhost:8073", width=1440, height=900):
    from playwright.sync_api import sync_playwright

    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": width, "height": height})
        ctx.add_init_script(
            f"localStorage.setItem('champ-de-mots-visual-style','{style}');"
            f"localStorage.setItem('theme','{theme}');localStorage.setItem('hub-onboarding-seen','1');"
        )

        def route(r):
            url = r.request.url
            if "localhost" in url or "cdn.jsdelivr" in url or (r.request.method == "GET" and "fastapicloud" not in url):
                r.continue_()
            else:
                r.abort()

        ctx.route("**/*", route)
        pg = ctx.new_page()
        pg.set_default_timeout(5000)
        pg.goto(f"{base}/games/champ-de-mots/{page_name}", timeout=90000)
        pg.wait_for_selector("#opening-screen [data-action=new]", timeout=60000)
        pg.wait_for_timeout(1500)

        def snap(label):
            r = scan(pg)
            r["label"] = label
            results.append(r)

        def click(sel):
            return pg.evaluate("(s) => { const e = document.querySelector(s); if (!e || e.disabled) return false; e.click(); return true; }", sel)

        def visible(sel):
            return pg.evaluate("(s) => { const e = document.querySelector(s); if (!e) return false; const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && !e.hidden; }", sel)

        def close_all():
            pg.keyboard.press("Escape")
            pg.wait_for_timeout(150)
            for _ in range(3):
                n = pg.evaluate("() => { let n = 0; document.querySelectorAll('.practice-close, [id$=close-button]').forEach(e => { const r = e.getBoundingClientRect(); if (r.width > 0 && !e.hidden) { e.click(); n++; } }); return n; }")
                pg.wait_for_timeout(150)
                if not n:
                    break
            pg.keyboard.press("Escape")
            pg.wait_for_timeout(150)

        def step(fn):
            try:
                fn()
            except Exception as exc:  # keep scanning the rest
                results.append({"label": "error", "counted": 0, "fails": [], "error": str(exc)[:160]})

        def play(prefix, n):
            for i in range(n):
                pg.wait_for_timeout(250)
                if visible(f"#{prefix}-answer-input"):
                    pg.fill(f"#{prefix}-answer-input", "zzz")
                    click(f"#{prefix}-submit-button")
                else:
                    pg.evaluate("(p) => { const b = [...document.querySelectorAll('#' + p + '-choices button')].filter(x => x.getBoundingClientRect().width > 0 && !x.disabled); if (b.length) b[0].click(); }", prefix)
                pg.wait_for_timeout(300)
                if i == 0:
                    snap(f"{prefix}-answered")
                if visible(f"#{prefix}-next-button"):
                    click(f"#{prefix}-next-button")

        snap("opening")
        click("#opening-screen [data-action=new]")
        pg.wait_for_timeout(1200)
        click("[data-action=tutorial-no]")
        pg.wait_for_timeout(800)
        pg.keyboard.press("Escape")
        pg.wait_for_timeout(500)
        snap("farm")
        for name in ("howto", "dashboard", "calendar", "planner", "phrasebook", "achievements", "changelog", "report-log", "settings", "cultural-notes", "shop"):
            def panel(name=name):
                click(f"#{name}-toggle-button")
                pg.wait_for_timeout(500)
                snap(f"panel-{name}")
                close_all()
            step(panel)

        def water():
            click("#water-next-button")
            pg.wait_for_timeout(700)
            snap("practice-open")
            play("practice", 3)
            close_all()
        step(water)

        def review():
            click("#review-toggle-button")
            pg.wait_for_timeout(500)
            snap("review-controls")
            click("#review-word-button")
            pg.wait_for_timeout(600)
            snap("review-open")
            play("review", 2)
            close_all()
        step(review)

        def proficiency():
            pg.evaluate("() => { const b = [...document.querySelectorAll('#farm button')].find(x => /proficiency/i.test(x.textContent)); b && b.click(); }")
            pg.wait_for_timeout(700)
            snap("proficiency-open")
            play("proficiency", 2)
            close_all()
        step(proficiency)

        for name, button in (("builder", "sentence-builder-button"), ("conversation", "conversation-button"), ("listening", "listening-button"), ("placement", "placement-button"), ("liaison", "liaison-toggle-button")):
            def tool(name=name, button=button):
                click(f"#{button}")
                pg.wait_for_timeout(700)
                snap(f"{name}-open")
                close_all()
            step(tool)

        def wateropts():
            click("#water-options-toggle-button")
            pg.wait_for_timeout(500)
            snap("water-options-open")
            click("#water-opt-mc-button")
            pg.wait_for_timeout(700)
            snap("water-opt-session")
            play("review", 2)
            close_all()
        step(wateropts)

        for game in ("blitz", "racer", "boutique", "cafe", "sprint", "pairs", "gaps", "listenpick", "wordorder", "amis"):
            def arcade(game=game):
                click(f"#{game}-toggle-button")
                pg.wait_for_timeout(700)
                snap(f"{game}-open")
                click(f"#{game}-start-button")
                pg.wait_for_timeout(700)
                options = {"boutique": "#boutique-options", "cafe": "#cafe-options", "pairs": "#pairs-board", "wordorder": "#wordorder-pool"}.get(game, f"#{game}-choices")
                for i in range(4):
                    pg.evaluate("(s) => { const b = [...document.querySelectorAll(s + ' button')].filter(x => x.getBoundingClientRect().width > 0 && !x.disabled); if (b.length) b[0].click(); }", options)
                    pg.wait_for_timeout(350)
                    if i == 1:
                        snap(f"{game}-play")
                    if game == "cafe" and visible("#cafe-twist-panel"):
                        snap("cafe-twist")
                        break
                close_all()
            step(arcade)

        pg.evaluate("() => document.querySelectorAll('body [hidden]').forEach(e => { if (!e.closest('#opening-screen, [aria-modal=true], [role=dialog]') && e.id !== 'visual-style-picker') e.hidden = false; })")
        pg.wait_for_timeout(300)
        snap("everything-shown")
        browser.close()

    groups = {}
    for r in results:
        for f in r["fails"]:
            key = re.sub(r"\d+", "N", f["sel"])
            g = groups.setdefault(key, {"min": 99, "n": 0, "text": f["text"], "fg": f["fg"], "bg": f["bg"], "labels": set()})
            if f["ratio"] < g["min"]:
                g.update(min=f["ratio"], fg=f["fg"], bg=f["bg"])
            g["n"] += 1
            g["labels"].add(r["label"])
    return results, groups


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    base = "http://localhost:8073"
    if "--base" in argv:
        base = argv[argv.index("--base") + 1]
        args = [a for a in args if a != base]
    page_name, style, theme = args[:3]
    started = time.time()
    results, groups = run(page_name, style, theme, base=base)
    counted = sum(r["counted"] for r in results)
    for key, g in sorted(groups.items(), key=lambda kv: kv[1]["min"]):
        print(f'{g["min"]:5.2f}  x{g["n"]:<3} {key[-70:]}  "{g["text"]}"  {g["fg"]} on {g["bg"]}  [{", ".join(sorted(g["labels"])[:3])}]')
    errors = [r["error"] for r in results if r.get("error")]
    print(f"{page_name} {style} {theme}: {counted} text boxes measured, {len(groups)} failing selector groups, {len(errors)} driver errors, {time.time() - started:.0f}s")
    for e in errors:
        print("  driver error:", e)
    return 1 if groups else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
