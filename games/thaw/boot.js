// Boot: load Pyodide, write the shared Python helpers and every thaw_*.py module into Pyodide's file system, then
// run game.py (the entry point), which imports them. Add a new Python module to THAW_PY_MODULES below (and to
// sw.js and offline-manifest.json) or the page cannot import it. Keep the list in dependency order; it must match
// _PART_NAMES in game.py (a test checks both against the .py files on disk).
const THAW_PY_MODULES = [
  "thaw_runstate.py",
  "thaw_rules.py",
  "thaw_model.py",
  "thaw_bridge.py",
  "thaw_sciencelog.py",
  "thaw_presets.py",
  "thaw_graphs.py",
  "thaw_mechanics.py",
  "thaw_records.py",
  "thaw_achievements.py",
  "thaw_panels.py",
  "thaw_readouts.py",
  "thaw_runs.py",
  "thaw_views.py",
  "thaw_saveparts.py",
  "thaw_timeline.py",
  "thaw_flavour.py",
  "thaw_pace.py",
  "thaw_settingscode.py",
  "thaw_savestate.py",
  "thaw_renderer.py",
  "thaw_loading.py",
  "thaw_handlers.py",
];

async function main() {
  const pyodide = await loadPyodide();
  window.pyodide = pyodide; // exposed for the save/load bridge below
  // game.py imports these (see the list at the top of this file); same fetch-then-writeFile pattern as Continuum's ENGINE_MODULES.
  await Promise.all(THAW_PY_MODULES.map(async (name) => {
    const moduleSource = await (await fetch(name)).text();
    pyodide.FS.writeFile(name, moduleSource, { encoding: "utf8" });
  }));
  // Shared info-page widget (see shared/info_page.py) -- written into
  // Pyodide's virtual filesystem before game.py runs so `import
  // info_page` resolves normally, same pattern as Continuum's
  // ENGINE_MODULES loop.
  const infoPageSource = await (await fetch("../../shared/info_page.py")).text();
  pyodide.FS.writeFile("info_page.py", infoPageSource, { encoding: "utf8" });
  // Shared narrative-log widget (Z11, see shared/narrative_log.py) --
  // same fetch-then-writeFile pattern as info_page.py above, so
  // game.py's `import narrative_log` resolves. G19's scientist's log
  // reuses this component's append-and-cap bookkeeping (its own
  // rendering stays bespoke -- see the CLAUDE.md build note for why).
  const narrativeLogSource = await (await fetch("../../shared/narrative_log.py")).text();
  pyodide.FS.writeFile("narrative_log.py", narrativeLogSource, { encoding: "utf8" });
  // Z-3e3: the shared best-run ghost (shared/ghost.py): Region A's pace line and its sentence are built through it.
  const ghostSource = await (await fetch("../../shared/ghost.py")).text();
  pyodide.FS.writeFile("ghost.py", ghostSource, { encoding: "utf8" });
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
    GameTutorial.init(window.THAW_PC_TUTORIAL_STEPS || THAW_TUTORIAL_STEPS, { gameId: "thaw" });
  }
  if (window.MobileHud) {
    MobileHud.init([
      { selector: "#funds-display", label: "Funds" },
      { selector: "#temperature-display", label: "Temp" },
    ]);
  }
}
main();
