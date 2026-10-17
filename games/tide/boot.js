// Boot: load Pyodide, write the shared Python helpers and every tide_*.py module into Pyodide's file system, then
// run game.py (the entry point), which imports them. Add a new Python module to TIDE_PY_MODULES below (and to
// sw.js and offline-manifest.json) or the page cannot import it. Keep the list in dependency order; it must match
// _PART_NAMES in game.py (a test checks both against the .py files on disk).
const TIDE_PY_MODULES = [
  "tide_rules.py",
  "tide_runstate.py",
  "tide_coasts.py",
  "tide_bridge.py",
  "tide_model_town.py",
  "tide_model_economy.py",
  "tide_model_season.py",
  "tide_coastline.py",
  "tide_library.py",
  "tide_graphs.py",
  "tide_panels.py",
  "tide_achievements.py",
  "tide_ticker.py",
  "tide_runcode.py",
  "tide_libraryview.py",
  "tide_daily.py",
  "tide_almanac.py",
  "tide_chrome.py",
  "tide_controls.py",
  "tide_readouts.py",
  "tide_seasonflow.py",
  "tide_flavour.py",
  "tide_workshop.py",
  "tide_events.py",
  "tide_savestate.py",
  "tide_renderer.py",
  "tide_loading.py",
  "tide_actions.py",
  "tide_handlers.py",
];

async function main() {
  const pyodide = await loadPyodide();
  window.pyodide = pyodide; // exposed for the save/load bridge below
  // game.py imports these (see the list at the top of this file); same fetch-then-writeFile pattern as Continuum's ENGINE_MODULES.
  await Promise.all(TIDE_PY_MODULES.map(async (name) => {
    const moduleSource = await (await fetch(name)).text();
    pyodide.FS.writeFile(name, moduleSource, { encoding: "utf8" });
  }));
  // Shared info-page widget (see shared/info_page.py) -- written into
  // Pyodide's virtual filesystem before game.py runs so `import
  // info_page` resolves normally, same pattern as Continuum's
  // ENGINE_MODULES loop.
  const infoPageSource = await (await fetch("../../shared/info_page.py")).text();
  pyodide.FS.writeFile("info_page.py", infoPageSource, { encoding: "utf8" });
  // D-3 / GD-5: the shared run-code and seed modules (run_code.py needs seed.py next to it).
  for (const f of ["seed.py", "run_code.py"]) {
    const src = await (await fetch("../../shared/" + f)).text();
    pyodide.FS.writeFile(f, src, { encoding: "utf8" });
  }
  // Achievements (ACHIEVEMENTS-SYSTEM-DESIGN.md): fetched alongside
  // game.py and handed in as a window global before it runs, same
  // contract SOL's reference integration established -- see
  // _read_achievements_json() in game.py.
  const [achievementsJson, changelogJson, code] = await Promise.all([
    fetch("achievements.json").then((response) => response.text()),
    fetch("changelog.json").then((response) => response.text()),
    fetch("game.py").then((response) => response.text()),
  ]);
  window.ACHIEVEMENTS_JSON = achievementsJson;
  window.CHANGELOG_JSON = changelogJson;
  await pyodide.runPythonAsync(code);

  if (window.GameTutorial) {
    GameTutorial.init(window.TIDE_PC_TUTORIAL_STEPS || TIDE_TUTORIAL_STEPS, { gameId: "tide" });
  }
  if (window.MobileHud) {
    MobileHud.init([
      { selector: "#funds-display", label: "" },
      { selector: "#acidity-display", label: "" },
      { selector: "#fish-yield-display", label: "" },
    ]);
  }
  if (window.MobileDock) {
    // D1: dock the investments panel + Advance Season button to the
    // bottom of the viewport on mobile, same shared/mobile-dock.js
    // mechanism as Grid/Canopy/Aftermath/Trade Empire/Champ de Mots.
    MobileDock.init("#actions-dock");
  }
}
main();
