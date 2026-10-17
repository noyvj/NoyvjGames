// Boot: load Pyodide, write the shared Python helpers and every canopy_*.py module into Pyodide's file system, then
// run game.py (the entry point), which imports them. Add a new Python module to CANOPY_PY_MODULES below (and to
// sw.js and offline-manifest.json) or the page cannot import it. Keep the list in dependency order; it must match
// _PART_NAMES in game.py (a test checks both against the .py files on disk).
const CANOPY_PY_MODULES = [
  "canopy_runstate.py",
  "canopy_rules.py",
  "canopy_worldvars.py",
  "canopy_helpers.py",
  "canopy_valuation.py",
  "canopy_records.py",
  "canopy_weather.py",
  "canopy_effects.py",
  "canopy_clearcut.py",
  "canopy_plot.py",
  "canopy_forestlog.py",
  "canopy_gridview.py",
  "canopy_carbon.py",
  "canopy_lifetime.py",
  "canopy_community.py",
  "canopy_layout.py",
  "canopy_stakeholders.py",
  "canopy_plotsheet.py",
  "canopy_regions.py",
  "canopy_summary.py",
  "canopy_labui.py",
  "canopy_achievements.py",
  "canopy_infopanels.py",
  "canopy_ghost.py",
  "canopy_charts.py",
  "canopy_realworld.py",
  "canopy_forecast.py",
  "canopy_tend.py",
  "canopy_challenge.py",
  "canopy_almanac.py",
  "canopy_contracts.py",
  "canopy_levels.py",
  "canopy_vault.py",
  "canopy_expedition.py",
  "canopy_gbstate.py",
  "canopy_survey.py",
  "canopy_hazards.py",
  "canopy_session.py",
  "canopy_comfort.py",
  "canopy_sessionview.py",
  "canopy_savestate.py",
  "canopy_renderer.py",
  "canopy_handlers_core.py",
  "canopy_handlers_panels.py",
  "canopy_handlers_modes.py",
  "canopy_loading.py",
  "canopy_tick.py",
  "canopy_setup.py",
];

async function main() {
  const pyodide = await loadPyodide();
  window.pyodide = pyodide; // exposed for the save/load bridge below
  // game.py imports these (see the list at the top of this file); same fetch-then-writeFile pattern as Continuum's ENGINE_MODULES.
  await Promise.all(CANOPY_PY_MODULES.map(async (name) => {
    const moduleSource = await (await fetch(name)).text();
    pyodide.FS.writeFile(name, moduleSource, { encoding: "utf8" });
  }));
  // Shared info-page widget (see shared/info_page.py) -- written into
  // Pyodide's virtual filesystem before game.py runs so `import
  // info_page` resolves normally, same pattern as Continuum's
  // ENGINE_MODULES loop.
  const infoPageSource = await (await fetch("../../shared/info_page.py")).text();
  pyodide.FS.writeFile("info_page.py", infoPageSource, { encoding: "utf8" });
  // Shared skill-tree rules (shared/skill_tree.py), the Python mirror of skill-tree.js: the Seed Vault
  // (GB-10/GB-26) validates, buys and refunds through it, so the page and the game never disagree.
  const skillTreeSource = await (await fetch("../../shared/skill_tree.py")).text();
  pyodide.FS.writeFile("skill_tree.py", skillTreeSource, { encoding: "utf8" });
  // Shared seeded-run helper (shared/seed.py): the Expedition's seed (GB-3) only decides the map.
  const seedSource = await (await fetch("../../shared/seed.py")).text();
  pyodide.FS.writeFile("seed.py", seedSource, { encoding: "utf8" });
  // Z-3e: shared best-session ghost (shared/ghost.py): the standing value per tick is recorded and compared through it.
  const ghostSource = await (await fetch("../../shared/ghost.py")).text();
  pyodide.FS.writeFile("ghost.py", ghostSource, { encoding: "utf8" });
  // ACHIEVEMENTS-SYSTEM-DESIGN.md's loading contract: fetch the static
  // catalog and hand it to Python as a window global *before* game.py
  // runs, same pattern SOL's reference integration established.
  const [achievementsJson, changelogJson, code] = await Promise.all([
    fetch("achievements.json").then((response) => response.text()),
    fetch("changelog.json").then((response) => response.text()),
    fetch("game.py").then((response) => response.text()),
  ]);
  window.ACHIEVEMENTS_JSON = achievementsJson;
  window.CHANGELOG_JSON = changelogJson;
  await pyodide.runPythonAsync(code);

  if (window.GameTutorial) {
    GameTutorial.init(window.CANOPY_PC_TUTORIAL_STEPS || CANOPY_TUTORIAL_STEPS, { gameId: "canopy" });
  }
  if (window.MobileHud) {
    MobileHud.init([
      { selector: "#income-display", label: "" },
      { selector: "#standing-value-display", label: "" },
    ]);
  }
  if (window.MobileDock) {
    MobileDock.init("#action-panel");
    // B15: same treatment, extended to the stats + legend panels
    // (wrapped together in #mobile-info-dock so they move as one
    // unit -- see the comment on that div in the markup above).
    MobileDock.init("#mobile-info-dock");
  }
  // Collapse/expand toggle for the docked stats+legend sheet on
  // mobile -- plain JS, not Python/game.py, since it's pure UI chrome
  // with no game-state dependency (documented exception, same class
  // as the feedback-prompt script below). No-ops harmlessly above the
  // mobile breakpoint since the toggle button is CSS-hidden there.
  const mobileInfoDock = document.getElementById("mobile-info-dock");
  const mobileInfoDockToggle = document.getElementById("mobile-info-dock-toggle");
  // UX-1: the docked action panel's real height drives where the Stats pill,
  // the Story pill and the page's bottom padding sit (CSS reads
  // --action-dock-h). The "..." button unfolds the extras the dock hides.
  const actionPanelEl = document.getElementById("action-panel");
  const actionDockMore = document.getElementById("action-dock-more");
  function publishDockHeight() {
    const docked = actionPanelEl.classList.contains("mobile-docked");
    const h = docked ? Math.ceil(actionPanelEl.getBoundingClientRect().height) : 0;
    if (h > 0) document.documentElement.style.setProperty("--action-dock-h", h + "px");
    else document.documentElement.style.removeProperty("--action-dock-h");
  }
  if (window.ResizeObserver) new ResizeObserver(publishDockHeight).observe(actionPanelEl);
  window.addEventListener("resize", publishDockHeight);
  publishDockHeight();
  actionDockMore.addEventListener("click", () => {
    const open = actionPanelEl.classList.toggle("action-dock--expanded");
    actionDockMore.setAttribute("aria-expanded", String(open));
    actionDockMore.textContent = open ? "×" : "⋯";
    publishDockHeight();
  });
  mobileInfoDockToggle.addEventListener("click", () => {
    const expanded = mobileInfoDock.classList.toggle("mobile-info-dock--expanded");
    mobileInfoDockToggle.textContent = expanded ? "📊 Stats & Legend ▴" : "📊 Stats & Legend ▾";
  });

  // B8: hover/tap tooltip on plot tiles, showing the exact numeric
  // value + degradation level game.py already computed into each
  // tile's `data-tooltip` attribute (see _plot_tooltip_text() in
  // game.py). Delegated on #plot-grid (which persists across
  // re-renders) rather than per-tile, since render_grid() rebuilds
  // every tile from scratch on every render -- plain DOM/positioning
  // logic with no game-state dependency, so it's plain JS rather than
  // round-tripping through Pyodide (documented exception, same class
  // as the feedback-prompt script below).
  const plotGrid = document.getElementById("plot-grid");
  const plotTooltip = document.getElementById("plot-tooltip");
  function showPlotTooltip(target) {
    const text = target.getAttribute && target.getAttribute("data-tooltip");
    if (!text) return;
    plotTooltip.textContent = text;
    plotTooltip.hidden = false;
    const rect = target.getBoundingClientRect();
    const tooltipRect = plotTooltip.getBoundingClientRect();
    let left = rect.left + rect.width / 2 - tooltipRect.width / 2;
    left = Math.max(8, Math.min(left, window.innerWidth - tooltipRect.width - 8));
    plotTooltip.style.left = `${left}px`;
    plotTooltip.style.top = `${rect.top - tooltipRect.height - 8}px`;
  }
  function hidePlotTooltip() {
    plotTooltip.hidden = true;
  }
  plotGrid.addEventListener("mouseover", (e) => {
    if (e.target.classList && e.target.classList.contains("plot-tile")) {
      showPlotTooltip(e.target);
    }
  });
  plotGrid.addEventListener("mouseout", (e) => {
    if (e.target.classList && e.target.classList.contains("plot-tile")) {
      hidePlotTooltip();
    }
  });
  plotGrid.addEventListener("focusin", (e) => {
    if (e.target.classList && e.target.classList.contains("plot-tile")) {
      showPlotTooltip(e.target);
    }
  });
  plotGrid.addEventListener("focusout", (e) => {
    if (e.target.classList && e.target.classList.contains("plot-tile")) {
      hidePlotTooltip();
    }
  });
  plotGrid.addEventListener("click", (e) => {
    if (e.target.classList && e.target.classList.contains("plot-tile")) {
      // Touch devices have no hover -- show briefly on tap instead.
      showPlotTooltip(e.target);
      setTimeout(hidePlotTooltip, 2200);
    }
  });

  // B12: a floating badge when a stakeholder request is pending and
  // the player has scrolled the panel itself out of view. Plain JS
  // (IntersectionObserver + a MutationObserver on the panel's own
  // `hidden` attribute, which game.py's render_stakeholder_panel()
  // already flips every render) -- no game-state logic, so nothing
  // for the fake-DOM pytest harness to meaningfully exercise; this
  // one is verified live in a real browser instead (see this game's
  // CLAUDE.md build notes).
  const stakeholderPanel = document.getElementById("stakeholder-panel");
  const stakeholderBadge = document.getElementById("stakeholder-badge");
  let stakeholderPanelIntersecting = true;
  function updateStakeholderBadge() {
    const pending = !stakeholderPanel.hidden;
    stakeholderBadge.hidden = !(pending && !stakeholderPanelIntersecting);
  }
  if (window.IntersectionObserver) {
    new IntersectionObserver(
      (entries) => {
        stakeholderPanelIntersecting = entries[0].isIntersecting;
        updateStakeholderBadge();
      },
      { threshold: 0 }
    ).observe(stakeholderPanel);
  }
  if (window.MutationObserver) {
    new MutationObserver(updateStakeholderBadge).observe(stakeholderPanel, {
      attributes: true,
      attributeFilter: ["hidden"],
    });
  }
  stakeholderBadge.addEventListener("click", () => {
    stakeholderPanel.scrollIntoView({ behavior: "smooth", block: "center" });
  });

  // B16: arrow-key navigation across the plot grid (Enter/Space to
  // act on the focused tile is already native <button> behavior, so
  // there's nothing to add for that half). Plain JS for the same
  // reason as the tooltip above -- pure focus-management, no game
  // state. Reads the grid's real column count from the `data-cols`
  // attribute game.py's render_grid() sets, rather than hardcoding it
  // a second time here.
  //
  // UX-3 (2026-10-07): this used to listen on #plot-grid and only act
  // when a tile was the focused element, but render_grid() rebuilds
  // every tile each second (and on every click), which silently drops
  // focus to <body>: so after clicking a plot, or one second after
  // tabbing to one, the arrow keys did nothing. Now (a) the listener is
  // on the document and starts from the focused tile, else the plot the
  // keyboard/pointer last touched, else the selected plot (on the
  // Desktop boot, where the page never scrolls, plot 0); and (b) a
  // childList observer puts focus back on the same tile after every
  // rebuild, so focus survives the tick. With no plot in play on the
  // Classic page the arrows keep their normal job of scrolling it.
  const ARROW_DELTA = {
    ArrowLeft: -1,
    ArrowRight: 1,
    ArrowUp: "up",
    ArrowDown: "down",
  };
  let keyboardPlotIndex = null; // the plot the keyboard/pointer last touched
  let keyboardFocusWanted = false; // true while focus "belongs" to the grid
  function plotIndexOf(el) {
    const m = el && el.id && /^plot-(\d+)$/.exec(el.id);
    return m && el.parentNode === plotGrid ? parseInt(m[1], 10) : null;
  }
  document.addEventListener("focusin", (e) => {
    const index = plotIndexOf(e.target);
    keyboardFocusWanted = index !== null;
    if (index !== null) keyboardPlotIndex = index;
  });
  plotGrid.addEventListener("pointerdown", (e) => {
    const index = plotIndexOf(e.target);
    if (index !== null) { keyboardPlotIndex = index; keyboardFocusWanted = true; }
  });
  if (window.MutationObserver) {
    new MutationObserver(() => {
      if (!keyboardFocusWanted || keyboardPlotIndex === null) return;
      const active = document.activeElement;
      if (active && active !== document.body && active !== document.documentElement) return;
      const tile = document.getElementById(`plot-${keyboardPlotIndex}`);
      if (tile && tile.parentNode === plotGrid) tile.focus({ preventScroll: true });
    }).observe(plotGrid, { childList: true });
  }
  document.addEventListener("keydown", (e) => {
    const delta = ARROW_DELTA[e.key];
    if (delta === undefined || e.defaultPrevented) return;
    if (e.ctrlKey || e.metaKey || e.altKey || e.shiftKey) return;
    const target = e.target;
    const tag = (target && target.tagName) || "";
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || (target && target.isContentEditable)) return;
    // Not while something modal is up: opening screen, confirm dialog, tutorial, shortcuts help.
    const modal = document.querySelector("#opening-screen, #confirm-dialog-overlay:not([hidden]), #tutorial-overlay:not([hidden]), #kb-shortcuts-panel:not([hidden]), #level-select:not([hidden])");
    if (modal && modal.getBoundingClientRect().width > 0) return;
    let index = plotIndexOf(document.activeElement);
    if (index === null && keyboardPlotIndex !== null && keyboardFocusWanted) index = keyboardPlotIndex;
    if (index === null) {
      const selected = plotGrid.querySelector(".plot-selected");
      index = plotIndexOf(selected);
    }
    if (index === null && keyboardPlotIndex !== null) index = keyboardPlotIndex;
    if (index === null) {
      // Nothing in play yet: on the Desktop boot the page does not scroll, so start at the first plot.
      if (window.NOYVJ_LAYOUT !== "pc") return;
      index = 0;
      const first = document.getElementById(`plot-${index}`); // index is 0 here; the tile ids are built in Python (_plot_tile_id)
      if (first) { e.preventDefault(); first.focus({ preventScroll: true }); }
      return;
    }
    const cols = parseInt(plotGrid.getAttribute("data-cols"), 10) || 6;
    const col = index % cols;
    let nextIndex = null;
    if (delta === "up") nextIndex = index - cols;
    else if (delta === "down") nextIndex = index + cols;
    else if (delta === -1 && col > 0) nextIndex = index - 1; // no wrap off the left edge
    else if (delta === 1 && col < cols - 1) nextIndex = index + 1; // no wrap off the right edge
    e.preventDefault(); // the arrows belong to the grid once a plot is in play, even at an edge
    if (nextIndex === null) return;
    const nextTile = document.getElementById(`plot-${nextIndex}`);
    if (nextTile) nextTile.focus({ preventScroll: false });
  });

  // UX-4: Escape dismisses the shared confirm dialog (Reset Session uses it). The dialog
  // has no Escape handling of its own, and on the Desktop boot the same key would open the
  // Menu behind it. A window-level capture listener runs before every document-level one.
  window.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    // W-1: the level select closes itself on Escape; flag the event so the Desktop boot does not
    // also open its Menu (or close a window) behind it. Not stopped, so the level select still sees it.
    const LEVEL_SELECT_DOM_ID = "level-select"; // the id shared/level-select.js gives its overlay (domId)
    const levelScreen = document.getElementById(LEVEL_SELECT_DOM_ID);
    if (levelScreen && !levelScreen.hidden) { e.__pcMenuOpened = true; return; }
    const overlay = document.getElementById("confirm-dialog-overlay");
    const cancel = document.getElementById("confirm-dialog-cancel");
    if (!overlay || overlay.hidden || !cancel) return;
    e.preventDefault();
    e.stopPropagation();
    cancel.click();
  }, true);

  // B16: "N" selects the plot the pending stakeholder request names
  // (Python does the selecting; this just routes the key and moves
  // focus/scroll). Ignored while typing in any field.
  document.addEventListener("keydown", (e) => {
    if (e.key !== "n" && e.key !== "N") return;
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    const tag = (e.target && e.target.tagName) || "";
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || (e.target && e.target.isContentEditable)) return;
    const fn = pyodide.globals.get("select_stakeholder_plot");
    const index = fn ? fn() : null;
    if (index === null || index === undefined) return;
    const tile = document.getElementById(`plot-${index}`);
    if (tile) tile.focus();
  });

  // GB-4/GB-2/GB-18 hotkeys: T tends the plot under the pointer (or the
  // last focused one, else the selected plot), G catches a golden
  // seedling wherever it is, U undoes the last clear. Python does the
  // work; this only routes the key. Ignored while typing in a field.
  let hoveredPlotIndex = null;
  plotGrid.addEventListener("mouseover", (e) => {
    const m = e.target && e.target.id && e.target.id.match(/^plot-(\d+)$/);
    if (m) hoveredPlotIndex = parseInt(m[1], 10);
  });
  plotGrid.addEventListener("focusin", (e) => {
    const m = e.target && e.target.id && e.target.id.match(/^plot-(\d+)$/);
    if (m) hoveredPlotIndex = parseInt(m[1], 10);
  });
  plotGrid.addEventListener("mouseleave", () => { hoveredPlotIndex = null; });
  document.addEventListener("keydown", (e) => {
    const key = e.key && e.key.toLowerCase();
    if (key !== "t" && key !== "g" && key !== "u" && key !== "c" && key !== "r" && key !== "p" && key !== "k") return;
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    const tag = (e.target && e.target.tagName) || "";
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || (e.target && e.target.isContentEditable)) return;
    if (key === "t") {
      const fn = pyodide.globals.get("tend_plot");
      if (fn) fn(hoveredPlotIndex);
    } else if (key === "g") {
      const fn = pyodide.globals.get("collect_golden_seedling");
      if (fn) fn();
    } else if (key === "p") {
      // GB-13: P drives off the poacher wherever it is (Poacher Patrol level only).
      const fn = pyodide.globals.get("hotkey_drive_off_poacher");
      if (fn) fn();
    } else if (key === "c" || key === "r" || key === "k") {
      // B-7: C clears and R replants the SELECTED plot (select one with Enter or a click first).
      // GB-21: K clear-cuts it (a quick payout for a soil dip that heals).
      const modal = document.querySelector("#opening-screen, #confirm-dialog-overlay:not([hidden]), #tutorial-overlay:not([hidden]), #kb-shortcuts-panel:not([hidden]), #level-select:not([hidden])");
      if (modal && modal.getBoundingClientRect().width > 0) return;
      const fn = pyodide.globals.get(key === "c" ? "hotkey_clear_selected" : key === "k" ? "hotkey_clear_cut_selected" : "hotkey_replant_selected");
      if (fn) fn();
    } else {
      const fn = pyodide.globals.get("undo_last_clear");
      if (fn) fn();
    }
  });

  // B26: keep a subtle glow on whichever plot the pointer/focus last
  // touched. render_grid() rebuilds every tile each tick, so remember
  // the tile id and re-apply after each rebuild (a childList observer;
  // adding a class is not a childList change, so no feedback loop).
  let lastHoveredTileId = null;
  function applyLastHovered() {
    plotGrid.querySelectorAll(".plot-last-hovered").forEach((el) => el.classList.remove("plot-last-hovered"));
    if (!lastHoveredTileId) return;
    const tile = document.getElementById(lastHoveredTileId);
    if (tile) tile.classList.add("plot-last-hovered");
  }
  plotGrid.addEventListener("mouseover", (e) => {
    if (e.target.classList && e.target.classList.contains("plot-tile")) {
      lastHoveredTileId = e.target.id;
      applyLastHovered();
    }
  });
  if (window.MutationObserver) {
    new MutationObserver(applyLastHovered).observe(plotGrid, { childList: true });
  }

  // B19: opt-in community comparison against GET /stats/games/canopy and
  // its /percentile endpoint (Z1). Plain JS like the feedback prompt:
  // it's a read-only fetch + text render with no game-state logic. The
  // endpoint may not be deployed yet, so every failure path ends in the
  // same plain "not available yet" message, and nothing is fetched until
  // the player presses the button (so no background request noise).
  const COMMUNITY_FIELDS = [
    ["standing_value", "Standing forest value"],
    ["total_income", "Harvested income"],
    ["community_relations", "Community relations"],
    ["total_replants", "Plots replanted"],
    ["total_recoveries", "Plots recovered"],
  ];
  const communityButton = document.getElementById("community-forest-button");
  const communityResult = document.getElementById("community-forest-result");
  communityButton.addEventListener("click", async () => {
    const API = "https://noyvjgames.fastapicloud.dev";
    const layoutFn = pyodide.globals.get("layout_active");
    if (layoutFn && layoutFn()) {  // B-29: custom shapes are not comparable with the standard grid
      communityResult.textContent = "Custom layouts are kept out of the community comparison. Switch back to the full grid to compare.";
      return;
    }
    communityButton.disabled = true;
    communityResult.textContent = "Loading...";
    try {
      const summaryRes = await fetch(`${API}/stats/games/canopy`);
      if (!summaryRes.ok) throw new Error(`status ${summaryRes.status}`);
      const summary = await summaryRes.json();
      if (summary.suppressed) {
        communityResult.textContent = `Not enough players yet for an anonymous comparison (needs ${summary.min_bucket}+).`;
        return;
      }
      const rows = [];
      for (const [field, label] of COMMUNITY_FIELDS) {
        const info = summary.fields && summary.fields[field];
        if (!info) continue;
        // standing_value is derived (a sum over the plots), so it comes from the function, not a global.
        const mine = field === "standing_value"
          ? Number(pyodide.globals.get("standing_forest_value")())
          : Number(pyodide.globals.get("community_field_value")(field));
        let pct = "";
        try {
          const pRes = await fetch(`${API}/stats/games/canopy/percentile?field=${field}&value=${encodeURIComponent(mine)}`);
          if (pRes.ok) {
            const p = await pRes.json();
            if (!p.suppressed && typeof p.percentile === "number") pct = `${Math.round(p.percentile)}th percentile`;
          }
        } catch (err) { /* percentile is a bonus; the average still shows */ }
        rows.push(`${label}: you ${mine.toFixed(1)} · community average ${Number(info.mean).toFixed(1)}${pct ? " · " + pct : ""}`);
      }
      communityResult.textContent = rows.length
        ? rows.join("\n")
        : "Not enough players yet for an anonymous comparison.";
    } catch (err) {
      communityResult.textContent = "Community comparison isn't available yet. Check back later.";
    } finally {
      communityButton.disabled = false;
    }
  });

  // B18: copy the playstyle badge next to the share snippet's copy.
  const badgeCopyButton = document.getElementById("session-summary-copy-badge-button");
  badgeCopyButton.addEventListener("click", async () => {
    const badgeLine = document.getElementById("session-summary-badge").textContent.replace("Playstyle badge:", "Canopy playstyle badge:");
    try {
      await navigator.clipboard.writeText(badgeLine);
      document.getElementById("session-summary-copy-status").textContent = "Badge copied!";
    } catch (err) {
      document.getElementById("session-summary-copy-status").textContent = "Couldn't copy the badge — select the text manually.";
    }
    setTimeout(() => {
      document.getElementById("session-summary-copy-status").textContent = "";
    }, 2500);
  });

  // B18: copy-to-clipboard for the session-summary share snippet.
  // Plain JS -- the Clipboard API isn't something game.py's fake-DOM
  // test harness can meaningfully exercise, same documented-exception
  // class as the plot tooltip above.
  const shareCopyButton = document.getElementById("session-summary-copy-button");
  const shareCopyStatus = document.getElementById("session-summary-copy-status");
  shareCopyButton.addEventListener("click", async () => {
    const text = document.getElementById("session-summary-share-text").textContent;
    try {
      await navigator.clipboard.writeText(text);
      shareCopyStatus.textContent = "Copied!";
    } catch (err) {
      shareCopyStatus.textContent = "Couldn't copy — select the text above manually.";
    }
    setTimeout(() => {
      shareCopyStatus.textContent = "";
    }, 2500);
  });
}
main();
