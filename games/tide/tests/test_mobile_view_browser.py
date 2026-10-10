"""D-26: the phone view (All / Coast / Meters / Log), swipes between the parts, bigger tap targets and the
tap-a-tile note. Runs the real index.html and ui.js without booting the game (see browser_support.py)."""

import re
from pathlib import Path

from .browser_support import chromium, tide_page  # noqa: F401  (fixtures)

GAME_DIR = Path(__file__).resolve().parent.parent

ADD_TILES = """() => {
  const grid = document.getElementById('coastline-grid');
  for (let r = 0; r < 2; r++) for (let c = 0; c < 8; c++) {
    const tile = document.createElement('div');
    tile.className = 'coastline-tile coastline-land';
    tile.id = 'coastline-tile-' + r + '-' + c;
    tile.title = 'Row ' + r + ' floods once sea level reaches ' + (90 - r * 15) + '.';
    grid.appendChild(tile);
  }
}"""

SWIPE = """(dx) => {
  const t = document.getElementById('coastline-comparison');
  const mk = (type, x) => {
    const touch = new Touch({identifier: 1, target: t, clientX: x, clientY: 300});
    return new TouchEvent(type, {bubbles: true, cancelable: true, touches: type === 'touchend' ? [] : [touch],
                                 changedTouches: [touch], targetTouches: []});
  };
  t.dispatchEvent(mk('touchstart', 200)); t.dispatchEvent(mk('touchend', 200 + dx));
}"""


def visible_tags(page):
    return page.evaluate("""() => [...document.querySelectorAll('[data-mview]')]
        .filter(e => getComputedStyle(e).display !== 'none')
        .flatMap(e => e.dataset.mview.split(' ')).filter((v, i, a) => a.indexOf(v) === i).sort()""")


def active(page):
    return page.evaluate("document.documentElement.getAttribute('data-mview-active')")


def test_markup_tags_are_only_the_three_views():
    html = (GAME_DIR / "index.html").read_text(encoding="utf-8")
    values = set(re.findall(r'data-mview="([^"]+)"', html))
    assert values == {"coast", "meters", "log"}
    picks = set(re.findall(r'data-mview-pick="([^"]+)"', html))
    assert picks == {"all", "coast", "meters", "log"}
    # The default is "All": the bar's All button starts pressed.
    assert re.search(r'id="mview-all"[^>]*aria-pressed="true"', html)


def test_desktop_page_has_the_bar_but_never_shows_it():
    desktop = (GAME_DIR / "pc.html").read_text(encoding="utf-8")
    assert 'id="mobile-views"' in desktop  # same markup; CSS hides it under data-layout="pc"
    css = (GAME_DIR / "style.css").read_text(encoding="utf-8")
    assert 'html:not([data-layout="pc"]) .mobile-views' in css


def test_default_view_hides_nothing(tide_page):
    t = tide_page()
    page = t.open()
    assert active(page) == "all"
    assert visible_tags(page) == ["coast", "log", "meters"]
    assert page.evaluate("getComputedStyle(document.getElementById('mobile-views')).display") == "flex"
    assert [e for e in t.errors if "loadPyodide" not in e] == []  # Pyodide is refused on purpose


def test_each_view_shows_only_its_own_part(tide_page):
    t = tide_page()
    page = t.open()
    for view in ("coast", "meters", "log"):
        page.evaluate(f"document.getElementById('mview-{view}').click()")
        assert active(page) == view
        assert visible_tags(page) == [view]
        assert page.evaluate(f"document.getElementById('mview-{view}').getAttribute('aria-pressed')") == "true"
        assert page.evaluate("document.getElementById('mview-all').getAttribute('aria-pressed')") == "false"
    # Things without a view always stay: the dock, the header, the feedback prompt.
    for selector in ("#actions-dock", "#feedback-prompt", ".game-toolbar"):
        assert page.evaluate(f"getComputedStyle(document.querySelector('{selector}')).display") != "none"
    page.evaluate("document.getElementById('mview-all').click()")
    assert visible_tags(page) == ["coast", "log", "meters"]


def test_swipe_moves_along_coast_meters_log_and_stops_at_the_ends(tide_page):
    t = tide_page()
    page = t.open()
    page.evaluate("document.getElementById('mview-coast').click()")
    seen = []
    for dx in (-120, -120, -120, 120, 120, 120):
        page.evaluate(SWIPE, dx)
        seen.append(active(page))
    assert seen == ["meters", "log", "log", "meters", "coast", "coast"]
    assert "Showing" in page.inner_text("#mobile-view-status")


def test_swipes_do_nothing_on_all_and_ignore_short_or_vertical_moves(tide_page):
    t = tide_page()
    page = t.open()
    page.evaluate(SWIPE, -150)
    assert active(page) == "all"
    page.evaluate("document.getElementById('mview-coast').click()")
    page.evaluate(SWIPE, -30)   # too short
    assert active(page) == "coast"
    page.evaluate("""() => {
      const t = document.getElementById('coastline-comparison');
      const mk = (type, x, y) => { const touch = new Touch({identifier: 1, target: t, clientX: x, clientY: y});
        return new TouchEvent(type, {bubbles: true, touches: type === 'touchend' ? [] : [touch], changedTouches: [touch]}); };
      t.dispatchEvent(mk('touchstart', 200, 100)); t.dispatchEvent(mk('touchend', 90, 400));   // mostly vertical
    }""")
    assert active(page) == "coast"


def test_a_swipe_that_starts_on_a_slider_or_graph_is_left_alone(tide_page):
    t = tide_page()
    page = t.open()
    page.evaluate("document.getElementById('mview-meters').click()")
    page.evaluate("""() => {
      const s = document.createElement('input'); s.type = 'range'; s.id = 'probe-slider'; document.body.appendChild(s);
      const touch = new Touch({identifier: 1, target: s, clientX: 200, clientY: 300});
      s.dispatchEvent(new TouchEvent('touchstart', {bubbles: true, touches: [touch], changedTouches: [touch]}));
      const end = new Touch({identifier: 1, target: s, clientX: 60, clientY: 300});
      s.dispatchEvent(new TouchEvent('touchend', {bubbles: true, touches: [], changedTouches: [end]}));
    }""")
    assert active(page) == "meters"


def test_choice_is_remembered_for_next_visit(tide_page):
    t = tide_page()
    page = t.open()
    page.evaluate("document.getElementById('mview-log').click()")
    assert page.evaluate("localStorage.getItem('tide-mobile-view')") == "log"
    page.reload()
    assert active(page) == "log"
    assert visible_tags(page) == ["log"]


def test_wide_window_shows_everything_and_no_bar(tide_page):
    t = tide_page(size=(1280, 800), touch=False)
    page = t.open()
    page.evaluate("document.getElementById('mview-coast').click()")  # a stored choice must not hide anything here
    assert page.evaluate("getComputedStyle(document.getElementById('mobile-views')).display") == "none"
    assert visible_tags(page) == ["coast", "log", "meters"]


def test_desktop_layout_never_hides_parts(tide_page):
    t = tide_page(size=(360, 740), page_name="index.html")
    page = t.open()
    page.evaluate("document.documentElement.setAttribute('data-layout', 'pc')")
    page.evaluate("document.documentElement.setAttribute('data-mview-active', 'coast')")
    assert page.evaluate("getComputedStyle(document.getElementById('mobile-views')).display") == "none"
    assert visible_tags(page) == ["coast", "log", "meters"]


def test_tiles_are_44px_tall_and_a_tap_writes_the_row_note(tide_page):
    t = tide_page()
    page = t.open()
    page.evaluate(ADD_TILES)
    height = page.evaluate("document.querySelector('#coastline-grid .coastline-tile').getBoundingClientRect().height")
    assert height >= 44
    page.evaluate("document.getElementById('coastline-tile-1-3').click()")
    assert page.inner_text("#coastline-tap-readout") == "Row 1 floods once sea level reaches 75."
    # Tiles being rebuilt (a new season) clears the note so it never goes stale.
    page.evaluate("document.getElementById('coastline-grid').innerHTML = ''")
    page.wait_for_function("document.getElementById('coastline-tap-readout').textContent === ''")


def test_invest_and_chip_buttons_reach_44px_on_a_phone(tide_page):
    t = tide_page()
    page = t.open()
    sizes = page.evaluate("""() => ['output-invest-button', 'advance-season-button', 'advance-x5-button',
        'ticker-filter-fish', 'graph-range-10', 'mview-coast'].map(id => [id, document.getElementById(id).getBoundingClientRect().height])""")
    for ident, height in sizes:
        assert height >= 43.5, (ident, height)
