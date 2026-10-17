/* Lexis view: glue only. The engine (game.py and its modules) holds every rule; this file draws what
   handle() returns and forwards what the player does. No game logic lives here. */
/* The page script is cut into five classic scripts that share ONE object, window.LexisApp (see the File map in
   CLAUDE.md). They load in this order and each is its own function, so no new global names exist:
     app-1-core.js      constants, helpers, the mobile transmit pad, the resume frame, drawing helpers (creates window.LexisApp)
     app-2-station.js   the station, scenes, notebook, transmit panel, planet tabs and planet 2 (compound language)
     app-3-bridge.js    planet 3 (bridge language), achievements, story, contact report, About page, what's new
     app-4-boards.js    number bench, star map, museum, globe, evidence board, sign keyboard, transmission cards, render()
     app.js             talking to the engine, wiring, keys, tutorial steps, boot (loads last)
   State that more than one part uses lives on the object: A.engine, A.view, A.currentPlanet, A.outgoing,
   A.outgoingGlyph, A.outgoingMessage, A.shownScenes, A.benchTarget, A.currentBenchA, A.currentBenchB. A function or
   constant another part uses is exported as A.name at the end of its own part. */
(function () {
  "use strict";

  var A = window.LexisApp = {};
  A.engine = null;   // { handle, getState, loadState, toJs }
  A.view = null;
  A.currentPlanet = "pulse";
  A.outgoing = "";
  A.outgoingGlyph = "";
  A.outgoingMessage = [];   // planet 3: the tokens of the message being built
  A.shownScenes = { pulse: null, compound: null, bridge: null };
  A.currentBenchA = 0;
  A.currentBenchB = 0;
  A.benchTarget = null;

  var ENGINE_MODULES = ["lang.py", "pulse.py", "parse.py", "world.py", "scenes.py", "deduce.py", "notebook.py", "compound.py", "compound_scenes.py", "deduce_compound.py", "glyphs.py", "achievements.py", "bridge.py", "bridge_scenes.py", "deduce_bridge.py", "story.py", "report.py", "info.py", "museum.py", "bench.py", "globes.py", "star_map.py"];
  var STORE_KEY = "lexis:state";
  var BRIEF_KEY = "lexis:brief-seen";
  var RESUME_KEY = "lexis:resume-frame";
  var NIGHT_KEY = "lexis-night-mode";
  var TOKEN_LEN = 4;
  var MAX_OUT = 40;

  var $ = function (id) { return document.getElementById(id); };
  var MAX_MESSAGE = 6;

  function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* convenience only */ } }
  function applyNight(on) {
    document.documentElement.setAttribute("data-night", on ? "true" : "false");
    lsSet(NIGHT_KEY, on);
  }

  // ---- accessibility helpers -------------------------------------------------------------------
  // Live regions only announce when their text really changes, so assign through setText.
  function setText(node, text) { if (node.textContent !== text) node.textContent = text; }
  // A control that cannot be used right now stays focusable (aria-disabled) so focus is never thrown to the
  // page top when the button the player just pressed turns itself off; its click handler checks the flag.
  function setEnabled(id, enabled) {
    var btn = $(id);
    if (enabled) btn.removeAttribute("aria-disabled"); else btn.setAttribute("aria-disabled", "true");
  }
  function isOff(btn) { return btn.disabled || btn.getAttribute("aria-disabled") === "true"; }
  function guard(id, handler) { $(id).addEventListener("click", function () { if (!isOff($(id))) handler(); }); }
  // Said out loud to screen-reader players without moving focus (a new transmission, a contact).
  function announce(text) {
    var live = $("announce");
    live.textContent = "";
    setTimeout(function () { live.textContent = text; }, 40);
  }
  // Rebuild a group of controls only when WHAT it holds changes, so a focused button or field survives the
  // redraw that follows every action. `signature` is any string that changes when the contents should.
  function fillOnce(container, signature, build) {
    if (container.dataset.signature === signature) return false;
    container.textContent = "";
    build(container);
    container.dataset.signature = signature;
    return true;
  }
  // Notebook rows are rebuilt only when the set of entries changes; otherwise each field just takes the
  // engine's stored text, unless the player is typing in it.
  function syncNotebookValues(list) {
    list.querySelectorAll("input[type=text]").forEach(function (input) {
      var stored = (A.view.notebook || {})[input.dataset.token] || "";
      if (document.activeElement !== input && input.value !== stored) input.value = stored;
    });
  }
  function ordinalIn(list, code) { var i = (list || []).indexOf(code); return i === -1 ? 0 : i + 1; }

  // Long-press to copy a sign from a scene into the transmit line.
  function attachLongPress(node, value) {
    var timer = null;
    node.addEventListener("touchstart", function () {
      if (document.documentElement.getAttribute("data-reduced-motion") === "true" || document.documentElement.getAttribute("data-effects") === "off") return;
      timer = setTimeout(function () {
        if (A.currentPlanet === "pulse") A.addMarks(value);
        else if (A.currentPlanet === "compound" && A.outgoingGlyph.length < 4) { A.outgoingGlyph += value; A.renderCompound(); }
        else if (A.currentPlanet === "bridge") A.addToMessage(value);
      }, 500);
    });
    node.addEventListener("touchend", function () { clearTimeout(timer); });
    node.addEventListener("touchmove", function () { clearTimeout(timer); });
  }

  // ---- mobile transmit pad -------------------------------------------------------------------
  var audioCtx = null;
  function playBuzz(type) {
    if (document.documentElement.getAttribute("data-reduced-motion") === "true" || document.documentElement.getAttribute("data-effects") === "off") return;
    if (!window.AudioContext && !window.webkitAudioContext) return;
    if (audioCtx === null) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    if (audioCtx.state === "suspended") audioCtx.resume();
    var osc = audioCtx.createOscillator();
    var gain = audioCtx.createGain();
    osc.type = "square";
    osc.frequency.value = type === "tick" ? 800 : 400;
    gain.gain.value = 0.15;
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.start();
    osc.stop(audioCtx.currentTime + (type === "tick" ? 0.08 : 0.2));
  }
  function initTransmitPad() {
    var pad = document.getElementById("transmit-pad");
    if (pad) return;
    pad = document.createElement("div");
    pad.id = "transmit-pad";
    pad.className = "transmit-pad";
    var tickBtn = document.createElement("button");
    tickBtn.type = "button";
    tickBtn.className = "pad-btn tick";
    tickBtn.setAttribute("aria-label", "Short signal (tick)");
    tickBtn.addEventListener("click", function () { A.addMarks("0"); playBuzz("tick"); });
    var barBtn = document.createElement("button");
    barBtn.type = "button";
    barBtn.className = "pad-btn bar";
    barBtn.setAttribute("aria-label", "Long signal (bar)");
    barBtn.addEventListener("click", function () { A.addMarks("1"); playBuzz("bar"); });
    pad.appendChild(tickBtn);
    pad.appendChild(barBtn);
    document.getElementById("game").appendChild(pad);
  }

  function initCrewLogSwipe() {
    if (document.documentElement.getAttribute("data-reduced-motion") === "true") return;
    var holder = $("crew-log-entries");
    if (!holder) return;
    var startX = 0;
    holder.addEventListener("touchstart", function (e) { startX = e.touches[0].clientX; }, { passive: true });
    holder.addEventListener("touchend", function (e) {
      var diff = startX - e.changedTouches[0].clientX;
      if (Math.abs(diff) > 50) {
        holder.scrollBy({ left: diff, behavior: "smooth" });
      }
    }, { passive: true });
  }

  function initResumeButton() {
    var btn = document.getElementById("resume-btn");
    if (!btn) {
      btn = document.createElement("button");
      btn.id = "resume-btn";
      btn.className = "resume-btn";
      btn.textContent = "Resume last visit";
      btn.addEventListener("click", loadResumeFrame);
      var gameEl = document.getElementById("game");
      if (gameEl) gameEl.appendChild(btn);
    }
    updateResumeButton();
  }

  function saveResumeFrame() {
    var frame = {
      planet: A.currentPlanet,
      outgoing: A.outgoing,
      glyph: A.outgoingGlyph,
      message: A.outgoingMessage.slice(),
      benchTarget: A.benchTarget,
      benchA: A.currentBenchA,
      benchB: A.currentBenchB
    };
    try { localStorage.setItem(RESUME_KEY, JSON.stringify(frame)); } catch(e) {}
  }

  function loadResumeFrame() {
    var raw = lsGet(RESUME_KEY);
    if (!raw) return;
    try {
      var frame = JSON.parse(raw);
      A.currentPlanet = frame.planet || "pulse";
      A.outgoing = frame.outgoing || "";
      A.outgoingGlyph = frame.glyph || "";
      A.outgoingMessage = frame.message || [];
      A.benchTarget = frame.benchTarget || null;
      A.currentBenchA = frame.benchA || 0;
      A.currentBenchB = frame.benchB || 0;
      A.render();
    } catch(e) {}
  }

  function updateResumeButton() {
    var btn = document.getElementById("resume-btn");
    if (!btn) return;
    btn.hidden = !lsGet(RESUME_KEY);
  }

  // ---- drawing helpers -----------------------------------------------------------------------
  function markNode(ch) {
    var span = document.createElement("span");
    span.className = ch === "1" ? "mark-1" : "mark-0";
    span.setAttribute("aria-hidden", "true");
    return span;
  }
  function describeMarks(marks) {
    return marks.split("").map(function (c) { return c === "1" ? "long" : "short"; }).join(", ");
  }
  function tokenNode(marks) {
    var span = document.createElement("span");
    span.className = "token";
    span.dataset.sign = marks;          // read by pc.js: hovering a sign lights every copy of it
    span.setAttribute("role", "img");
    span.setAttribute("aria-label", describeMarks(marks));
    marks.split("").forEach(function (c) { span.appendChild(markNode(c)); });
    return span;
  }
  function signalNode(marks) {
    var wrap = document.createElement("span");
    wrap.className = "signal";
    for (var i = 0; i < marks.length; i += TOKEN_LEN) wrap.appendChild(tokenNode(marks.slice(i, i + TOKEN_LEN)));
    return wrap;
  }
  function lampsText(n) { return n === 0 ? "no lamps lit" : n === 1 ? "1 lamp lit" : n + " lamps lit"; }

  // The newest transmission is highlighted (an effect, switchable) and read out; the redraws that follow a
  // notebook edit or a tab change are not new transmissions and stay quiet.
  function noteScenes(planet, list) {
    var count = A.view.scenes.length, before = A.shownScenes[planet];
    A.shownScenes[planet] = count;
    if (before === null || count <= before || !list.lastElementChild) return;
    var last = list.lastElementChild;
    last.classList.add("fresh");
    var said = last.querySelector(".reply");
    announce("Transmission " + count + " received. " + last.querySelector(".what").textContent + (said ? " " + said.textContent : ""));
  }

  // what the other parts use (see the File map in CLAUDE.md)
  A.$ = $; A.BRIEF_KEY = BRIEF_KEY; A.ENGINE_MODULES = ENGINE_MODULES; A.MAX_MESSAGE = MAX_MESSAGE;
  A.MAX_OUT = MAX_OUT; A.NIGHT_KEY = NIGHT_KEY; A.STORE_KEY = STORE_KEY; A.TOKEN_LEN = TOKEN_LEN;
  A.applyNight = applyNight; A.attachLongPress = attachLongPress; A.describeMarks = describeMarks;
  A.fillOnce = fillOnce; A.guard = guard; A.initCrewLogSwipe = initCrewLogSwipe;
  A.initResumeButton = initResumeButton; A.initTransmitPad = initTransmitPad; A.lampsText = lampsText;
  A.lsGet = lsGet; A.lsSet = lsSet; A.noteScenes = noteScenes; A.ordinalIn = ordinalIn;
  A.saveResumeFrame = saveResumeFrame; A.setEnabled = setEnabled; A.setText = setText;
  A.signalNode = signalNode; A.syncNotebookValues = syncNotebookValues; A.tokenNode = tokenNode;
})();
