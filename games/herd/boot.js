// Boot: load Pyodide, write the shared Python helpers and every herd_*.py module into Pyodide's file system, then run
// game.py (the entry point), which imports them. Add a new Python module to HERD_PY_MODULES below (and to sw.js and
// offline-manifest.json) or the page cannot import it.
const HERD_PY_MODULES = [
  "herd_rules.py",
  "herd_runstate.py",
  "herd_util.py",
  "herd_model.py",
  "herd_purchases.py",
  "herd_blind.py",
  "herd_visuals.py",
  "herd_messages.py",
  "herd_achievements.py",
  "herd_pasture.py",
  "herd_changelog.py",
  "herd_sandbox.py",
  "herd_barns.py",
  "herd_loadouts.py",
  "herd_rules_ui.py",
  "herd_ledger.py",
  "herd_succession.py",
  "herd_extras.py",
  "herd_collection.py",
  "herd_round.py",
  "herd_explain.py",
  "herd_planner.py",
  "herd_pins.py",
  "herd_mixer.py",
  "herd_family.py",
  "herd_profile.py",
  "herd_savegame.py",
  "herd_settings_code.py",
  "herd_summary.py",
  "herd_renderer.py",
  "herd_loading.py",
  "herd_handlers_play.py",
  "herd_handlers_panels.py",
];

async function main() {
  const pyodide = await loadPyodide();
  window.pyodide = pyodide; // exposed for the save/load bridge below
  // game.py imports these (see the list at the top of this file); same fetch-then-writeFile pattern as Continuum's ENGINE_MODULES.
  await Promise.all(HERD_PY_MODULES.map(async (name) => {
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
  // resolves normally. Powers the F15 real-world comparison chart.
  const comparisonChartSource = await (await fetch("../../shared/comparison_chart.py")).text();
  pyodide.FS.writeFile("comparison_chart.py", comparisonChartSource, { encoding: "utf8" });
  // Z-3e: the shared best-farm ghost (shared/ghost.py): rounds are recorded and compared through it.
  const ghostSource = await (await fetch("../../shared/ghost.py")).text();
  pyodide.FS.writeFile("ghost.py", ghostSource, { encoding: "utf8" });
  // F-25: the shared progress-code helper (shared/export_progress.py) for the settings code.
  const exportProgressSource = await (await fetch("../../shared/export_progress.py")).text();
  pyodide.FS.writeFile("export_progress.py", exportProgressSource, { encoding: "utf8" });
  // ACHIEVEMENTS-SYSTEM-DESIGN.md §2/§7: fetch achievements.json
  // alongside game.py and hand it to Python as a window global before
  // game.py runs, same convention as SOL/Grid/Canopy.
  // "What's New" changelog (K16, planning/TODO.md) -- same fetch
  // convention as achievements.json above.
  const [achievementsJson, changelogJson, code] = await Promise.all([
    fetch("achievements.json").then((response) => response.text()),
    fetch("changelog.json").then((response) => response.text()),
    fetch("game.py").then((response) => response.text()),
  ]);
  window.ACHIEVEMENTS_JSON = achievementsJson;
  window.CHANGELOG_JSON = changelogJson;
  await pyodide.runPythonAsync(code);

  if (window.GameTutorial) {
    GameTutorial.init(herdTutorialSteps(),{ gameId: "herd" });
  }
  if (window.MobileHud) {
    MobileHud.init([
      { selector: "#funds-display" },
      { selector: "#herd-display" },
      { selector: "#methane-display" },
    ]);
  }
}
main();
