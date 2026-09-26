# Later

Things deliberately deferred — either you said "later"/"maybe," or an item needs more explanation/a feasibility check from me before it's worth committing to. Nothing here is scheduled; revisit whenever you bring this file back up. Original labels (from `IMPROVEMENT-IDEAS-2026-09.md`) kept so we can trace back to the original context if needed.

---

## Standing question: what can you actually do with audio?

Several items across the ideas file got parked specifically pending this — you said you're skeptical of the audio suggestions because you're not sure what's realistically possible, and asked me to explain before revisiting any of them. Short answer up front, full discussion whenever you want to pick this up: browser-side audio in this stack would mean the Web Audio API (or plain `<audio>` tags) triggered from JS — Pyodide/Python itself can't play sound directly, so any audio cue would be a small JS hook the Python side calls into, the same "Python owns state, JS owns the one external thing it needs" pattern the save widget and the report-button sender already use. Simple UI cues (a click blip, a chime on a milestone) are genuinely easy — either a tiny synthesized tone via Web Audio (no asset files needed at all) or a couple of short royalty-free sound files dropped into each game's folder. A full ambient music bed per era/game is a bigger, different kind of task (finding/licensing longer tracks, a volume/mute control, probably more worth doing once, shared, rather than per-game). Worth a real conversation on scope before touching any of these:

- **A5** (SOL): light click/coin-drop sound effect.
- **B5** (Canopy): a minimal recovery/wildlife chime — Pass 1 explicitly skipped this for lack of an audio system at the time.
- **K4** (Continuum): a distinct audio cue per era transition.
- **K11** (Continuum): an optional ambient audio bed per era.
- **G7** (Thaw): a minimal ping for the tipping-point moment — Pass 1 also skipped this for the same reason.
- **L21, round 2** (Le Champ de Mots): a pronunciation-practice mode (slowed TTS playback + visual syllable breakdown) — your round-2 answer: "audio is still an issue we are not dealing with yet."

---

## A. SOL

- **A5**: light sound effects — see the audio question above.
- **A7**: a "+X since last save" delta readout right after loading. You said: "don't understand the meaning." To clarify: the idea is that the moment a save code finishes loading, the game shows something like "+540 Iron, +12 Auto-Miners since this save was made" — a quick summary of what's different between the saved state and wherever you are now, mostly useful if you load an *old* save and want to see how much you'd be giving up, or just as a fun "look how far you've come" moment right after loading. Let me know if that's worth building once explained, or if it still doesn't seem useful.
- **A12**: a personal-best "fastest full playthrough" timer.
- **A13**: a "pure clicker / never touched automation" challenge achievement — you tied this back to A2's "keep achievements easy, not extreme" constraint; revisit together.

## K. Continuum

- **K3**: a dedicated full-playthrough integration test (Tribal through Space Age in one run) — a testing/engineering task, not player-facing; low urgency.
- **K4, K11**: see the audio question above.

## L. The Hub Itself

- **L5** (UPDATE 2026-09-20: you approved this in round 2 as Y11 and it is now an open item in `planning/TODO.md`; the reasoning below is why it needs its own design pass first, not a reason to skip it): site-wide dark/light theme toggle — a real, documented decision, not left unresolved. Building this now would mean a fake or half-working toggle: every game on the site currently uses a single dark, glass-panel space theme (confirmed across Continuum, Canopy, Trade Empire, and every other game's own CLAUDE.md visual-pass notes) with no existing light-theme CSS anywhere for a toggle to switch *to*. A genuine light/dark toggle needs a full second color scheme — backgrounds, borders, meter fills, text contrast, each game's own accent hue — designed and maintained across every single game's `style.css`, which is a large, dedicated design pass in its own right, not a toggle-widget task that fits inside the per-game settings-panel work (`planning/TODO.md`'s "per-game settings panel" section, origin A9). Decided: don't build a toggle until that design pass happens. When it does, the toggle itself would be the easy, mechanical part — a `data-theme` attribute + a CSS custom-property swap, the same shape the settings panels' own `--text-scale` variable already uses.
- **L9**: whether the site is ready to apply for real ads, and how. You asked directly, so here's the actual answer rather than a deferred question: `planning/pwa-and-ads-setup.md` already has the full setup order written out — (1) apply for Google AdSense (approval can take days to weeks, so applying early doesn't commit you to anything), (2) confirm HTTPS (GitHub Pages already provides this), (3) once approved, add the `ads.txt` file AdSense gives you and drop the real client/slot IDs into the ad bar that's already built and labeled everywhere. The ad bar itself, its labeling, and the placeholder wiring are all already done — the only blocker is actually submitting the AdSense application, which needs your own Google account and is a "you" step, not a "me" step. Say the word whenever you want to move on this.
- ~~**L18**~~ — shipped: the PWA install banner is built and checked off in `planning/TODO.md`.
- ~~**L20**~~ — resolved: this round's Z25 answered "yes" to an opt-in autosave checkbox (every ~5 minutes, defaulting OFF so it never silently overwrites a save without the player choosing it), now tracked as accepted work in `planning/TODO.md`, not deferred anymore.

## B. Canopy

- **B5**: audio cue — see the audio question above.

## C. Grid

- **C6**: "later" (no further comment attached).
- **C14**: confirmation before retiring the last unit of a plant type. Your note: "an undo button or an 'are you sure?' with a 'don't show again' option — having to confirm every time can get irritating." This is now the seed of the shared confirmation-dialog pattern in `TODO.md`; revisit the exact UX shape (undo window vs. confirm-with-opt-out) once that pattern's designed.

## D. Tide

- **D10**: "later" (no further comment attached).
- **D20**: "maybe later" (no further comment attached — was "a light visual flourish on the endgame," carried over from the original idea's own wording).

## F. Herd

- **F4**: "later" (no further comment attached).
- **F10**: a full "Restart Farm" reset. Your note: "maybe prestige system rather than full reset" — worth deciding whether Herd wants a Loop/SOL-style prestige layer instead of a plain wipe-and-restart.
- **F20**: swapping the context-blurb once methane crosses a threshold. Your note: "I'm not sure what that changes." To clarify: right now the intro/context text at the top of the game stays the same fixed sentence the whole session; this idea would swap in a different pre-written sentence once methane has visibly become a real problem, so the framing text reacts to how the session is actually going rather than staying static flavor text throughout. Minor, cosmetic — fine to drop if it still doesn't seem worth it once explained.

## G. Thaw

- **G7**: audio ping — see the audio question above.
- **G8**: an in-game reset/restart control. Your note: "idk the difference of making a new save and resetting enough." To clarify: right now, "starting over" means either reloading the page (loses everything unless you'd saved) or loading a different/blank save code by hand — there's no single in-game button that just resets the current session back to zero while you keep playing. It's a minor convenience over what already exists via save codes, not a new capability — likely fine to drop if a manual reload/new save code is good enough for you.

## H. Loop

- **H16**: "later" (no further comment attached).

## I. Drift

- **I4**: an in-game "Start New Region" reset control, marked "maybe" — same category as Thaw's G8 above (a convenience over reload/new-save-code, not new capability).

---

## Round 2 (from `IMPROVEMENT-IDEAS-ROUND-2.md`) — labels re-used from round 1, tagged "round 2" to disambiguate

### Z. Games (cross-game)

- **Z9, round 2**: a cross-game "campaign" framing — one combined progress checklist/percentage across all 12 games. Your answer: "maybe later but probably not, I am trying to let all the games exist on their own right now." Not building.

### Canopy

- **B5, round 2**: comparing the forest's standing value against the site aggregate average — you want "a full multiplayer pass soon" first.

### Tide

- **D25, round 2**: the "shared coastline" cooperative-framing community stat — explicitly saved for the multiplayer update.

### Aftermath

- **E11, round 2**: a "mutual aid network" positive event — explicitly waiting for the multiplayer update.

### Thaw

- **G25, round 2**: a "counterfactual world tour" (previewing Region D's trajectory applied to A/B/C's starting conditions) — marked "no but maybe later."

### Continuum

- **K30, round 2**: a "peer city" async ghost overlay *(needs the Z1 aggregate backend from round 2)* — you said it could be good but might also be confusing, and want to prioritize scoping multiplayer across the site first; revisit once that's underway.

### New game concepts (Section M)

- **M2, round 2 — Silk Road**: a historical trade-route management game. You left the call to me ("if you believe it is different enough [from Trade Empire], build it") — my honest read is it's mechanically too similar to Trade Empire (route goods between nodes, react to market/events) without a sharper hook, so parking rather than building. Revisit if a genuinely distinct mechanic comes up, not just a historical reskin.
- **M8, round 2 — Contraption**: a physics-based sandbox puzzle game. You asked "if you think it's possible, yes; otherwise no." A real drag-and-place physics puzzle needs a proper JS physics engine (e.g. Matter.js) — feasible, but a bigger stack decision than a normal new-game plan (similar in scale to Continuum's Three.js adoption). Parking until that's a deliberate choice.
- **M9, round 2 — Offbeat**: a rhythm/timing arcade game. You flagged the concern yourself — precise timing is hard given Pyodide's boot overhead, and audio is still unresolved (see the standing audio question at the top of this file). Parking until both are addressed.

### Warframe Build Tracker (Section X, now tracked in `planning/TODO.md`'s own X section, not a separate local file)

- **Riven disposition reference column**, round 2 — "maybe much later, right now is a crafting and resource tracker," per your answer.
