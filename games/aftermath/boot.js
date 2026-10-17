// Boot: load Pyodide, write the shared Python helpers and every aftermath_*.py module into Pyodide's file system, then
// run game.py (the entry point), which imports them. Add a new Python module to AFTERMATH_PY_MODULES below (and to
// sw.js and offline-manifest.json) or the page cannot import it. Keep the list in dependency order; it must match
// _PART_NAMES in game.py (a test checks both against the .py files on disk).
const AFTERMATH_PY_MODULES = [
  "aftermath_runstate.py",
  "aftermath_rules.py",
  "aftermath_persist.py",
  "aftermath_skilltree.py",
  "aftermath_bonuses.py",
  "aftermath_achievements.py",
  "aftermath_pastruns.py",
  "aftermath_panels.py",
  "aftermath_codex.py",
  "aftermath_runview.py",
  "aftermath_tools.py",
  "aftermath_challenges.py",
  "aftermath_skillmap.py",
  "aftermath_chronicle.py",
  "aftermath_flourish.py",
  "aftermath_model_run.py",
  "aftermath_renderer.py",
  "aftermath_actions.py",
  "aftermath_savestate.py",
  "aftermath_handlers.py",
];

async function main() {
  const pyodide = await loadPyodide();
  window.pyodide = pyodide; // exposed for the save/load bridge below
  // game.py imports these (see the list at the top of this file); same fetch-then-writeFile pattern as Continuum's ENGINE_MODULES.
  await Promise.all(AFTERMATH_PY_MODULES.map(async (name) => {
    const moduleSource = await (await fetch(name)).text();
    pyodide.FS.writeFile(name, moduleSource, { encoding: "utf8" });
  }));
  // Shared info-page widget (see shared/info_page.py) -- written into
  // Pyodide's virtual filesystem before game.py runs so `import
  // info_page` resolves normally, same pattern as Continuum's
  // ENGINE_MODULES loop.
  const infoPageSource = await (await fetch("../../shared/info_page.py")).text();
  pyodide.FS.writeFile("info_page.py", infoPageSource, { encoding: "utf8" });
  // Shared "export my progress" helper (Z8, see shared/export_progress.py)
  // -- same fetch-then-write-into-Pyodide-FS pattern as info_page.py just
  // above, so `import export_progress` resolves normally from game.py.
  const exportProgressSource = await (await fetch("../../shared/export_progress.py")).text();
  pyodide.FS.writeFile("export_progress.py", exportProgressSource, { encoding: "utf8" });
  // E-4: the shared run-code module needs seed.py next to it (alphabet, prefix rule, hash).
  // E-2/E-11/GE-16: skill_tree.py is the shared skill-tree rules module (W-3), used for the skill map's states, tiers and checks.
  // Z-3d: ghost.py is the shared best-run ghost (Recorder, load, compare, summary).
  for (const f of ["seed.py", "run_code.py", "skill_tree.py", "ghost.py"]) {
    const src = await (await fetch("../../shared/" + f)).text();
    pyodide.FS.writeFile(f, src, { encoding: "utf8" });
  }
  // Achievements catalog (ACHIEVEMENTS-SYSTEM-DESIGN.md §2) -- fetched
  // and handed to Python as a window global before game.py runs, same
  // three-line convention every other achievements-rollout game uses.
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
    GameTutorial.init(window.AFTERMATH_PC_TUTORIAL_STEPS || AFTERMATH_TUTORIAL_STEPS, { gameId: "aftermath" });
  }
  if (window.MobileHud) {
    MobileHud.init([
      { selector: "#resources-display", label: "" },
      { selector: "#resilience-display", label: "" },
      { selector: "#growth-display", label: "" },
    ]);
  }
  if (window.MobileDock) {
    // E1 (planning/TODO.md's mobile-dock rollout): docks the whole
    // Resilience/Growth/Face-Next-Event/Start-New-Run cluster as one
    // unit on mobile, same shared/mobile-dock.js mechanism Canopy's
    // #action-panel and Grid's #advance-round-button already use.
    MobileDock.init("#actions-dock");
  }
}
main();
