/*
 * Pause a real-time game while its browser tab is hidden (planning/TODO.md Z-28). A hidden tab is
 * not "off": browsers keep running timers, only slower (about once a second, later once a minute),
 * so a game left in a background tab used to advance in tiny silent steps. With this on, the game
 * simply stops while the tab is hidden and says so when you come back.
 *
 * It uses the Page Visibility API only (document.visibilityState + the visibilitychange event).
 * It never touches game rules: it asks the game's time controller to hold, and releases the hold
 * when the tab is visible again. Nothing is stored about the hidden time, so nothing is "caught up"
 * afterwards. A player's own pause or speed choice is never overwritten: the hold sits next to it.
 *
 * Setting. One on/off toggle per game, kept in localStorage as "on"/"off" under `<gameId>-pause-hidden`
 * (the same on/off shape the games' settings.js files use for their other toggles), default ON. It is
 * a per-browser preference, never part of a save. Turning it OFF restores the old behaviour exactly:
 * the game keeps ticking at whatever rate the browser allows for a background tab. Put a checkbox in
 * the game's settings panel and this file wires it, including the panel's "Reset to defaults" button:
 *   <label class="settings-checkbox-label" for="pause-hidden-checkbox">
 *     <input type="checkbox" id="pause-hidden-checkbox" checked> Pause when this tab is hidden</label>
 *
 * When the tab comes back after a hold that really paused a running game, a one-line note appears
 * ("Paused while the tab was hidden") for a few seconds. If the player had paused already there is
 * nothing to report and no note.
 *
 * Away report. A game's own "while you were away" report (SOL's travel report) counts game ticks,
 * not wall-clock time, so the hidden time adds nothing to it: no tick runs while the tab is hidden.
 * A tab that is opened in the background starts held, and runs from the first moment it is visible.
 *
 * Wiring, two ways:
 *   1. Games on shared/time-controls.js (SOL, Canopy, Trade Empire): one tag, nothing else.
 *        <script src="../../shared/pause-hidden.js" data-game-id="sol"></script>
 *      (after time-controls.js). It holds that game's NoyvjTime controller with the reason "hidden".
 *   2. A game with its own clock (Continuum): add data-manual to the tag and call
 *        NoyvjPauseHidden.init({ gameId: "continuum", hooks: { pause() { ...; return true }, resume() { ... } } })
 *      once the game is up. pause() returns true when it stopped something that was running (then the
 *      note is shown on return), false when there was nothing to stop.
 *
 * API (window.NoyvjPauseHidden): init(opts) -> instance, get(gameId), plus on an instance
 * enabled(), setEnabled(bool), isHeld(), check(), note(text), destroy().
 * opts: gameId, hooks, checkbox (selector, default "#pause-hidden-checkbox"), storageKey, defaultOn (true),
 * noteText, noteMs (5000), isHidden() (default document.visibilityState === "hidden"; tests override it).
 */
(function (root) {
  "use strict";

  var doc = root.document;
  var instances = {};
  var STYLE_ID = "pause-hidden-style";
  var NOTE_TEXT = "Paused while the tab was hidden";

  function injectStyle() {
    if (doc.getElementById(STYLE_ID)) return;
    var style = doc.createElement("style");
    style.id = STYLE_ID;
    style.textContent =
      ".ph-note{position:fixed;left:50%;bottom:3.6rem;transform:translateX(-50%);z-index:9998;" +
      "max-width:calc(100vw - 32px);box-sizing:border-box;padding:0.5rem 0.9rem;border-radius:10px;" +
      "border:2px solid #c9d6ff;background:#1c2240;color:#eef0fa;font:600 0.9rem/1.3 system-ui,sans-serif;" +
      "text-align:center;cursor:pointer}" +
      "html[data-theme=light] .ph-note{background:#fff;color:#1b2033;border-color:#243b8a}" +
      "@media (prefers-color-scheme:light){html:not([data-theme]) .ph-note{background:#fff;color:#1b2033;border-color:#243b8a}}" +
      ".ph-note::before{content:'\\23F8  ' / ''}" +
      ".ph-note[hidden]{display:none!important}";
    (doc.head || doc.documentElement).appendChild(style);
  }

  function init(opts) {
    opts = opts || {};
    var gameId = String(opts.gameId || "game");
    if (instances[gameId]) instances[gameId].destroy();

    var storageKey = opts.storageKey || gameId + "-pause-hidden";
    var defaultOn = opts.defaultOn !== false;
    var noteText = opts.noteText || NOTE_TEXT;
    var noteMs = opts.noteMs == null ? 5000 : opts.noteMs;
    var isHidden = typeof opts.isHidden === "function" ? opts.isHidden : function () { return doc.visibilityState === "hidden"; };

    var hooks = opts.hooks;
    if (!hooks) {
      var time = root.NoyvjTime;
      var ctl = time ? time.controller(gameId) : null;
      hooks = ctl ? {
        pause: function () { var was = ctl.isRunning(); ctl.hold("hidden"); return was; },
        resume: function () { ctl.release("hidden"); }
      } : null;
    }

    var held = false;
    var heldWasRunning = false;
    var noteEl = null;
    var noteTimer = null;
    var box = null;
    var resetButton = null;
    var dead = false;

    function enabled() {
      try {
        var raw = root.localStorage.getItem(storageKey);
        if (raw === "on") return true;
        if (raw === "off") return false;
      } catch (e) { /* storage blocked: use the default */ }
      return defaultOn;
    }

    function setEnabled(on) {
      try { root.localStorage.setItem(storageKey, on ? "on" : "off"); } catch (e) { /* not persisted this load */ }
      if (box) box.checked = Boolean(on);
      if (!on && held && !isHidden()) release();
    }

    function hideNote() {
      if (noteTimer) { root.clearTimeout(noteTimer); noteTimer = null; }
      if (noteEl) noteEl.hidden = true;
    }

    function note(text) {
      injectStyle();
      if (!noteEl) {
        noteEl = doc.createElement("div");
        noteEl.className = "ph-note";
        noteEl.id = "pause-hidden-note";
        noteEl.setAttribute("role", "status");
        noteEl.setAttribute("aria-live", "polite");
        noteEl.addEventListener("click", hideNote);
        (doc.body || doc.documentElement).appendChild(noteEl);
      }
      noteEl.textContent = text || noteText;
      noteEl.hidden = false;
      if (noteTimer) root.clearTimeout(noteTimer);
      if (noteMs > 0) noteTimer = root.setTimeout(hideNote, noteMs);
    }

    function hold() {
      if (held || !hooks) return;
      held = true;
      heldWasRunning = Boolean(hooks.pause());
    }

    function release() {
      if (!held) return;
      held = false;
      if (hooks) hooks.resume();
      if (heldWasRunning) note();
      heldWasRunning = false;
    }

    function check() {
      if (dead) return;
      if (isHidden()) { if (enabled()) hold(); }
      else release();
    }

    function onVisibility() { check(); }
    doc.addEventListener("visibilitychange", onVisibility);

    function bindSettings() {
      var selector = opts.checkbox || "#pause-hidden-checkbox";
      box = doc.querySelector(selector);
      if (box) {
        box.checked = enabled();
        box.addEventListener("change", function () { setEnabled(box.checked); });
      }
      resetButton = doc.getElementById("settings-reset-button");
      if (resetButton) resetButton.addEventListener("click", function () { setEnabled(defaultOn); });
    }
    if (doc.readyState === "loading") doc.addEventListener("DOMContentLoaded", bindSettings);
    else bindSettings();

    var instance = {
      gameId: gameId,
      enabled: enabled,
      setEnabled: setEnabled,
      isHeld: function () { return held; },
      check: check,
      note: note,
      destroy: function () {
        dead = true;
        doc.removeEventListener("visibilitychange", onVisibility);
        hideNote();
        if (noteEl && noteEl.parentNode) noteEl.parentNode.removeChild(noteEl);
        noteEl = null;
        if (held && hooks) hooks.resume();
        held = false;
        if (instances[gameId] === instance) delete instances[gameId];
      }
    };
    instances[gameId] = instance;
    check();   // a tab opened in the background starts held
    return instance;
  }

  root.NoyvjPauseHidden = { init: init, get: function (gameId) { return instances[String(gameId)] || null; } };

  var script = doc.currentScript;
  if (script && script.getAttribute("data-game-id") && !script.hasAttribute("data-manual")) {
    var gameId = script.getAttribute("data-game-id");
    var boot = function () { init({ gameId: gameId }); };
    if (doc.readyState === "loading") doc.addEventListener("DOMContentLoaded", boot);
    else boot();
  }
})(typeof window !== "undefined" ? window : this);
