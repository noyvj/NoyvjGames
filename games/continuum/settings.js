/*
 * Continuum — Phase 5 accessibility: text scaling.
 *
 * Deliberately independent of Pyodide/Three.js entirely (see CLAUDE.md's
 * Phase 5 build notes: "This can and should be built independently of the
 * Three.js work if that's more time-efficient"). This file has no Python
 * dependency and no 3D dependency — it works even if game.py never boots
 * and render3d.js never installs itself, and it is wired up before either
 * of those in index.html's <head>/body order.
 *
 * UX shape follows the same "module-level toggle, plain UI control,
 * browser-level preference rather than game/save state" pattern
 * champ-de-mots' accent-sensitivity toggle already established (see that
 * game's CLAUDE.md, Milestone 8 build notes) — except text size benefits
 * from surviving a reload the way an in-session toggle doesn't need to,
 * so this uses localStorage (matching how the shared save widget and
 * render3d.js's own 2D/3D view toggle both already persist a browser-side
 * UI preference outside of get_state()/load_state()) rather than starting
 * fresh every page load.
 */

(function () {
  "use strict";

  const STORAGE_KEY = "continuum-text-scale";
  const MIN_SCALE = 0.85;
  const MAX_SCALE = 1.5;
  const STEP = 0.1;
  const DEFAULT_SCALE = 1.0;

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

  function init() {
    let scale = readStoredScale();
    applyScale(scale);

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
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  window.ContinuumAccessibility = { applyScale: applyScale, MIN_SCALE: MIN_SCALE, MAX_SCALE: MAX_SCALE };
})();
