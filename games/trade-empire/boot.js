// Boot: load Pyodide, write the shared Python helpers and every trade_*.py module into Pyodide's file system, then
// run game.py (the entry point), which imports them. Add a new Python module to TRADE_PY_MODULES below (and to
// sw.js and offline-manifest.json) or the page cannot import it. Keep the list in dependency order; it must match
// _PART_NAMES in game.py (a test checks both against the .py files on disk).
const TRADE_PY_MODULES = [
  "trade_runstate.py",
  "trade_rules.py",
  "trade_records.py",
  "trade_charter.py",
  "trade_uikit.py",
  "trade_colony.py",
  "trade_research.py",
  "trade_mapdraw.py",
  "trade_effects.py",
  "trade_market.py",
  "trade_hub.py",
  "trade_blueprints.py",
  "trade_captains.py",
  "trade_ships.py",
  "trade_crew.py",
  "trade_founding.py",
  "trade_guild.py",
  "trade_weather.py",
  "trade_blackout.py",
  "trade_crises.py",
  "trade_expedition.py",
  "trade_meridian.py",
  "trade_exchange.py",
  "trade_cartel.py",
  "trade_ghost.py",
  "trade_chain_rules.py",
  "trade_chain_logic.py",
  "trade_panels_fleet.py",
  "trade_panels_systems.py",
  "trade_mapview.py",
  "trade_achievements.py",
  "trade_summary.py",
  "trade_charter_ui.py",
  "trade_chain_ui.py",
  "trade_modes.py",
  "trade_savestate.py",
  "trade_loadparts.py",
  "trade_sandbox.py",
  "trade_renderer.py",
  "trade_loading.py",
  "trade_handlers_core.py",
  "trade_handlers_features.py",
  "trade_handlers_modes.py",
  "trade_tick.py",
  "trade_setup.py",
];

async function main() {
  const pyodide = await loadPyodide();
  window.pyodide = pyodide; // exposed for the save/load bridge below
  // game.py imports these (see the list at the top of this file); same fetch-then-writeFile pattern as Continuum's ENGINE_MODULES.
  await Promise.all(TRADE_PY_MODULES.map(async (name) => {
    const moduleSource = await (await fetch(name)).text();
    pyodide.FS.writeFile(name, moduleSource, { encoding: "utf8" });
  }));
  // ACHIEVEMENTS-SYSTEM-DESIGN.md's loading contract: fetch the static
  // catalog and hand it to Python as a window global *before* game.py
  // runs, same pattern SOL (the reference integration) established.
  // Shared seeded-run helper (shared/seed.py, Z-1): game.py's `import seed` resolves from Pyodide's filesystem.
  const seedSource = await (await fetch("../../shared/seed.py")).text();
  pyodide.FS.writeFile("seed.py", seedSource, { encoding: "utf8" });
  // Z-3e5: shared best-charter ghost (shared/ghost.py): one credits number per tick is recorded and compared through it.
  const ghostSource = await (await fetch("../../shared/ghost.py")).text();
  pyodide.FS.writeFile("ghost.py", ghostSource, { encoding: "utf8" });
  const [achievementsJson, changelogJson, code] = await Promise.all([
    fetch("achievements.json").then((response) => response.text()),
    fetch("changelog.json").then((response) => response.text()),
    fetch("game.py").then((response) => response.text()),
  ]);
  window.ACHIEVEMENTS_JSON = achievementsJson;
  window.CHANGELOG_JSON = changelogJson;
  await pyodide.runPythonAsync(code);

  if (window.GameTutorial) {
    GameTutorial.init(window.TRADE_EMPIRE_PC_TUTORIAL_STEPS || TRADE_EMPIRE_TUTORIAL_STEPS, { gameId: "trade-empire" });
  }
  if (window.MobileHud) {
    MobileHud.init([
      { selector: "#profit-display", label: "" },
      { selector: "#automation-slots-display", label: "" },
    ]);
  }
  if (window.MobileDock) {
    MobileDock.init("#mobile-needs-strip");
  }
}
main();
