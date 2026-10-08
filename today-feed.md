# today.json: the weekly challenge feed

`today.json` (repo root) is the one admin-edited file behind the hub's **Today** strip (`hub-today.js`, TODO Y-2). Edit it by hand and push; there is no build step. The strip also shows things that need no feed: whether today's Signal puzzle is done, your daily streak (both read from this browser's own records) and the seasonal event on today (from `shared/seasonal-events.js`, `shared/seasonal-dates.json` and `events.json`).

The file shipped with the feature is a **sample** (`"sample": true`): the strip labels it as one. Replace the entries and set `"sample": false` (or delete it) when you publish a real schedule. Only use things the games really have: a challenge is a suggestion the player tries by themselves, nothing checks it, so the strip offers an "I did this one" tick that is the player's own and is stored on their device only.

```json
{
  "version": 1,
  "sample": false,
  "updated": "2026-10-08",
  "note": "Shown nowhere, for you.",
  "repeat": true,
  "daily": [ { "game": "signal", "label": "Signal daily puzzle" } ],
  "weekly": [
    { "start": "2026-10-05", "game": "herd", "title": "Herd: decouple within 12 rounds",
      "text": "One or two sentences.", "sample": false }
  ]
}
```

| Field | Meaning |
|---|---|
| `version` | Must be `1`. Any other value makes the strip ignore the file and say the feed could not be loaded. |
| `sample` | `true` marks every challenge as a sample on the page. |
| `updated` | `YYYY-MM-DD`, for you. |
| `note` | Free text for you; not shown. |
| `repeat` | `true`: after the last entry the schedule loops from the first (week by week, anchored on the first `start`). `false` or missing: a week with no entry says "No weekly challenge is scheduled this week." |
| `daily` | Games whose daily puzzle the strip lists, each `{ "game": slug, "label": text }`. Signal reads its own state. Any other slug is read from `localStorage["noyvj-daily-v1"]` (the `markCompleted` record of `shared/seed.js`), so a game only needs to call `markCompleted` when its daily run ends. Missing or empty: Signal only. |
| `weekly[].start` | A real date, normally a Monday. The entry covers `start` for seven days. Dates are UTC. |
| `weekly[].game` | A game slug from the hub (`herd`, `grid`, ...). The strip links to `games/<slug>/index.html`; arbitrary URLs are not allowed on purpose. |
| `weekly[].title` | Up to 80 characters, required. |
| `weekly[].text` | Up to 240 characters. |
| `weekly[].sample` | `true` flags this entry as a sample even if the file is not. |

Malformed entries (bad date, slug with odd characters, no title) are skipped silently; the rest still show. Test any date with `index.html?event-date=2026-11-02`.
