"""admin.html's Problem reports panel (planning/TODO.md Z-17): lists what players sent, shows every
attachment only as a field the player chose, and triages with Mark done and Fixed. The backend is
answered by the test."""

import json

SIGNED_IN = "localStorage.setItem('hub_bearer_token','tok-owner');"

REPORTS = [
    {"id": "r1", "game_id": "canopy", "page": "/games/canopy/index.html", "note": "The tree button does nothing <b>x</b>",
     "schema_version": "3", "browser": "Chrome 130", "viewport": "360x740 @2x", "console_log": ["+1.0s [error] boom", "+2.0s [warn] hmm"],
     "attachment": {"save_code": "ABCD-2345"}, "username": "mara", "is_resolved": False, "resolved_at": None,
     "is_fixed": False, "fixed_note": None, "fixed_at": None, "created_at": "2026-10-09T10:00:00Z"},
    {"id": "r2", "game_id": "grid", "page": "/games/grid/index.html", "note": "Plain note only",
     "schema_version": None, "browser": None, "viewport": None, "console_log": None, "attachment": None, "username": None,
     "is_resolved": True, "resolved_at": "2026-10-09T11:00:00Z", "is_fixed": False, "fixed_note": None, "fixed_at": None,
     "created_at": "2026-10-08T10:00:00Z"},
]


def open_admin(harness, reports=REPORTS):
    h = harness(init_scripts=[SIGNED_IN])
    h.api_responses[("GET", "/users/me")] = (200, {"username": "noyvj"})
    h.api_responses[("GET", "/admin/bug-reports")] = (200, reports)
    h.goto("/admin.html")
    h.page.wait_for_function("document.querySelectorAll('#bugs-table tbody tr').length > 0 && !document.querySelector('#bugs-table .empty-row')")
    return h


def rows(h):
    return h.page.eval_on_selector_all("#bugs-table tbody tr", "els => els.map(e => e.textContent)")


def test_open_reports_are_listed_with_only_what_was_attached(harness):
    h = open_admin(harness)
    only = rows(h)
    assert len(only) == 1 and "Canopy" in only[0] and "The tree button does nothing" in only[0]
    assert "ABCD-2345" in only[0] and "Chrome 130" in only[0] and "360x740" in only[0] and "mara" in only[0]
    assert "Save schema" in only[0] and "2 console lines" in only[0]
    assert h.page.query_selector("#bugs-table b") is None                   # note text is escaped, never markup
    assert "1 open" in h.page.inner_text("#bugs-status")


def test_a_report_with_nothing_attached_says_so(harness):
    h = open_admin(harness)
    h.page.select_option("#bugs-state", "done")
    done = rows(h)
    assert len(done) == 1 and "Plain note only" in done[0] and "Nothing attached" in done[0]
    h.page.select_option("#bugs-state", "all")
    assert len(rows(h)) == 2
    h.page.fill("#bugs-filter", "grid")
    assert len(rows(h)) == 1


def test_mark_done_and_fixed_patch_the_report(harness):
    h = open_admin(harness)
    h.api_responses[("PATCH", "/admin/bug-reports/r1")] = (200, {**REPORTS[0], "is_resolved": True, "resolved_at": "2026-10-09T12:00:00Z"})
    h.page.click("#bugs-table .bug-toggle")
    h.page.wait_for_function("document.querySelectorAll('#bugs-table tbody tr .bug-toggle').length === 0 || document.querySelector('#bugs-table .empty-row')")
    patches = [json.loads(c[2]) for c in h.api_calls if c[0] == "PATCH" and c[1] == "/admin/bug-reports/r1"]
    assert patches == [{"resolved": True}]
    h.page.select_option("#bugs-state", "all")
    h.api_responses[("PATCH", "/admin/bug-reports/r1")] = (200, {**REPORTS[0], "is_resolved": True, "is_fixed": True, "fixed_note": "Marked fixed from the admin page"})
    h.page.click('#bugs-table .bug-fixed[data-id="r1"]')
    h.page.wait_for_function("document.querySelector('#bugs-table .bug-fixed[data-id=\"r1\"]').checked")
    patches = [json.loads(c[2]) for c in h.api_calls if c[0] == "PATCH" and c[1] == "/admin/bug-reports/r1"]
    assert patches[-1]["fixed"] is True


def test_an_old_server_without_the_route_shows_a_plain_message(harness):
    h = harness(init_scripts=[SIGNED_IN])
    h.api_responses[("GET", "/users/me")] = (200, {"username": "noyvj"})
    h.goto("/admin.html")
    h.page.wait_for_function("document.getElementById('bugs-status').textContent.includes('Failed to load problem reports')")
