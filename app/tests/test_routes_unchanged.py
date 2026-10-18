"""The route table, pinned. A task that deletes, renames or re-orders a route fails this test.

Adding a route on purpose: add its (method, path) line to EXPECTED_ROUTES in the position where it is
registered (the order is the order of the include_router lines in main.py), in the same change. Do not
delete or edit an existing line to make a test pass; report it instead.
"""

from main import app

EXPECTED_ROUTES = [
    ("GET", "/openapi.json"),
    ("GET", "/docs"),
    ("GET", "/docs/oauth2-redirect"),
    ("GET", "/redoc"),
    ("GET", "/health"),
    ("POST", "/ratings"),
    ("GET", "/ratings-summary"),
    ("GET", "/ratings/{game_slug}"),
    ("POST", "/saves"),
    ("GET", "/saves/{save_code}"),
    ("PUT", "/saves/{save_code}"),
    ("POST", "/answer-reports"),
    ("GET", "/answer-reports"),
    ("PATCH", "/answer-reports/{report_id}"),
    ("PATCH", "/answer-reports/{report_id}/fixed"),
    ("POST", "/auth/signup"),
    ("POST", "/auth/login"),
    ("POST", "/saves/{save_code}/claim"),
    ("GET", "/users/me/saves"),
    ("PUT", "/users/me/saves/{game_id}/slots/{slot}"),
    ("POST", "/users/me/snapshots"),
    ("GET", "/users/me/snapshots"),
    ("GET", "/users/me/snapshots/{snapshot_id}"),
    ("DELETE", "/users/me/snapshots/{snapshot_id}"),
    ("GET", "/owner/notes/{key}"),
    ("PUT", "/owner/notes/{key}"),
    ("GET", "/users/me"),
    ("GET", "/users/me/settings"),
    ("PUT", "/users/me/settings"),
    ("POST", "/feedback"),
    ("GET", "/feedback"),
    ("GET", "/admin/feedback"),
    ("PATCH", "/admin/feedback/{feedback_id}"),
    ("GET", "/admin/ratings"),
    ("PATCH", "/admin/ratings/{rating_id}"),
    ("GET", "/admin/stats"),
    ("GET", "/users/me/email"),
    ("PUT", "/users/me/email"),
    ("GET", "/admin/users"),
    ("PATCH", "/admin/users/{user_id}"),
    ("GET", "/stats/games"),
    ("GET", "/stats/games/{game_id}"),
    ("GET", "/stats/games/{game_id}/percentile"),
    ("GET", "/stats/achievements"),
    ("GET", "/leaderboards/{game_id}/{board}"),
    ("PUT", "/leaderboards/{game_id}/{board}"),
    ("DELETE", "/leaderboards/{game_id}/{board}"),
    ("GET", "/leaderboard"),
    ("GET", "/leaderboard/{game_id}/{board}"),
    ("POST", "/scores"),
    ("DELETE", "/scores/{game_id}/{board}"),
    ("GET", "/users/me/scores"),
    ("DELETE", "/users/me/scores"),
    ("GET", "/users/me/leaderboard-privacy"),
    ("PUT", "/users/me/leaderboard-privacy"),
    ("GET", "/admin/scores"),
    ("PATCH", "/admin/scores/{score_id}"),
    ("GET", "/market/prices"),
    ("GET", "/pools/{game_id}/{pool}"),
    ("POST", "/pools/{game_id}/{pool}"),
    ("POST", "/stats/pageview"),
    ("GET", "/users/me/export"),
    ("DELETE", "/users/me"),
    ("GET", "/admin/timeseries"),
    ("PUT", "/whats-new/votes/{entry_id}"),
    ("DELETE", "/whats-new/votes/{entry_id}"),
    ("GET", "/admin/whats-new-votes"),
    ("POST", "/bug-reports"),
    ("GET", "/admin/bug-reports"),
    ("PATCH", "/admin/bug-reports/{report_id}"),
    ("POST", "/ghosts"),
    ("GET", "/ghosts/{game_id}/mine"),
    ("DELETE", "/ghosts/{game_id}"),
    ("GET", "/ghosts/{game_id}/peer"),
    ("POST", "/ghosts/report"),
    ("GET", "/admin/ghost-reports"),
    ("POST", "/admin/ghost-reports/{report_id}/resolve"),
    ("PUT", "/admin/ghosts/{ghost_id}/hidden"),
    ("GET", "/users/me/profile"),
    ("PUT", "/users/me/profile"),
    ("POST", "/users/me/profile/backfill"),
    ("GET", "/profiles/{username}"),
]


def _route_table():
    rows = []
    for route in app.routes:
        for method in sorted(route.methods or []):
            if method != "HEAD":
                rows.append((method, route.path))
    return rows


def test_route_table_is_unchanged():
    assert _route_table() == EXPECTED_ROUTES


def test_no_route_is_registered_twice():
    table = _route_table()
    assert len(table) == len(set(table))
