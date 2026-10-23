/* Robot Script, part 5 of 5 (loads last): difficulty, long-press reordering, wire(), the tutorial steps and boot(). */
(function () {
  "use strict";

  var A = window.RobotScriptApp;
  var $ = A.$, askThen = A.askThen, BACKUP_KEY = A.BACKUP_KEY, DIFF_GAME = A.DIFF_GAME, DIFF_TEXT = A.DIFF_TEXT,
      ENGINE_MODULES = A.ENGINE_MODULES, invalidateRun = A.invalidateRun, loadChangelog = A.loadChangelog,
      lsGet = A.lsGet, lsSet = A.lsSet, onKey = A.onKey, onRewind = A.onRewind, onRoomClick = A.onRoomClick,
      onRun = A.onRun, onSkip = A.onSkip, onStep = A.onStep, send = A.send, showToast = A.showToast,
      speedMs = A.speedMs, stepFrame = A.stepFrame, STORE_KEY = A.STORE_KEY,
      updatePlaybackSpeed = A.updatePlaybackSpeed, wirePanelToggle = A.wirePanelToggle;

  // ---- difficulty (AN-17, shared/difficulty.js): the page keeps the choice, the engine applies it and is never told to save it ----
  function sendDifficulty() {
    if (!A.engine) return null;
    if (!window.NoyvjDifficulty) return send({ action: "open" });
    return send({ action: "difficulty", level: window.NoyvjDifficulty.get(DIFF_GAME) });
  }
  function wireDifficulty() {
    if (!window.NoyvjDifficulty) return;
    window.NoyvjDifficulty.mount("#difficulty-slot", { game: DIFF_GAME, collapsible: true, descriptions: DIFF_TEXT });
    window.NoyvjDifficulty.onChange(function (d) { if (d.game === DIFF_GAME) { invalidateRun(); sendDifficulty(); } });
  }

  // R4-RSMO-1: press and hold a step's letter, then drag it up or down and let go to move it that many places. The page uses
  // no timers for this: the hold is judged at release from the events' own time stamps. Each place is an ordinary `move`
  // edit (so Undo takes it back), and the arrow buttons on the step remain the keyboard way.
  var REORDER_HOLD_MS = 500, REORDER_ROW_PX = 44;
  function _initReorderHandles() {
    var holder = $("program");
    var d = null;
    holder.addEventListener("pointerdown", function (e) {
      if (e.pointerType === "mouse" && e.button) return;
      var grip = e.target.closest ? e.target.closest(".node-glyph") : null;
      var node = grip && grip.closest(".node");
      if (!node || !node.dataset.a) { d = null; return; }
      d = { at: node.dataset.a, t0: e.timeStamp, y0: e.clientY, id: e.pointerId };
      try { grip.setPointerCapture(e.pointerId); } catch (err) { /* only keeps the drag alive outside the row */ }
    });
    holder.addEventListener("pointerup", function (e) {
      if (!d || e.pointerId !== d.id) return;
      var drag = d;
      d = null;
      if (e.timeStamp - drag.t0 < REORDER_HOLD_MS) return;
      var places = Math.round((e.clientY - drag.y0) / REORDER_ROW_PX);
      if (!places) return;
      var dir = places > 0 ? 1 : -1;
      var parts = drag.at.split("/");
      var index = parseInt(parts.pop(), 10);
      for (var n = Math.abs(places); n > 0; n--) {
        var r = send({ action: "move", at: parts.concat([String(index)]).join("/"), delta: dir }, true);
        if (!r || r.ok === false) break;          // the end of the list: the engine said no, nothing more to do
        index += dir;
      }
    });
    holder.addEventListener("pointercancel", function () { d = null; });
  }

  function wire() {
    wireDifficulty();
    _initReorderHandles();
    $("toast").addEventListener("click", function () { showToast(""); });

    // Speed chip (mobile)
    var speedChip = $("speed-chip");
    if (speedChip) {
      Array.prototype.forEach.call(speedChip.querySelectorAll("button"), function(btn) {
        btn.addEventListener("click", function() {
          A.playbackSpeed = Number(btn.dataset.speed);
          Array.prototype.forEach.call(speedChip.querySelectorAll("button"), function(b) { b.setAttribute("aria-pressed", String(b === btn)); });
          if (A.play.running && A.play.trace) updatePlaybackSpeed(speedMs());
        });
      });
    }

    // Playback slider and keyboard controls
    document.addEventListener("robotScriptPlaybackSpeedChange", function (e) {
      updatePlaybackSpeed(e.detail);
    });
    document.addEventListener("robotScriptFrameStep", function (e) {
      stepFrame(e.detail);
    });
    wirePanelToggle("rooms-toggle-button", "rooms-panel");
    wirePanelToggle("workshop-toggle-button", "workshop-panel");
    wirePanelToggle("achievements-toggle-button", "achievements-panel");
    wirePanelToggle("medals-toggle-button", "medals-panel");
    $("hint-button").addEventListener("click", function () { send({ action: "hint" }); });
    // R4-RSMO-10 (hint-sheet.js): the phone's hint sheet asks for hints and the answer through these events
    document.addEventListener("robotScriptHintRequest", function () { send({ action: "hint" }); });
    document.addEventListener("robotScriptHintAnswer", function () { send({ action: "load_answer" }, true); });
    $("answer-load-button").addEventListener("click", function () { send({ action: "load_answer" }, true); });
    wirePanelToggle("changelog-toggle-button", "changelog-panel");
    wirePanelToggle("info-page-toggle-button", "info-page-panel");
    $("room-holder").addEventListener("click", onRoomClick);
    $("sbx-paint-button").addEventListener("click", function () {
      send({ action: "sbx_paint", x: Number($("sbx-col").value) - 1, y: Number($("sbx-row").value) - 1, tile: A.sandboxTile }, true);
    });
    $("sbx-preset-button").addEventListener("click", function () {
      askThen("robot-script-preset", "Replace the sandbox room with this preset? The room you painted will be erased.", "Replace it", function () {
        send({ action: "sbx_preset", name: $("sbx-preset").value }, true);
      });
    });
    $("run-button").addEventListener("click", onRun);
    $("step-button").addEventListener("click", onStep);
    $("skip-button").addEventListener("click", onSkip);
    $("rewind-button").addEventListener("click", onRewind);
    $("next-button").addEventListener("click", function () { send({ action: "next" }); });
    $("undo-button").addEventListener("click", function () { send({ action: "undo" }, true); });
    $("clear-button").addEventListener("click", function () { send({ action: "clear" }, true); });
    $("best-button").addEventListener("click", function () { send({ action: "load_best" }, true); });
    $("reset-button").addEventListener("click", function () {
      askThen("robot-script-reset", "Start the whole deck over? Your medals, lists and tally will be erased.", "Erase it", function () { send({ action: "reset" }); });
    });
    document.addEventListener("keydown", onKey);
    document.addEventListener("robotScriptSwipeDelete", function (e) {
      send({ action: "remove", at: e.detail }, true);
    });
    document.addEventListener("robotScriptSwipeUndo", function () { send({ action: "undo" }, true); });
    // The save widget loads a save straight into the engine; this redraws afterwards.
    window.robotScriptRefresh = function () { if (A.engine) { A.roomId = null; send({ action: "open" }); } };
  }

  var TUTORIAL_STEPS = [
    { title: "Welcome to the deck", text: "A maintenance robot does exactly what your list says. Write the list, press Run, and watch. Nothing is timed, and a run that goes wrong costs nothing. Skip any time and reopen this from the Tutorial button." },
    { selector: "#room-panel", title: "The room", text: "The robot starts on its tile facing the way its nose points. The checklist above the room says what the room needs: here, reach the glowing exit pad. Parts are diamonds, sockets are dashed frames, switches are numbered plates and doors are barred and lettered." },
    { selector: "#palette", title: "Instructions", text: "Tap an instruction to add it to your list. The robot only has what this room allows; later chapters add more. Forward moves one tile, and every instruction you add is one step." },
    { selector: "#program", title: "Your list", text: "The marked gap shows where the next step goes. Tap another gap to add somewhere else, the arrows move a step, and the x removes it. Undo takes back your last change." },
    { selector: "#run-button", title: "Run, Step and Skip", text: "Run plays your list. Step does one action at a time and Skip jumps to the end. If the robot cannot do a step (a wall, a shut door, nothing to pick up), it stops there and says why. Your list stays, so just fix it and run again." },
    { selector: "#size-line", title: "Steps and medals", text: "Fewer steps earn better medals: gold at the reference length, silver a little over, bronze for any clear. Hints are free and never touch a medal." },
    { selector: "#goals", title: "Your goals", text: "Three goals stay in view, and you can do them in any order. Every run, every step you write and every hint you ask for counts toward something on the screen." },
    { selector: "#rooms-toggle-button", title: "Rooms and Scrap", text: "Rooms lists every chapter, and every room is open from the start. Each room you clear gives Scrap, the salvage drone in the Workshop, a part, and a better list gives the same part a better finish. Once you have cleared every room of Loops, the third chapter, a free sandbox opens." },
    { title: "You are ready", text: "Take your time. Your lists and medals are saved as you go." }
  ];

  async function boot() {
    var changelog = loadChangelog();
    var pyodide = await window.loadPyodide();
    for (var i = 0; i < ENGINE_MODULES.length; i++) {
      var source = await (await fetch(ENGINE_MODULES[i], { cache: "no-cache" })).text();
      pyodide.FS.writeFile(ENGINE_MODULES[i], source, { encoding: "utf8" });
    }
    await pyodide.runPythonAsync(await (await fetch("game.py", { cache: "no-cache" })).text());
    window.pyodide = pyodide;   // the shared save widget looks for it
    A.engine = { handle: pyodide.globals.get("handle"), getState: pyodide.globals.get("get_state"), loadState: pyodide.globals.get("load_state") };
    var saved = lsGet(STORE_KEY);
    if (saved && saved !== "{}") {
      lsSet(BACKUP_KEY, saved);      // kept until the next good save, so a load problem can never cost the player a game
      try { A.engine.loadState(pyodide.toPy(JSON.parse(saved))); } catch (e) { /* a bad save never blocks play */ }
    }
    $("engine-status").textContent = "";
    sendDifficulty();
    await changelog;
    if (window.GameTutorial) window.GameTutorial.init(window.robotScriptTutorialSteps ? window.robotScriptTutorialSteps(TUTORIAL_STEPS) : TUTORIAL_STEPS, { gameId: "robot-script" });
  }

  wire();
  boot().catch(function (err) {
    $("engine-status").textContent = "The deck could not start (" + err + "). Reload to try again.";
  });
})();
