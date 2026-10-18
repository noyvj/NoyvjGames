// Boot: load Pyodide, write the shared Python helper and every drift_*.py module into Pyodide's file system, then
// run game.py (the entry point), which imports them. Add a new Python module to DRIFT_PY_MODULES below (and to
// sw.js and offline-manifest.json) or the page cannot import it. Keep the list in dependency order; it must match
// _PART_NAMES in game.py (a test checks both against the .py files on disk).
const DRIFT_PY_MODULES = [
  "drift_runstate.py",
  "drift_rules.py",
  "drift_model_region.py",
  "drift_regional.py",
  "drift_trendgraph.py",
  "drift_visuals.py",
  "drift_messages.py",
  "drift_achievements.py",
  "drift_pages.py",
  "drift_ledger.py",
  "drift_calendar.py",
  "drift_collection.py",
  "drift_undo.py",
  "drift_tiers.py",
  "drift_plans.py",
  "drift_assist.py",
  "drift_settings.py",
  "drift_loading.py",
  "drift_report.py",
  "drift_newsview.py",
  "drift_renderer.py",
  "drift_handlers.py",
  "drift_savestate.py",
];

async function main() {
  const pyodide = await loadPyodide();
  window.pyodide = pyodide; // exposed for the save/load bridge below
  // Shared info-page widget (see shared/info_page.py) -- written into
  // Pyodide's virtual filesystem before game.py runs so `import
  // info_page` resolves normally, same pattern as Continuum's
  // ENGINE_MODULES loop.
  const infoPageSource = await (await fetch("../../shared/info_page.py")).text();
  pyodide.FS.writeFile("info_page.py", infoPageSource, { encoding: "utf8" });
  // game.py imports these (see the list at the top of this file); same fetch-then-writeFile pattern as Continuum's ENGINE_MODULES.
  await Promise.all(DRIFT_PY_MODULES.map(async (name) => {
    const moduleSource = await (await fetch(name)).text();
    pyodide.FS.writeFile(name, moduleSource, { encoding: "utf8" });
  }));
  const [achievementsJson, changelogJson, code] = await Promise.all([
    fetch("achievements.json").then((response) => response.text()),
    fetch("changelog.json").then((response) => response.text()),
    fetch("game.py").then((response) => response.text()),
  ]);
  window.ACHIEVEMENTS_JSON = achievementsJson;
  window.CHANGELOG_JSON = changelogJson;
  await pyodide.runPythonAsync(code);

  if (window.GameTutorial) {
    GameTutorial.init(window.DRIFT_PC_TUTORIAL_STEPS || DRIFT_TUTORIAL_STEPS, { gameId: "drift" });
  }
  if (window.MobileHud) {
    MobileHud.init([
      { selector: "#hud-round-display", label: "" },
      { selector: "#hud-strain-display", label: "Strain" },
      { selector: "#hud-wellbeing-display", label: "Wellbeing" },
    ]);
  }
}
main();
