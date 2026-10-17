/* Signal, part 3 of 4: persisting state, talking to the engine, applying a response, act(), and starting Pyodide and the engine. */
(function () {
  "use strict";

  var A = window.SignalPage;
  var $ = A.$, LS_STATE = A.LS_STATE, LS_VIEW = A.LS_VIEW, PYODIDE_URL = A.PYODIDE_URL,
      SIGNAL_PY_MODULES = A.SIGNAL_PY_MODULES, SLOW_MODES = A.SLOW_MODES, catalogPromise = A.catalogPromise,
      jsonParse = A.jsonParse, lsGet = A.lsGet, lsSet = A.lsSet, nextFrame = A.nextFrame, render = A.render,
      renderAchievements = A.renderAchievements, renderStats = A.renderStats, setMessage = A.setMessage,
      timings = A.timings, toastQueue = A.toastQueue;
  var api = null;
  var engineStarting = false;
  var booting = false;

  // ---- engine plumbing ---------------------------------------------------------------
  function persistState() {
    try {
      var proxy = window.pyodide.globals.get("get_state")();
      var obj = proxy.toJs({ dict_converter: Object.fromEntries });
      proxy.destroy();
      A.currentState = jsonParse(JSON.stringify(obj, function (k, v) { return v === undefined ? null : v; }));
      lsSet(LS_STATE, JSON.stringify(A.currentState));
    } catch (err) {
      console.error("signal: persist failed", err);
    }
    renderAchievements();
  }

  function cacheView() {
    if (A.view) lsSet(LS_VIEW, JSON.stringify(A.view));
  }

  function showToast(text) {
    toastQueue.push(text);
    if (toastQueue.length === 1) nextToast();
  }
  function nextToast() {
    if (!toastQueue.length) return;
    var node = $("achievement-toast");
    $("achievement-toast-text").textContent = toastQueue[0];
    node.hidden = false;
    setTimeout(function () {
      node.hidden = true;
      toastQueue.shift();
      nextToast();
    }, 3200);
  }

  function send(req) {
    return JSON.parse(api(JSON.stringify(req)));
  }

  function triggerHaptic(reading, top) {
    if (navigator.vibrate && document.documentElement.getAttribute("data-reduced-motion") !== "true") {
      var ms = Math.max(5, Math.round((reading / top) * 25));
      navigator.vibrate(ms);
    }
  }

  function applyResponse(resp, req) {
    if (resp.view) {
      A.view = resp.view;
      A.cachedValid = true;
      if (resp.view.settings && resp.view.settings.last_preset) $("practice-preset").value = resp.view.settings.last_preset;
    }
    if (!resp.ok) {
      setMessage(resp.error || "Something went wrong.");
    } else if (resp.message) {
      setMessage(resp.message);
    } else if (A.view && A.view.first_run && !A.view.pings.length && A.view.status === "inprogress") {
      setMessage("First time? Tap a tile to ping it. The number is the summed signal there. Then mark where you think the transmitters are.");
    }
    if (req && req.action === "share" && resp.text) A.lastShareText = resp.text;
    if (req && (req.action === "open" || req.action === "practice") && resp.ok) A.lastShareText = "";
    (resp.new || []).forEach(function (a) { showToast("Achievement: " + a.label + " (" + a.description + ")"); });
    (resp.events || []).forEach(function (ev) {
      if (ev.type === "leaderboard" && window.NoyvjLeaderboard) window.NoyvjLeaderboard.report(ev.game, ev.board, ev.score, ev.detail);
    });
    if (resp.dirty) persistState();
    if (A.view) { render(); cacheView(); }
    if (req.action === "ping" && A.view.pings && A.view.pings.length > 0) {
      var lastPing = A.view.pings[A.view.pings.length - 1];
      triggerHaptic(lastPing.v || 0, A.view.board.top || 5);
      var boardEl = $("board");
      if (document.documentElement.getAttribute("data-reduced-motion") !== "true") {
        boardEl.classList.add("haptic-active");
        setTimeout(function() { boardEl.classList.remove("haptic-active"); }, 200);
      }
    }
  }

  var QUEUEABLE = { ping: true, mark: true, clear_marks: true, commit: true, give_up: true, open: true, practice: true };

  async function act(req, opts) {
    opts = opts || {};
    if (!A.engineReady) {
      var relative = req.action === "ping" || req.action === "mark" || req.action === "clear_marks" || req.action === "commit" || req.action === "give_up";
      if (!QUEUEABLE[req.action] || (relative && !A.cachedValid)) {
        setMessage("Receiver warming up... give it a moment, then tap again.");
        startEngine();
        return;
      }
      A.queue.push(req);
      if (req.action === "ping") { A.pendingCells[req.r + "," + req.c] = true; }
      setMessage("Receiver warming up... your tap is queued and will be applied in order.");
      startEngine();
      render();
      return;
    }
    if (opts.slow || (req.action === "practice" && SLOW_MODES[req.mode])) {
      setMessage("Tuning the receiver (generating a big board)...");
      await nextFrame();
    }
    var started = performance.now();
    var resp = send(req);
    if (req.action === "ping" && timings.firstPing === null) {
      timings.firstPing = Math.round(performance.now());
      renderDiagnostics();
    }
    applyResponse(resp, req);
    return performance.now() - started;
  }

  function loadScript(src) {
    return new Promise(function (resolve, reject) {
      var s = document.createElement("script");
      s.src = src;
      s.onload = resolve;
      s.onerror = function () { reject(new Error("could not load " + src)); };
      document.head.appendChild(s);
    });
  }

  function renderDiagnostics() {
    if (timings.paint === null) {
      var paints = performance.getEntriesByName("first-contentful-paint");
      if (paints.length) timings.paint = Math.round(paints[0].startTime);
    }
    var parts = [];
    if (timings.paint !== null) parts.push("first paint " + (timings.paint / 1000).toFixed(2) + " s");
    else {
      var nav = performance.getEntriesByType("navigation")[0];
      if (nav && nav.domContentLoadedEventEnd) parts.push("static shell ready " + (nav.domContentLoadedEventEnd / 1000).toFixed(2) + " s");
    }
    if (timings.pyodide !== null) parts.push("Pyodide loaded " + (timings.pyodide / 1000).toFixed(2) + " s");
    if (timings.ready !== null) parts.push("engine ready " + (timings.ready / 1000).toFixed(2) + " s");
    if (timings.firstPing !== null) parts.push("first ping " + (timings.firstPing / 1000).toFixed(2) + " s" + (timings.firstPingQueued ? " (tapped before ready, queued)" : ""));
    $("diagnostics-line").textContent = parts.length ? "This page load: " + parts.join(", ") + " (all measured from navigation start)." : "";
  }

  async function startEngine() {
    if (engineStarting) return;
    engineStarting = true;
    booting = true;
    try {
      await loadScript(PYODIDE_URL);
      var pyodide = await window.loadPyodide();
      window.pyodide = pyodide;
      timings.pyodide = Math.round(performance.now());
      await catalogPromise;
      await Promise.all(SIGNAL_PY_MODULES.map(async function (name) {
        var moduleSource = await (await fetch(name)).text();
        pyodide.FS.writeFile(name, moduleSource, { encoding: "utf8" });
      }));
      var code = await (await fetch("game.py")).text();
      pyodide.runPython(code);
      timings.game = Math.round(performance.now());
      api = pyodide.globals.get("handle");
      var saved = jsonParse(lsGet(LS_STATE) || "null");
      if (saved) {
        var proxy = pyodide.toPy(saved);
        pyodide.globals.get("load_state")(proxy);
        if (proxy.destroy) proxy.destroy();
      }
      var boot = send({ action: "boot" });
      A.engineReady = true;
      booting = false;
      timings.ready = Math.round(performance.now());
      applyResponse(boot, { action: "boot" });
      if (Object.keys(A.pendingSettings).length) {
        var s = A.pendingSettings;
        A.pendingSettings = {};
        s.action = "settings";
        applyResponse(send(s), s);
      }
      var replay = A.queue;
      A.queue = [];
      A.pendingCells = {};
      if (replay.some(function (q) { return q.action === "ping"; })) timings.firstPingQueued = true;
      for (var i = 0; i < replay.length; i++) {
        var resp = send(replay[i]);
        if (replay[i].action === "ping" && timings.firstPing === null) timings.firstPing = Math.round(performance.now());
        applyResponse(resp, replay[i]);
      }
      persistState();
      renderDiagnostics();
      if (!$("stats-panel").hidden) requestStats();
    } catch (err) {
      console.error("signal: engine failed to start", err);
      booting = false;
      engineStarting = false;
      setMessage("The engine could not load (offline for the first time?). The board is still readable; try reloading.");
    }
  }

  // Called by game.py's load_state() after the save widget loads a save.
  window.signalOnStateLoaded = function () {
    if (!A.engineReady || booting) return;
    var resp = send({ action: "boot" });
    resp.dirty = true;
    applyResponse(resp, { action: "boot" });
    setMessage("Save loaded.");
  };

  async function requestStats() {
    if (!A.engineReady) { renderStats(null); return; }
    renderStats(send({ action: "stats" }));
  }

  // what the other parts use (see the File map in CLAUDE.md)
  A.act = act; A.applyResponse = applyResponse; A.requestStats = requestStats; A.send = send;
  A.startEngine = startEngine;
})();
