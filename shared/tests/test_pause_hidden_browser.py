"""shared/pause-hidden.js (planning/TODO.md Z-28) in headless Chromium, next to shared/time-controls.js.
Visibility is forced by redefining document.visibilityState and firing visibilitychange, which is
exactly what the browser does. The rule under test: while the tab is hidden no tick runs, the player's
own pause/speed survives, the setting can turn it off, and a note appears on return only when a running
game was really paused."""

import pytest

from conftest import page_html

HEAD = ('<link rel="stylesheet" href="/shared/time-controls.css">'
        '<style>body{margin:0;padding:12px;font-family:system-ui;background:#12162a;color:#eee}</style>')
BODY = ('<div id="time-controls"></div>'
        '<div id="settings-panel"><label for="pause-hidden-checkbox"><input type="checkbox" id="pause-hidden-checkbox" checked> Pause when this tab is hidden</label>'
        '<button id="settings-reset-button" type="button">Reset</button></div>'
        '<script src="/shared/time-controls.js" data-game-id="demo" data-container="#time-controls"></script>'
        '<script src="/shared/pause-hidden.js" data-game-id="demo"></script>'
        '<script>window.ticks = 0; window.NoyvjTime.start("demo", function () { window.ticks += 1; }, 1000);</script>')

SET_VISIBILITY = """state => {
  Object.defineProperty(document, 'visibilityState', {configurable: true, get: () => state});
  Object.defineProperty(document, 'hidden', {configurable: true, get: () => state === 'hidden'});
  document.dispatchEvent(new Event('visibilitychange'));
}"""


def open_page(harness, body=BODY, **kw):
    h = harness(**kw)
    h.pages["/t.html"] = page_html(HEAD, body)
    h.page.clock.install()
    h.goto()
    return h


def set_vis(h, state):
    h.page.evaluate(SET_VISIBILITY, state)


def ticks(h):
    return h.page.evaluate("window.ticks")


def note(h):
    return h.page.evaluate("(() => { const n = document.getElementById('pause-hidden-note'); return n && !n.hidden ? n.textContent : null; })()")


def test_no_tick_runs_while_hidden_and_it_resumes_where_it_was(harness):
    h = open_page(harness)
    h.page.click('.nt-speed[data-speed="2"]')
    h.page.evaluate("window.ticks = 0")
    h.page.clock.run_for(1000)
    assert ticks(h) == 2
    set_vis(h, "hidden")
    h.page.clock.run_for(10 * 60_000)
    assert ticks(h) == 2                      # ten minutes hidden: nothing advanced, nothing banked
    assert h.page.evaluate("NoyvjTime.get('demo').snapshot().state") == "held"
    set_vis(h, "visible")
    assert ticks(h) == 2                      # no burst on return
    h.page.clock.run_for(1000)
    assert ticks(h) == 4                      # still 2x, the player's speed survived the hold
    assert not h.errors


def test_the_note_appears_once_on_return_and_goes_away(harness):
    h = open_page(harness)
    set_vis(h, "hidden")
    assert note(h) is None
    set_vis(h, "visible")
    assert note(h) == "Paused while the tab was hidden"
    assert h.page.get_attribute("#pause-hidden-note", "role") == "status"
    h.page.clock.run_for(6000)
    assert note(h) is None


def test_a_player_who_paused_stays_paused_and_gets_no_note(harness):
    h = open_page(harness)
    h.page.click(".nt-pause")
    set_vis(h, "hidden")
    set_vis(h, "visible")
    assert note(h) is None
    assert h.page.evaluate("NoyvjTime.get('demo').paused") is True
    h.page.evaluate("window.ticks = 0")
    h.page.clock.run_for(5000)
    assert ticks(h) == 0


def test_turning_the_setting_off_keeps_the_old_behaviour(harness):
    h = open_page(harness)
    h.page.uncheck("#pause-hidden-checkbox")
    assert h.page.evaluate("localStorage.getItem('demo-pause-hidden')") == "off"
    set_vis(h, "hidden")
    h.page.evaluate("window.ticks = 0")
    h.page.clock.run_for(3000)
    assert ticks(h) == 3                       # a hidden tab keeps ticking as the browser allows
    set_vis(h, "visible")
    assert note(h) is None


def test_the_setting_is_remembered_and_the_reset_button_restores_the_default(harness):
    h = open_page(harness)
    h.page.uncheck("#pause-hidden-checkbox")
    h.page.reload()
    assert h.page.is_checked("#pause-hidden-checkbox") is False
    h.page.click("#settings-reset-button")
    assert h.page.is_checked("#pause-hidden-checkbox") is True
    assert h.page.evaluate("localStorage.getItem('demo-pause-hidden')") == "on"


def test_a_tab_opened_in_the_background_starts_held(harness):
    h = harness(init_scripts=["Object.defineProperty(document, 'visibilityState', {configurable: true, get: () => 'hidden'});"])
    h.pages["/t.html"] = page_html(HEAD, BODY)
    h.page.clock.install()
    h.goto()
    h.page.clock.run_for(5000)
    assert ticks(h) == 0
    set_vis(h, "visible")
    h.page.clock.run_for(2000)
    assert ticks(h) == 2


def test_hidden_twice_in_a_row_holds_once(harness):
    h = open_page(harness)
    set_vis(h, "hidden")
    set_vis(h, "hidden")
    assert h.page.evaluate("NoyvjTime.get('demo').snapshot().held") == ["hidden"]
    set_vis(h, "visible")
    assert h.page.evaluate("NoyvjTime.get('demo').snapshot().held") == []


def test_blocked_storage_falls_back_to_on(harness):
    h = open_page(harness)
    h.page.evaluate("void (Storage.prototype.getItem = function () { throw new Error('blocked'); })")
    assert h.page.evaluate("NoyvjPauseHidden.get('demo').enabled()") is True


def test_manual_mode_uses_the_games_own_hooks(harness):
    body = ('<div id="msg"></div><script src="/shared/pause-hidden.js" data-game-id="own" data-manual></script>'
            '<script>window.log = []; window.speed = 2;'
            'NoyvjPauseHidden.init({gameId: "own", hooks: {'
            ' pause() { window.log.push("pause"); return window.speed !== 0; },'
            ' resume() { window.log.push("resume"); }}});</script>')
    h = open_page(harness, body)
    set_vis(h, "hidden")
    set_vis(h, "visible")
    assert h.page.evaluate("window.log") == ["pause", "resume"]
    assert note(h) == "Paused while the tab was hidden"
    h.page.evaluate("window.speed = 0")
    set_vis(h, "hidden")
    set_vis(h, "visible")
    assert h.page.evaluate("window.log") == ["pause", "resume", "pause", "resume"]
    h.page.clock.run_for(6000)
    assert note(h) is None                     # nothing was running, so no note this time


@pytest.mark.parametrize("size", [(1440, 900), (360, 740)])
def test_the_note_fits_the_screen_in_one_line_or_two(harness, size):
    h = open_page(harness, size=size)
    set_vis(h, "hidden")
    set_vis(h, "visible")
    box = h.page.evaluate("(() => { const r = document.getElementById('pause-hidden-note').getBoundingClientRect(); return [r.left, r.right, r.bottom, innerWidth, innerHeight]; })()")
    assert box[0] >= 0 and box[1] <= box[3] and box[2] <= box[4]
