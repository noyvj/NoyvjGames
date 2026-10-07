"""shared/level-select.js in headless Chromium (Playwright): the original
script-tag API still works, and the W-1 additions (data-driven unlock rules,
best results, game-supplied persistence, keyboard and screen-reader behaviour,
themes) behave. Skipped when Playwright or Chromium is not installed."""

import json
import mimetypes
from pathlib import Path

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

ROOT = Path(__file__).resolve().parents[2]
ORIGIN = "http://harness.test"


def make_levels(n=12):
    levels = []
    for i in range(1, n + 1):
        level = {"id": f"l{i}", "title": f"Level {i}", "blurb": f"Blurb {i}", "kind": "level"}
        if i % 5 == 0:
            level["kind"] = "mode" if i % 10 == 5 else "mechanic"
        if i > 1:
            level["requires"] = [f"l{i - 1}"]
        levels.append(level)
    levels[3]["requires"] = []          # level 4 opens with only "complete 2 other levels"
    levels[3]["requires_count"] = 2
    levels[2]["better"] = "lower"
    levels[2]["unit"] = "seasons"
    return {"title": "Harness levels", "levels": levels}


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="font-family:system-ui;background:#12162a;color:#eee"><h1>Game</h1>
<button id="levels-open-button" type="button">Levels</button><button id="other" type="button">other</button>
<script>window.started = []; window.NoyvjLevelStart = (id) => window.started.push(id);</script>
%(script)s
</body></html>"""

AUTO = '<script src="/shared/level-select.js" data-game-id="harness" data-levels="/levels.json" data-open="#levels-open-button"></script>'
FACTORY = '<script src="/shared/level-select.js"></script>'


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception as exc:
            pytest.skip(f"Chromium unavailable: {exc}")
        yield b
        b.close()


def open_page(browser, script=AUTO, size=(1440, 900), theme=None, store=None, levels=None):
    context = browser.new_context(viewport={"width": size[0], "height": size[1]})
    page = context.new_page()
    data = levels if levels is not None else make_levels()

    def serve(route, request):
        url = request.url[len(ORIGIN):].split("?")[0]
        if url == "/t.html":
            return route.fulfill(status=200, content_type="text/html", body=PAGE % {"script": script})
        if url == "/levels.json":
            return route.fulfill(status=200, content_type="application/json", body=json.dumps(data))
        file = ROOT / url.lstrip("/")
        if file.is_file():
            return route.fulfill(status=200, content_type=mimetypes.guess_type(file.name)[0] or "text/plain", body=file.read_bytes())
        return route.fulfill(status=404, body="")

    page.route(f"{ORIGIN}/**", serve)
    page.goto(f"{ORIGIN}/t.html")
    if store is not None:
        page.evaluate("(s) => { localStorage.clear(); for (const k in s) localStorage.setItem(k, s[k]); }", store)
        page.reload()
    if theme:
        page.evaluate("(t) => document.documentElement.setAttribute('data-theme', t)", theme)
    if script == AUTO:
        page.wait_for_function("NoyvjLevels.ready()")
    return context, page


def create(page, **extra):
    page.evaluate(
        """(extra) => {
          window.changes = [];
          window.ls = NoyvjLevels.create(Object.assign({
            title: 'Created', levels: extra.levels, onChange: (s) => window.changes.push(s),
            onStart: (id, level) => window.started.push(id + ':' + level.kind), trigger: '#levels-open-button',
          }, extra.options || {}, extra.state ? { state: extra.state } : {}));
        }""",
        {"levels": make_levels()["levels"], "options": extra.get("options"), "state": extra.get("state")},
    )


def focused_level(page):
    return page.evaluate("document.activeElement.dataset.level")


# ---- pure logic ------------------------------------------------------------

def test_pure_logic_unlock_rules_results_and_audit(browser):
    context, page = open_page(browser, script=FACTORY)
    out = page.evaluate("""(data) => {
      const L = NoyvjLevels.logic;
      const levels = L.normaliseLevels(data.levels.concat([{ id: 'l1', title: 'dup' }, { nope: 1 }, { id: 'm', title: 'M', mode: true }]));
      const s0 = L.emptyState();
      const res = {};
      res.count = levels.length;
      res.modeAlias = levels[levels.length - 1].kind;
      res.reason2 = L.lockReason(levels, s0, levels[1]);
      res.reason4 = L.lockReason(levels, s0, levels[3]);
      const a = L.recordResult(levels, s0, 'l1', 5);
      const b = L.recordResult(levels, a.state, 'l2', 'fine');
      res.afterTwo = L.lockReason(levels, b.state, levels[3]);
      res.reason2Done = L.lockReason(levels, b.state, levels[1]);
      res.inputUntouched = JSON.stringify(s0);
      // higher is better by default; a worse result does not replace the best
      const hi = L.recordResult(levels, a.state, 'l1', 3);
      res.hi = [hi.changed, hi.improved, hi.state.best.l1];
      const hi2 = L.recordResult(levels, a.state, 'l1', 9);
      res.hi2 = [hi2.changed, hi2.improved, hi2.state.best.l1];
      // level 3 is 'lower is better' with a unit
      const c = L.recordResult(levels, s0, 'l3', 7);
      const c2 = L.recordResult(levels, c.state, 'l3', 9);
      const c3 = L.recordResult(levels, c.state, 'l3', 4);
      res.lower = [c.state.best.l3, c2.changed, c3.state.best.l3, c3.improved];
      res.unknown = L.recordResult(levels, s0, 'nope', 1).changed;
      res.progress = L.progress(levels, b.state);
      res.nextUp = L.nextUp(levels, b.state).id;
      res.sanitized = L.sanitizeState(levels, { done: ['l1', 'zzz', 'l1', 7], best: { l1: { value: 3, text: 'x'.repeat(100) }, l9: { value: 1 }, l2: 'bad' } });
      res.legacy = L.sanitizeState(levels, ['l1', 'l2', 'q']);
      res.audit = L.audit(levels.slice(0, 5).map((l, i) => i === 4 ? Object.assign({}, l, { kind: 'level' }) : l));
      res.auditUnknown = L.audit([{ id: 'a', title: 'A', kind: 'level', requires: ['ghost'] }]);
      return res;
    }""", make_levels())
    assert out["count"] == 13 and out["modeAlias"] == "mode"
    assert out["reason2"] == "Complete Level 1 first"
    assert out["reason4"] == "Complete 2 more levels first"
    assert out["afterTwo"] == "" and out["reason2Done"] == ""
    assert out["inputUntouched"] == '{"done":[],"best":{}}'
    assert out["hi"] == [False, False, {"value": 5, "text": "5"}]
    assert out["hi2"] == [True, True, {"value": 9, "text": "9"}]
    assert out["lower"] == [{"value": 7, "text": "7 seasons"}, False, {"value": 4, "text": "4 seasons"}, True]
    assert out["unknown"] is False
    assert out["progress"] == {"done": 2, "total": 13}
    assert out["nextUp"] == "l3"
    assert out["sanitized"]["done"] == ["l1"] and out["sanitized"]["best"] == {"l1": {"value": 3, "text": "x" * 60}}
    assert out["legacy"]["done"] == ["l1", "l2"]
    assert out["audit"] == ["level 5 (l5) should be a mode or a mechanic"]
    assert out["auditUnknown"] == ["a requires unknown level ghost"]
    context.close()


# ---- the original script-tag API ---------------------------------------------

def test_script_tag_api_still_works_with_local_storage_fallback(browser):
    context, page = open_page(browser, store={"levels:harness": json.dumps(["l1"])})
    assert page.evaluate("NoyvjLevels.done()") == ["l1"], "the first version's stored list is read"
    page.click("#levels-open-button")
    assert page.locator("#level-select").is_visible()
    assert page.locator("#level-select").get_attribute("role") == "dialog"
    assert page.locator(".level-card").count() == 12
    # Play on an unlocked level starts it through window.NoyvjLevelStart and closes the dialog
    page.locator('.level-play[data-level="l2"]').click()
    assert page.evaluate("started") == ["l2"]
    assert page.locator("#level-select").is_hidden()
    # complete() persists to the same key as before (done ids, a plain list)
    assert page.evaluate("NoyvjLevels.complete('l2')") is True
    assert page.evaluate("NoyvjLevels.complete('l2')") is False
    assert json.loads(page.evaluate("localStorage.getItem('levels:harness')")) == ["l1", "l2"]
    assert page.evaluate("NoyvjLevels.isDone('l2')") is True
    context.close()


def test_calls_made_before_the_file_arrives_are_replayed(browser):
    context = browser.new_context()
    page = context.new_page()
    data = make_levels()

    def serve(route, request):
        url = request.url[len(ORIGIN):].split("?")[0]
        if url == "/t.html":
            body = PAGE % {"script": AUTO.replace("<script src", "<script>window.changes=[];</script><script src")}
            return route.fulfill(status=200, content_type="text/html", body=body.replace(
                "</body>", "<script>NoyvjLevels.configure({ onChange: (s) => window.changes.push(s), state: { done: ['l1'] } });"
                          "NoyvjLevels.complete('l2', 12);</script></body>"))
        if url == "/levels.json":
            return route.fulfill(status=200, content_type="application/json", body=json.dumps(data))
        file = ROOT / url.lstrip("/")
        return route.fulfill(status=200, body=file.read_bytes(), content_type=mimetypes.guess_type(file.name)[0] or "text/plain") if file.is_file() else route.fulfill(status=404, body="")

    page.route(f"{ORIGIN}/**", serve)
    page.goto(f"{ORIGIN}/t.html")
    page.wait_for_function("NoyvjLevels.ready()")
    assert page.evaluate("NoyvjLevels.getState()") == {"done": ["l1", "l2"], "best": {"l2": {"value": 12, "text": "12"}}}
    assert page.evaluate("changes.length") == 1
    assert page.evaluate("localStorage.getItem('levels:harness')") is None, "no storage of its own once the game supplies onChange"
    context.close()


def test_missing_levels_file_leaves_the_game_alone(browser):
    context = browser.new_context()
    page = context.new_page()
    page.route(f"{ORIGIN}/**", lambda route, request: route.fulfill(
        status=200, content_type="text/html", body=PAGE % {"script": AUTO}) if request.url.endswith("t.html")
        else (route.fulfill(status=200, content_type="text/javascript", body=(ROOT / "shared/level-select.js").read_text())
              if request.url.endswith("level-select.js") else route.fulfill(status=404, body="")))
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"{ORIGIN}/t.html")
    page.wait_for_timeout(300)
    assert page.locator("#level-select").count() == 0 and errors == []
    page.click("#levels-open-button")
    assert page.locator("#level-select").count() == 0
    context.close()


# ---- the factory: persistence by callback, rules, results ---------------------

def test_game_supplied_persistence_touches_no_storage_and_reports_every_change(browser):
    context, page = open_page(browser, script=FACTORY)
    create(page, state={"done": ["l1"]})
    assert page.evaluate("ls.done()") == ["l1"]
    assert page.evaluate("ls.complete('l2', { value: 40, text: '40 coins' })") is True
    assert page.evaluate("ls.complete('l2', 10)") is False, "a worse result changes nothing"
    assert page.evaluate("ls.complete('l2', 55)") is True, "a better result updates the best"
    assert page.evaluate("changes.length") == 2
    assert page.evaluate("changes[1]") == {"done": ["l1", "l2"], "best": {"l2": {"value": 55, "text": "55"}}}
    assert page.evaluate("Object.keys(localStorage)") == []
    assert page.evaluate("ls.best('l2')") == {"value": 55, "text": "55"}
    # setState (loading a save) replaces progress without echoing onChange
    page.evaluate("ls.setState({ done: ['l1', 'l2', 'l3'], best: {} })")
    assert page.evaluate("ls.done()") == ["l1", "l2", "l3"] and page.evaluate("changes.length") == 2
    context.close()


def test_cards_show_state_unlock_reason_best_and_every_fifth_is_a_mode(browser):
    context, page = open_page(browser, script=FACTORY)
    create(page, state={"done": ["l1", "l2"], "best": {"l2": {"value": 31, "text": "31 coins"}}})
    page.click("#levels-open-button")
    cards = page.evaluate("""() => [...document.querySelectorAll('.level-card')].map((c) => ({
      id: c.dataset.level, state: c.dataset.state, kind: c.querySelector('.level-kind').textContent,
      status: c.querySelector('.level-status').textContent, best: c.querySelector('.level-best').textContent,
      bestHidden: c.querySelector('.level-best').hidden, button: c.querySelector('button').textContent,
      label: c.querySelector('button').getAttribute('aria-label'), disabled: c.querySelector('button').getAttribute('aria-disabled'),
      border: getComputedStyle(c).borderStyle, width: getComputedStyle(c).borderTopWidth }))""")
    by = {c["id"]: c for c in cards}
    assert page.locator(".level-progress").inner_text() == "2 of 12 complete"
    assert by["l1"]["state"] == "done" and by["l1"]["status"] == "✓ Completed" and by["l1"]["button"] == "Play again"
    assert by["l2"]["best"] == "Best: 31 coins" and by["l1"]["bestHidden"] is True
    assert by["l3"]["state"] == "ready" and by["l3"]["status"] == "▶ Ready" and by["l3"]["button"] == "Play"
    assert by["l4"]["state"] == "ready", "requires_count 2 is met by two completed levels"
    assert by["l6"]["state"] == "locked" and by["l6"]["status"] == "⊘ Locked: Complete Level 5 first"
    assert by["l6"]["disabled"] == "true" and by["l6"]["button"] == "Locked"
    assert by["l6"]["label"] == "Locked: level 6, Level 6"
    assert by["l5"]["kind"] == "★ Game mode" and by["l10"]["kind"] == "✦ New mechanic" and by["l1"]["kind"] == "Level"
    # shape cues differ for done / ready / locked and for modes
    assert by["l1"]["border"] == "solid" and by["l6"]["border"] == "dashed"
    assert by["l5"]["state"] == "locked" and by["l5"]["border"] == "dashed"
    assert by["l1"]["width"] != by["l3"]["width"]
    assert page.evaluate("document.querySelectorAll('ol.level-grid > li').length") == 12
    context.close()


def test_a_ready_mode_has_a_double_border(browser):
    context, page = open_page(browser, script=FACTORY)
    create(page, state={"done": ["l1", "l2", "l3", "l4"]})
    page.click("#levels-open-button")
    assert page.evaluate("getComputedStyle(document.querySelector('[data-level=\"l5\"]')).borderStyle") == "double"
    context.close()


def test_play_calls_onstart_with_the_level_and_closes_returning_focus(browser):
    context, page = open_page(browser, script=FACTORY)
    create(page, state={"done": ["l1", "l2", "l3", "l4"]})
    page.focus("#levels-open-button")
    page.keyboard.press("Enter")
    assert page.locator("#level-select").is_visible()
    assert focused_level(page) == "l5", "focus lands on the next level to play"
    page.keyboard.press("Enter")
    assert page.evaluate("started") == ["l5:mode"]
    assert page.locator("#level-select").is_hidden()
    assert page.evaluate("document.activeElement.id") == "levels-open-button"
    context.close()


def test_locked_levels_are_focusable_explain_themselves_and_do_not_start(browser):
    context, page = open_page(browser, script=FACTORY)
    create(page)
    page.click("#levels-open-button")
    assert focused_level(page) == "l1"
    page.keyboard.press("ArrowRight")
    assert focused_level(page) == "l2"
    page.keyboard.press("Enter")
    page.wait_for_timeout(80)
    assert page.evaluate("started") == []
    assert page.locator(".level-live").inner_text() == "Level 2 is locked. Complete Level 1 first."
    assert page.locator("#level-select").is_visible()
    describedby = page.evaluate("document.activeElement.getAttribute('aria-describedby').split(' ').map((i) => document.getElementById(i).textContent)")
    assert describedby[0].startswith("⊘ Locked")
    context.close()


def test_arrow_keys_move_by_card_and_by_row_with_one_tab_stop(browser):
    context, page = open_page(browser, script=FACTORY)
    create(page)
    page.click("#levels-open-button")
    cols = page.evaluate("""() => { const t = document.querySelectorAll('.level-card')[0].offsetTop;
      return [...document.querySelectorAll('.level-card')].filter((c) => c.offsetTop === t).length; }""")
    assert cols == 5, "rows of five on a wide screen"
    assert page.evaluate("[...document.querySelectorAll('.level-play')].filter((b) => b.tabIndex === 0).length") == 1
    page.keyboard.press("ArrowDown")
    assert focused_level(page) == "l6"
    page.keyboard.press("ArrowDown")
    assert focused_level(page) == "l11"
    page.keyboard.press("ArrowDown")
    assert focused_level(page) == "l11", "no row below"
    page.keyboard.press("ArrowUp")
    assert focused_level(page) == "l6"
    page.keyboard.press("End")
    assert focused_level(page) == "l10"
    page.keyboard.press("Home")
    assert focused_level(page) == "l6"
    page.keyboard.press("Shift+End")
    assert focused_level(page) == "l12"
    page.keyboard.press("Shift+Home")
    assert focused_level(page) == "l1"
    page.keyboard.press("ArrowLeft")
    assert focused_level(page) == "l1"
    context.close()


def test_tab_stays_inside_the_dialog_and_escape_closes(browser):
    context, page = open_page(browser, script=FACTORY)
    create(page)
    page.focus("#levels-open-button")
    page.keyboard.press("Enter")
    page.keyboard.press("Tab")
    assert page.evaluate("document.activeElement.textContent") == "Close"
    page.keyboard.press("Tab")
    assert focused_level(page) == "l1", "wraps back to the levels"
    page.keyboard.press("Shift+Tab")
    assert page.evaluate("document.activeElement.textContent") == "Close"
    page.keyboard.press("Escape")
    assert page.locator("#level-select").is_hidden()
    assert page.evaluate("document.activeElement.id") == "levels-open-button"
    context.close()


def test_can_play_gate_and_unlock_text(browser):
    context, page = open_page(browser, script=FACTORY)
    page.evaluate("""(levels) => {
      levels[0].unlock_text = 'Buy the Poacher Pass in the Seed Vault';
      window.ls = NoyvjLevels.create({ levels, onChange() {}, canPlay: (l) => (l.id === 'l1' ? 'Needs the Poacher Pass' : true), trigger: '#levels-open-button' });
    }""", make_levels()["levels"])
    page.click("#levels-open-button")
    assert page.locator('.level-card[data-level="l1"] .level-status').inner_text() == "⊘ Locked: Needs the Poacher Pass"
    assert page.evaluate("ls.start('l1')") is False
    page.evaluate("ls.configure({ canPlay: () => true })")
    assert page.locator('.level-card[data-level="l1"]').get_attribute("data-state") == "ready"
    context.close()


def test_text_is_never_interpreted_as_html(browser):
    context, page = open_page(browser, script=FACTORY)
    page.evaluate("""() => { NoyvjLevels.create({ levels: [{ id: 'x', title: '<img src=x onerror=window.pwned=1>', blurb: '<b>bold</b>', kind: 'level' }],
      onChange() {}, trigger: '#levels-open-button' }); }""")
    page.click("#levels-open-button")
    assert page.evaluate("window.pwned") is None
    assert page.locator(".level-card b").count() == 0
    assert "<b>bold</b>" in page.locator(".level-card p:not(.level-best)").inner_text()
    context.close()


@pytest.mark.parametrize("size", [(1440, 900), (360, 740)])
@pytest.mark.parametrize("theme", ["dark", "light"])
def test_layout_in_both_themes_and_sizes(browser, size, theme):
    context, page = open_page(browser, script=FACTORY, size=size, theme=theme)
    create(page, state={"done": ["l1", "l2"]})
    page.click("#levels-open-button")
    geo = page.evaluate("""() => { const p = document.querySelector('.level-select-panel').getBoundingClientRect();
      const cs = getComputedStyle(document.querySelector('.level-select-panel'));
      return { l: p.left, r: p.right, t: p.top, b: p.bottom, vw: innerWidth, vh: innerHeight, bg: cs.backgroundColor, fg: cs.color,
               overflowY: cs.overflowY, sw: document.documentElement.scrollWidth,
               small: [...document.querySelectorAll('.level-select button')].filter((b) => b.getBoundingClientRect().height < 40).length }; }""")
    assert geo["l"] >= 0 and geo["r"] <= geo["vw"] and geo["t"] >= 0 and geo["b"] <= geo["vh"]
    assert geo["sw"] <= geo["vw"]
    assert geo["small"] == 0
    assert geo["overflowY"] == "auto"
    assert (geo["bg"] == "rgb(247, 248, 252)") == (theme == "light")
    context.close()


def test_reduced_motion_removes_card_transitions(browser):
    context, page = open_page(browser, script=FACTORY)
    create(page)
    page.click("#levels-open-button")
    assert page.evaluate("getComputedStyle(document.querySelector('.level-card')).transitionDuration") != "0s"
    page.evaluate("document.documentElement.setAttribute('data-reduced-motion', 'true')")
    assert page.evaluate("getComputedStyle(document.querySelector('.level-card')).transitionDuration") == "0s"
    context.close()
