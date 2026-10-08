# Multiplayer scoping (Round 3 R-39, W-6)

**Purpose.** You said multiplayer is likely the next big development and asked for a scoping document as the first step. This does not build anything. It lists what the site already has, what each parked or wanted item actually needs, the smallest sensible phases, and the decisions that are yours.

Written 2026-09-27 from the code as it stands (FastAPI on FastAPI Cloud, Neon Postgres, GitHub Pages front end, no websockets).

---

## 1. What already exists (the "multiplayer-lite" layer)

| Piece | What it does | Where |
|---|---|---|
| Accounts | Username and password, bearer-token sessions, optional email, test-account flag | `app/main.py` |
| Cloud saves | One JSON save per (game, slot), three slots for signed-in players | `/saves`, `/users/me/saves` |
| Aggregate stats (Z1) | Anonymous per-game means, percentiles and achievement rarity, hidden below 3 saves | `app/stats.py` |
| Opt-in leaderboards | One best score per account per board, public username and score only | `app/leaderboards.py`, `shared/leaderboard.js` |
| Community pools | Anonymous per-day totals everyone adds to (Loop's recycling pool; Canopy's community plot next) | `app/pools.py`, `shared/community-pool.js` |
| Community index lines | A sentence built from the stats (Aftermath, Drift, Tide) | `shared/community-index.js` |
| Throttling | Login and save-code guessing are rate limited | `app/throttle.py` |

Everything above is **asynchronous and aggregate**: nobody plays at the same time as anybody else, and nothing a player does is visible to one specific other player.

## 2. What the parked and wanted items need

| Item | Shape | Needs beyond §1 |
|---|---|---|
| Canopy community plot and "best day" (GB-19) | Shared counter with a daily record and an opt-in contributor leaderboard | Nothing new: pools (built) plus leaderboards |
| Tide D25 shared coastline stat | Aggregate stat across players | Nothing new: a derived save field and a community-index line |
| Aftermath E11 mutual-aid network positive event | A player's preparedness helps others | Either an aggregate (players' average resilience raises everyone's chance of the event: no new backend) or a real gift between accounts (new) |
| Continuum K30 "peer city" ghost overlay | Show another player's city trajectory beside yours | A way to fetch one anonymous other save's per-season series: new read-only endpoint over stored saves, opt-in publishing |
| Canopy GB-12 rival logging company as a 1v1 mode | Two players, one contested map | Real two-player sessions: new (see §3, level 3) |
| Last Line and Signal leaderboards | Best wave, daily score | Leaderboards (built) plus a daily-board variant |
| Daily/weekly community events (N) | Same event for everyone | Nothing: dates are computed client-side |

## 3. The four levels of "multiplayer" and what each costs

1. **Aggregate and opt-in public boards** (done). No new risk; keep adding boards and pools.
2. **Asynchronous ghosts and gifts**: play against a recorded trajectory or receive a small bonus from another account. Needs: an opt-in "publish my run" flag, a table of published run summaries (per-round series, not raw saves), a read endpoint that returns one at random within a difficulty band, and a moderation story (report button, admin hide). No live connection. Suitable for Continuum's peer city, Aftermath's mutual aid, Grid's twin against a real player.
3. **Turn-based two-player over polling**: two players alternate turns; the server stores the match state and each client polls every few seconds. Suitable for Heist Committee, Last Line or Canopy's rival mode if turn based. Needs: a matches table, invite links, turn validation on the server (the game logic is Python in the browser, so the server either trusts the client or re-runs the rules: re-running needs the game logic importable server side), a forfeit/timeout rule. Cost: moderate, no websockets.
4. **Real-time**: websockets or server-sent events, presence, latency handling. FastAPI supports it but FastAPI Cloud's limits on long connections and the Pyodide clients make this the most expensive level. Recommendation: do not start here.

## 4. The hard parts (independent of level)

- **Trust.** Every score and run summary is client supplied; a determined player can post anything. Options: accept that (friendly boards), or replay-verify (level 3 could verify by re-running the deterministic simulation, which is why deterministic games with seeds are the best fit: Signal, Last Line, Canopy's seeded daily forest).
- **Identity and privacy.** Only the public username ever appears. Anything shared publicly must be opt-in and removable. Personal-data games (Undersleep) must never be published.
- **Moderation.** Usernames on boards and any free text (nicknames, forest names) need a report button and an admin hide, plus a small blocklist. The admin page already has a lock; a moderation panel would extend it.
- **Abuse limits.** Rate limits exist for pools, feedback, login and save codes; every new write endpoint needs the same treatment (cap per request, per-address limit).
- **Cost and limits.** Neon and FastAPI Cloud free tiers: keep rows small and queries cheap (pools store one row per day; boards one row per account).
- **Testing.** Level 2 and 3 need a fake clock and fake second player in the pytest suite; the existing backend suite already runs on sqlite.

## 5. Suggested phases

1. **Now (in the Round 3 list):** Canopy community plot on pools, Signal and Last Line boards, event badges. Zero new infrastructure.
2. **Next:** one level-2 feature as a pilot, Continuum's peer-city ghost (the parked K30), because Continuum already keeps a per-season history and has the most to gain. Deliver: opt-in publishing, a summary table, one read endpoint, a report button.
3. **Then:** a level-3 pilot on the smallest deterministic turn-based game (Heist Committee or Last Line once built): invite link, polling, server-side rule check.
4. **Only if wanted:** real-time.

## 6. Decisions that are yours

1. Do you want any level above 1 at all this round, or keep everything aggregate and opt-in?
2. If level 2: is publishing a run summary under your public username acceptable, or must ghosts be anonymous?
3. If level 3: are two-player games friend-only (invite link) or open matchmaking? (Friend-only is far safer and cheaper.)
4. Do you accept client-trusted scores, or do you want replay verification for deterministic games?
5. Who moderates? (Today only you, through the admin page.)

## 7. What I will do without asking

Keep building level-1 features (boards, pools, aggregates), keep every new endpoint capped and rate limited, and keep all publishing opt-in. Nothing at level 2 or above is started until you answer §6.

## 8. Decisions so far (the user, 2026-10-07)

1. Which level of multiplayer this round: the assistant's call.
2. Ghosts and run summaries: opt-in only.
3. Two-player games: the player chooses friend-only or open, with friend-only recommended in the interface. (Round 2 also answered "later, I want to do a full multiplayer pass soon" on the Round 2 multiplayer item.)
4. Client-trusted scores versus replay verification: the user is unsure; my recommendation is client-trusted for now, verification only where cheating would matter (asked again in FOR-YOU 5).
5. Moderation: the user for now, and the assistant too if that can be made possible (an admin-token read of reports, never silent deletion).


**Decided 2026-10-08 (you said "go with that"):** scores stay client-trusted for now; replay verification is added only for a game where cheating would matter (Signal and Last Line are the candidates, later).
