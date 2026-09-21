/*
 * Loop — settings panel: text-scale + reduced-motion toggle.
 *
 * Deliberately independent of Pyodide entirely, same discipline Continuum's
 * Phase 5 accessibility.js established (see games/continuum/CLAUDE.md's
 * Phase 5 build notes) and Aftermath/Herd/Thaw's own settings.js already
 * carried over -- this file has no Python dependency, so the panel works
 * even if game.py never boots, and it's wired up before game.py's own
 * <script> runs.
 *
 * Consolidates text-scale (A-/A/A+, same clamp/step shape as Continuum's
 * control) and a reduced-motion checkbox into one panel, per
 * planning/TODO.md's "per-game settings panel" site-wide goal (origin A9).
 * Deliberately NO sound toggle -- this hub has no audio system built
 * anywhere yet (see planning/LATER.md's "what can you actually do with
 * audio" standing question), so a sound control here would control
 * nothing real.
 *
 * Both settings are browser-level UI preferences, not game state --
 * persisted to localStorage so they survive a reload, but deliberately
 * never touching get_state()/load_state(), since a save code is meant to
 * be portable across devices/browsers and a local browser's accessibility
 * preference shouldn't silently override another device's.
 */
(function () {
  "use strict";

  const TEXT_SCALE_KEY = "loop-text-scale";
  const MOTION_KEY = "loop-reduced-motion";
  const MIN_SCALE = 0.85;
  const MAX_SCALE = 1.5;
  const STEP = 0.1;
  const DEFAULT_SCALE = 1.0;

  function readStoredScale() {
    try {
      const raw = window.localStorage.getItem(TEXT_SCALE_KEY);
      const value = parseFloat(raw);
      if (!isNaN(value) && value >= MIN_SCALE && value <= MAX_SCALE) {
        return value;
      }
    } catch (e) {
      // Storage can throw in a locked-down/private-browsing context --
      // fall back to the default rather than failing the whole page.
    }
    return DEFAULT_SCALE;
  }

  function writeStoredScale(value) {
    try {
      window.localStorage.setItem(TEXT_SCALE_KEY, String(value));
    } catch (e) {
      // Losing persistence isn't worth breaking the control for this load.
    }
  }

  function applyScale(value) {
    const clamped = Math.max(MIN_SCALE, Math.min(MAX_SCALE, value));
    document.documentElement.style.setProperty("--text-scale", clamped);
    document.documentElement.setAttribute("data-text-scale", clamped.toFixed(2));
    writeStoredScale(clamped);
    return clamped;
  }

  function readStoredMotion() {
    try {
      return window.localStorage.getItem(MOTION_KEY) === "true";
    } catch (e) {
      return false;
    }
  }

  function writeStoredMotion(value) {
    try {
      window.localStorage.setItem(MOTION_KEY, String(value));
    } catch (e) {
      // Same as above.
    }
  }

  function applyMotion(reduced) {
    document.documentElement.setAttribute("data-reduced-motion", reduced ? "true" : "false");
    writeStoredMotion(reduced);
    return reduced;
  }

  function init() {
    let scale = readStoredScale();
    applyScale(scale);
    let reduced = readStoredMotion();
    applyMotion(reduced);

    const panel = document.getElementById("settings-panel");
    const toggleButton = document.getElementById("settings-toggle-button");
    const decreaseButton = document.getElementById("text-size-decrease-button");
    const increaseButton = document.getElementById("text-size-increase-button");
    const resetButton = document.getElementById("text-size-reset-button");
    const motionCheckbox = document.getElementById("reduced-motion-checkbox");

    if (motionCheckbox) {
      motionCheckbox.checked = reduced;
    }

    if (toggleButton && panel) {
      toggleButton.addEventListener("click", function () {
        panel.hidden = !panel.hidden;
      });
    }
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
    if (motionCheckbox) {
      motionCheckbox.addEventListener("change", function () {
        reduced = applyMotion(motionCheckbox.checked);
      });
    }

    const settingsResetButton = document.getElementById("settings-reset-button");
    if (settingsResetButton) {
      settingsResetButton.addEventListener("click", function () {
        scale = applyScale(DEFAULT_SCALE);
        reduced = applyMotion(false);
        if (motionCheckbox) {
          motionCheckbox.checked = false;
        }
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  window.LoopSettings = { applyScale: applyScale, applyMotion: applyMotion, MIN_SCALE: MIN_SCALE, MAX_SCALE: MAX_SCALE };
})();
