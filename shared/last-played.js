/*
 * Shared "last played" stamper — planning/TODO.md's Z14 (the shared helper)
 * + Z2 (surfacing it on hub title cards).
 *
 * One script, included unchanged by every game via:
 *   <script src="../../shared/last-played.js" data-game-id="<slug>"></script>
 * (same data-game-id convention as shared/save-widget.js). On every load of
 * a game's own page, it stamps `localStorage["last-played:<slug>"]` with
 * the current time (epoch ms) -- nothing else. The hub's own index.html/
 * script.js reads those keys back (one per game) to render a "Last played
 * ..." badge per title card, distinct from the git-history-sourced "Updated
 * ..." badge (TODO.md L7) already on every card -- that one says when the
 * GAME last changed; this one says when THIS PLAYER, in THIS BROWSER, last
 * opened it.
 *
 * Deliberately client-side/per-browser only, like every other browser-level
 * preference on this site (text-scale, reduced-motion, personal-best
 * stats) -- never touches get_state()/load_state() or the save-code system,
 * since "when did I last open this" isn't part of portable save data and
 * doesn't need to follow a save code to a different browser/device.
 *
 * Deliberately NOT gated on Pyodide finishing (or even existing) -- this
 * fires immediately on script load, so a game that never gets past the
 * Pyodide boot screen still records a "last played" stamp the moment the
 * page was opened, which is the honest definition of "played" for this
 * purpose (visited), not "finished loading."
 */
(function () {
  const SCRIPT = document.currentScript;
  const GAME_ID = SCRIPT && SCRIPT.dataset.gameId;
  if (!GAME_ID) {
    console.error("last-played.js: missing required data-game-id attribute on its <script> tag");
    return;
  }
  try {
    localStorage.setItem("last-played:" + GAME_ID, String(Date.now()));
  } catch (err) {
    // Private-browsing mode, storage quota, or a locked-down browser --
    // failing silently here is correct: this is a "nice to have" freshness
    // badge, not something any game's own functionality depends on.
    console.error("last-played.js: localStorage.setItem failed", err);
  }

  // QI-58: the hub's "Pick up where you stopped" strip also shows the exact thing the player was doing.
  // A game opts in by either calling window.NoyvjResume.set("Day 14, 3 events in") whenever it likes, or by
  // defining a Python function `resume_note()` that returns a short string; the page asks for it when it
  // is hidden or left (never on a timer). The note is one short plain-text line (80 characters at most),
  // kept per browser in localStorage["resume-note:<slug>"] as {t, text}, and never part of a save.
  const NOTE_KEY = "resume-note:" + GAME_ID;
  const NOTE_MAX = 80;
  function clean(text) {
    return String(text === undefined || text === null ? "" : text).replace(/\s+/g, " ").trim().slice(0, NOTE_MAX);
  }
  function setNote(text) {
    const value = clean(text);
    try {
      if (value) localStorage.setItem(NOTE_KEY, JSON.stringify({ t: Date.now(), text: value }));
      else localStorage.removeItem(NOTE_KEY);
    } catch (err) { /* storage blocked: the strip just shows no note */ }
    return value;
  }
  function pullFromGame() {
    try {
      const py = window.pyodide;
      if (!py || !py.globals || typeof py.globals.get !== "function") return;
      const fn = py.globals.get("resume_note");
      if (typeof fn !== "function") return;
      const result = fn();
      setNote(result);
      if (result && typeof result.destroy === "function") result.destroy();
      if (typeof fn.destroy === "function") fn.destroy();
    } catch (err) { /* a game's note must never break the page */ }
  }
  window.NoyvjResume = { set: setNote, pull: pullFromGame, key: NOTE_KEY };
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "hidden") pullFromGame(); });
  window.addEventListener("pagehide", pullFromGame);
})();
