"""N-2: the page side of Aftermath's Halloween event (games/aftermath/index.html inline script plus
shared/seasonal-events.js): the banner shows only inside the window, a finished run with resources left earns
the hub badge once, the badge list is handed to the game's set_event_badges, and the local counter ignores
runs with nothing left. Pyodide is not loaded (the harness blocks the CDN): a fake stands in for it."""

import json

FAKE_PY = """window.__py = []; window.pyodide = {globals: {get(name) {
  const fn = (arg) => window.__py.push([name, arg]); fn.destroy = () => {}; return fn; }}};"""
QUIET = "localStorage.setItem('tutorial-seen:aftermath','1')"


def open_game(harness, date):
    h = harness(init_scripts=[QUIET])
    h.goto(f"/games/aftermath/index.html?event-date={date}")
    h.page.wait_for_function("typeof window.aftermathRunFinished === 'function'")
    h.page.evaluate(FAKE_PY)
    return h


def badges(h):
    raw = h.page.evaluate("localStorage.getItem('event_badges_v1')")
    return json.loads(raw)["badges"] if raw else []


def test_banner_only_inside_the_window(harness):
    inside = open_game(harness, "2026-10-31")
    inside.page.wait_for_selector("[role=region][aria-label*='Seasonal event']")
    assert "Night of Storms" in inside.page.inner_text("[role=region][aria-label*='Seasonal event']")
    outside = open_game(harness, "2026-08-15")
    assert outside.page.locator("[role=region][aria-label*='Seasonal event']").count() == 0


def test_a_run_with_resources_left_earns_the_badge_once(harness):
    h = open_game(harness, "2026-10-29")
    h.page.evaluate("window.aftermathRunFinished(0)")
    assert badges(h) == []
    h.page.evaluate("window.aftermathRunFinished(12)")
    assert [b["id"] for b in badges(h)] == ["halloween-2026"]
    h.page.evaluate("window.aftermathRunFinished(30)")
    assert len(badges(h)) == 1
    calls = [c for c in h.page.evaluate("window.__py") if c[0] == "set_event_badges"]
    assert len(calls) == 1
    assert json.loads(calls[0][1])[0]["id"] == "halloween-2026"


def test_nothing_is_counted_or_granted_outside_the_window(harness):
    h = open_game(harness, "2026-03-01")
    h.page.evaluate("window.aftermathRunFinished(50)")
    assert badges(h) == []
    assert h.page.evaluate("Object.keys(localStorage).filter(k => k.startsWith('aftermath-season:')).length") == 0


def test_a_saved_badge_list_is_adopted_on_load(harness):
    h = open_game(harness, "2026-03-01")
    h.page.evaluate("""window.aftermathAdoptBadges(JSON.stringify([
      {id: 'halloween-2025', label: 'Halloween 2025', earned_at: '2025-10-31'}]))""")
    assert [b["id"] for b in badges(h)] == ["halloween-2025"]
    h.page.evaluate("window.aftermathAdoptBadges('{oops')")
    assert len(badges(h)) == 1
