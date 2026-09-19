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

  function init() {
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
  }

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
