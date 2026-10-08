"""Regression tests from the shared/ QA pass (planning/TODO.md QA-1 to QA-4): the cases the
per-component tests did not cover, namely a script included twice, localStorage that throws, and the
two timing races found while reading. Each test names the bug it pins.

Runs the real scripts in headless Chromium against the fake origin from conftest.py; nothing reaches
the network. Also holds one static test that keeps the decorative backgrounds off the main thread.
"""

import json
import re
from pathlib import Path

from conftest import ROOT, page_html

# Every storage call throws, as in a browser with site data blocked.
BLOCKED_STORAGE = """
for (const name of ['getItem', 'setItem', 'removeItem', 'clear', 'key']) {
  Storage.prototype[name] = function () { throw new DOMException('blocked', 'SecurityError'); };
}
"""


def script(name, attrs=""):
    return f'<script src="/shared/{name}" {attrs}></script>'


# ---- hub-auth.js ---------------------------------------------------------------------------------

def test_hub_auth_reads_as_signed_out_when_storage_throws_and_survives_a_second_include(harness):
    h = harness(init_scripts=[BLOCKED_STORAGE])
    h.pages["/t.html"] = page_html(script("hub-auth.js") + script("hub-auth.js"), "<p>x</p>")
    h.goto()
    assert h.page.evaluate("hubGetBearerToken()") is None
    assert h.page.evaluate("hubAuthHeaders()") == {}
    assert h.page.evaluate("HUB_AUTH_TOKEN_KEY") == "hub_bearer_token"
    assert h.errors == [], "a const declared twice used to be a SyntaxError"


# ---- save-widget.js ------------------------------------------------------------------------------

def test_save_widget_is_fully_wired_when_storage_throws(harness):
    """localStorage.getItem for the active slot ran unguarded while the widget was being built, so with
    storage blocked the script died halfway and the Save button never got its handler."""
    h = harness(init_scripts=[BLOCKED_STORAGE])
    h.pages["/t.html"] = page_html(
        script("hub-auth.js") + script("save-widget.js", 'data-game-id="qa"'), "<div id='game'>g</div>")
    h.goto()
    h.page.wait_for_selector("#save-widget")
    h.page.evaluate("document.getElementById('save-widget').classList.remove('collapsed')")
    h.page.click(".save-widget-save-button")
    h.page.wait_for_function(
        "document.querySelector('.save-widget-status').textContent.includes('Still loading')")
    h.page.click(".save-widget-load-button")
    h.page.wait_for_function(
        "document.querySelector('.save-widget-status').textContent.includes('Still loading')")
    assert h.errors == []
    assert h.api_calls == []


def test_save_widget_included_twice_mounts_one_panel(harness):
    h = harness()
    tag = script("save-widget.js", 'data-game-id="qa"')
    h.pages["/t.html"] = page_html(script("hub-auth.js") + tag + tag, "<div id='game'>g</div>")
    h.goto()
    h.page.wait_for_selector("#save-widget")
    assert h.page.locator("#save-widget").count() == 1
    assert h.errors == []


def test_save_widget_reads_the_account_saves_once_at_page_load(harness):
    """Autoload and the slot rows each fetched GET /users/me/saves one after the other; the second
    request is the same answer, so the startup path now makes one."""
    h = harness(init_scripts=["localStorage.setItem('hub_bearer_token', 't');"])
    row = {"save_code": "AAAA-0001", "game_id": "qa", "slot": 1, "slot_name": "Save 1",
           "save_data": {"v": 1}, "created_at": "2026-10-01T00:00:00Z", "updated_at": "2026-10-01T00:00:00Z"}
    h.api_responses[("GET", "/users/me/saves")] = (200, [row])
    pyodide = ("window.__loaded = null; window.pyodide = { toPy: (x) => x, globals: { get(n) {"
               "if (n === 'load_state') return (d) => { window.__loaded = d; };"
               "if (n === 'get_state') return () => ({ toJs: () => ({v: 1}) }); } } };")
    h.pages["/t.html"] = page_html(
        f"<script>{pyodide}</script>" + script("hub-auth.js") + script("save-widget.js", 'data-game-id="qa"'),
        "<div id='game'>g</div>")
    h.goto()
    h.page.wait_for_function("window.__loaded !== null")
    h.page.wait_for_selector(".save-widget-slot", state="attached")   # the panel starts collapsed (Z-22)
    reads = [c for c in h.api_calls if c[0] == "GET" and c[1].startswith("/users/me/saves")]
    assert len(reads) == 1, reads
    assert h.page.locator(".save-widget-slot").count() == 3


# ---- confirm-dialog.js ---------------------------------------------------------------------------

def test_confirm_dialog_still_confirms_when_storage_throws_and_adds_its_styles_lazily(harness):
    """ask() read the skip flag from localStorage unguarded, so with storage blocked the dialog never
    opened and the guarded action silently did nothing. The stylesheet is now added on first use."""
    h = harness(init_scripts=[BLOCKED_STORAGE])
    h.pages["/t.html"] = page_html(script("confirm-dialog.js") + script("confirm-dialog.js"), "<p>x</p>")
    h.goto()
    assert h.page.evaluate("document.getElementById('confirm-dialog-styles')") is None
    h.page.evaluate("window.__done = 0; ConfirmDialog.ask({id: 'qa', message: 'Sure?', onConfirm: () => { window.__done += 1; }})")
    assert h.page.is_visible("#confirm-dialog-overlay")
    assert h.page.evaluate("!!document.getElementById('confirm-dialog-styles')") is True
    h.page.check("#confirm-dialog-skip-checkbox")   # remembering fails silently; the action must still run
    h.page.click("#confirm-dialog-confirm")
    assert h.page.evaluate("window.__done") == 1
    assert h.errors == []


# ---- theme.js ------------------------------------------------------------------------------------

def test_theme_toggle_flips_once_when_the_script_is_included_twice(harness):
    h = harness(init_scripts=["localStorage.setItem('theme', 'dark');"])
    h.pages["/t.html"] = page_html(script("theme.js") + script("theme.js"), '<button id="theme-toggle">t</button>')
    h.goto()
    assert h.page.evaluate("document.documentElement.dataset.theme") == "dark"
    h.page.click("#theme-toggle")
    assert h.page.evaluate("document.documentElement.dataset.theme") == "light"


# ---- keyboard-shortcuts.js -----------------------------------------------------------------------

def test_shortcut_help_opens_after_init_is_called_twice(harness):
    """Each init() added its own keydown listener, so two of them toggled the "?" panel open and shut
    in the same keypress."""
    h = harness()
    h.pages["/t.html"] = page_html(script("keyboard-shortcuts.js"), "<p>x</p>")
    h.goto()
    h.page.evaluate("KeyboardShortcuts.init({panels: []}); KeyboardShortcuts.init({panels: []});")
    h.page.keyboard.press("Shift+?")
    assert h.page.evaluate("document.getElementById('kb-shortcuts-panel').hidden") is False
    h.page.keyboard.press("Escape")
    assert h.page.evaluate("document.getElementById('kb-shortcuts-panel').hidden") is True


# ---- tutorial.js ---------------------------------------------------------------------------------

TUTORIAL_BODY = """
<button id="tutorial-restart-button" type="button">Tutorial</button>
<button id="howto-toggle-button" type="button">How to Play</button>
<div id="howto-panel" hidden></div>
<button id="target" type="button">Target</button>
<script>
  window.__steps = [
    {selector: "#target", title: "One", text: "First step."},
    {title: "Two", text: "A centered step."},
  ];
</script>
"""


def test_tutorial_init_twice_does_not_stack_handlers(harness):
    h = harness()
    h.pages["/t.html"] = page_html(script("tutorial.js"), TUTORIAL_BODY)
    h.goto()
    h.page.evaluate("window.__openingScreenOwnsTutorial = true;"
                    "GameTutorial.init(__steps, {gameId: 'qa'}); GameTutorial.init(__steps, {gameId: 'qa'});")
    h.page.click("#howto-toggle-button")
    assert h.page.evaluate("document.getElementById('howto-panel').hidden") is False, \
        "two handlers opened then immediately closed the panel"
    assert h.page.locator("#howto-panel .howto-step").count() == 2


def test_tutorial_quick_next_leaves_the_centered_card_centered(harness):
    """The first positioning of a step runs 260 ms after it is rendered. A stale one from the step
    before ran after a quick Next and put the spotlight back on the old target over a centered card."""
    h = harness()
    h.pages["/t.html"] = page_html(script("tutorial.js"), TUTORIAL_BODY)
    h.goto()
    h.page.evaluate("window.__openingScreenOwnsTutorial = true; GameTutorial.init(__steps, {gameId: 'qa'});")
    h.page.click("#tutorial-restart-button")
    h.page.click("[data-testid=tutorial-next]")      # well inside the 260 ms of step one
    h.page.wait_for_timeout(600)
    assert h.page.get_attribute("#tutorial-card", "class") == "centered"
    assert h.page.evaluate("getComputedStyle(document.getElementById('tutorial-spotlight')).display") == "none"


# ---- info-footer.js ------------------------------------------------------------------------------

def test_info_footer_stops_polling_once_panels_and_changelog_are_there(harness):
    """The footer polled every 500 ms for a full minute on every game page. It now stops as soon as
    every panel exists and the changelog date is known (the observers keep the text current)."""
    h = harness(init_scripts=["window.__cleared = 0; const c = window.clearInterval;"
                              "window.clearInterval = function (id) { window.__cleared += 1; return c.call(window, id); };"])
    h.pages["/t.html"] = page_html(
        script("info-footer.js", 'data-game-id="qa"'),
        '<h1>QA game</h1><div id="howto-panel"><p>How</p></div><div id="info-page-panel"><p>Info</p></div>')
    h.goto()
    h.page.wait_for_timeout(1300)
    assert h.page.evaluate("window.__cleared") == 0, "no changelog yet: it must keep waiting for it"
    h.page.evaluate("window.CHANGELOG_JSON = JSON.stringify([{date: '2026-10-01', entry: 'x'}])")
    h.page.wait_for_function("window.__cleared === 1", timeout=3000)
    assert "updated 2026-10-01" in h.page.inner_text("#howto-panel .noyvj-info-footer")


# ---- leaderboard.js ------------------------------------------------------------------------------

def test_report_is_false_when_the_server_refuses_the_score(harness):
    h = harness(init_scripts=["localStorage.setItem('hub_bearer_token', 't'); localStorage.setItem('lb-optin:g:b', 'true');"])
    h.api_responses[("PUT", "/leaderboards/g/b")] = (422, {"detail": "no"})
    h.pages["/t.html"] = page_html(script("hub-auth.js") + script("leaderboard.js"), "<div id='m'></div>")
    h.goto()
    assert h.page.evaluate("NoyvjLeaderboard.report('g', 'b', 5)") is False


# ---- the decorative backgrounds ------------------------------------------------------------------

def test_background_drifts_animate_transform_not_background_position():
    """An animated background-position repaints every gradient on every frame (about two seconds of
    CPU per three on a software-rendered browser, measured on Sol, Herd and Thaw). The drifts are
    compositor transforms now; this keeps a later edit from putting the repaint back."""
    for name in ("space-bg.css", "ambient-bg.css"):
        css = (ROOT / "shared" / name).read_text(encoding="utf-8")
        blocks = re.findall(r"@keyframes\s+[\w-]+\s*\{(.*?\n\})", css, flags=re.S)
        assert blocks, name
        for block in blocks:
            assert "background-position" not in block, f"{name}: a keyframe animates background-position"
