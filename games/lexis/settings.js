/*
 * Lexis -- display settings: text size, reduced motion, effects, high contrast, theme.
 *
 * Works before the engine loads and, like every game's settings.js, keeps its values in localStorage as a
 * per-device display choice. They are deliberately NOT part of get_state()/load_state(): a save code travels
 * between devices and a local accessibility choice should not override another device's.
 *
 * Reduced motion starts from the system's `prefers-reduced-motion` until the player chooses; effects (the lamp
 * glow and the highlight on a new transmission) are on by default and have their own switch, so a player can
 * keep animation but drop the glow, or the other way round. The page's CSS reads the three html attributes
 * set here (data-reduced-motion, data-effects, data-high-contrast) and the text scale variable.
 */
(function () {
  "use strict";

  var SCALE_KEY = "lexis-text-scale";
  var MOTION_KEY = "lexis-reduced-motion";
  var EFFECTS_KEY = "lexis-effects";
  var CONTRAST_KEY = "lexis-high-contrast";
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

  function init() {
    var panel = document.getElementById("settings-panel");
    var toggle = document.getElementById("settings-toggle-button");
    var motionBox = document.getElementById("reduced-motion-checkbox");
    var effectsBox = document.getElementById("effects-checkbox");
    var contrastBox = document.getElementById("high-contrast-checkbox");
    var themeButton = document.getElementById("theme-setting-button");
    if (motionBox) motionBox.checked = reduced;
    if (effectsBox) effectsBox.checked = effects;
    if (contrastBox) contrastBox.checked = contrast;
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
      remove(CONTRAST_KEY);
      contrast = applyContrast(false, false);
      if (motionBox) motionBox.checked = reduced;
      if (effectsBox) effectsBox.checked = true;
      if (contrastBox) contrastBox.checked = false;
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();

  window.LexisSettings = { applyScale: applyScale, MIN_SCALE: MIN_SCALE, MAX_SCALE: MAX_SCALE };
})();
