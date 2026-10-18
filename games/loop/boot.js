// Boot: load Pyodide, write the shared info page and every loop_*.py module into Pyodide's file system, then run
// game.py (the entry point), which imports them. Add a new Python module to LOOP_PY_MODULES below (and to sw.js and
// offline-manifest.json) or the page cannot import it.
const LOOP_PY_MODULES = [
  "loop_rules.py",
  "loop_model.py",
  "loop_runstate.py",
  "loop_bridge.py",
  "loop_career.py",
  "loop_ledger.py",
  "loop_messages.py",
  "loop_info_panel.py",
  "loop_achievements.py",
  "loop_effects.py",
  "loop_changelog.py",
  "loop_readouts.py",
  "loop_visual_maps.py",
  "loop_sparklines.py",
  "loop_summaries.py",
  "loop_assist.py",
  "loop_planner.py",
  "loop_ghost_codes.py",
  "loop_narrator.py",
  "loop_savegame.py",
  "loop_renderer.py",
  "loop_handlers.py",
  "loop_loading.py",
];

async function main() {
  const pyodide = await loadPyodide();
  window.pyodide = pyodide; // exposed for the save/load bridge below
  // game.py imports these (see the list at the top of this file); same fetch-then-writeFile pattern as Continuum's ENGINE_MODULES.
  await Promise.all(LOOP_PY_MODULES.map(async (name) => {
    const moduleSource = await (await fetch(name)).text();
    pyodide.FS.writeFile(name, moduleSource, { encoding: "utf8" });
  }));
  // Shared info-page widget (see shared/info_page.py) -- written into
  // Pyodide's virtual filesystem before game.py runs so `import
  // info_page` resolves normally, same pattern as Continuum's
  // ENGINE_MODULES loop.
  const infoPageSource = await (await fetch("../../shared/info_page.py")).text();
  pyodide.FS.writeFile("info_page.py", infoPageSource, { encoding: "utf8" });
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
    GameTutorial.init(loopTutorialSteps(), { gameId: "loop" });
  }
  if (window.MobileHud) {
    MobileHud.init([
      { selector: "#funds-display", label: "" },
      { selector: "#circular-fraction-display", label: "" },
      { selector: "#damage-display", label: "" },
    ]);
  }
}
main();
