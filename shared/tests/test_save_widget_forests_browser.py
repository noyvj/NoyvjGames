"""B-15: named local profiles ("forests") in shared/save-widget.js.

A game opts in with window.NoyvjSaveProfiles. Not signed in, the player keeps up to three named profiles, each
owning an anonymous save code and the localStorage keys the game lists; the active one's code stays in
savecode:<slug>. Signed-in players keep the account slots and see no menu. A page that does not opt in is
unchanged.

Real scripts in headless Chromium against the conftest harness. The save endpoints are answered by an in-memory
backend defined here, so nothing reaches the live API."""

import json
import re

from conftest import API, ORIGIN, page_html

SLUG = "demo"
PREF = "demo_pref_v1"

HOOK = """
window.NoyvjSaveProfiles = {
  noun: "forest", defaultName: "My forest", gameKeys: ["%(pref)s"%(extra_keys)s],
  startNew() { window.__calls.push("startNew"); if (window.__failStart) throw new Error("boom"); window.__game = { coins: 0, diff: "normal" }; },
  afterSwitch(info) { window.__calls.push("afterSwitch:" + info.name + ":" + info.isNew); },
};
"""

GAME = """
window.__calls = [];
window.__game = { coins: 0, diff: "normal" };
window.pyodide = { toPy: (x) => x, globals: { get(name) {
  if (name === "get_state") return () => ({ toJs: () => JSON.parse(JSON.stringify(window.__game)), destroy() {} });
  if (name === "load_state") return (d) => { window.__calls.push("load"); window.__game = JSON.parse(JSON.stringify(d)); };
  return undefined; } } };
"""


class Backend:
    """The anonymous save endpoints (POST /saves, PUT/GET /saves/{code}) in memory."""

    def __init__(self):
        self.saves = {}
        self.log = []
        self.fail_writes = False
        self.fail_reads = False
        self.missing = set()
        self._n = 0

    def handle(self, route, request):
        headers = {"access-control-allow-origin": "*", "access-control-allow-headers": "*",
                   "access-control-allow-methods": "GET,POST,PUT,DELETE", "cache-control": "no-store"}
        path = request.url[len(API):].split("?")[0]
        if request.method == "OPTIONS":
            return route.fulfill(status=204, headers=headers)
        self.log.append((request.method, path))

        def send(status, body):
            route.fulfill(status=status, headers=dict(headers, **{"content-type": "application/json"}), body=json.dumps(body))

        if path == "/users/me/saves" and request.method == "GET":
            return send(200, [])
        if path == "/saves" and request.method == "POST":
            if self.fail_writes:
                return send(500, {"detail": "down"})
            self._n += 1
            code = f"AAAA-{self._n:04d}"
            self.saves[code] = json.loads(request.post_data)["save_data"]
            return send(200, {"save_code": code, "game_id": SLUG, "save_data": self.saves[code]})
        m = re.fullmatch(r"/saves/([A-Z0-9-]+)", path)
        if m:
            code = m.group(1)
            if request.method == "PUT":
                if self.fail_writes:
                    return send(500, {"detail": "down"})
                self.saves[code] = json.loads(request.post_data)["save_data"]
                return send(200, {"save_code": code, "game_id": SLUG, "save_data": self.saves[code]})
            if request.method == "GET":
                if code in self.missing or code not in self.saves:
                    return send(404, {"detail": "Save code not found"})
                if self.fail_reads:
                    return send(500, {"detail": "down"})
                return send(200, {"save_code": code, "game_id": SLUG, "save_data": self.saves[code]})
        return send(404, {"detail": "unmocked " + path})

    def writes(self):
        return [(m, p) for m, p in self.log if m in ("POST", "PUT")]


def open_game(harness, backend, store=None, signed_in=False, hook=True, extra_keys="", size=(1440, 900), init=()):
    scripts = list(init)
    seed = dict(store or {})
    if signed_in:
        seed["hub_bearer_token"] = "tok"
        seed["hub_account_username"] = "sam"
    if seed:
        scripts.append("if (!localStorage.getItem('__seeded')) { localStorage.setItem('__seeded', '1'); "
                       f"Object.entries({json.dumps(seed)}).forEach(([k, v]) => localStorage.setItem(k, v)); }}")
    h = harness(init_scripts=scripts, size=size)
    h.context.route(API + "/**", backend.handle)
    hook_js = HOOK % {"pref": PREF, "extra_keys": extra_keys} if hook else ""
    h.pages["/t.html"] = page_html(
        f"<script>{GAME}{hook_js}</script>",
        '<div id="game">Game</div><script src="/shared/confirm-dialog.js"></script>'
        '<script src="/shared/hub-auth.js"></script>'
        f'<script src="/shared/save-widget.js" data-game-id="{SLUG}"></script>')
    h.goto("/t.html")
    h.page.wait_for_selector("#save-widget", state="attached")
    # the game "ran" for a moment: the widget's baseline is the booted state, later states count as played
    h.page.wait_for_timeout(150)
    return h


def open_menu(h):
    h.page.evaluate("document.getElementById('save-widget').classList.remove('collapsed')")
    if h.page.get_attribute("[data-testid=save-widget-forests-toggle]", "aria-expanded") != "true":
        h.page.click("[data-testid=save-widget-forests-toggle]")


def forests(h):
    return h.page.evaluate("NoyvjSaveWidget.forests()")


def play(h, coins, diff="normal"):
    h.page.evaluate(f"window.__game = {{ coins: {coins}, diff: {json.dumps(diff)} }}")


def game(h):
    return h.page.evaluate("window.__game")


def ls(h, key):
    return h.page.evaluate("(k) => localStorage.getItem(k)", key)


def ask_open(h):
    return h.page.evaluate("!document.getElementById('confirm-dialog-overlay').hidden") if h.page.query_selector("#confirm-dialog-overlay") else False


def confirm(h):
    h.page.wait_for_selector("#confirm-dialog-overlay:not([hidden])")
    h.page.click("[data-testid=confirm-dialog-confirm]")


def create(h, name):
    open_menu(h)
    h.page.click("[data-testid=save-widget-forest-new]")
    h.page.fill("[data-testid=save-widget-forest-name]", name)
    h.page.click("[data-testid=save-widget-forest-ok]")


def in_forest(h, name):
    """Waits until the menu's toggle says the named forest is the open one."""
    h.page.wait_for_function("(n) => document.querySelector('.save-widget-forests-toggle-text').textContent.includes(n)", arg=name, timeout=20000)


def live_text(h):
    return h.page.inner_text("[data-testid=save-widget-forest-live]")


def names(h):
    return h.page.evaluate("[...document.querySelectorAll('.save-widget-forest-name')].map(e => e.textContent)")


# ---- opt-in, signed-in and migration -------------------------------------------------------------------------

def test_a_page_without_the_hook_has_no_menu_and_stores_nothing(harness):
    h = open_game(harness, Backend(), hook=False, store={"savecode:demo": "OLD1-0001"})
    assert h.page.is_hidden("[data-testid=save-widget-forests]")
    assert forests(h) is None
    assert ls(h, "forests:demo") is None
    assert h.errors == []


def test_signed_in_players_keep_account_slots_and_see_no_menu(harness):
    h = open_game(harness, Backend(), signed_in=True)
    h.page.wait_for_selector("[data-testid=save-widget-slots]:not([hidden])", state="attached")
    assert h.page.is_hidden("[data-testid=save-widget-forests]")
    assert forests(h) is None
    assert ls(h, "forests:demo") is None


def test_migration_the_first_forest_adopts_the_existing_code_and_settings(harness):
    h = open_game(harness, Backend(), store={"savecode:demo": "OLD1-0001", PREF: "mangrove"})
    open_menu(h)
    assert names(h) == ["My forest (current)"]
    assert ls(h, "savecode:demo") == "OLD1-0001" and ls(h, PREF) == "mangrove"   # nothing moved or lost
    assert forests(h) == {"active": "f1", "list": [{"id": "f1", "name": "My forest", "hasSave": True}]}
    assert json.loads(ls(h, "forests:demo"))["list"][0]["name"] == "My forest"
    assert h.page.inner_text("[data-testid=save-widget-code]") == "Code: OLD1-0001"


def test_migration_on_a_browser_with_no_save_at_all(harness):
    backend = Backend()
    h = open_game(harness, backend)
    open_menu(h)
    assert names(h) == ["My forest (current)"]
    assert forests(h) == {"active": "f1", "list": [{"id": "f1", "name": "My forest", "hasSave": False}]}
    assert ls(h, "savecode:demo") is None and ls(h, PREF) is None
    assert backend.log == [] and h.errors == []
    # and the first Save still works and the code stays the (only) forest's
    play(h, 5)
    h.page.click("[data-testid=save-widget-save]")
    h.page.wait_for_function("document.querySelector('[data-testid=save-widget-save]').textContent === 'Save Progress'")
    assert ls(h, "savecode:demo") == "AAAA-0001"
    assert forests(h)["list"][0]["hasSave"] is True


def test_a_corrupt_store_falls_back_to_the_default_and_clamps_names(harness):
    h = open_game(harness, Backend(), store={"forests:demo": "{not json", "savecode:demo": "OLD1-0001"})
    assert forests(h) == {"active": "f1", "list": [{"id": "f1", "name": "My forest", "hasSave": True}]}
    bad = {"v": 1, "active": "zzz", "list": [
        {"id": "a1", "name": "x" * 60, "code": "AAAA-0001"},
        {"id": "a1", "name": "duplicate id", "code": None},
        {"id": "<b>", "name": "bad id"},
        {"id": "b2", "name": "  ​\u0007 ", "code": "not a code!!", "keys": {PREF: "ok", "hub_bearer_token": "stolen", "other": "x"}},
    ]}
    h2 = open_game(harness, Backend(), store={"forests:demo": json.dumps(bad)})
    f = h2.page.evaluate("NoyvjSaveWidget.forests()")
    assert f["active"] == "a1" and [x["name"] for x in f["list"]] == ["x" * 24, "Forest 2"]
    assert h2.errors == []


def test_blocked_storage_hides_the_menu(harness):
    h = open_game(harness, Backend(), init=["Storage.prototype.setItem = function () { throw new Error('blocked'); };"])
    assert h.page.is_hidden("[data-testid=save-widget-forests]")
    assert forests(h) is None


# ---- creating and switching ------------------------------------------------------------------------------------

def test_new_forest_saves_the_current_one_first_then_starts_fresh_and_you_can_come_back(harness):
    backend = Backend()
    h = open_game(harness, backend, store={PREF: "mangrove"})
    play(h, 40, "ranger")
    create(h, "Ranger practice")
    confirm(h)                                   # "Start the new forest ... Your progress in My forest is saved first"
    in_forest(h, "Ranger practice")
    assert backend.writes() == [("POST", "/saves")]                       # the first forest was saved...
    assert backend.saves["AAAA-0001"] == {"coins": 40, "diff": "ranger"}
    assert game(h) == {"coins": 0, "diff": "normal"}                      # ...then the new one started fresh
    assert ls(h, "savecode:demo") is None and ls(h, PREF) is None         # own code, own settings (none yet)
    assert h.page.evaluate("window.__calls") == ["startNew", "afterSwitch:Ranger practice:true"]
    f = forests(h)
    assert f["active"] != "f1" and [x["name"] for x in f["list"]] == ["My forest", "Ranger practice"]
    assert "Started the new forest" in live_text(h)
    # play the new one, then go back
    play(h, 7, "wildfire")
    h.page.evaluate("localStorage.setItem('%s', 'standard')" % PREF)
    h.page.click("[data-testid=save-widget-forest-1-open]")
    confirm(h)
    in_forest(h, "My forest")
    assert game(h) == {"coins": 40, "diff": "ranger"}                    # the first forest, with its own difficulty
    assert ls(h, "savecode:demo") == "AAAA-0001" and ls(h, PREF) == "mangrove"
    assert backend.saves["AAAA-0002"] == {"coins": 7, "diff": "wildfire"}
    assert "Opened" in live_text(h)
    # and forth again: the second forest comes back with its own settings
    h.page.click("[data-testid=save-widget-forest-2-open]")      # nothing was changed since opening My forest: no question
    in_forest(h, "Ranger practice")
    assert not ask_open(h)
    assert game(h) == {"coins": 7, "diff": "wildfire"}
    assert ls(h, "savecode:demo") == "AAAA-0002" and ls(h, PREF) == "standard"


def test_the_saved_line_and_code_follow_the_forest(harness):
    backend = Backend()
    h = open_game(harness, backend)
    play(h, 3)
    open_menu(h)
    h.page.click("[data-testid=save-widget-save]")
    h.page.wait_for_function("document.querySelector('[data-testid=save-widget-save]').textContent === 'Save Progress'")
    assert "Saved" in h.page.inner_text("[data-testid=save-widget-saved-line]")
    create(h, "Second")                           # nothing changed since the save: no confirm, no extra write
    in_forest(h, "Second")
    assert not ask_open(h)
    assert backend.writes() == [("POST", "/saves")]
    assert h.page.inner_text("[data-testid=save-widget-saved-line]") == "Not saved yet"
    assert h.page.is_hidden("[data-testid=save-widget-code]")


def test_switching_with_no_unsaved_changes_asks_nothing_and_writes_nothing(harness):
    backend = Backend()
    backend.saves["AAAA-0009"] = {"coins": 12, "diff": "normal"}
    store = {"forests:demo": json.dumps({"v": 1, "active": "a", "list": [
        {"id": "a", "name": "One", "code": "AAAA-0001", "keys": {}}, {"id": "b", "name": "Two", "code": "AAAA-0009", "keys": {PREF: "x"}}]})}
    h = open_game(harness, backend, store=store)
    open_menu(h)
    h.page.click("[data-testid=save-widget-forest-2-open]")                # the booted state is the baseline: nothing to lose
    in_forest(h, "Two")
    assert not ask_open(h)
    assert backend.writes() == []
    assert game(h) == {"coins": 12, "diff": "normal"} and ls(h, PREF) == "x" and ls(h, "savecode:demo") == "AAAA-0009"


def test_cancelling_the_confirm_changes_nothing(harness):
    backend = Backend()
    h = open_game(harness, backend)
    play(h, 9)
    create(h, "Other")
    h.page.wait_for_selector("#confirm-dialog-overlay:not([hidden])")
    assert "saved first" in h.page.inner_text("[data-testid=confirm-dialog-message]")
    h.page.click("[data-testid=confirm-dialog-cancel]")
    h.page.wait_for_timeout(200)
    assert backend.log == [] and game(h)["coins"] == 9
    assert forests(h)["list"] == [{"id": "f1", "name": "My forest", "hasSave": False}]
    assert h.page.is_enabled("[data-testid=save-widget-forest-new]")


def test_a_failed_save_stops_the_switch_and_switch_anyway_keeps_a_snapshot(harness):
    backend = Backend()
    backend.fail_writes = True
    h = open_game(harness, backend)
    play(h, 21)
    create(h, "Other")
    confirm(h)                                                              # "saved first"
    h.page.wait_for_function("document.querySelector('[data-testid=confirm-dialog-message]').textContent.includes('anything since its last save is lost')", timeout=20000)
    assert game(h)["coins"] == 21 and len(forests(h)["list"]) == 1          # nothing switched yet
    assert "Couldn't save" in live_text(h)
    h.page.click("[data-testid=confirm-dialog-cancel]")
    h.page.wait_for_timeout(200)
    assert game(h)["coins"] == 21 and len(forests(h)["list"]) == 1 and h.page.is_enabled("[data-testid=save-widget-forest-new]")
    # try again and choose to switch anyway
    h.page.click("[data-testid=save-widget-forest-new]")
    h.page.fill("[data-testid=save-widget-forest-name]", "Other")
    h.page.click("[data-testid=save-widget-forest-ok]")
    h.page.wait_for_selector("#confirm-dialog-overlay:not([hidden])")
    h.page.click("[data-testid=confirm-dialog-confirm]")
    h.page.wait_for_function("document.querySelector('[data-testid=confirm-dialog-message]').textContent.includes('anything since')", timeout=20000)
    h.page.click("[data-testid=confirm-dialog-confirm]")
    in_forest(h, "Other")
    assert game(h)["coins"] == 0
    snaps = h.page.evaluate("NoyvjSaveWidget.localSnapshots()")
    assert snaps and snaps[0]["reason"] == "forest-switch"                   # the 21 coins are in "Restore an earlier state"


def test_a_forest_that_cannot_be_opened_leaves_everything_as_it_was(harness):
    backend = Backend()
    store = {"forests:demo": json.dumps({"v": 1, "active": "a", "list": [
        {"id": "a", "name": "One", "code": None, "keys": {}}, {"id": "b", "name": "Two", "code": "AAAA-0009", "keys": {PREF: "x"}}]}), PREF: "mine"}
    h = open_game(harness, backend, store=store)
    open_menu(h)
    h.page.click("[data-testid=save-widget-forest-2-open]")                  # the server has never heard of AAAA-0009
    h.page.wait_for_function("document.querySelector('[data-testid=save-widget-forest-live]').textContent.includes('wasn')")
    assert "still in" in live_text(h)
    assert ls(h, PREF) == "mine" and ls(h, "savecode:demo") is None
    assert forests(h)["active"] == "a" and h.page.is_enabled("[data-testid=save-widget-forest-new]")
    # an offline failure reads differently and also changes nothing
    backend.saves["AAAA-0009"] = {"coins": 1, "diff": "normal"}
    backend.fail_reads = True
    h.page.click("[data-testid=save-widget-forest-2-open]")
    h.page.wait_for_function("document.querySelector('[data-testid=save-widget-forest-live]').textContent.includes('Couldn')", timeout=20000)
    assert forests(h)["active"] == "a" and ls(h, PREF) == "mine"


def test_a_failing_start_puts_the_old_forest_back(harness):
    backend = Backend()
    h = open_game(harness, backend, store={PREF: "mine"})
    play(h, 30, "ranger")
    h.page.evaluate("window.__failStart = true")
    create(h, "Broken")
    confirm(h)
    h.page.wait_for_function("document.querySelector('[data-testid=save-widget-forest-live]').textContent.includes('back in')", timeout=20000)
    assert game(h) == {"coins": 30, "diff": "ranger"}
    assert [x["name"] for x in forests(h)["list"]] == ["My forest"] and forests(h)["active"] == "f1"
    assert ls(h, PREF) == "mine" and ls(h, "savecode:demo") == "AAAA-0001"


# ---- the three-forest limit, names, delete ----------------------------------------------------------------------

def test_at_most_three_forests_and_the_new_button_says_why(harness):
    h = open_game(harness, Backend())
    for name in ("Two", "Three"):
        create(h, name)
        in_forest(h, name)
        if ask_open(h):
            confirm(h)
    open_menu(h)
    assert len(forests(h)["list"]) == 3
    assert h.page.is_disabled("[data-testid=save-widget-forest-new]")
    assert "the most this browser keeps" in h.page.inner_text("[data-testid=save-widget-forest-note]")


def test_names_are_checked_and_shown_as_plain_text(harness):
    h = open_game(harness, Backend())
    open_menu(h)
    h.page.click("[data-testid=save-widget-forest-new]")
    for bad, message in (("   ", "1 to 24"), ("my FOREST", "already have"), ("x" * 25, None)):
        h.page.evaluate("(v) => { const i = document.querySelector('[data-testid=save-widget-forest-name]'); i.removeAttribute('maxlength'); i.value = v; }", bad)
        h.page.click("[data-testid=save-widget-forest-ok]")
        if message:
            assert message in h.page.inner_text("[data-testid=save-widget-forest-error]")
        else:
            assert "24" in h.page.inner_text("[data-testid=save-widget-forest-error]")
    assert len(forests(h)["list"]) == 1
    # a name with markup is just text
    h.page.fill("[data-testid=save-widget-forest-name]", "<b>x</b><img src=x>")
    h.page.click("[data-testid=save-widget-forest-ok]")
    in_forest(h, "<b>")
    assert h.page.query_selector("#save-widget .save-widget-forest b, #save-widget .save-widget-forest img, #save-widget .save-widget-forests-toggle b") is None
    assert "<b>x</b><img src=x>" in names(h)[1]


def test_rename_keeps_the_save_and_checks_duplicates(harness):
    backend = Backend()
    h = open_game(harness, backend, store={"savecode:demo": "OLD1-0001"})
    open_menu(h)
    h.page.click("[data-testid=save-widget-forest-1-rename]")
    assert h.page.input_value("[data-testid=save-widget-forest-name]") == "My forest"
    h.page.fill("[data-testid=save-widget-forest-name]", "  Ranger   practice ")
    h.page.press("[data-testid=save-widget-forest-name]", "Enter")             # keyboard: Enter submits
    in_forest(h, "Ranger practice")
    assert ls(h, "savecode:demo") == "OLD1-0001" and backend.log == []
    assert "Renamed" in live_text(h)
    assert h.page.evaluate("document.activeElement.dataset.testid") == "save-widget-forest-new"


def test_escape_closes_the_name_box_and_returns_focus(harness):
    h = open_game(harness, Backend())
    open_menu(h)
    h.page.click("[data-testid=save-widget-forest-new]")
    assert h.page.evaluate("document.activeElement.dataset.testid") == "save-widget-forest-name"
    h.page.press("[data-testid=save-widget-forest-name]", "Escape")
    assert h.page.is_hidden("[data-testid=save-widget-forest-editor]")
    assert h.page.evaluate("document.activeElement.dataset.testid") == "save-widget-forest-new"
    assert len(forests(h)["list"]) == 1


def test_delete_asks_forgets_only_the_browsers_copy_and_never_the_last_or_current_one(harness):
    backend = Backend()
    store = {"forests:demo": json.dumps({"v": 1, "active": "a", "list": [
        {"id": "a", "name": "One", "code": None, "keys": {}}, {"id": "b", "name": "Two", "code": "AAAA-0009", "keys": {}}]})}
    h = open_game(harness, backend, store=store)
    open_menu(h)
    assert h.page.query_selector("[data-testid=save-widget-forest-1-delete]") is None      # the one you are in
    h.page.click("[data-testid=save-widget-forest-2-delete]")
    h.page.wait_for_selector("#confirm-dialog-overlay:not([hidden])")
    message = h.page.inner_text("[data-testid=confirm-dialog-message]")
    assert "AAAA-0009" in message and "not erased" in message                              # the code is named
    h.page.click("[data-testid=confirm-dialog-cancel]")
    assert len(forests(h)["list"]) == 2
    h.page.click("[data-testid=save-widget-forest-2-delete]")
    confirm(h)
    h.page.wait_for_function("document.querySelectorAll('.save-widget-forest').length === 1")
    assert backend.log == [] and "Deleted" in live_text(h)                                   # nothing was sent anywhere
    assert h.page.query_selector("[data-testid=save-widget-forest-1-delete]") is None      # now the last one: no delete at all


# ---- the settings keys a game lists ----------------------------------------------------------------------------

def test_only_plain_game_keys_are_carried_never_the_widgets_own_or_the_token(harness):
    h = open_game(harness, Backend(), extra_keys=', "hub_bearer_token", "savecode:demo", "forests:demo", "bad key!", "demo_other"',
                  store={PREF: "mine", "demo_other": "second", "hub_x": "nope"})
    play(h, 2)
    create(h, "Other")
    confirm(h)
    in_forest(h, "Other")
    stored = json.loads(ls(h, "forests:demo"))
    assert stored["list"][0]["keys"] == {PREF: "mine", "demo_other": "second"}   # the plain game keys, nothing of the widget's own
    assert ls(h, PREF) is None and ls(h, "demo_other") is None and ls(h, "hub_x") == "nope"


# ---- the Save button, accessibility and layout -----------------------------------------------------------------

def test_the_save_button_during_a_forest_still_saves_to_that_forests_code(harness):
    backend = Backend()
    h = open_game(harness, backend)
    play(h, 4)
    create(h, "Second")
    confirm(h)
    in_forest(h, "Second")
    play(h, 99)
    h.page.click("[data-testid=save-widget-save]")
    h.page.wait_for_function("document.querySelector('[data-testid=save-widget-save]').textContent === 'Save Progress'")
    assert ls(h, "savecode:demo") == "AAAA-0002" and backend.saves["AAAA-0002"]["coins"] == 99 and backend.saves["AAAA-0001"]["coins"] == 4


def test_menu_is_keyboard_reachable_with_44px_targets_and_a_polite_status(harness):
    h = open_game(harness, Backend(), size=(360, 740))
    open_menu(h)
    h.page.click("[data-testid=save-widget-forest-new]")
    sizes = h.page.evaluate("""() => [...document.querySelectorAll('.save-widget-forests button, .save-widget-forests input')]
      .filter((el) => el.offsetParent !== null).map((el) => [el.dataset.testid, Math.round(el.getBoundingClientRect().height)])""")
    assert sizes and all(height >= 44 for _, height in sizes), sizes
    live = h.page.get_attribute("[data-testid=save-widget-forest-live]", "aria-live")
    assert live == "polite" and h.page.get_attribute("[data-testid=save-widget-forest-live]", "role") == "status"
    assert h.page.get_attribute("[data-testid=save-widget-forests-toggle]", "aria-expanded") == "true"
    # keyboard: the toggle is a real button in the tab order
    assert h.page.evaluate("document.querySelector('[data-testid=save-widget-forests-toggle]').tabIndex") >= 0
    box = h.page.evaluate("(() => { const r = document.getElementById('save-widget').getBoundingClientRect(); return [r.left, r.right, innerWidth]; })()")
    assert box[0] >= 0 and box[1] <= box[2]
    h.page.keyboard.press("Escape")


def test_light_theme_buttons_are_light(harness):
    h = open_game(harness, Backend(), size=(360, 740))
    h.page.evaluate("document.documentElement.setAttribute('data-theme', 'light')")
    open_menu(h)
    bg = h.page.evaluate("getComputedStyle(document.querySelector('[data-testid=save-widget-forest-1-rename]')).backgroundImage")
    assert "219, 228, 251" in bg
    toggle_bg = h.page.evaluate("getComputedStyle(document.querySelector('[data-testid=save-widget-forests-toggle]')).backgroundImage")
    assert "219, 228, 251" in toggle_bg


def test_no_timers_were_added_for_the_menu(harness):
    # the menu reacts to clicks only: switching twice quickly while busy is ignored, not queued
    backend = Backend()
    h = open_game(harness, backend)
    play(h, 5)
    create(h, "Two")
    confirm(h)
    h.page.evaluate("document.querySelector('[data-testid=save-widget-forest-new]').click(); document.querySelector('[data-testid=save-widget-forest-new]').click()")
    in_forest(h, "Two")
    assert len(forests(h)["list"]) == 2
