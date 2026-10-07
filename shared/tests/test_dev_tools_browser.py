"""shared/error-boundary.js (Z-25), shared/debug-overlay.js (Z-24), shared/perf-mark.js (Z-21) and
shared/info-footer.js (Z-29) in headless Chromium."""

import json
import re

from conftest import ORIGIN, page_html

FAKE_PY = """
window.fakeState = {season: 4, resources: {food: 12.5}, name: "caf\\u00e9"};
window.makePyodide = () => ({ globals: { get: (name) => name === 'get_state' ?
  Object.assign(() => ({ toJs: () => window.fakeState, destroy() {} }), { destroy() {} }) : undefined } });
"""


# ---- error boundary --------------------------------------------------------

def boundary_page(harness, extra_body="", init=()):
    h = harness(init_scripts=list(init))
    h.pages["/t.html"] = page_html('<script src="/shared/error-boundary.js" data-game-id="demo"></script>',
                                   "<main id='game'>game</main>" + extra_body)
    h.goto()
    return h


def panel(page):
    return page.query_selector("#noyvj-error-panel")


def test_an_uncaught_error_shows_one_friendly_panel(harness):
    h = boundary_page(harness)
    h.page.evaluate("setTimeout(() => { throw new Error('boom from a handler'); }, 0)")
    h.page.wait_for_selector("#noyvj-error-panel")
    p = panel(h.page)
    assert p.get_attribute("role") == "alert"
    text = p.inner_text()
    assert "Something went wrong" in text and "saved game has not been touched" in text
    assert "boom from a handler" in text
    assert [b.inner_text() for b in p.query_selector_all("button")] == ["Copy details", "Reload page", "Dismiss"]
    h.page.evaluate("setTimeout(() => { throw new Error('boom from a handler'); }, 0)")
    h.page.wait_for_function("document.querySelector('#noyvj-error-last').textContent.includes('2 errors')")
    assert len(h.page.query_selector_all("#noyvj-error-panel")) == 1


def test_unhandled_rejections_and_python_style_errors_are_caught(harness):
    h = boundary_page(harness)
    h.page.evaluate("""() => { class PythonError extends Error { constructor(m) { super(m); this.name = 'PythonError'; } }
      Promise.reject(new PythonError('Traceback ... KeyError: farmers')); }""")
    h.page.wait_for_selector("#noyvj-error-panel")
    assert "PythonError: Traceback" in panel(h.page).inner_text()


def test_noise_is_not_reported(harness):
    h = boundary_page(harness)
    h.page.evaluate("""() => {
      Promise.reject(new TypeError('Failed to fetch'));
      Promise.reject(new DOMException('aborted', 'AbortError'));
      window.dispatchEvent(new ErrorEvent('error', {message: 'ResizeObserver loop completed with undelivered notifications.'}));
      window.dispatchEvent(new ErrorEvent('error', {message: 'Script error.'}));
      window.dispatchEvent(new ErrorEvent('error', {message: 'adsbygoogle.push() error: No slot size', filename: 'https://pagead2.googlesyndication.com/x.js', lineno: 1}));
      const img = document.createElement('img'); img.src = '/missing.png'; document.body.append(img);
    }""")
    h.page.wait_for_timeout(300)
    assert panel(h.page) is None and h.page.evaluate("NoyvjErrors.count()") == 0


def test_dismiss_hides_and_a_new_error_reopens(harness):
    h = boundary_page(harness)
    h.page.evaluate("NoyvjErrors.report(new Error('first'), 'test')")
    h.page.click("#noyvj-error-dismiss")
    assert panel(h.page) is None
    h.page.evaluate("NoyvjErrors.report(new Error('second'), 'test')")
    assert panel(h.page) is not None and "second" in panel(h.page).inner_text()


COPY_VIA_EXEC_COMMAND = ("document.execCommand = () => { const t = document.querySelector('textarea[readonly]');"
                         " window.__copied = t && t.value; return true; };")
COPY_VIA_CLIPBOARD = ("Object.defineProperty(navigator, 'clipboard', {value: {writeText: (t) => { window.__copied = t; return Promise.resolve(); }}});")


def assert_clean_report(clip):
    for needle in ("NoyvjGames error report", "game: demo", "RangeError: too deep", "browser: ", "window: ", "lite mode: n/a"):
        assert needle in clip, needle
    assert "secret-token" not in clip and "SAVECODE123" not in clip, "no save codes or tokens in the report"


def test_copy_details_puts_a_plain_report_on_the_clipboard_without_saves(harness):
    for init in (COPY_VIA_CLIPBOARD, COPY_VIA_EXEC_COMMAND):      # a secure page, and the older fallback
        h = boundary_page(harness, init=[init])
        h.page.evaluate("localStorage.setItem('hub_bearer_token', 'secret-token'); localStorage.setItem('sol:save', 'SAVECODE123')")
        h.page.evaluate("NoyvjErrors.report(new RangeError('too deep'), 'test')")
        h.page.click("#noyvj-error-copy")
        h.page.wait_for_function("document.getElementById('noyvj-error-copy').textContent === 'Copied'")
        assert_clean_report(h.page.evaluate("window.__copied"))


def test_a_failed_copy_says_so(harness):
    h = boundary_page(harness, init=["document.execCommand = () => false;"])
    h.page.evaluate("NoyvjErrors.report(new Error('x'), 'test')")
    h.page.click("#noyvj-error-copy")
    h.page.wait_for_function("document.getElementById('noyvj-error-copy').textContent === 'Could not copy'")


def test_the_boundary_never_touches_storage_and_tags_stay_text(harness):
    h = boundary_page(harness)
    before = h.page.evaluate("JSON.stringify(Object.assign({}, localStorage))")
    h.page.evaluate("NoyvjErrors.report(new Error('<img src=x onerror=alert(1)>'), 'test')")
    assert h.page.evaluate("JSON.stringify(Object.assign({}, localStorage))") == before
    assert h.page.query_selector("#noyvj-error-panel img") is None
    assert "<img" in panel(h.page).inner_text()


def test_light_theme_panel_is_readable(harness):
    h = harness()
    h.pages["/t.html"] = page_html('<script src="/shared/error-boundary.js"></script>', "<p>x</p>", 'data-theme="light"')
    h.goto()
    h.page.evaluate("NoyvjErrors.report(new Error('x'), 'test')")
    assert h.page.evaluate("getComputedStyle(document.getElementById('noyvj-error-panel')).backgroundColor") == "rgb(255, 248, 236)"


# ---- debug overlay ---------------------------------------------------------

def debug_page(harness, query="", extra_head=""):
    h = harness(init_scripts=[FAKE_PY])
    h.pages["/t.html"] = page_html(extra_head + '<script src="/shared/debug-overlay.js"></script>', "<p>game</p>")
    h.goto("/t.html" + query)
    return h


def test_debug_overlay_is_completely_inert_without_the_flag(harness):
    for query in ("", "?debug=0", "?debug=true", "?debugger=1"):
        h = harness(init_scripts=[FAKE_PY])
        h.pages["/t.html"] = page_html("<script>window.fetch0 = window.fetch;</script>"
                                       '<script src="/shared/debug-overlay.js"></script>', "<p>game</p>")
        h.goto("/t.html" + query)
        h.page.wait_for_timeout(200)
        assert h.page.query_selector("#noyvj-debug-overlay") is None, query
        assert h.page.evaluate("window.fetch === window.fetch0"), "fetch must not be patched"
        assert h.page.evaluate("NoyvjDebug.active") is False


def test_debug_overlay_shows_fps_state_size_and_last_save_length(harness):
    h = debug_page(harness, "?debug=1", '<script>window.fetch0 = window.fetch;</script>')
    h.page.evaluate("window.pyodide = makePyodide(); NoyvjDebug.measureState()")
    h.page.wait_for_function("/fps\\s+[1-9]/.test(document.getElementById('noyvj-debug-overlay').textContent)", timeout=5000)
    text = h.page.inner_text("#noyvj-debug-overlay")
    expected = len(json.dumps({"season": 4, "resources": {"food": 12.5}, "name": "café"}, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    assert f"state      {expected} B" in text
    assert "last save  none yet" in text
    body = json.dumps({"save_data": {"x": "é" * 10}})
    h.page.evaluate("(b) => fetch('https://noyvjgames.fastapicloud.dev/saves', {method: 'POST', body: b}).catch(() => {})", body)
    assert h.page.evaluate("NoyvjDebug.snapshot().saveBytes") == len(body.encode("utf-8"))
    h.page.evaluate("(b) => fetch('https://noyvjgames.fastapicloud.dev/users/me/saves/sol/slots/2', {method: 'PUT', body: b}).catch(() => {})", body + "xx")
    assert h.page.evaluate("NoyvjDebug.snapshot().saveBytes") == len(body.encode("utf-8")) + 2
    h.page.evaluate("fetch('https://noyvjgames.fastapicloud.dev/ratings/sol', {method: 'POST', body: 'zz'}).catch(() => {})")
    assert h.page.evaluate("NoyvjDebug.snapshot().saveBytes") == len(body.encode("utf-8")) + 2, "only save endpoints count"
    assert h.page.evaluate("document.getElementById('noyvj-debug-overlay').getAttribute('aria-hidden')") == "true"
    assert h.page.evaluate("getComputedStyle(document.getElementById('noyvj-debug-overlay')).pointerEvents") == "none"


def test_debug_overlay_survives_a_broken_state_function(harness):
    h = debug_page(harness, "?debug=1")
    h.page.evaluate("window.pyodide = {globals: {get: () => { throw new Error('nope'); }}}; NoyvjDebug.measureState()")
    assert "state      n/a" in h.page.inner_text("#noyvj-debug-overlay")
    assert h.errors == []


# ---- perf marks -------------------------------------------------------------

def perf_page(harness, tag_extra=""):
    h = harness(init_scripts=[FAKE_PY])
    h.pages["/t.html"] = page_html(f'<script src="/shared/perf-mark.js" data-game-id="demo"{tag_extra}></script>', "<p>game</p>")
    h.goto()
    return h


def test_perf_marks_follow_the_boot_in_order_with_one_log_format(harness):
    h = perf_page(harness)
    h.page.wait_for_function("NoyvjPerf.marks()['dom-ready'] !== undefined")
    assert set(h.page.evaluate("NoyvjPerf.marks()")) == {"script-start", "dom-ready"}
    h.page.wait_for_timeout(120)
    h.page.evaluate("window.pyodide = {globals: {get: () => undefined}}")
    h.page.wait_for_function("NoyvjPerf.marks()['pyodide-loaded'] !== undefined")
    assert "game-setup-done" not in h.page.evaluate("NoyvjPerf.marks()"), "no get_state yet"
    h.page.evaluate("window.pyodide = makePyodide()")
    h.page.wait_for_function("NoyvjPerf.marks()['first-interactive'] !== undefined", timeout=5000)
    marks = h.page.evaluate("NoyvjPerf.marks()")
    order = ["script-start", "dom-ready", "pyodide-loaded", "game-setup-done", "first-interactive"]
    assert list(marks) == order and [marks[k] for k in order] == sorted(marks.values())
    lines = [t for kind, t in h.console if t.startswith("[noyvj-perf]")]
    assert len(lines) == 6
    for name, line in zip(order, lines):
        assert re.fullmatch(rf"\[noyvj-perf\] demo {name} \d+ms", line), line
    assert re.fullmatch(r"\[noyvj-perf\] demo boot \d+ms \(pyodide \d+ms, game setup \d+ms, first paint \d+ms\)", lines[-1])
    entries = h.page.evaluate("performance.getEntriesByType('mark').map(e => e.name).filter(n => n.startsWith('noyvj:'))")
    assert entries == [f"noyvj:{n}" for n in order]
    assert h.page.evaluate("performance.getEntriesByName('noyvj:boot').length") == 1
    summary = h.page.evaluate("NoyvjPerf.summary()")
    assert summary["game"] == "demo" and summary["total"] == marks["first-interactive"] - marks["script-start"]


def test_perf_marks_do_not_log_twice_on_repeat(harness):
    h = perf_page(harness)
    h.page.evaluate("window.pyodide = makePyodide()")
    h.page.wait_for_function("NoyvjPerf.marks()['first-interactive'] !== undefined", timeout=5000)
    h.page.wait_for_timeout(1800)       # the background-tab fallback timer fires too
    lines = [t for kind, t in h.console if t.startswith("[noyvj-perf]")]
    assert len(lines) == len(set(lines)) == 6


# ---- info footer ------------------------------------------------------------

CHANGELOG = json.dumps({"changelog": [{"date": "2026-09-01", "entry": "a"}, {"date": "2026-10-07", "entry": "b"}, {"date": "2026-09-20", "entry": "c"}]})


def test_footer_names_the_game_changelog_date_and_site_url(harness):
    h = harness()
    h.pages["/games/thaw/t.html"] = page_html(
        f'<script>window.CHANGELOG_JSON = {json.dumps(CHANGELOG)};</script><script src="/shared/info-footer.js" data-game-id="thaw"></script>',
        '<h1>Thaw</h1><section id="howto-panel"><h2>How</h2><p>steps</p></section><section id="info-page-panel" hidden></section>')
    h.goto("/games/thaw/t.html")
    h.page.wait_for_selector("#howto-panel .noyvj-info-footer")
    text = h.page.inner_text("#howto-panel .noyvj-info-footer")
    assert text == f"NoyvjGames · Thaw · updated 2026-10-07 · {ORIGIN}/"
    assert h.page.query_selector("#info-page-panel .noyvj-info-footer") is None, "an empty panel gets no footer"
    assert h.page.evaluate("document.getElementById('howto-panel').lastElementChild.className") == "noyvj-info-footer"


def test_footer_comes_back_when_the_game_rewrites_its_panel(harness):
    h = harness()
    h.pages["/games/thaw/t.html"] = page_html(
        '<script src="/shared/info-footer.js" data-game-id="thaw"></script>',
        '<h1>Thaw</h1><section id="info-page-panel"><p>old</p></section>')
    h.goto("/games/thaw/t.html")
    h.page.wait_for_selector("#info-page-panel .noyvj-info-footer")
    h.page.evaluate("document.getElementById('info-page-panel').innerHTML = '<p>new framing</p><ul><li>source</li></ul>'")
    h.page.wait_for_selector("#info-page-panel .noyvj-info-footer")
    assert h.page.evaluate("document.getElementById('info-page-panel').children.length") == 3
    assert h.page.evaluate("document.getElementById('info-page-panel').lastElementChild.className") == "noyvj-info-footer"
    # a text-only panel counts as content too
    h.page.evaluate("document.getElementById('info-page-panel').textContent = 'plain text'")
    h.page.wait_for_selector("#info-page-panel .noyvj-info-footer")


def test_footer_shows_a_seed_when_the_game_has_one_and_escapes_text(harness):
    h = harness()
    h.pages["/games/thaw/t.html"] = page_html(
        '<script>window.NOYVJ_SEED = "THAW-K7F2Q <b>x</b>";</script><script src="/shared/info-footer.js" data-game-id="thaw"></script>',
        '<h1>Thaw</h1><section id="howto-panel"><p>x</p></section>')
    h.goto("/games/thaw/t.html")
    h.page.wait_for_selector(".noyvj-info-footer")
    assert "seed THAW-K7F2Q <b>x</b>" in h.page.inner_text(".noyvj-info-footer")
    assert h.page.query_selector(".noyvj-info-footer b") is None
    seeded = h.page.evaluate("(() => { window.NoyvjSeed = {current: () => 'SEED-2'}; return NoyvjInfoFooter.text(); })()")
    assert "seed SEED-2" in seeded


def test_footer_tolerates_a_missing_or_broken_changelog(harness):
    for changelog in ("window.CHANGELOG_JSON = 'not json';", "window.CHANGELOG_JSON = [];", ""):
        h = harness()
        h.pages["/games/thaw/t.html"] = page_html(
            f'<script>{changelog}</script><script src="/shared/info-footer.js" data-game-id="thaw"></script>',
            '<h1>Thaw</h1><section id="howto-panel"><p>x</p></section>')
        h.goto("/games/thaw/t.html")
        h.page.wait_for_selector(".noyvj-info-footer")
        assert "updated" not in h.page.inner_text(".noyvj-info-footer")
        assert h.errors == []
