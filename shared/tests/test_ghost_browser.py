"""shared/ghost.js in headless Chromium (planning/TODO.md Z-3b). The decisive test: the JavaScript cleaning,
turn reading, comparison and summary agree with shared/ghost.py exactly, on many inputs (clean, hostile
and thinned). Then the drawn line: faint, dashed, labelled, behind the chart's own lines, toggleable,
accessible, safe on bad input, and it never touches the network."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import ghost as gh  # noqa: E402
import seed as sd  # noqa: E402
from conftest import page_html  # noqa: E402

PAGE = page_html(
    '<style>body{margin:0;padding:12px;font-family:system-ui;background:#12162a;color:#eee}</style>',
    '<h1>Game</h1><label><input type="checkbox" id="tog"> Ghost</label><p id="sum" role="status"></p>'
    '<svg id="chart" viewBox="0 0 400 200" width="400" height="200" role="img" aria-label="Trend">'
    '<polyline id="mine" points="0,180 100,120 200,80 300,60 400,40" fill="none" stroke="#6af"/></svg>'
    '<script src="/shared/ghost.js"></script>')

BEST = {"v": 1, "turns": 5, "values": [0, 10, 20, 30, 40], "label": "Run 3"}


def open_page(harness, init=(), **kw):
    h = harness(init_scripts=list(init), **kw)
    h.pages["/t.html"] = PAGE
    h.goto()
    return h


# --------------------------------------------------------------------------------------------
# Python and JavaScript agree
# --------------------------------------------------------------------------------------------
def raw_corpus():
    r = sd.Rng("ghost-identity")
    junk = [None, "7", "x", True, False, [], [1], {}, float("nan"), float("inf"), float("-inf"), 1e30, -1e30, -0.0]
    out = []
    for _ in range(160):
        n = r.choice([0, 1, 2, 3, 9, 40, 119, 120, 121, 300, 1000])
        vals = []
        for _ in range(n):
            if r.chance(0.08):
                vals.append(r.choice(junk))
            else:
                vals.append(r.choice([r.randint(-50, 5000), round(r.uniform(-100, 100), 3), r.random() * 10 ** r.randint(0, 9)]))
        turns = r.choice([None, n, n + 1, max(0, n - 3), n * 3, 0, -4, 7, 100000, 10 ** 7, 2.9, "9", True, float("nan")])
        d = {"v": 1, "values": vals, "label": r.choice(["", "Run 3", "  spaced   out ", "x" * 80, "a\x01b", "日本語", "tab\there"])}
        if turns is not None:
            d["turns"] = turns
        out.append(d)
    out += [None, 5, "x", [], [1, 2, 3], {}, {"values": 5}, {"values": list(range(5001))}, {"values": list(range(5000)), "turns": 5000}]
    return out


def js_safe(x):
    """json cannot carry nan/inf: encode them the way the test page decodes them."""
    if isinstance(x, float) and (x != x or x in (float("inf"), float("-inf"))):
        return {"__num__": repr(x)}
    if isinstance(x, list):
        return [js_safe(i) for i in x]
    if isinstance(x, dict):
        return {k: js_safe(v) for k, v in x.items()}
    return x


DECODE = """const dec = (x) => Array.isArray(x) ? x.map(dec) : (x && typeof x === 'object')
  ? ('__num__' in x ? ({'nan': NaN, 'inf': Infinity, '-inf': -Infinity})[x.__num__] : Object.fromEntries(Object.entries(x).map(([k, v]) => [k, dec(v)]))) : x;"""


def test_load_agrees_with_python_on_many_inputs(harness):
    h = open_page(harness)
    corpus = raw_corpus()
    got = h.page.evaluate(DECODE + "; (items) => items.map((x) => NoyvjGhost.load(dec(x)))", js_safe(corpus))
    assert len(got) == len(corpus) > 150
    for raw, js in zip(corpus, got):
        assert js == gh.load(raw), str(raw)[:120]
    assert sum(1 for g in got if g) > 50
    assert not h.errors


def test_value_at_and_compare_and_summary_agree_with_python(harness):
    h = open_page(harness)
    r = sd.Rng("ghost-compare")
    cases = []
    for _ in range(200):
        n = r.choice([2, 5, 30, 120, 400, 2000])
        best = gh.make_trace([r.uniform(0, 100) + i * r.random() for i in range(n)], label="b")
        m = r.choice([1, 2, 5, n // 2 or 1, n, n + 3])
        live = [r.choice([r.randint(0, 200), round(r.uniform(0, 200), 3), None, "x"] if r.chance(0.1) else [r.randint(0, 200)]) for _ in range(m)]
        cases.append({"trace": best, "live": live, "higher": r.chance(0.7), "unit": r.choice(["", "%", " funds"]),
                      "who": r.choice(["", "your Run 3", "the ghost"]),
                      "turns": [0, 1, 2, n // 2, n, n + 1, 2.7, -3]})
    js = h.page.evaluate("""(cases) => cases.map((c) => {
      const res = NoyvjGhost.compare(c.live, c.trace, c.higher);
      return { reads: c.turns.map((t) => NoyvjGhost.valueAt(c.trace, t)), res,
               text: NoyvjGhost.summary(res, c.who, c.unit) };
    })""", cases)
    for c, got in zip(cases, js):
        assert got["reads"] == [gh.value_at(c["trace"], t) for t in c["turns"]]
        want = gh.compare(c["live"], c["trace"], c["higher"])
        assert got["res"] == want
        assert got["text"] == gh.summary(want, c["who"], c["unit"])
    assert {gh.compare(c["live"], c["trace"], c["higher"])["status"] for c in cases} >= {"ahead", "behind", "ended"}
    assert h.page.evaluate("[NoyvjGhost.compare([], %s), NoyvjGhost.compare(null, %s)]" % (json.dumps(BEST), json.dumps(BEST))) == [None, None]


def test_make_trace_and_format_number_agree(harness):
    h = open_page(harness)
    inputs = [[0, 1, 2, 3], [5], [], ["a", 1, None, 2], list(range(500)), [1.005, 2.675, -0.125, 0.125, 1e13]]
    js = h.page.evaluate("(items) => items.map((v) => NoyvjGhost.makeTrace(v, undefined, 'L'))", inputs)
    assert js == [gh.make_trace(v, label="L") for v in inputs]
    nums = [0, 5, 5.5, 5.25, 5.254, 5.256, 1234567.891, 0.005, 0.004, -3.5, 99999999999.999]
    assert h.page.evaluate("(n) => n.map(NoyvjGhost.formatNumber)", nums) == [gh.format_number(x) for x in nums]


def test_a_python_recorder_trace_is_read_the_same_by_javascript(harness):
    h = open_page(harness)
    rec = gh.Recorder()
    for i in range(700):
        rec.record((i * 13) % 97 / 4)
    trace = rec.trace("Pilot")
    assert len(trace["values"]) <= gh.MAX_LEN
    reads = h.page.evaluate("([t, turns]) => turns.map((n) => NoyvjGhost.valueAt(t, n))", [trace, list(range(0, 705, 7))])
    assert reads == [gh.value_at(trace, n) for n in range(0, 705, 7)]


# --------------------------------------------------------------------------------------------
# drawing
# --------------------------------------------------------------------------------------------
DRAW = """(opts) => {
  window.g = NoyvjGhost.draw(document.getElementById('chart'), Object.assign({
    trace: %s, live: [0, 8, 15, 33, 50], turns: 5, label: 'Best run',
    x: { left: 0, right: 400 }, y: { top: 20, bottom: 180, min: 0, max: 50 },
    summaryEl: document.getElementById('sum') }, opts || {}));
  return !!window.g;
}""" % json.dumps(BEST)


def test_draws_a_dashed_labelled_line_behind_the_chart(harness):
    h = open_page(harness)
    assert h.page.evaluate(DRAW)
    info = h.page.evaluate("""() => {
      const svg = document.getElementById('chart');
      const g = svg.querySelector('[data-noyvj-ghost]');
      const line = g.querySelector('polyline');
      return { first: svg.firstElementChild === g, points: line.getAttribute('points'),
               dash: line.getAttribute('stroke-dasharray'), opacity: line.getAttribute('opacity'),
               label: g.querySelector('text').textContent, role: g.getAttribute('role'),
               aria: g.getAttribute('aria-label'), title: g.querySelector('title').textContent,
               pe: g.getAttribute('pointer-events'), testid: g.getAttribute('data-testid'),
               summary: document.getElementById('sum').textContent, ns: g.namespaceURI,
               mine: document.getElementById('mine') !== null };
    }""")
    assert info["first"] and info["mine"]
    # y: value 0 at the bottom (180), 50 at the top (20); x spread over 5 turns across 0..400
    assert info["points"] == "0.0,180.0 100.0,148.0 200.0,116.0 300.0,84.0 400.0,52.0"
    assert info["dash"] and float(info["opacity"]) < 1
    assert info["label"] == "Ghost: Best run"
    assert info["role"] == "img" and info["pe"] == "none" and info["testid"] == "ghost-line"
    assert info["summary"] == info["aria"] == info["title"] == "ghost: you are 10 ahead of your best run at turn 5"
    assert info["ns"] == "http://www.w3.org/2000/svg"
    assert not h.errors and h.api_calls == []


def test_behind_summary_and_lower_is_better(harness):
    h = open_page(harness)
    h.page.evaluate(DRAW, {"live": [0, 5, 9]})
    assert h.page.inner_text("#sum") == "ghost: your best run was 11 ahead at turn 3"
    h.page.evaluate("() => window.g.update({ higherIsBetter: false })")
    assert h.page.inner_text("#sum") == "ghost: you are 11 ahead of your best run at turn 3"
    h.page.evaluate("() => window.g.update({ higherIsBetter: true, unit: '%', who: 'your Run 3' })")
    assert h.page.inner_text("#sum") == "ghost: your Run 3 was 11% ahead at turn 3"
    assert h.page.evaluate("window.g.summary()") == h.page.inner_text("#sum")


def test_show_hide_toggle_and_the_summary_follows(harness):
    h = open_page(harness)
    h.page.evaluate(DRAW)
    disp = "document.querySelector('[data-noyvj-ghost]').style.display"
    assert h.page.evaluate("window.g.isOn()") is True and h.page.evaluate(disp) == ""
    assert h.page.evaluate("window.g.hide()") is False
    assert h.page.evaluate(disp) == "none" and h.page.inner_text("#sum") == ""
    assert h.page.get_attribute("[data-noyvj-ghost]", "aria-hidden") == "true"
    assert h.page.evaluate("window.g.toggle()") is True
    assert h.page.evaluate(disp) == "" and h.page.inner_text("#sum").startswith("ghost: ")
    assert h.page.evaluate("window.g.toggle(false)") is False
    h.page.evaluate("() => window.g.show()")
    assert h.page.get_attribute("[data-noyvj-ghost]", "aria-hidden") == "false"


def test_starts_hidden_when_asked(harness):
    h = open_page(harness)
    h.page.evaluate(DRAW, {"on": False})
    assert h.page.evaluate("document.querySelector('[data-noyvj-ghost]').style.display") == "none"
    assert h.page.evaluate("window.g.isOn()") is False and h.page.inner_text("#sum") == ""


def test_bind_toggle_checkbox_and_remembered_choice(harness):
    h = open_page(harness)
    h.page.evaluate(DRAW)
    h.page.evaluate("() => NoyvjGhost.bindToggle(document.getElementById('tog'), window.g, { storageKey: 'ghost-test' })")
    assert h.page.is_checked("#tog")
    h.page.uncheck("#tog")
    assert h.page.evaluate("window.g.isOn()") is False
    assert h.page.evaluate("localStorage.getItem('ghost-test')") == "0"
    h.page.check("#tog")
    assert h.page.evaluate("window.g.isOn()") is True and h.page.evaluate("localStorage.getItem('ghost-test')") == "1"
    # a later page load picks the saved choice up
    h.page.evaluate("localStorage.setItem('ghost-test', '0')")
    h.page.evaluate("() => { window.g.destroy(); }")
    h.page.evaluate(DRAW)
    h.page.evaluate("() => NoyvjGhost.bindToggle(document.getElementById('tog'), window.g, { storageKey: 'ghost-test' })")
    assert not h.page.is_checked("#tog") and h.page.evaluate("window.g.isOn()") is False


def test_bind_toggle_survives_blocked_storage(harness):
    h = open_page(harness, init=["Object.defineProperty(window, 'localStorage', {get() { throw new Error('blocked'); }});"])
    h.page.evaluate(DRAW)
    h.page.evaluate("() => NoyvjGhost.bindToggle(document.getElementById('tog'), window.g, { storageKey: 'k' })")
    h.page.uncheck("#tog")
    assert h.page.evaluate("window.g.isOn()") is False
    assert not h.errors


def test_update_redraws_on_a_rerendered_svg(harness):
    h = open_page(harness)
    h.page.evaluate(DRAW)
    h.page.evaluate("""() => { const s = document.getElementById('chart'); s.innerHTML = '<polyline points="0,0 1,1"/>'; }""")
    assert h.page.locator("[data-noyvj-ghost]").count() == 0
    h.page.evaluate("() => window.g.update({ live: [0, 10, 20] })")
    assert h.page.locator("[data-noyvj-ghost]").count() == 1
    assert h.page.evaluate("document.getElementById('chart').firstElementChild.hasAttribute('data-noyvj-ghost')")
    assert h.page.inner_text("#sum") == "ghost: level with your best run at turn 3"
    # a game that replaces the whole svg passes the new one
    h.page.evaluate("""() => { const old = document.getElementById('chart'); const n = old.cloneNode(false);
      n.id = 'chart2'; old.replaceWith(n); window.g.update({ svg: n }); }""")
    assert h.page.locator("#chart2 [data-noyvj-ghost]").count() == 1 and h.page.locator("[data-noyvj-ghost]").count() == 1


def test_destroy_removes_the_line_and_the_text(harness):
    h = open_page(harness)
    h.page.evaluate(DRAW)
    h.page.evaluate("() => window.g.destroy()")
    assert h.page.locator("[data-noyvj-ghost]").count() == 0 and h.page.inner_text("#sum") == ""


def test_function_axis_mappings_and_clamping(harness):
    h = open_page(harness)
    h.page.evaluate(DRAW, {"x": None, "y": None})   # None -> null: no usable mapping draws nothing
    assert h.page.locator("[data-noyvj-ghost] polyline").count() == 0
    h.page.evaluate("""() => window.g.update({ x: (t) => t * 10, y: (v) => 200 - v })""")
    assert h.page.get_attribute("[data-noyvj-ghost] polyline", "points") == "10.0,200.0 20.0,190.0 30.0,180.0 40.0,170.0 50.0,160.0"
    # y values outside min..max are clamped inside the chart
    h.page.evaluate("() => window.g.update({ x: { left: 0, right: 400 }, y: { top: 20, bottom: 180, min: 0, max: 20 } })")
    ys = [float(p.split(",")[1]) for p in h.page.get_attribute("[data-noyvj-ghost] polyline", "points").split()]
    assert min(ys) == 20 and max(ys) == 180
    # flat axis (min == max) does not divide by zero
    h.page.evaluate("() => window.g.update({ y: { top: 20, bottom: 180, min: 5, max: 5 } })")
    assert set(h.page.get_attribute("[data-noyvj-ghost] polyline", "points").replace(",", " ").split()[1::2]) == {"100.0"}


def test_chart_shorter_than_the_ghost_draws_only_the_shared_turns(harness):
    h = open_page(harness)
    h.page.evaluate(DRAW, {"turns": 3, "live": [0, 5, 9]})
    assert h.page.get_attribute("[data-noyvj-ghost] polyline", "points") == "0.0,180.0 200.0,148.0 400.0,116.0"
    # a longer chart than the ghost: the line simply stops where the ghost's run ended
    h.page.evaluate("() => window.g.update({ turns: 9, live: [0, 1, 2, 3, 4, 5, 6] })")
    pts = h.page.get_attribute("[data-noyvj-ghost] polyline", "points").split()
    assert len(pts) == 5 and pts[-1].startswith("200.0,")
    assert h.page.inner_text("#sum") == "ghost: your best run ended before turn 7"


def test_long_traces_draw_a_bounded_number_of_points(harness):
    h = open_page(harness)
    long_trace = gh.make_trace([i % 50 for i in range(3000)])
    h.page.evaluate(DRAW, {"trace": long_trace, "turns": 3000, "live": [1, 2, 3]})
    n = len(h.page.get_attribute("[data-noyvj-ghost] polyline", "points").split())
    assert 100 <= n <= 400


@pytest.mark.parametrize("bad", [None, 5, "x", [], {}, {"values": [1]}, {"values": "no", "turns": 9}, {"turns": 5}])
def test_unusable_traces_draw_nothing_and_say_so(harness, bad):
    h = open_page(harness)
    assert h.page.evaluate(DRAW, {"trace": bad})
    assert h.page.locator("[data-noyvj-ghost]").count() == 0
    assert h.page.inner_text("#sum") == "ghost: no earlier run to race yet"
    assert not h.errors


def test_hostile_text_is_never_written_as_markup(harness):
    h = open_page(harness)
    evil = {"turns": 3, "values": [1, 2, 3], "label": '<img src=x onerror="window.__pwned=1">'}
    h.page.evaluate(DRAW, {"trace": evil, "label": '<b>x</b>', "who": '<script>window.__pwned=1</script>', "live": [0, 0]})
    assert h.page.evaluate("window.__pwned") is None
    assert h.page.locator("#sum b, #sum img, [data-noyvj-ghost] b, [data-noyvj-ghost] img").count() == 0
    assert "<b>" in h.page.text_content("[data-noyvj-ghost] text")   # shown as plain text


def test_draw_on_a_missing_svg_is_a_quiet_none(harness):
    h = open_page(harness)
    assert h.page.evaluate("NoyvjGhost.draw(null, {})") is None
    assert h.page.evaluate("NoyvjGhost.draw(undefined)") is None
    assert not h.errors


def test_line_colour_comes_from_a_css_variable(harness):
    h = open_page(harness)
    h.page.evaluate(DRAW)
    h.page.add_style_tag(content=":root{--ghost-color:#ff00ff}")
    color = h.page.evaluate("getComputedStyle(document.querySelector('.noyvj-ghost-line')).stroke")
    assert color.replace(" ", "") in ("rgb(255,0,255)", "#ff00ff")
