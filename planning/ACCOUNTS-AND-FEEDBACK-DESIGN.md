# Accounts & Feedback Design — Game Hub

Companion doc to `SAVE-SYSTEM-DESIGN.md` — this covers Phase 2 (real accounts, linked to the existing save-code system) plus a new feature: site-wide feedback. Same stack assumptions: Neon (Postgres 17), FastAPI Cloud, static GitHub Pages front end, Pyodide games.

Status: **Backend + frontend built and tested — 2026-08-19, auth redesigned same day.** Accounts, save-claim, and feedback all live in `app/main.py` / `app/models.py`, covered by `app/tests/test_accounts.py` and `app/tests/test_feedback.py`. **Auth approach is no longer this doc's §1 (magic link, email-only)** — that needed an email provider/API key as a separate, out-of-scope decision, so it was replaced with **username + password**, no email at all: `POST /auth/signup` and `POST /auth/login`, passwords hashed with salted PBKDF2-HMAC-SHA256 (stdlib only, no new dependency), no complexity rules enforced (the frontend shows an advisory hint instead). The `AuthSession` bearer-token table is unchanged by this swap — it never cared how identity was proven. **Real consequence of dropping email: there is no password-reset path.** A forgotten password permanently strands that account's claimed saves/feedback; email-based recovery is deferred, not solved, by this design. Frontend: the hub (`index.html`/`script.js`) has the sign-up/sign-in box and a general feedback widget; SOL (`games/sol/index.html`) is the claim-step reference integration, same role it played for `SAVE-SYSTEM-DESIGN.md` Phase 1. **Not yet deployed to production** — this is all live and tested against a local backend only; the real FastAPI Cloud instance still needs the code pushed/deployed before any of this works on the live site. See `BCM206-DEV-LOG.md` for the build session.

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
