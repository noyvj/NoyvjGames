// Boot: load Pyodide, write the shared Python helper and every champ_*.py module (the game's and the minigames') plus
// minigames.py and formats.py into Pyodide's file system, then run game.py (the entry point), which imports them.
// Add a new Python module to CHAMP_PY_MODULES below (and to sw.js and offline-manifest.json) or the page cannot import it.
const CHAMP_PY_MODULES = [
  "champ_rules.py",
  "champ_runstate.py",
  "champ_catalog.py",
  "champ_model.py",
  "champ_qbuild.py",
  "champ_questions.py",
  "champ_grading.py",
  "champ_labels.py",
  "champ_util.py",
  "champ_stats.py",
  "champ_calendar.py",
  "champ_points.py",
  "champ_reportlog.py",
  "champ_watering.py",
  "champ_growth.py",
  "champ_practice_base.py",
  "champ_reports.py",
  "champ_leech.py",
  "champ_semesters.py",
  "champ_arrange.py",
  "champ_legend.py",
  "champ_water_pool.py",
  "champ_review_base.py",
  "champ_review.py",
  "champ_proficiency.py",
  "champ_bonus.py",
  "champ_builder.py",
  "champ_listening.py",
  "champ_conversation.py",
  "champ_placement.py",
  "champ_examformats.py",
  "champ_phrasebook.py",
  "champ_dashboard.py",
  "champ_liaison.py",
  "champ_achievements.py",
  "champ_planner.py",
  "champ_accent.py",
  "champ_prefs.py",
  "champ_shop.py",
  "champ_practice.py",
  "champ_wateropts.py",
  "champ_farm.py",
  "champ_renderer.py",
  "champ_setup.py",
  "champ_savegame.py",
  "champ_minigames_rules.py",
  "champ_minigames_runstate.py",
  "champ_minigames_core.py",
  "champ_minigames_blitz.py",
  "champ_minigames_racer.py",
  "champ_minigames_boutique.py",
  "champ_minigames_cafe.py",
  "champ_minigames_sprint.py",
  "champ_minigames_arcade.py",
  "champ_minigames_games.py",
  "champ_minigames_amis.py",
  "champ_minigames_registry.py",
  "minigames.py",
  "formats.py",
];

async function main() {
  const pyodide = await loadPyodide();
  window.pyodide = pyodide; // exposed for the shared save widget
  // The catalog is handed to Python as a window global rather than read
  // from the Pyodide filesystem — no build step, one fetch, and the
  // pytest harness can stand in for it with the same attribute.
  const [
    catalogJson,
    supplementaryNotesJson,
    achievementsJson,
    changelogJson,
    narrativeLogCode,
    code,
  ] = await Promise.all([
    fetch("fren_combined_catalog.json").then((response) => response.text()),
    fetch("fren_supplementary_notes.json").then((response) => response.text()),
    fetch("achievements.json").then((response) => response.text()),
    fetch("changelog.json").then((response) => response.text()),
    // Shared narrative-log widget (Z11, see shared/narrative_log.py):
    // this game's "My Reports" panel is the third integration, after
    // Continuum's own Chronicle and Thaw's scientist's log. Written
    // into the Pyodide filesystem the same way minigames.py is below,
    // so game.py's `import narrative_log` resolves normally.
    fetch("../../shared/narrative_log.py").then((response) => response.text()),
    fetch("game.py").then((response) => response.text()),
  ]);
  window.CATALOG_JSON = catalogJson;
  window.SUPPLEMENTARY_NOTES_JSON = supplementaryNotesJson;
  // ACHIEVEMENTS-SYSTEM-DESIGN.md §2: achievements.json is the single
  // source of truth for this game's achievement catalog, read from
  // Python the same way the catalog/supplementary-notes files already
  // are (_read_json_asset()'s window-global-then-filesystem-fallback).
  window.ACHIEVEMENTS_JSON = achievementsJson;
  // "What's New" changelog panel (origin K16): same loading contract,
  // one more window global handed to game.py's _read_json_asset().
  window.CHANGELOG_JSON = changelogJson;
  // Milestones 27-30: the arcade minigame family is its own importable
  // module (see minigames.py's own docstring), not JSON data -- writing
  // its source onto Pyodide's virtual filesystem before running game.py
  // is what makes game.py's own `import minigames` resolve normally in
  // the browser, the same way it already resolves under pytest via a
  // real file on disk.
  // Every Python module game.py imports (see the list at the top of this file); same fetch-then-writeFile pattern as
  // Continuum's ENGINE_MODULES.
  await Promise.all(CHAMP_PY_MODULES.map(async (name) => {
    const moduleSource = await (await fetch(name)).text();
    pyodide.FS.writeFile(name, moduleSource);
  }));
  pyodide.FS.writeFile("narrative_log.py", narrativeLogCode);
  await pyodide.runPythonAsync(code);

  // Milestones 27-30: each minigame's on-screen countdown is Python
  // state (a plain counter), never a Python clock -- see minigames.py's
  // own docstring. This is the one JS-owned setInterval that actually
  // drives real-world timing for all of them; every tick function is a
  // documented no-op whenever that particular minigame isn't an active
  // running session, so ticking all of them once a second here (rather
  // than starting/stopping a separate interval per game) is harmless.
  // shared/pause-hidden.js sets this while the tab is hidden: the whole
  // one-second tick (and so every countdown) is held, never caught up.
  window.CHAMP_MINIGAMES_HELD = false;
  setInterval(() => {
    if (window.CHAMP_MINIGAMES_HELD) return;
    const blitzTick = pyodide.globals.get("blitz_tick");
    if (blitzTick) blitzTick();
    const sprintTick = pyodide.globals.get("sprint_tick");
    if (sprintTick) sprintTick();
    const racerTick = pyodide.globals.get("racer_tick");
    if (racerTick) racerTick();
    const boutiqueTick = pyodide.globals.get("boutique_tick");
    if (boutiqueTick) boutiqueTick();
    const cafeTick = pyodide.globals.get("cafe_tick");
    if (cafeTick) cafeTick();
    for (const name of ["pairs_tick", "gaps_tick", "listenpick_tick", "wordorder_tick", "amis_tick"]) {
      const tick = pyodide.globals.get(name);
      if (tick) tick();
    }
  }, 1000);

  // Z-28: hold the countdowns while the tab is hidden. pause() reports
  // whether a timed run was actually in progress (then the return note
  // shows); the tick maths itself is untouched.
  if (window.NoyvjPauseHidden) {
    window.NoyvjPauseHidden.init({
      gameId: "champ-de-mots",
      hooks: {
        pause: function () {
          window.CHAMP_MINIGAMES_HELD = true;
          try {
            const running = pyodide.globals.get("minigame_run_active");
            if (!running) return false;
            const yes = !!running();
            if (running.destroy) running.destroy();
            return yes;
          } catch (e) { return false; }
        },
        resume: function () { window.CHAMP_MINIGAMES_HELD = false; },
      },
    });
  }

  // The first-run visual-style picker (visual-style.js) goes first; the
  // tutorial only starts once it has been answered or skipped.
  const startTutorial = function () {
    if (window.GameTutorial) {
      GameTutorial.init(window.CHAMP_DE_MOTS_PC_TUTORIAL_STEPS || CHAMP_DE_MOTS_TUTORIAL_STEPS, { gameId: "champ-de-mots" });
    }
  };
  if (window.ChampDeMotsVisualStyle) {
    window.ChampDeMotsVisualStyle.whenPickerDone(startTutorial);
  } else {
    startTutorial();
  }
  if (window.MobileHud) {
    MobileHud.init([
      { selector: "#day-display", label: "Day" },
      { selector: "#due-display", label: "Ready" },
    ]);
  }
  // shared/mobile-dock.js: the farm grid (#farm, 722 cells) sits far
  // below every panel that reacts to a plot/row click -- practice
  // questions, proficiency tests and bonus sections are all opened
  // from something inside #farm but rendered near the top of the
  // page. Docking all three to a fixed bottom bar on narrow screens
  // keeps water/answer/close reachable without scrolling between the
  // farm and the panel, same pattern Canopy already established for
  // its #action-panel. #review-panel is deliberately left out: its
  // own trigger buttons already live inside #review-section right
  // next to it, so there's no far-apart pair to fix there.
  if (window.MobileDock) {
    MobileDock.init("#practice-panel");
    MobileDock.init("#proficiency-panel");
    MobileDock.init("#bonus-panel");
  }
}
main();
