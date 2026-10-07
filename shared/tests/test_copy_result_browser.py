"""shared/copy-result.js (planning/TODO.md Z-20) in headless Chromium: the one-line result format and
the copy button with its text-box fallback. No network."""

import pytest

from conftest import page_html

PAGE = page_html('<style>body{margin:0;padding:12px;font-family:system-ui;background:#12162a;color:#eee}'
                 'html[data-theme="light"] body{background:#eef2fc;color:#1b2033}</style>',
                 '<h1>End screen</h1><div id="slot"></div>'
                 '<script src="/shared/copy-result.js" data-game-id="tide"></script>')

CLIPBOARD_OK = ("window.__copied = null; Object.defineProperty(navigator, 'clipboard', {configurable: true, "
                "value: {writeText: (t) => { window.__copied = t; return Promise.resolve(); }}});")
CLIPBOARD_BLOCKED = ("Object.defineProperty(navigator, 'clipboard', {configurable: true, "
                     "value: {writeText: () => Promise.reject(new Error('denied'))}}); document.execCommand = () => false;")


def open_page(harness, init=(), **kw):
    h = harness(init_scripts=list(init), **kw)
    h.pages["/t.html"] = PAGE
    h.goto()
    return h


def fmt(h, fields):
    return h.page.evaluate("f => NoyvjCopyResult.format(f)", fields)


def test_the_example_line_from_the_brief(harness):
    h = open_page(harness)
    assert fmt(h, {"game": "Tide", "score": 4210, "unit": "pts", "stats": [{"n": 3, "one": "storm survived", "many": "storms survived"}]}) \
        == "Tide, 4,210 pts, 3 storms survived"


def test_seed_is_appended_only_when_given(harness):
    h = open_page(harness)
    base = {"game": "Tide", "score": 4210, "unit": "pts", "stats": ["3 storms survived"]}
    assert fmt(h, base) == "Tide, 4,210 pts, 3 storms survived"
    assert fmt(h, {**base, "seed": "TIDE-K7F2Q"}) == "Tide, 4,210 pts, 3 storms survived (seed TIDE-K7F2Q)"
    for empty in ("", None, "   ", 5):
        assert "seed" not in fmt(h, {**base, "seed": empty})


def test_with_seed_uses_the_current_seed_when_the_module_is_loaded(harness):
    h = harness()
    h.pages["/t.html"] = page_html("", '<script src="/shared/seed.js"></script><script src="/shared/copy-result.js"></script>')
    h.goto()
    assert fmt(h, {"game": "Tide", "withSeed": True}) == "Tide"
    h.page.evaluate("NoyvjSeed.set('TIDE-K7F2Q')")
    assert fmt(h, {"game": "Tide", "withSeed": True}) == "Tide (seed TIDE-K7F2Q)"
    assert fmt(h, {"game": "Tide"}) == "Tide"
    plain = open_page(harness)
    assert fmt(plain, {"game": "Tide", "withSeed": True}) == "Tide"   # no seed module: nothing, no error
    assert not plain.errors


@pytest.mark.parametrize("fields,expected", [
    ({"game": "Grid"}, "Grid"),
    ({"game": "Grid", "score": 0, "unit": "pts"}, "Grid, 0 pts"),
    ({"game": "Grid", "score": 1234567}, "Grid, 1,234,567"),
    ({"game": "Grid", "score": 12.345, "unit": "%"}, "Grid, 12.35 %"),
    ({"game": "Grid", "score": "A+"}, "Grid, A+"),
    ({"game": "Grid", "stats": [None, False, "", "ok", 7]}, "Grid, ok, 7"),
    ({"game": "Grid", "stats": [{"n": 1, "one": "storm survived", "many": "storms survived"}]}, "Grid, 1 storm survived"),
    ({"game": "Grid", "stats": "not a list"}, "Grid"),
    ({"score": 5}, "5"),
    ({}, ""),
    (None, ""),
    ({"game": "A\nB   C", "stats": ["x\r\ny"]}, "A B C, x y"),
])
def test_format_cases(harness, fields, expected):
    assert fmt(open_page(harness), fields) == expected


def test_line_is_capped_and_plain_text(harness):
    h = open_page(harness)
    out = fmt(h, {"game": "Tide", "stats": ["x" * 400]})
    assert len(out) == 240 and out.endswith("…")
    assert fmt(h, {"game": "<b>Tide</b>"}) == "<b>Tide</b>"   # returned as text; the button writes textContent only


def test_link_line(harness):
    h = open_page(harness)
    assert fmt(h, {"game": "Tide", "link": True}) == "Tide\nhttp://harness.test/games/tide/"
    assert fmt(h, {"game": "Tide", "link": "https://example.test/t/"}) == "Tide\nhttps://example.test/t/"


def test_plural_helper(harness):
    h = open_page(harness)
    assert h.page.evaluate("[NoyvjCopyResult.plural(1, 'run', 'runs'), NoyvjCopyResult.plural(0, 'run', 'runs'), NoyvjCopyResult.plural(1500, 'run', 'runs')]") \
        == ["1 run", "0 runs", "1,500 runs"]


def test_button_copies_the_live_result_each_click(harness):
    h = open_page(harness, init=[CLIPBOARD_OK])
    h.page.evaluate("""() => { window.n = 1; window.copied = [];
      NoyvjCopyResult.mountButton('#slot', {getResult: () => ({game: 'Tide', score: n * 100, unit: 'pts'}), onCopy: (t) => copied.push(t)}); }""")
    btn = ".noyvj-cr-btn"
    h.page.click(btn)
    h.page.wait_for_function("window.__copied === 'Tide, 100 pts'")
    h.page.evaluate("n = 2")
    h.page.click(btn)
    h.page.wait_for_function("window.__copied === 'Tide, 200 pts'")
    assert h.page.evaluate("copied") == ["Tide, 100 pts", "Tide, 200 pts"]
    assert "✓ Copied: Tide, 200 pts" in h.page.inner_text(".noyvj-cr-status")
    assert h.page.get_attribute(".noyvj-cr-status", "aria-live") == "polite"
    assert h.api_calls == [] and not h.errors


def test_button_with_static_fields_and_update(harness):
    h = open_page(harness, init=[CLIPBOARD_OK])
    h.page.evaluate("window.b = NoyvjCopyResult.mountButton('#slot', {game: 'Tide', score: 5, label: 'Copy my score'})")
    assert "Copy my score" in h.page.inner_text(".noyvj-cr-btn")
    h.page.click(".noyvj-cr-btn")
    h.page.wait_for_function("window.__copied === 'Tide, 5'")
    h.page.evaluate("b.update({game: 'Tide', score: 9, seed: 'TIDE-K7F2Q'})")
    h.page.click(".noyvj-cr-btn")
    h.page.wait_for_function("window.__copied === 'Tide, 9 (seed TIDE-K7F2Q)'")


def test_button_falls_back_to_a_selected_text_box(harness):
    h = open_page(harness, init=[CLIPBOARD_BLOCKED])
    h.page.evaluate("NoyvjCopyResult.mountButton('#slot', {game: 'Tide', score: 4210, unit: 'pts'})")
    h.page.click(".noyvj-cr-btn")
    h.page.wait_for_selector(".noyvj-cr-box")
    assert h.page.input_value(".noyvj-cr-box") == "Tide, 4,210 pts"
    assert h.page.evaluate("document.activeElement.className") == "noyvj-cr-box"
    assert h.page.evaluate("document.activeElement.selectionEnd - document.activeElement.selectionStart") == len("Tide, 4,210 pts")
    assert "Ctrl+C" in h.page.inner_text(".noyvj-cr-status")


def test_button_with_nothing_to_copy_says_so(harness):
    h = open_page(harness, init=[CLIPBOARD_OK])
    h.page.evaluate("NoyvjCopyResult.mountButton('#slot', {getResult: () => ({})})")
    h.page.click(".noyvj-cr-btn")
    assert "Nothing to copy" in h.page.inner_text(".noyvj-cr-status")
    assert h.page.evaluate("window.__copied") is None


@pytest.mark.parametrize("size", [(1440, 900), (360, 740)])
@pytest.mark.parametrize("theme", ["dark", "light"])
def test_button_size_overflow_and_contrast(harness, size, theme):
    h = open_page(harness, size=size, touch=size[0] < 500)
    h.page.evaluate("t => document.documentElement.setAttribute('data-theme', t)", theme)
    h.page.evaluate("NoyvjCopyResult.mountButton('#slot', {game: 'Tide', score: 1})")
    assert h.page.evaluate("document.querySelector('.noyvj-cr-btn').getBoundingClientRect().height") >= 44
    assert h.page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    colors = h.page.evaluate("""() => { const s = getComputedStyle(document.querySelector('.noyvj-cr-btn'));
      return [s.color, s.backgroundColor]; }""")

    def lum(css):
        import re
        r, g, b = [int(float(x)) for x in re.findall(r"[\d.]+", css)[:3]]
        f = lambda c: ((c / 255 + 0.055) / 1.055) ** 2.4 if c / 255 > 0.03928 else c / 255 / 12.92  # noqa: E731
        return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)
    a, b = lum(colors[0]), lum(colors[1])
    assert (max(a, b) + 0.05) / (min(a, b) + 0.05) >= 4.5


def test_reduced_motion_removes_the_transition(harness):
    h = open_page(harness)
    h.page.evaluate("NoyvjCopyResult.mountButton('#slot', {game: 'Tide'})")
    assert h.page.evaluate("getComputedStyle(document.querySelector('.noyvj-cr-btn')).transitionDuration") != "0s"
    h.page.evaluate("document.documentElement.setAttribute('data-reduced-motion', 'true')")
    assert h.page.evaluate("getComputedStyle(document.querySelector('.noyvj-cr-btn')).transitionDuration") == "0s"
