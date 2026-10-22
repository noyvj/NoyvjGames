/* Robot Script view: glue only. The engine (game.py and its modules) holds every rule; this file draws what handle()
   returns, plays a run back, and forwards what the player does. No game logic lives here.

   The page script is cut into five classic scripts that share ONE object, window.RobotScriptApp (see the File map
   in CLAUDE.md). They load in this order and each is wrapped in its own function, so no new global names exist:
     app-1-core.js     constants, shared state, helpers, send() and askThen()
     app-2-room.js     the stats, the room drawing (applyFrame) and run playback (Run, Step, Skip, Rewind, result card)
     app-3-editor.js   the list editor (palette, program, blocks) and the keyboard
     app-4-panels.js   About and What's New, the room picker and sandbox, medals, goals, achievements, the workshop,
                       hints and render()
     app.js            difficulty, long-press reordering, wire(), the tutorial steps and boot() (loads last)
   State that more than one part reads or writes lives on the object: A.engine, A.view, A.roomId, A.headDeg, A.play,
   A.playbackSpeed, A.refocus, A.sandboxTile, A.PALETTE_SIG. Functions another part calls are exported as A.name at
   the end of their own part. */
(function () {
  "use strict";

  var A = window.RobotScriptApp = {};
  A.engine = null;
  A.view = null;
  A.roomId = null;
  A.headDeg = 0;
  A.play = { frames: null, i: 0, timer: null, trace: null, running: false, bpAt: -1 };
  A.playbackSpeed = 1;
  A.refocus = false;
  A.sandboxTile = "#";
  A.PALETTE_SIG = "";

  var ENGINE_MODULES = ["dsl.py", "room.py", "run.py", "editor.py", "render.py", "progress.py", "info.py", "hints.py", "rooms_moving.py", "rooms_turning.py", "rooms_loops.py", "rooms_routines.py", "rooms_branches.py", "rooms_capstone.py", "rooms.py", "companion.py", "achievements.py", "sandbox.py"];
  var STORE_KEY = "robot-script:state";
  var DIFF_GAME = "robot-script";
  var DIFF_TEXT = {
    easy: "The first hint press opens the nudge and the hint together, and the medal bars are two steps looser (gold at the reference length plus 2).",
    normal: "The game as designed: gold at the reference length, silver a little over, bronze for any clear.",
    hard: "No answer step (nudge and hint only), and silver is tighter. Hard medals are kept on their own record, so your Normal medals never change.",
  };
  var BACKUP_KEY = "robot-script:state-backup";
  var TILE = 48;
  var SPEED_MS = { slow: 600, normal: 280, fast: 90, instant: 0 };
  var GLYPHS = { F: "↑", L: "↶", R: "↷", G: "⤓", P: "⤒", S: "⚡", rep: "↻", until: "↻?", "if": "?", callA: "A", callB: "B" };

  var $ = function (id) { return document.getElementById(id); };

  function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* convenience only */ } }
  function setText(node, text) { if (node.textContent !== text) node.textContent = text; }
  function announce(text) {
    var live = $("announce");
    live.textContent = "";
    setTimeout(function () { live.textContent = text; }, 40);
  }
  function el(tag, cls, text) {
    var node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function showToast(text) {
    var t = $("toast");
    t.textContent = text;
    t.classList.toggle("on", Boolean(text));
  }
  function plural(n, one, many) { return n + " " + (n === 1 ? one : many); }

  // ---- talking to the engine --------------------------------------------------------------------------------
  function persist() {
    try {
      var proxy = A.engine.getState();
      var obj = proxy.toJs({ dict_converter: Object.fromEntries });
      if (proxy.destroy) proxy.destroy();
      lsSet(STORE_KEY, JSON.stringify(obj));
    } catch (e) { /* the save widget keeps the real copy */ }
  }
  function send(request, isEdit) {
    if (!A.engine) return null;
    var result = JSON.parse(A.engine.handle(JSON.stringify(request)));
    if (result.error) { $("engine-status").textContent = "Something went wrong: " + result.error; return null; }
    if (isEdit && result.ok) A.invalidateRun();
    A.view = result;
    showToast("");
    if (request.action === "pick" || request.action === "next" || request.action === "reset") A.invalidateRun();
    A.render();
    var edit = $("edit-line");
    var isFail = result.ok === false && request.action !== "run";
    setText(edit, isFail ? result.message : "");
    if (isFail) announce(result.message);
    else if (isEdit && request.action === "insert") announce("Added. " + plural(A.view.program.size, "step", "steps") + " in the list.");
    persist();
    return result;
  }

  function askThen(id, message, confirmLabel, go) {
    if (window.ConfirmDialog) window.ConfirmDialog.ask({ id: id, message: message, confirmLabel: confirmLabel, allowSkip: false, onConfirm: go });
    else go();
  }

  // what the other parts use
  A.$ = $;
  A.announce = announce;
  A.askThen = askThen;
  A.BACKUP_KEY = BACKUP_KEY;
  A.DIFF_GAME = DIFF_GAME;
  A.DIFF_TEXT = DIFF_TEXT;
  A.el = el;
  A.ENGINE_MODULES = ENGINE_MODULES;
  A.GLYPHS = GLYPHS;
  A.lsGet = lsGet;
  A.lsSet = lsSet;
  A.plural = plural;
  A.send = send;
  A.setText = setText;
  A.showToast = showToast;
  A.SPEED_MS = SPEED_MS;
  A.STORE_KEY = STORE_KEY;
  A.TILE = TILE;
})();
