/*
 * Hull Repair -- display settings: text size, reduced motion, effects, high contrast, theme.
 *
 * Works before the engine loads and, like every game's settings.js, keeps its values in localStorage as a
 * per-device display choice. They are deliberately NOT part of get_state()/load_state(): a save code travels
 * between devices and a local accessibility choice should not override another device's.
 *
 * Reduced motion starts from the system's `prefers-reduced-motion` until the player chooses; effects (the glow on a joined
 * line) are on by default and have their own switch, so a player can keep movement but drop the glints, or the other way
 * round. Empty-cell dots (a small dot on every cell no line touches yet) are on by default. The page's CSS reads the html
 * attributes set here (data-reduced-motion, data-effects, data-high-contrast, data-dots) and the text scale variable.
 */
(function () {
  "use strict";

  var SCALE_KEY = "hull-repair-text-scale";
  var MOTION_KEY = "hull-repair-reduced-motion";
  var EFFECTS_KEY = "hull-repair-effects";
  var CONTRAST_KEY = "hull-repair-high-contrast";
  var MIN_SCALE = 0.85;
  var MAX_SCALE = 1.5;
  var STEP = 0.1;
  var DEFAULT_SCALE = 1.0;
  var root = document.documentElement;

  function get(key) {
    try { return window.localStorage.getItem(key); } catch (e) { return null; }
  }
  function set(key, value) {
    try { window.localStorage.setItem(key, String(value)); } catch (e) { /* not worth breaking the control */ }
  }
  function remove(key) {
    try { window.localStorage.removeItem(key); } catch (e) { /* ignore */ }
  }
  function systemPrefersReducedMotion() {
    try { return Boolean(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches); } catch (e) { return false; }
  }

  function readScale() {
    var value = parseFloat(get(SCALE_KEY));
    return !isNaN(value) && value >= MIN_SCALE && value <= MAX_SCALE ? value : DEFAULT_SCALE;
  }
  function applyScale(value) {
    var clamped = Math.max(MIN_SCALE, Math.min(MAX_SCALE, Math.round(value * 100) / 100));
    root.style.setProperty("--text-scale", clamped);
    root.setAttribute("data-text-scale", clamped.toFixed(2));
    set(SCALE_KEY, clamped);
    return clamped;
  }

  // A stored "true"/"false" is the player's choice; nothing stored means "follow the system".
  function motionChoice() {
    var stored = get(MOTION_KEY);
    return stored === "true" ? true : stored === "false" ? false : null;
  }
  function applyMotion(on, remember) {
    root.setAttribute("data-reduced-motion", on ? "true" : "false");
    if (remember) set(MOTION_KEY, on);
    return on;
  }
  function applyEffects(on, remember) {
    root.setAttribute("data-effects", on ? "on" : "off");
    if (remember) set(EFFECTS_KEY, on);
    return on;
  }
  function applyContrast(on, remember) {
    root.setAttribute("data-high-contrast", on ? "true" : "false");
    if (remember) set(CONTRAST_KEY, on);
    return on;
  }

  var scale = applyScale(readScale());
  var reduced = applyMotion(motionChoice() === null ? systemPrefersReducedMotion() : motionChoice(), false);
  var effects = applyEffects(get(EFFECTS_KEY) !== "false", false);
  var contrast = applyContrast(get(CONTRAST_KEY) === "true", false);

  var DOTS_KEY = "hull-repair-dots";
  function applyDots(on, remember) {
    root.setAttribute("data-dots", on ? "on" : "off");
    if (remember) set(DOTS_KEY, on);
    return on;
  }
  var dots = applyDots(get(DOTS_KEY) !== "false", false);

  function init() {
    var panel = document.getElementById("settings-panel");
    var toggle = document.getElementById("settings-toggle-button");
    var motionBox = document.getElementById("reduced-motion-checkbox");
    var effectsBox = document.getElementById("effects-checkbox");
    var contrastBox = document.getElementById("high-contrast-checkbox");
    var dotsBox = document.getElementById("dots-checkbox");
    var themeButton = document.getElementById("theme-setting-button");
    if (motionBox) motionBox.checked = reduced;
    if (effectsBox) effectsBox.checked = effects;
    if (contrastBox) contrastBox.checked = contrast;
    if (dotsBox) dotsBox.checked = dots;
    if (toggle && panel) {
      toggle.addEventListener("click", function () {
        panel.hidden = !panel.hidden;
        toggle.setAttribute("aria-expanded", String(!panel.hidden));
      });
    }
    function on(id, handler) {
      var el = document.getElementById(id);
      if (el) el.addEventListener("click", handler);
    }
    on("text-size-decrease-button", function () { scale = applyScale(scale - STEP); });
    on("text-size-increase-button", function () { scale = applyScale(scale + STEP); });
    on("text-size-reset-button", function () { scale = applyScale(DEFAULT_SCALE); });
    if (motionBox) motionBox.addEventListener("change", function () { reduced = applyMotion(motionBox.checked, true); });
    if (effectsBox) effectsBox.addEventListener("change", function () { effects = applyEffects(effectsBox.checked, true); });
    if (contrastBox) contrastBox.addEventListener("change", function () { contrast = applyContrast(contrastBox.checked, true); });
    if (dotsBox) dotsBox.addEventListener("change", function () { dots = applyDots(dotsBox.checked, true); });

    function syncThemeButton() {
      if (!themeButton || !window.NoyvjTheme) return;
      var light = window.NoyvjTheme.get() === "light";
      themeButton.textContent = light ? "Switch to the dark theme" : "Switch to the light theme";
      themeButton.setAttribute("aria-pressed", String(light));
    }
    if (themeButton) {
      themeButton.addEventListener("click", function () { if (window.NoyvjTheme) window.NoyvjTheme.toggle(); });
      document.addEventListener("noyvj-theme-change", syncThemeButton);
      syncThemeButton();
    }

    on("display-reset-button", function () {
      scale = applyScale(DEFAULT_SCALE);
      remove(MOTION_KEY);
      reduced = applyMotion(systemPrefersReducedMotion(), false);
      remove(EFFECTS_KEY);
      effects = applyEffects(true, false);
      remove(DOTS_KEY);
      dots = applyDots(true, false);
      remove(CONTRAST_KEY);
      contrast = applyContrast(false, false);
      if (motionBox) motionBox.checked = reduced;
      if (effectsBox) effectsBox.checked = true;
      if (contrastBox) contrastBox.checked = false;
      if (dotsBox) dotsBox.checked = true;
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();

  window.HullRepairSettings = { applyScale: applyScale, MIN_SCALE: MIN_SCALE, MAX_SCALE: MAX_SCALE };
})();
