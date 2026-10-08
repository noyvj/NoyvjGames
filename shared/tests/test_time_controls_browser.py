"""shared/time-controls.js (planning/TODO.md W-2) in headless Chromium, with a fake clock so ticks are
counted exactly. The rule under test: the control only changes how OFTEN the tick is called, never what a
tick does, and a pause means no tick at all (no stored time debt, nothing caught up afterwards)."""

import pytest

from conftest import page_html

HEAD = ('<link rel="stylesheet" href="/shared/time-controls.css">'
        '<style>body{margin:0;padding:12px;font-family:system-ui;background:#12162a;color:#eee}'
        'html[data-theme="light"] body{background:#eef2fc;color:#1b2033}</style>')
BODY = ('<div id="time-controls"></div><input id="box" type="text"><button id="other" type="button">other</button>'
        '<div id="opening-screen" hidden style="width:100px;height:20px"></div>'
        '<script src="/shared/time-controls.js" data-game-id="demo" data-container="#time-controls"></script>'
        '<script>window.ticks = 0; window.NoyvjTime.start("demo", function () { window.ticks += 1; }, 1000);</script>')


def open_page(harness, **kw):
    h = harness(**kw)
    h.pages["/t.html"] = page_html(HEAD, BODY)
    h.page.clock.install()
    h.goto()
    return h


def run(h, ms):
    h.page.clock.run_for(ms)


def ticks(h):
    return h.page.evaluate("window.ticks")


def test_one_x_ticks_once_per_base_interval(harness):
    h = open_page(harness)
    run(h, 5000)
    assert ticks(h) == 5
    assert not h.errors


@pytest.mark.parametrize("speed,expected", [(1, 5), (2, 10), (4, 20)])
def test_speed_scales_only_how_often_the_tick_is_called(harness, speed, expected):
    h = open_page(harness)
    h.page.click(f'.nt-speed[data-speed="{speed}"]')
    h.page.evaluate("window.ticks = 0")
    run(h, 5000)
    assert ticks(h) == expected
    snap = h.page.evaluate("NoyvjTime.get('demo').snapshot()")
    assert snap["speed"] == speed and snap["intervalMs"] == 1000 // speed and snap["running"] is True


def test_pause_stops_ticks_completely_and_resume_catches_up_nothing(harness):
    h = open_page(harness)
    run(h, 3000)
    assert ticks(h) == 3
    h.page.click(".nt-pause")
    run(h, 60_000)
    assert ticks(h) == 3                       # a whole minute passed, no tick, nothing banked
    h.page.click(".nt-pause")                   # resume
    assert ticks(h) == 3                       # resuming does not fire a burst
    run(h, 2000)
    assert ticks(h) == 5


def test_choosing_a_speed_while_paused_resumes_at_that_speed(harness):
    h = open_page(harness)
    h.page.click(".nt-pause")
    h.page.click('.nt-speed[data-speed="2"]')
    snap = h.page.evaluate("NoyvjTime.get('demo').snapshot()")
    assert snap["paused"] is False and snap["speed"] == 2
    run(h, 1000)
    assert ticks(h) == 2


def test_hold_never_overwrites_the_players_pause_or_speed(harness):
    h = open_page(harness)
    h.page.click('.nt-speed[data-speed="4"]')
    h.page.evaluate("NoyvjTime.get('demo').hold('hidden')")
    h.page.evaluate("window.ticks = 0")
    run(h, 3000)
    assert ticks(h) == 0
    assert h.page.inner_text(".nt-status") == "⏸ Paused (tab hidden)"
    assert h.page.evaluate("document.documentElement.getAttribute('data-time-state')") == "held"
    h.page.evaluate("NoyvjTime.get('demo').release('hidden')")
    assert h.page.evaluate("NoyvjTime.get('demo').speed") == 4
    run(h, 1000)
    assert ticks(h) == 4
    # a player who paused before the hold is still paused after it
    h.page.click(".nt-pause")
    h.page.evaluate("NoyvjTime.get('demo').hold('hidden'); NoyvjTime.get('demo').release('hidden')")
    assert h.page.evaluate("NoyvjTime.get('demo').isRunning()") is False


def test_starting_again_replaces_the_tick_and_never_adds_a_second_timer(harness):
    h = open_page(harness)
    h.page.evaluate("window.other = 0; NoyvjTime.start('demo', function () { window.other += 1; }, 1000)")
    h.page.evaluate("window.ticks = 0")
    run(h, 4000)
    assert ticks(h) == 0 and h.page.evaluate("window.other") == 4


def test_the_interval_has_a_floor_and_bad_input_is_ignored(harness):
    h = open_page(harness)
    assert h.page.evaluate("NoyvjTime.intervalFor(100, 4)") == 25
    assert h.page.evaluate("NoyvjTime.intervalFor(40, 4)") == 20          # floor
    assert h.page.evaluate("NoyvjTime.intervalFor(1000, 0)") == 1000
    assert h.page.evaluate("NoyvjTime.intervalFor(0, 2)") == 0
    assert h.page.evaluate("NoyvjTime.get('demo').setSpeed(3)") is False   # not a configured speed
    assert h.page.evaluate("NoyvjTime.start('demo', null, 1000)") is False
    assert h.page.evaluate("NoyvjTime.start('demo', function () {}, -5)") is False


def test_a_throwing_tick_does_not_stop_the_loop(harness):
    h = open_page(harness)
    h.page.evaluate("window.n = 0; NoyvjTime.start('demo', function () { window.n += 1; if (window.n === 2) throw new Error('boom'); }, 1000)")
    for _ in range(4):                          # the fake clock re-raises the page error; the real page just logs it
        try:
            run(h, 1000)
        except Exception:
            pass
    assert h.page.evaluate("window.n") == 4


def test_keys_space_slower_faster(harness):
    h = open_page(harness)
    h.page.keyboard.press("]")
    assert h.page.evaluate("NoyvjTime.get('demo').speed") == 2
    h.page.keyboard.press("]")
    h.page.keyboard.press("]")                  # already at the top: stays 4
    assert h.page.evaluate("NoyvjTime.get('demo').speed") == 4
    h.page.keyboard.press("[")
    assert h.page.evaluate("NoyvjTime.get('demo').speed") == 2
    h.page.keyboard.press("Space")
    assert h.page.evaluate("NoyvjTime.get('demo').paused") is True
    h.page.keyboard.press("Space")
    assert h.page.evaluate("NoyvjTime.get('demo').paused") is False
    h.page.keyboard.press("]")                  # choosing a speed from a pause resumes
    h.page.keyboard.press("Space")
    h.page.keyboard.press("[")
    assert h.page.evaluate("NoyvjTime.get('demo').snapshot()")["running"] is True


def test_keys_leave_text_boxes_focused_buttons_and_dialogs_alone(harness):
    h = open_page(harness)
    h.page.focus("#box")
    h.page.keyboard.press("Space")
    h.page.keyboard.press("]")
    assert h.page.evaluate("NoyvjTime.get('demo').snapshot()")["running"] is True
    assert h.page.evaluate("NoyvjTime.get('demo').speed") == 1
    h.page.focus("#other")                       # Space belongs to a focused button
    h.page.keyboard.press("Space")
    assert h.page.evaluate("NoyvjTime.get('demo').paused") is False
    h.page.evaluate("document.activeElement.blur(); document.getElementById('opening-screen').hidden = false")
    h.page.keyboard.press("Space")               # the opening screen is up
    assert h.page.evaluate("NoyvjTime.get('demo').paused") is False
    h.page.evaluate("document.getElementById('opening-screen').hidden = true")
    h.page.keyboard.press("Space")
    assert h.page.evaluate("NoyvjTime.get('demo').paused") is True


def test_keys_can_be_turned_off_and_handled_by_the_game(harness):
    h = harness()
    h.pages["/t.html"] = page_html(HEAD, BODY.replace('data-container="#time-controls"', 'data-container="#time-controls" data-keys="off"'))
    h.page.clock.install()
    h.goto()
    h.page.keyboard.press("Space")
    assert h.page.evaluate("NoyvjTime.get('demo').paused") is False
    handled = h.page.evaluate("NoyvjTime.get('demo').handleKey({key: ' ', target: document.body, repeat: false})")
    assert handled is True and h.page.evaluate("NoyvjTime.get('demo').paused") is True


def test_buttons_say_their_state_in_text_and_aria(harness):
    h = open_page(harness)
    assert h.page.get_attribute('.nt-speed[data-speed="1"]', "aria-pressed") == "true"
    assert h.page.get_attribute(".nt-pause", "aria-pressed") == "false"
    assert h.page.inner_text(".nt-status") == "▶ Running at 1x"
    h.page.click('.nt-speed[data-speed="4"]')
    assert h.page.inner_text(".nt-status") == "▶ Running at 4x"
    assert h.page.get_attribute('.nt-speed[data-speed="4"]', "aria-pressed") == "true"
    h.page.click(".nt-pause")
    assert h.page.get_attribute(".nt-pause", "aria-pressed") == "true"
    assert h.page.inner_text(".nt-status") == "⏸ Paused"
    assert all(h.page.get_attribute(f'.nt-speed[data-speed="{n}"]', "aria-pressed") == "false" for n in (1, 2, 4))
    assert h.page.get_attribute(".nt-bar", "role") == "group"
    assert h.page.get_attribute(".nt-status", "role") == "status"
    # the pressed state is not colour only: a check mark and a heavier border
    h.page.click('.nt-speed[data-speed="2"]')
    style = h.page.evaluate("""() => { const b = document.querySelector('.nt-speed[aria-pressed=true]');
        return {before: getComputedStyle(b, '::before').content, border: getComputedStyle(b).borderTopWidth}; }""")
    assert "✓" in style["before"] and style["border"] == "3px"


def test_every_control_is_a_real_button_of_at_least_44px_and_keyboard_operable(harness):
    h = open_page(harness)
    sizes = h.page.evaluate("[...document.querySelectorAll('.nt-btn')].map(b => { const r = b.getBoundingClientRect(); return [b.tagName, r.width, r.height]; })")
    assert len(sizes) == 4
    for tag, w, hgt in sizes:
        assert tag == "BUTTON" and w >= 44 and hgt >= 44
    h.page.focus('.nt-speed[data-speed="2"]')
    h.page.keyboard.press("Enter")
    assert h.page.evaluate("NoyvjTime.get('demo').speed") == 2
    h.page.keyboard.press("Space")               # Space on the focused button presses the button, not the global pause
    assert h.page.evaluate("NoyvjTime.get('demo').speed") == 2
    assert h.page.evaluate("NoyvjTime.get('demo').paused") is False


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_light_and_dark_keep_the_text_readable(harness, scheme):
    h = harness(media={"color_scheme": scheme})
    h.pages["/t.html"] = page_html(HEAD, BODY, 'data-theme="%s"' % scheme)
    h.page.clock.install()
    h.goto()
    colours = h.page.evaluate("""() => { const s = getComputedStyle(document.querySelector('.nt-status'));
        const g = getComputedStyle(document.querySelector('.nt-bar'));
        return [s.color, g.backgroundColor]; }""")
    assert colours[0] != colours[1]


def test_reduced_motion_removes_the_transition(harness):
    h = harness(media={"reduced_motion": "reduce"})
    h.pages["/t.html"] = page_html(HEAD, BODY)
    h.page.clock.install()
    h.goto()
    assert h.page.evaluate("getComputedStyle(document.querySelector('.nt-btn')).transitionDuration") in ("0s", "")
    h.page.evaluate("document.documentElement.setAttribute('data-reduced-motion', 'true')")
    assert h.page.evaluate("getComputedStyle(document.querySelector('.nt-btn')).transitionDuration") in ("0s", "")


def test_on_a_phone_width_the_bar_fits_without_sideways_scroll(harness):
    h = open_page(harness, size=(360, 740), touch=True)
    assert h.page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")
    right = h.page.evaluate("document.querySelector('.nt-bar').getBoundingClientRect().right")
    assert right <= 360


def test_onchange_callbacks_and_the_document_event_report_every_change(harness):
    h = open_page(harness)
    h.page.evaluate("window.seen = []; document.addEventListener('noyvj-time-change', e => window.seen.push(e.detail.state + ':' + e.detail.speed));")
    h.page.click('.nt-speed[data-speed="2"]')
    h.page.click(".nt-pause")
    h.page.click(".nt-pause")
    assert h.page.evaluate("window.seen") == ["running:2", "paused:2", "running:2"]


def test_destroy_clears_the_timer_and_the_markup(harness):
    h = open_page(harness)
    h.page.evaluate("NoyvjTime.get('demo').destroy()")
    h.page.evaluate("window.ticks = 0")
    run(h, 5000)
    assert ticks(h) == 0
    assert h.page.query_selector(".nt-bar") is None
    assert h.page.evaluate("NoyvjTime.get('demo')") is None
