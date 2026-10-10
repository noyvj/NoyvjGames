"""shared/sandbox-mode.js + shared/sandbox-mode.css (Z-18) in headless Chromium. The component is only
plumbing (the enter/leave button, the "Sandbox: nothing here is saved" banner, a dashed frame, the
announcements), so a fake `window.pyodide.globals.get(name)` stands in for a game's three Python
functions. Per-game rules (real state untouched, no achievements, no collapse, a save restores the
real game) are tested in each adopting game's own tests."""

from conftest import page_html

HEAD = ('<link rel="stylesheet" href="/shared/sandbox-mode.css">'
        '<style>body{margin:0;padding:12px;font-family:system-ui;background:#12162a;color:#eee}</style>')
BODY = ('<div id="bar"><button id="t" type="button" data-sandbox-toggle>Practice sandbox</button></div>'
        '<p id="s" data-sandbox-status></p>'
        '<script>'
        'window.calls = [];'
        'window.gameOn = false;'
        'window.enterOk = true;'
        'var table = {'
        '  sandbox_enter: function () { window.calls.push("enter"); if (window.enterOk) window.gameOn = true; return window.enterOk; },'
        '  sandbox_leave: function () { window.calls.push("leave"); window.gameOn = false; return true; },'
        '  sandbox_is_active: function () { return window.gameOn; }'
        '};'
        'window.pyodide = { globals: { get: function (n) { var f = table[n]; if (!f) return undefined;'
        '  var g = function () { return f(); }; g.destroy = function () { window.calls.push("destroy:" + n); }; return g; } } };'
        '</script>'
        '<script src="/shared/sandbox-mode.js" data-game-id="demo"></script>')


def open_page(harness, body=BODY, **kw):
    h = harness(**kw)
    h.pages["/t.html"] = page_html(HEAD, body)
    h.goto()
    return h


def banner_visible(h):
    return h.page.evaluate("(() => { const b = document.getElementById('noyvj-sandbox-banner'); "
                           "return !!b && !b.hidden && getComputedStyle(b).display !== 'none'; })()")


def test_starts_off_with_the_enter_label_and_no_visible_banner(harness):
    h = open_page(harness)
    assert h.page.inner_text("#t") == "Practice sandbox"
    assert h.page.get_attribute("#t", "aria-pressed") == "false"
    assert not banner_visible(h)
    assert h.page.evaluate("document.documentElement.hasAttribute('data-sandbox')") is False
    assert h.page.evaluate("NoyvjSandbox.active()") is False
    assert h.page.evaluate("window.calls") == []                 # nothing is called until the player asks
    assert not h.errors


def test_enter_shows_the_banner_the_frame_and_the_leave_label(harness):
    h = open_page(harness)
    h.page.click("#t")
    assert h.page.evaluate("window.calls.filter(c => c.indexOf('destroy') !== 0)") == ["enter"]
    assert h.page.evaluate("window.gameOn") is True
    assert banner_visible(h)
    text = h.page.inner_text("#noyvj-sandbox-banner")
    assert "Sandbox: nothing here is saved." in text
    assert "real game is safe" in text
    assert h.page.inner_text("#t") == "Leave sandbox"
    assert h.page.get_attribute("#t", "aria-pressed") == "true"
    assert h.page.get_attribute("html", "data-sandbox") == "true"
    assert "Sandbox on" in h.page.inner_text("#s")
    frame = h.page.evaluate("(() => { const s = getComputedStyle(document.documentElement, '::after'); "
                            "return [s.position, s.borderTopStyle, s.pointerEvents]; })()")
    assert frame == ["fixed", "dashed", "none"]
    assert not h.errors


def test_the_banner_is_a_fixed_overlay_and_never_pushes_the_page(harness):
    h = open_page(harness)
    before = h.page.evaluate("document.getElementById('bar').getBoundingClientRect().top")
    h.page.click("#t")
    after = h.page.evaluate("document.getElementById('bar').getBoundingClientRect().top")
    assert before == after
    assert h.page.evaluate("getComputedStyle(document.getElementById('noyvj-sandbox-banner')).position") == "fixed"
    box = h.page.evaluate("(() => { const r = document.getElementById('noyvj-sandbox-banner').getBoundingClientRect(); "
                          "return [r.left, r.right, innerWidth]; })()")
    assert box[0] >= 0 and box[1] <= box[2]


def test_leave_from_the_banner_or_the_toggle_puts_everything_back(harness):
    h = open_page(harness)
    h.page.click("#t")
    h.page.click("#noyvj-sandbox-banner [data-sandbox-leave]")
    assert h.page.evaluate("window.gameOn") is False
    assert not banner_visible(h)
    assert h.page.inner_text("#t") == "Practice sandbox"
    assert h.page.get_attribute("#t", "aria-pressed") == "false"
    assert h.page.evaluate("document.documentElement.hasAttribute('data-sandbox')") is False
    assert h.page.inner_text("#s") == ""
    h.page.click("#t")
    h.page.click("#t")                                           # the toggle itself also leaves
    assert h.page.evaluate("window.gameOn") is False and not banner_visible(h)
    assert h.page.evaluate("window.calls.filter(c => c.indexOf('destroy') !== 0)") == ["enter", "leave", "enter", "leave"]
    assert not h.errors


def test_the_pyodide_function_proxies_are_destroyed_after_each_call(harness):
    h = open_page(harness)
    h.page.click("#t")
    h.page.click("#t")
    calls = h.page.evaluate("window.calls")
    assert calls.count("destroy:sandbox_enter") == 1 and calls.count("destroy:sandbox_leave") == 1
    assert calls.count("destroy:sandbox_is_active") >= 2


def test_a_game_that_leaves_by_itself_is_picked_up_by_sync_and_announced(harness):
    h = open_page(harness)
    h.page.evaluate("window.events = []; document.addEventListener('noyvj-sandbox-change', e => window.events.push(e.detail))")
    h.page.click("#t")
    h.page.evaluate("window.gameOn = false; NoyvjSandbox.sync()")      # e.g. load_state() left the sandbox
    assert not banner_visible(h) and h.page.inner_text("#t") == "Practice sandbox"
    assert h.page.evaluate("window.events") == [{"active": True, "gameId": "demo"}, {"active": False, "gameId": "demo"}]
    h.page.evaluate("NoyvjSandbox.sync()")                             # nothing changed: no extra event
    assert len(h.page.evaluate("window.events")) == 2


def test_on_change_listeners_run_in_order(harness):
    h = open_page(harness)
    h.page.evaluate("window.seen = []; NoyvjSandbox.onChange(a => window.seen.push(a))")
    h.page.click("#t")
    h.page.click("#t")
    assert h.page.evaluate("window.seen") == [True, False]


def test_a_game_that_is_still_loading_gets_a_clear_message_and_no_error(harness):
    h = open_page(harness)
    h.page.evaluate("delete window.pyodide")
    h.page.click("#t")
    assert not banner_visible(h)
    assert "still loading" in h.page.inner_text("#s")
    h.page.wait_for_timeout(120)
    assert "still loading" in h.page.evaluate("document.getElementById('noyvj-sandbox-live').textContent")
    assert not h.errors


def test_a_refused_enter_leaves_everything_off(harness):
    h = open_page(harness)
    h.page.evaluate("window.enterOk = false")
    h.page.click("#t")
    assert not banner_visible(h) and h.page.inner_text("#t") == "Practice sandbox"
    assert h.page.evaluate("NoyvjSandbox.active()") is False


def test_a_toggle_added_or_moved_later_still_works_by_delegation(harness):
    h = open_page(harness)
    h.page.evaluate("(() => { const b = document.createElement('button'); b.id = 'late'; b.type = 'button'; "
                    "b.setAttribute('data-sandbox-toggle', ''); b.textContent = 'Try it'; document.body.appendChild(b); })()")
    h.page.click("#late")
    assert banner_visible(h) and h.page.inner_text("#late") == "Leave sandbox"
    h.page.click("#late")
    assert h.page.inner_text("#late") == "Try it", "the button's own enter label comes back"


def test_the_announcement_region_is_a_polite_status_and_text_is_text_only(harness):
    h = open_page(harness)
    h.page.click("#t")
    h.page.wait_for_timeout(120)
    assert h.page.get_attribute("#noyvj-sandbox-live", "role") == "status"
    assert h.page.get_attribute("#noyvj-sandbox-live", "aria-live") == "polite"
    assert "Nothing you do here is saved" in h.page.evaluate("document.getElementById('noyvj-sandbox-live').textContent")
    assert h.page.evaluate("document.getElementById('noyvj-sandbox-banner').querySelectorAll('script,img,iframe').length") == 0


def test_the_leave_button_is_a_real_button_with_a_tap_target(harness):
    h = open_page(harness, size=(360, 740), touch=True)
    h.page.click("#t")
    box = h.page.evaluate("(() => { const r = document.querySelector('#noyvj-sandbox-banner [data-sandbox-leave]').getBoundingClientRect(); "
                          "return [r.width, r.height]; })()")
    assert box[1] >= 36 and box[0] >= 44
    right = h.page.evaluate("document.getElementById('noyvj-sandbox-banner').getBoundingClientRect().right")
    assert right <= 360


def test_nothing_is_stored_and_nothing_is_sent(harness):
    h = open_page(harness)
    h.page.click("#t")
    h.page.click("#t")
    assert h.page.evaluate("localStorage.length + sessionStorage.length") == 0
    assert h.page.evaluate("document.cookie") == ""
    assert h.api_calls == []


def test_a_reload_is_the_real_game_again(harness):
    h = open_page(harness)
    h.page.click("#t")
    assert banner_visible(h)
    h.goto()
    assert not banner_visible(h) and h.page.inner_text("#t") == "Practice sandbox"


def test_configure_accepts_plain_javascript_handlers(harness):
    body = ('<button id="t" type="button" data-sandbox-toggle>Try the sandbox</button>'
            '<script src="/shared/sandbox-mode.js" data-game-id="plain"></script>'
            '<script>window.flag = false; NoyvjSandbox.configure({gameId: "plain", '
            'enter: () => { window.flag = true; return true; }, leave: () => { window.flag = false; return true; }, '
            'active: () => window.flag});</script>')
    h = open_page(harness, body=body)
    h.page.click("#t")
    assert banner_visible(h) and h.page.evaluate("window.flag") is True
    h.page.click("#noyvj-sandbox-banner [data-sandbox-leave]")
    assert h.page.evaluate("window.flag") is False and h.page.inner_text("#t") == "Try the sandbox"


def test_light_theme_uses_the_light_tokens_and_keeps_contrast(harness):
    h = open_page(harness)
    h.page.evaluate("document.documentElement.setAttribute('data-theme','light')")
    h.page.click("#t")
    colors = h.page.evaluate("(() => { const s = getComputedStyle(document.getElementById('noyvj-sandbox-banner')); "
                             "return [s.backgroundColor, s.color]; })()")
    assert colors[0] == "rgb(255, 246, 214)" and colors[1] == "rgb(59, 47, 0)"


def test_it_prints_as_nothing(harness):
    h = open_page(harness)
    h.page.click("#t")
    h.page.emulate_media(media="print")
    assert not banner_visible(h)
