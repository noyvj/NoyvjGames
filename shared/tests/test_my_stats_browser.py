"""QI-57: shared/last-played.js keeps a small local play log (opens, visible seconds per day and per hour,
capped, switchable off) and my-stats.html turns it into a plain readout. Nothing leaves the browser."""

import json

QUIET = "localStorage.setItem('hub-onboarding-seen','1'); localStorage.setItem('tutorial-seen:hub','1')"

GAME = """<!doctype html><html><head><meta charset="utf-8"></head><body>
<script>
window.__t = 1760000000000;               // fixed clock so seconds are exact
Date.now = () => window.__t;
</script>
<script src="/shared/last-played.js" data-game-id="tide"></script></body></html>"""


def log(h, slug="tide"):
    raw = h.page.evaluate(f"localStorage.getItem('play-log:{slug}')")
    return json.loads(raw) if raw else None


def open_game(harness, init=()):
    h = harness(init_scripts=list(init))
    h.pages["/g.html"] = GAME
    h.goto("/g.html")
    return h


def advance_and_leave(h, seconds):
    h.page.evaluate(f"window.__t += {seconds * 1000}; window.dispatchEvent(new Event('pagehide')); 0")


def test_an_open_is_counted_and_visible_time_is_added_when_the_page_is_left(harness):
    h = open_game(harness)
    data = log(h)
    day = next(iter(data["days"].values()))
    assert day["n"] == 1 and day["s"] == 0
    advance_and_leave(h, 95)
    data = log(h)
    day = next(iter(data["days"].values()))
    assert day["s"] == 95 and sum(data["hours"]) == 95


def test_one_stretch_is_capped_at_thirty_minutes(harness):
    h = open_game(harness)
    advance_and_leave(h, 5 * 3600)
    assert next(iter(log(h)["days"].values()))["s"] == 1800


def test_a_hidden_tab_does_not_count_until_it_is_shown_again(harness):
    h = open_game(harness)
    h.page.evaluate("""Object.defineProperty(document, 'visibilityState', {value: 'hidden', configurable: true});
      window.__t += 60000; document.dispatchEvent(new Event('visibilitychange')); 0""")
    assert next(iter(log(h)["days"].values()))["s"] == 60
    h.page.evaluate("""window.__t += 600000;
      Object.defineProperty(document, 'visibilityState', {value: 'visible', configurable: true});
      document.dispatchEvent(new Event('visibilitychange')); window.__t += 30000; window.dispatchEvent(new Event('pagehide')); 0""")
    assert next(iter(log(h)["days"].values()))["s"] == 90      # the 10 hidden minutes are not play


def test_switching_it_off_records_nothing(harness):
    h = open_game(harness, init=["localStorage.setItem('play-log:off','1')"])
    assert log(h) is None
    advance_and_leave(h, 50)
    assert log(h) is None


def test_old_days_are_dropped_past_the_cap_and_a_corrupt_log_restarts(harness):
    days = {f"2025-{m:02d}-{d:02d}": {"s": 1, "n": 1} for m in range(1, 7) for d in range(1, 29)}
    seed = "localStorage.setItem('play-log:tide', %s)" % json.dumps(json.dumps({"days": days, "hours": [0] * 24}))
    h = open_game(harness, init=[seed])
    assert len(log(h)["days"]) == 120
    h2 = open_game(harness, init=["localStorage.setItem('play-log:tide','{oops')"])
    assert sum(d["n"] for d in log(h2)["days"].values()) == 1


def seed_stats(*pairs):
    days_a = {"2026-10-05": {"s": 3600, "n": 2}, "2026-10-06": {"s": 1200, "n": 1}}
    hours_a = [0] * 24
    hours_a[21] = 3600
    hours_a[8] = 1200
    data = {"tide": {"days": days_a, "hours": hours_a},
            "canopy": {"days": {"2026-10-06": {"s": 300, "n": 1}}, "hours": [0] * 24}}
    return "; ".join(f"localStorage.setItem('play-log:{k}', {json.dumps(json.dumps(v))})" for k, v in data.items())


def stats_page(harness, *init):
    h = harness(init_scripts=[QUIET, *init])
    h.goto("/my-stats.html")
    h.page.wait_for_function("document.getElementById('stats-summary').textContent !== 'Loading…'")
    return h


def test_empty_state_is_a_calm_sentence(harness):
    h = stats_page(harness)
    assert "Nothing recorded yet" in h.page.inner_text("#stats-summary")
    assert h.page.is_hidden("#stats-games-card")


def test_stats_page_totals_games_weekdays_and_times_of_day(harness):
    h = stats_page(harness, seed_stats())
    summary = h.page.inner_text("#stats-summary")
    assert "1 h 25 min" in summary and "2 games" in summary and "4 times opened" in summary and "Most played: Tide" in summary
    rows = h.page.evaluate("[...document.querySelectorAll('#stats-games-body tr')].map(r => [...r.children].map(c => c.textContent))")
    assert rows[0] == ["Tide", "1 h 20 min", "3", "2"] and rows[1][0] == "Canopy"
    weekdays = h.page.evaluate("[...document.querySelectorAll('#stats-weekday li')].map(l => l.textContent)")
    assert any(w.startswith("Monday") and "1 h 00 min" in w for w in weekdays)       # 2026-10-05 is a Monday
    assert any(w.startswith("Tuesday") and "25 min" in w for w in weekdays)
    periods = h.page.evaluate("[...document.querySelectorAll('#stats-hours li')].map(l => l.textContent)")
    assert any(p.startswith("Evening") and "1 h 00 min" in p for p in periods)
    assert any(p.startswith("Morning") and "20 min" in p for p in periods)
    assert h.page.locator("#stats-recent li").count() == 14


def test_clear_needs_two_presses_and_the_switch_persists(harness):
    h = stats_page(harness, seed_stats())
    h.page.click("#stats-clear")
    assert h.page.evaluate("localStorage.getItem('play-log:tide')") is not None
    assert "Press again" in h.page.inner_text("#stats-clear")
    h.page.click("#stats-clear")
    assert h.page.evaluate("localStorage.getItem('play-log:tide')") is None
    assert "Nothing recorded yet" in h.page.inner_text("#stats-summary")
    h.page.uncheck("#stats-record")
    assert h.page.evaluate("localStorage.getItem('play-log:off')") == "1"
    h.page.check("#stats-record")
    assert h.page.evaluate("localStorage.getItem('play-log:off')") is None


def test_no_network_and_no_errors_and_fits_a_phone(harness):
    h = harness(init_scripts=[QUIET, seed_stats()], size=(360, 740))
    h.goto("/my-stats.html")
    h.page.wait_for_function("document.getElementById('stats-summary').textContent !== 'Loading…'")
    assert h.api_calls == [] and h.errors == []
    assert h.page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")
