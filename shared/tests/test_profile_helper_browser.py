"""shared/profile.js (planning/TODO.md Z-7) in headless Chromium: posts only for a signed-in player,
throttled, never throws or blocks, keeps work waiting when a post fails. Clock and backend are
controlled by the test."""

import json

from conftest import API, page_html

TAG = '<script src="/shared/profile.js" data-game-id="canopy"></script>'
PAGE = page_html(TAG, "<p>a game</p>")
SIGNED_IN = "localStorage.setItem('hub_bearer_token','tok-abc')"
CLOCK = "window.__t = 1000000; "


def open_page(harness, init=(), page=PAGE):
    h = harness(init_scripts=list(init))
    h.pages["/t.html"] = page
    h.goto()
    h.requests = []
    h.page.on("request", lambda r: h.requests.append(r) if r.url.startswith(API) else None)
    h.page.evaluate("window.__t = 1000000; NoyvjProfile.configure({now: () => window.__t})")
    h.api_responses[("PUT", "/users/me/profile")] = (200, {"is_public": False})
    return h


def posts(h):
    return [json.loads(c[2]) for c in h.api_calls if c[0] == "PUT" and c[1] == "/users/me/profile"]


def settle(h):
    h.page.wait_for_timeout(150)


def test_signed_out_does_nothing_and_remembers_nothing(harness):
    h = open_page(harness)
    assert h.page.evaluate("NoyvjProfile.update({seconds: 90, achievements: 3, streaks: {daily: 4}})") is None
    settle(h)
    assert h.api_calls == []
    assert h.page.evaluate("localStorage.getItem('profile-sync:canopy')") is None


def test_first_update_posts_numbers_only_with_the_token(harness):
    h = open_page(harness, init=[SIGNED_IN])
    h.page.evaluate("NoyvjProfile.update({seconds: 312, achievements: 7, streaks: {daily: 4}})")
    settle(h)
    assert posts(h) == [{"progress": {"game": "canopy", "add_seconds": 312, "achievements": 7, "streaks": {"daily": 4}}}]
    assert h.requests[0].headers["authorization"] == "Bearer tok-abc"
    pending = h.page.evaluate("NoyvjProfile.pending('canopy')")
    assert pending == {"seconds": 0, "achievements": None, "streaks": {}}


def test_updates_inside_five_minutes_wait_and_are_summed_into_the_next_post(harness):
    h = open_page(harness, init=[SIGNED_IN])
    h.page.evaluate("NoyvjProfile.update({seconds: 100, achievements: 2})")
    settle(h)
    h.page.evaluate("window.__t += 60000; NoyvjProfile.update({seconds: 50, achievements: 3, streaks: {daily: 2}})")
    h.page.evaluate("window.__t += 60000; NoyvjProfile.update({seconds: 25, achievements: 3, streaks: {daily: 5}})")
    settle(h)
    assert len(posts(h)) == 1                                   # throttled
    assert h.page.evaluate("NoyvjProfile.pending('canopy')") == {"seconds": 75, "achievements": 3, "streaks": {"daily": 5}}
    h.page.evaluate("window.__t += 300000; NoyvjProfile.update({seconds: 5})")
    settle(h)
    assert posts(h)[1] == {"progress": {"game": "canopy", "add_seconds": 80, "achievements": 3, "streaks": {"daily": 5}}}


def test_a_failed_post_keeps_the_work_for_the_next_try(harness):
    h = open_page(harness, init=[SIGNED_IN])
    h.api_responses[("PUT", "/users/me/profile")] = (500, {"detail": "boom"})
    h.page.evaluate("NoyvjProfile.update({seconds: 100, achievements: 2})")
    settle(h)
    assert h.page.evaluate("NoyvjProfile.pending('canopy')")["seconds"] == 100
    h.api_responses[("PUT", "/users/me/profile")] = (200, {})
    h.page.evaluate("window.__t += 400000; NoyvjProfile.update({seconds: 20})")
    settle(h)
    assert posts(h)[-1]["progress"]["add_seconds"] == 120
    assert h.page.evaluate("NoyvjProfile.pending('canopy')")["seconds"] == 0


def test_too_many_requests_backs_off_for_fifteen_minutes(harness):
    h = open_page(harness, init=[SIGNED_IN])
    h.api_responses[("PUT", "/users/me/profile")] = (429, {"detail": "slow"})
    h.page.evaluate("NoyvjProfile.update({seconds: 10})")
    settle(h)
    h.api_responses[("PUT", "/users/me/profile")] = (200, {})
    h.page.evaluate("window.__t += 600000; NoyvjProfile.update({seconds: 10})")      # 10 min: still backing off
    settle(h)
    assert len(posts(h)) == 1
    h.page.evaluate("window.__t += 400000; NoyvjProfile.update({seconds: 10})")      # past 15 min
    settle(h)
    assert len(posts(h)) == 2 and posts(h)[1]["progress"]["add_seconds"] == 30


def test_it_never_throws_even_with_blocked_storage_and_no_server(harness):
    blocked = "Object.defineProperty(window, 'localStorage', {get() { throw new Error('blocked'); }});"
    h = open_page(harness, init=[blocked])
    assert h.page.evaluate("NoyvjProfile.update({seconds: 5, achievements: 1})") is None
    assert h.page.evaluate("NoyvjProfile.flush()") is None
    h2 = open_page(harness, init=[SIGNED_IN])
    h2.page.evaluate("NoyvjProfile.configure({apiBase: 'https://offline.invalid'})")
    assert h2.page.evaluate("NoyvjProfile.update({seconds: 5})") is None
    settle(h2)
    assert h.errors == [] and h2.errors == []


def test_update_returns_immediately_it_is_not_a_promise(harness):
    h = open_page(harness, init=[SIGNED_IN])
    assert h.page.evaluate("typeof NoyvjProfile.update({seconds: 1})") == "undefined"


def test_without_seconds_it_counts_the_time_the_page_was_visible(harness):
    h = open_page(harness, init=[SIGNED_IN])
    h.page.evaluate("window.__t += 95000; NoyvjProfile.update({achievements: 1})")
    settle(h)
    assert posts(h)[0]["progress"]["add_seconds"] == 95


def test_explicit_seconds_replace_the_measured_ones(harness):
    h = open_page(harness, init=[SIGNED_IN])
    h.page.evaluate("window.__t += 95000; NoyvjProfile.update({seconds: 10})")
    settle(h)
    assert posts(h)[0]["progress"]["add_seconds"] == 10


def test_achievements_may_be_a_count_or_a_list_and_only_rise(harness):
    h = open_page(harness, init=[SIGNED_IN])
    h.api_responses[("PUT", "/users/me/profile")] = (500, {})
    h.page.evaluate("NoyvjProfile.update({seconds: 1, achievements: ['a','b','c']})")
    h.page.evaluate("NoyvjProfile.update({seconds: 1, achievements: 2})")
    settle(h)
    assert h.page.evaluate("NoyvjProfile.pending('canopy')")["achievements"] == 3


def test_bad_input_is_ignored(harness):
    h = open_page(harness, init=[SIGNED_IN])
    h.page.evaluate("NoyvjProfile.update({game: 'Bad Slug', seconds: 5})")
    h.page.evaluate("NoyvjProfile.update(null); NoyvjProfile.update('x'); NoyvjProfile.update()")
    h.page.evaluate("NoyvjProfile.update({seconds: 5, streaks: {'Bad Label': 3, ok_label: -2, fine: 'x', good: 6}})")
    settle(h)
    assert posts(h)[-1]["progress"]["streaks"] == {"good": 6}
    assert all(p["progress"]["game"] == "canopy" for p in posts(h))


def test_seasonal_badge_ids_ride_along_and_bad_ones_do_not(harness):
    badges = {"version": 1, "badges": [{"id": "halloween-2026", "label": "Anything <b>goes</b>"}, {"id": "Bad Id"}, {"label": "no id"}]}
    h = open_page(harness, init=[SIGNED_IN, f"localStorage.setItem('event_badges_v1', {json.dumps(json.dumps(badges))})"])
    h.page.evaluate("NoyvjProfile.update({seconds: 1})")
    settle(h)
    body = posts(h)[0]
    assert body["event_badges"] == ["halloween-2026"]
    assert "goes" not in json.dumps(body)               # labels are never sent


def test_a_page_that_is_hiding_sends_what_is_waiting(harness):
    h = open_page(harness, init=[SIGNED_IN])
    h.page.evaluate("NoyvjProfile.update({seconds: 1})")
    settle(h)
    h.page.evaluate("window.__t += 60000; NoyvjProfile.update({seconds: 40})")       # throttled: waits
    assert len(posts(h)) == 1
    h.page.evaluate("window.__t += 30000; window.dispatchEvent(new Event('pagehide'))")
    settle(h)
    assert len(posts(h)) == 2 and posts(h)[1]["progress"]["add_seconds"] >= 40


def test_one_post_never_credits_more_than_four_hours(harness):
    h = open_page(harness, init=[SIGNED_IN])
    h.page.evaluate("NoyvjProfile.update({seconds: 20000})")
    settle(h)
    assert posts(h)[0]["progress"]["add_seconds"] == 14400
    assert h.page.evaluate("NoyvjProfile.pending('canopy')")["seconds"] == 20000 - 14400
