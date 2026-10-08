"""Z-30: the shared components carry stable `data-testid` hooks (naming convention in
planning/game-template.md, section 'data-testid convention'). Real scripts in headless Chromium,
no network. The test pins the NAMES, because other tests and future Playwright scripts rely on
them, and checks that every id in a component is unique on the page."""

import json

import pytest

from conftest import page_html

PAGE = """
<div id="game">Game</div>
<div id="achievements-panel">
  <div data-achievement-id="first_win" class="achievement-card"><p class="achievement-card-description">Win once</p></div>
  <div data-achievement-id="second_win" class="achievement-card"><p class="achievement-card-description">Win twice</p></div>
</div>
<div id="howto-panel"></div>
<script>
window.pyodide = { toPy: (x) => x, globals: { get(name) {
  if (name === "get_state") return () => ({ toJs: () => ({ v: 1 }) });
  if (name === "load_state") return () => {};
  return undefined; } } };
</script>
<script src="/shared/hub-auth.js"></script>
<script src="/shared/save-widget.js" data-game-id="harness"></script>
<script src="/shared/confirm-dialog.js"></script>
<script src="/shared/tutorial.js"></script>
<script src="/shared/achievement-stats.js" data-game-id="harness"></script>
"""


def ids(page):
    return page.evaluate("Array.from(document.querySelectorAll('[data-testid]')).map(e => e.getAttribute('data-testid'))")


@pytest.fixture
def page(harness):
    h = harness()
    h.pages["/t.html"] = page_html(body=PAGE)
    # Achievement stats come from the backend; a failed fetch must not matter here.
    h.api_responses[("GET", "/stats/games/harness/achievements")] = (200, {"players": 0, "achievements": {}})
    p = h.goto()
    p.wait_for_selector("[data-testid='save-widget']")
    yield p, h


def test_save_widget_has_a_testid_on_every_control(page):
    p, _ = page
    found = set(ids(p))
    expected = {"save-widget", "save-widget-toggle", "save-widget-body", "save-widget-save", "save-widget-autosave",
                "save-widget-code", "save-widget-copy", "save-widget-claim", "save-widget-new", "save-widget-slots",
                "save-widget-load-input", "save-widget-load", "save-widget-status"}
    assert expected <= found, sorted(expected - found)
    # The hooks sit on the elements the class names say they do.
    assert p.eval_on_selector("[data-testid='save-widget-save']", "e => e.classList.contains('save-widget-save-button')")
    assert p.eval_on_selector("[data-testid='save-widget-load-input']", "e => e.tagName") == "INPUT"


def test_confirm_dialog_testids_appear_when_it_opens(page):
    p, _ = page
    p.evaluate("ConfirmDialog.ask({id: 'harness-sure', message: 'Sure?', confirmLabel: 'Yes', onConfirm: () => { window.__yes = true; }})")
    found = set(ids(p))
    assert {"confirm-dialog", "confirm-dialog-box", "confirm-dialog-message", "confirm-dialog-skip",
            "confirm-dialog-cancel", "confirm-dialog-confirm"} <= found
    assert p.inner_text("[data-testid='confirm-dialog-message']") == "Sure?"
    p.click("[data-testid='confirm-dialog-confirm']")
    assert p.evaluate("window.__yes") is True


def test_tutorial_testids_and_howto_steps(page):
    p, _ = page
    p.evaluate("""GameTutorial.init([{title: 'One', text: 'First step'}, {title: 'Two', text: 'Second step'}],
                                    {gameId: 'harness', autoStart: false, howtoPanelId: 'howto-panel', howtoContainerId: 'howto-panel'});
                GameTutorial.start();""")
    found = set(ids(p))
    assert {"tutorial-overlay", "tutorial-spotlight", "tutorial-card", "tutorial-step-counter", "tutorial-title",
            "tutorial-text", "tutorial-card-buttons", "tutorial-next", "tutorial-skip"} <= found
    assert "tutorial-back" not in found                          # first step: no Back button
    assert p.inner_text("[data-testid='tutorial-title']") == "One"
    p.click("[data-testid='tutorial-next']")
    assert p.inner_text("[data-testid='tutorial-title']") == "Two"
    assert "tutorial-back" in set(ids(p))
    assert p.inner_text("[data-testid='tutorial-next']") == "Done"


def test_achievement_rows_and_panel_are_tagged(page):
    p, _ = page
    p.evaluate("window.applyAchievementStats()")
    found = ids(p)
    assert "achievements-panel" in found
    assert "achievement-row-first_win" in found and "achievement-row-second_win" in found


def test_testids_are_lowercase_kebab_case_and_unique(page):
    p, _ = page
    p.evaluate("ConfirmDialog.ask({id: 'harness-x', message: 'x', onConfirm: () => {}})")
    p.evaluate("window.applyAchievementStats()")
    found = ids(p)
    assert len(found) == len(set(found)), "duplicate data-testid values on one page"
    for name in found:
        assert name == name.lower() and all(c.isalnum() or c in "-_" for c in name), name
