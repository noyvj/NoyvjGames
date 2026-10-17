// Boot: load Pyodide, write the shared Python helpers, challenges.py and every sol_*.py module into Pyodide's file system,
// then run game.py (the entry point), which imports them. Add a new Python module to SOL_PY_MODULES below (and to
// sw.js and offline-manifest.json) or the page cannot import it. Keep the list in dependency order; it must match
// _PART_NAMES in game.py (a test checks both against the .py files on disk).
const SOL_PY_MODULES = [
  "sol_runstate.py",
  "sol_rules.py",
  "sol_util.py",
  "sol_story.py",
  "sol_runmods.py",
  "sol_scarcity.py",
  "sol_econ.py",
  "sol_rhythm.py",
  "sol_observatory.py",
  "sol_codex.py",
  "sol_charter.py",
  "sol_doctrines.py",
  "sol_sim.py",
  "sol_headless.py",
  "sol_achievements.py",
  "sol_panels.py",
  "sol_statsview.py",
  "sol_planner.py",
  "sol_overview.py",
  "sol_actions.py",
  "sol_capsules.py",
  "sol_savestate.py",
  "sol_scarcity_run.py",
  "sol_ghost.py",
  "sol_scarcity_panel.py",
  "sol_charter_panel.py",
  "sol_run.py",
  "sol_session.py",
  "sol_handlers.py",
];

async function main() {
  const pyodide = await loadPyodide();
  window.pyodide = pyodide; // exposed for the save/load bridge below
  // game.py imports these (see the list at the top of this file); same fetch-then-writeFile pattern as Continuum's ENGINE_MODULES.
  await Promise.all(SOL_PY_MODULES.map(async (name) => {
    const moduleSource = await (await fetch(name)).text();
    pyodide.FS.writeFile(name, moduleSource, { encoding: "utf8" });
  }));
  // Shared "export my progress" helper (Z8, see shared/export_progress.py)
  // -- written into Pyodide's virtual filesystem before game.py runs so
  // `import export_progress` resolves normally, same fetch-then-write
  // pattern Aftermath's index.html already uses for shared/info_page.py.
  const exportProgressSource = await (await fetch("../../shared/export_progress.py")).text();
  pyodide.FS.writeFile("export_progress.py", exportProgressSource, { encoding: "utf8" });
  // Round-6: the Scarcity Run's pure helpers (challenges.py) and the shared seeded-run module they
  // draw from (shared/seed.py, the same Rng every daily on the site uses), written next to game.py.
  const [seedSource, challengesSource] = await Promise.all([
    fetch("../../shared/seed.py").then((response) => response.text()),
    fetch("challenges.py").then((response) => response.text()),
  ]);
  pyodide.FS.writeFile("seed.py", seedSource, { encoding: "utf8" });
  pyodide.FS.writeFile("challenges.py", challengesSource, { encoding: "utf8" });
  // Z-3d3: the shared ghost-run trace (shared/ghost.py): the Ghost Run's sentence is built through it.
  const ghostSource = await (await fetch("../../shared/ghost.py")).text();
  pyodide.FS.writeFile("ghost.py", ghostSource, { encoding: "utf8" });
  // ACHIEVEMENTS-SYSTEM-DESIGN.md's loading contract: fetch the static
  // catalog and hand it to Python as a window global *before* game.py
  // runs, same pattern Le Champ de Mots established for its own JSON
  // assets (see that game's index.html + game.py's _read_json_asset()).
  const [achievementsJson, changelogJson, code] = await Promise.all([
    fetch("achievements.json").then((response) => response.text()),
    fetch("changelog.json").then((response) => response.text()),
    fetch("game.py").then((response) => response.text()),
  ]);
  window.ACHIEVEMENTS_JSON = achievementsJson;
  window.CHANGELOG_JSON = changelogJson;
  await pyodide.runPythonAsync(code);

  if (window.GameTutorial) {
    GameTutorial.init(window.SOL_PC_TUTORIAL_STEPS || SOL_TUTORIAL_STEPS, { gameId: "sol" });
  }
  if (window.MobileHud) {
    MobileHud.init([
      { selector: "#resource-count", label: "Iron" },
      { selector: "#ecology-percent", label: "Ecology" },
    ]);
  }
}
main();
