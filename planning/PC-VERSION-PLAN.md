# PC version of every game: plan and discussion

Status: **plan revised 2026-10-06 after the user's first three answers; nothing built.** The user asked for "a huge update to all games, building them out more like PC games than browser games", while keeping the current version available. Answers so far (section 8): layout and feel only, no downloadable app; the two layouts are separate "boots" chosen before entering a game, with shared saves; audio stays off but is raised again in every ideas round; **Continuum is the only game that gets any of this work for the next two weeks** because it is due for class.

---

## 1. The gap today

Twelve of the thirteen games render as one narrow column: `#game { max-width: 480px }` in Canopy, Grid, Tide, Aftermath, Herd, Thaw, Loop, Drift, Trade Empire and Continuum, 420px in SOL, 34rem in Signal. Only Le Champ de Mots goes wider (900px). On a 1920x1080 monitor that is a phone-sized strip in the middle of an empty window. The page scrolls, every panel (achievements, what's new, settings, summary) opens by pushing content down the same column, and the primary controls are far from the thing they act on. That is a mobile app in a browser tab, which is the opposite of how PC games are built.

What already exists and helps:
- Every game has Pyodide-run Python logic (`game.py`) separate from a thin HTML/CSS view bound by element ids. That separation is what makes a second presentation layer possible without touching mechanics.
- `shared/mobile-dock.js` already moves a game's action panel to a fixed bar on narrow screens by reparenting the node, and `shared/mobile-hud.js` pins a status bar. A PC layout is the same idea at the other end of the screen-size range.
- `shared/opening-screen.js` (New Game / Saves / Settings / Info / Feedback) is already a title-screen.
- `shared/theme*.js`, `shared/site-settings.js` (account-synced theme, text scale, reduced motion), `shared/tutorial.js`, `shared/keyboard-shortcuts.js`, `shared/save-widget.js` are shared, so a PC shell can reuse them.
- Continuum already has a Three.js scene and Le Champ de Mots a four-style visual switcher, so there is precedent for a richer "stage".
- **Continuum's Hamlet view is the half-built version of this plan.** Today it is an in-page toggle (desktop-only, off by default, `#game.hamlet-on` widens the page to 1180px and puts the controls on buildings in the 3D scene as real buttons, with the ordinary panels hidden by CSS). Its recorded limits are exactly the ones a proper Desktop boot should fix: at about 1024px wide some chips overlap, and the guided tutorial points at `#work`, `#buildings` and `#research`, which are hidden in Hamlet mode. The plan is to grow it into Continuum's Desktop boot rather than start over.

## 2. What "PC game" means here

A feel and layout change, not new mechanics. The game's rules, saves and tests stay as they are.

| Browser-page feel (today) | PC-game feel (target) |
|---|---|
| One scrolling column | Fixed full-window layout, no page scroll |
| Panels open inline and push content down | Panels are windows or side drawers over the game, closed with Esc |
| Controls grouped by code order | Controls grouped by role: top HUD, left actions, centre stage, right details/log |
| Mouse or touch only | Mouse-first with hotkeys for everything frequent, hover tooltips, right-click where natural, optional gamepad later |
| Toolbar of 8 text buttons | One menu button plus an icon rail; the rest live in the menu |
| Boots into the game after a blank wait | Loading screen with progress, then title screen, then game |
| Notifications are toasts that cover content | A notification stack in a fixed corner with history |
| No sense of window | Fullscreen button, UI scale, graphics/animation settings, remembered per game |
| Sound: none | Sound would be a big part of the feel, but see decision 3 |

Things that deliberately do not change: Python owns state, saves and achievements work exactly as now, mobile keeps its own dock/HUD layout, everything stays free and static (no build step).

## 3. How it would work

### 3.1 Two boots, chosen before the game loads
Each game keeps its current page as the **Classic** boot (`games/<slug>/index.html`, untouched) and gains a **Desktop** boot (`games/<slug>/pc.html`). Both load the same `game.py` and engine modules and use the same `game_id`, so a save made in one opens in the other. The choice is made before entering, never mid-session:
- the hub's game card and the game's opening screen each offer "Classic" and "Desktop" (Desktop only offered on wide windows with a fine pointer; phones and small windows only ever get Classic);
- the pick is remembered per browser and later synced with the account settings that already hold theme and text scale;
- switching later means going back to the opening screen or hub and picking the other; the save carries over, so it costs one reload, not a lost game.

Why this answers the loading concern: Python boots once per page load either way (a single page that rearranges itself never boots it twice), but separate entry pages mean the Classic page does not download any Desktop CSS or JS and vice versa, the Classic page cannot regress because nothing in it changes, and the Desktop page can be written for a wide window instead of undoing a 480px column with overrides. The heavy parts (Pyodide itself, `game.py`, the engine modules) are the same files at the same URLs, so the browser and service worker cache them once for both boots.

### 3.2 A shared shell, not 13 rewrites
New `shared/pc-shell.js` and `shared/pc-shell.css`, included only by the `pc.html` pages. A game's `pc.html` is a short page: the shell's frame (top bar, rail, stage, details, log, window layer, menu) with the game's own elements placed in it, plus the same script and Pyodide boot block as its `index.html`. Because `game.py` finds everything by id, the rule is **every id `game.py` looks up must exist in both pages**, and a shared test enforces it by parsing `game.py` and both HTML files. No mechanic, state or save-format change, so the existing suites keep applying.

Repeated markup (the toolbar, panels, boot script) is generated from one shared template where possible, so the two entry pages cannot drift for the same reasons as the duplicated per-game shells did before the shared components existed.

### 3.3 Windows
Panels that are "open on demand" today (achievements, what's new, settings, summary, almanac, session summary, how-to-play, civilization summary, etc.) become windows managed by the shell: title bar, close button, Esc to close, focus trap while open, optionally movable and remembering their position. The existing `hidden` attribute toggling keeps working because the shell watches it. The blanket `[hidden] { display:none !important }` added in the 2026-10-06 audit is a prerequisite and is already in.

### 3.4 The stage
Most games have a thing the player actually looks at: Canopy's plot grid, Champ de Mots' farm grid, Trade Empire's colony network, Loop's supply chain, Continuum's settlement scene, SOL's planets. In PC layout that becomes the large centre area, scaling with the window (CSS grid/SVG scale, not fixed pixels), with the controls around it instead of below it. Dashboard-style games without a visual (Grid, Tide, Aftermath, Herd, Thaw, Drift) get a central chart/readout area built from elements they already render (their charts, region visuals and status readouts).

### 3.5 PC-feel features (shared, built once)
- Input: a unified hotkey layer on top of `shared/keyboard-shortcuts.js` (one consistent scheme: Esc menu, Space advance/pause, number keys for speed, Tab cycles panels), a hotkey hint bar, hover tooltips for every icon button, rebind later.
- Chrome: fullscreen button, UI scale, "reduce effects", a notification stack with history, an in-game menu (Resume, Save, Settings, Achievements, Exit to hub) opened by Esc.
- Boot: a shared loading screen showing Pyodide progress (the single biggest "this is a web page" tell is the blank wait), then the existing opening screen.
- Polish layer (later): subtle transitions, number tick-ups, hover and press states, per-game accent theming.
- Accessibility carries over: keyboard reachability, focus order that matches the visual zones, screen-reader names, reduced motion, colorblind-safe state encoding (the earlier audits are the bar).

### 3.6 Packaging
Out of scope by the user's answer: this is a layout and feel change on the website, not a downloadable app. (Installing the site as a PWA in its own window stays possible later without changing this plan.)

## 4. The games, grouped by what their PC layout centres on

These groupings come from the current page structure; each game's real manifest gets worked out during its own conversion and may differ.

| Archetype | Games | PC layout idea |
|---|---|---|
| **Board/stage first** | Canopy, Le Champ de Mots, Trade Empire, Loop, SOL, Continuum | Large central board or map. Left rail holds the actions for the current selection (what `mobile-dock` pins at the bottom on phones). Right panel holds selection details, requests/events and the log. Top bar holds resources and time. Continuum's existing 3D scene becomes the stage with research and civic panels as windows. |
| **Dashboard + decisions** | Grid, Tide, Aftermath, Herd, Thaw, Drift | Central chart/region visual with the indicators around it. Decision cards (invest, policy, event choices) in a right column. Season/round advance as one prominent button plus a hotkey. History, summary and comparison panels become windows. |
| **Single board** | Signal | Centred puzzle with the tool palette on one side and daily/archive/stats on the other; it already has the smallest page, so it is the cheapest conversion. |

## 5. Rollout order

Sizes are relative effort: S, M, L, XL.

**Schedule constraint (user, 2026-10-06):** Continuum is the flagship BCM114 Round 2 Digital Artefact and is due in about two weeks (around 2026-10-20). For that period it is the only game that gets any of this work, and the PC work only goes ahead if it does not compete with what the class needs. No other game is touched until Continuum's deadline has passed.

| Phase | What | Size |
|---|---|---|
| 0 | Decisions in section 8 (the first three are answered). Capture "before" screenshots of Continuum at 1920x1080 and 1440x900 for the evidence trail. | S |
| 1 | **(first slice built 2026-10-06: `pc.html` generator, shell frame and windows, Hamlet on by default, Desktop tutorial, layout switch on the opening screen; second pass the same day added a hotkey hint bar, a notification stack and the Story pill in the toolbar; still to do: a human play-through of every era, tooltips and window positions) Continuum Desktop boot** (`games/continuum/pc.html`), built from the Hamlet view: shared shell frame, windows for the panels, fix the two known Hamlet limits (chip overlap at about 1024px, tutorial pointing at hidden panels), shared saves with Classic, boot choice on the opening screen. Done when Continuum plays fully in Desktop with Classic unchanged and its 765 tests green. Ships only if it is ready and safe before the deadline; otherwise it waits and Classic is what gets marked. | L |
| 2 | **Extract the shell.** Move what Continuum proved into `shared/pc-shell.*` so a second game needs only a `pc.html`. | M |
| 3 | **Second archetype, after the deadline:** Canopy (board) or Tide (dashboard), whichever the user prefers, to check the shell works for a game that was never designed for it. | M |
| 4 | Shared PC features: unified hotkeys and hint bar, tooltips, notification stack, settings (UI scale, fullscreen, effects), hub-card boot picker, account sync of the choice. | L |
| 5 | **Roll out by archetype**, one game per milestone, tagged like existing milestones: remaining board games, then dashboards, then Signal. | XL (12 x M) |
| 6 | Visual identity pass per game (accent, stage art, transitions). Audio only if the user says yes (see decision 2). | L |

## 6. Testing and quality bar

- Existing per-game suites stay green unchanged; if a PC change needs a test edit, that is a signal the change touched mechanics and should be rethought.
- New shared test: every id `game.py` looks up exists in both `index.html` and `pc.html` (the two boots cannot drift), and both pages use the same `game_id` so saves are shared.
- Live checks per game at 1920x1080, 1440x900, 1280x720 and 1100px, in light and dark themes, with the audit hygiene sweep (hidden-but-visible elements, unnamed controls, overflow) as the gate.
- Keyboard-only pass: every action reachable, focus never trapped, Esc always leaves.
- Pyodide boot time measured before and after (the loading screen must not make it worse).

## 7. Risks

- **Two pages that must stay in step.** `index.html` and `pc.html` both have to contain every id `game.py` uses. A shared parity test catches a missing id at once; shared markup comes from one template so the pages cannot drift quietly.
- **Per-game CSS entanglement.** Each stylesheet is 1,100 to 2,000 lines written for a 480px column. The shell must scope its changes under `html[data-layout="pc"]` so classic is unaffected, and games will still need their own spacing and chart-size rules.
- **Tutorial and tooltips.** `shared/tutorial.js` spotlights elements by selector and position; it must work when those elements are inside windows or zones.
- **Scope.** This touches all 13 games. Mitigation: one shared shell, one game per milestone, classic always available so nothing blocks shipping.
- **Audio expectation.** A PC feel without any sound can read as half done. The user's answer is "not yet"; it is raised again in every ideas round until they say yes.

## 8. Decisions

Answered by the user on 2026-10-06:

1. **What "PC version" means: layout and feel only.** No downloadable app. The two layouts are separate boots chosen before entering a game, with shared saves, so a player never loads both (section 3.1).
2. **Audio: not yet, but keep asking.** It is raised again in every ideas document until the user says yes. Until then the plan assumes silence. (`planning/LATER.md` and `planning/TODO.md` now say this instead of "ask around round 6".)
3. **Continuum comes first and alone.** It is the class deliverable, due in about two weeks, and already has the Hamlet view as a start; it is the pilot in place of Canopy. Nothing else is converted until after the deadline.

Still open, each with a recommendation (a "go with your recommendations" covers them):

4. **Second game after Continuum:** Canopy (a board, the biggest game) or Tide (a dashboard). Recommended: Tide first as the cheaper proof, then Canopy.
5. **Look.** Keep the shared glass-panel frame and give each game its own accent and stage art over time, rather than a full per-game visual identity up front.
6. **Controller support.** Not in this pass; hotkeys are designed so it can be added later.
7. **Mobile.** Unchanged and still first-class with its own dock and HUD, tested alongside every Desktop milestone.
8. **Does Continuum's Desktop boot belong in the next two weeks at all?** Recommended: only as a small, safe step (the Hamlet limits and a boot choice on the opening screen), and only after anything the class marking actually asks for. Please say which parts of Continuum the class needs finished, so the PC work is fitted around them rather than competing with them.

## 9. Not part of this plan

New mechanics or content, backend changes, multiplayer (see `planning/MULTIPLAYER-SCOPING.md`), new games, and anything that changes how saves or achievements work. If a PC layout seems to need one of those, it gets its own item.
