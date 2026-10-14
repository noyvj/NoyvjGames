/* Robot Script, Desktop boot only (loaded by pc.html). The guided tutorial for the Desktop layout: the Classic
   walkthrough names toolbar buttons, which the Desktop layout turns into icons, the Menu and windows, and the list
   editor sits in a side column. index.html uses these steps when they exist (window.ROBOT_SCRIPT_PC_TUTORIAL_STEPS)
   and its own otherwise. */
window.ROBOT_SCRIPT_PC_TUTORIAL_STEPS = [
  {
    title: "Welcome to the deck",
    text: "A maintenance robot does exactly what your list says. Write the list, press Run, and watch. Nothing is timed, and a run that goes wrong costs nothing. This walkthrough covers the Desktop layout. Skip it any time, and reopen it from the Menu.",
  },
  {
    selector: "#room-panel",
    title: "The room",
    text: "The robot starts on its tile facing the way its nose points. The checklist above the room says what the room needs. Parts are diamonds, sockets are dashed frames, switches are numbered plates and doors are barred and lettered.",
  },
  {
    selector: "#pc-side",
    title: "Your list",
    text: "The side column holds your list. Tap an instruction to add it where the marked gap is, tap another gap to add somewhere else, and use the arrows and the x to rearrange or remove steps. Every instruction is one step.",
  },
  {
    selector: "#run-button",
    title: "Run, Step and Skip",
    text: "Run plays your list. Step does one action at a time and Skip jumps to the end. If the robot cannot do a step it stops there and says why. Your list stays, so fix it and run again.",
  },
  {
    selector: "#size-line",
    title: "Steps and medals",
    text: "Fewer steps earn better medals: gold at the reference length, silver a little over, bronze for any clear. Hints are free and never touch a medal.",
  },
  {
    selector: "#goals",
    title: "Your goals",
    text: "Three goals stay in view, in any order. Every run, every step you write and every hint you ask for counts toward something on the screen.",
  },
  {
    selector: "#pc-menu-button",
    title: "Icons and the Menu",
    text: "The icons open the Rooms, Scrap's Workshop, Achievements and Settings. The Menu, or Escape when nothing else is open, holds the rest: this tutorial, About and What's New. Each opens as a window over the game, and Escape closes the top one.",
  },
  {
    title: "You are ready",
    text: "Take your time. Your lists and medals are saved as you go.",
  },
];

// R4-RSPC-3: a gutter beside every step of the list. Click it to set a breakpoint: a run that is playing pauses just
// before that step (app.js reads window.ROBOT_SCRIPT_breakpoints, a Set of step addresses such as "main/2"), and Resume or
// Step carries on. Breakpoints live for this visit only; one that no longer points at a step is dropped.
(function () {
  "use strict";
  var set = new Set();
  window.ROBOT_SCRIPT_breakpoints = set;

  function paint() {
    var present = {};
    var nodes = document.querySelectorAll("#program .node[data-a]");
    for (var i = 0; i < nodes.length; i++) {
      var a = nodes[i].getAttribute("data-a");
      present[a] = true;
      var gutter = nodes[i].querySelector(".bp-gutter");
      if (!gutter) {
        gutter = makeGutter(a);
        nodes[i].insertBefore(gutter, nodes[i].firstChild);
      }
      var on = set.has(a);
      gutter.setAttribute("aria-pressed", String(on));
      gutter.textContent = on ? "●" : "○";
      gutter.classList.toggle("bp-on", on);
    }
    set.forEach(function (a) { if (!present[a]) set.delete(a); });
  }

  function makeGutter(address) {
    var b = document.createElement("button");
    b.type = "button";
    b.className = "bp-gutter";
    b.setAttribute("data-touch-exempt", "");
    b.setAttribute("aria-label", "Breakpoint before this step");
    b.title = "Breakpoint: a run pauses before this step";
    b.addEventListener("click", function () {
      if (set.has(address)) set.delete(address); else set.add(address);
      paint();
    });
    return b;
  }

  document.addEventListener("DOMContentLoaded", function () {
    var program = document.getElementById("program");
    if (!program) return;
    // the game rebuilds the whole list after every edit, so the gutters are added again after each rebuild
    new MutationObserver(paint).observe(program, { childList: true });
    paint();
  });
})();

// R4-RSPC-7: a playback slider (slow to fast) with [ and ] for speed and the arrow keys for frame stepping. app.js owns
// the playback; this only tells it the delay (robotScriptPlaybackSpeedChange) or a frame step (robotScriptFrameStep).
(function () {
  "use strict";
  var KEY = "robot-script-playback-speed";
  var MIN_MS = 50;
  var MAX_MS = 600;
  function load() {
    try {
      var v = parseInt(localStorage.getItem(KEY), 10);
      return v >= 0 && v <= 100 ? v : null;
    } catch (e) { return null; }
  }
  function save(v) { try { localStorage.setItem(KEY, String(v)); } catch (e) { /* a convenience only */ } }
  function delayFor(v) { return Math.round(MAX_MS - (v / 100) * (MAX_MS - MIN_MS)); }

  document.addEventListener("DOMContentLoaded", function () {
    var playback = document.getElementById("playback");
    if (!playback) return;
    var label = document.createElement("label");
    label.className = "pc-speed";
    label.appendChild(document.createTextNode("Speed "));
    var slider = document.createElement("input");
    slider.type = "range";
    slider.min = "0";
    slider.max = "100";
    slider.step = "5";
    slider.id = "playback-slider";
    var stored = load();
    slider.value = String(stored === null ? 50 : stored);
    label.appendChild(slider);
    playback.appendChild(label);

    function apply(v, tell) {
      v = Math.max(0, Math.min(100, v));
      slider.value = String(v);
      save(v);
      var delay = delayFor(v);
      window.robotScriptPlaybackDelay = delay;
      if (tell) document.dispatchEvent(new CustomEvent("robotScriptPlaybackSpeedChange", { detail: delay }));
    }
    slider.addEventListener("input", function () { apply(parseInt(slider.value, 10), true); });
    if (stored !== null) apply(stored, false);   // until the player moves it, the Settings run speed stands

    document.addEventListener("keydown", function (e) {
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      var tag = e.target && e.target.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
      if (document.querySelector("dialog[open], .confirm-dialog, [role='dialog']")) return;
      if (e.key === "[") { apply(parseInt(slider.value, 10) - 10, true); e.preventDefault(); }
      else if (e.key === "]") { apply(parseInt(slider.value, 10) + 10, true); e.preventDefault(); }
      else if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
        document.dispatchEvent(new CustomEvent("robotScriptFrameStep", { detail: e.key === "ArrowLeft" ? -1 : 1 }));
        e.preventDefault();
      }
    });
  });
})();
