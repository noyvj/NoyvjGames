"""Z-22 (the save widget as a top-corner pill with a live "Saved N min ago" line) and Z-10 (the save
"time machine": snapshots and "Restore an earlier state") for shared/save-widget.js and
shared/opening-screen.js. Real scripts in headless Chromium against the same harness page and mock
backend as test_save_widget_slots_browser.py, extended with the /users/me/snapshots routes. Nothing
reaches the network. Skipped when Playwright or Chromium is not installed."""

import json
import re
import time

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

from test_save_widget_slots_browser import (  # noqa: E402
    API, MockBackend, ORIGIN, expand_widget, open_page, settle,
)


class SnapBackend(MockBackend):
    """The save-slot mock plus POST/GET /users/me/snapshots(/id), and switches to make saves fail."""

    def __init__(self):
        super().__init__()
        self.snaps = []          # dicts: id, game_id, slot, summary, created_at, size, save_data
        self.fail_saves = False
        self.snap_status = 200   # answer for POST /users/me/snapshots

    def handle(self, route, request):
        path = request.url[len(API):].split("?")[0]
        headers = {
            "access-control-allow-origin": ORIGIN, "access-control-allow-headers": "*",
            "access-control-allow-methods": "GET,POST,PUT,PATCH,DELETE", "cache-control": "no-store",
        }

        def send(status, body):
            route.fulfill(status=status, headers=dict(headers, **{"content-type": "application/json"}), body=json.dumps(body))

        if request.method != "OPTIONS" and path.startswith("/users/me/snapshots"):
            self.log.append((request.method, path))
            if path == "/users/me/snapshots" and request.method == "POST":
                if self.snap_status != 200:
                    return send(self.snap_status, {"detail": "no"})
                body = json.loads(request.post_data)
                row = {"id": f"snap-{len(self.snaps) + 1}", "game_id": body["game_id"], "slot": body["slot"],
                       "summary": body["summary"], "size": len(json.dumps(body["save_data"])),
                       "created_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()), "save_data": body["save_data"]}
                self.snaps.append(row)
                return send(200, {k: v for k, v in row.items() if k != "save_data"})
            if path == "/users/me/snapshots" and request.method == "GET":
                return send(200, [{k: v for k, v in r.items() if k != "save_data"} for r in reversed(self.snaps)])
            m = re.fullmatch(r"/users/me/snapshots/([^/]+)", path)
            if m and request.method == "GET":
                row = next((r for r in self.snaps if r["id"] == m.group(1)), None)
                return send(200, row) if row else send(404, {"detail": "Snapshot not found"})
        if self.fail_saves and request.method in ("PUT", "POST") and (path.startswith("/users/me/saves/") or path == "/saves"):
            self.log.append((request.method, path))
            return send(422, {"detail": "refused"})
        return super().handle(route, request)


def seeded_backend():
    b = SnapBackend()
    b.add(1, 11, 300)
    b.add(2, 22, 5)    # the latest
    b.add(3, 33, 120)
    return b


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception as exc:
            pytest.skip(f"Chromium unavailable: {exc}")
        yield b
        b.close()


def pill_text(page):
    return page.locator(".save-widget-saved-line").inner_text()


def local_snaps(page):
    return page.evaluate("window.NoyvjSaveWidget.localSnapshots()")


def use_raw_state(page):
    """The harness's get_state only reports {v}; this makes it report window.__raw as it is."""
    page.evaluate("""() => { const real = window.pyodide.globals.get;
      window.pyodide.globals.get = (n) => n === 'get_state' ? () => ({ toJs: () => window.__raw }) : real(n); }""")


def restart_autosave_under_a_fake_clock(page):
    """The autosave interval is created at page load; install the fake clock, then re-create it."""
    page.clock.install()
    page.evaluate("""() => { const box = document.querySelector('.save-widget-autosave-checkbox');
      box.checked = false; box.dispatchEvent(new Event('change')); box.checked = true; box.dispatchEvent(new Event('change')); }""")


def load_slot(page, n):
    expand_widget(page)
    page.locator(".save-widget-slot").nth(n - 1).get_by_text("Load").click()
    settle(page, 700)


# ---------------------------------------------------------------- Z-22

@pytest.mark.parametrize("size", [(360, 740), (1440, 900)])
def test_pill_starts_collapsed_in_the_top_right_corner_on_every_screen_size(browser, size):
    context, page = open_page(browser, seeded_backend(), size=size, hash_="#play")
    settle(page, 1200)
    info = page.evaluate("""() => { const w = document.getElementById('save-widget'); const r = w.getBoundingClientRect();
      return { collapsed: w.classList.contains('collapsed'), top: r.top, right: r.right, width: r.width, height: r.height,
               vw: innerWidth, bodyShown: getComputedStyle(w.querySelector('.save-widget-body')).display !== 'none',
               expanded: w.querySelector('.save-widget-toggle').getAttribute('aria-expanded') }; }""")
    assert info["collapsed"] and not info["bodyShown"] and info["expanded"] == "false"
    assert info["top"] <= 8 and info["right"] >= info["vw"] - 8, "top-right corner"
    assert info["width"] < 260 and info["height"] < 48, "a small pill"
    context.close()


def test_pill_steps_below_a_full_width_bar_fixed_to_the_top(browser):
    extra = '<div id="whats-new-banner" style="position:fixed;top:0;left:0;right:0;height:60px;z-index:600">news</div>'
    context, page = open_page(browser, seeded_backend(), hash_="#play", extra=extra)
    settle(page, 1200)
    assert page.evaluate("document.getElementById('save-widget').getBoundingClientRect().top") >= 60
    page.evaluate("document.getElementById('whats-new-banner').remove()")
    settle(page, 1800)
    assert page.evaluate("document.getElementById('save-widget').getBoundingClientRect().top") <= 8, "back in the corner once the bar is gone"
    context.close()


def test_open_panel_stays_clear_of_the_bottom_ad_bar(browser):
    extra = '<div class="ad-bar" style="position:fixed;left:0;right:0;bottom:0;height:50px"></div>'
    context, page = open_page(browser, seeded_backend(), size=(360, 420), hash_="#play", extra=extra)
    settle(page, 1200)
    expand_widget(page)
    bottom = page.evaluate("document.getElementById('save-widget').getBoundingClientRect().bottom")
    assert bottom <= 420 - 50, bottom
    context.close()


def test_saved_line_reads_the_time_since_the_last_save(browser):
    backend = MockBackend()
    context, page = open_page(browser, backend, signed_in=False, hash_="#play")
    settle(page, 800)
    assert pill_text(page) == "Not saved yet"
    expand_widget(page)
    page.locator(".save-widget-save-button").click()
    settle(page, 900)
    assert pill_text(page) == "Saved just now"
    assert page.evaluate("document.querySelector('.save-widget-toggle').getAttribute('aria-label')").endswith("Saved just now")
    context.close()
    seven = int(time.time() * 1000) - 7 * 60 * 1000
    context, page = open_page(browser, MockBackend(), signed_in=False, hash_="#play", store={"savedat:harness": str(seven)})
    settle(page, 800)
    assert pill_text(page) == "Saved 7 min ago"
    assert "7 minutes ago" in page.evaluate("document.querySelector('.save-widget-saved-line').title")
    context.close()


def test_a_failed_save_becomes_a_plain_text_warning_until_the_next_good_save(browser):
    backend = SnapBackend()
    backend.add(1, 11, 5)
    context, page = open_page(browser, backend, hash_="#play", store={"activeslot:harness": "1"})
    settle(page, 1200)
    expand_widget(page)
    backend.fail_saves = True
    page.locator(".save-widget-slot").nth(0).get_by_text("Save here").click()
    settle(page, 900)
    assert pill_text(page) == "Save failed — try again"
    assert page.locator(".save-widget-saved-line").get_attribute("data-state") == "failed"
    assert page.locator(".save-widget-warning").is_visible()
    assert "did not go through" in page.locator(".save-widget-warning").inner_text()
    assert page.locator(".save-widget-warning").get_attribute("role") == "status"
    backend.fail_saves = False
    page.locator(".save-widget-slot").nth(0).get_by_text("Save here").click()
    settle(page, 900)
    assert pill_text(page) == "Saved just now" and page.locator(".save-widget-warning").is_hidden()
    context.close()


def test_a_failed_autosave_also_shows_the_warning(browser):
    backend = SnapBackend()
    backend.add(1, 11, 5)
    context, page = open_page(browser, backend, hash_="#play",
                              store={"activeslot:harness": "1", "autosave-enabled:harness": "true"})
    settle(page, 1200)
    backend.fail_saves = True
    # the autosave only writes to a slot the player confirmed this visit: confirm slot 1 via a good save first
    backend.fail_saves = False
    expand_widget(page)
    page.locator(".save-widget-slot").nth(0).get_by_text("Save here").click()
    settle(page, 800)
    assert pill_text(page) == "Saved just now"
    backend.fail_saves = True
    restart_autosave_under_a_fake_clock(page)
    page.clock.run_for(5 * 60 * 1000 + 100)
    settle(page, 900)
    assert pill_text(page) == "Save failed — try again"
    context.close()


def test_desktop_boot_reserves_the_corner_in_the_top_bar(browser):
    extra = ('<div id="pc-topbar" style="display:flex;justify-content:flex-end;position:relative">'
             '<div id="speed" style="width:300px;height:40px;background:#444">speed</div></div>'
             '<div id="pc-menu-panel"><div class="pc-menu-group"><h3>Game</h3></div></div>')
    pre = "window.NOYVJ_LAYOUT = 'pc'; document.documentElement.setAttribute('data-layout', 'pc');"
    context, page = open_page(browser, seeded_backend(), size=(1440, 900), hash_="#play", extra=extra, pre=pre)
    settle(page, 1500)
    geo = page.evaluate("""() => { const w = document.getElementById('save-widget').getBoundingClientRect();
      const s = document.getElementById('speed').getBoundingClientRect();
      return { wLeft: w.left, sRight: s.right, pad: getComputedStyle(document.getElementById('pc-topbar')).paddingRight }; }""")
    assert float(geo["pad"].rstrip("px")) >= 100
    assert geo["sRight"] <= geo["wLeft"], "the top bar's own controls end before the pill starts"
    context.close()


def test_pill_slides_left_of_a_theme_toggle_a_game_pins_in_the_corner(browser):
    extra = ('<button id="theme-toggle-floating" style="position:fixed;top:11px;right:16px;width:104px;height:32px;z-index:800">Light</button>'
             '<div id="pc-topbar" style="display:flex;justify-content:flex-start"><div id="tools" style="width:2000px;height:30px"></div></div>')
    pre = "window.NOYVJ_LAYOUT = 'pc'; document.documentElement.setAttribute('data-layout', 'pc');"
    context, page = open_page(browser, seeded_backend(), size=(1440, 900), hash_="#play", extra=extra, pre=pre)
    settle(page, 1800)
    geo = page.evaluate("""() => { const w = document.getElementById('save-widget').getBoundingClientRect();
      const t = document.getElementById('theme-toggle-floating').getBoundingClientRect();
      return { wRight: w.right, tLeft: t.left, wLeft: w.left, barPad: parseFloat(getComputedStyle(document.getElementById('pc-topbar')).paddingRight) }; }""")
    assert geo["wRight"] <= geo["tLeft"], "the pill sits to the left of the theme toggle, not on top of it"
    assert geo["barPad"] >= 1440 - 16 - geo["wLeft"] - 8 - 1, "and the top bar clears the pill"
    context.close()


def test_a_game_stylesheet_that_pins_the_widget_to_the_bottom_cannot_stretch_the_pill(browser):
    extra = "<style>html body #save-widget.collapsed { bottom: 3px; }</style>"
    context, page = open_page(browser, seeded_backend(), hash_="#play", extra=extra)
    settle(page, 1200)
    assert page.evaluate("document.getElementById('save-widget').getBoundingClientRect().height") < 50
    context.close()


def test_collapsed_main_menu_button_is_just_its_icon(browser):
    context, page = open_page(browser, seeded_backend(), hash_="#play")
    settle(page, 1500)
    assert page.evaluate("getComputedStyle(document.querySelector('#noyvj-menu-button .noyvj-menu-label')).display") == "none"
    assert page.locator("#noyvj-menu-button").get_attribute("aria-label") == "Main menu"
    expand_widget(page)
    assert page.evaluate("getComputedStyle(document.querySelector('#noyvj-menu-button .noyvj-menu-label')).display") != "none"
    context.close()


# ---------------------------------------------------------------- Z-10

def test_loading_a_save_snapshots_the_state_it_replaces(browser):
    backend = seeded_backend()
    context, page = open_page(browser, backend, hash_="#play", store={"activeslot:harness": "2"})
    settle(page, 1200)
    page.evaluate("window.__state = {v: 50}")
    load_slot(page, 1)
    snaps = local_snaps(page)
    assert len(snaps) == 1 and snaps[0]["slot"] == 2 and snaps[0]["summary"] == "1 key, 0.0 KB"
    assert page.evaluate("window.__loaded") == {"v": 11}
    posted = [s for s in backend.snaps]
    assert len(posted) == 1 and posted[0]["slot"] == 2 and posted[0]["save_data"] == {"v": 50}
    assert snaps[0]["rid"] == posted[0]["id"], "the local entry remembers its backend id"
    context.close()


def test_a_default_or_unchanged_state_is_never_snapshotted(browser):
    backend = seeded_backend()
    context, page = open_page(browser, backend, hash_="#play")
    settle(page, 1200)
    page.evaluate("window.__state = {v: 7}")   # the state the game booted with
    load_slot(page, 1)
    assert local_snaps(page) == [] and backend.snaps == []
    use_raw_state(page)
    page.evaluate("window.__raw = {}")         # an empty state
    load_slot(page, 2)
    assert local_snaps(page) == [] and backend.snaps == []
    page.evaluate("window.__raw = {v: 40}")
    load_slot(page, 1)
    assert len(local_snaps(page)) == 1 and local_snaps(page)[0]["slot"] == 2   # taken while slot 2 was the active one
    page.evaluate("window.__raw = {v: 40}")     # the same state again: slot 1 is active now, so one more row...
    load_slot(page, 1)
    page.evaluate("window.__raw = {v: 40}")     # ...but a third load of the same state in the same slot adds nothing
    load_slot(page, 1)
    assert [s["slot"] for s in local_snaps(page)] == [1, 2]
    context.close()


def test_only_the_newest_five_snapshots_per_slot_are_kept_locally(browser):
    backend = seeded_backend()
    context, page = open_page(browser, backend, hash_="#play", store={"activeslot:harness": "1"})
    settle(page, 1200)
    for n in range(1, 8):
        page.evaluate(f"window.__state = {{v: {100 + n}}}")
        load_slot(page, 2)
    snaps = local_snaps(page)
    assert len(snaps) == 5
    assert page.evaluate("JSON.parse(localStorage.getItem('snapshots:harness'))[0].json") == '{"v":107}'
    context.close()


def test_a_huge_state_is_not_stored_locally_but_the_widget_keeps_working(browser):
    backend = seeded_backend()
    context, page = open_page(browser, backend, hash_="#play")
    settle(page, 1200)
    use_raw_state(page)
    page.evaluate("window.__raw = {blob: 'x'.repeat(200000)}")
    load_slot(page, 1)
    assert local_snaps(page) == [], "over the local size guard"
    assert len(backend.snaps) == 1, "but the backend takes it"
    assert page.evaluate("window.__loaded") == {"v": 11}
    context.close()


def test_a_full_or_blocked_storage_never_breaks_a_load(browser):
    backend = seeded_backend()
    context, page = open_page(browser, backend, hash_="#play")
    settle(page, 1200)
    page.evaluate("""() => { const real = Storage.prototype.setItem;
      Storage.prototype.setItem = function (k, v) { if (k.startsWith('snapshots:')) throw new DOMException('quota', 'QuotaExceededError'); return real.call(this, k, v); }; }""")
    page.evaluate("window.__state = {v: 60}")
    load_slot(page, 1)
    assert page.evaluate("window.__loaded") == {"v": 11}
    assert local_snaps(page) == []
    context.close()


def test_the_summary_uses_the_games_own_headline_when_it_has_one(browser):
    pre = """const realGet = window.pyodide.globals.get;
      window.pyodide.globals.get = (n) => n === 'share_result'
        ? () => JSON.stringify({game: 'H', score: 1234, unit: 'pts', stats: ['3 turns', {n: 2, one: 'storm', many: 'storms'}, 'dropped']})
        : realGet(n);"""
    backend = seeded_backend()
    context, page = open_page(browser, backend, hash_="#play", pre=pre)
    settle(page, 1200)
    page.evaluate("window.__state = {v: 50}")
    load_slot(page, 1)
    assert local_snaps(page)[0]["summary"] == "1,234 pts, 3 turns, 2 storms"
    context.close()


def test_autosave_snapshots_at_most_once_per_ten_minutes(browser):
    backend = seeded_backend()
    context, page = open_page(browser, backend, hash_="#play",
                              store={"activeslot:harness": "2", "autosave-enabled:harness": "true"})
    settle(page, 800)
    restart_autosave_under_a_fake_clock(page)
    page.evaluate("window.__state = {v: 70}")
    page.clock.run_for(5 * 60 * 1000 + 100)     # first tick: a snapshot
    settle(page, 300)
    assert len(local_snaps(page)) == 1
    page.evaluate("window.__state = {v: 71}")
    page.clock.run_for(5 * 60 * 1000)           # five minutes later: too soon
    settle(page, 300)
    assert len(local_snaps(page)) == 1
    page.evaluate("window.__state = {v: 72}")
    page.clock.run_for(5 * 60 * 1000)           # ten minutes after the first: allowed again
    settle(page, 300)
    assert len(local_snaps(page)) == 2
    context.close()


def test_restore_list_shows_time_and_summary_and_restoring_can_be_undone(browser):
    backend = seeded_backend()
    extra = '<script src="/shared/confirm-dialog.js"></script>'
    context, page = open_page(browser, backend, hash_="#play", extra=extra, store={"activeslot:harness": "2"})
    settle(page, 1200)
    page.evaluate("window.__state = {v: 50}")
    load_slot(page, 1)                                   # snapshots {v:50}; game is now {v:11}
    page.locator(".save-widget-restore-toggle").click()
    settle(page, 500)
    items = page.locator(".save-widget-restore-item")
    assert items.count() == 1, "the local entry and its backend twin are one row"
    text = items.first.inner_text()
    assert "just now" in text and "slot 2" in text and "1 key, 0.0 KB" in text
    items.first.get_by_text("Restore").click()
    assert page.locator("#confirm-dialog-overlay").is_visible(), "restoring asks first"
    assert "snapshotted first" in page.locator("#confirm-dialog-overlay").inner_text()
    page.locator("#confirm-dialog-confirm").click()
    settle(page, 700)
    assert page.evaluate("window.__loaded") == {"v": 50}
    assert "Restored" in page.locator(".save-widget-status").inner_text()
    # the state it replaced ({v: 11}) was snapshotted first, so the restore can be undone
    assert page.locator(".save-widget-restore-item").count() == 2
    assert page.locator(".save-widget-restore-item").first.inner_text().count("1 key") == 1
    page.locator(".save-widget-restore-item").first.get_by_text("Restore").click()
    page.locator("#confirm-dialog-confirm").click()
    settle(page, 700)
    assert page.evaluate("window.__loaded") == {"v": 11}
    context.close()


def test_restore_list_includes_snapshots_that_exist_only_on_the_account(browser):
    backend = seeded_backend()
    backend.snaps.append({"id": "snap-old", "game_id": "harness", "slot": 3, "summary": "Day 9, 4 plots", "size": 20,
                          "created_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(time.time() - 3 * 3600)),
                          "save_data": {"v": 909}})
    context, page = open_page(browser, backend, hash_="#play")
    settle(page, 1200)
    expand_widget(page)
    page.locator(".save-widget-restore-toggle").click()
    settle(page, 500)
    row = page.locator(".save-widget-restore-item")
    assert row.count() == 1 and "Day 9, 4 plots" in row.first.inner_text() and "3 h ago" in row.first.inner_text()
    row.first.get_by_text("Restore").click()          # no confirm dialog on this page: acts at once
    settle(page, 700)
    assert page.evaluate("window.__loaded") == {"v": 909}
    context.close()


def test_anonymous_players_snapshot_locally_only(browser):
    backend = MockBackend()
    backend.add(None, 5, 3, code="ZZZZ-1111", user=False)
    context, page = open_page(browser, backend, signed_in=False, hash_="#play")
    settle(page, 1200)
    page.evaluate("window.__state = {v: 33}")
    expand_widget(page)
    page.evaluate("document.querySelector('.save-widget-load-input').value = 'ZZZZ-1111'")
    page.locator(".save-widget-load-button").click()
    settle(page, 900)
    snaps = local_snaps(page)
    assert len(snaps) == 1 and snaps[0]["slot"] == 0 and snaps[0]["rid"] is None
    assert not any(path.startswith("/users/me/snapshots") for _, path in backend.log)
    context.close()


def test_new_game_from_the_menu_snapshots_what_was_on_screen(browser):
    backend = seeded_backend()
    context, page = open_page(browser, backend, hash_="#play")
    settle(page, 1500)
    page.evaluate("window.__state = {v: 123}")
    page.on("dialog", lambda d: d.accept())
    page.locator("#noyvj-menu-button").click()
    with page.expect_navigation():
        page.locator('#opening-screen [data-action="new"]').click()
    settle(page, 1200)
    snaps = local_snaps(page)
    assert len(snaps) == 1 and json.loads(page.evaluate("JSON.parse(localStorage.getItem('snapshots:harness'))[0].json")) == {"v": 123}
    context.close()


def test_a_snapshot_that_could_not_be_uploaded_is_sent_on_the_next_visit(browser):
    backend = seeded_backend()
    backend.snap_status = 500
    context, page = open_page(browser, backend, hash_="#play")
    settle(page, 1200)
    page.evaluate("window.__state = {v: 50}")
    load_slot(page, 1)
    assert local_snaps(page)[0]["rid"] is None and backend.snaps == []
    backend.snap_status = 200
    page.reload()
    settle(page, 1500)
    assert len(backend.snaps) == 1 and backend.snaps[0]["save_data"] == {"v": 50}
    assert local_snaps(page)[0]["rid"] == backend.snaps[0]["id"]
    context.close()
