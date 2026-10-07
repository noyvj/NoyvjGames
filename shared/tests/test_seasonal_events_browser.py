"""shared/seasonal-events.js in headless Chromium (Playwright): the JavaScript
date rules agree with shared/seasonal_events.py on every day of eight years,
and the banner, flavour overrides, dismissal and badge grant behave
(planning/TODO.md W-4). Skipped when Playwright or Chromium is not installed."""

import json
import mimetypes
import re
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared"))
import seasonal_events as se  # noqa: E402

ORIGIN = "http://harness.test"
HUB_ID = re.compile(r"^[a-z0-9-]{1,64}$")

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>body{margin:0;padding:12px;font-family:system-ui;background:#12162a;color:#eee}
html[data-theme="light"] body{background:#eef2fc;color:#1b2033}</style></head>
<body><h1>Game</h1><div id="slot"></div><button id="x">x</button>
<script src="/shared/seasonal-events.js"></script></body></html>"""

HALLOWEEN = {"halloween": {"title": "Night of Storms", "text": "The storms are loud tonight.", "task": "Survive one run with resources left",
                           "goal": 3, "unit": "run"}}


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception as exc:
            pytest.skip(f"Chromium unavailable: {exc}")
        yield b
        b.close()


def open_page(browser, size=(1440, 900), theme=None, query="", store=None):
    context = browser.new_context(viewport={"width": size[0], "height": size[1]})
    page = context.new_page()

    def serve(route, request):
        url = request.url[len(ORIGIN):].split("?")[0]
        if url == "/t.html":
            return route.fulfill(status=200, content_type="text/html", body=PAGE)
        file = ROOT / url.lstrip("/")
        if file.is_file():
            return route.fulfill(status=200, content_type=mimetypes.guess_type(file.name)[0] or "text/plain", body=file.read_bytes())
        return route.fulfill(status=404, body="")

    page.route(f"{ORIGIN}/**", serve)
    page.goto(f"{ORIGIN}/t.html")
    if store is not None:
        page.evaluate("(s) => { localStorage.clear(); for (const k in s) localStorage.setItem(k, s[k]); }", store)
    if query:
        page.goto(f"{ORIGIN}/t.html{query}")
    if theme:
        page.evaluate("(t) => document.documentElement.setAttribute('data-theme', t)", theme)
    return context, page


def init(page, today="2026-10-31", events=None, extra=None):
    page.evaluate(
        """([today, events, extra]) => {
          window.progressValue = 0; window.grants = [];
          window.se = NoyvjSeasonal.init(Object.assign({
            game: 'harness', today, events, dates: window.__dates,
            progress: () => window.progressValue,
            onGrant: (badge, all) => window.grants.push([badge, all]),
          }, extra || {}));
        }""",
        [today, events if events is not None else HALLOWEEN, extra],
    )


def banner(page):
    return page.locator(".noyvj-se")


# ---- date rules agree with Python --------------------------------------------

def test_active_windows_match_the_python_engine_on_every_day(browser):
    context, page = open_page(browser)
    page.evaluate("fetch('/shared/seasonal-dates.json').then((r) => r.json()).then((d) => NoyvjSeasonal.setDates(d))")
    page.wait_for_timeout(300)
    first, last = date(2025, 1, 1), date(2032, 12, 31)
    days = (last - first).days + 1
    js = page.evaluate(
        """([first, days]) => {
          const out = {};
          const [y, m, d] = first.split('-').map(Number);
          for (let i = 0; i < days; i++) {
            const iso = new Date(Date.UTC(y, m - 1, d + i)).toISOString().slice(0, 10);
            const act = NoyvjSeasonal.activeEvents(iso);
            if (act.length) out[iso] = act.map((e) => e.id + '@' + e.year + ':' + e.start + '..' + e.end);
          }
          return out;
        }""",
        [first.isoformat(), days],
    )
    expected = {}
    for n in range(days):
        day = first + timedelta(days=n)
        found = []
        for event in se.active_events(day):
            start, end = se.event_window(event, event["year"])
            found.append(f"{event['id']}@{event['year']}:{start.isoformat()}..{end.isoformat()}")
        if found:
            expected[day.isoformat()] = found
    assert js == expected
    assert len(expected) > 300, "the comparison covered real event days"
    context.close()


def test_easter_and_nth_weekday_match_python(browser):
    context, page = open_page(browser)
    years = list(range(1990, 2101))
    assert page.evaluate("(ys) => ys.map((y) => NoyvjSeasonal.easterSunday(y))", years) == [se.easter_sunday(y).isoformat() for y in years]
    cases = [(y, m, wd, n) for y in (2024, 2026, 2027, 2028) for m in (1, 2, 5, 11, 12) for wd in (0, 3, 6) for n in (1, 2, 4, -1)]
    got = page.evaluate("(cs) => cs.map(([y, m, wd, n]) => NoyvjSeasonal.nthWeekday(y, m, wd, n))", cases)
    assert got == [se.nth_weekday(*c).isoformat() for c in cases]
    context.close()


def test_default_event_table_is_the_python_one_and_badge_ids_match(browser):
    context, page = open_page(browser)
    js_events = page.evaluate("NoyvjSeasonal.DEFAULT_EVENTS")
    assert js_events == se.DEFAULT_EVENTS
    js_ids = page.evaluate("(es) => es.map((e) => NoyvjSeasonal.badgeId(Object.assign({}, e, { year: 2027 })))", se.DEFAULT_EVENTS)
    assert js_ids == [se.hub_badge_id(dict(e, year=2027)) for e in se.DEFAULT_EVENTS]
    assert all(HUB_ID.match(i) for i in js_ids)
    entry = page.evaluate("NoyvjSeasonal.badgeEntry({ id: 'new_year', name: 'New Year', year: 2027 }, '2027-01-01')")
    assert entry == se.badge_entry({"id": "new_year", "name": "New Year", "year": 2027}, "2027-01-01")
    context.close()


def test_a_year_the_tables_do_not_cover_is_never_active(browser):
    context, page = open_page(browser)
    page.evaluate("fetch('/shared/seasonal-dates.json').then((r) => r.json()).then((d) => NoyvjSeasonal.setDates(d))")
    page.wait_for_timeout(300)
    ids = page.evaluate("(d) => NoyvjSeasonal.activeEvents(d).map((e) => e.id)", "2031-11-05")
    assert ids == [], "Diwali 2031 is not in the table, so nothing is active"
    assert page.evaluate("NoyvjSeasonal.activeEvents('2026-12-06').map((e) => e.id)") == ["hanukkah"]
    assert page.evaluate("NoyvjSeasonal.activeEvents('not a date')") == []
    context.close()


# ---- where today comes from -----------------------------------------------------

def test_today_option_url_parameter_and_clock_in_that_order(browser):
    context, page = open_page(browser, query="?event-date=2026-12-25")
    info = page.evaluate("NoyvjSeasonal.resolveToday()")
    assert (info["iso"], info["source"]) == ("2026-12-25", "url")
    assert page.evaluate("NoyvjSeasonal.resolveToday('2026-10-31').iso") == "2026-10-31"
    assert page.evaluate("NoyvjSeasonal.resolveToday(() => new Date(2027, 0, 2)).iso") == "2027-01-02"
    assert page.evaluate("NoyvjSeasonal.resolveToday('garbage').iso") == "2026-12-25", "a bad option falls through to the URL"
    context.close()
    context, page = open_page(browser)
    page.clock.set_fixed_time("2028-04-16T12:00:00")
    page.reload()
    info = page.evaluate("NoyvjSeasonal.resolveToday()")
    assert info["iso"] == "2028-04-16" and info["source"] == "clock", "the real clock is read, never a hardcoded date"
    context.close()


# ---- banner, flavour, dismissal, grant --------------------------------------------

def test_banner_shows_flavour_task_progress_and_end_date(browser):
    context, page = open_page(browser)
    init(page)
    b = banner(page)
    assert b.count() == 1 and b.get_attribute("role") == "region"
    assert b.get_attribute("aria-label") == "Seasonal event: Night of Storms"
    assert page.locator(".noyvj-se-title").inner_text() == "Night of Storms"
    assert page.locator(".noyvj-se-text").inner_text() == "The storms are loud tonight."
    assert page.locator(".noyvj-se-task").inner_text() == "Task: Survive one run with resources left"
    assert page.locator(".noyvj-se-state").inner_text() == "Open until 1 Nov · badge: Halloween 2026"
    assert page.locator(".noyvj-se-progress").inner_text() == "Progress: 0 of 3 runs"
    page.evaluate("progressValue = 1; se.refresh()")
    assert page.locator(".noyvj-se-progress").inner_text() == "Progress: 1 of 3 runs"
    assert page.locator(".noyvj-se-meter").get_attribute("max") == "3"
    assert page.locator(".noyvj-se-icon").get_attribute("aria-hidden") == "true"
    assert page.evaluate("getComputedStyle(document.querySelector('.noyvj-se')).borderStyle") == "dashed"
    context.close()


def test_a_game_only_shows_the_events_it_hosts_and_only_inside_the_window(browser):
    context, page = open_page(browser)
    init(page, today="2026-10-31", events={"christmas": {"text": "x"}})
    assert banner(page).count() == 0, "this game does not host Halloween"
    page.evaluate("se.destroy()")
    init(page, today="2026-10-24")
    assert banner(page).count() == 0, "a day before the window"
    assert page.evaluate("se.active()") == []
    page.evaluate("se.setToday('2026-10-25')")
    assert banner(page).count() == 1, "the first day of the window"
    page.evaluate("se.setToday('2026-11-02')")
    assert banner(page).count() == 0, "the banner leaves when the window closes"
    context.close()


def test_default_flavour_when_a_game_supplies_none(browser):
    context, page = open_page(browser)
    init(page, today="2026-12-20", events={"christmas": {}}, extra={"progress": None})
    assert page.locator(".noyvj-se-title").inner_text() == "Christmas"
    assert "Christmas is on for a few days" in page.locator(".noyvj-se-text").inner_text()
    assert page.locator(".noyvj-se-task").is_hidden() and page.locator(".noyvj-se-progress").is_hidden()
    context.close()


def test_a_custom_calendar_and_an_icon_override(browser):
    context, page = open_page(browser)
    calendar = [{"id": "founders_day", "name": "Founders Day", "when": {"kind": "fixed", "month": 3, "day": 9, "before": 0, "after": 1}}]
    init(page, today="2027-03-10", events={"founders_day": {"icon": "⚑"}}, extra={"calendar": calendar})
    assert page.locator(".noyvj-se-title").inner_text() == "Founders Day"
    assert page.locator(".noyvj-se-icon").inner_text() == "⚑"
    assert page.evaluate("se.active()[0].badgeId") == "founders-day-2027"
    context.close()


def test_dismiss_hides_it_and_is_remembered_across_a_reload(browser):
    context, page = open_page(browser)
    init(page)
    page.locator(".noyvj-se-dismiss").click()
    assert banner(page).is_hidden()
    assert page.evaluate("localStorage.getItem('seasonal-dismissed:harness:halloween-2026')") == "1"
    page.evaluate("progressValue = 1; se.refresh()")
    assert banner(page).is_hidden(), "a refresh does not bring a dismissed banner back"
    page.reload()
    init(page)
    assert banner(page).is_hidden()
    context.close()


def test_a_dismissed_banner_still_grants_the_badge_when_the_task_is_done(browser):
    context, page = open_page(browser)
    init(page)
    page.locator(".noyvj-se-dismiss").click()
    page.evaluate("progressValue = 3; se.refresh()")
    assert page.evaluate("se.hasBadge('halloween-2026')") is True
    assert banner(page).is_hidden()
    context.close()


def test_reaching_the_goal_grants_one_hub_contract_badge_once(browser):
    context, page = open_page(browser)
    init(page)
    page.evaluate("progressValue = 2; se.refresh()")
    assert page.evaluate("se.badges()") == []
    page.evaluate("progressValue = 3; se.refresh()")
    page.evaluate("progressValue = 5; se.refresh(); se.refresh()")
    badges = page.evaluate("se.badges()")
    assert badges == [{"id": "halloween-2026", "label": "Halloween 2026", "earned_at": "2026-10-31"}]
    assert HUB_ID.match(badges[0]["id"])
    assert page.evaluate("grants.length") == 1, "onGrant fires once, however often it is refreshed"
    assert page.evaluate("grants[0][1]") == badges
    stored = json.loads(page.evaluate("localStorage.getItem('event_badges_v1')"))
    assert stored == {"version": 1, "badges": badges}, "exactly what the hub's collectEventBadges reads"
    assert banner(page).get_attribute("data-state") == "earned"
    assert page.locator(".noyvj-se-title").inner_text() == "Night of Storms — badge earned"
    assert page.locator(".noyvj-se-state").inner_text() == "✓ Badge earned: Halloween 2026"
    assert page.evaluate("getComputedStyle(document.querySelector('.noyvj-se')).borderStyle") == "solid"
    assert page.locator(".noyvj-se-task").is_hidden()
    assert page.locator(".noyvj-se-toast").inner_text() == "✓ Badge earned: Halloween 2026"
    assert page.locator(".noyvj-se-toasts").get_attribute("role") == "status"
    context.close()


def test_qualifies_callback_and_manual_grant_and_custom_label(browser):
    context, page = open_page(browser)
    init(page, events={"halloween": {"badge_label": "Stormwatcher 2026"}}, extra={"autoGrant": False})
    assert page.evaluate("se.grant('halloween')") == {"granted": True, "badge": {"id": "halloween-2026", "label": "Stormwatcher 2026", "earned_at": "2026-10-31"}}
    assert page.evaluate("se.grant('halloween').granted") is False
    assert page.evaluate("se.grant('christmas')") == {"granted": False, "badge": None, "reason": "not-active"}
    context.close()
    context, page = open_page(browser)
    page.evaluate("""() => { window.done = false; window.se2 = NoyvjSeasonal.init({ game: 'h2', today: '2026-10-31', events: { halloween: {} },
      dates: {}, qualifies: () => window.done }); }""")
    assert page.evaluate("se2.badges().length") == 0
    page.evaluate("done = true; se2.refresh()")
    assert page.evaluate("se2.badges().length") == 1
    context.close()


def test_badges_from_a_save_are_adopted_and_malformed_ones_ignored(browser):
    store = {"event_badges_v1": json.dumps({"version": 1, "badges": [{"id": "christmas-2025", "label": "Christmas 2025", "earned_at": "2025-12-25"}]})}
    context, page = open_page(browser, store=store)
    page.reload()
    init(page)
    assert [b["id"] for b in page.evaluate("se.badges()")] == ["christmas-2025"], "this device's earlier badges are kept"
    page.evaluate("""se.adoptBadges([{ id: 'easter-2026', label: 'Easter 2026', earned_at: '2026-04-05' },
      { id: 'Bad_ID', label: 'x' }, { id: 'ok', label: '' }, null, 'junk', { id: 'christmas-2025', label: 'dupe' }])""")
    assert [b["id"] for b in page.evaluate("se.badges()")] == ["christmas-2025", "easter-2026"]
    stored = json.loads(page.evaluate("localStorage.getItem('event_badges_v1')"))
    assert [b["id"] for b in stored["badges"]] == ["christmas-2025", "easter-2026"]
    page.evaluate("progressValue = 3; se.refresh()")
    stored = json.loads(page.evaluate("localStorage.getItem('event_badges_v1')"))
    assert [b["id"] for b in stored["badges"]] == ["christmas-2025", "easter-2026", "halloween-2026"], "a grant adds to, never replaces, the list"
    context.close()


def test_local_badges_can_be_switched_off_when_the_game_keeps_them_in_its_save(browser):
    context, page = open_page(browser)
    init(page, extra={"localBadges": False, "rememberDismiss": False})
    page.evaluate("progressValue = 3; se.refresh()")
    assert page.evaluate("grants.length") == 1
    page.locator(".noyvj-se-dismiss").click()
    assert page.evaluate("Object.keys(localStorage)") == []
    context.close()


def test_inline_container_and_the_moving_holiday_table_loads_by_itself(browser):
    context, page = open_page(browser)
    page.evaluate("""() => { window.se = NoyvjSeasonal.init({ game: 'h', today: '2026-12-06', events: { hanukkah: { text: 'Eight nights' } }, container: '#slot' }); }""")
    page.wait_for_selector("#slot .noyvj-se")
    assert page.locator("#slot .noyvj-se-title").inner_text() == "Hanukkah"
    assert page.evaluate("document.querySelector('.noyvj-se-stack').className").endswith("--inline")
    assert page.evaluate("getComputedStyle(document.querySelector('.noyvj-se-stack')).position") == "static"
    context.close()


def test_text_is_never_interpreted_as_html(browser):
    context, page = open_page(browser)
    init(page, events={"halloween": {"title": "<img src=x onerror=window.pwned=1>", "text": "<b>hi</b>", "task": "<i>t</i>"}})
    assert page.evaluate("window.pwned") is None
    assert page.locator(".noyvj-se b, .noyvj-se i, .noyvj-se img").count() == 0
    context.close()


@pytest.mark.parametrize("size", [(1440, 900), (360, 740)])
@pytest.mark.parametrize("theme", ["dark", "light"])
def test_banner_layout_in_both_themes_and_sizes(browser, size, theme):
    context, page = open_page(browser, size=size, theme=theme)
    init(page)
    page.evaluate("progressValue = 3; se.refresh()")
    geo = page.evaluate("""() => { const r = document.querySelector('.noyvj-se').getBoundingClientRect();
      const t = document.querySelector('.noyvj-se-toast').getBoundingClientRect();
      const cs = getComputedStyle(document.querySelector('.noyvj-se'));
      return { l: r.left, r: r.right, t: r.top, b: r.bottom, vw: innerWidth, sw: document.documentElement.scrollWidth,
               bg: cs.backgroundColor, fg: cs.color, tl: t.left, tr: t.right,
               btn: document.querySelector('.noyvj-se-dismiss').getBoundingClientRect().height }; }""")
    assert geo["l"] >= 0 and geo["r"] <= geo["vw"] and geo["sw"] <= geo["vw"]
    assert geo["tl"] >= 0 and geo["tr"] <= geo["vw"]
    assert geo["btn"] >= 40
    assert geo["bg"].startswith("rgba(255, 255, 255") == (theme == "light")
    context.close()


def test_the_fixed_strip_reserves_its_height_so_it_never_covers_the_page_header(browser):
    context, page = open_page(browser)
    before = page.evaluate("document.querySelector('h1').getBoundingClientRect().top")
    init(page)
    banner_bottom = page.evaluate("document.querySelector('.noyvj-se-stack').getBoundingClientRect().bottom")
    h1_top = page.evaluate("document.querySelector('h1').getBoundingClientRect().top")
    assert h1_top >= banner_bottom - 1 and h1_top > before, "the game's heading starts below the banner"
    page.locator(".noyvj-se-dismiss").click()
    assert page.evaluate("document.querySelector('h1').getBoundingClientRect().top") == before, "the space is given back"
    page.evaluate("se.destroy()")
    context.close()
    context, page = open_page(browser)
    page.evaluate("""() => { window.se = NoyvjSeasonal.init({ game: 'r', today: '2026-10-31', events: { halloween: {} }, reserveSpace: false, dates: {} }); }""")
    assert page.evaluate("document.documentElement.classList.contains('noyvj-se-reserve')") is False
    context.close()
