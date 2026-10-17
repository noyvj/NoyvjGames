// Boot: load Pyodide, write every Python module (the engine modules, their split parts and the continuum_* parts of game.py)
// into Pyodide's file system, then run game.py (the entry point), which imports them. Add a new Python module to
// ENGINE_MODULES below (and to sw.js and offline-manifest.json) or the page cannot import it. continuum_* modules
// must stay in the same order as _PART_NAMES in game.py (a test checks the list against the .py files on disk).
// Continuum is split into engine modules (see game.py's docstring), so
// unlike the smaller hub games it fetches more than one Python file.
// Each engine module is written into Pyodide's virtual filesystem (the
// working directory, which is on sys.path) before game.py runs and
// imports them. Still no build step — just more than one fetch.
const ENGINE_MODULES = [
  // engine modules (each one is a facade over its split parts where it has some)
  "sim.py",
  "sustainability.py",
  "research.py",
  "log.py",
  "transition.py",
  "save.py",
  "info_content.py",
  "visual.py",
  "summary.py",
  "challenges.py",
  "trajectory.py",
  "views.py",
  "archive.py",
  "consulting.py",
  "founding.py",
  "minutes.py",
  "hamlet.py",
  "forecast.py",
  "statlog.py",
  "explain.py",
  "postmortem.py",
  "naming.py",
  "dataexport.py",
  "monuments.py",
  "par.py",
  "techdebt.py",
  "challengerun.py",
  "timelapse.py",
  "advisors.py",
  "eastereggs.py",
  "dynasty.py",
  "banners.py",
  "doctrines.py",
  "rewind.py",
  "citizens.py",
  "neighbours.py",
  "orders.py",
  "heritage.py",
  "beyond.py",
  "geography.py",
  "sandbox.py",
  "peers.py",
  // the split parts of sim.py and research.py
  "continuum_sim_tables.py",
  "continuum_sim_numbers.py",
  "continuum_sim_city.py",
  "continuum_research_tree.py",
  "continuum_research_nodes_early.py",
  "continuum_research_nodes_mid.py",
  "continuum_research_nodes_late.py",
  // game.py's parts, in dependency order
  "continuum_runstate.py",
  "continuum_base.py",
  "continuum_founders.py",
  "continuum_achievements.py",
  "continuum_clock.py",
  "continuum_archive.py",
  "continuum_dynasty.py",
  "continuum_beyond.py",
  "continuum_techdebt.py",
  "continuum_heritage.py",
  "continuum_infopanels.py",
  "continuum_savestate.py",
  "continuum_timelapse.py",
  "continuum_citizens.py",
  "continuum_panels.py",
  "continuum_challenge.py",
  "continuum_geography.py",
  "continuum_progress.py",
  "continuum_extras.py",
  "continuum_peers.py",
  "continuum_views.py",
  "continuum_orders.py",
  "continuum_scenario.py",
  "continuum_hamlet.py",
  "continuum_advance.py",
  "continuum_advisors.py",
  "continuum_renderer.py",
  "continuum_setup.py",
];

async function main() {
  const pyodide = await loadPyodide();
  window.pyodide = pyodide; // exposed for the shared save widget
  await Promise.all(ENGINE_MODULES.map(async (name) => {
    const moduleSource = await (await fetch(name)).text();
    pyodide.FS.writeFile(name, moduleSource, { encoding: "utf8" });
  }));
  // Shared info-page widget (see shared/info_page.py) -- written into
  // Pyodide's virtual filesystem before game.py runs so `import
  // info_page` resolves normally, same pattern used by all 8 climate
  // quartet games (e.g. canopy's boot script).
  const infoPageSource = await (await fetch("../../shared/info_page.py")).text();
  pyodide.FS.writeFile("info_page.py", infoPageSource, { encoding: "utf8" });
  // Shared narrative-log widget (Z11, see shared/narrative_log.py) --
  // same fetch-then-writeFile pattern as info_page.py above, so both
  // `log.py` and `game.py`'s own `import narrative_log` resolve
  // normally. Continuum is this component's reference integration
  // (its own pre-existing "Chronicle" log was generalized into this
  // shared module); Thaw and Le Champ de Mots reuse it too.
  const narrativeLogSource = await (await fetch("../../shared/narrative_log.py")).text();
  pyodide.FS.writeFile("narrative_log.py", narrativeLogSource, { encoding: "utf8" });
  // Shared skill-tree rules (shared/skill_tree.py): the Dynasty perk tree (dynasty.py) is validated and
  // bought through them, the same way Canopy's Seed Vault is.
  const skillTreeSource = await (await fetch("../../shared/skill_tree.py")).text();
  pyodide.FS.writeFile("skill_tree.py", skillTreeSource, { encoding: "utf8" });
  // Shared seeded-run module (shared/seed.py): challengerun.py derives the daily challenge
  // from the UTC date with it, the same function the JavaScript side (seed.js) uses.
  const seedSource = await (await fetch("../../shared/seed.py")).text();
  pyodide.FS.writeFile("seed.py", seedSource, { encoding: "utf8" });
  // Shared comparison-chart component (Z17, see
  // shared/comparison_chart.py) -- same fetch-then-writeFile pattern
  // as info_page.py/narrative_log.py above, so trajectory.py's
  // `import comparison_chart` resolves normally. Continuum's K13
  // "your city vs. history" chart (trajectory.py) is one of the
  // three integrations this shared module was generalized for.
  const comparisonChartSource = await (await fetch("../../shared/comparison_chart.py")).text();
  pyodide.FS.writeFile("comparison_chart.py", comparisonChartSource, { encoding: "utf8" });
  // ACHIEVEMENTS-SYSTEM-DESIGN.md's loading contract: fetch the static
  // catalog and hand it to Python as a window global *before* game.py
  // runs, same pattern SOL/Le Champ de Mots use for their own JSON
  // assets (see those games' game.py `_read_achievements_json()`/
  // `_read_json_asset()`).
  const [achievementsJson, changelogJson, code] = await Promise.all([
    fetch("achievements.json").then((response) => response.text()),
    fetch("changelog.json").then((response) => response.text()),
    fetch("game.py").then((response) => response.text()),
  ]);
  window.ACHIEVEMENTS_JSON = achievementsJson;
  window.CHANGELOG_JSON = changelogJson;
  await pyodide.runPythonAsync(code);

  if (window.GameTutorial) {
    GameTutorial.init(window.CONTINUUM_PC_TUTORIAL_STEPS || CONTINUUM_TUTORIAL_STEPS, { gameId: "continuum" });
  }
  if (window.MobileHud) {
    MobileHud.init([
      { selector: "#population-display", label: "Pop" },
      { selector: "#food-display", label: "Food" },
      { selector: "#score-display", label: "Score" },
    ]);
  }
  if (window.MobileDock) {
    // Site-wide mobile-dock rollout (planning/TODO.md, K9). Continuum's
    // per-row actions (+/- work assignment, per-row Build, per-node
    // Study) are already inline -- no far-apart selection-vs-action
    // split within any of those rows, the same reason Grid's plant
    // rows didn't need this. The real equivalent gap here is bigger
    // than Grid's: every season funnels toward the single Advance
    // Season button, which sits at the very bottom of an even longer
    // page (status, sustainability, work, buildings, research, log,
    // era progress, and Look Back all above it) -- so adjusting work/
    // builds meant scrolling all the way down to advance, then all
    // the way back up to #status to read the season report. Docking
    // Advance Season mirrors Grid's own #advance-round-button judgment
    // call exactly.
    MobileDock.init("#speed-controls");
  }
  // U1: the season clock. Real-time, only while the page is visible; each
  // step is clamped inside game.py's tick_clock() so a throttled or
  // just-woken tab never fast-forwards.
  {
    const tick = pyodide.globals.get("tick_clock");
    let last = performance.now();
    // Z-28: shared/pause-hidden.js holds the clock (sim speed 0) while the tab is hidden. If the
    // player turned that setting off, the clock keeps running in a hidden tab at whatever rate the
    // browser allows (each step is still clamped to one second inside tick_clock).
    const setSpeed = pyodide.globals.get("set_speed");
    // sim_speed lives in continuum_runstate, so a copy read from the globals would go stale: ask the function instead.
    const currentSimSpeed = pyodide.globals.get("current_sim_speed");
    let speedBeforeHold = 0;
    if (window.NoyvjPauseHidden) {
      window.NoyvjPauseHidden.init({
        gameId: "continuum",
        hooks: {
          pause() {
            const running = Number(currentSimSpeed()) || 0;
            if (!running) return false;   // already paused by the player: nothing to stop, no note
            speedBeforeHold = running;
            setSpeed(0);
            return true;
          },
          resume() {
            if (speedBeforeHold && !Number(currentSimSpeed())) setSpeed(speedBeforeHold);
            speedBeforeHold = 0;
          },
        },
      });
    }
    setInterval(() => {
      const now = performance.now();
      const dt = (now - last) / 1000;
      last = now;
      const hold = window.NoyvjPauseHidden && window.NoyvjPauseHidden.get("continuum");
      if (document.visibilityState === "visible" || (hold && !hold.enabled())) tick(dt);
    }, 250);
  }
  // Phase 5: attempt the 3D layer last, after the real 2D game is
  // fully up and playable. ContinuumVisual.init() is fully
  // self-contained about failing gracefully (see render3d.js) --
  // Three.js not loading, or WebGL not being available, must never
  // stop the game from reaching this point already playable.
  if (window.ContinuumVisual) {
    window.ContinuumVisual.init(pyodide);
  }
}
main();
