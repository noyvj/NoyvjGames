# Accounts & Feedback Design — Game Hub

Companion doc to `SAVE-SYSTEM-DESIGN.md` — this covers Phase 2 (real accounts, linked to the existing save-code system) plus a new feature: site-wide feedback. Same stack assumptions: Neon (Postgres 17), FastAPI Cloud, static GitHub Pages front end, Pyodide games.

Status: **Backend + frontend built and tested — 2026-08-19, auth redesigned same day.** Accounts, save-claim, and feedback all live in `app/main.py` / `app/models.py`, covered by `app/tests/test_accounts.py` and `app/tests/test_feedback.py`. **Auth approach is no longer this doc's §1 (magic link, email-only)** — that needed an email provider/API key as a separate, out-of-scope decision, so it was replaced with **username + password**, no email at all: `POST /auth/signup` and `POST /auth/login`, passwords hashed with salted PBKDF2-HMAC-SHA256 (stdlib only, no new dependency), no complexity rules enforced (the frontend shows an advisory hint instead). The `AuthSession` bearer-token table is unchanged by this swap — it never cared how identity was proven. **Real consequence of dropping email: there is no automated password-reset path.** A forgotten password permanently strands that account's claimed saves/feedback unless you personally intervene. **Decided 2026-09-15: admin-assisted manual reset, not an email provider.** No new code or service needed — if a user forgets their password, the fix is a direct update to their row in the Neon database (their `password_hash` column) by whoever has DB access, i.e. you. Reasonable at this site's current scale; revisit only if that becomes a real, recurring burden. Frontend: the hub (`index.html`/`script.js`) has the sign-up/sign-in box and a general feedback widget; SOL (`games/sol/index.html`) is the claim-step reference integration, same role it played for `SAVE-SYSTEM-DESIGN.md` Phase 1. **Deployment note (clarified 2026-09-15):** the real FastAPI Cloud instance auto-deploys on every push to this repo's GitHub remote — there's no separate manual deploy step. This backend code is tested locally but, as of this note, this repo's commits haven't been pushed to GitHub yet this session, so it isn't live on the real site yet. See `BCM206-DEV-LOG.md` for the build session.

---

## 1. Accounts (realizes Phase 2 from SAVE-SYSTEM-DESIGN.md)

**Auth approach: magic link, email-only.** No passwords to store, hash, or reset — you send a one-time link, they click it, they're logged in. Lowest-effort option that still counts as a real account system for the DA.

### Schema

```sql
create table users (
  id            uuid primary key default gen_random_uuid(),
  email         text unique not null,
  created_at    timestamptz not null default now()
);

create table auth_tokens (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid not null references users(id),
  token         text unique not null,
  expires_at    timestamptz not null,   -- suggest 15 min expiry
  used          boolean not null default false
);

-- from SAVE-SYSTEM-DESIGN.md, now put to use:
-- alter table saves add column user_id uuid references users(id);
```

### Flow

1. `POST /auth/request-link {email}` — creates or finds the user, generates a token, emails a link containing it (e.g. via Resend or similar — needs its own API key, separate decision).
2. User clicks the link → hits `GET /auth/verify?token=...` → token checked (unexpired, unused), marked used, returns a bearer token.
3. **Session storage:** since this is a static GitHub Pages front end talking to a separate FastAPI origin, cookies get messy (cross-origin, SameSite issues). Store the bearer token in the browser's `localStorage` instead and send it as an `Authorization: Bearer` header on subsequent requests. Simpler, no CORS cookie fighting.

### Linking to saves

- `POST /saves/{save_code}/claim` (authenticated) — attaches the logged-in `user_id` to an existing save-code row. This is how someone who started anonymously keeps their progress after making an account — nobody loses a save by signing up.
- `GET /users/me/saves` (authenticated) — lists all saves tied to the logged-in user, across games.

## 2. Site-wide feedback

One feedback system, usable two ways: attached to a specific game (rating + comment on that game) or general site feedback (not tied to any one game — e.g. "the save system is confusing").

### Schema

```sql
create table feedback (
  id            uuid primary key default gen_random_uuid(),
  game_id       text,                          -- null = general site feedback
  user_id       uuid references users(id),      -- nullable: anonymous feedback allowed
  rating        smallint check (rating between 1 and 5),  -- nullable: comment-only is fine
  comment       text,
  is_hidden     boolean not null default false, -- manual moderation flag
  created_at    timestamptz not null default now()
);

create index on feedback (game_id);
```

Require at least one of `rating` or `comment` at the API level — don't allow fully empty submissions.

### API

| Method | Path                    | Purpose                                          |
|--------|--------------------------|---------------------------------------------------|
| POST   | `/feedback`               | Submit feedback (game-specific or general)         |
| GET    | `/feedback?game_id=X`     | Public feedback for one game (excludes hidden)     |
| GET    | `/feedback`                | General site feedback, no `game_id` filter (excludes hidden) |

### Moderation — keep it minimal for now

This is public-facing user-generated content, so it needs *some* abuse protection, but full moderation tooling is its own project. MVP approach:
- Rate-limit `POST /feedback` per IP (e.g. 5/hour) to blunt spam.
- `is_hidden` flag lets you hand-hide a bad entry via a direct DB edit — no admin UI needed yet. Build a real moderation view only if it becomes an actual problem.

## 3. How the three systems connect

`users` is the hub: `saves.user_id` and `feedback.user_id` both point back to it. A logged-in user's identity is what threads their progress and their feedback together across every game on the hub — which is itself a small, reportable instance of a networked-system design decision if you want a BCM206 contextualisation angle here (a single identity node connecting activity across the platform, rather than siloed per-game state).

## 4. Suggested build order

1. Accounts (magic link + `users` + `auth_tokens`) — nothing else depends on this working first except the *claim* step.
2. Save-claim endpoint — wire accounts into the existing save system.
3. Feedback (general site feedback first, since it needs no auth; game-specific filtering is a one-line addition once general works).

Log each stage in `BCM206-DEV-LOG.md` as you go, same as the save system.

## 5. Cross-game aggregate stats (TODO.md Z1)

Read-only, public, cache-friendly endpoints over the existing `saves` table — **zero per-game backend changes**. Code: `app/stats.py` (pure helpers + the per-game whitelist) and the `/stats/*` block at the end of `app/main.py`.

| Path | Returns |
|------|---------|
| `GET /stats/games` | the whitelist: game id -> opted-in numeric field paths, plus `min_bucket` |
| `GET /stats/games/{game_id}` | `save_count`, `achievements` (`earned_pct` + `earned_count` per id, denominator = that game's saves), `fields` (per whitelisted path: `count`, `mean`, `p10/25/50/75/90`) |
| `GET /stats/games/{game_id}/percentile?field=..&value=..` | mid-rank percentile (0-100) of a submitted value among that game's saves (ties count half) |
| `GET /stats/achievements` | every game's achievement rarity in one call (hub dashboard, the "% of players who have this" figure) |

**What counts as a "player":** a save row. Anonymous save codes and account-linked saves are both included; one person with several saves counts several times. This is an accepted approximation, and it means an attacker can skew stats by POSTing saves (same open-write posture as the rest of the API).

**Privacy rules (enforced in `stats.py`):** any bucket built from fewer than `MIN_BUCKET = 3` saves is suppressed — the whole game, each achievement (earned by <3 saves is dropped and only counted in `achievements_suppressed_count`), each numeric field, and the percentile endpoint (`suppressed: true`, `percentile: null`). No min/max is ever returned. Only whitelisted numeric leaf fields are read; achievement ids must match `^[a-z0-9_]{1,64}$`; nothing string-valued from a save, no usernames, no `user_id`, no save codes appear in any response.

**Opting a field in:** add its top-level key (or dotted path, e.g. `region.temperature`, `current_state.city.population`) to that game's tuple in `stats.STATS_FIELDS`; non-numeric, bool, NaN/Infinity or missing values are skipped per save. Unknown game or non-whitelisted field -> 404; non-finite `value` -> 422.

**Performance:** one `SELECT save_data WHERE game_id=?` (newest `MAX_SAVES_SCANNED = 5000`), decoded in Python (opaque JSON cannot be safely cast in portable SQL), with a 60 s in-process cache per game and `Cache-Control: public, max-age=300`. Revisit (SQL JSON aggregation or a materialised table) only if a game's save count grows into the tens of thousands.

**Known gap for dependents:** stats are current-state snapshots, not per-run history — features needing "best ever" or per-era comparisons (Continuum benchmark, SOL leaderboard) should first opt in a suitable field, and any true leaderboard would need an explicit opt-in submission endpoint (deliberately not built here).
