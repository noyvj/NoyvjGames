/*
 * Continuum — settings panel: text-scale + reduce-motion.
 *
 * Milestone 19 (site-wide goal, planning/TODO.md origin A9): "one panel
 * per game consolidating text-scale, sound, and animation toggles."
 * This file used to be accessibility.js, a Phase 5 standalone toolbar
 * control for text-size alone -- it's renamed and extended here to
 * fold that exact, unchanged text-scale behavior into a consolidated
 * `#settings-panel` (same toggle-button-plus-hideable-panel idiom the
 * achievements panel already uses) alongside a new reduce-motion
 * toggle. No sound control -- this hub has no audio implemented
 * anywhere yet (see planning/LATER.md's "Standing question: what can
 * you actually do with audio?"), so a toggle for it would control
 * nothing real.
 *
 * Still deliberately independent of Pyodide/Three.js entirely (see
 * CLAUDE.md's Phase 5 build notes: "This can and should be built
 * independently of the Three.js work if that's more time-efficient").
 * This file has no Python dependency and no 3D dependency -- it works
 * even if game.py never boots and render3d.js never installs itself,
 * and it is wired up before either of those in index.html's
 * <head>/body order.
 *
 * Text-scale UX shape follows the same "module-level toggle, plain UI
 * control, browser-level preference rather than game/save state"
 * pattern champ-de-mots' accent-sensitivity toggle already established
 * (see that game's CLAUDE.md, Milestone 8 build notes) -- except text
 * size benefits from surviving a reload the way an in-session toggle
 * doesn't need to, so this uses localStorage (matching how the shared
 * save widget and render3d.js's own 2D/3D view toggle both already
 * persist a browser-side UI preference outside of
 * get_state()/load_state()) rather than starting fresh every page
 * load. Reduce-motion follows the exact same persistence shape.
 *
 * Reduce-motion works by adding a `.reduce-motion` class to the root
 * <html> element; style.css's global override (search "Settings
 * panel: manual" in that file) forces every animation/transition
 * already in the page to be instantaneous while that class is present
 * -- layered on top of, not replacing, the existing per-animation
 * `@media (prefers-reduced-motion: reduce)` rules that already respect
 * the OS-level setting.
 *
 * The text-scale storage key (`continuum-text-scale`) and its
 * MIN/MAX/STEP/DEFAULT constants are byte-for-byte unchanged from the
 * original accessibility.js -- a player who already set a preference
 * here keeps it after this rename/consolidation, and the control
 * behaves exactly as it did before.
 */
(function () {
  "use strict";

  var STORAGE_KEY = "continuum-text-scale";
  var REDUCE_MOTION_KEY = "continuum-reduced-motion";
  var MIN_SCALE = 0.85;
  var MAX_SCALE = 1.5;
  var STEP = 0.1;
  var DEFAULT_SCALE = 1.0;

  function readStoredScale() {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      const value = parseFloat(raw);
      if (!isNaN(value) && value >= MIN_SCALE && value <= MAX_SCALE) {
        return value;
      }
    } catch (e) {
      // Storage can throw in a locked-down/private-browsing context —
      // fall back to the default rather than failing the whole page.
    }
    return DEFAULT_SCALE;
  }

  function writeStoredScale(value) {
    try {
      window.localStorage.setItem(STORAGE_KEY, String(value));
    } catch (e) {
      // Same as above — losing persistence isn't worth breaking the
      // control for this page load.
    }
  }

  function applyScale(value) {
    const clamped = Math.max(MIN_SCALE, Math.min(MAX_SCALE, value));
    // A single custom property on the root element, read by style.css's
    // own font-size rules (see the ":root { --text-scale }" block) —
    // this is the one thing this file touches outside of its own control
    // buttons, so it can't silently fight any other CSS in the game.
    document.documentElement.style.setProperty("--text-scale", clamped);
    document.documentElement.setAttribute("data-text-scale", clamped.toFixed(2));
    writeStoredScale(clamped);
    return clamped;
  }

  function readStoredMotion() {
    try {
      return window.localStorage.getItem(REDUCE_MOTION_KEY) === "true";
    } catch (e) {
      return false;
    }
  }

  function writeStoredMotion(value) {
    try {
      window.localStorage.setItem(REDUCE_MOTION_KEY, value ? "true" : "false");
    } catch (e) {
      // Same as above.
    }
  }

  function applyMotion(value) {
    document.documentElement.classList.toggle("reduce-motion", value);
    writeStoredMotion(value);
    return value;
  }

  // --- K-30: keyboard shortcut remapping ---------------------------------------
  // The game's shortcuts (index.html's keydown handler asks `actionFor(key)`).
  // Each action has one single-character key. A choice is a per-browser
  // preference kept in localStorage, like the text size above, never part of the
  // save. A key must be a printable single character that is not a space and not
  // already used by another action (the second binding is refused with a
  // message rather than silently swapped). Escape, Tab, Enter, the arrows and
  // modifier combinations are never bindable: they keep their normal meaning.
  var KEYS_STORAGE_KEY = "continuum-keys-v1";
  var KEY_ACTIONS = [
    { id: "pause", label: "Pause or resume time", def: "p" },
    { id: "camera-overview", label: "Camera: overview", def: "1" },
    { id: "camera-closeup", label: "Camera: close-up", def: "2" },
    { id: "camera-aerial", label: "Camera: aerial", def: "3" },
    { id: "camera-isometric", label: "Camera: isometric", def: "4" },
    { id: "screensaver", label: "Screensaver on or off", def: "s" },
    { id: "help", label: "Show or hide the shortcut list", def: "?" },
  ];
  var keyBindings = {};
  var keyListeners = [];

  function normaliseKey(key) {
    if (typeof key !== "string" || key.length !== 1) return null;
    if (key === " " || key.charCodeAt(0) < 33) return null;
    return key.toLowerCase();
  }

  function defaultBindings() {
    var out = {};
    KEY_ACTIONS.forEach(function (a) { out[a.id] = a.def; });
    return out;
  }

  function readStoredKeys() {
    var out = defaultBindings();
    try {
      var raw = JSON.parse(window.localStorage.getItem(KEYS_STORAGE_KEY) || "null");
      if (!raw || typeof raw !== "object") return out;
      var used = {};
      KEY_ACTIONS.forEach(function (a) {
        var key = normaliseKey(raw[a.id]);
        if (key && !used[key]) { out[a.id] = key; used[key] = true; }
      });
      // A partly bad file must not leave two actions on one key: fall back whole.
      var seen = {};
      for (var i = 0; i < KEY_ACTIONS.length; i++) {
        var k = out[KEY_ACTIONS[i].id];
        if (seen[k]) return defaultBindings();
        seen[k] = true;
      }
    } catch (e) {
      return defaultBindings();
    }
    return out;
  }

  function writeStoredKeys() {
    try {
      window.localStorage.setItem(KEYS_STORAGE_KEY, JSON.stringify(keyBindings));
    } catch (e) {
      // Not saved this time; the choice still works until the page closes.
    }
  }

  function keyFor(action) { return keyBindings[action] || null; }

  function actionFor(key) {
    var k = normaliseKey(key);
    if (!k) return null;
    for (var i = 0; i < KEY_ACTIONS.length; i++) {
      if (keyBindings[KEY_ACTIONS[i].id] === k) return KEY_ACTIONS[i].id;
    }
    return null;
  }

  function labelOfKey(key) { return key.length === 1 && key >= "a" && key <= "z" ? key.toUpperCase() : key; }

  function setKey(action, key) {
    var k = normaliseKey(key);
    var known = KEY_ACTIONS.some(function (a) { return a.id === action; });
    if (!known || !k) return { ok: false, reason: "That key cannot be used for a shortcut." };
    var owner = actionFor(k);
    if (owner && owner !== action) {
      var label = KEY_ACTIONS.filter(function (a) { return a.id === owner; })[0].label;
      return { ok: false, reason: labelOfKey(k) + " is already used for: " + label + "." };
    }
    keyBindings[action] = k;
    writeStoredKeys();
    notifyKeys();
    return { ok: true };
  }

  function resetKeys() {
    keyBindings = defaultBindings();
    writeStoredKeys();
    notifyKeys();
  }

  function notifyKeys() {
    refreshShortcutViews();
    keyListeners.forEach(function (fn) { try { fn(); } catch (e) { /* a listener must not break the others */ } });
  }

  // Keep the visible shortcut lists honest: the "?" cheat-sheet and (Desktop
  // layout only) the hint bar under the scene both name the live keys.
  function refreshShortcutViews() {
    var list = document.querySelector("#shortcuts-panel .shortcuts-list");
    if (list) {
      list.innerHTML = "";
      function add(keys, text) {
        var li = document.createElement("li");
        keys.forEach(function (k, i) {
          var kbd = document.createElement("kbd");
          kbd.textContent = k;
          if (i) li.appendChild(document.createTextNode(" "));
          li.appendChild(kbd);
        });
        li.appendChild(document.createTextNode(" " + text));
        list.appendChild(li);
      }
      add([labelOfKey(keyBindings.help)], "show or hide this list");
      add([labelOfKey(keyBindings.pause)], "pause or resume time");
      add(["camera-overview", "camera-closeup", "camera-aerial", "camera-isometric"].map(function (id) { return labelOfKey(keyBindings[id]); }),
        "camera: overview, close-up, aerial, isometric");
      add([labelOfKey(keyBindings.screensaver)], "screensaver on or off (Esc or a click leaves it)");
      add(["Esc"], "close this list");
    }
    var bar = document.getElementById("pc-hintbar");
    if (bar) {
      Array.prototype.forEach.call(bar.querySelectorAll("span"), function (span) {
        var kbd = span.querySelector("kbd");
        if (!kbd) return;
        var text = span.textContent.replace(kbd.textContent, "").trim();
        if (/^Pause/.test(text)) kbd.textContent = labelOfKey(keyBindings.pause);
        else if (/^Camera/.test(text)) {
          var cams = ["camera-overview", "camera-closeup", "camera-aerial", "camera-isometric"].map(function (id) { return keyBindings[id]; });
          var defaults = cams.join("") === "1234";
          kbd.textContent = defaults ? "1\u20134" : cams.map(labelOfKey).join(" ");
        } else if (/^All shortcuts/.test(text)) kbd.textContent = labelOfKey(keyBindings.help);
      });
    }
  }

  function setupKeyBindings() {
    keyBindings = readStoredKeys();
    var list = document.getElementById("keybind-list");
    var status = document.getElementById("keybind-status");
    var resetButton = document.getElementById("keybind-reset-button");
    var capturing = null;
    var buttons = {};

    function say(text) { if (status) status.textContent = text; }

    function paint() {
      KEY_ACTIONS.forEach(function (a) {
        var b = buttons[a.id];
        if (!b) return;
        var isCapturing = capturing === a.id;
        b.textContent = isCapturing ? "Press a key" : labelOfKey(keyBindings[a.id]);
        b.setAttribute("aria-pressed", isCapturing ? "true" : "false");
        b.setAttribute("aria-label", a.label + ": key " + labelOfKey(keyBindings[a.id]) + ". Activate to change it.");
      });
    }

    function stopCapture() {
      capturing = null;
      window.removeEventListener("keydown", onCaptureKey, true);
      paint();
    }

    function onCaptureKey(event) {
      if (event.key === "Shift" || event.key === "Control" || event.key === "Alt" || event.key === "Meta") return;
      event.preventDefault();
      event.stopImmediatePropagation();
      if (event.key === "Escape") { stopCapture(); say("Cancelled. The shortcut keeps its key."); return; }
      if (event.ctrlKey || event.metaKey || event.altKey) { say("Plain keys only: no Ctrl, Alt or Command combinations."); return; }
      var action = capturing;
      var result = setKey(action, event.key);
      if (result.ok) {
        var label = KEY_ACTIONS.filter(function (a) { return a.id === action; })[0].label;
        stopCapture();
        say(label + " is now " + labelOfKey(keyBindings[action]) + ".");
      } else {
        say(result.reason + " Press another key, or Esc to cancel.");
      }
    }

    if (list) {
      KEY_ACTIONS.forEach(function (a) {
        var row = document.createElement("div");
        row.className = "keybind-row";
        var label = document.createElement("span");
        label.className = "keybind-label";
        label.textContent = a.label;
        var button = document.createElement("button");
        button.type = "button";
        button.className = "secondary";
        button.id = "keybind-" + a.id + "-button";
        button.addEventListener("click", function () {
          if (capturing === a.id) { stopCapture(); say("Cancelled."); return; }
          if (capturing) stopCapture();
          capturing = a.id;
          window.addEventListener("keydown", onCaptureKey, true);
          paint();
          say("Press the new key for: " + a.label + ". Esc cancels.");
        });
        buttons[a.id] = button;
        row.appendChild(label);
        row.appendChild(button);
        list.appendChild(row);
      });
    }
    if (resetButton) {
      resetButton.addEventListener("click", function () {
        if (capturing) stopCapture();
        resetKeys();
        paint();
        say("Shortcuts are back to their defaults.");
      });
    }
    keyListeners.push(paint);
    paint();
    refreshShortcutViews();
    // The Desktop layout builds its hint bar after load.
    window.setTimeout(refreshShortcutViews, 1500);
    return { isCapturing: function () { return capturing !== null; } };
  }

  function init() {
    var keyUi = setupKeyBindings();
    window.ContinuumKeys.isCapturing = keyUi.isCapturing;
    let scale = applyScale(readStoredScale());
    let reduced = applyMotion(readStoredMotion());

    var toggleButton = document.getElementById("settings-toggle-button");
    var panel = document.getElementById("settings-panel");
    var open = false;

    function updateToggleLabel() {
      if (!toggleButton) return;
      toggleButton.textContent = open ? "Hide Settings" : "⚙️ Settings";
    }

    if (toggleButton && panel) {
      updateToggleLabel();
      toggleButton.addEventListener("click", function () {
        open = !open;
        panel.hidden = !open;
        updateToggleLabel();
      });
    }

    const decreaseButton = document.getElementById("text-size-decrease-button");
    const increaseButton = document.getElementById("text-size-increase-button");
    const resetButton = document.getElementById("text-size-reset-button");

    if (decreaseButton) {
      decreaseButton.addEventListener("click", function () {
        scale = applyScale(scale - STEP);
      });
    }
    if (increaseButton) {
      increaseButton.addEventListener("click", function () {
        scale = applyScale(scale + STEP);
      });
    }
    if (resetButton) {
      resetButton.addEventListener("click", function () {
        scale = applyScale(DEFAULT_SCALE);
      });
    }

    var motionButton = document.getElementById("reduce-motion-toggle-button");

    function updateMotionLabel() {
      if (!motionButton) return;
      motionButton.textContent = "Reduce Motion: " + (reduced ? "On" : "Off");
      motionButton.classList.toggle("active", reduced);
    }

    if (motionButton) {
      updateMotionLabel();
      motionButton.addEventListener("click", function () {
        reduced = applyMotion(!reduced);
        updateMotionLabel();
      });
    }

    var settingsResetButton = document.getElementById("settings-reset-button");
    if (settingsResetButton) {
      settingsResetButton.addEventListener("click", function () {
        scale = applyScale(DEFAULT_SCALE);
        reduced = applyMotion(false);
        updateMotionLabel();
        resetKeys();
      });
    }
  }

  // Defaults first, so index.html's key handler works even before init() has run.
  keyBindings = readStoredKeys();
  window.ContinuumKeys = {
    actionFor: actionFor,
    keyFor: keyFor,
    setKey: setKey,
    reset: resetKeys,
    actions: KEY_ACTIONS,
    onChange: function (fn) { keyListeners.push(fn); },
    isCapturing: function () { return false; },
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  window.ContinuumSettings = {
    applyScale: applyScale,
    applyMotion: applyMotion,
    MIN_SCALE: MIN_SCALE,
    MAX_SCALE: MAX_SCALE,
  };
})();
