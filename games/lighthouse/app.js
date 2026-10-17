/* Lighthouse, part 6 of 6 (loads last): talking to the engine, seeds, settings, wiring, tutorial, keys and boot. */
(function () {
  "use strict";

  var A = window.LighthouseApp;
  var $ = A.$, BASE_MS = A.BASE_MS, EERIE_KEY = A.EERIE_KEY, ENGINE_MODULES = A.ENGINE_MODULES,
      GAME_ID = A.GAME_ID, HUM_KEY = A.HUM_KEY, LEVEL_IDS = A.LEVEL_IDS, NOTE_KEY = A.NOTE_KEY,
      QUIET_KEY = A.QUIET_KEY, STORE_KEY = A.STORE_KEY, announce = A.announce, guard = A.guard,
      humPref = A.humPref, loadChangelog = A.loadChangelog, lsGet = A.lsGet, lsRemove = A.lsRemove,
      lsSet = A.lsSet, render = A.render, renderScene = A.renderScene, setText = A.setText,
      showToast = A.showToast, soundFor = A.soundFor, syncTime = A.syncTime, wirePanelToggle = A.wirePanelToggle;
  var engine = null;     // { handle, getState, loadState }

  // ---- talking to the engine -------------------------------------------------------------------------
  function persist() {
    try {
      var proxy = engine.getState();
      var obj = proxy.toJs({ dict_converter: Object.fromEntries });
      if (proxy.destroy) proxy.destroy();
      lsSet(STORE_KEY, JSON.stringify(obj));
    } catch (e) { /* the save widget is the real save */ }
  }
  function send(request, userMoved) {
    if (!engine) return null;
    var result = JSON.parse(engine.handle(JSON.stringify(request)));
    if (result.error) { $("engine-status").textContent = "Something went wrong: " + result.error; return null; }
    var before = A.view && A.view.phase;
    render(result, userMoved === undefined ? (before !== result.phase && request.action !== "step") : userMoved);
    if (result.message) { setText($("day-message"), result.message); }
    persist();
    return result;
  }
  function daySend(request) {
    var result = send(request, false);
    if (result) { setText($("day-message"), result.message || ""); announce(result.message || ""); }
  }
  function tick() {
    if (!engine || !A.view || A.view.phase !== "night") return;
    send({ action: "step", n: 1 });
  }

  function randomSeed() {
    try { var a = new Uint32Array(1); window.crypto.getRandomValues(a); return a[0] % 2147483646 + 1; } catch (e) { return Math.floor(Math.random() * 2147483646) + 1; }
  }
  // Z-1c: every new year gets a shared seed text (shared/seed.js); the engine's number is derived from the text,
  // so the same text always gives the same year. Without the shared script it falls back to a plain number.
  function seedNumber(text) { return window.NoyvjSeed.rng(text).randint(1, 2147483646); }
  function runSeed(text) {
    if (window.NoyvjSeed) {
      var t = text || window.NoyvjSeed.newSeed(GAME_ID);
      return { seed: seedNumber(t), seed_text: t };
    }
    return { seed: randomSeed() };
  }
  function newRunRequest(action, text) {
    var r = runSeed(text);
    r.action = action;
    r.quiet = quietPref();
    return r;
  }
  var seedCopies = [];
  function mountSeeds() {
    if (!window.NoyvjSeed) return;
    ["#seed-copy-slot", "#yearend-seed"].forEach(function (sel) {
      if (document.querySelector(sel)) seedCopies.push(window.NoyvjSeed.mountCopy(sel, { seed: "", label: "This year's seed" }));
    });
    // Z-5c: "Today's run" is a year sailed from the UTC date's seed (the same weather, ships and story beats for everyone
    // that day). It asks first, because it replaces the year in progress; nothing else is lost. Finishing the year records it.
    ["#daily-slot", "#yearend-daily"].forEach(function (sel) {
      if (!document.querySelector(sel) || !window.NoyvjSeed.daily) return;
      window.NoyvjSeed.daily.mountButton(sel, {
        game: GAME_ID,
        onStart: function (text) {
          window.NoyvjSeed.set(A.view && A.view.seed_text || "");   // the button set it; put the year's own seed back until the player says yes
          var go = function () { A.orderDraft = null; A.lastPhase = null; send(newRunRequest("abandon", text), true); showToast("Today's year begins from seed " + text + ". Your records are kept."); };
          if (window.ConfirmDialog) window.ConfirmDialog.ask({ id: GAME_ID + "-daily-start", message: "Abandon this year and sail today's seed, " + text + "? Your lifetime records and achievements are kept.", confirmLabel: "Sail today's run", allowSkip: false, onConfirm: go });
          else go();
        },
      });
    });
    if (document.querySelector("#seed-start-slot")) {
      window.NoyvjSeed.mountStart("#seed-start-slot", {
        game: GAME_ID, buttonLabel: "Sail this seed",
        onStart: function (text) {
          var go = function () { A.orderDraft = null; A.lastPhase = null; send(newRunRequest("abandon", text), true); showToast("A fresh year begins from seed " + text + ". Your records are kept."); };
          if (window.ConfirmDialog) window.ConfirmDialog.ask({ id: GAME_ID + "-seed-start", message: "Abandon this year and sail seed " + text + "? Your lifetime records and achievements are kept.", confirmLabel: "Start from this seed", allowSkip: false, onConfirm: go });
          else go();
        },
      });
    }
  }
  // Z-5c: a year sailed from today's seed and brought to its year end counts once for the day (the shared record the hub's
  // Today strip reads). An older day's seed never counts, and nothing in the game changes.
  function recordDaily(v) {
    try {
      var S = window.NoyvjSeed;
      if (!S || !S.daily || !v.seed_text || !S.daily.isDaily(GAME_ID, v.seed_text)) return;
      S.daily.markCompleted(GAME_ID, { text: "Year kept: " + v.rep_title + " to the harbour" });
    } catch (e) { /* the shared record is a courtesy and must never break the page */ }
  }
  function renderSeed(v) {
    if (!window.NoyvjSeed) return;
    window.NoyvjSeed.set(v.seed_text || "");
    seedCopies.forEach(function (c) { if (c) c.update(v.seed_text || ""); });
  }
  function quietPref() { return lsGet(QUIET_KEY) === "on"; }
  function eeriePref() { return lsGet(EERIE_KEY) !== "off"; }
  function applyEerie(on, tell) {
    lsSet(EERIE_KEY, on ? "on" : "off");
    var btn = $("eerie-toggle-button");
    btn.setAttribute("aria-pressed", String(on));
    btn.textContent = "Eerie details: " + (on ? "on" : "off");
    $("eerie-checkbox").checked = on;
    if (tell && engine) send({ action: "settings", eerie: on }, false);
  }
  function maybeContentNote() {
    if (lsGet(NOTE_KEY) || !A.view || !A.view.story.on) return;
    $("content-note-text").textContent = A.view.story.note;
    $("content-note-panel").hidden = false;
  }

  function shareFields() {
    var v = A.view;
    if (!v) return {};
    return {
      game: "Lighthouse",
      seed: v.seed_text || "",
      score: v.mode === "endless" || v.phase === "yearend" ? "Year " + v.year + ", night " + v.night : "Night " + v.night,
      stats: [
        { n: v.meta.ships_passed, one: "ship brought safely past", many: "ships brought safely past" },
        { n: v.meta.nights_kept, one: "night kept", many: "nights kept" },
        v.rep_title + " to the harbour"
      ]
    };
  }
  function mountCopyResult() {
    if (!window.NoyvjCopyResult) return;
    ["#yearend-copy-result", "#report-copy-result"].forEach(function (sel) {
      if (document.querySelector(sel)) window.NoyvjCopyResult.mountButton(sel, { getResult: shareFields });
    });
  }

  // ---- wiring -----------------------------------------------------------------------------------------
  function wire() {
    mountCopyResult();
    mountSeeds();
    guard("light-lamp-button", function () { send({ action: "start_night" }, true); });
    guard("morning-continue-button", function () { send({ action: "end_morning" }, true); });
    guard("end-day-button", function () { A.orderDraft = null; send({ action: "end_day" }, true); });
    guard("continue-button", function () { send({ action: "continue" }, true); });
    guard("wind-button", function () { send({ action: "wind" }); });
    guard("tend-button", function () { send({ action: "tend" }); });
    guard("patch-button", function () { var part = $("patch-select").value; if (part) send({ action: "patch", part: part }); });
    $("ration-select").addEventListener("change", function () { send({ action: "plan", ration: parseInt($("ration-select").value, 10) || 0 }); });
    ["wind", "watch", "repair"].forEach(function (t) {
      $("task-" + t).addEventListener("change", function () { var tasks = {}; tasks[t] = $("task-" + t).checked; send({ action: "plan", tasks: tasks }); });
    });
    $("focus-select").addEventListener("change", function () { send({ action: "plan", focus: $("focus-select").value }); });
    wirePanelToggle("achievements-toggle-button", "achievements-panel");
    wirePanelToggle("letters-toggle-button", "letters-panel");
    wirePanelToggle("changelog-toggle-button", "changelog-panel");
    wirePanelToggle("info-page-toggle-button", "info-page-panel");
    $("quiet-checkbox").checked = quietPref();
    $("sfx-hum-checkbox").checked = humPref();
    $("sfx-hum-checkbox").addEventListener("change", function () { lsSet(HUM_KEY, $("sfx-hum-checkbox").checked ? "on" : "off"); if (A.view) soundFor(A.view); });
    applyEerie(eeriePref(), false);
    $("eerie-toggle-button").addEventListener("click", function () { applyEerie(!eeriePref(), true); announce("Eerie details " + (eeriePref() ? "on" : "off") + "."); });
    $("eerie-checkbox").addEventListener("change", function () { applyEerie($("eerie-checkbox").checked, true); });
    $("content-note-ok").addEventListener("click", function () { lsSet(NOTE_KEY, "seen"); $("content-note-panel").hidden = true; });
    $("content-note-eerie-off").addEventListener("click", function () { lsSet(NOTE_KEY, "seen"); $("content-note-panel").hidden = true; applyEerie(false, true); });
    $("quiet-checkbox").addEventListener("change", function () { lsSet(QUIET_KEY, $("quiet-checkbox").checked ? "on" : "off"); });
    guard("abandon-button", function () {
      var go = function () { A.orderDraft = null; A.lastPhase = null; send(newRunRequest("abandon"), true); showToast("A fresh year begins. Your records are kept."); };
      if (window.ConfirmDialog) window.ConfirmDialog.ask({ id: GAME_ID + "-abandon", message: "Abandon this year and start another? Your lifetime records and achievements are kept.", confirmLabel: "Abandon the year", allowSkip: false, onConfirm: go });
      else go();
    });
    guard("reset-button", function () {
      var go = function () { A.orderDraft = null; A.lastPhase = null; A.knownEarned = null; send(newRunRequest("reset"), true); lsRemove(STORE_KEY); showToast("Everything is reset."); };
      if (window.ConfirmDialog) window.ConfirmDialog.ask({ id: GAME_ID + "-reset", message: "Reset all progress, including records and achievements? This cannot be undone.", confirmLabel: "Reset everything", allowSkip: false, onConfirm: go });
      else go();
    });
    // the save widget loads a save directly into the engine; this redraws the page afterwards
    window.lighthouseRefresh = function () {
      if (!engine) return;
      A.orderDraft = null; A.lastPhase = null; A.knownEarned = null; A.knownUnread = null; A.lastLogCount = 0;
      send({ action: "open" }, false);
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("noyvj-theme-change", function () { if (A.view) renderScene(A.view); });
  }

  var TUTORIAL_STEPS = [
    { title: "The keeper's life", text: "You keep one light on one rock. Each evening you plan the night, the night plays out, and each morning you read how the ships fared. Nothing you do can end the game, and everything can be paused. Skip any time and reopen this from the Tutorial button." },
    { selector: "#hud", title: "The station at a glance", text: "Oil feeds the lamp, energy is yours, The Light is the harbour's opinion of you, and salvage buys upgrades. Every meter has a number and a word as well as a bar." },
    { selector: "#goals-panel", title: "Three goals, no order", text: "Three goals are always on show: the next title the harbour could give you, the upgrade nearest your salvage, and something to try. Do them in any order; each is replaced when it is done." },
    { selector: "#scene-panel", title: "The rock", text: "The beam sweeps the sea and ships pass by. A ship that is lit up by your beam gets a ring and a mark in the list below. Fog, haze, squalls and storms all shorten how far the beam reaches." },
    { selector: "#barometer-card", title: "The barometer", text: "Tonight's weather as a band of two steps. It is right about nine nights in ten, so it is a hint, not a promise." },
    { selector: "#board-card", title: "The harbour board", text: "The ships expected tonight, roughly when, and how far the beam must reach for each to find you. Plan your lamp around them." },
    { selector: "#plan-blocks", title: "The lamp plan", text: "Choose a lamp level for dusk, deep night and dawn. Brighter reaches further and burns more oil; the estimate under it tells you whether the oil will last." },
    { selector: "#task-wind", title: "The keeper's rounds", text: "Tick the rounds you want: winding the clockwork when it runs low, keeping watch, patching between rounds. Each costs energy or supplies." },
    { selector: "#light-lamp-button", title: "Light the lamp", text: "When you are ready. In the night you can pause, speed up to 2x or 4x, change the lamp for the rest of the current part of the night (keys 1 to 4), wind the clockwork (W) and see to trouble (T)." },
    { selector: "#station-panel", title: "The station", text: "Storms wear the tower, the lantern glass, the rail, the dock and the cistern. In the day you mend them with supplies from the supply boat, whose twelve crates you order yourself." },
    { selector: "#letters-toggle-button", title: "Letters", text: "Passing sailors write once their boat has got safely by often enough, and some send gifts. Odd things happen too, and every one of them has a kind explanation." },
    { selector: "#eerie-toggle-button", title: "Eerie details", text: "This switch is always here. Off keeps the letters and the cosy cast but skips the odd happenings. The Story button at bottom left hides the whole story layer." },
    { selector: "#info-page-toggle-button", title: "About the Light", text: "How the rules work, and a few real facts about lighthouses with their sources named." },
    { title: "You are ready", text: "Set the lamp, light it, and keep the sea company. Take your time." },
  ];


  function onKey(e) {
    if (e.altKey || e.ctrlKey || e.metaKey || !A.view || A.view.phase !== "night") return;
    var t = e.target;
    if (!t || !t.closest || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName)) return;
    if (document.querySelector("#opening-screen, #confirm-dialog-overlay:not([hidden]), #tutorial-overlay:not([hidden])")) return;
    var k = e.key.toLowerCase();
    var bindings = window.LIGHTHOUSE_KEYBINDINGS || {};

    // Lamp levels 1-4
    if (k >= "1" && k <= "4") {
      var bound = bindings["lamp-" + parseInt(k, 10)];
      if (!bound || bound.toLowerCase() === k) { e.preventDefault(); send({ action: "level", level: LEVEL_IDS[parseInt(k, 10) - 1] }); }
    }
    // Wind clockwork
    else if (k === "w") {
      var windBound = bindings["wind"];
      if (!windBound || windBound.toLowerCase() === k) { e.preventDefault(); send({ action: "wind" }); }
    }
    // See to trouble
    else if (k === "t") {
      var tendBound = bindings["tend"];
      if (!tendBound || tendBound.toLowerCase() === k) { e.preventDefault(); send({ action: "tend" }); }
    }
  }

  function setBusy(on) {
    ["light-lamp-button", "morning-continue-button", "end-day-button", "continue-button", "wind-button", "tend-button", "patch-button", "abandon-button", "reset-button"].forEach(function (id) { $(id).disabled = on; });
  }

  async function boot() {
    setBusy(true);
    var changelog = loadChangelog();
    var pyodide = await window.loadPyodide();
    for (var i = 0; i < ENGINE_MODULES.length; i++) {
      var source = await (await fetch(ENGINE_MODULES[i])).text();
      pyodide.FS.writeFile(ENGINE_MODULES[i], source, { encoding: "utf8" });
    }
    await pyodide.runPythonAsync(await (await fetch("game.py")).text());
    window.pyodide = pyodide;   // the shared save widget looks for it
    engine = { handle: pyodide.globals.get("handle"), getState: pyodide.globals.get("get_state"), loadState: pyodide.globals.get("load_state") };
    var choice = "continue";
    try { if (window.NoyvjOpeningScreen && window.NoyvjOpeningScreen.choice) choice = await window.NoyvjOpeningScreen.choice; } catch (e) { choice = "continue"; }
    var saved = choice === "new" ? null : lsGet(STORE_KEY);
    var restored = false;
    if (saved) {
      try { engine.loadState(pyodide.toPy(JSON.parse(saved))); restored = true; } catch (e) { restored = false; }
    }
    $("engine-status").textContent = "";
    setBusy(false);
    A.reducedMotion = document.documentElement.getAttribute("data-reduced-motion") === "true";
    engine.handle(JSON.stringify({ action: "settings", eerie: eeriePref() }));
    if (!restored) send(newRunRequest("new_game"), false);
    else {
      send({ action: "open" }, false);
      if (A.view.meta.nights_kept > 0 || A.view.night > 1) showToast("Welcome back. The light is just as you left it.");
    }
    maybeContentNote();
    if (window.NoyvjTime) {
      window.NoyvjTime.start(GAME_ID, tick, BASE_MS);
      var ctl = window.NoyvjTime.get(GAME_ID);
      var setTickMs = function () { var s = ctl.snapshot(); $("scene").style.setProperty("--tick-ms", (s.intervalMs || BASE_MS) + "ms"); };
      ctl.subscribe(setTickMs); setTickMs();
      syncTime(A.view);
    }
    new MutationObserver(function () {
      A.reducedMotion = document.documentElement.getAttribute("data-reduced-motion") === "true";
      if (A.view) renderScene(A.view);
    }).observe(document.documentElement, { attributes: true, attributeFilter: ["data-reduced-motion"] });
    await changelog;
    if (window.GameTutorial) window.GameTutorial.init(window.lighthouseTutorialSteps ? window.lighthouseTutorialSteps(TUTORIAL_STEPS) : TUTORIAL_STEPS, { gameId: GAME_ID });
    if (window.MobileHud) window.MobileHud.init([{ selector: "#hud-night", label: "Night" }, { selector: "#hud-oil", label: "Oil" }, { selector: "#hud-repair", label: "Repair" }, { selector: "#hud-energy", label: "Energy" }]);
    if (window.MobileDock) window.MobileDock.init("#night-controls", { breakpoint: 640 });
    watchDock();
  }

  // On a phone the night controls are pinned to the bottom of the screen; keep the floating pills clear of them.
  function watchDock() {
    var dock = $("night-controls");
    function measure() {
      var h = dock.classList.contains("mobile-docked") && !dock.hidden ? dock.getBoundingClientRect().height : 0;
      document.documentElement.style.setProperty("--dock-h", Math.round(h) + "px");
    }
    if (window.ResizeObserver) new ResizeObserver(measure).observe(dock);
    window.addEventListener("resize", measure);
    document.addEventListener("noyvj-time-change", measure);
    measure();
  }

  wire();
  boot().catch(function (err) {
    $("engine-status").textContent = "The lamp room could not start (" + err + "). Reload to try again.";
  });

  // what the other parts use (see the File map in CLAUDE.md)
  A.daySend = daySend; A.recordDaily = recordDaily; A.renderSeed = renderSeed; A.send = send;
})();
