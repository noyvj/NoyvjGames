/* Lexis, part 5 of 5 (loads last): talking to the engine, wiring, keys, tutorial steps and boot. */
(function () {
  "use strict";

  var A = window.LexisApp;
  var $ = A.$, BRIEF_KEY = A.BRIEF_KEY, ENGINE_MODULES = A.ENGINE_MODULES, MAX_OUT = A.MAX_OUT,
      NIGHT_KEY = A.NIGHT_KEY, STORE_KEY = A.STORE_KEY, applyNight = A.applyNight,
      generateBenchTarget = A.generateBenchTarget, guard = A.guard, initCrewLogSwipe = A.initCrewLogSwipe,
      initResumeButton = A.initResumeButton, initTransmitPad = A.initTransmitPad,
      loadChangelog = A.loadChangelog, lsGet = A.lsGet, lsSet = A.lsSet, render = A.render,
      renderBench = A.renderBench, renderBridge = A.renderBridge, renderCompound = A.renderCompound,
      renderTransmit = A.renderTransmit, setText = A.setText, setToggleState = A.setToggleState,
      wirePanelToggle = A.wirePanelToggle, wireSceneCards = A.wireSceneCards;

  // ---- talking to the engine -----------------------------------------------------------------
  function persist() {
    try {
      var proxy = A.engine.getState();
      var obj = proxy.toJs({ dict_converter: Object.fromEntries });
      if (proxy.destroy) proxy.destroy();
      lsSet(STORE_KEY, JSON.stringify(obj));
    } catch (e) { /* the save is a convenience until the save widget is wired */ }
  }
  function send(request) {
    request.planet = request.planet || A.currentPlanet;
    var result = JSON.parse(A.engine.handle(JSON.stringify(request)));
    if (result.error) { $("engine-status").textContent = "Something went wrong: " + result.error; return null; }
    if (result.right !== undefined) return result;   // a confirm: not a view
    A.view = result;
    render();
    persist();
    return result;
  }

  function addMarks(marks) {
    if (A.outgoing.length + marks.length > MAX_OUT) return;
    A.outgoing += marks;
    renderTransmit();
  }
  function addPart(code) {
    if (A.outgoingGlyph.length >= 4) return;
    A.outgoingGlyph += code;
    renderCompound();
  }
  function checkedForms(listId) {
    var forms = [];
    $(listId).querySelectorAll("input[type=checkbox]").forEach(function (box) { if (box.checked) forms.push(box.dataset.token); });
    return forms;
  }
  var lastConfirmStamp = 0;
  function triggerConfirmStamp(el) {
    var now = Date.now();
    if (now - lastConfirmStamp < 180000) return; // cooldown: 3 minutes
    lastConfirmStamp = now;
    el.classList.remove("stamp");
    void el.offsetWidth; // force reflow to restart animation
    el.classList.add("stamp");
  }

  function wireCheck(buttonId, listId, resultId) {
    guard(buttonId, function () {
      var forms = checkedForms(listId);
      var out = $(resultId);
      if (!forms.length) { setText(out, "Tick some entries first."); return; }
      var result = send({ action: "confirm", forms: forms });
      var text = result ? result.right + " of the " + result.chosen + " ticked entries are right." : "";
      out.textContent = "";
      setTimeout(function () { out.textContent = text; }, 40);   // re-announced even when the answer is unchanged
      if (result && result.confirm_stamp) triggerConfirmStamp(out);
    });
  }

  function wireCompound() {
    $("tab-pulse").addEventListener("click", function () { A.currentPlanet = "pulse"; send({ action: "open" }); });
    $("tab-compound").addEventListener("click", function () { A.currentPlanet = "compound"; send({ action: "open" }); });
    guard("c-next-scene-button", function () { send({ action: "next_scene" }); });
    guard("c-back-button", function () { A.outgoingGlyph = A.outgoingGlyph.slice(0, -1); renderCompound(); });
    guard("c-clear-button", function () { A.outgoingGlyph = ""; renderCompound(); });
    guard("c-send-button", function () {
      if (!A.outgoingGlyph) return;
      var result = send({ action: "speak", glyph: A.outgoingGlyph });
      if (result && result.reaction) $("c-reaction").textContent = result.reaction.text;
      A.outgoingGlyph = "";
      renderCompound();
    });
    wireCheck("c-check-button", "c-notebook-list", "c-check-result");
  }

  function wireBridge() {
    $("tab-bridge").addEventListener("click", function () { A.currentPlanet = "bridge"; send({ action: "open" }); });
    guard("b-next-scene-button", function () { send({ action: "next_scene" }); });
    guard("b-back-button", function () { A.outgoingMessage.pop(); renderBridge(); });
    guard("b-clear-button", function () { A.outgoingMessage = []; renderBridge(); });
    guard("b-send-button", function () {
      if (!A.outgoingMessage.length) return;
      var result = send({ action: "speak", message: A.outgoingMessage.join(" ") });
      if (result && result.reaction) $("b-reaction").textContent = (result.reaction.reply ? "The station says: " : "") + result.reaction.text;
      A.outgoingMessage = [];
      renderBridge();
    });
    wireCheck("b-check-button", "b-notebook-list", "b-check-result");
  }

  var TUTORIAL_STEPS = [
    { title: "Welcome, officer", text: "You are the communications officer on a survey ship. Each planet speaks a language nobody has translated. Your job is to work out what the signals mean, then answer. Skip any time and reopen this from the Tutorial button." },
    { selector: "#goal-line", title: "The crew's request", text: "The crew tells you what they need from each planet. When you manage it, contact is made and the next planet comes into range." },
    { selector: "#transmissions-panel", title: "Watch what happens", text: "Each transmission is a signal and what the station did when it arrived. Compare them: what stays the same, and what changes?" },
    { selector: "#notebook-panel", title: "Write your guesses", text: "Write what you think each group of marks means. Nothing here is marked right or wrong. Ticking entries and pressing Check tells you how many are right, never which." },
    { selector: "#transmit-panel", title: "Answer", text: "Build a signal and send it. The station answers in its own terms, and when it cannot understand you, it says why." },
    { selector: "#tab-compound", title: "Planet 2", text: "When planet 1 answers, a second world comes into range. Its signs are built from parts, so learning the parts lets you read signs nobody showed you." },
    { selector: "#tab-bridge", title: "Planet 3", text: "The third world builds on the first two: things you learned on planet 2, numbers from planet 1, and a few new marks that change what a message does. Contact here needs a particular result on its counter, and the crew tells you which." },
    { selector: "#crew-log-toggle-button", title: "Crew log", text: "Each contact adds an entry from the crew, newest first, with the mission brief at the bottom. The story never says what a sign means. The Story button, bottom left, hides it." },
    { selector: "#settings-toggle-button", title: "Settings", text: "Text size, reduced motion, an effects switch, high contrast and the light or dark theme. The page follows your system's reduced-motion and theme choices until you pick your own. The What's New button lists every change to Lexis." },
    { selector: "#info-page-toggle-button", title: "About Lexis", text: "Real-world facts behind the game, each with its source named and the date it was read. After you reach planet 3, a Contact report also appears, telling you which of your notebook entries were right." },
    { title: "You are ready", text: "Every word can be worked out from what you are shown. Take your time." },
  ];

  // ---- keyboard ---------------------------------------------------------------------------------
  // Everything is already reachable with Tab (real buttons, tick boxes and fields). These add speed inside a
  // Transmit panel (only while focus is in it, never page-wide) and arrow-key movement along a row of buttons.
  var BUILDERS = {
    pulse: { keys: { s: function () { addMarks("0"); }, l: function () { addMarks("1"); } },
             back: function () { A.outgoing = A.outgoing.slice(0, -1); renderTransmit(); },
             clear: function () { A.outgoing = ""; renderTransmit(); } },
    compound: { keys: {},
                back: function () { A.outgoingGlyph = A.outgoingGlyph.slice(0, -1); renderCompound(); },
                clear: function () { A.outgoingGlyph = ""; renderCompound(); } },
    bridge: { keys: {},
              back: function () { A.outgoingMessage.pop(); renderBridge(); },
              clear: function () { A.outgoingMessage = []; renderBridge(); } },
  };
  function focusSibling(button, step) {
    var row = button.closest(".token-buttons, .builder");
    var all = Array.prototype.slice.call(row.querySelectorAll("button"));
    var at = all.indexOf(button);
    var next = step === "first" ? all[0] : step === "last" ? all[all.length - 1] : all[at + step];
    if (next) next.focus();
  }
  function onKey(e) {
    if (e.altKey || e.ctrlKey || e.metaKey) return;
    var target = e.target;
    if (!target || !target.closest || /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName)) return;
    var rowKey = { ArrowLeft: -1, ArrowRight: 1, Home: "first", End: "last" }[e.key];
    if (rowKey !== undefined && target.tagName === "BUTTON" && target.closest(".token-buttons, .builder")) {
      e.preventDefault();
      focusSibling(target, rowKey);
      return;
    }
    var panel = target.closest("[data-builder]");
    if (!panel) return;
    var builder = BUILDERS[panel.getAttribute("data-builder")];
    if (!builder) return;
    if (e.key === "Backspace") { e.preventDefault(); builder.back(); return; }
    if (e.key === "Delete") { e.preventDefault(); builder.clear(); return; }
    var add = builder.keys[e.key.toLowerCase()];
    if (add && e.key.length === 1) { e.preventDefault(); add(); }
  }

  // Z-20: the shared "Copy result" button under the contact report (the report only exists after planet 3).
  function mountCopyResult() {
    if (!window.NoyvjCopyResult || !$("report-copy-result")) return;
    window.NoyvjCopyResult.mountButton("#report-copy-result", {
      getResult: function () {
        var report = A.view && A.view.report;
        if (!report) return {};
        var t = report.totals;
        return {
          game: "Lexis",
          score: t.right + " of " + t.written + " notebook entries right",
          stats: [
            { n: report.planets.length, one: "planet contacted", many: "planets contacted" },
            t.transmissions + " transmissions received",
            report.achievements.length + " of " + report.achievements_total + " achievements"
          ]
        };
      }
    });
  }

  function wire() {
    mountCopyResult();
    initTransmitPad();
    initResumeButton();
    wireCompound();
    wireBridge();
    wirePanelToggle("achievements-toggle-button", "achievements-panel");
    wirePanelToggle("crew-log-toggle-button", "crew-log-panel");
    initCrewLogSwipe();
    wirePanelToggle("report-toggle-button", "report-panel");
    wirePanelToggle("info-page-toggle-button", "info-page-panel");
    wirePanelToggle("changelog-toggle-button", "changelog-panel");
    wirePanelToggle("star-map-toggle-button", "star-map-panel");
    wirePanelToggle("museum-toggle-button", "museum-panel");
    wirePanelToggle("evidence-toggle-button", "evidence-board-panel");
    wireSceneCards();
    var notebookOpen = false;
    guard("notebook-toggle-button", function () {
      notebookOpen = !notebookOpen;
      $("notebook-panel").classList.toggle("sheet-open", notebookOpen);
      $("notebook-toggle-button").setAttribute("aria-expanded", String(notebookOpen));
    });
    // The save widget loads a save directly into the engine; this redraws the page afterwards.
    window.lexisRefresh = function () {
      if (!A.engine) return;
      A.shownScenes = { pulse: null, compound: null, bridge: null };   // a loaded save is not a new transmission
      send({ action: "open" });
    };
    guard("next-scene-button", function () { send({ action: "next_scene" }); });
    guard("add-0", function () { addMarks("0"); });
    guard("add-1", function () { addMarks("1"); });
    guard("back-button", BUILDERS.pulse.back);
    guard("clear-button", BUILDERS.pulse.clear);
    guard("send-button", function () {
      if (!A.outgoing) return;
      var result = send({ action: "speak", marks: A.outgoing });
      if (result && result.reaction) $("reaction").textContent = result.reaction.text;
      A.outgoing = "";
      renderTransmit();
    });
    wireCheck("check-button", "notebook-list", "check-result");
    guard("bench-new-button", function () {
      A.benchTarget = generateBenchTarget();
      A.currentBenchA = 0;
      A.currentBenchB = 0;
      renderBench();
    });
    guard("bench-check-button", function () { renderBench(); });
    // Close the notebook sheet when turning to landscape so it doesn't overlap the scene.
    window.addEventListener("orientationchange", function () {
      if (window.matchMedia("(orientation: landscape)").matches) {
        var panel = $("notebook-panel");
        if (panel && panel.classList.contains("sheet-open")) {
          panel.classList.remove("sheet-open");
          var btn = $("notebook-toggle-button");
          if (btn) btn.setAttribute("aria-expanded", "false");
        }
      }
    });
    document.addEventListener("keydown", onKey);
  }

  function setBusy(busy) {
    ["next-scene-button", "check-button", "add-0", "add-1", "back-button", "clear-button", "send-button", "c-next-scene-button", "c-check-button", "c-back-button", "c-clear-button", "c-send-button", "b-next-scene-button", "b-check-button", "b-back-button", "b-clear-button", "b-send-button"].forEach(function (id) { $(id).disabled = busy; });
  }

  async function boot() {
    setBusy(true);
    var changelog = loadChangelog();      // the panel and the shared what's-new banner do not need the engine
    var pyodide = await window.loadPyodide();
    for (var i = 0; i < ENGINE_MODULES.length; i++) {
      var source = await (await fetch(ENGINE_MODULES[i])).text();
      pyodide.FS.writeFile(ENGINE_MODULES[i], source, { encoding: "utf8" });
    }
    await pyodide.runPythonAsync(await (await fetch("game.py")).text());
    window.pyodide = pyodide;   // the shared save widget (milestone 5) looks for it
    A.engine = { handle: pyodide.globals.get("handle"), getState: pyodide.globals.get("get_state"), loadState: pyodide.globals.get("load_state"), globe_svg: pyodide.globals.get("globe_svg") };
    var saved = lsGet(STORE_KEY);
    if (saved) {
      try { A.engine.loadState(pyodide.toPy(JSON.parse(saved))); } catch (e) { /* a bad save never blocks play */ }
    }
    $("engine-status").textContent = "";
    setBusy(false);
    applyNight(lsGet(NIGHT_KEY) === "true");
    var nightBtn = document.getElementById("night-toggle-button");
    if (!nightBtn) {
      nightBtn = document.createElement("button");
      nightBtn.id = "night-toggle-button";
      nightBtn.className = "primary";
      nightBtn.textContent = "Night mode";
      nightBtn.addEventListener("click", function () { applyNight(document.documentElement.getAttribute("data-night") !== "true"); });
      var toolbar = document.querySelector(".game-toolbar");
      if (toolbar) toolbar.appendChild(nightBtn);
    }
    send({ action: "open" });
    if (lsGet(BRIEF_KEY) === null) {      // the mission brief opens by itself the first time only
      $("crew-log-panel").hidden = false;
      setToggleState("crew-log-toggle-button", "crew-log-panel");
      lsSet(BRIEF_KEY, "seen");
    }
    await changelog;
    if (window.GameTutorial) window.GameTutorial.init(window.lexisTutorialSteps ? window.lexisTutorialSteps(TUTORIAL_STEPS) : TUTORIAL_STEPS, { gameId: "lexis" });
  }

  wire();
  boot().catch(function (err) {
    $("engine-status").textContent = "The station could not start (" + err + "). Reload to try again.";
  });

  // what the other parts use (see the File map in CLAUDE.md)
  A.addMarks = addMarks; A.addPart = addPart; A.send = send;
})();
