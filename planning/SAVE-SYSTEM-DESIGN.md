# Save System Design — Game Hub

Design doc for save functionality + accounts across the game hub. Written against the existing stack: Neon (Postgres 17, currently Auth off), FastAPI Cloud, static GitHub Pages front end, Pyodide-run Python games.

Status: **draft — not yet built.** Use this as the spec Claude Code implements against, and update it in place as decisions change (this file evolves; `BCM206-DEV-LOG.md` records *when* and *why* it changed).

---

## 1. Scope decision

You listed "save functions and accounts" together, but they're two separate features with very different build costs. Recommend splitting into two phases so accounts don't block saving from shipping:

- **Phase 1 — Save codes (no real accounts).** Each save generates a short code (e.g. `SOL-4X7K-9QPZ`). Enter the code on any device to restore progress. No login, no password, no email required. This is the MVP and is enough to satisfy "public, working save system."
- **Phase 2 — Accounts (stretch, "if I have time").** Layer real accounts on top of the same save records later, without needing to redesign the schema — see §4.

This split also gives you a natural two-part Operation chain for the Skill Journal / Infrastructure Design report: build → test save codes, then (if time allows) build → test accounts on top.

## 2. Database schema (Neon / Postgres)

```sql
-- Phase 1
create table saves (
  id            uuid primary key default gen_random_uuid(),
  save_code     text unique not null,        -- short human-entered code
  game_id       text not null,               -- e.g. 'sol', 'grid', 'canopy'
  save_data     jsonb not null,               -- serialized game state
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);

create index on saves (save_code);
create index on saves (game_id);

-- Phase 2 (add later, don't build yet)
create table users (
  id            uuid primary key default gen_random_uuid(),
  email         text unique,
  created_at    timestamptz not null default now()
);

alter table saves add column user_id uuid references users(id);
```

## 3. API (FastAPI)

Phase 1 only, three endpoints:

| Method | Path                  | Purpose                                  |
|--------|-----------------------|-------------------------------------------|
| POST   | `/saves`               | Create a save, returns a new `save_code`  |
| GET    | `/saves/{save_code}`   | Fetch save data to restore progress       |
| PUT    | `/saves/{save_code}`   | Overwrite save data (autosave/manual save)|

Save code generation: 8-10 chars, unambiguous alphabet (no `0/O`, `1/I/l`), grouped for readability (`XXXX-XXXX`). Collision check on insert; regenerate on collision.

## 4. Phase 2 — accounts (later)

When you get to it: email-only "magic link" auth (no passwords to manage) is the lowest-effort option that still counts as real accounts. On login, look up `saves` by `user_id` instead of by code. Existing save-code saves can be "claimed" by a logged-in user (adds `user_id` to an existing row) so nobody loses progress from Phase 1.

## 5. Browser ↔ Pyodide ↔ API flow

1. Game running in Pyodide holds state as a Python dict/object.
2. On save trigger, serialize state to JSON (`json.dumps` from Pyodide, passed to JS via `pyodide.toJs` / a small JS bridge).
3. JS does the `fetch()` call to the FastAPI endpoint (this is the one approved JS-in-the-loop moment beyond the Tide exception — flag this to the 206 marker as a deliberate infra decision, since it's a genuine case where Python-in-browser needs a JS bridge to talk to an external API).
4. On load, reverse the flow: fetch save data, pass into Pyodide, deserialize into game state.

## 6. What to log in BCM206-DEV-LOG.md as this gets built

Each work session against this doc should produce one log entry: what part of this spec you attempted, what worked, what you had to change from the spec (and why — that's your adaptation evidence), and what's still open. Update this doc's schema/API sections in place if reality diverges from the plan; don't let the log and the spec disagree.
