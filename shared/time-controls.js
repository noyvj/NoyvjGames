/*
 * Shared pause and fast-forward control for the real-time games (planning/TODO.md W-2). A small
 * "Pause / 1x / 2x / 4x" group plus the loop that drives a game's tick, so the speed only ever
 * changes HOW OFTEN the game's own tick function is called. It never changes what a tick does:
 *   - 2x calls the tick twice as often (the interval is baseMs / 2), 4x four times as often;
 *   - pause stops calling it at all, so nothing accrues while paused, and no tick is ever
 *     "caught up" afterwards (there is no stored time debt: resuming starts a fresh interval);
 *   - a tick is never skipped or merged, and never run twice in a row to "make up" for lag. If a
 *     slow computer cannot keep up with 4x, the game simply runs slower than 4x.
 * Player actions (clicks, buying, planting) are not ticks and keep working while paused.
 * Full guide: planning/SHARED-COMPONENTS.md, section "Time controls".
 *
 * Markup (one container, ideally near the top of the game):
 *   <div id="time-controls"></div>
 *   <link rel="stylesheet" href="../../shared/time-controls.css">
 *   <script src="../../shared/time-controls.js" data-game-id="sol" data-container="#time-controls"></script>
 *
 * The game hands over its tick instead of calling setInterval itself. From Python (Pyodide):
 *   from js import window
 *   window.NoyvjTime.start("sol", create_proxy(tick), TICK_INTERVAL_MS)      # returns True
 * and from JavaScript NoyvjTime.start(gameId, fn, baseMs). Calling start again replaces the tick
 * (never a second timer). A game that has no NoyvjTime keeps its own setInterval as a fallback.
 *
 * Public API (window.NoyvjTime):
 *   create({gameId, container, speeds, label, keys, modalSelector, onChange})  mount the buttons
 *   start(gameId, tick, baseMs)      give the controller the game's tick (get-or-creates it)
 *   controller(gameId)               the get-or-create controller; get(gameId) is the same, no create
 *   intervalFor(baseMs, speed)       the pure interval rule (>= MIN_INTERVAL_MS)
 *   KEYS                             the documented default keys
 * Controller: speed, speeds, setSpeed(n), pause(), resume(), toggle(), hold(reason), release(reason),
 *   isRunning(), snapshot(), subscribe(fn) -> unsubscribe, handleKey(event) -> true when it acted,
 *   ticksRun, stop(), destroy(). A "hold" is a pause that is not the player's (shared/pause-hidden.js
 *   holds with the reason "hidden"): it never overwrites the player's own pause or speed choice.
 *
 * Keys (documented defaults, only active while no text box, dialog, tutorial or opening screen has
 * the focus; `keys: false` turns them off and a game may call handleKey itself):
 *   Space  pause / resume   (only when no button, link or tile has the focus, because Space
 *                            belongs to a focused control; the Pause button itself is always there)
 *   [      slower (4x -> 2x -> 1x)        ]   faster (1x -> 2x -> 4x)
 * Choosing a speed while paused resumes at that speed.
 *
 * State is never colour alone: the active button gets a check mark and a heavier border, the
 * status line says "Paused" or "Running at 2x" in words with a symbol, and <html data-time-state>
 * is "running", "paused" or "held" for a game that wants to style around it. Transitions only run
 * when neither prefers-reduced-motion nor html[data-reduced-motion="true"] is set (see the css).
 */
(function (root) {
  "use strict";

  var DEFAULT_SPEEDS = [1, 2, 4];
  var MIN_INTERVAL_MS = 20;
  var KEYS = { pause: " ", slower: "[", faster: "]" };
  var DEFAULT_MODAL = "#opening-screen, #confirm-dialog-overlay:not([hidden]), #tutorial-overlay:not([hidden]), " +
    "#kb-shortcuts-panel:not([hidden]), #level-select:not([hidden])";
  var HOLD_LABELS = { hidden: "tab hidden" };
  var INTERACTIVE = 'button, a[href], summary, select, input, textarea, [role="button"], [role="tab"], ' +
    '[role="menuitem"], [role="switch"], [role="checkbox"], [role="option"], [contenteditable], ' +
    '[tabindex]:not([tabindex="-1"])';

  var registry = {};
  var doc = root.document;

  function intervalFor(baseMs, speed) {
    var base = Number(baseMs);
    var s = Number(speed);
    if (!(base > 0)) return 0;
    if (!(s > 0)) s = 1;
    return Math.max(MIN_INTERVAL_MS, Math.round(base / s));
  }

  function sanitizeSpeeds(list) {
    var out = [];
    (Array.isArray(list) ? list : []).forEach(function (n) {
      n = Number(n);
      if (n > 0 && isFinite(n) && out.indexOf(n) === -1) out.push(n);
    });
    out.sort(function (a, b) { return a - b; });
    return out.length ? out : DEFAULT_SPEEDS.slice();
  }

  function el(tag, cls, text) {
    var node = doc.createElement(tag);
    if (cls) node.className = cls;
    if (text != null) node.textContent = text;
    return node;
  }

  function isTypingTarget(target) {
    if (!target || !target.tagName) return false;
    var tag = target.tagName;
    return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || Boolean(target.isContentEditable);
  }

  function modalIsUp(selector) {
    if (!selector) return false;
    var node;
    try { node = doc.querySelector(selector); } catch (e) { return false; }
    return Boolean(node && node.getBoundingClientRect().width > 0);
  }

  function makeController(gameId) {
    var speeds = DEFAULT_SPEEDS.slice();
    var speed = speeds[0];
    var userPaused = false;
    var holds = [];
    var tickFn = null;
    var baseMs = 0;
    var timer = null;
    var listeners = [];
    var ui = null;
    var keyHandler = null;
    var modalSelector = DEFAULT_MODAL;
    var keyMap = KEYS;
    var ticksRun = 0;
    var destroyed = false;

    function isRunning() { return !userPaused && holds.length === 0; }

    function state() {
      if (userPaused) return "paused";
      if (holds.length) return "held";
      return "running";
    }

    function snapshot() {
      var running = isRunning();
      return {
        gameId: gameId,
        speed: speed,
        paused: userPaused,
        held: holds.slice(),
        running: running,
        state: state(),
        effectiveSpeed: running ? speed : 0,
        intervalMs: running && baseMs > 0 ? intervalFor(baseMs, speed) : 0,
        ticksRun: ticksRun
      };
    }

    function fire() {
      // Gate again at call time: a pause or hold that landed between two timer fires must win.
      if (!isRunning() || !tickFn) return;
      ticksRun += 1;
      tickFn();   // an exception here is the game's own (it reaches the error boundary); the timer lives on
    }

    function restartTimer() {
      if (timer !== null) { root.clearInterval(timer); timer = null; }
      if (tickFn && baseMs > 0 && isRunning() && !destroyed) {
        timer = root.setInterval(fire, intervalFor(baseMs, speed));
      }
    }

    function statusText() {
      var s = state();
      if (s === "paused") return "⏸ Paused";
      if (s === "held") {
        var why = HOLD_LABELS[holds[0]] || holds[0];
        return "⏸ Paused (" + why + ")";
      }
      return "▶ Running at " + speed + "x";
    }

    function renderUi() {
      var s = state();
      doc.documentElement.setAttribute("data-time-state", s);
      if (!ui) return;
      ui.group.setAttribute("data-state", s);
      ui.group.setAttribute("data-speed", String(speed));
      ui.pause.setAttribute("aria-pressed", s === "running" ? "false" : "true");
      ui.speedButtons.forEach(function (b) {
        var on = s === "running" && Number(b.getAttribute("data-speed")) === speed;
        b.setAttribute("aria-pressed", on ? "true" : "false");
      });
      ui.status.textContent = statusText();
    }

    function emit() {
      var snap = snapshot();
      listeners.slice().forEach(function (fn) { try { fn(snap); } catch (e) { /* a listener must not break the loop */ } });
      try { doc.dispatchEvent(new root.CustomEvent("noyvj-time-change", { detail: snap })); } catch (e) { /* old browser */ }
    }

    function changed() {
      restartTimer();
      renderUi();
      emit();
    }

    var api = {
      gameId: gameId,
      get speed() { return speed; },
      get speeds() { return speeds.slice(); },
      get ticksRun() { return ticksRun; },
      get paused() { return userPaused; },
      isRunning: isRunning,
      snapshot: snapshot,
      setSpeed: function (n) {
        n = Number(n);
        if (speeds.indexOf(n) === -1) return false;
        var was = speed, wasPaused = userPaused;
        speed = n;
        userPaused = false;   // choosing a speed means "run at this speed"
        if (was !== speed || wasPaused) changed();
        return true;
      },
      pause: function () { if (!userPaused) { userPaused = true; changed(); } return true; },
      resume: function () { if (userPaused) { userPaused = false; changed(); } return true; },
      toggle: function () { return userPaused ? api.resume() : api.pause(); },
      hold: function (reason) {
        reason = String(reason || "hold");
        if (holds.indexOf(reason) === -1) { holds.push(reason); changed(); }
        return true;
      },
      release: function (reason) {
        reason = String(reason || "hold");
        var i = holds.indexOf(reason);
        if (i !== -1) { holds.splice(i, 1); changed(); }
        return true;
      },
      subscribe: function (fn) {
        if (typeof fn !== "function") return function () {};
        listeners.push(fn);
        return function () { var i = listeners.indexOf(fn); if (i !== -1) listeners.splice(i, 1); };
      },
      handleKey: function (event) {
        if (!event || event.defaultPrevented || event.ctrlKey || event.metaKey || event.altKey) return false;
        if (isTypingTarget(event.target) || modalIsUp(modalSelector)) return false;
        var key = event.key;
        if (key === keyMap.pause) {
          if (event.repeat) return false;
          // Space activates a focused control; only take it when nothing like that has the focus.
          var t = event.target;
          if (t && t.closest && t !== doc.body && t !== doc.documentElement && t.closest(INTERACTIVE)) return false;
          api.toggle();
          return true;
        }
        if (key === keyMap.slower || key === keyMap.faster) {
          var at = speeds.indexOf(speed);
          var next = key === keyMap.faster ? at + 1 : at - 1;
          if (next < 0 || next >= speeds.length) return true;   // already at the end: acted, nothing changes
          return api.setSpeed(speeds[next]);
        }
        return false;
      },
      start: function (fn, ms) {
        if (typeof fn !== "function" && !(fn && typeof fn.call === "function")) return false;
        ms = Number(ms);
        if (!(ms > 0)) return false;
        tickFn = fn;
        baseMs = ms;
        changed();
        return true;
      },
      stop: function () { tickFn = null; baseMs = 0; changed(); },
      configure: function (opts) {
        opts = opts || {};
        if (opts.speeds) {
          speeds = sanitizeSpeeds(opts.speeds);
          if (speeds.indexOf(speed) === -1) speed = speeds[0];
        }
        if (typeof opts.modalSelector === "string") modalSelector = opts.modalSelector;
        if (typeof opts.onChange === "function") api.subscribe(opts.onChange);
        if (opts.startPaused) userPaused = true;
        if (opts.keys && typeof opts.keys === "object") keyMap = Object.assign({}, KEYS, opts.keys);
        if (opts.keys === false) {
          if (keyHandler) { doc.removeEventListener("keydown", keyHandler); keyHandler = null; }
        } else if (!keyHandler) {
          keyHandler = function (event) { if (api.handleKey(event)) event.preventDefault(); };
          doc.addEventListener("keydown", keyHandler);
        }
        if (opts.container) mount(opts.container, opts.label);
        changed();
        return api;
      },
      destroy: function () {
        destroyed = true;
        if (timer !== null) { root.clearInterval(timer); timer = null; }
        if (keyHandler) { doc.removeEventListener("keydown", keyHandler); keyHandler = null; }
        if (ui && ui.group.parentNode) ui.group.parentNode.removeChild(ui.group);
        ui = null;
        listeners = [];
        if (registry[gameId] === api) delete registry[gameId];
        doc.documentElement.removeAttribute("data-time-state");
      }
    };

    function mount(container, label) {
      var host = typeof container === "string" ? doc.querySelector(container) : container;
      if (!host) return;
      if (ui && ui.group.parentNode) ui.group.parentNode.removeChild(ui.group);
      var group = el("div", "nt-bar");
      group.setAttribute("role", "group");
      group.setAttribute("aria-label", label || "Game speed");

      var pause = el("button", "nt-btn nt-pause");
      pause.type = "button";
      pause.title = "Pause or resume (Space)";
      var glyph = el("span", "nt-glyph", "⏸");
      glyph.setAttribute("aria-hidden", "true");
      pause.appendChild(glyph);
      pause.appendChild(el("span", "nt-text", "Pause"));
      pause.addEventListener("click", function () { api.toggle(); });
      group.appendChild(pause);

      var speedButtons = speeds.map(function (n) {
        var b = el("button", "nt-btn nt-speed", n + "x");
        b.type = "button";
        b.setAttribute("data-speed", String(n));
        b.setAttribute("aria-label", n === 1 ? "Normal speed, 1x" : n + "x speed");
        b.title = "Run at " + n + "x ([ slower, ] faster)";
        b.addEventListener("click", function () { api.setSpeed(n); });
        group.appendChild(b);
        return b;
      });

      var status = el("span", "nt-status");
      status.setAttribute("role", "status");
      status.setAttribute("aria-live", "polite");
      group.appendChild(status);

      host.textContent = "";
      host.classList.add("nt-host");
      host.appendChild(group);
      ui = { group: group, pause: pause, speedButtons: speedButtons, status: status };
      renderUi();
    }

    return api;
  }

  function controller(gameId) {
    gameId = String(gameId || "game");
    if (!registry[gameId]) registry[gameId] = makeController(gameId);
    return registry[gameId];
  }

  function create(opts) {
    opts = opts || {};
    return controller(opts.gameId).configure(opts);
  }

  function start(gameId, tick, baseMs) {
    return controller(gameId).start(tick, baseMs);
  }

  root.NoyvjTime = {
    create: create,
    start: start,
    controller: controller,
    get: function (gameId) { return registry[String(gameId)] || null; },
    intervalFor: intervalFor,
    KEYS: KEYS,
    MIN_INTERVAL_MS: MIN_INTERVAL_MS,
    DEFAULT_SPEEDS: DEFAULT_SPEEDS
  };

  // Auto-mount from the script tag: <script src=".../time-controls.js" data-game-id="sol" data-container="#time-controls">
  var script = doc.currentScript;
  if (script && script.getAttribute("data-game-id")) {
    var cfg = {
      gameId: script.getAttribute("data-game-id"),
      container: script.getAttribute("data-container") || "#time-controls"
    };
    if (script.getAttribute("data-speeds")) cfg.speeds = script.getAttribute("data-speeds").split(",");
    if (script.getAttribute("data-keys") === "off") cfg.keys = false;
    if (script.getAttribute("data-start-paused") === "true") cfg.startPaused = true;
    if (script.getAttribute("data-modal-selector")) cfg.modalSelector = script.getAttribute("data-modal-selector");
    var boot = function () { create(cfg); };
    if (doc.readyState === "loading") doc.addEventListener("DOMContentLoaded", boot);
    else boot();
  }
})(typeof window !== "undefined" ? window : this);
