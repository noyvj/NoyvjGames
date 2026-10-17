// Boot: load Pyodide, write the shared Python helpers and every grid_*.py module into Pyodide's file system, then run
// game.py (the entry point), which imports them. Add a new Python module to GRID_PY_MODULES below (and to sw.js and
// offline-manifest.json) or the page cannot import it. Keep the list in dependency order; it must match
// _PART_NAMES in game.py (a test checks both against the .py files on disk).
const GRID_PY_MODULES = [
  "grid_rules.py",
  "grid_runstate.py",
  "grid_state_round.py",
  "grid_state_extras.py",
  "grid_state.py",
  "grid_sandbox_state.py",
  "grid_whatif.py",
  "grid_career_data.py",
  "grid_career_actions.py",
  "grid_prefs.py",
  "grid_achievements.py",
  "grid_shadow.py",
  "grid_savegame.py",
  "grid_trend.py",
  "grid_panels.py",
  "grid_views.py",
  "grid_messages.py",
  "grid_announce.py",
  "grid_difficulty.py",
  "grid_summary.py",
  "grid_skyline.py",
  "grid_achievement_cards.py",
  "grid_runs.py",
  "grid_sandbox.py",
  "grid_fleet.py",
  "grid_runsetup.py",
  "grid_coach.py",
  "grid_arbitrage.py",
  "grid_schematic.py",
  "grid_realgrid.py",
  "grid_slots.py",
  "grid_gridley.py",
  "grid_callouts.py",
  "grid_advance.py",
  "grid_careerpanel.py",
  "grid_renderer.py",
  "grid_loading.py",
  "grid_handlers_panels.py",
  "grid_handlers_play.py",
];

async function main() {
  const pyodide = await loadPyodide();
  window.pyodide = pyodide; // exposed for the save/load bridge below
  // game.py imports these (see the list at the top of this file); same fetch-then-writeFile pattern as Continuum's ENGINE_MODULES.
  await Promise.all(GRID_PY_MODULES.map(async (name) => {
    const moduleSource = await (await fetch(name)).text();
    pyodide.FS.writeFile(name, moduleSource, { encoding: "utf8" });
  }));
  // Shared info-page widget (see shared/info_page.py) -- written into
  // Pyodide's virtual filesystem before game.py runs so `import
  // info_page` resolves normally, same pattern as Continuum's
  // ENGINE_MODULES loop.
  const infoPageSource = await (await fetch("../../shared/info_page.py")).text();
  pyodide.FS.writeFile("info_page.py", infoPageSource, { encoding: "utf8" });
  // Shared comparison-chart component (Z17, see
  // shared/comparison_chart.py) -- same fetch-then-writeFile pattern
  // as info_page.py above, so game.py's `import comparison_chart`
  // resolves normally. Grid's own C15/global-comparison trend-graph
  // code is the reference integration this shared module was
  // generalized from.
  const comparisonChartSource = await (await fetch("../../shared/comparison_chart.py")).text();
  pyodide.FS.writeFile("comparison_chart.py", comparisonChartSource, { encoding: "utf8" });
  // Shared seeded-run helper (shared/seed.py, Z-1) and skill-tree rules (shared/skill_tree.py, W-3):
  // game.py's `import seed` / `import skill_tree` resolve from the virtual filesystem the same way.
  const seedSource = await (await fetch("../../shared/seed.py")).text();
  pyodide.FS.writeFile("seed.py", seedSource, { encoding: "utf8" });
  // Shared ghost-run trace (shared/ghost.py, Z-3c): the best run's clean share and funds are recorded and compared through it.
  const ghostSource = await (await fetch("../../shared/ghost.py")).text();
  pyodide.FS.writeFile("ghost.py", ghostSource, { encoding: "utf8" });
  const skillTreeSource = await (await fetch("../../shared/skill_tree.py")).text();
  pyodide.FS.writeFile("skill_tree.py", skillTreeSource, { encoding: "utf8" });
  const [achievementsJson, changelogJson, code] = await Promise.all([
    fetch("achievements.json").then((response) => response.text()),
    fetch("changelog.json").then((response) => response.text()),
    fetch("game.py").then((response) => response.text()),
  ]);
  window.ACHIEVEMENTS_JSON = achievementsJson;
  window.CHANGELOG_JSON = changelogJson;
  await pyodide.runPythonAsync(code);

  if (window.GameTutorial) {
    GameTutorial.init(window.GRID_PC_TUTORIAL_STEPS || GRID_TUTORIAL_STEPS, { gameId: "grid" });
  }
  if (window.MobileHud) {
    // C-20: round and capacity join funds, demand and emissions (the bar scrolls sideways when it is full).
    MobileHud.init([
      { selector: "#round-display", label: "Round" },
      { selector: "#funds-display", label: "Funds" },
      { selector: "#demand-display", label: "Demand" },
      { selector: "#capacity-display", label: "Capacity" },
      { selector: "#emissions-display", label: "Emissions" },
    ]);
  }
  if (window.MobileDock) {
    // TODO.md's "finish the mobile-dock rollout" goal labels this
    // "Grid — plant-build action row", but Grid's six plant rows
    // already keep their own Build/Retire/Maintain buttons inline
    // (unlike Canopy's #plot-grid/#action-panel split, there's no
    // far-apart selection-vs-action gap within a row). The real
    // equivalent friction here is the single action every round of
    // building funnels toward -- Advance Round -- sitting at the very
    // bottom of a long page (status panel + trend graph + six plant
    // rows). Docking it mirrors Canopy/Trade Empire's exact pattern
    // (act on your build without scrolling back to the bottom).
    MobileDock.init("#advance-round-button");
  }
}
main();
