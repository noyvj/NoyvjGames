/*
 * Signal -- browser glue. Contains NO game rules.
 *
 * Every rule (generator, solver, scoring, streaks, achievements, share text,
 * save merge) lives in game.py and its signal_*.py parts and runs in Pyodide. This file only:
 *   - paints the static shell instantly, from the last engine view cached in
 *     localStorage ("signal:lastview") and the last saved state
 *     ("signal:state"), so a returning player sees their board, readings and
 *     archive calendar before the engine exists;
 *   - loads Pyodide + game.py LAZILY after first paint (or on the first tap
 *     or key press, whichever comes first) and queues taps made meanwhile;
 *   - forwards taps to the engine as JSON and draws whatever view it returns.
 * The only arithmetic here is presentation: the label of a tile, the height
 * of a bar, and the calendar layout.
 */
/* The page script is cut into four classic scripts that share ONE object, window.SignalPage (see the File map in
   CLAUDE.md). They load in this order and each is its own function, so no new global names exist:
     app-1-core.js      constants, the engine module list, helpers, catalogs, default and cached view (creates window.SignalPage)
     app-2-render.js    resume state, tabs, board, status, waterfall, result, render(), calendar, changelog, achievements, stats
     app-3-engine.js    persisting state, sending to the engine, applying a response, act(), starting Pyodide and the engine
     app.js             user actions, wire(), the hold-to-aim magnifier, init() and window.SignalApp (loads last)
   State that more than one part uses lives on the object: A.view, A.engineReady, A.cachedValid, A.queue, A.pendingCells,
   A.tool, A.cursor, A.currentState, A.cal, A.pendingSettings, A.lastShareText. A function or constant another part uses is
   exported as A.name at the end of its own part. */
(function () {
  "use strict";

  var A = window.SignalPage = {};
  A.engineReady = false;
  A.view = null;
  A.cachedValid = false;
  A.queue = [];
  A.pendingCells = {};
  A.tool = "ping";
  A.cursor = { r: 0, c: 0 };
  A.currentState = null;
  A.cal = { y: 0, m: 0 };
  A.pendingSettings = {};
  A.lastShareText = "";

  var GAME = "signal";
  // Mirrors game.py's EPOCH (tests/test_shell.py asserts they agree).
  var EPOCH = "2026-09-27";
  var PYODIDE_URL = "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js";
  var LS_STATE = "signal:state";
  var LS_VIEW = "signal:lastview";
  var LS_TOOL = "signal:tool";
  var LS_CURSOR = "signal:cursor";
  var MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
  var GLYPHS = "▁▂▃▄▅▆▇█";
  var SYMBOL = { none: "·", inprogress: "…", won: "✔", lost: "✖" };
  var SLOW_MODES = { wide: true, bigsky: true };
  // The engine files game.py imports, in dependency order (they must match _PART_NAMES in game.py; a test checks it).
  // startEngine() writes each one into Pyodide's file system before it runs game.py.
  var SIGNAL_PY_MODULES = ["signal_runstate.py", "signal_rules.py", "signal_puzzle.py", "signal_share.py", "signal_records.py", "signal_session.py", "signal_actions.py", "signal_savestate.py"];

  var $ = function (id) { return document.getElementById(id); };
  var catalog = { ach: [], log: [] };
  var toastQueue = [];
  var timings = { paint: null, pyodide: null, game: null, ready: null, firstPing: null, firstPingQueued: false };

  function lsGet(key) { try { return window.localStorage.getItem(key); } catch (e) { return null; } }
  function lsSet(key, value) { try { window.localStorage.setItem(key, value); } catch (e) { /* convenience only */ } }
  function lsRemove(key) { try { window.localStorage.removeItem(key); } catch (e) { /* convenience only */ } }
  function jsonParse(text) { try { return JSON.parse(text); } catch (e) { return null; } }
  function utcToday() { return new Date().toISOString().slice(0, 10); }
  function label(r, c) { return String.fromCharCode(65 + c) + (r + 1); }
  // Lets the browser paint a "working" message before a long synchronous engine
  // call. Races a frame against a short timer so a background tab (where
  // requestAnimationFrame never fires) cannot stall the game.
  function nextFrame() {
    return new Promise(function (resolve) {
      var done = false;
      function finish() { if (!done) { done = true; resolve(); } }
      requestAnimationFrame(function () { setTimeout(finish, 0); });
      setTimeout(finish, 60);
    });
  }
  function el(tag, cls, text) {
    var node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  // ---- static catalogs (fetched at once: the shared whats-new banner and the
  // engine both read these window globals) ---------------------------------
  var catalogPromise = Promise.all([
    fetch("achievements.json").then(function (r) { return r.text(); }),
    fetch("changelog.json").then(function (r) { return r.text(); }),
  ]).then(function (texts) {
    window.ACHIEVEMENTS_JSON = texts[0];
    window.CHANGELOG_JSON = texts[1];
    var a = jsonParse(texts[0]);
    var l = jsonParse(texts[1]);
    catalog.ach = a && a.achievements ? a.achievements : [];
    var list = Array.isArray(l) ? l : (l && l.changelog) || [];
    catalog.log = list.slice().sort(function (x, y) { return x.date < y.date ? 1 : -1; });
    A.renderChangelog();
    A.renderAchievements();
  }).catch(function (err) { console.error("signal: catalog fetch failed", err); });

  // ---- default / cached view -----------------------------------------------
  function defaultView() {
    return {
      session: { type: "daily", date: utcToday(), mode: "easy", label: "Signal · Easy · Daily", number: null, code: null },
      board: { n: 9, k: 2, radius: 4, budget: 8, par: null, top: 5, assist: true, spacing: 3, mode_label: "Easy" },
      pings: [], marks: [], status: "inprogress", pings_left: 8, can_commit: false, possible: null,
      truth: null, guess: null, result: null, stats: null, ach: null, settings: { mode: "easy", assist_shading: true, ascii_share: false, show_streaks: false, last_preset: "easy" },
      today: utcToday(), epoch: EPOCH, next_utc: null, first_run: true, ascii: false,
    };
  }

  function loadCachedView() {
    var cached = jsonParse(lsGet(LS_VIEW) || "null");
    if (!cached || !cached.board || !cached.session || !Array.isArray(cached.pings)) return null;
    // Fill anything an older cached view lacks so the static paint never throws.
    var base = defaultView();
    cached.settings = cached.settings || base.settings;
    cached.marks = Array.isArray(cached.marks) ? cached.marks : [];
    if (typeof cached.pings_left !== "number") cached.pings_left = cached.board.budget - cached.pings.length;
    if (!cached.status) cached.status = "inprogress";
    return cached;
  }

  // A cached view is only safe to queue taps against if the engine will boot
  // into the very same puzzle: a daily must still be today's; archive and
  // practice sessions are resumed as they were.
  function isCachedValid(v) {
    if (!v) return true; // brand-new visitor: boot opens today's Easy, same as the stub
    if (v.session.type === "daily") return v.session.date === utcToday();
    return true;
  }

  // what the other parts use (see the File map in CLAUDE.md)
  A.$ = $; A.EPOCH = EPOCH; A.GAME = GAME; A.LS_CURSOR = LS_CURSOR; A.LS_STATE = LS_STATE; A.LS_TOOL = LS_TOOL;
  A.LS_VIEW = LS_VIEW; A.MONTHS = MONTHS; A.PYODIDE_URL = PYODIDE_URL; A.SIGNAL_PY_MODULES = SIGNAL_PY_MODULES;
  A.SLOW_MODES = SLOW_MODES; A.SYMBOL = SYMBOL; A.catalog = catalog; A.catalogPromise = catalogPromise;
  A.defaultView = defaultView; A.el = el; A.isCachedValid = isCachedValid; A.jsonParse = jsonParse;
  A.label = label; A.loadCachedView = loadCachedView; A.lsGet = lsGet; A.lsRemove = lsRemove; A.lsSet = lsSet;
  A.nextFrame = nextFrame; A.timings = timings; A.toastQueue = toastQueue; A.utcToday = utcToday;
})();
