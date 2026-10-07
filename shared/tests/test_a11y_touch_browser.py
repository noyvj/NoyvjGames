"""shared/a11y.css (Z-19) and shared/touch-targets.css (Z-23) in headless Chromium."""

from conftest import page_html

A11Y_HEAD = ('<style>.spin{animation:spin 5s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}'
             '.fade{transition:opacity 3s}.keep{animation:spin 5s linear infinite}'
             'a{color:#4af;text-decoration:none}.muted{opacity:.5;color:#888}'
             'button{border:1px solid #444;background:#222;color:#eee}</style>'
             '<link rel="stylesheet" href="/shared/a11y.css">')
A11Y_BODY = ('<div class="ambient-bg"><div class="ambient-bg-blobs" style="animation:spin 3s linear infinite"></div></div>'
             '<div id="spin" class="spin">s</div><div id="fade" class="fade">f</div>'
             '<div id="keep" class="keep" data-motion-essential>k</div>'
             '<a id="link" href="#x">link</a><p id="muted" class="muted">muted</p><button id="b">b</button>')


def a11y_page(harness, media=None, attrs="", **kwargs):
    h = harness(media=media, **kwargs)
    h.pages["/t.html"] = page_html(A11Y_HEAD, A11Y_BODY, attrs)
    h.goto()
    return h


def style(page, selector, prop):
    return page.evaluate("([s, p]) => getComputedStyle(document.querySelector(s))[p]", [selector, prop])


def test_nothing_changes_without_a_preference(harness):
    h = a11y_page(harness)
    assert style(h.page, "#spin", "animationDuration") == "5s"
    assert style(h.page, "#fade", "transitionDuration") == "3s"
    assert style(h.page, "#link", "textDecorationLine") == "none"
    assert style(h.page, "#muted", "opacity") == "0.5"
    assert style(h.page, "#b", "borderTopWidth") == "1px"


def reduced(page):
    return {s: style(page, s, "animationDuration") for s in ("#spin", "#keep", ".ambient-bg-blobs")}


def test_os_reduce_motion_ends_animations_and_transitions(harness):
    h = harness()
    page = h.page
    h.pages["/t.html"] = page_html(A11Y_HEAD, A11Y_BODY)
    page.emulate_media(reduced_motion="reduce")
    h.goto()
    d = reduced(page)
    assert d["#spin"] in ("1e-05s", "0.00001s") and d["#keep"] == "5s", "data-motion-essential opts out"
    assert d[".ambient-bg-blobs"] in ("0s", "1e-05s")
    assert style(page, "#fade", "transitionDuration") in ("1e-05s", "0.00001s")
    assert style(page, "#spin", "animationIterationCount") == "1"


def test_a_games_own_reduce_motion_switch_gets_the_same_treatment(harness):
    for attrs in ('data-reduced-motion="true"', 'class="reduce-motion"', 'data-hub-reduced-motion="true"'):
        h = a11y_page(harness, attrs=attrs)
        assert style(h.page, "#spin", "animationDuration") in ("1e-05s", "0.00001s"), attrs
    off = a11y_page(harness, attrs='data-reduced-motion="false"')
    assert style(off.page, "#spin", "animationDuration") == "5s", 'the "off" state of a game switch must not trigger it'


def test_more_contrast_strengthens_borders_links_text_and_focus(harness):
    h = harness()
    h.pages["/t.html"] = page_html(A11Y_HEAD, A11Y_BODY)
    h.page.emulate_media(contrast="more")
    h.goto()
    page = h.page
    assert style(page, "#b", "borderTopWidth") == "2px"
    assert style(page, "#link", "textDecorationLine") == "underline"
    assert style(page, "#muted", "opacity") == "1"
    assert style(page, "#muted", "color") == "rgb(255, 255, 255)"
    assert style(page, ".ambient-bg", "opacity") == "0.35"
    page.keyboard.press("Tab")
    page.keyboard.press("Tab")
    assert page.evaluate("document.activeElement.id") in ("link", "b")
    assert style(page, ":focus-visible", "outlineWidth") == "3px"


def test_more_contrast_in_the_light_theme_uses_black(harness):
    h = harness()
    h.pages["/t.html"] = page_html(A11Y_HEAD, A11Y_BODY, 'data-theme="light"')
    h.page.emulate_media(contrast="more")
    h.goto()
    assert style(h.page, "#muted", "color") == "rgb(0, 0, 0)"


# ---- touch targets ---------------------------------------------------------

TOUCH_HEAD = ('<style>button{font-size:12px;padding:4px 6px;border:1px solid #888}'
              '.bar{display:flex;flex-wrap:wrap;gap:8px;width:300px}.bar button{flex:1 1 0}'
              'details.info-toggle{margin:30px}.info-toggle summary{display:inline-flex;width:18px;height:18px;border-radius:50%;'
              'list-style:none;align-items:center;justify-content:center}'
              'a.hub-back-link{display:inline-block;font-size:13px;margin:30px}'
              '.board{display:grid;grid-template-columns:repeat(9,31px)}.board button{width:31px;height:31px;padding:0}'
              '</style><link rel="stylesheet" href="/shared/touch-targets.css">')
TOUCH_BODY = ('<a class="hub-back-link" href="#" id="back">All games</a>'
              '<div class="bar" id="bar"><button>Tutorial</button><button>How to Play</button><button>Achievements</button>'
              '<button>What\'s New</button><button>Settings</button><button>Reset Session</button></div>'
              '<details class="info-toggle" id="d"><summary id="i">i</summary><p>text</p></details>'
              '<label id="lab"><input id="cb" type="checkbox"> Mentor</label>'
              '<select id="sel"><option>One</option></select><input id="txt" type="text">'
              '<div class="board" id="board"></div>'
              '<div id="fixed" style="position:fixed;right:4px;bottom:4px"><button id="story">B</button></div>')


def touch_page(harness, size):
    h = harness(size=size, touch=size[0] < 700)
    h.pages["/t.html"] = page_html(TOUCH_HEAD, TOUCH_BODY)
    h.goto()
    h.page.evaluate("""() => { const b = document.getElementById('board');
      for (let i = 0; i < 81; i++) { const c = document.createElement('button'); c.className = 'cell'; if (i % 2) c.setAttribute('data-touch-exempt', ''); b.append(c); } }""")
    return h


def size_of(page, selector):
    r = page.evaluate("(s) => { const r = document.querySelector(s).getBoundingClientRect(); return [r.width, r.height]; }", selector)
    return r


def test_small_buttons_and_fields_reach_44px_on_a_phone(harness):
    h = touch_page(harness, (360, 740))
    for selector in ("#bar button", "#sel", "#txt", "#story", "#lab"):
        assert size_of(h.page, selector)[1] >= 44 - 0.01, selector


def test_a_wrapping_toolbar_keeps_its_row_packing(harness):
    # The 44px rule must not become a min-width: with flex:1 1 0 that would fit more buttons per row.
    wide = touch_page(harness, (1440, 900))
    phone = touch_page(harness, (360, 740))
    rows = lambda page: len({round(b["y"]) for b in page.evaluate(
        "Array.from(document.querySelectorAll('#bar button')).map(b => ({y: b.getBoundingClientRect().top}))")})
    assert rows(phone.page) == rows(wide.page)


def test_nothing_changes_on_a_wide_window_with_a_mouse(harness):
    h = touch_page(harness, (1440, 900))
    assert size_of(h.page, "#bar button")[1] < 40
    assert size_of(h.page, "#sel")[1] < 40


def test_info_buttons_and_back_link_keep_their_look_but_get_a_44px_hit_area(harness):
    h = touch_page(harness, (360, 740))
    page = h.page
    assert size_of(page, "#i") == [18, 18]
    for selector in ("#i", "#back"):
        box = page.evaluate("(s) => { const r = document.querySelector(s).getBoundingClientRect(); return [r.left + r.width/2, r.top + r.height/2]; }", selector)
        for dx, dy in ((-21, -21), (21, -21), (-21, 21), (21, 21)):
            hit = page.evaluate("([x, y, s]) => { const e = document.elementFromPoint(x, y); return !!e && (e === document.querySelector(s) || document.querySelector(s).contains(e)); }",
                                [box[0] + dx, box[1] + dy, selector])
            assert hit, f"{selector} {dx},{dy}"


def test_checkbox_is_bigger_and_exempt_elements_are_left_alone(harness):
    h = touch_page(harness, (360, 740))
    w, hgt = size_of(h.page, "#cb")
    assert w >= 22 and hgt >= 22
    cells = h.page.evaluate("Array.from(document.querySelectorAll('#board button[data-touch-exempt]')).map(b => b.getBoundingClientRect().height)")
    assert cells and all(abs(c - 31) < 0.5 for c in cells), "data-touch-exempt keeps a board cell its size"


def test_touch_action_is_manipulation_everywhere(harness):
    for size in ((360, 740), (1440, 900)):
        h = touch_page(harness, size)
        assert style(h.page, "#bar button", "touchAction") == "manipulation"
        assert style(h.page, "#sel", "touchAction") == "manipulation"
        assert style(h.page, "#back", "touchAction") == "manipulation"
