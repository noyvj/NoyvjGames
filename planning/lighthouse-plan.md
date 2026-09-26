# Lighthouse — Groundwork Plan (Round 3 M2)

Status: PLAN ONLY. No `games/lighthouse/` folder exists yet. Once approved, this becomes the seed for `games/lighthouse/CLAUDE.md` (per `game-template.md`).
User answer (Round 3, M item 2): "yes but maybe make it feel like it is about to become a horror game at any minute even though it never does". Taste rule (standing): fun first, no lesson. No BCM tag (personal project). Working title only.

**Shared baseline:** `overclock-plan.md` section 4 (save, settings, achievements, changelog, tutorial, confirm dialog, mobile dock/HUD, colorblind rules, test harness, feedback) and section 5 (hub integration) apply with slug `lighthouse`. Section 11 lists only what differs.

## 1. One-line pitch
You keep one light on one rock. Storms come, ships pass, oil is finite, and a small cast of passing sailors leave letters, gifts and things you cannot quite explain, while everything about the place keeps suggesting something is about to go wrong, and it never does.

## 2. Concept
A cozy idle/management game with two layers:

- **The Keep (mechanical layer).** Nights are the unit of play. Each evening you allocate oil, lamp brightness, repairs and your own rest; the night then plays out (fast-forward and pause available) while weather and ships arrive; a morning report shows what the light did. Steady, low-stakes, satisfying: the fun is the tension of a bad night and the calm of a clear one. Closest in shape to SOL's idle loop (tick-driven, pause and fast-forward), not to any of the climate games.
- **The Unease (story layer).** A deliberate, sustained feeling that this could turn into a horror game: a light on the far shore that is not on the chart, a ship in the log that never appears on the horizon, wet footprints on the stairs, a voice that turns out to be the wind in the lens housing. **It never pays off into horror.** Every odd detail has a warm resolution scheduled in the data. The game is about the anticipation of dread being misplaced, and the relief being the reward. See section 6, which is the most important section in this file.

The story layer (letters, sailors, mysteries, odd details) is switchable with the shared story toggle. With it off you have a quiet, complete lighthouse-management sim.

## 3. Stack
- Default: Python via Pyodide, plain HTML/CSS with an inline SVG scene, no build step, run via `python -m http.server`.
- Simulation: deterministic seeded sim in Python, stepped in fixed **ticks** (one tick = 10 in-game minutes; a night is ~48 ticks; a day segment is planning, not ticks). JS calls `step(n_ticks)` at a coarse rate (about 4 ticks per second at 1x, 8 and 16 at 2x and 4x). The sim never reads the real clock, so tests call `step()` in a loop. **Honest limit:** the coarse JS timer is only a pacing device; nothing depends on precise timing, and a paused or backgrounded tab simply stops the night (no catch-up, no penalty).
- **No audio.** This stack has no audio and the user has dropped audio for now. Every "sound" in the dread design is expressed as text or a visual cue (section 6). Do not design any beat that only works with sound.
- Rendering: SVG scene (rock, tower, sea, sky by hour, ship silhouettes, sweeping beam) plus DOM panels for logistics. The beam sweeps with CSS transform; under reduce motion it is a static cone plus a "sweep position" tick mark.

## 4. Core constraints (do not violate without asking)
1. **Horror is never delivered.** No jump scares, no gore, no death of the keeper, no harm to sailors from anything supernatural, no cruelty. Every unsettling detail is resolved warmly within a bounded number of nights (section 6.4). This is a hard rule, enforced by a data test.
2. **The keeper cannot die or lose.** Bad nights cost oil, repairs, reputation and comfort; ships can be delayed, damaged or turn back. There is no keeper death and no on-screen sailor death. Losses are always reversible by play.
3. Nothing gates play on the real clock. No waiting timers, no offline production that punishes absence, no daily-login rewards.
4. Story layer is fully removable: the sim, achievements-by-play and saves work identically with it off.
5. Never colour-only: weather severity, oil level and repair state each have icon + number + pattern; the night sky palette is decoration.
6. The eerie sub-layer has its own setting (see 6.6) so a player can keep the letters and cozy cast but skip the unease.
7. No real people, no real wrecks, no real disasters as material. Names of places and ships are invented.

## 5. The Keep: mechanics

### 5.1 Resources and stats
- **Oil** (stock; burned by the lamp). Refilled by supply boat visits (seeded schedule, one every few nights) and gifts.
- **Lamp brightness** (Dim / Standard / Bright / Storm): higher brightness reaches further and helps in fog but burns more oil per tick. **Lamp-hours** counted per night for the report and one achievement.
- **Clockwork** (rotation): a wind-up mechanism has to be wound every N ticks; forgetting means the beam stops sweeping (light on but a fixed cone, half as useful). Winding is a small action, and a good candidate for an idle automation upgrade. Real fact for flavor, only if sourced on screen: many historical lighthouses did use clockwork to turn the lens.
- **Structure** (0-100 per part): Tower, Lantern room glass, Gallery rail, Dock, Cistern (water). Storms damage parts; repairs cost **supplies** (timber, glass, tar) and keeper time.
- **Keeper energy** (0-100): work spends it, sleep and food restore it; low energy slows actions (it never blocks the light). This is where the player gets ordinary management tension.
- **Supplies** (food, tar, glass, timber) and **Comfort** (a cosmetic-plus-small-bonus stat driven by gifts and the keeper's room).
- **Reputation** ("The Light"): how ships regard the station; rises when ships pass safely, falls when they are delayed. Reputation gates which sailors and mysteries appear (section 7).

### 5.2 Loop
1. **Evening plan:** set brightness schedule (a 3-block plan for the night: dusk, deep, dawn), assign the keeper's tasks (winding, repairs, watch), allocate oil for the night, choose a repair queue, optionally read the **barometer** (weather forecast with an honest uncertainty band).
2. **Night run:** ticks advance at 1x/2x/4x or paused; events surface as short log lines and icons on the SVG horizon: weather changes, ships appear, small incidents (a shutter bangs, a wick smokes). The player can intervene at any time (brighten, wind, patch), which spends oil, energy or supplies.
3. **Morning report:** ships passed, ships delayed, lamp-hours, oil used, damage, letters found, a one-line summary. Deliveries and gifts arrive here.
4. **Day tasks:** repairs, restock from the supply boat, tidy the keeper's room, read letters (story layer), then next evening.
A full night takes about 3-5 minutes at 1x with normal play; the whole cycle is 5-8 minutes. Pause is unlimited and free.

### 5.3 Weather and ships (seeded, deterministic)
- `weather(seed, night)` gives a schedule of segments: clear, haze, fog, squall, storm, plus wind. Storms have a rise, a peak and a fade; fog and storms both raise the required brightness for safe passage.
- `ships(seed, night)` gives arrivals: ship type (fisher, cargo, ferry, yacht, mail boat), a visibility threshold, a heading and a **need** (light must be seen at the right moment, or the mail boat must land supplies at the dock in calm water).
- A ship **passes safely** when the beam reaches it (brightness high enough for weather) during its approach window. Otherwise it is **delayed** (turns back, waits for morning) or, in the worst case, **damaged** and needs the keeper's help the next day (rowboat rescue is a small mini-choice, always succeeds narratively but costs time and supplies). No one is lost, ever (constraint 2). Stakes come from resource pressure and reputation, not from death.
- Forecast: barometer shows `severity_band` for the next night. It is truthful on average and wrong sometimes (seeded), so reading it is a judgment call.

### 5.4 Progression
- **Station upgrades** (spend Reputation-earned Salvage): better lens (reach), oil-saver wick, winding weights (rings longer), a bigger cistern, a fog bell (a visible pulse ring and log line, since there is no audio), a storm shutter set, a small boat, a greenhouse box (supplies), a wind vane (better forecasts).
- **Seasons:** a year is four seasons of ~10 nights each; season changes weather weights and daylight length (longer nights in winter use more oil), and shifts which sailors come by.
- **Prestige-free:** no reset loop. The long arc is the letters and mysteries (section 7) and the year at the light. After the first year it continues in "keeper for life" endless mode.
- Mode set: Story (letters + mysteries + eerie details), Quiet (no story layer), Endless (after year one, seeds continue).

## 6. The unease: how to make it feel like horror without ever becoming horror
This section is the design core. It exists so a future session can add odd details without accidentally breaking the promise.

### 6.1 The promise, stated as rules
1. **Anticipation only.** The player is made to expect something; the resolution is always ordinary, kind or funny.
2. **Every unease beat has a resolution in the data** (section 6.4). No dangling dread.
3. **The resolution is always warm or gently funny**, and never that "it was a hoax to scare you". The reveal reframes the object of fear as a person, an animal or a sea-and-weather fact who needed help or company.
4. **Nothing in the game punishes the player for being afraid.** The scary-looking option is never the wrong one.
5. **Ambiguity is allowed, but it must resolve to warmth.** Some mysteries stay slightly unexplained (was it the previous keeper's habit or the wind?), but never toward harm.
6. **The keeper is never alone in the bad way.** The player is always told the ships are okay by morning.

### 6.2 Techniques (all sound-free)
| Technique | Example | How it is delivered without audio |
|---|---|---|
| **Wrong-count detail** | The lamp-hour tally is one hour higher than the log says | A small number that does not add up in the morning report; a footnote appears only if the player hovers or expands |
| **Sparse odd objects** | A second cup set out; a chair turned to face the sea; the door open 2 degrees | One changed pixel-level element in the keeper's room SVG, described in a single line of alt text and only surfaced by the story layer |
| **Off-chart light** | A steady light on the horizon in a direction with no land | A single small point on the SVG horizon at certain nights, not in any ship or chart list |
| **Ghost entries** | A ship appears in the log that was never on the horizon | A log line with a normal ship icon and a tiny "?" status; morning report shows "unrecorded" |
| **Wrong-handwriting** | A note in the logbook in a hand that is not yours | Letter panel typeface swap (a different web-safe cursive stack) for one entry |
| **Withheld camera** | The thing in the fog is always a silhouette at the edge of the beam | The fog rendering never resolves detail; text says "the shape stays just past where the light reaches" |
| **Repetition with drift** | A knock every third night, slightly later each time | Log line schedule, gently shifting |
| **Long pauses** | Text that lands slowly | A text line reveals one clause at a time using a CSS step reveal (respects reduce motion: instant) |
| **Fog as curtain** | The nights with the most odd details are the foggiest | The scene gets denser fog; nothing more |
| **Domestic wrongness** | The kettle is warm when you arrive | A room description change, one line |

The techniques rely on typography, timing of reveal, contrast between calm sim and unusual detail, and the player's own expectations. They do not need audio, video or real-time precision.

### 6.3 Dread pacing
- A hidden **unease** meter (0-100, not shown) controls how often odd details appear. It rises on foggy or storm nights and when the player is idle in the story layer, and it drops sharply when a letter or gift lands or a mystery resolves.
- **Cap and cooldown:** at most 2 odd details per night, none on the first night of a season, always at least one kind beat between two odd ones.
- **Peaks are scheduled, not random.** Each mystery has a build (3 to 5 odd beats), a "the moment" beat (looks like the horror moment), and a resolution beat (warm). The moment beat is carefully written to stop just short.
- The first year is a crescendo of expectation across four mysteries, each resolved before the season ends.

### 6.4 The dread ledger (data and tests)
`content/mysteries.json` defines each mystery as `{id, title, season, beats: [{night, kind: "odd"|"moment"|"kind"|"resolve", text_key, tags}], resolves_by_night, resolution_tags}`. Every mystery must have exactly one `resolve` beat that occurs no later than `resolves_by_night`. Tests:
- every `odd`/`moment` beat belongs to a mystery with a later `resolve`;
- no unresolved mystery at the end of any year;
- the resolution beat carries a `warm` tag; a lint fails on banned words in any player-visible string (death, dead, corpse, blood, murder, scream and similar);
- unease meter simulations over 1,000 seeded years never exceed the cap.

### 6.5 Example mysteries (launch draft; user vetoes tone)
1. **The Second Light.** A small lamp appears off the north-east horizon on foggy nights. Odd beats: it moves, it blinks in a pattern, the pattern matches your own beam a few seconds late. Moment: it is closer than it should be. Resolution: a retired fisher, unable to sleep, rows out at night to keep the keeper company and mimics the beam to say hello. They leave a jar of preserves on the dock.
2. **The Knocking at the Cistern.** A tapping from the cistern room on every third night. Resolution: a very determined seal pup dragging a shell against the pipe, and the keeper ends up with a pet.
3. **The Extra Cup.** A second cup appears on the table, warm. Resolution: the mail-boat captain has been letting themselves in at dawn to leave a hot drink because the keeper never leaves the rock; they were too shy to knock.
4. **The Unsigned Letters.** Letters in an unfamiliar hand, each one describing the keeper's night with eerie accuracy. Resolution: a child on a passing ferry who watches the light every evening and writes what they imagine keeper life is like; the accuracy is a coincidence of how routine the place is; they exchange drawings.
5. **The Wrong Ship.** A ship in the log that is never seen. Resolution: an old ferry retired years ago whose crew, on the anniversary, sails past a mile out to salute the light, invisible in fog. The honest, sweet ambiguity: you can never confirm it.
6. **The Chair Facing the Sea.** The chair in the day room rotates a little each week. Resolution: the previous keeper's chair on a slowly settling floor (warm, gently funny), and the previous keeper turns out to be a regular correspondent.
More mysteries are Pass 2 content; each is authored to the same build-moment-resolve shape.

### 6.6 Settings for the unease
- Shared **Story** toggle: hides the whole story layer (letters, sailors, mysteries, odd details).
- Game setting **Eerie details** (on/off, default on): hides only odd/moment beats; letters and warm beats remain. Both persist as per-device display settings (like `story-toggle.js`, not in the save).
- **Content note** on the first Story-mode start: a one-line, non-spoiling line ("This game plays with the feeling of dread. Nothing frightening ever happens.") plus links to the two switches.

## 7. The cast and the letters
- **A recurring cast of ~12 passing sailors** at launch, each with a ship, a route, a voice, a small personal arc that advances by ship passes and reputation gates. Examples: the mail-boat captain (quiet, punctual), a fisher who never catches anything but is always cheerful, a cartographer who keeps correcting the chart, a child on the ferry, a smuggler who is very bad at it, a pair of correspondents who write each other through you.
- **Letters:** unlocked after safe passage streaks or mystery beats; short (60-120 words), read in a letter panel; each letter can attach a **gift**.
- **Gifts:** cosmetic room items (a shell mobile, a chipped mug), a couple with a small effect (better lens cloth: reach +1 for a week of nights, in game days, not real time), and a few that connect to mysteries.
- **Small mysteries** are the six above at launch, each with 5 to 9 beats spread across the year. The cast is who resolves them, so meeting people warms the place.
- Story-chapters: `shared/story-chapters.js` carries the year as a chapter list (`story.json`), with the mysteries as their own sub-threads. Chapters reached only via `NoyvjStory.reach(id)`.

## 8. Data model
```json
{
  "schema": 1,
  "meta": {"nights_kept": 0, "years": 0, "ships_passed": 0, "ships_delayed": 0,
           "best": {"clean_night_streak": 0, "lamp_hours_year": 0},
           "letters_read": [], "gifts": [], "mysteries_resolved": [],
           "achievements_earned": {}},
  "run": {
    "seed": 0, "night": 0, "season": 0, "phase": "evening|night|morning|day",
    "tick": 0, "rng": {"seed": 0, "draws": 0},
    "oil": 0, "supplies": {}, "structure": {}, "energy": 100, "reputation": 0, "comfort": 0,
    "plan": {"brightness": ["standard","bright","standard"], "tasks": []},
    "ships": [], "weather": [], "log": [], "unease": 0, "beats_seen": [], "upgrades": []
  },
  "settings": {"text_scale": 1, "reduce_motion": false, "eerie_details": true, "speed": 1}
}
```
The `run` weather and ship schedule are regenerated from `seed` and `night`, not stored. Only mutable state and consumed beats are saved. `load_state` tolerates missing keys. `achievements_earned` is written and never read back. Story on/off is a per-device setting (localStorage) like every other game.

## 9. Achievements (16)
1. First Light — complete your first night.
2. Quiet Night — a night with no incident.
3. Fog Bank — bring every ship through a foggy night.
4. Storm Warden — survive a storm with structure above half.
5. Reading by Lamplight — read 5 letters.
6. The Whole Cast — meet all 12 sailors.
7. Second Light — resolve mystery 1 (each mystery has its own achievement, 6 in total; hidden titles until resolved).
8. Tidy — repair every part in one day.
9. Frugal — finish a season with oil never below 20.
10. Year at the Rock — complete a year.
11. Wound Tight — wind the clockwork on time for a full week of nights.
12. A Good Neighbour — receive 10 gifts.
13. Fog Bell — build the fog bell.
14. Nothing Happened — end a night with zero events (a joke about the whole game).
15. Bravery is Optional — play the game with Eerie details off through a year (cosmetic, non-judgmental wording).
16. Keeper for Life — reach endless mode.
Follows `ACHIEVEMENTS-SYSTEM-DESIGN.md`; mystery achievements come from the story layer, so a Quiet-mode player can still reach 100% of the non-story set (tracked as a separate count, like Undersleep's journal achievements).

## 10. Testing approach
- pytest sim harness (SOL-style): weather/ship determinism from seed, oil burn by brightness, ship pass/delay rules, clockwork stop, structure damage and repair, energy effects, season transitions, save round-trip mid-night, pause/fast-forward invariance (running 100 ticks at once equals running them in 100 calls).
- **Dread ledger tests** (section 6.4) plus the banned-word lint over all shipped player-visible strings.
- Worst-case perf test (Thaw's pattern): a 4x fast-forward night with the maximum number of events under a step-time ceiling.
- Keeper-cannot-lose test: fuzz 1,000 bad seeds and assert there is no state from which the game ends.
- Live checks via the shared `hub-dev-server`: 375px layout, story toggle and eerie toggle, reduce motion, keyboard-only night, offline load.

## 11. Baseline checklist pointer (what differs)
Use `overclock-plan.md` sections 4 and 5, slug `lighthouse`. Specifics:
| Item | Note |
|---|---|
| Save | Mid-night save is safe because the RNG state is serialised; the weather/ship schedule is regenerated from seed |
| Settings | Text scale, reduce motion, **Eerie details**, sim speed default |
| Story toggle | `shared/story-toggle.js` with selectors for `#letters, .odd-detail, .sailor-note, #story-chapters`; mechanical log lines are never listed |
| Confirm dialog | Abandon year, Reset progress, Spend rare upgrade |
| Mobile dock / HUD | Dock: speed/pause/brightness; HUD: oil, energy, night |
| Colorblind | Weather and oil never color-only; ship types by silhouette + label |
| Light theme | A "day-scene" variant of the SVG for the light theme (pale sky, dark tower) |
| Real-world examples | Only the clockwork fact and similar flavor lines; each shown fact names a source per the convention (the "sourced real-world examples" pattern in Canopy and Drift) or is left out |
| Ambient | `shared/ambient-bg.css` for the page backdrop; the SVG scene handles the rest |
| Leaderboard | None planned. A cozy game with no ranking is intentional |
| Info panel | "About the Light" panel: how brightness and oil work, plus the content note |

## 12. Milestones
Commit + tag each: `git tag lighthouse-milestone-0N`. Milestones 1-4 ship a complete cozy management game with no story layer.

| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Sim core | Deterministic weather + ship generators, tick `step()`, oil/brightness/clockwork/structure/energy, text harness that plays a night. Tests: determinism, pause/ff invariance | Not started |
| 2 | Night UI | SVG scene, beam, ship silhouettes, evening plan panel, morning report, speed/pause controls | Not started |
| 3 | Day loop + upgrades | Repairs, supplies, supply boat, upgrades, seasons, forecast | Not started |
| 4 | Complete Quiet mode | One year to completion, endless continue, save widget, settings, confirm dialogs. **First complete, playable game** | Not started |
| 5 | Cast, letters, gifts | 12 sailors, letter panel, gifts, room scene, story toggle | Not started |
| 6 | The Unease | Unease meter, odd-detail techniques, six mysteries with the dread ledger tests, Eerie details setting, content note | Not started |
| 7 | Standard kit | Tutorial, mobile dock/HUD, changelog, info panel, feedback, light theme, colorblind audit | Not started |
| 8 | Achievements + polish | 16 achievements, panel/toast, copy lint, perf test, balance bots | Not started |
| 9 | Hub integration | Card, thumbnail, favicon, `sw.js`, manifests, root CLAUDE.md row, dev logs, tag | Not started |

## 13. Risks
- **Dread that lands as actual anxiety.** Mitigation: content note, two switches, warm resolution rule, tests on the ledger, and no punishing of "the scary option".
- **The promise breaking through later additions.** Mitigation: the dread ledger data test, the banned-word lint, and this section as the checklist for any new mystery.
- **A management sim with no stakes.** Mitigation: real pressure from oil, fog and repair trade-offs; ships get delayed and damaged; reputation matters.
- **Idle-game drift into timers.** Mitigation: the sim only runs while the page is open and is fully pausable; no offline progress.
- **Odd details without audio feeling flat.** Mitigation: typography and reveal pacing, wrong-count detail, fog rendering; prototype the first mystery at Milestone 6 before writing all six.
- **Text volume.** ~12 sailors, ~40 letters, ~50 odd beats. Mitigation: launch with 6 sailors and 3 mysteries if the schedule needs it; the data shape does not change.

## 14. Open questions for the user
1. Is "no on-screen death, ever, even for sailors" right, or do you want a ship to be truly lost once per year for weight? (Recommend no.)
2. Should the eerie sub-toggle default on (recommended) or be opt-in?
3. Any hard "no" for the dread techniques (e.g. no figures in windows)?
