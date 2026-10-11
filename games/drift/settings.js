/*
 * Drift — settings panel: text-scale + reduce-motion.
 *
 * Site-wide goal (planning/TODO.md, origin A9): one panel per game
 * consolidating text-scale and animation/motion toggles (no sound
 * toggle -- this hub has no audio implemented anywhere yet, see
 * planning/LATER.md's "Standing question: what can you actually do
 * with audio?").
 *
 * Deliberately independent of Pyodide/game.py entirely -- same
 * "browser-level UI preference, not game/save state" pattern
 * Continuum's Phase 5 accessibility.js established first (see that
 * file and games/continuum/CLAUDE.md's Phase 5 build notes). This
 * script has no Python dependency and works even if Pyodide never
 * boots. Persisted to localStorage (per-browser, not per-save) since a
 * baked-in local display preference has no business riding a portable
 * save code -- the exact reasoning Continuum's own Milestone 16 (K15)
 * verification already confirmed for its own text-scale setting.
 *
 * Reduce-motion works by adding a `.reduce-motion` class to the root
 * <html> element; style.css's global override (search "Settings panel:
 * manual" in that file) forces every animation/transition already in
 * the page to be instantaneous while that class is present -- layered
 * on top of, not replacing, the existing per-animation
 * `@media (prefers-reduced-motion: reduce)` rules that already respect
 * the OS-level setting.
 */
(function () {
  "use strict";

  var TEXT_SCALE_KEY = "drift-text-scale";
  var REDUCE_MOTION_KEY = "drift-reduced-motion";
  var MIN_SCALE = 0.85;
  var MAX_SCALE = 1.5;
  var STEP = 0.1;
  var DEFAULT_SCALE = 1.0;
  // I-20: two more display preferences, same per-browser storage and root-class approach as reduce motion.
  var CONTRAST_KEY = "drift-high-contrast";
  var DYSLEXIA_KEY = "drift-easy-read-font";
  // I-21 / I-19: animation speed (slow, normal, fast, off) and spacing density (comfortable, compact).
  var ANIM_SPEED_KEY = "drift-anim-speed";
  var DENSITY_KEY = "drift-density";
  // How long an animation runs relative to its normal length (style.css multiplies every duration by this).
  var ANIM_SCALES = { slow: 2, normal: 1, fast: 0.5, off: 1 };
  var DENSITIES = ["comfortable", "compact"];

  function readChoice(key, allowed, fallback) {
    try {
      var raw = window.localStorage.getItem(key);
      if (allowed.indexOf(raw) !== -1) return raw;
    } catch (e) {
      // Storage can throw in private mode: use the default.
    }
    return fallback;
  }

  function writeChoice(key, value) {
    try {
      window.localStorage.setItem(key, value);
    } catch (e) {
      // Losing persistence is not worth breaking the control.
    }
  }

  function applyAnimSpeed(value) {
    if (!Object.prototype.hasOwnProperty.call(ANIM_SCALES, value)) value = "normal";
    var root = document.documentElement;
    root.setAttribute("data-anim-speed", value);
    root.style.setProperty("--drift-anim-scale", String(ANIM_SCALES[value]));
    writeChoice(ANIM_SPEED_KEY, value);
    return value;
  }

  function applyDensity(value) {
    if (DENSITIES.indexOf(value) === -1) value = "comfortable";
    document.documentElement.setAttribute("data-density", value);
    writeChoice(DENSITY_KEY, value);
    return value;
  }

  // Marks the pressed button of a button group (aria-pressed plus the .active look).
  function markGroup(groupId, attribute, current) {
    var group = document.getElementById(groupId);
    if (!group) return;
    Array.prototype.forEach.call(group.querySelectorAll("button"), function (button) {
      var on = button.getAttribute(attribute) === current;
      button.classList.toggle("active", on);
      button.setAttribute("aria-pressed", on ? "true" : "false");
    });
  }

  function readFlag(key) {
    try {
      return window.localStorage.getItem(key) === "true";
    } catch (e) {
      return false;
    }
  }

  function applyFlag(key, className, value) {
    document.documentElement.classList.toggle(className, value);
    try {
      window.localStorage.setItem(key, value ? "true" : "false");
    } catch (e) {
      // Losing persistence is not worth breaking the control.
    }
    return value;
  }

  function readStoredScale() {
    try {
      var raw = window.localStorage.getItem(TEXT_SCALE_KEY);
      var value = parseFloat(raw);
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
    var clamped = Math.max(MIN_SCALE, Math.min(MAX_SCALE, value));
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
    var scale = applyScale(readStoredScale());
    var reduced = applyMotion(readStoredMotion());

    var contrast = applyFlag(CONTRAST_KEY, "high-contrast", readFlag(CONTRAST_KEY));
    var easyFont = applyFlag(DYSLEXIA_KEY, "easy-read-font", readFlag(DYSLEXIA_KEY));
    var contrastButton = document.getElementById("high-contrast-toggle-button");
    var fontButton = document.getElementById("dyslexia-font-toggle-button");

    function updateFlagLabels() {
      if (contrastButton) {
        contrastButton.textContent = "High Contrast: " + (contrast ? "On" : "Off");
        contrastButton.classList.toggle("active", contrast);
        contrastButton.setAttribute("aria-pressed", contrast ? "true" : "false");
      }
      if (fontButton) {
        fontButton.textContent = "Easy-Read Font: " + (easyFont ? "On" : "Off");
        fontButton.classList.toggle("active", easyFont);
        fontButton.setAttribute("aria-pressed", easyFont ? "true" : "false");
      }
    }
    updateFlagLabels();
    if (contrastButton) {
      contrastButton.addEventListener("click", function () {
        contrast = applyFlag(CONTRAST_KEY, "high-contrast", !contrast);
        updateFlagLabels();
      });
    }
    if (fontButton) {
      fontButton.addEventListener("click", function () {
        easyFont = applyFlag(DYSLEXIA_KEY, "easy-read-font", !easyFont);
        updateFlagLabels();
      });
    }

    var animSpeed = applyAnimSpeed(readChoice(ANIM_SPEED_KEY, Object.keys(ANIM_SCALES), "normal"));
    var density = applyDensity(readChoice(DENSITY_KEY, DENSITIES, "comfortable"));
    markGroup("anim-speed-group", "data-speed", animSpeed);
    markGroup("density-group", "data-density", density);
    Array.prototype.forEach.call(document.querySelectorAll("#anim-speed-group button"), function (button) {
      button.addEventListener("click", function () {
        animSpeed = applyAnimSpeed(button.getAttribute("data-speed"));
        markGroup("anim-speed-group", "data-speed", animSpeed);
      });
    });
    Array.prototype.forEach.call(document.querySelectorAll("#density-group button"), function (button) {
      button.addEventListener("click", function () {
        density = applyDensity(button.getAttribute("data-density"));
        markGroup("density-group", "data-density", density);
      });
    });

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

    var decreaseButton = document.getElementById("text-size-decrease-button");
    var increaseButton = document.getElementById("text-size-increase-button");
    var resetButton = document.getElementById("text-size-reset-button");

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
        contrast = applyFlag(CONTRAST_KEY, "high-contrast", false);
        easyFont = applyFlag(DYSLEXIA_KEY, "easy-read-font", false);
        updateFlagLabels();
        var dusk = document.getElementById("skin-dusk-button"); // the region skin lives in game.py; Dusk is the default
        if (dusk) dusk.click();
        animSpeed = applyAnimSpeed("normal");
        density = applyDensity("comfortable");
        markGroup("anim-speed-group", "data-speed", animSpeed);
        markGroup("density-group", "data-density", density);
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  window.DriftSettings = {
    applyScale: applyScale,
    applyMotion: applyMotion,
    applyFlag: applyFlag,
    applyAnimSpeed: applyAnimSpeed,
    applyDensity: applyDensity,
    MIN_SCALE: MIN_SCALE,
    MAX_SCALE: MAX_SCALE,
  };
})();
