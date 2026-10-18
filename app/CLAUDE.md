# app/ — the NoyvjGames backend (FastAPI + SQLAlchemy)

One FastAPI app: star ratings, feedback and bug reports, save codes, accounts (username + password), account
saves and snapshots, opt-in leaderboards, community pools, cross-game stats, ghost settlements, profiles and the
admin/owner routes. FastAPI Cloud (Python 3.12) redeploys `app/` by itself a few minutes after the user pushes to
GitHub; production data is a Neon Postgres database. Here, tests run under Python 3.9 against in-memory sqlite and
never touch a real database: `cd app && python3 -m pytest -q` (about 500 tests, about 40 s).

Before 2026-10-18 all routes lived in one 97 KB `main.py`. It was split by feature (TODO item LA-4) with no
behaviour change: every route path, method, status code, model and header is identical (the OpenAPI schema was
compared byte for byte before and after).

## File map (one line per file; open only the file the task names)

| File | What lives there | Layer |
|---|---|---|
| `main.py` | App assembly only: creates `app`, the body-size and CORS middleware, the startup schema thread, one `include_router` per router file (in route-registration order), and the "Compatibility names" block that re-exports every name the old single-file `main` had. No routes. | 4 |
| `routes_core.py` | `GET /health`; ratings (`/ratings`, `/ratings-summary`); anonymous save codes (`POST/GET/PUT /saves...`) | 3 |
| `routes_answer_reports.py` | Champ de Mots "I think this should count" reports + admin triage | 3 |
| `routes_accounts.py` | `POST /auth/signup`, `POST /auth/login` (password check, login throttle, session start) | 3 |
| `routes_account_saves.py` | claim a save code, save slots, snapshots (the save "time machine") | 3 |
| `routes_owner.py` | `/owner/notes/{key}` (ideas answers, game notes, playtest notes) | 3 |
| `routes_me.py` | `GET /users/me`, synced settings (`/users/me/settings`) | 3 |
| `routes_feedback.py` | site feedback (`/feedback`) and admin moderation of feedback and ratings, `GET /admin/stats` | 3 |
| `routes_email.py` | optional account email (`/users/me/email`) | 3 |
| `routes_admin_users.py` | `GET /admin/users`, `PATCH /admin/users/{user_id}` (test-account flag) | 3 |
| `routes_stats.py` | public cross-game aggregate stats (`/stats/...`) | 3 |
| `routes_leaderboards.py` | original per-game leaderboards `/leaderboards/{game_id}/{board}` | 3 |
| `routes_scores.py` | opt-in score boards (`/scores`, `/leaderboard...`, `/users/me/scores`, privacy, admin hide); the biggest router file | 3 |
| `routes_market_pools.py` | `/market/prices`, community pools `/pools/...`, `POST /stats/pageview` | 3 |
| `routes_account_data.py` | `GET /users/me/export`, `DELETE /users/me` | 3 |
| `routes_admin_timeseries.py` | `GET /admin/timeseries` | 3 |
| `routes_votes.py` | What's New "was this helpful?" votes + `GET /admin/whats-new-votes` | 3 |
| `routes_bug_reports.py` | in-game "Report a problem" (`/bug-reports`) + admin triage | 3 |
| `routes_profiles.py` | player profiles (`/users/me/profile...`, public `GET /profiles/{username}`) | 3 |
| `ghosts.py` | ghost settlements: helpers AND `make_router(...)` (the routes; `main.py` calls it, passing in the auth functions) | 3 |
| `auth.py` | `get_current_user`, `get_current_user_optional`, `require_admin`, `OWNER_USERNAME`, `owner_signup_allowed`, `_normalize_username`, `_test_user_ids` | 2 |
| `schemas_saves.py` | save-code constants and `SaveIn`, `SaveUpdate`, `SaveOut` (shared by `routes_core` and `routes_account_saves`) | 2 |
| `schemas_admin.py` | `HiddenFlagIn` (body of the admin hide routes) | 2 |
| `constants.py` | `ID_MAX_LENGTH`, `TEXT_MAX_LENGTH` | 1 |
| `passwords.py` | PBKDF2 `_hash_password` / `_verify_password` | 1 |
| `rate_limits.py` | all `*_LIMITER` objects (`FailureLimiter`), `_client_key`, `_throttle`, `reset_write_limiters` | 1 |
| `database.py` | engine (`DATABASE_URL`), `SessionLocal`, `Base`, `get_db`, `patch_schema`, `init_schema` | 0 |
| `models.py` | every SQLAlchemy table (list below) | 0 |
| `throttle.py` | the `FailureLimiter` class | 0 |
| `account_data.py`, `boards.py`, `bug_reports.py`, `leaderboards.py`, `market.py`, `pools.py`, `profiles.py`, `snapshots.py`, `stats.py` | pure helper modules (rules, validation, queries) used by the routers; no routes | 0-1 |
| `pyproject.toml` | dependencies and the `py-modules` list. **Never edit** (see do-nots) | - |
| `tests/` | one `test_<topic>.py` per feature, `conftest.py`, `test_file_sizes.py`, `test_routes_unchanged.py` | - |

### Layering rule

A module imports only from a lower layer (the layer column). Layer 0 and 1 import nothing from this app except
other layer-0/1 files; `auth` and `schemas_*` (layer 2) import layer 0-1; `routes_*` (layer 3) import layers 0-2 and
never another `routes_*` file; `main.py` imports everything. If two routers need the same model or helper, move it
to a layer-2 file (`schemas_*.py` or `auth.py`), do not import one router from another. No cycles.

## How to add an endpoint

1. Pick the router file for the feature (File map). A new feature gets a new `routes_<topic>.py` starting with
   `from fastapi import APIRouter` and `router = APIRouter()`; keep every file under 14,000 estimated tokens
   (`tests/test_file_sizes.py` enforces it).
2. Write the request model (`pydantic.BaseModel`, with `Field(max_length=...)` on every string, using
   `ID_MAX_LENGTH` / `TEXT_MAX_LENGTH` from `constants`) in the same router file; only a model used by two routers goes
   to a `schemas_*.py`.
3. Decorate with `@router.get/post/put/patch/delete("/path")`. Take the database as `db: Session = Depends(get_db)`,
   the caller as `current_user: User = Depends(get_current_user)` (or `get_current_user_optional`, or
   `_admin: None = Depends(require_admin)`). Public write routes call `_throttle(SOME_LIMITER, request)` first.
4. New router file only: add `from routes_<topic> import router as routes_<topic>_router` and
   `app.include_router(routes_<topic>_router)` to `main.py` (at the end, before the Compatibility block, unless the
   path could be shadowed by an earlier `/{param}` route), and report that `py-modules` in `pyproject.toml` needs the
   new module name.
5. Add the route's `("METHOD", "/path")` line to `EXPECTED_ROUTES` in `tests/test_routes_unchanged.py` at the position
   where it is registered. This is the only edit allowed there.
6. Write `tests/test_<topic>.py` (see test conventions) and run the whole suite.

## Compatibility names (why `main.py` has a long import block at the bottom)

Tests and old scripts do `import main` and read names like `main.RATING_LIMITER`. Those names are re-exported from
the module that owns them. Reading works; **replacing** a name does not: `monkeypatch.setattr(main, "X", ...)`
changes only `main`'s copy. Patch the module whose code uses the name, for example
`monkeypatch.setattr(routes_bug_reports, "BUG_REPORT_LIMITER", ...)`, `routes_profiles` for the two profile limiters,
`routes_accounts` for `_username_exists`, `routes_core` for `engine` (the health route). Objects that are only
mutated (`main._feedback_submission_log.clear()`, `SIGNUP_LIMITER.reset()`) work through either name.

## For the local AI

### Who may call what (auth model)

| Label | Meaning | How |
|---|---|---|
| public | no credentials (write routes are rate limited per address) | - |
| session | a signed-in account | header `Authorization: Bearer <bearer_token>` from signup/login; missing or unknown = 401 |
| session? | account optional (anonymous works, signed-in is recorded) | same header, optional |
| admin | the site owner or an AI session | header `X-Admin-Token` equal to env `ADMIN_TOKEN` or `AI_ADMIN_TOKEN` (compared in constant time), OR a session of the account named `noyvj`. With neither env var set: 503. Wrong or missing: 401 |
| owner | the account named `noyvj` only | session of that account, else 403 |

The name `noyvj` is reserved at signup unless env `OWNER_SIGNUP_ALLOWED` is `1`/`true` (tests set it).
Accounts whose username starts with `aitest` are flagged `is_test` at signup; admin/stat routes can hide them.

### Routes by router (method path: body -> response fields; auth)

Bodies list fields; `?` means optional. All bodies are JSON. Limits: a request body over 5,000,000 bytes gets 413.

**routes_core.py**
- GET /health -> `status`, `db`; public (always 200, `Cache-Control: no-store`)
- POST /ratings: `RatingIn` (`game_slug`, `stars?` 1-5, `comment?`, `response?`; needs stars or response) -> `RatingOut` (`id`, `game_slug`, `stars`, `comment`, `response`); public, rate limited
- GET /ratings-summary -> `games`; public
- GET /ratings/{game_slug} -> list of `RatingOut`; public (hidden rows left out)
- POST /saves: `SaveIn` (`game_id`, `save_data`) -> `SaveOut` (`save_code`, `game_id`, `slot`, `slot_name`, `save_data`, `created_at`, `updated_at`); public, rate limited
- GET /saves/{save_code} -> `SaveOut`; public (wrong codes are throttled per address)
- PUT /saves/{save_code}: `SaveUpdate` (`save_data`) -> `SaveOut`; public

**routes_answer_reports.py**
- POST /answer-reports: `AnswerReportIn` (`game_id?`, `item_id`, `submitted_answer`, `marked_correct_answer` list, `topic_type?`) -> `AnswerReportOut` (`id`, `game_id`, `item_id`, `submitted_answer`, `marked_correct_answer`, `topic_type`, `created_at`, `is_resolved`, `resolved_at`, `is_fixed`, `fixed_note`, `fixed_at`); public, rate limited
- GET /answer-reports?game_id&topic_type&item_id&resolved -> list of `AnswerReportOut`; admin
- PATCH /answer-reports/{report_id}: `ReportResolveIn` (`resolved`) -> `AnswerReportOut`; admin
- PATCH /answer-reports/{report_id}/fixed: `ReportFixedIn` (`fixed`, `note?`) -> `AnswerReportOut`; admin

**routes_accounts.py**
- POST /auth/signup: `AuthIn` (`username`, `password`) -> `AuthOut` (`bearer_token`, `username`); public, rate limited; 409 if the name is taken
- POST /auth/login: `AuthIn` -> `AuthOut`; public; failed attempts counted per username and per address (429 when blocked)

**routes_account_saves.py** (all session)
- POST /saves/{save_code}/claim -> `SaveOut`
- GET /users/me/saves -> list of `SaveOut`
- PUT /users/me/saves/{game_id}/slots/{slot}: `SlotSaveIn` (`save_data`, `name?`) -> `SaveOut`
- POST /users/me/snapshots: `SnapshotIn` (`game_id`, `slot?`, `summary?`, `save_data`) -> snapshot dict (see `_snapshot_out`); rate limited per account
- GET /users/me/snapshots?game_id -> list of snapshot dicts; GET /users/me/snapshots/{snapshot_id} -> one (with `save_data`); DELETE /users/me/snapshots/{snapshot_id} -> `deleted`

**routes_owner.py**
- GET /owner/notes/{key} -> `key`, `value`, `updated_at`; admin
- PUT /owner/notes/{key}: any JSON object -> `key`, `updated_at`; owner (capped at 1 MB)

**routes_me.py** (session)
- GET /users/me -> `username`; GET /users/me/settings -> `settings`; PUT /users/me/settings: a settings object (theme, text scale, reduced motion; validated by `_validate_settings`) -> `settings`

**routes_feedback.py**
- POST /feedback: `FeedbackIn` (`game_id?`, `rating?` 1-5, `comment?`; needs one of the two) -> `FeedbackOut` (`id`, `game_id`, `user_id`, `rating`, `comment`, `created_at`); session?; limited to `FEEDBACK_RATE_LIMIT_PER_HOUR` per address
- GET /feedback?game_id -> list of `FeedbackPublicOut` (`id`, `game_id`, `rating`, `comment`, `created_at`; no user id, hidden rows left out); public
- GET /admin/feedback?include_hidden; PATCH /admin/feedback/{feedback_id}: `HiddenFlagIn` (`is_hidden`) -> `AdminFeedbackOut`; admin
- GET /admin/ratings?game_slug&include_hidden; PATCH /admin/ratings/{rating_id}: `HiddenFlagIn` -> `AdminRatingOut`; admin
- GET /admin/stats?hide_test -> `AdminStatsOut` (`total_users`, `total_saves`, `saves_by_game`); admin

**routes_email.py** (session): GET /users/me/email -> `email`; PUT /users/me/email: `EmailIn` (`email?`, null clears) -> `email`

**routes_admin_users.py** (admin): GET /admin/users?include_test -> list of `AdminUserOut` (`id`, `username`, `email`, `is_test`, `created_at`, `save_count`); PATCH /admin/users/{user_id}: `UserTestFlagIn` (`is_test`) -> `AdminUserOut`

**routes_stats.py** (public, read-only, groups smaller than `MIN_BUCKET` suppressed): GET /stats/games -> `min_bucket`, `games`; GET /stats/games/{game_id}; GET /stats/games/{game_id}/percentile?field&value -> `game_id`, `field`, `suppressed`, `min_bucket`, `count`, `percentile`; GET /stats/achievements -> `min_bucket`, `games`

**routes_leaderboards.py**: GET /leaderboards/{game_id}/{board} -> `game_id`, `board`, `label`, `order`, `entries`, `mine`; session?. PUT same path: `LeaderboardSubmit` (`score`, `detail?`) -> `accepted`, `improved`, `score`, `rank` (or `accepted`, `reason`); session. DELETE same path -> `removed`; session

**routes_scores.py**
- GET /leaderboard -> `boards`, `min_visible`, `top_n`; public
- GET /leaderboard/{game_id}/{board}?window&period -> `game_id`, `board`, `label`, `order`, `unit`, `windows`, `window`, `period`, `min_visible`, `suppressed`, `total`, `entries`, `mine`, `shows_username`; session?
- POST /scores: `ScoreSubmit` (`game`, `board`, `score`, `detail?`, `opt_in?`, `windows?`) -> `accepted`, `improved`, `results` (or `accepted`, `reason`); session
- DELETE /scores/{game_id}/{board} -> `removed`; GET /users/me/scores -> `scores`, `show_username`; DELETE /users/me/scores -> `removed`; session
- GET/PUT /users/me/leaderboard-privacy (`LeaderboardPrivacyIn`: `show_username`) -> `show_username`; session
- GET /admin/scores?game_id&board&window&period&include_hidden&limit -> list of `AdminScoreOut`; PATCH /admin/scores/{score_id}: `HiddenFlagIn` -> `AdminScoreOut`; admin

**routes_market_pools.py**: GET /market/prices -> `prices` (fetched from a public market site; tests never call it); GET /pools/{game_id}/{pool} and POST /pools/{game_id}/{pool}: `PoolContribution` (`amount`) -> pool summary; POST /stats/pageview -> `total`; all public, writes rate limited

**routes_account_data.py** (session): GET /users/me/export -> the account's whole data (`account_data.build_export`); DELETE /users/me: `DeleteAccountIn` (`confirm_username`) -> `deleted`, `removed`

**routes_admin_timeseries.py**: GET /admin/timeseries?days&hide_test; admin

**routes_votes.py**: PUT /whats-new/votes/{entry_id}: `HelpfulVoteIn` (`helpful`) -> `entry_id`, `helpful`; DELETE same path -> `entry_id`, `removed`; both session? (anonymous callers send header `X-Vote-Token`), limited per address. GET /admin/whats-new-votes?hide_test -> `entries`; admin

**routes_bug_reports.py**: POST /bug-reports: `BugReportIn` (`game_id`, `page?`, `note`, `schema_version?`, `browser?`, `viewport?`, `console_log?`, `attachment?`, `link_account?`) -> `id`, `received`; session?, rate limited per address. GET /admin/bug-reports?game_id&resolved&fixed&limit -> list of `BugReportAdminOut`; PATCH /admin/bug-reports/{report_id}: `BugReportPatch` (`resolved?`, `fixed?`, `note?`) -> `BugReportAdminOut`; admin

**ghosts.py** (`make_router`): POST /ghosts: `GhostPublish` (`game`, `scenario`, `hard?`, `series`, `opt_in?`); GET /ghosts/{game_id}/mine; DELETE /ghosts/{game_id}; session. GET /ghosts/{game_id}/peer?scenario&era&hard&exclude (session?). POST /ghosts/report: `GhostReportIn` (`game`, `ghost_id`, `reason?`) public. GET /admin/ghost-reports; POST /admin/ghost-reports/{report_id}/resolve; PUT /admin/ghosts/{ghost_id}/hidden: `GhostHideIn` (`hidden`); admin

**routes_profiles.py**: GET /users/me/profile; PUT /users/me/profile: `ProfilePut` (`is_public?`, `favourite_game?`, `progress?`, `event_badges?`); POST /users/me/profile/backfill -> `updated`, `profile`; all session (update brake per account). GET /profiles/{username} public (404 for both "no such account" and "not public")

### Models and tables (`models.py`)

`Rating`=ratings, `Save`=saves, `SaveSnapshot`=save_snapshots, `User`=users (`username`, `password_hash`, `settings_json`, `email`, `is_test`), `AuthSession`=auth_sessions (`user_id`, `token`; sessions never expire), `AnswerReport`=answer_reports, `Feedback`=feedback, `LeaderboardEntry`=leaderboard_entries, `PoolDay`=pool_days, `PageView`=pageviews, `OwnerNote`=owner_notes, `ScoreEntry`=score_entries, `ScoreProfile`=score_profiles, `HelpfulVote`=helpful_votes, `BugReport`=bug_reports, `UserProfile`=user_profiles, `GhostSeries`=ghost_series, `GhostReport`=ghost_reports. Passwords are never stored: only `password_hash` (`salt$digest`).

### Test conventions (`tests/`)

- `conftest.py` sets `DATABASE_URL=sqlite:///:memory:` (one shared in-memory database through `StaticPool`; the tables are created when `database` is imported), `ADMIN_TOKEN=test-admin-token`, `AI_ADMIN_TOKEN=test-ai-token`, `OWNER_SIGNUP_ALLOWED=1`, puts `app/` on `sys.path`, and resets the per-address write limiters before every test. Data is **not** cleared between tests: use fresh game ids, usernames and keys per test.
- A test file starts `from fastapi.testclient import TestClient`, `from main import app`, `client = TestClient(app)`.
- Admin calls: `headers={"X-Admin-Token": "test-admin-token"}` (`conftest.ADMIN_HEADERS`).
- Make an account: `client.post("/auth/signup", json={"username": "somename", "password": "pw"})`, take `bearer_token` from the reply, then `headers={"Authorization": f"Bearer {token}"}`. Or insert directly: `from database import SessionLocal; from models import User, AuthSession` then `db.add(User(username=..., password_hash="x"))` and an `AuthSession(user_id=user.id, token="a-test-token")` (see `make_user` in `tests/test_snapshots.py`). The owner account is the one named `noyvj`.
- Throttles: reset a limiter between tests with `.reset()`; replace one with `monkeypatch.setattr(<module that uses it>, "X_LIMITER", FailureLimiter(max_failures=3, window_seconds=3600))`.
- Assert on status code AND on the response fields; also test the failure paths (401 without a token, 403 for a non-owner, 422 for a bad body).
- Python 3.9 syntax only (no `X | Y` types, no `match`), because the tests run under 3.9 while production is 3.12.

### Do not

1. Never connect to, read from or write to a real database (Neon). Tests use sqlite only; never set `DATABASE_URL` to anything else, never run a script against production.
2. Never print, log, commit or paste a token, password, `ADMIN_TOKEN` value or bearer token (test values like `test-admin-token` are fine).
3. No schema change without Claude: do not add, rename or retype a table or column in `models.py`. Neon has no migrations, so a new column needs a manual `ALTER TABLE` step (`database.patch_schema`) that only the main session does. Report what you need.
4. No new dependency (no new `import` of a package outside the standard library, fastapi, pydantic, sqlalchemy and the files here).
5. No new route that returns another player's private data (email, save data, user ids, username next to a score unless the player opted in). Public read routes return aggregates or opt-in data only.
6. Keep Python 3.9-compatible syntax.
7. Never edit `pyproject.toml`, `requirements-dev.txt` or any deployment file; if a new module or package is needed, say so in the report.
8. Do not delete, rename or reorder a route, and do not weaken `tests/test_routes_unchanged.py` or `tests/test_file_sizes.py` to make a change pass. Keep every file under 14,000 estimated tokens; if one gets close, ask for a split.
