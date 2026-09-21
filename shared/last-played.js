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
})();
