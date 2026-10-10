"""QI-58 "Pick up where you stopped": shared/last-played.js lets a game leave a one-line note (a direct set, or
a Python resume_note() read when the page is hidden) and the hub strip shows the three most recent games with
their notes, without sending anything anywhere."""

import json
import time

QUIET = "localStorage.setItem('hub-onboarding-seen','1'); localStorage.setItem('tutorial-seen:hub','1')"

GAME_PAGE = """<!doctype html><html><head><meta charset="utf-8"></head><body>
<script>window.pyodide = {globals: {get(name) {
  if (name !== 'resume_note') return undefined;
  const fn = () => window.__note; fn.destroy = () => { window.__destroyed = true; }; return fn; }}};</script>
<script src="/shared/last-played.js" data-game-id="tide"></script></body></html>"""


def stamp(slug, ago_hours=1):
    return f"localStorage.setItem('last-played:{slug}', String(Date.now() - {int(ago_hours * 3600 * 1000)}))"


def note(slug, text):
    return f"localStorage.setItem('resume-note:{slug}', JSON.stringify({{t: Date.now(), text: {json.dumps(text)}}}))"


def hub(harness, *init):
    h = harness(init_scripts=[QUIET, *init])
    h.goto("/index.html")
    h.page.wait_for_selector("#game-grid .title-card")
    return h


def strip(h):
    return h.page.evaluate("[...document.querySelectorAll('#pickup-list a')].map(a => a.textContent)")


def test_strip_is_hidden_for_a_new_visitor(harness):
    h = hub(harness)
    assert h.page.is_hidden("#pickup-section")


def test_shows_the_three_most_recent_games_newest_first_with_their_notes(harness):
    h = hub(harness, stamp("canopy", 50), stamp("tide", 2), note("tide", "Year 12, tide rising"),
            stamp("grid", 5), stamp("signal", 30), stamp("sol", 100))
    out = strip(h)
    assert len(out) == 3
    assert out[0].startswith("Tide — Year 12, tide rising") and "last played 2 hours ago" in out[0]
    assert out[1].startswith("Grid") and "—" not in out[1]
    assert out[2].startswith("Signal")
    assert h.page.is_visible("#pickup-section")


def test_old_games_and_unreadable_notes_are_ignored(harness):
    h = hub(harness, stamp("canopy", 24 * 90), stamp("tide", 1), "localStorage.setItem('resume-note:tide','{not json')")
    out = strip(h)
    assert len(out) == 1 and out[0].startswith("Tide") and "—" not in out[0].split("(")[0]


def test_note_text_is_plain_text_and_capped(harness):
    h = hub(harness, stamp("tide", 1), note("tide", "<b>x</b> " + "y" * 200))
    assert h.page.evaluate("document.querySelectorAll('#pickup-list a b').length") == 0
    assert len(strip(h)[0].split("—")[1].split(" (")[0].strip()) <= 80


def test_game_can_set_a_note_directly(harness):
    h = harness()
    h.pages["/g.html"] = GAME_PAGE
    h.goto("/g.html")
    assert h.page.evaluate("NoyvjResume.set('  Day 14,\\n3 events in  ')") == "Day 14, 3 events in"
    stored = json.loads(h.page.evaluate("localStorage.getItem('resume-note:tide')"))
    assert stored["text"] == "Day 14, 3 events in" and abs(stored["t"] - time.time() * 1000) < 60000
    h.page.evaluate("NoyvjResume.set('')")
    assert h.page.evaluate("localStorage.getItem('resume-note:tide')") is None


def test_python_resume_note_is_read_when_the_page_is_hidden(harness):
    h = harness()
    h.pages["/g.html"] = GAME_PAGE
    h.goto("/g.html")
    h.page.evaluate("window.__note = 'Wave 3 of 6'; window.dispatchEvent(new Event('pagehide')); 0")
    stored = json.loads(h.page.evaluate("localStorage.getItem('resume-note:tide')"))
    assert stored["text"] == "Wave 3 of 6"
    assert h.page.evaluate("window.__destroyed") is True


def test_a_game_without_resume_note_and_a_throwing_one_do_nothing(harness):
    h = harness()
    h.pages["/g.html"] = GAME_PAGE.replace("window.__note", "(() => { throw new Error('x'); })()")
    h.goto("/g.html")
    h.page.evaluate("window.dispatchEvent(new Event('pagehide')); 0")
    assert h.page.evaluate("localStorage.getItem('resume-note:tide')") is None
    assert h.errors == []
