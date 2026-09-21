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

## 6. Multiplayer scoping (2026-09-21)

Scoping only (TODO.md R2-multiplayer); nothing here is built. Sources: your "full multiplayer pass soon" (Canopy B5) and "next big development after this set" (Continuum K30), the parked items in `LATER.md` (B5, D25, E11, K30; E9 and F7 build-outs), and the async/seed/ghost/leaderboard ideas in `IMPROVEMENT-IDEAS-ROUND-3.md` section Z. Most of those ideas already converge on one stack: a shared seeded-run module, run/ghost codes, and opt-in boards.

### 6.1 What "multiplayer" can mean here (tiered)

Current facts: static GitHub Pages front end, games are client-side Pyodide, one FastAPI app with request/response endpoints on FastAPI Cloud, Neon Postgres, username+password accounts with a bearer token, an in-process (per-instance, reset-on-restart) rate limiter, and read-only cached `/stats/*`.

| Tier | Meaning | Backend needs | Ops burden (solo) |
|------|---------|---------------|-------------------|
| 0 | Aggregate-only: "you vs. all players" percentiles, achievement rarity. **Built (section 5).** | Nothing new | Done |
| 1 | Async social: community comparison strips, seeded daily/weekly runs, challenge links, ghost traces, opt-in leaderboards, shared holiday-week events | 3-4 new tables, ~8 small endpoints, one shared JS+Python module. Same request/response model as today | Low. No new services. Main cost is abuse handling |
| 2 | Async shared world: regional pools (Tide shared coastline), mutual-aid pools (Aftermath E11), co-op "world code" with one turn per day | Tier 1 plus server-side merge logic with concurrency control (row locks or optimistic version) | Medium. Shared mutable state means bad data can hurt everyone; needs caps, decay and an admin reset |
| 3 | Real-time: live rooms, WebSockets, presence | Persistent connections, room state in memory or Redis, reconnection handling | High. See caveat below |

Platform caveats (unverified, listed as open question Q4, not asserted): whether FastAPI Cloud supports long-lived WebSocket connections, how many instances it runs (the current rate limiter and the stats cache are per-process, so they weaken if it scales out), cold-start behaviour, and Neon connection limits and idle-suspend latency. Verify each before committing to Tier 2 concurrency or Tier 3. Neon itself has no pub/sub beyond Postgres LISTEN/NOTIFY, and a serverless-style Postgres is a poor fit for chatty real-time writes.

**Recommendation:** build Tier 1 completely, then Tier 2 for exactly two pilots (Tide, Aftermath). Defer Tier 3 unless you answer Q3 with a clear "yes"; nothing on the parked list needs it. Every parked item (B5, D25, E9, E11, F7, K30) is Tier 1 or 2. Tier 1 also fits the "friends aren't truthful" concern better than any live mode, since you can label everything "for fun, unverified" without ever pretending to referee.

### 6.2 Trust model

Every value the client submits is untrusted: the Python runs in the player's own browser and can be edited in devtools. The plan is to make cheating boring and low-stakes, not impossible.

1. **No stakes.** No prizes, no cash, nothing that unlocks gameplay power from rank alone. Boards are labelled "for fun, self-reported unless marked verified".
2. **Whitelist plus sanity bounds.** Extend the `stats.STATS_FIELDS` pattern into a per-game `SCORE_BOARDS` registry: board name, score field, min/max, and a max-plausible-rate check (score per elapsed ticks). Out-of-range submissions are rejected (422), not clamped.
3. **Verified tier where the game is deterministic.** Seeded runs submit `{seed, inputs[], claimed_score}`. The server (or an admin batch) re-runs a headless copy of the game logic; a match marks the row "verified". Which games can do this is uncertain: it needs game logic importable without the DOM, and RNG routed through the shared seed module. Unverified rows are still shown, in a separate lane. Treat verification as a milestone-6 stretch, not a launch requirement (Q5).
4. **Rate limits.** Move from the in-process dict to a DB-backed count (per user per board per day, per IP per hour) so it survives restarts and multiple instances. One scored submission per user per board per seed; a better result replaces it.
5. **Identity and display.** Rows are anonymous by default ("Player 7F2Q", a hash of user id plus board salt). Showing the username is a single account setting, off by default, with a one-click "hide me and delete my rows". Anonymous save codes cannot post to boards: a submission needs an account (accounts already exist and cost the player nothing).
6. **Moderation.** Usernames are free text today, so displayed names need a blocklist check at opt-in and a report button on every row that writes to the existing feedback/report tables; the admin page (`admin.html`) gets a "hide row / ban name" action. Free-text player content (chat, notes, care packages) is a non-goal (section 6.6) because it is the main moderation cost.
7. **Privacy.** Aggregates keep `MIN_BUCKET = 3` suppression. Anything naming an individual is opt-in, exportable and deletable, and the deletion path must cover new tables (extend account delete when it exists; note there is currently no account-delete endpoint, which is a prerequisite: Q7). Pool and region features publish only sums and counts, never per-contributor rows.
8. **Poisoning.** Shared pools (Tier 2) cap per-user contribution per day, ignore values beyond a plausible per-turn maximum, and decay toward a baseline so a single griefer cannot permanently damage a region.

### 6.3 Per-game feature map

| Game | Best 1-2 features | Tier | Shared pieces needed |
|------|-------------------|------|----------------------|
| SOL | Daily/weekly "Scarcity Run" seed board; speedrun leaderboard (time to terraform, existing A2/A13 challenge runs) | 1 | seed module, `/scores`, daily-seed feed, verification (SOL is deterministic-friendly) |
| Canopy | B5: forest standing value vs. site aggregate (percentile strip, uses existing `/percentile`); daily seeded forest with a holiday-week event (Z23b badges) | 0-1 | comparison widget, event feed |
| Grid | Daily seeded grid with ghost trend line; ghost replay codes (round-by-round clean share) | 1 | seed module, trace recorder/ghost overlay, share code |
| Tide | D25: shared-coastline cooperative stat (players' saved rows pooled per region, a regional "coast held" meter); daily Tide seed | 2 (pilot) then 1 | pools table, contribution cap, seed module |
| Aftermath | E11: mutual-aid network (sums of aid actions across players unlock a positive event); E9 holiday events via the event feed | 2 (pilot) and 1 | pools table, event feed, aggregate-only reads |
| Herd | F7: community farm comparison (percentile of dollars-and-methane against the community); "Ranch of the Week" seed board | 0-1 | comparison widget, seed module, weekly feed |
| Thaw | "Cold Case" daily seed with community percentile; hold-the-line survival leaderboard | 1 | seed module, `/scores` |
| Loop | Daily/weekly seed (reuses the deterministic featured-category logic); ghost run code for the supply-fraction graph | 1 | seed module, ghost code |
| Drift | Weekly Region Challenge seed; mentor ghost from your own past run first, imported friend ghost second | 1 | seed module, ghost code |
| Trade Empire | Blackout Challenge seeded run with an opt-in board; shared market-price index as an aggregate (everyone's trade volume nudges regional prices, read-only) | 1 then 2 | `/scores`, optional pool |
| Continuum | K30: peer-city ghost as an opt-in "compare" panel (median-city trace from aggregates, never a raw individual city by default); daily seed with a par score | 1 | trace recorder, aggregate trace endpoint, seed module |
| Le Champ de Mots | L12 classmate farm visits: read-only snapshot by share code plus a "5 hard words" challenge set; class leaderboard (streak/reviews, opt-in) | 1-2 | snapshot table, share codes, `/scores` |

Continuum K30 confusion concern: ship it off by default as a small labelled panel ("median city at the same year") rather than an overlay on the main view, and playtest it in milestone 3 before wiring it to real ghosts.

### 6.4 Shared backend, contracts, and milestones

**New tables** (SQLAlchemy in `app/models.py`, tests on sqlite as today): `score_entries` (id, user_id, game_id, board, seed, score, meta JSON, verified bool, hidden bool, created_at; unique on user+board+seed), `challenges` (code, game_id, seed, creator_user_id, creator_score, created_at, expires_at), `traces` (score_entry_id, compact per-turn array, size-capped), `pools` (game_id, pool_key, period, value, contributor_count, updated_at) plus `pool_contributions` (one per user per period, for caps), `events` (slug, game_id or null, starts_at, ends_at, config JSON; admin-authored, also readable as a static JSON fallback), `user_settings` (user_id, show_username, board_opt_in).

**Endpoints** (all auth by the existing bearer token): `GET /seed/{game}/{daily|weekly}` (or computed client-side from the UTC date, with the server only recording it), `POST /scores`, `GET /leaderboard/{game}/{board}`, `DELETE /scores/me/{game}`, `POST /challenges` and `GET /challenges/{code}`, `GET /traces/{score_id}` and `GET /stats/games/{id}/trace` (median trace, with suppression), `GET /events/active`, `POST /pools/{game}/contribute` and `GET /pools/{game}/{key}`, `PATCH /users/me/settings`.

**Shared JS/Python modules** (dropped unchanged into every game, same as `save-widget.js`): `shared/seed.py` plus `shared/seed.js` (string seed to PRNG, date-to-seed helper; every game routes randomness through it), `shared/mp-client.js` (the client SDK: `mpSubmitScore`, `mpLeaderboard`, `mpChallenge`, `mpGhost`, `mpEvent`, built on `hubAuthHeaders()` from `hub-auth.js`, degrades silently when offline or signed out), `shared/trace.py` (compact per-turn recorder), `shared/ghost-overlay.js`, and a small `shared/mp-panel.js` UI (board table, "copy challenge link", opt-in toggle).

**Seeded-run contract:** a run declares `{game, mode, seed, version, inputs}`. `version` is the game's content version; boards are partitioned by it so a balance change never mixes old and new scores. Daily seed = hash(game + UTC date). All randomness comes from the seed-derived PRNG only.

**Submission/verification contract:** `POST /scores {game, board, seed, version, score, meta, trace?, inputs?}`; the server validates against `SCORE_BOARDS`, applies rate limits, upserts best-only, and returns rank plus percentile. `verified` is set only by the replay checker.

**Milestones** (each demonstrable end to end):
1. **Seed and share, no backend.** `shared/seed`, "Copy result as text", seed field on start screens; pilot in SOL and Tide. Demo: two browsers replay the same seed identically.
2. **Comparison strips (Tier 0 to UI).** `mp-panel` percentile widget; Canopy B5 and Herd F7 ship. Demo: forest value vs. site median on a live save.
3. **Scores and boards.** `score_entries`, `/scores`, `/leaderboard`, opt-in settings, delete-my-rows, admin hide; pilot one board each on SOL and Thaw. Demo: submit, appear anonymously, toggle name, delete.
4. **Challenge links and ghosts.** `challenges`, `traces`, `ghost-overlay`; Grid and Drift ghosts, then Continuum K30 median-city panel. Demo: friend opens a link and sees "beat 4,210" with a faint line.
5. **Events feed.** `events` table plus the hub "Today" strip; Canopy and Aftermath holiday weeks (E9), earned badges into Z23b. Demo: admin schedules a week-long event with no redeploy.
6. **Pools (Tier 2 pilot).** `pools`, contribution caps, decay; Tide D25 shared coastline and Aftermath E11 mutual aid. Demo: several accounts move one regional meter; a cap test blocks a spammer.
7. **Verification (stretch).** Headless replay checker for SOL/Loop, "verified" lane. Demo: an edited-score submission is flagged.
8. **Rollout.** Remaining games' daily/weekly seeds, hub `leaderboards.html`, docs and log entries. Real-time only if Q3 is a clear yes, as a separate scoping doc.

### 6.5 Risks

- **Solo-maintainer load:** abuse reports and name moderation grow with players. Mitigated by anonymity by default and no free text, not eliminated.
- **Open-write API:** the current API already lets anyone POST saves and skew stats; boards raise the incentive. Bounds and verification reduce, never remove.
- **Neon/FastAPI Cloud limits and cost** (unverified): connection caps, idle-suspend latency and instance count could bite once traffic is real. Add basic timing logs in milestone 3.
- **Per-process state:** the rate limiter and stats cache assume a single instance; milestone 3 must move limits to the DB.
- **Balance versions:** every game patch splits its boards; needs the `version` field from day one.
- **Assessment framing:** BCM206 evidence favours a documented, working, modest system over a large one. Cut scope by milestone, not by half-building all of them.

### 6.6 Non-goals

Real money, prizes or wagers; free-text chat or player-authored public text; friend lists and direct messages (share links cover it); real-time play in the first pass; anti-cheat beyond bounds and replay checks; any ranking presented as authoritative; email or third-party login (still deferred).

### 6.7 Open questions for you

1. **Games first?** Suggested pilots: SOL and Tide (seeded and deterministic-friendly, a pool candidate), then Aftermath. Or pick your own three.
2. **Should leaderboards exist at all?** You worried that friends are not exactly truthful about reviews. Options: (a) no boards, only seeds, ghosts and percentile strips; (b) opt-in "for fun" boards; (c) boards only for verified runs. Recommended: (b), with (c) later.
3. **Appetite for real-time?** Recommended answer: not in this pass. Say yes only if you have a specific live mode in mind; it changes the hosting question.
4. **May I verify the platform?** Checking FastAPI Cloud's WebSocket support, instance scaling, limits and pricing, plus Neon's plan limits, needs your dashboards or accounts (add to FOR-YOU.md when we start).
5. **Is verified replay worth the effort?** It forces headless, seed-only game logic in each game. Alternative: bounds-only and "unverified" labels everywhere.
6. **Identity/username policy:** anonymous "Player 7F2Q" by default with opt-in username display, or usernames always shown? Any name restrictions (blocklist, length, no display for first N days)?
7. **Account deletion:** none exists today; multiplayer needs "delete my account and all rows". Build it as milestone 3 groundwork?
8. **Events and holidays:** who authors them (you, via an admin form, or a static JSON in the repo), and which dates matter (Christmas is the one you named)?
9. **Tone for Tier 2:** should shared-pool features be cooperative-only (Tide coastline, Aftermath mutual aid) with no competitive framing, as your parked wording suggests?
