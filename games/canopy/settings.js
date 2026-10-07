/*
 * Canopy — settings panel: text-scale + reduced-motion toggle.
 *
 * Deliberately independent of Pyodide entirely, same discipline Continuum's
 * Phase 5 accessibility.js already established (see games/continuum/
 * CLAUDE.md's Phase 5 build notes) -- this file has no Python dependency,
 * so the panel works even if game.py never boots, and it's wired up before
 * game.py's own <script> runs.
 *
 * Consolidates text-scale (A-/A/A+, same clamp/step shape as Continuum's
 * control) and a reduced-motion checkbox into one panel, per
 * planning/TODO.md's "per-game settings panel" site-wide goal (origin A9).
 * Deliberately NO sound toggle -- this hub has no audio system built
 * anywhere yet (see planning/LATER.md's "what can you actually do with
 * audio" standing question), so a sound control here would control
 * nothing real.
 *
 * Both settings are browser-level UI preferences, not game state -- same
 * category champ-de-mots' ACCENT_SENSITIVE toggle and Continuum's own
 * text-scale/view-mode settings already established for this hub (see
 * Continuum's K15 build note): persisted to localStorage so they survive a
 * reload, but deliberately never touching get_state()/load_state(), since
 * a save code is meant to be portable across devices/browsers and a local
 * browser's accessibility preference shouldn't silently override another
 * device's.
 */
// B30: purely decorative seasonal tint on the backdrop, keyed off the
// real calendar month (northern-hemisphere meteorological seasons). Only
// sets a data attribute; style.css does the tinting. Not game state.
(function () {
  try {
    const month = new Date().getMonth(); // 0 = January
    const season = month >= 2 && month <= 4 ? "spring" : month >= 5 && month <= 7 ? "summer" : month >= 8 && month <= 10 ? "autumn" : "winter";
    document.documentElement.setAttribute("data-season", season);
  } catch (err) {
    /* decorative only */
  }
})();

(function () {
  "use strict";

  const TEXT_SCALE_KEY = "canopy-text-scale";
  const MOTION_KEY = "canopy-reduced-motion";
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

  // B-8 / B-10 / B-26: three display options the game reads back from localStorage on every render
  // (game.py's ui_pref()), so they are per-browser like the two above and never part of a save.
  const PLOT_CONTRAST_KEY = "canopy-plot-contrast";
  const SOIL_OVERLAY_KEY = "canopy-soil-overlay";
  const NUMBER_FORMAT_KEY = "canopy-number-format";
  const NUMBER_FORMATS = ["standard", "grouped", "compact", "precise"];
  const DEFAULT_NUMBER_FORMAT = "standard";

  function readFlag(key) {
    try {
      return window.localStorage.getItem(key) === "true";
    } catch (e) {
      return false;
    }
  }

  function writeStored(key, value) {
    try {
      window.localStorage.setItem(key, String(value));
    } catch (e) {
      // Losing persistence isn't worth breaking the control.
    }
  }

  function readNumberFormat() {
    try {
      const value = window.localStorage.getItem(NUMBER_FORMAT_KEY);
      return NUMBER_FORMATS.indexOf(value) >= 0 ? value : DEFAULT_NUMBER_FORMAT;
    } catch (e) {
      return DEFAULT_NUMBER_FORMAT;
    }
  }

  // Asks the game to redraw so a changed option shows at once instead of on the next tick.
  function refreshGame() {
    try {
      if (window.pyodide && window.pyodide.globals) {
        const render = window.pyodide.globals.get("render");
        if (render) render();
      }
    } catch (e) {
      // The game redraws every second anyway.
    }
  }

  function applyPlotContrast(on) {
    document.documentElement.setAttribute("data-plot-contrast", on ? "true" : "false");
    writeStored(PLOT_CONTRAST_KEY, on);
    refreshGame();
    return on;
  }

  function applySoilOverlay(on) {
    document.documentElement.setAttribute("data-soil-overlay", on ? "true" : "false");
    writeStored(SOIL_OVERLAY_KEY, on);
    refreshGame();
    return on;
  }

  function applyNumberFormat(value) {
    const format = NUMBER_FORMATS.indexOf(value) >= 0 ? value : DEFAULT_NUMBER_FORMAT;
    writeStored(NUMBER_FORMAT_KEY, format);
    refreshGame();
    return format;
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

    const contrastCheckbox = document.getElementById("plot-contrast-checkbox");
    const soilCheckbox = document.getElementById("soil-overlay-checkbox");
    const formatSelect = document.getElementById("number-format-select");
    document.documentElement.setAttribute("data-plot-contrast", readFlag(PLOT_CONTRAST_KEY) ? "true" : "false");
    document.documentElement.setAttribute("data-soil-overlay", readFlag(SOIL_OVERLAY_KEY) ? "true" : "false");
    if (contrastCheckbox) {
      contrastCheckbox.checked = readFlag(PLOT_CONTRAST_KEY);
      contrastCheckbox.addEventListener("change", function () {
        applyPlotContrast(contrastCheckbox.checked);
      });
    }
    if (soilCheckbox) {
      soilCheckbox.checked = readFlag(SOIL_OVERLAY_KEY);
      soilCheckbox.addEventListener("change", function () {
        applySoilOverlay(soilCheckbox.checked);
      });
    }
    if (formatSelect) {
      formatSelect.value = readNumberFormat();
      formatSelect.addEventListener("change", function () {
        formatSelect.value = applyNumberFormat(formatSelect.value);
      });
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
        if (contrastCheckbox) contrastCheckbox.checked = false;
        if (soilCheckbox) soilCheckbox.checked = false;
        if (formatSelect) formatSelect.value = DEFAULT_NUMBER_FORMAT;
        applyPlotContrast(false);
        applySoilOverlay(false);
        applyNumberFormat(DEFAULT_NUMBER_FORMAT);
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  window.CanopySettings = { applyScale: applyScale, applyMotion: applyMotion, applyPlotContrast: applyPlotContrast, applySoilOverlay: applySoilOverlay, applyNumberFormat: applyNumberFormat, MIN_SCALE: MIN_SCALE, MAX_SCALE: MAX_SCALE };
})();
