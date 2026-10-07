/*
 * Pyodide boot timing for every game (TODO Z-21). Include it early in <head>, before the game's
 * own scripts; it needs no per-game code. It records five milestones with performance.mark()
 * and logs each one on the console in a single format:
 *
 *   [noyvj-perf] <game> <milestone> <ms>ms          (ms since the page started loading)
 *
 *   script-start       this file ran (the first moment the page's own code is running)
 *   dom-ready          the HTML finished parsing
 *   pyodide-loaded     window.pyodide exists (the game's boot script finished loadPyodide())
 *   game-setup-done    the game's Python ran far enough to define get_state() (all games do)
 *   first-interactive  the first frame after that has been painted, so a click can be handled
 *
 * and, when the last one lands, one summary line plus a performance.measure("noyvj:boot"). The
 * marks are visible in the browser's Performance panel (User Timing track) and from the console:
 * NoyvjPerf.marks() returns {name: ms}, NoyvjPerf.summary() the same with the gaps between them.
 * Logging uses console.info, so it is hidden unless the console shows the Info level. Nothing is
 * stored or sent anywhere. shared/debug-overlay.js (?debug=1) shows the same numbers on screen.
 */
(function () {
  "use strict";
  if (window.NoyvjPerf) return;

  const SCRIPT = document.currentScript;
  const GAME = (SCRIPT && SCRIPT.dataset.gameId) || (location.pathname.match(/\/games\/([^/]+)\//) || [, "hub"])[1];
  const ORDER = ["script-start", "dom-ready", "pyodide-loaded", "game-setup-done", "first-interactive"];
  const marks = {};
  const POLL_MS = 50;
  const GIVE_UP_MS = 120000;

  function now() { return Math.round(performance.now()); }

  function mark(name) {
    if (Object.prototype.hasOwnProperty.call(marks, name)) return marks[name];
    const at = now();
    marks[name] = at;
    try { performance.mark(`noyvj:${name}`); } catch (e) { /* User Timing unavailable */ }
    try { console.info(`[noyvj-perf] ${GAME} ${name} ${at}ms`); } catch (e) { /* no console */ }
    if (name === "first-interactive") finish();
    return at;
  }

  function finish() {
    try { performance.measure("noyvj:boot", "noyvj:script-start", "noyvj:first-interactive"); } catch (e) { /* ignore */ }
    const s = summary();
    try {
      console.info(`[noyvj-perf] ${GAME} boot ${s.total}ms (pyodide ${s.gaps["pyodide-loaded"]}ms, game setup ${s.gaps["game-setup-done"]}ms, first paint ${s.gaps["first-interactive"]}ms)`);
    } catch (e) { /* no console */ }
  }

  function summary() {
    const gaps = {};
    let prev = null;
    ORDER.forEach((name) => {
      if (marks[name] === undefined) return;
      gaps[name] = prev === null ? 0 : marks[name] - prev;
      prev = marks[name];
    });
    const end = marks["first-interactive"];
    return { game: GAME, marks: Object.assign({}, marks), gaps, total: end === undefined ? null : end - marks["script-start"] };
  }

  function gameDefinesState(py) {
    try {
      const fn = py.globals.get("get_state");
      if (!fn) return false;
      if (typeof fn.destroy === "function") fn.destroy();
      return true;
    } catch (e) { return false; }
  }

  mark("script-start");

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", () => mark("dom-ready"), { once: true });
  else mark("dom-ready");

  const started = performance.now();
  const timer = setInterval(() => {
    if (performance.now() - started > GIVE_UP_MS || marks["first-interactive"] !== undefined) { clearInterval(timer); return; }
    const py = window.pyodide;
    if (!py) return;
    mark("pyodide-loaded");
    if (marks["game-setup-done"] === undefined && gameDefinesState(py)) {
      mark("game-setup-done");
      // The frame after setup; a tab opened in the background never gets one, so also give up
      // waiting for it after 1.5 s (the page is interactive either way).
      const done = () => { mark("first-interactive"); clearInterval(timer); };
      requestAnimationFrame(() => requestAnimationFrame(done));
      setTimeout(done, 1500);
    }
  }, POLL_MS);

  window.NoyvjPerf = { mark, marks: () => Object.assign({}, marks), summary, game: GAME };
})();
