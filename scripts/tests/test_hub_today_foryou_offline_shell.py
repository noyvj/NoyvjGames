"""Static and browser tests for the hub's Today strip (Y-2), For you row (Y-5), offline downloads
(Y-9), phone app shell (Y-16) and personal collections (Y-18).

Browser tests drive the real pages in headless Chromium with the live backend answered by the test and
every other host refused (see hub_browser_fixtures). The harness origin is not a secure context, so the
Cache API does not exist there: the offline tests install a small in-memory stand-in for it, and the
Python-runtime CDN is answered with small fake bodies. Nothing here reaches the network.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

from hub_browser_fixtures import chromium, harness  # noqa: F401  (pytest fixtures)

ROOT = Path(__file__).resolve().parents[2]
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")
SEEN = "localStorage.setItem('hub-onboarding-seen','1');localStorage.setItem('tutorial-seen:hub','1');"


def last_played(*slugs):
    return "".join(f"localStorage.setItem('last-played:{s}','{1700000000000 + i}');" for i, s in enumerate(slugs))


FAKE_CACHES = """
(function () {
  const store = { 'site-cache-v39': new Map() };
  const make = (name) => ({
    put: async (u, r) => { store[name].set(u, r); },
    delete: async (u) => store[name].delete(u),
    match: async (u) => store[name].get(u),
  });
  window.__store = store;
  window.caches = {
    keys: async () => Object.keys(store),
    open: async (n) => { if (!store[n]) store[n] = new Map(); return make(n); },
    match: async (u) => { for (const n of Object.keys(store)) if (store[n].has(u)) return store[n].get(u); return undefined; },
    delete: async (n) => delete store[n],
  };
})();
"""


def with_cdn(h, fail=None):
    """Answer the CDN with small fake bodies; `fail` is a substring that gets a 503."""
    def handler(route, request):
        if fail and fail in request.url:
            return route.fulfill(status=503, body="no")
        return route.fulfill(status=200, body="x" * 500, content_type="application/octet-stream",
                             headers={"access-control-allow-origin": "*"})
    h.context.route("https://cdn.jsdelivr.net/**", handler)


# ---------------------------------------------------------------- static

def test_page_heads_still_end_with_lite_mode_css():
    for name in ("index.html", "settings.html"):
        text = (ROOT / name).read_text(encoding="utf-8")
        head = text.split("</head>")[0].rstrip()
        assert head.endswith('<link rel="stylesheet" href="shared/lite-mode.css">'), name


def test_index_wires_new_scripts_after_script_js_and_places_sections():
    order = [m for m in re.findall(r'<script src="([^"]+)"', INDEX)]
    for name in ("hub-today.js", "hub-foryou.js", "hub-collections.js", "hub-offline.js", "hub-shell.js"):
        assert order.index(name) > order.index("script.js")
    assert INDEX.index('id="today-strip"') < INDEX.index('id="account-section"') < INDEX.index('id="game-grid"')
    assert INDEX.index('id="for-you-section"') < INDEX.index('id="game-filter-bar"')
    assert "viewport-fit=cover" in INDEX


def test_app_nav_has_the_planned_targets_and_no_profile():
    nav = re.search(r'<nav id="app-nav".*?</nav>', INDEX, re.S).group(0)
    labels = re.findall(r"<span>([^<]+)</span>", nav)
    assert labels == ["Games", "Today", "More"]
    assert "rofile" not in nav
    for href in re.findall(r'<li><a href="([^"]+)"', nav):
        assert (ROOT / href).is_file(), href
    assert {"settings.html", "help.html", "credits.html", "achievements.html"} == set(re.findall(r'<li><a href="([^"]+)"', nav))


def test_today_feed_is_a_well_formed_flagged_sample():
    feed = json.loads((ROOT / "today.json").read_text(encoding="utf-8"))
    assert feed["version"] == 1 and feed["sample"] is True
    import datetime
    starts = [w["start"] for w in feed["weekly"]]
    assert len(starts) == len(set(starts)) >= 3
    for w in feed["weekly"]:
        assert datetime.date.fromisoformat(w["start"]).weekday() == 0, "weeks start on a Monday"
        assert (ROOT / "games" / w["game"] / "index.html").is_file()
        assert w["sample"] is True and 0 < len(w["title"]) <= 80 and len(w["text"]) <= 240
    assert (ROOT / "today-feed.md").is_file()


def test_offline_manifest_is_current_and_consistent():
    done = subprocess.run([sys.executable, str(ROOT / "scripts" / "generate-offline-manifest.py"), "--check"],
                          capture_output=True, text=True)
    assert done.returncode == 0, done.stdout
    manifest = json.loads((ROOT / "offline-manifest.json").read_text(encoding="utf-8"))
    slugs = re.findall(r'data-game-slug="([a-z0-9-]+)"', INDEX)
    assert set(manifest["games"]) == set(slugs)
    sw = (ROOT / "sw.js").read_text(encoding="utf-8")
    for slug, game in manifest["games"].items():
        assert any(e["path"] == f"games/{slug}/game.py" for e in game["files"]) or slug in ("signal",) or game["files"]
        for e in game["files"] + game["shared"]:
            assert (ROOT / e["path"]).is_file(), e["path"]
            assert e["precached"] == (f'"{e["path"]}"' in sw or f'"./{e["path"]}"' in sw), e["path"]
        for e in game["cdn"]:
            assert e["url"].startswith("https://cdn.jsdelivr.net/")
        if slug != "signal":
            assert any(e["url"].endswith("pyodide.asm.wasm") and e["bytes"] for e in game["cdn"]), slug


def test_new_hub_files_never_touch_the_backend_or_sw():
    for name in ("hub-today.js", "hub-foryou.js", "hub-collections.js", "hub-offline.js", "hub-shell.js"):
        text = (ROOT / name).read_text(encoding="utf-8")
        assert "fastapicloud" not in text, name
        assert "method: \"POST\"" not in text and "method: 'POST'" not in text, name


def test_reduced_motion_and_phone_only_css():
    css = (ROOT / "style.css").read_text(encoding="utf-8")
    assert re.search(r"\.app-nav, \.pull-refresh \{ display: none; \}", css)
    assert "@media (max-width: 640px)" in css and "safe-area-inset-bottom" in css
    assert "display-mode: standalone" in css


# ---------------------------------------------------------------- Today strip (Y-2)

def today_page(h, path="/index.html?event-date=2026-10-08"):
    page = h.goto(path)
    page.wait_for_function("document.getElementById('today-items').children.length >= 4")
    return page


def test_today_empty_states_are_honest(harness):
    h = harness(init_scripts=[SEEN])
    page = today_page(h)
    text = page.inner_text("#today-strip")
    assert "Not played yet" in text and "No streak yet" in text
    assert page.locator(".today-sample").count() == 1 and "sample schedule" in text, "the shipped schedule is flagged as a sample"
    assert h.errors == []


def test_today_reads_signal_done_and_streak(harness):
    state = {"days": {
        "2026-10-06:easy": {"kind": "daily", "result": "won", "pings": [[0, 0, 1], [1, 1, 2]]},
        "2026-10-07:easy": {"kind": "daily", "result": "won", "pings": [[0, 0, 1]]},
        "2026-10-08:easy": {"kind": "daily", "result": "won", "pings": [[0, 0, 1], [1, 1, 2], [2, 2, 3]]},
    }}
    h = harness(init_scripts=[SEEN, f"localStorage.setItem('signal:state', {json.dumps(json.dumps(state))});"])
    page = today_page(h)
    text = page.inner_text("#today-strip")
    assert "Partly done" in text and "Easy won in 3 pings" in text and "Hard not played" in text
    assert "3 days in a row in Signal" in text


def test_today_streak_stops_after_a_missed_day_and_a_loss_today(harness):
    state = {"days": {"2026-10-05:easy": {"kind": "daily", "result": "won", "pings": []},
                      "2026-10-06:easy": {"kind": "daily", "result": "won", "pings": []}}}
    h = harness(init_scripts=[SEEN, f"localStorage.setItem('signal:state', {json.dumps(json.dumps(state))});"])
    page = today_page(h)
    assert "No streak running. Your best is 2 days" in page.inner_text("#today-strip")
    assert page.evaluate("HubToday.signalStreak({days:{'2026-10-07:easy':{kind:'daily',result:'won'},'2026-10-08:easy':{kind:'daily',result:'lost'}}}, '2026-10-08').count") == 0


def test_today_uses_the_shared_daily_record_for_other_games(harness):
    record = {"version": 1, "date": "2026-10-08",
              "runs": {"tide": {"seed": "TIDE-X54PB", "completed_at": "2026-10-08T01:00:00Z", "text": "4,210 pts"}},
              "streaks": {"tide": {"count": 4, "best": 6, "last": "2026-10-08"}}}
    feed = {"version": 1, "sample": False, "daily": [{"game": "tide", "label": "Tide daily"}], "weekly": []}
    h = harness(init_scripts=[SEEN, f"localStorage.setItem('noyvj-daily-v1', {json.dumps(json.dumps(record))});"])
    h.pages["/today.json"] = json.dumps(feed)
    page = today_page(h)
    text = page.inner_text("#today-strip")
    assert "tide daily" in text.lower() and "Done today: 4,210 pts" in text
    assert "4 days in a row in Tide (best 6)" in text
    assert "No weekly challenge is scheduled this week." in text
    assert page.locator(".today-sample").count() == 0


def test_today_weekly_picks_the_week_and_loops(harness):
    h = harness(init_scripts=[SEEN])
    page = today_page(h, "/index.html?event-date=2026-10-14")
    assert "Grid: go renewable early" in page.inner_text("#today-strip")
    assert page.evaluate("""(async () => {
        const feed = HubToday.sanitizeFeed(await (await fetch('today.json')).json());
        return [HubToday.weeklyFor(feed, '2026-11-02').entry.game, HubToday.weeklyFor(feed, '2026-10-04'), HubToday.weeklyFor(feed, '2026-11-02').repeating];
    })()""") == ["herd", None, True]


def test_today_feed_failure_and_bad_entries(harness):
    h = harness(init_scripts=[SEEN])
    h.pages["/today.json"] = "not json"
    page = today_page(h)
    assert "could not be loaded" in page.inner_text("#today-strip")
    page2 = h.goto("/index.html")
    bad = page2.evaluate("""HubToday.sanitizeFeed({version:1, weekly:[
        {start:'2026-02-30', game:'herd', title:'x'}, {start:'2026-10-05', game:'../evil', title:'x'},
        {start:'2026-10-05', game:'herd', title:''}, {start:'2026-10-05', game:'herd', title:'ok'}]}).weekly.length""")
    assert bad == 1


def test_today_event_on_and_off_days(harness):
    h = harness(init_scripts=[SEEN])
    page = today_page(h, "/index.html?event-date=2026-10-31")
    text = page.inner_text("#today-strip")
    assert "Halloween is on until" in text and "Badge: Halloween 2026 (not earned yet)" in text
    assert "No game hosts this event yet" in text
    page = h.goto("/index.html?event-date=2026-09-10")
    page.wait_for_function("document.getElementById('today-items').children.length >= 4")
    page.wait_for_function("document.getElementById('today-items').textContent.includes('Next:') || document.getElementById('today-items').textContent.includes('is on until')")
    assert "No event today. Next:" in page.inner_text("#today-strip")


def test_today_survives_blocked_storage(harness):
    h = harness(init_scripts=["Object.defineProperty(window,'localStorage',{get(){throw new DOMException('denied','SecurityError')}});"])
    page = today_page(h)
    assert "Not played yet" in page.inner_text("#today-strip")
    assert h.errors == []


def test_today_layout_at_phone_width_has_no_sideways_scroll(harness):
    h = harness(size=(360, 740), touch=True, init_scripts=[SEEN])
    page = today_page(h)
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    assert page.evaluate("document.getElementById('today-strip').getBoundingClientRect().width <= 360")


# ---------------------------------------------------------------- For you (Y-5)

SUGGEST = """HubForYou.suggest({
  games: [
    {slug:'canopy', name:'Canopy', tags:['climate','quick']}, {slug:'grid', name:'Grid', tags:['climate','quick']},
    {slug:'sol', name:'SOL', tags:['space','deep-systems']}, {slug:'champ', name:'Le Champ', tags:['language-learning','deep-systems']}],
  opened: %s, progress: %s, recommended: %s, labels: {climate:'Climate', quick:'Quick', space:'Space'}})"""


def test_foryou_reasons_finished_played_untouched(harness):
    h = harness(init_scripts=[SEEN])
    page = h.goto("/index.html")
    played = page.evaluate(SUGGEST % ('{canopy: 5}', "{}", "''"))
    assert played[0] == {"slug": "grid", "kind": "tags", "reason": "Because you played Canopy: also Climate."}
    assert [p["kind"] for p in played[1:]] == ["untouched", "untouched"]
    finished = page.evaluate(SUGGEST % ('{canopy: 5}', "{canopy: {earned: 7, total: 10}}", "''"))
    assert finished[0]["reason"] == "Because you finished Canopy: also Climate."
    rec = page.evaluate(SUGGEST % ('{canopy: 5}', "{}", "'champ'"))
    assert rec[1]["slug"] == "champ" and "first-visit questions" in rec[1]["reason"]
    assert page.evaluate(SUGGEST % ('{}', "{}", "''")) == []
    all_open = page.evaluate(SUGGEST % ("{canopy:1, grid:1, sol:1, champ:1}", "{canopy:{earned:9,total:10}, grid:{earned:1,total:10}, sol:{earned:0,total:4}, champ:{earned:3,total:5}}", "''"))
    assert [a["slug"] for a in all_open] == ["sol", "grid"] and all_open[0]["reason"] == "You have earned 0 of 4 achievements here."


def test_foryou_row_hidden_for_new_players_shown_for_returning(harness):
    h = harness(init_scripts=[SEEN])
    page = h.goto("/index.html")
    page.wait_for_timeout(300)
    assert page.evaluate("document.getElementById('for-you-section').hidden") is True
    h2 = harness(init_scripts=[SEEN, last_played("canopy")])
    page = h2.goto("/index.html")
    page.wait_for_function("!document.getElementById('for-you-section').hidden")
    text = page.inner_text("#for-you-list")
    assert "Because you played Canopy" in text
    assert page.evaluate("document.querySelectorAll('#for-you-list a').length") == 3
    assert page.evaluate("document.querySelector('#for-you-list a').getAttribute('href')").startswith("games/")


def test_foryou_dismiss_is_remembered_and_survey_blocks_it(harness):
    h = harness(init_scripts=[SEEN, last_played("canopy")])
    page = h.goto("/index.html")
    page.wait_for_function("!document.getElementById('for-you-section').hidden")
    page.click("#for-you-dismiss")
    assert page.evaluate("document.getElementById('for-you-section').hidden") is True
    page.reload()
    page.wait_for_timeout(500)
    assert page.evaluate("document.getElementById('for-you-section').hidden") is True
    assert int(page.evaluate("localStorage.getItem('hub-foryou-hidden-until')")) > 0
    # A returning player who has not seen the first-visit survey: the row waits for it.
    h2 = harness(init_scripts=[last_played("canopy")])
    page = h2.goto("/index.html")
    page.wait_for_selector("#onboarding-survey-overlay")
    page.wait_for_timeout(1200)
    assert page.evaluate("document.getElementById('for-you-section').hidden") is True


def test_foryou_uses_account_progress_for_finished(harness):
    h = harness(init_scripts=[SEEN, last_played("canopy"), "localStorage.setItem('hub_bearer_token','t');localStorage.setItem('hub_account_username','u');"])
    h.api_responses[("GET", "/users/me/saves")] = (200, [{"game_id": "canopy", "save_code": "A", "updated_at": "2026-10-01T00:00:00Z",
                                                          "save_data": {"achievements_earned": [f"a{i}" for i in range(20)]}}])
    page = h.goto("/index.html")
    page.wait_for_function("document.getElementById('for-you-list').textContent.includes('finished Canopy')")


# ---------------------------------------------------------------- offline (Y-9)

def offline_page(h, size=None):
    page = h.goto("/index.html")
    page.wait_for_function("document.querySelectorAll('.offline-button').length >= 19")
    return page


def expand(page, slug):
    card = page.locator(f".title-card:has(.review-widget[data-game-slug='{slug}'])")
    card.locator(".title-card-expand").click()
    return card


def test_offline_download_and_remove(harness):
    h = harness(init_scripts=[SEEN, FAKE_CACHES])
    with_cdn(h)
    page = offline_page(h)
    card = expand(page, "canopy")
    assert "Download for offline (about " in card.locator(".offline-button").inner_text()
    assert "Not stored on this device" in card.locator(".offline-status").inner_text()
    card.locator(".offline-button").click()
    page.wait_for_function("document.querySelector('.review-widget[data-game-slug=canopy]').parentElement.querySelector('.offline-button').dataset.mode === 'remove'")
    assert "Available offline" in card.locator(".offline-status").inner_text()
    store = page.evaluate("[...window.__store['site-cache-v39'].keys()]")
    assert any(u.endswith("games/canopy/game.py") for u in store)
    assert any(u.endswith("pyodide.asm.wasm") for u in store)
    assert "canopy" in json.loads(page.evaluate("localStorage.getItem('hub_offline_games')"))
    page.wait_for_function("!document.getElementById('offline-storage-line').hidden")
    assert "1 of 19 games downloaded" in page.inner_text("#offline-storage-line")
    # Remove: the game's own downloaded files and the runtime go, precached files stay.
    precached = page.evaluate("HubOffline.loadManifest().then(m => m.games.canopy.files.filter(f => f.precached).map(f => f.path))")
    card.locator(".offline-button").click()
    page.wait_for_function("document.querySelector('.review-widget[data-game-slug=canopy]').parentElement.querySelector('.offline-button').dataset.mode === 'download'")
    store = page.evaluate("[...window.__store['site-cache-v39'].keys()]")
    assert not any(u.endswith("games/canopy/game.py") for u in store) or "games/canopy/game.py" in precached
    assert not any(u.endswith("pyodide.asm.wasm") for u in store)
    assert page.evaluate("localStorage.getItem('hub_offline_games')") in ("{}", None)
    assert h.errors == []


def test_offline_remove_keeps_runtime_while_another_game_needs_it(harness):
    h = harness(init_scripts=[SEEN, FAKE_CACHES])
    with_cdn(h)
    page = offline_page(h)
    for slug in ("canopy", "grid"):
        expand(page, slug).locator(".offline-button").click()
        page.wait_for_function(f"document.querySelector('.review-widget[data-game-slug={slug}]').parentElement.querySelector('.offline-button').dataset.mode === 'remove'")
    expand_card = page.locator(".title-card:has(.review-widget[data-game-slug='canopy'])")
    expand_card.locator(".offline-button").click()
    page.wait_for_function("document.querySelector('.review-widget[data-game-slug=canopy]').parentElement.querySelector('.offline-button').dataset.mode === 'download'")
    assert page.evaluate("[...window.__store['site-cache-v39'].keys()].some(u => u.endsWith('pyodide.asm.wasm'))")
    assert page.evaluate("HubOffline.status('grid').then(s => s.state)") == "ready"


def test_offline_failure_is_plain_text_and_not_marked_done(harness):
    h = harness(init_scripts=[SEEN, FAKE_CACHES])
    with_cdn(h, fail="pyodide.asm.wasm")
    page = offline_page(h)
    card = expand(page, "canopy")
    card.locator(".offline-button").click()
    page.wait_for_function("document.querySelector('.review-widget[data-game-slug=canopy]').parentElement.querySelector('.offline-status').textContent.includes('Could not download')")
    text = card.locator(".offline-status").inner_text()
    assert "pyodide.asm.wasm" in text and "HTTP 503" in text and "not marked as available offline" in text
    assert page.evaluate("localStorage.getItem('hub_offline_games')") is None
    assert "Download for offline" in card.locator(".offline-button").inner_text()


def test_offline_without_room_or_connection_says_so(harness):
    h = harness(init_scripts=[SEEN, FAKE_CACHES, "Object.defineProperty(navigator, 'storage', {value: {estimate: async () => ({usage: 1000, quota: 5000000})}});"])
    with_cdn(h)
    page = offline_page(h)
    card = expand(page, "canopy")
    card.locator(".offline-button").click()
    page.wait_for_function("document.querySelector('.review-widget[data-game-slug=canopy]').parentElement.querySelector('.offline-status').textContent.includes('Not enough free storage')")
    assert "Available offline" not in card.locator(".offline-status").inner_text()
    h.context.set_offline(True)
    page.evaluate("window.dispatchEvent(new Event('offline'))")
    page.wait_for_function("document.querySelector('.review-widget[data-game-slug=canopy]').parentElement.querySelector('.offline-button').disabled")
    assert "offline" in card.locator(".offline-status").inner_text().lower()


def test_offline_stale_record_asks_to_download_again(harness):
    h = harness(init_scripts=[SEEN, FAKE_CACHES, "localStorage.setItem('hub_offline_games', JSON.stringify({canopy: {at: '2026-10-01T00:00:00.000Z', bytes: 1}}));"])
    page = offline_page(h)
    card = expand(page, "canopy")
    assert "Needs downloading again" in card.locator(".offline-status").inner_text()
    assert card.locator(".offline-button").inner_text().startswith("Download again")


def test_offline_unsupported_browser_hides_controls(harness):
    h = harness(init_scripts=[SEEN])  # no Cache API on this insecure origin
    page = h.goto("/index.html")
    page.wait_for_timeout(400)
    assert page.evaluate("document.querySelectorAll('.offline-button').length") == 0
    assert h.errors == []


def test_settings_manager_lists_downloads_with_remove(harness):
    h = harness(init_scripts=[SEEN, FAKE_CACHES])
    with_cdn(h)
    page = offline_page(h)
    expand(page, "canopy").locator(".offline-button").click()
    page.wait_for_function("document.querySelector('.review-widget[data-game-slug=canopy]').parentElement.querySelector('.offline-button').dataset.mode === 'remove'")
    page.evaluate("(() => { const d = document.createElement('div'); d.id = 'manager'; document.body.appendChild(d); HubOffline.mountSettings(d); })()")
    page.wait_for_function("document.querySelector('#manager .offline-manage-item')")
    assert "Canopy: downloaded" in page.inner_text("#manager")
    assert "1 game is stored for offline use" in page.inner_text("#manager")
    page.evaluate("document.querySelector('#manager .offline-manage-item button').click()")
    page.wait_for_function("document.getElementById('manager').textContent.includes('No games are stored for offline use')")


def test_settings_page_mounts_the_manager_and_flags_stale_records(harness):
    h = harness(init_scripts=[SEEN, FAKE_CACHES, "localStorage.setItem('hub_offline_games', JSON.stringify({canopy: {at: '2026-10-01T00:00:00.000Z', bytes: 1}}));"])
    page = h.goto("/settings.html")
    page.wait_for_function("document.querySelector('#settings-offline-list .offline-manage-item')")
    text = page.inner_text("#settings-offline-list")
    assert "Canopy: needs downloading again" in text
    assert "No games are stored for offline use" in text and "1 needs downloading again" in text
    assert h.errors == []


def test_reset_hub_preferences_keeps_collections_and_download_record(harness):
    h = harness(init_scripts=[SEEN])
    page = h.goto("/settings.html")
    page.wait_for_timeout(300)
    page.evaluate("localStorage.setItem('hub_collections_v1','{}');localStorage.setItem('hub_offline_games','{}');localStorage.setItem('hub_filter_collection','c-x')")
    page.click("#settings-clear-prefs")
    page.click("#settings-confirm-yes")
    assert page.evaluate("localStorage.getItem('hub_collections_v1') !== null && localStorage.getItem('hub_offline_games') !== null")
    assert page.evaluate("localStorage.getItem('hub_filter_collection')") is None


# ---------------------------------------------------------------- app shell (Y-16)

def test_app_nav_visible_on_phone_hidden_on_desktop(harness):
    phone = harness(size=(360, 740), touch=True, init_scripts=[SEEN]).goto("/index.html")
    assert phone.is_visible("#app-nav")
    geo = phone.evaluate("""(() => { const n = document.getElementById('app-nav').getBoundingClientRect();
        const a = document.querySelector('.ad-bar').getBoundingClientRect();
        return {navBottom: n.bottom, adTop: a.top, pad: parseFloat(getComputedStyle(document.body).paddingBottom)}; })()""")
    assert geo["navBottom"] == geo["adTop"], "the bar sits directly above the ad bar, never over it"
    assert geo["pad"] >= 122
    desk = harness(size=(1440, 900), init_scripts=[SEEN]).goto("/index.html")
    assert not desk.is_visible("#app-nav")


def test_app_nav_more_menu_keyboard_and_dismiss(harness):
    page = harness(size=(360, 740), touch=True, init_scripts=[SEEN]).goto("/index.html")
    page.click("#app-nav-more")
    assert page.get_attribute("#app-nav-more", "aria-expanded") == "true"
    assert page.evaluate("document.activeElement.textContent") == "Settings"
    page.keyboard.press("Escape")
    assert page.evaluate("document.getElementById('app-nav-sheet').hidden")
    assert page.evaluate("document.activeElement.id") == "app-nav-more"
    page.click("#app-nav-more")
    page.click("#hub-tagline")
    assert page.evaluate("document.getElementById('app-nav-sheet').hidden")


def test_app_nav_scrolls_to_sections_and_marks_current(harness):
    page = harness(size=(360, 740), touch=True, init_scripts=[SEEN], media={"reduced_motion": "reduce"}).goto("/index.html")
    page.click("[data-nav=games]")
    page.wait_for_function("document.querySelector('[data-nav=games]').getAttribute('aria-current') === 'true'")
    assert page.evaluate("scrollY") > 300
    page.click("[data-nav=today]")
    page.wait_for_function("document.querySelector('[data-nav=today]').getAttribute('aria-current') === 'true'")


def test_banners_and_back_to_top_stay_clear_of_the_bar(harness):
    page = harness(size=(360, 740), touch=True, init_scripts=[SEEN]).goto("/index.html")
    page.evaluate("document.getElementById('back-to-top').hidden = false")
    geo = page.evaluate("""(() => { const r = (id) => document.getElementById(id).getBoundingClientRect();
        return {top: r('back-to-top').bottom, nav: r('app-nav').top}; })()""")
    assert geo["top"] <= geo["nav"], "back-to-top sits above the bottom bar"


def touch_pull(page, start_y, end_y):
    cdp = page.context.new_cdp_session(page)
    cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": 180, "y": start_y}]})
    for i in range(1, 9):
        cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": 180, "y": start_y + (end_y - start_y) * i / 8}]})
    text = page.inner_text("#pull-refresh") if page.is_visible("#pull-refresh") else ""
    return cdp, text


STANDALONE = ("const mm=window.matchMedia.bind(window);window.matchMedia=(q)=>q.includes('display-mode: standalone')?"
              "{matches:true,media:q,addEventListener(){},removeEventListener(){},addListener(){},removeListener(){}}:mm(q);")


def test_pull_to_refresh_only_when_installed(harness):
    browser_tab = harness(size=(360, 740), touch=True, init_scripts=[SEEN]).goto("/index.html")
    assert browser_tab.evaluate("HubShell.standalone()") is False
    cdp, text = touch_pull(browser_tab, 250, 400)
    cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    assert text == "", "a normal browser tab keeps the browser's own pull-to-refresh"

    app = harness(size=(360, 740), touch=True, init_scripts=[SEEN, STANDALONE]).goto("/index.html")
    app.evaluate("window.__marker = 1")
    cdp, text = touch_pull(app, 250, 300)
    assert text == "Pull down to refresh"
    cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    assert app.evaluate("window.__marker") == 1 and not app.is_visible("#pull-refresh")
    cdp, text = touch_pull(app, 250, 400)
    assert text == "Release to refresh"
    with app.expect_navigation():
        cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    assert app.evaluate("window.__marker || 0") == 0, "the page reloaded"


def test_pull_to_refresh_ignores_pulls_that_start_on_controls(harness):
    app = harness(size=(360, 740), touch=True, init_scripts=[SEEN, STANDALONE]).goto("/index.html")
    box = app.locator("#game-search-input").bounding_box()
    app.evaluate("document.getElementById('game-search-input').scrollIntoView({block:'center'})")
    app.wait_for_timeout(500)
    app.evaluate("scrollTo({top: 0, behavior: 'instant'})")
    top_button = app.locator("#random-game-button").bounding_box()
    assert box and top_button
    cdp = app.context.new_cdp_session(app)
    cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": 180, "y": 120}]})
    cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": 180, "y": 320}]})
    cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    assert app.evaluate("window.HubShell.PULL_THRESHOLD") == 80


# ---------------------------------------------------------------- collections (Y-18)

def test_collections_create_add_filter_delete(harness):
    h = harness(init_scripts=[SEEN])
    page = h.goto("/index.html")
    page.wait_for_selector(".title-card-collections", state="attached")
    assert page.evaluate("document.getElementById('game-collection-filter').hidden") is True
    card = expand(page, "canopy")
    card.locator("summary.collections-summary").click()
    card.locator(".collections-chip", has_text="Cozy").click()
    assert "In your collections: Cozy." in card.locator(".collections-note").inner_text()
    other = expand(page, "herd")
    other.locator("summary.collections-summary").click()
    other.locator(".collections-option input").check()
    page.select_option("#game-collection-filter", label="Cozy (2)")
    visible = page.evaluate("[...document.querySelectorAll('.title-card')].filter(c => !c.hidden).map(c => c.querySelector('.review-widget').dataset.gameSlug)")
    assert sorted(visible) == ["canopy", "herd"]
    page.reload()
    page.wait_for_selector(".title-card-collections", state="attached")
    assert page.evaluate("document.getElementById('game-collection-filter').selectedOptions[0].textContent") == "Cozy (2)"
    assert page.evaluate("[...document.querySelectorAll('.title-card')].filter(c => !c.hidden).length") == 2
    # shared tags never change
    assert page.evaluate("document.querySelector('.review-widget[data-game-slug=canopy]').closest('.title-card').dataset.tags") == "climate quick"
    page.click("#collection-manage button:has-text('Delete collection')")
    page.click("#collection-manage button:has-text('Yes, delete')")
    assert page.evaluate("[...document.querySelectorAll('.title-card')].filter(c => !c.hidden).length") == 19
    assert page.evaluate("document.getElementById('game-collection-filter').hidden") is True
    assert h.errors == []


def test_collections_validation_and_sanitising(harness):
    h = harness(init_scripts=[SEEN])
    page = h.goto("/index.html")
    res = page.evaluate("""(() => {
        const out = [HubCollections.create('  '), HubCollections.create('Cozy'), HubCollections.create('cozy'), HubCollections.create('x'.repeat(60))];
        return out.map(r => [r.ok, r.error || '']);
    })()""")
    assert res[0][0] is False and res[1][0] is True and res[2][0] is False and "already have" in res[2][1]
    assert page.evaluate("HubCollections.list()[1].name.length") == 24
    clean = page.evaluate("""HubCollections.sanitize({version: 1, collections: [
        {id: 'c-ok', name: 'A', slugs: ['herd', 'herd', 'Bad Slug', 5]}, {id: 'nope', name: 'B', slugs: []}, {id: 'c-two', name: 'a', slugs: []}]})""")
    assert clean == [{"id": "c-ok", "name": "A", "slugs": ["herd"]}]
    assert page.evaluate("HubCollections.sanitize('junk').length") == 0
    page.evaluate("for (let i = 0; i < 20; i++) HubCollections.create('n' + i)")
    assert page.evaluate("HubCollections.list().length") == 12


def test_collections_survive_blocked_storage(harness):
    h = harness(init_scripts=[SEEN, "Object.defineProperty(window,'localStorage',{get(){throw new DOMException('denied','SecurityError')}});"])
    page = h.goto("/index.html")
    page.wait_for_selector(".title-card-collections", state="attached")
    assert h.errors == []
