"""shared/lite-mode.js + shared/lite-mode.css (Z-31) in headless Chromium: the attribute is set
before first paint, the storage key and automatic slow-device default behave, the toggles and API
work, the CSS removes animations/blur/background layers/large shadows, the account sync goes
through shared/site-settings.js, and Thaw's old lite mode now drives the same switch."""

import json

from conftest import ORIGIN, page_html

SLOW_DEVICE = "Object.defineProperty(navigator, 'deviceMemory', {value: 2, configurable: true});"
FEW_CORES = "Object.defineProperty(navigator, 'hardwareConcurrency', {value: 2, configurable: true});"
FAST_DEVICE = ("Object.defineProperty(navigator, 'deviceMemory', {value: 8, configurable: true});"
               "Object.defineProperty(navigator, 'hardwareConcurrency', {value: 8, configurable: true});")

HEAD = ('<link rel="stylesheet" href="/shared/lite-mode.css"><script src="/shared/lite-mode.js"></script>'
        "<style>.spin{animation:spin 5s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}"
        ".fade{transition:opacity 3s}.glass{backdrop-filter:blur(8px)}"
        ".card{box-shadow:0 20px 60px rgba(0,0,0,.6)}.ring{box-shadow:0 0 0 3px red}</style>")
BODY = ('<div class="space-bg"><div class="space-bg-nebula" style="filter:blur(60px)"></div></div>'
        '<div id="spin" class="spin">x</div><div id="fade" class="fade">y</div><div id="glass" class="glass">g</div>'
        '<div id="card" class="card">c</div><div id="ring" class="ring selected">r</div>'
        '<div id="panel" class="game-panel">p</div>'
        '<button id="t" data-lite-toggle>Lite</button><input id="c" type="checkbox" data-lite-toggle>'
        '<p id="s" data-lite-status></p>')


def open_lite(harness, init=(), **kwargs):
    h = harness(init_scripts=init, **kwargs)
    h.pages["/t.html"] = page_html(HEAD, BODY)
    h.goto()
    return h


def lite(page):
    return page.evaluate("document.documentElement.getAttribute('data-lite')")


def test_off_by_default_on_a_normal_device(harness):
    h = open_lite(harness, init=[FAST_DEVICE])
    assert lite(h.page) == "false"
    assert h.page.evaluate("NoyvjLite.on()") is False and h.page.evaluate("NoyvjLite.auto()") is False
    assert h.page.query_selector(".noyvj-lite-note") is None
    assert h.page.inner_text("#t") == "Lite mode: off" and h.page.get_attribute("#t", "aria-pressed") == "false"


def test_attribute_is_set_before_first_paint(harness):
    watcher = ("window.__lite = null; new MutationObserver(() => { if (window.__lite === null && "
               "document.documentElement.hasAttribute('data-lite')) window.__lite = {state: document.readyState, "
               "body: !!document.body, value: document.documentElement.getAttribute('data-lite')}; })"
               ".observe(document, {attributes: true, subtree: true, attributeFilter: ['data-lite']});")
    h = open_lite(harness, init=[watcher, "localStorage.setItem('lite-mode','true')"])
    seen = h.page.evaluate("window.__lite")
    assert seen == {"state": "loading", "body": False, "value": "true"}


def test_automatic_default_on_for_low_memory_with_a_visible_note(harness):
    h = open_lite(harness, init=[SLOW_DEVICE])
    assert lite(h.page) == "true"
    assert h.page.evaluate("NoyvjLite.on() && NoyvjLite.auto() && NoyvjLite.chosen() === null")
    note = h.page.query_selector(".noyvj-lite-note")
    assert note and note.is_visible()
    assert "memory" in note.inner_text() and "Turn it off" in note.inner_text()
    assert h.page.evaluate("localStorage.getItem('lite-mode')") is None, "an automatic default must not be stored as a choice"
    assert "slow" in h.page.inner_text("#s")


def test_automatic_default_on_for_two_cores(harness):
    h = open_lite(harness, init=[FEW_CORES])
    assert lite(h.page) == "true" and "2 processor cores" in h.page.inner_text(".noyvj-lite-note")


def test_turning_the_automatic_default_off_is_remembered_and_the_note_goes(harness):
    h = open_lite(harness, init=[SLOW_DEVICE])
    h.page.click(".noyvj-lite-note >> text=Turn it off")
    assert lite(h.page) == "false"
    assert h.page.query_selector(".noyvj-lite-note") is None
    assert h.page.evaluate("localStorage.getItem('lite-mode')") == "false"
    h.page.reload()
    assert lite(h.page) == "false" and h.page.query_selector(".noyvj-lite-note") is None


def test_keeping_the_automatic_default_stores_a_choice(harness):
    h = open_lite(harness, init=[SLOW_DEVICE])
    h.page.click(".noyvj-lite-note >> text=Keep it on")
    assert h.page.evaluate("localStorage.getItem('lite-mode')") == "true" and h.page.evaluate("NoyvjLite.auto()") is False
    h.page.reload()
    assert lite(h.page) == "true" and h.page.query_selector(".noyvj-lite-note") is None


def test_an_explicit_off_beats_the_slow_device_hint(harness):
    h = open_lite(harness, init=[SLOW_DEVICE, "localStorage.setItem('lite-mode','false')"])
    assert lite(h.page) == "false" and h.page.query_selector(".noyvj-lite-note") is None


def test_api_set_reset_event_and_listeners(harness):
    h = open_lite(harness, init=[FAST_DEVICE])
    out = h.page.evaluate("""() => {
      const seen = [], events = [];
      const off = NoyvjLite.onChange((on, detail) => seen.push([on, detail.fromSync]));
      document.addEventListener('noyvj-lite-change', (e) => events.push([e.detail.on, e.detail.auto, e.detail.fromSync]));
      NoyvjLite.set(true); NoyvjLite.set(true); NoyvjLite.set(false);
      off(); NoyvjLite.set(true);
      NoyvjLite.setFromSync(false);
      const stored = localStorage.getItem('lite-mode');
      NoyvjLite.reset();
      return {seen, events, stored, afterReset: [NoyvjLite.on(), NoyvjLite.chosen(), localStorage.getItem('lite-mode')]};
    }""")
    assert out["seen"] == [[True, False], [False, False]]      # no event for an unchanged set(true); unsubscribed after off()
    assert out["events"] == [[True, False, False], [False, False, False], [True, False, False], [False, False, True]]
    assert out["stored"] == "false" and out["afterReset"] == [False, None, None]


def test_toggles_follow_the_state_and_change_it(harness):
    h = open_lite(harness, init=[FAST_DEVICE])
    h.page.click("#t")
    assert lite(h.page) == "true" and h.page.inner_text("#t") == "Lite mode: on" and h.page.is_checked("#c")
    h.page.click("#c")
    assert lite(h.page) == "false" and h.page.inner_text("#t") == "Lite mode: off"
    assert h.page.evaluate("localStorage.getItem('lite-mode')") == "false"


def test_another_tab_changing_the_key_updates_this_page(harness):
    h = open_lite(harness, init=[FAST_DEVICE])
    second = h.context.new_page()
    second.goto(ORIGIN + "/t.html")
    second.evaluate("NoyvjLite.set(true)")
    h.page.wait_for_function("document.documentElement.getAttribute('data-lite') === 'true'")


def test_css_switches_off_cost_but_keeps_focus_rings_and_selected_state(harness):
    h = open_lite(harness, init=[FAST_DEVICE])
    cost = """() => {
      const cs = (id) => getComputedStyle(document.getElementById(id));
      return {spinDur: cs('spin').animationDuration, spinIter: cs('spin').animationIterationCount,
        fadeDur: cs('fade').transitionDuration, blur: cs('glass').backdropFilter,
        cardShadow: cs('card').boxShadow, ringShadow: cs('ring').boxShadow,
        nebula: getComputedStyle(document.querySelector('.space-bg-nebula')).display,
        panelShadow: cs('panel').boxShadow};
    }"""
    before = h.page.evaluate(cost)
    assert before["spinDur"] == "5s" and before["blur"] != "none" and "60px" in before["cardShadow"]
    assert before["nebula"] != "none"
    h.page.evaluate("NoyvjLite.set(true)")
    # a property change starts its (now 0.01 ms) transition, so give the next frame a chance to finish it
    h.page.wait_for_function("getComputedStyle(document.getElementById('glass')).backdropFilter === 'none'")
    after = h.page.evaluate(cost)
    assert after["spinDur"] in ("1e-05s", "0.00001s") and after["spinIter"] == "1"
    assert after["fadeDur"] in ("1e-05s", "0.00001s")
    assert after["blur"] == "none"
    assert after["cardShadow"] == "none"                  # [class*="card"]: a large panel shadow
    assert "3px" in after["ringShadow"], ".selected keeps its ring"
    assert after["nebula"] == "none"


def test_lite_on_still_finishes_animations_so_end_states_apply(harness):
    h = open_lite(harness, init=[FAST_DEVICE, "localStorage.setItem('lite-mode','true')"])
    h.page.evaluate("""() => { const e = document.createElement('div'); e.id = 'pop'; e.style.animation = 'pop 2s forwards';
      e.textContent = 'x'; const st = document.createElement('style');
      st.textContent = '@keyframes pop{from{opacity:0}to{opacity:.5}}'; document.head.append(st); document.body.append(e); }""")
    h.page.wait_for_function("getComputedStyle(document.getElementById('pop')).opacity === '0.5'", timeout=1500)


# ---- account sync through shared/site-settings.js -------------------------

SYNC_HEAD = ('<script src="/shared/theme.js"></script><script src="/shared/lite-mode.js"></script>'
             '<script src="/shared/site-settings.js"></script>')


def open_sync(harness, remote, local=None):
    token = "localStorage.setItem('hub_bearer_token','test-token');"
    init = [FAST_DEVICE, token] + ([local] if local else [])
    h = harness(init_scripts=init)
    h.api_responses[("GET", "/users/me/settings")] = (200, {"settings": remote})
    h.api_responses[("PUT", "/users/me/settings")] = (200, {"settings": remote})
    h.pages["/t.html"] = page_html(SYNC_HEAD, "<p>hub</p>")
    h.goto()
    h.page.wait_for_timeout(400)
    return h


def put_bodies(h):
    return [json.loads(body) for method, path, body in h.api_calls if method == "PUT"]


def test_signed_in_account_value_is_applied_and_stored_locally(harness):
    h = open_sync(harness, {"theme": "dark", "lite_mode": True})
    assert lite(h.page) == "true" and h.page.evaluate("localStorage.getItem('lite-mode')") == "true"
    assert not any("lite_mode" in b for b in put_bodies(h)), "an applied remote value is not echoed back"


def test_a_local_choice_is_pushed_to_the_account(harness):
    h = open_sync(harness, {"theme": "dark"})
    assert not any("lite_mode" in b for b in put_bodies(h)), "an automatic or unchosen default is never uploaded"
    h.page.evaluate("NoyvjLite.set(true)")
    h.page.wait_for_timeout(300)
    assert {"lite_mode": True} in put_bodies(h)


def test_an_existing_local_choice_is_uploaded_when_the_account_has_none(harness):
    h = open_sync(harness, {"theme": "dark"}, local="localStorage.setItem('lite-mode','true')")
    assert any(b.get("lite_mode") is True for b in put_bodies(h))


def test_signed_out_players_make_no_requests(harness):
    h = harness(init_scripts=[FAST_DEVICE])
    h.pages["/t.html"] = page_html(SYNC_HEAD, "<p>hub</p>")
    h.goto()
    h.page.evaluate("NoyvjLite.set(true)")
    h.page.wait_for_timeout(300)
    assert h.api_calls == []


SEEN_TOURS = "localStorage.setItem('hub-onboarding-seen','1');localStorage.setItem('tutorial-seen:hub','1');"


# ---- the real hub pages ---------------------------------------------------

def test_hub_index_has_a_working_lite_button(harness):
    h = harness(init_scripts=[FAST_DEVICE, SEEN_TOURS])
    h.goto("/index.html")
    h.page.wait_for_selector("#lite-toggle")
    assert h.page.inner_text("#lite-toggle") == "Lite mode: off"
    h.page.click("#lite-toggle")
    assert lite(h.page) == "true" and h.page.inner_text("#lite-toggle") == "Lite mode: on"
    assert h.page.evaluate("localStorage.getItem('lite-mode')") == "true"
    assert h.page.evaluate("Boolean(document.querySelector('link[href*=\"lite-mode.css\"]'))")


def test_hub_settings_page_has_the_switch_and_reset_clears_it(harness):
    h = harness(init_scripts=[FAST_DEVICE, SEEN_TOURS, "localStorage.setItem('lite-mode','true')"])
    h.goto("/settings.html")
    h.page.wait_for_selector("#settings-lite")
    assert h.page.is_checked("#settings-lite") and lite(h.page) == "true"
    h.page.uncheck("#settings-lite")
    assert lite(h.page) == "false" and h.page.evaluate("localStorage.getItem('lite-mode')") == "false"
    h.page.check("#settings-lite")
    h.page.click("#settings-clear-prefs")
    h.page.click("#settings-confirm-yes")
    h.page.wait_for_function("localStorage.getItem('lite-mode') === null")
    assert not h.page.is_checked("#settings-lite") and lite(h.page) == "false"


# ---- Thaw's own lite mode is now the shared switch ------------------------

THAW_BODY = ('<div id="settings-panel" hidden><input type="checkbox" id="lite-mode-checkbox">'
             '<input type="checkbox" id="reduced-motion-checkbox"><button id="settings-reset-button">r</button></div>'
             '<button id="settings-toggle-button">s</button>')
THAW_HEAD = '<script src="/shared/lite-mode.js"></script><script src="/games/thaw/settings.js"></script>'


def open_thaw(harness, init=()):
    h = harness(init_scripts=[FAST_DEVICE, *init])
    h.pages["/t.html"] = page_html(THAW_HEAD, THAW_BODY)
    h.goto()
    return h


def test_thaw_checkbox_drives_the_shared_switch(harness):
    h = open_thaw(harness)
    assert not h.page.is_checked("#lite-mode-checkbox")
    h.page.evaluate("document.getElementById('settings-panel').hidden = false")
    h.page.check("#lite-mode-checkbox")
    assert lite(h.page) == "true" and h.page.evaluate("localStorage.getItem('lite-mode')") == "true"
    h.page.evaluate("NoyvjLite.set(false)")                       # the hub's switch changes it
    assert not h.page.is_checked("#lite-mode-checkbox")
    h.page.evaluate("NoyvjLite.set(true)")
    h.page.click("#settings-reset-button")                         # Thaw's reset turns it off
    assert lite(h.page) == "false" and not h.page.is_checked("#lite-mode-checkbox")


def test_thaws_old_per_game_choice_is_carried_over_once(harness):
    h = open_thaw(harness, init=["localStorage.setItem('thaw-lite-mode','true')"])
    assert lite(h.page) == "true" and h.page.is_checked("#lite-mode-checkbox")
    assert h.page.evaluate("localStorage.getItem('thaw-lite-mode')") is None
    assert h.page.evaluate("localStorage.getItem('lite-mode')") == "true"


def test_thaws_old_choice_does_not_override_a_new_one(harness):
    h = open_thaw(harness, init=["localStorage.setItem('thaw-lite-mode','true');localStorage.setItem('lite-mode','false')"])
    assert lite(h.page) == "false" and not h.page.is_checked("#lite-mode-checkbox")


def test_thaw_attribute_is_the_shared_one(harness):
    h = open_thaw(harness)
    assert h.page.evaluate("document.documentElement.hasAttribute('data-lite-mode')") is False
