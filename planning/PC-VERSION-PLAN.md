# PC version of every game: plan and discussion

Status: **discussion draft, nothing built.** Written 2026-10-06 after the user asked for "a huge update to all games, building them out more like PC games than browser games", while keeping the current version available. The decisions in section 8 need answers before any build work is scheduled into `planning/TODO.md`.

---

## 1. The gap today

Twelve of the thirteen games render as one narrow column: `#game { max-width: 480px }` in Canopy, Grid, Tide, Aftermath, Herd, Thaw, Loop, Drift, Trade Empire and Continuum, 420px in SOL, 34rem in Signal. Only Le Champ de Mots goes wider (900px). On a 1920x1080 monitor that is a phone-sized strip in the middle of an empty window. The page scrolls, every panel (achievements, what's new, settings, summary) opens by pushing content down the same column, and the primary controls are far from the thing they act on. That is a mobile app in a browser tab, which is the opposite of how PC games are built.

What already exists and helps:
- Every game has Pyodide-run Python logic (`game.py`) separate from a thin HTML/CSS view bound by element ids. That separation is what makes a second presentation layer possible without touching mechanics.
- `shared/mobile-dock.js` already moves a game's action panel to a fixed bar on narrow screens by reparenting the node, and `shared/mobile-hud.js` pins a status bar. A PC layout is the same idea at the other end of the screen-size range.
- `shared/opening-screen.js` (New Game / Saves / Settings / Info / Feedback) is already a title-screen.
- `shared/theme*.js`, `shared/site-settings.js` (account-synced theme, text scale, reduced motion), `shared/tutorial.js`, `shared/keyboard-shortcuts.js`, `shared/save-widget.js` are shared, so a PC shell can reuse them.
- Continuum already has a Three.js scene and Le Champ de Mots a four-style visual switcher, so there is precedent for a richer "stage".

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

### 3.1 One switch, two layouts
`html[data-layout="pc"]` or `"classic"`. The classic layout is today's page, untouched. Default is automatic: PC layout when the window is at least ~1100px wide with a fine pointer, classic otherwise. A "Layout: Desktop / Classic" choice in each game's settings (and synced with the account settings that already hold theme and text scale) overrides it. Phones and small windows never get the PC layout unless chosen.

### 3.2 A shared shell instead of 13 rewrites
New `shared/pc-shell.js` and `shared/pc-shell.css`, included once per game like `mobile-dock.js`. Each game ships a small layout manifest (a JSON block next to its `index.html`) that says which existing elements belong in which zone:

```
zones:   hud (top bar) | rail (left actions) | stage (centre) | details (right) | log (bottom/right)
windows: { "achievements-panel": "Achievements", "changelog-panel": "What's New", "settings-panel": "Settings", ... }
```

In PC layout the shell builds the frame and moves (reparents) the existing nodes into the zones, the same technique as `mobile-dock.js`. Because the nodes themselves are moved, not copied, `game.py` keeps finding them by id and all listeners survive. In classic layout the shell puts them back. No mechanic or id changes, so the existing test suites keep applying.

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

### 3.6 Packaging (optional, later)
Static site stays the source of truth. If wanted later: install as a PWA in its own window (the manifest and service worker already exist, so `display: standalone`/`fullscreen` is a small step), and a wrapped desktop build (Tauri or Electron around the same files, Pyodide bundled for offline play) for itch.io or Steam. That is a distribution decision, not part of the layout work, and is not scheduled here.

## 4. The games, grouped by what their PC layout centres on

These groupings come from the current page structure; each game's real manifest gets worked out during its own conversion and may differ.

| Archetype | Games | PC layout idea |
|---|---|---|
| **Board/stage first** | Canopy, Le Champ de Mots, Trade Empire, Loop, SOL, Continuum | Large central board or map. Left rail holds the actions for the current selection (what `mobile-dock` pins at the bottom on phones). Right panel holds selection details, requests/events and the log. Top bar holds resources and time. Continuum's existing 3D scene becomes the stage with research and civic panels as windows. |
| **Dashboard + decisions** | Grid, Tide, Aftermath, Herd, Thaw, Drift | Central chart/region visual with the indicators around it. Decision cards (invest, policy, event choices) in a right column. Season/round advance as one prominent button plus a hotkey. History, summary and comparison panels become windows. |
| **Single board** | Signal | Centred puzzle with the tool palette on one side and daily/archive/stats on the other; it already has the smallest page, so it is the cheapest conversion. |

## 5. Rollout order

Sizes are relative effort: S, M, L, XL.

| Phase | What | Size |
|---|---|---|
| 0 | Decisions in section 8; capture current screenshots at 1920x1080 and 1440x900 as the "before" for the BCM evidence trail. | S |
| 1 | **Shell spike on one game.** Build `pc-shell` (layout switch, zones, manifest loader, window manager, Esc menu, loading screen) against **Canopy**: biggest game, a clear stage (the plot grid), existing `mobile-dock`. Done when Canopy plays fully in PC layout with classic one toggle away and its 557 tests unchanged. | L |
| 2 | **Prove the second archetype** on **Tide** (a dashboard game). If the manifest idea needs to change, this is where it shows. | M |
| 3 | Shared PC features: unified hotkeys and hint bar, tooltips, notification stack, settings (layout, UI scale, fullscreen, effects), account sync of the layout choice. | L |
| 4 | **Roll out by archetype**, board games first, then dashboards, then Signal: Le Champ de Mots, Trade Empire, Loop, SOL, Continuum; Grid, Aftermath, Herd, Thaw, Drift; Signal. One game per milestone, tagged like existing milestones. | XL (13 x M) |
| 5 | Visual identity pass per game (accent, stage art, transitions); audio if approved. | L |
| 6 | Optional: PWA fullscreen window, desktop wrapper, store pages. | decision first |

## 6. Testing and quality bar

- Existing per-game suites stay green unchanged; if a PC change needs a test edit, that is a signal the change touched mechanics and should be rethought.
- New shared tests: every id named in a game's manifest exists in its `index.html`; every zone/window referenced is known; classic layout restores the original DOM order.
- Live checks per game at 1920x1080, 1440x900, 1280x720 and 1100px, in light and dark themes, with the audit hygiene sweep (hidden-but-visible elements, unnamed controls, overflow) as the gate.
- Keyboard-only pass: every action reachable, focus never trapped, Esc always leaves.
- Pyodide boot time measured before and after (the loading screen must not make it worse).

## 7. Risks

- **Reparenting fragility.** Moving nodes works for `mobile-dock`, but some games re-render containers wholesale via `innerHTML`; any node the game destroys and recreates must be re-homed by the shell. The Canopy spike is meant to find these.
- **Per-game CSS entanglement.** Each stylesheet is 1,100 to 2,000 lines written for a 480px column. The shell must scope its changes under `html[data-layout="pc"]` so classic is unaffected, and games will still need their own spacing and chart-size rules.
- **Tutorial and tooltips.** `shared/tutorial.js` spotlights elements by selector and position; it must work when those elements are inside windows or zones.
- **Scope.** This touches all 13 games. Mitigation: one shared shell, one game per milestone, classic always available so nothing blocks shipping.
- **Audio expectation.** A PC feel without any sound will read as half done. The standing answer (planning/LATER.md) is "not now"; see decision 3.

## 8. Decisions needed

Each has a recommendation; "go with your recommendations" is a fine answer.

1. **What does "PC version" mean?** Recommended: the layout and feel change in section 2, same URL, same code, with the classic layout kept. Alternatives: also a downloadable desktop app (see 3.6), or a separate "PC edition" site. Which do you mean, or is it layout first and packaging later?
2. **Automatic or manual?** Recommended: automatic PC layout on wide windows with a Settings override remembered on the account, so visiting on a laptop just looks like a PC game.
3. **Audio.** Recommended: reopen it now for this project, starting with a shared, default-off sound system (muted by default, mute control in the in-game menu) and a few synthesized UI sounds with no asset files. This replaces the "ask around round 6" parking in `planning/LATER.md`. Or keep it parked and ship silent.
4. **Pilot game.** Recommended: Canopy first, then Tide. Say if you would rather start with another game (Signal is the cheapest, Continuum the most spectacular).
5. **Look.** Keep the current glass-panel style and refine it, or let each game get its own PC visual identity (more work, more PC-game-like)? Recommended: keep the shared frame, give each game its own accent and stage art over time.
6. **Controller support.** Recommended: not in this pass; design hotkeys so it can be added later.
7. **Distribution.** itch.io or Steam in the future, or just the website? Recommended: decide after phase 4; it does not change the layout work.
8. **Mobile.** Recommended: unchanged and still first-class (its own dock and HUD), tested alongside every PC milestone.

## 9. Not part of this plan

New mechanics or content, backend changes, multiplayer (see `planning/MULTIPLAYER-SCOPING.md`), new games, and anything that changes how saves or achievements work. If a PC layout seems to need one of those, it gets its own item.
