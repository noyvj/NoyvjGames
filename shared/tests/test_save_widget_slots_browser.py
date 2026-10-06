"""Behavioural tests for shared/save-widget.js (slots, claim, autoload) and
shared/opening-screen.js (Continue / New Game / "Main menu" re-entry).

Runs the real scripts in headless Chromium (Playwright) against a harness page
with a fake Pyodide and an in-memory copy of the backend's save-slot contract
(app/main.py: GET /users/me/saves, PUT /users/me/saves/{game}/slots/{n},
POST /saves, POST /saves/{code}/claim). Nothing touches the network: every
request to the production API host is answered by the mock below. Skipped when
Playwright or its Chromium is not installed.

Regressions covered (planning/TODO.md UX-2, UX-6, UX-8):
  * slot rows were laid out by class-only CSS that the widget's own
    `#save-widget button { width: 100% }` rule beat, so "Save here" was pushed off
    the panel and the label squeezed to nothing;
  * the open panel and the opening card had no max-height / scrolling;
  * save-widget.js ran before opening-screen.js existed, so "wait for the player's
    choice" never happened and New Game was overwritten by the latest save;
  * backend timestamps without a zone were read as local time;
  * a way back to the opening screen (Main menu) after it is dismissed.
"""

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

ROOT = Path(__file__).resolve().parents[2]
API = "https://noyvjgames.fastapicloud.dev"
ORIGIN = "http://harness.test"
TOKEN = "test-token"


def naive_utc(minutes_ago):
    """The shape a naive-timestamp database sends: no zone suffix."""
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).strftime("%Y-%m-%dT%H:%M:%S")


class MockBackend:
    def __init__(self):
        self.rows = []  # dicts shaped like SaveOut (+ private _user)
        self.log = []   # (method, path)
        self._n = 0

    def add(self, slot, v, minutes_ago, code=None, user=True):
        self._n += 1
        row = {
            "save_code": code or f"AAAA-{self._n:04d}", "game_id": "harness", "slot": slot,
            "slot_name": f"Save {slot}" if slot else None, "save_data": {"v": v},
            "created_at": naive_utc(minutes_ago), "updated_at": naive_utc(minutes_ago), "_user": user,
        }
        self.rows.append(row)
        return row

    def out(self, row):
        return {k: v for k, v in row.items() if not k.startswith("_")}

    def handle(self, route, request):
        headers = {
            "access-control-allow-origin": ORIGIN, "access-control-allow-headers": "*",
            "access-control-allow-methods": "GET,POST,PUT,PATCH,DELETE", "cache-control": "no-store",
        }
        path = request.url[len(API):].split("?")[0]
        if request.method == "OPTIONS":
            return route.fulfill(status=204, headers=headers)
        self.log.append((request.method, path))
        auth = request.headers.get("authorization")

        def send(status, body):
            route.fulfill(status=status, headers=dict(headers, **{"content-type": "application/json"}), body=json.dumps(body))

        if path == "/users/me/saves" and request.method == "GET":
            if auth != f"Bearer {TOKEN}":
                return send(401, {"detail": "no"})
            mine = [r for r in self.rows if r["_user"]]
            return send(200, [self.out(r) for r in sorted(mine, key=lambda r: r["updated_at"], reverse=True)])
        m = re.fullmatch(r"/users/me/saves/([^/]+)/slots/(\d+)", path)
        if m and request.method == "PUT":
            if auth != f"Bearer {TOKEN}":
                return send(401, {"detail": "no"})
            slot, data = int(m.group(2)), json.loads(request.post_data)["save_data"]
            row = next((r for r in self.rows if r["_user"] and r["slot"] == slot), None)
            if row is None:
                row = self.add(slot, 0, 0)
            row["save_data"] = data
            row["updated_at"] = naive_utc(0)
            return send(200, self.out(row))
        if path == "/saves" and request.method == "POST":
            body = json.loads(request.post_data)
            row = self.add(None, 0, 0, user=False)
            row["save_data"] = body["save_data"]
            return send(200, self.out(row))
        m = re.fullmatch(r"/saves/([A-Z0-9-]+)/claim", path)
        if m and request.method == "POST":
            row = next((r for r in self.rows if r["save_code"] == m.group(1)), None)
            if row is None:
                return send(404, {"detail": "Save code not found"})
            taken = {r["slot"] for r in self.rows if r["_user"] and r["slot"]}
            free = [n for n in (1, 2, 3) if n not in taken]
            if not free:
                return send(409, {"detail": "All save slots for this game are full"})
            row.update(_user=True, slot=free[0], slot_name=f"Save {free[0]}")
            return send(200, self.out(row))
        m = re.fullmatch(r"/saves/([A-Z0-9-]+)", path)
        if m and request.method == "GET":
            row = next((r for r in self.rows if r["save_code"] == m.group(1)), None)
            return send(200, self.out(row)) if row else send(404, {"detail": "Save code not found"})
        return send(404, {"detail": "unmocked " + path})


HARNESS = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"></head><body>
<div id="game">Game</div>
%(extra)s
<script>
window.__state = {v: 7}; window.__loaded = null;
window.pyodide = { toPy: (x) => x, globals: { get(name) {
  if (name === "get_state") return () => ({ toJs: () => ({ v: window.__state.v }) });
  if (name === "load_state") return (d) => { window.__loaded = d; window.__state = d; };
  return undefined; } } };
%(pre)s
</script>
<script src="/shared/hub-auth.js"></script>
<script src="/shared/save-widget.js" data-game-id="harness"></script>
<script src="/shared/opening-screen.js" data-game-id="harness" data-game-name="Harness"></script>
</body></html>"""


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception as exc:  # Chromium not installed
            pytest.skip(f"Chromium unavailable: {exc}")
        yield b
        b.close()


def open_page(browser, backend, size=(360, 740), signed_in=True, hash_="", extra="", pre="", store=None):
    context = browser.new_context(viewport={"width": size[0], "height": size[1]})
    page = context.new_page()

    def serve(route, request):
        url = request.url[len(ORIGIN):].split("?")[0]
        if url == "/harness.html":
            return route.fulfill(status=200, content_type="text/html", body=HARNESS % {"extra": extra, "pre": pre})
        file = ROOT / url.lstrip("/")
        if file.is_file():
            return route.fulfill(status=200, content_type="text/javascript", body=file.read_text(encoding="utf-8"))
        return route.fulfill(status=404, body="")

    page.route(f"{ORIGIN}/**", serve)
    page.route(f"{API}/**", backend.handle)
    page.goto(f"{ORIGIN}/harness.html")  # establish the origin before seeding storage
    seed = dict(store or {})
    if signed_in:
        seed["hub_bearer_token"] = TOKEN
    page.evaluate(
        "(seed) => { localStorage.clear(); sessionStorage.clear(); for (const k in seed) localStorage.setItem(k, seed[k]); }",
        seed,
    )
    page.goto(f"{ORIGIN}/harness.html{hash_}")
    page.reload()
    page.wait_for_selector("#save-widget", state="attached")
    return context, page


def settle(page, ms=800):
    page.wait_for_timeout(ms)


def expand_widget(page):
    page.evaluate("document.getElementById('save-widget').classList.remove('collapsed')")


def seeded_backend():
    b = MockBackend()
    b.add(1, 11, 300)
    b.add(2, 22, 5)    # the latest
    b.add(3, 33, 120)
    return b


def test_slot_rows_fit_inside_the_panel_at_phone_width(browser):
    context, page = open_page(browser, seeded_backend(), hash_="#play")
    settle(page, 1200)
    expand_widget(page)
    geo = page.evaluate("""() => {
      const w = document.getElementById('save-widget').getBoundingClientRect();
      const rows = [...document.querySelectorAll('.save-widget-slot')].map((row) => ({
        label: row.querySelector('.save-widget-slot-label').getBoundingClientRect().width,
        buttons: [...row.querySelectorAll('button')].map((b) => { const r = b.getBoundingClientRect(); return [r.left, r.right, r.width]; }),
      }));
      return { w: [w.left, w.right, w.top, w.bottom], rows, vw: innerWidth, vh: innerHeight };
    }""")
    assert len(geo["rows"]) == 3
    left, right, top, bottom = geo["w"]
    assert left >= 0 and right <= geo["vw"] and top >= 0 and bottom <= geo["vh"]
    for row in geo["rows"]:
        assert row["label"] > 80, "slot label must be readable, not squeezed to nothing"
        assert len(row["buttons"]) == 2, "an occupied slot offers Load and Save here"
        for b_left, b_right, width in row["buttons"]:
            assert b_left >= left - 1 and b_right <= right + 1, "slot buttons must stay inside the panel"
            assert width > 40
    context.close()


def test_open_panel_scrolls_inside_a_short_viewport(browser):
    context, page = open_page(browser, seeded_backend(), size=(360, 420), hash_="#play")
    settle(page, 1200)
    expand_widget(page)
    info = page.evaluate("""() => { const w = document.getElementById('save-widget'); const r = w.getBoundingClientRect();
      return { top: r.top, bottom: r.bottom, vh: innerHeight, overflowY: getComputedStyle(w).overflowY,
               scrollable: w.scrollHeight > w.clientHeight }; }""")
    assert info["top"] >= 0 and info["bottom"] <= info["vh"]
    assert info["overflowY"] in ("auto", "scroll") and info["scrollable"]
    context.close()


def test_saving_to_a_chosen_slot_and_loading_another(browser):
    backend = seeded_backend()
    context, page = open_page(browser, backend, hash_="#play")
    settle(page, 1200)
    expand_widget(page)
    page.evaluate("window.__state = {v: 99}")
    # Slot 3 holds something and is not the slot being played, so the tap asks first
    # (no shared ConfirmDialog on this page: the widget falls back to allowing it).
    page.locator(".save-widget-slot").nth(2).get_by_text("Save here").click()
    settle(page, 900)
    assert any(r["slot"] == 3 and r["save_data"] == {"v": 99} for r in backend.rows)
    assert ("PUT", "/users/me/saves/harness/slots/3") in backend.log
    assert page.evaluate("localStorage.getItem('activeslot:harness')") == "3"
    # Load slot 1: the game state becomes slot 1's data and slot 1 becomes the active slot.
    page.locator(".save-widget-slot").nth(0).get_by_text("Load").click()
    settle(page, 900)
    assert page.evaluate("window.__loaded") == {"v": 11}
    assert page.evaluate("localStorage.getItem('activeslot:harness')") == "1"
    assert page.locator(".save-widget-claim-button").is_hidden(), "a slot save is already in the account"
    context.close()


def test_timestamps_without_a_zone_are_read_as_utc(browser):
    backend = MockBackend()
    backend.add(1, 1, 0)
    context, page = open_page(browser, backend, hash_="#play")
    settle(page, 1200)
    label = page.locator(".save-widget-slot-label").first.inner_text()
    assert "just now" in label, label
    context.close()


def test_continue_loads_the_latest_slot(browser):
    context, page = open_page(browser, seeded_backend())
    settle(page, 1200)
    assert page.locator("#opening-screen").count() == 1
    assert page.evaluate("window.__loaded") is None, "nothing may load before the player answers the opening screen"
    page.locator('#opening-screen [data-action="continue"]').click()
    settle(page, 1200)
    assert page.evaluate("window.__loaded") == {"v": 22}, "Continue loads the most recently updated slot"
    context.close()


def test_new_game_is_never_overwritten_by_the_latest_save(browser):
    context, page = open_page(browser, seeded_backend(), store={"activeslot:harness": "2"})
    settle(page, 1200)
    page.locator('#opening-screen [data-action="new"]').click()
    settle(page, 1500)
    assert page.evaluate("window.__loaded") is None, "New Game must not be overwritten by the account's latest save"
    assert page.evaluate("localStorage.getItem('activeslot:harness')") is None, "the abandoned game's slot is forgotten"
    context.close()


def test_main_menu_button_reopens_the_opening_screen_without_losing_progress(browser):
    context, page = open_page(browser, seeded_backend(), hash_="#play")
    settle(page, 1500)
    page.evaluate("window.__state = {v: 123}")
    button = page.locator("#save-widget .save-widget-header #noyvj-menu-button")
    assert button.count() == 1
    assert page.locator("#opening-screen").count() == 0
    button.click()
    assert page.locator("#opening-screen").count() == 1
    assert "Resume" in page.locator("#opening-screen .opening-continue-label").inner_text()
    assert page.locator('#opening-screen a[data-action="hub"]').get_attribute("href") == "../../index.html"
    assert page.evaluate("getComputedStyle(document.getElementById('save-widget')).visibility") == "hidden"
    page.locator('#opening-screen [data-action="continue"]').click()
    assert page.locator("#opening-screen").count() == 0
    assert page.evaluate("window.__state") == {"v": 123}, "Resume only closes the screen"
    assert page.evaluate("typeof window.NoyvjOpeningScreen.show") == "function"
    context.close()


def test_new_game_from_the_menu_asks_then_restarts_without_loading_a_save(browser):
    context, page = open_page(browser, seeded_backend(), hash_="#play")
    settle(page, 1500)
    seen = []
    page.on("dialog", lambda d: (seen.append(d.message), d.accept()))
    page.locator("#noyvj-menu-button").click()
    with page.expect_navigation():
        page.locator('#opening-screen [data-action="new"]').click()
    settle(page, 1500)
    assert seen and "new game" in seen[0].lower()
    assert page.evaluate("window.__loaded") is None, "the restarted page must not load the latest save over New Game"
    context.close()


def test_opening_screen_scrolls_on_a_short_viewport(browser):
    context, page = open_page(browser, seeded_backend(), size=(360, 300))
    settle(page, 900)
    info = page.evaluate("""() => { const o = document.getElementById('opening-screen');
      const c = o.querySelector('.opening-card').getBoundingClientRect();
      return { overflowY: getComputedStyle(o).overflowY, scrollable: o.scrollHeight > o.clientHeight, cardTop: c.top }; }""")
    assert info["overflowY"] in ("auto", "scroll")
    assert info["scrollable"] and info["cardTop"] >= 0, "the card must start on-screen and scroll, not be clipped at the top"
    context.close()


def test_desktop_boot_gets_a_menu_entry_not_a_fixed_button(browser):
    extra = '<div id="pc-topbar"></div><div id="pc-menu-panel"><div class="pc-menu-group"><h3>Game</h3></div></div>'
    context, page = open_page(
        browser, seeded_backend(), size=(1440, 900), hash_="#play", extra=extra, pre="window.NOYVJ_LAYOUT = 'pc';"
    )
    settle(page, 1500)
    assert page.locator("#pc-menu-panel #noyvj-menu-button").count() == 1
    assert page.locator(".noyvj-menu-button-fixed").count() == 0
    page.locator("#pc-menu-panel #noyvj-menu-button").click()
    assert page.locator("#opening-screen").count() == 1
    context.close()


def test_anonymous_player_still_saves_with_a_code_and_sees_no_slots(browser):
    backend = MockBackend()
    context, page = open_page(browser, backend, signed_in=False, hash_="#play")
    settle(page, 1000)
    expand_widget(page)
    page.locator(".save-widget-save-button").click()
    settle(page, 1000)
    assert page.locator(".save-widget-code").is_visible()
    assert page.locator(".save-widget-slots").is_hidden()
    assert ("POST", "/saves") in backend.log
    context.close()


def test_claiming_an_anonymous_save_takes_a_slot_and_makes_it_active(browser):
    backend = MockBackend()
    backend.add(None, 5, 3, code="ZZZZ-1111", user=False)
    context, page = open_page(browser, backend, hash_="#play", store={"savecode:harness": "ZZZZ-1111"})
    settle(page, 1200)
    expand_widget(page)
    page.locator(".save-widget-claim-button").click()
    settle(page, 1200)
    assert page.evaluate("localStorage.getItem('activeslot:harness')") == "1"
    assert "slot 1" in page.locator(".save-widget-status").inner_text()
    assert page.locator(".save-widget-claim-button").is_hidden()
    context.close()
