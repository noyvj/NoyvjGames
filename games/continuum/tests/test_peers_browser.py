"""peers.js (R-33) in headless Chromium: the Settings sharing switch and the "Show another settlement" /
"Report" network buttons. The Python half (what is sent, how it is drawn) is tested in test_peers.py; here
`window.pyodide` is a stub that returns canned strings, so this file checks only the browser logic: that
nothing is sent before the player acts, what each switch position does, and that every failure ends in a
plain message.

Every API call is answered by a mock inside the page's network layer (an abort-all route is registered
first): nothing here can reach the live backend. Skipped when Playwright or Chromium is not installed."""

import json
import mimetypes
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

ROOT = Path(__file__).resolve().parents[3]
ORIGIN = "http://harness.test"
API = "https://noyvjgames.fastapicloud.dev"

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"></head><body>
<button id="settings-toggle-button" type="button">Settings</button>
<input type="checkbox" id="peer-publish-checkbox" disabled><p id="peer-publish-note"></p>
<button id="peer-show-button" type="button">Show</button>
<button id="peer-report-button" type="button" hidden>Report this settlement</button>
<p id="peer-status"></p>
<script>
  window.pyCalls = [];
  window.PLAN = "";            // what peer_publish_plan returns
  window.QUERY = {scenario: "standard", era: 2, hard: false};
  window.SHOWN = "";           // id of the ghost currently on screen
  window.SHOW_OK = true;
  const FNS = {
    peer_publish_plan: (a, b) => { window.pyCalls.push(["plan", a, b]); return window.PLAN; },
    peer_query_json: (exclude) => { window.pyCalls.push(["query", exclude]); const q = Object.assign({}, window.QUERY); if (exclude) q.exclude = exclude; return JSON.stringify(q); },
    peer_show: (raw) => { window.pyCalls.push(["show", raw]); if (window.SHOW_OK) window.SHOWN = JSON.parse(raw).id; return window.SHOW_OK; },
    peer_ghost_id: () => window.SHOWN,
    peer_message: (kind) => "MSG:" + kind,
  };
  window.pyodide = { globals: { get: (name) => { const f = FNS[name]; if (!f) return undefined; const w = (...a) => f(...a); w.destroy = () => {}; return w; } } };
</script>
<script src="/shared/hub-auth.js"></script>
<script src="/games/continuum/peers.js"></script></body></html>"""

PLAN = json.dumps({"game": "continuum", "scenario": "standard", "hard": False, "opt_in": True,
                   "series": [[s, 2, 10 + s, 50.0 + s] for s in range(1, 9)]})
GHOST = {"id": "0b1c2d3e-aaaa-bbbb-cccc-1234567890ab", "scenario": "standard", "hard": False, "era": 2,
         "seasons": 8, "series": [[s, 2, 12 + s, 51.0 + s] for s in range(1, 9)]}


class Api:
    def __init__(self):
        self.calls = []
        self.user = "alice"
        self.status = {}          # (method, path) -> status code override
        self.peer = {"ghost": GHOST, "reason": None}
        self.abort_peer = False

    def handle(self, route, request):
        url = urlparse(request.url)
        cors = {"access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "*"}
        if request.method == "OPTIONS":
            return route.fulfill(status=204, headers=cors)
        body = request.post_data_json if request.post_data else None
        self.calls.append({"method": request.method, "path": url.path, "query": parse_qs(url.query), "body": body,
                           "auth": request.headers.get("authorization")})
        override = self.status.get((request.method, url.path))
        if request.method == "GET" and url.path.endswith("/peer") and self.abort_peer:
            return route.abort()
        if override is not None:
            return route.fulfill(status=override, headers=cors, content_type="application/json", body="{}")
        if url.path == "/users/me":
            return route.fulfill(status=200, headers=cors, content_type="application/json", body=json.dumps({"username": self.user}))
        if url.path == "/ghosts" and request.method == "POST":
            return route.fulfill(status=200, headers=cors, content_type="application/json", body=json.dumps({"accepted": True, "seasons": 8, "era": 2}))
        if request.method == "DELETE":
            return route.fulfill(status=200, headers=cors, content_type="application/json", body=json.dumps({"removed": 1}))
        if url.path.endswith("/peer"):
            return route.fulfill(status=200, headers=cors, content_type="application/json", body=json.dumps(self.peer))
        if url.path == "/ghosts/report":
            return route.fulfill(status=200, headers=cors, content_type="application/json", body=json.dumps({"reported": True, "counted": True}))
        return route.fulfill(status=404, headers=cors, content_type="application/json", body="{}")

    def to(self, method, path_prefix):
        return [c for c in self.calls if c["method"] == method and c["path"].startswith(path_prefix)]

    def writes(self):
        return [c for c in self.calls if c["method"] in ("POST", "PUT", "DELETE")]


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception as exc:
            pytest.skip(f"Chromium unavailable: {exc}")
        yield b
        b.close()


def open_page(browser, api, signed_in=True, store=None):
    context = browser.new_context(viewport={"width": 900, "height": 700})
    page = context.new_page()

    def serve(route, request):
        url = request.url[len(ORIGIN):].split("?")[0]
        if url == "/t.html":
            return route.fulfill(status=200, content_type="text/html", body=PAGE)
        file = ROOT / url.lstrip("/")
        if file.is_file():
            return route.fulfill(status=200, content_type=mimetypes.guess_type(file.name)[0] or "text/plain", body=file.read_bytes())
        return route.fulfill(status=404, body="")

    page.route("**/*", lambda route, request: route.abort())
    page.route(f"{ORIGIN}/**", serve)
    page.route(f"{API}/**", api.handle)
    seed = dict(store or {})
    if signed_in:
        seed["hub_bearer_token"] = "test-token"
    page.add_init_script(f"for (const [k, v] of Object.entries({json.dumps(seed)})) localStorage.setItem(k, v);")
    page.goto(f"{ORIGIN}/t.html")
    page.wait_for_timeout(250)
    return context, page


def tick(page):
    page.locator("#peer-publish-checkbox").check()
    page.wait_for_timeout(350)


def state(page):
    return page.evaluate("() => JSON.parse(localStorage.getItem('continuum-peer-publish') || 'null')")


# ---------------------------------------------------------------- the Settings switch

def test_nothing_is_sent_on_load_even_when_signed_in(browser):
    api = Api()
    context, page = open_page(browser, api)
    page.wait_for_timeout(200)
    assert api.calls == []
    assert page.locator("#peer-publish-checkbox").is_checked() is False
    assert page.locator("#peer-publish-checkbox").is_enabled()
    context.close()


def test_signed_out_the_switch_is_locked_and_says_why(browser):
    api = Api()
    context, page = open_page(browser, api, signed_in=False)
    assert page.locator("#peer-publish-checkbox").is_disabled()
    assert "Sign in" in page.locator("#peer-publish-note").inner_text()
    assert api.calls == []
    context.close()


def test_ticking_the_switch_checks_the_account_then_sends_exactly_the_python_payload(browser):
    api = Api()
    context, page = open_page(browser, api)
    page.evaluate("(p) => { window.PLAN = p; }", PLAN)
    tick(page)
    assert [c["path"] for c in api.calls] == ["/users/me", "/ghosts"]
    post = api.to("POST", "/ghosts")[0]
    assert post["body"] == json.loads(PLAN) and post["auth"] == "Bearer test-token"
    assert post["body"]["opt_in"] is True
    assert "Shared 8 seasons" in page.locator("#peer-publish-note").inner_text()
    assert state(page)["on"] is True and state(page)["user"] == "alice"
    context.close()


def test_ticking_with_too_few_seasons_sends_nothing_yet_but_stays_on(browser):
    api = Api()
    context, page = open_page(browser, api)
    tick(page)                                   # PLAN is "" : not enough seasons yet
    assert api.to("POST", "/ghosts") == []
    assert state(page)["on"] is True
    assert "few seasons" in page.locator("#peer-publish-note").inner_text()
    # a later season finishes and a plan is now ready: the hook sends it
    page.evaluate("(p) => { window.PLAN = p; }", PLAN)
    page.evaluate("() => window.ContinuumPeers.seasonDone()")
    page.wait_for_timeout(300)
    assert len(api.to("POST", "/ghosts")) == 1
    context.close()


def test_the_season_hook_does_nothing_while_sharing_is_off(browser):
    api = Api()
    context, page = open_page(browser, api)
    page.evaluate("(p) => { window.PLAN = p; }", PLAN)
    page.evaluate("() => window.ContinuumPeers.seasonDone()")
    page.wait_for_timeout(200)
    assert api.calls == []
    context.close()


def test_the_hook_passes_the_last_sent_season_so_python_can_decide(browser):
    api = Api()
    context, page = open_page(browser, api)
    page.evaluate("(p) => { window.PLAN = p; }", PLAN)
    tick(page)
    page.evaluate("() => { window.pyCalls.length = 0; window.PLAN = ''; window.ContinuumPeers.seasonDone(); }")
    page.wait_for_timeout(200)
    plans = page.evaluate("() => window.pyCalls.filter((c) => c[0] === 'plan')")
    assert plans == [["plan", 8, 2]]
    assert len(api.to("POST", "/ghosts")) == 1       # nothing due, nothing resent
    context.close()


def test_unticking_deletes_what_was_shared(browser):
    api = Api()
    context, page = open_page(browser, api)
    page.evaluate("(p) => { window.PLAN = p; }", PLAN)
    tick(page)
    page.locator("#peer-publish-checkbox").uncheck()
    page.wait_for_timeout(350)
    assert len(api.to("DELETE", "/ghosts/continuum")) == 1
    assert "removed" in page.locator("#peer-publish-note").inner_text()
    assert state(page)["on"] is False and state(page)["pendingDelete"] is False
    page.evaluate("() => window.ContinuumPeers.seasonDone()")
    page.wait_for_timeout(200)
    assert len(api.to("POST", "/ghosts")) == 1       # no more sends once it is off
    context.close()


def test_a_failed_removal_is_remembered_and_retried_at_the_next_load(browser):
    api = Api()
    api.status[("DELETE", "/ghosts/continuum")] = 500
    context, page = open_page(browser, api, store={"continuum-peer-publish": json.dumps({"on": True, "user": "alice", "pendingDelete": False})})
    page.locator("#peer-publish-checkbox").uncheck()
    page.wait_for_timeout(350)
    assert state(page)["pendingDelete"] is True
    assert "could not reach the server" in page.locator("#peer-publish-note").inner_text().lower()
    context.close()
    api2 = Api()
    context, page = open_page(browser, api2, store={"continuum-peer-publish": json.dumps({"on": False, "user": "alice", "pendingDelete": True})})
    page.wait_for_timeout(300)
    assert len(api2.to("DELETE", "/ghosts/continuum")) == 1
    assert state(page)["pendingDelete"] is False
    context.close()


def test_a_pending_removal_is_never_run_by_a_different_account(browser):
    api = Api()
    api.user = "mallory"
    context, page = open_page(browser, api, store={"continuum-peer-publish": json.dumps({"on": False, "user": "alice", "pendingDelete": True})})
    page.wait_for_timeout(300)
    assert api.to("DELETE", "/ghosts") == []
    context.close()


def test_a_different_account_turns_the_switch_off_without_sending(browser):
    api = Api()
    api.user = "bob"
    context, page = open_page(browser, api, store={"continuum-peer-publish": json.dumps({"on": True, "user": "alice", "pendingDelete": False})})
    page.wait_for_timeout(300)
    assert state(page)["on"] is False
    assert page.locator("#peer-publish-checkbox").is_checked() is False
    assert "different account" in page.locator("#peer-publish-note").inner_text()
    page.evaluate("(p) => { window.PLAN = p; }", PLAN)
    page.evaluate("() => window.ContinuumPeers.seasonDone()")
    page.wait_for_timeout(200)
    assert api.writes() == []
    context.close()


def test_a_refused_publish_switches_sharing_off_but_a_busy_server_does_not(browser):
    api = Api()
    api.status[("POST", "/ghosts")] = 422
    context, page = open_page(browser, api)
    page.evaluate("(p) => { window.PLAN = p; }", PLAN)
    tick(page)
    assert state(page)["on"] is False and page.locator("#peer-publish-checkbox").is_checked() is False
    context.close()
    api = Api()
    api.status[("POST", "/ghosts")] = 429
    context, page = open_page(browser, api)
    page.evaluate("(p) => { window.PLAN = p; }", PLAN)
    tick(page)
    assert state(page)["on"] is True
    assert "try again" in page.locator("#peer-publish-note").inner_text()
    context.close()


def test_an_unreachable_account_check_leaves_the_switch_off(browser):
    api = Api()
    api.status[("GET", "/users/me")] = 500
    context, page = open_page(browser, api)
    tick(page)
    assert page.locator("#peer-publish-checkbox").is_checked() is False
    assert api.writes() == []
    assert not state(page) or state(page).get("on") is not True
    context.close()


# ---------------------------------------------------------------- looking at another settlement

def test_show_asks_for_the_players_band_and_hands_the_ghost_to_python(browser):
    api = Api()
    context, page = open_page(browser, api, signed_in=False)
    page.locator("#peer-show-button").click()
    page.wait_for_timeout(350)
    get = api.to("GET", "/ghosts/continuum/peer")[0]
    assert get["query"] == {"scenario": ["standard"], "era": ["2"], "hard": ["false"]}
    assert get["auth"] is None
    shown = page.evaluate("() => window.pyCalls.filter((c) => c[0] === 'show')")
    assert json.loads(shown[0][1]) == GHOST
    assert page.locator("#peer-status").inner_text() == "MSG:shown"
    assert page.locator("#peer-report-button").is_enabled()
    assert api.writes() == []                          # looking writes nothing
    context.close()


def test_show_another_excludes_the_one_on_screen(browser):
    api = Api()
    context, page = open_page(browser, api)
    page.locator("#peer-show-button").click()
    page.wait_for_timeout(300)
    page.locator("#peer-show-button").click()
    page.wait_for_timeout(300)
    second = api.to("GET", "/ghosts/continuum/peer")[1]
    assert second["query"]["exclude"] == [GHOST["id"]]
    assert second["auth"] == "Bearer test-token"       # so the server can leave out your own
    context.close()


@pytest.mark.parametrize("reason", ["too_few", "no_match"])
def test_an_empty_answer_shows_the_plain_reason(browser, reason):
    api = Api()
    api.peer = {"ghost": None, "reason": reason}
    context, page = open_page(browser, api)
    page.locator("#peer-show-button").click()
    page.wait_for_timeout(300)
    assert page.locator("#peer-status").inner_text() == f"MSG:{reason}"
    assert page.evaluate("() => window.pyCalls.filter((c) => c[0] === 'show').length") == 0
    assert page.locator("#peer-report-button").is_hidden()
    context.close()


@pytest.mark.parametrize("mode", ["server_error", "not_found", "no_content", "offline"])
def test_every_failure_fails_soft_with_the_unavailable_message(browser, mode):
    api = Api()
    if mode == "server_error":
        api.status[("GET", "/ghosts/continuum/peer")] = 500
    elif mode == "not_found":
        api.status[("GET", "/ghosts/continuum/peer")] = 404
    elif mode == "no_content":
        api.status[("GET", "/ghosts/continuum/peer")] = 204
    else:
        api.abort_peer = True
    context, page = open_page(browser, api)
    page.locator("#peer-show-button").click()
    page.wait_for_timeout(350)
    assert page.locator("#peer-status").inner_text() == "MSG:unavailable"
    assert page.locator("#peer-show-button").is_enabled()          # can simply try again
    assert page.evaluate("() => window.pyCalls.filter((c) => c[0] === 'show').length") == 0
    context.close()


def test_a_ghost_python_refuses_is_reported_as_unavailable(browser):
    api = Api()
    context, page = open_page(browser, api)
    page.evaluate("() => { window.SHOW_OK = false; }")
    page.locator("#peer-show-button").click()
    page.wait_for_timeout(300)
    assert page.locator("#peer-status").inner_text() == "MSG:unavailable"
    context.close()


def test_report_sends_only_the_game_the_id_and_a_fixed_reason(browser):
    api = Api()
    context, page = open_page(browser, api)
    page.locator("#peer-show-button").click()
    page.wait_for_timeout(300)
    page.evaluate("() => { document.getElementById('peer-report-button').hidden = false; }")
    page.locator("#peer-report-button").click()
    page.wait_for_timeout(300)
    body = api.to("POST", "/ghosts/report")[0]["body"]
    assert body == {"game": "continuum", "ghost_id": GHOST["id"], "reason": "implausible"}
    assert api.to("POST", "/ghosts/report")[0]["auth"] is None       # the reporter is not identified
    assert page.locator("#peer-report-button").is_disabled()
    assert "Reported" in page.locator("#peer-report-button").inner_text()
    context.close()


def test_a_failed_report_can_be_tried_again(browser):
    api = Api()
    api.status[("POST", "/ghosts/report")] = 500
    context, page = open_page(browser, api)
    page.locator("#peer-show-button").click()
    page.wait_for_timeout(300)
    page.evaluate("() => { document.getElementById('peer-report-button').hidden = false; }")
    page.locator("#peer-report-button").click()
    page.wait_for_timeout(300)
    assert page.locator("#peer-report-button").is_enabled()
    assert "Could not send the report" in page.locator("#peer-status").inner_text()
    context.close()
