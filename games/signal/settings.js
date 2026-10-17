/*
 * Signal -- display settings: text scale, reduced motion, high contrast.
 *
 * Independent of Pyodide (works before the engine loads) and, like every
 * other game's settings.js, a browser-level preference kept in localStorage
 * and deliberately NOT part of get_state()/load_state(): a save code is
 * portable across devices and a local accessibility choice should not
 * override another device's. The game-rule settings (assist shading, ASCII
 * share) do live in the save, see game.py.
 */
(function () {
  "use strict";

  var SCALE_KEY = "signal-text-scale";
  var MOTION_KEY = "signal-reduced-motion";
  var CONTRAST_KEY = "signal-high-contrast";
  var OLED_KEY = "signal-oled-mode";
  var MAGNIFIER_KEY = "signal-magnifier";   // read by app.js (hold-to-aim bubble); "off" turns it off
  var MIN_SCALE = 0.85;
  var MAX_SCALE = 1.5;
  var STEP = 0.1;
  var DEFAULT_SCALE = 1.0;

  function get(key) {
    try { return window.localStorage.getItem(key); } catch (e) { return null; }
  }
  function set(key, value) {
    try { window.localStorage.setItem(key, String(value)); } catch (e) { /* not worth breaking the control */ }
  }
  function readScale() {
    var value = parseFloat(get(SCALE_KEY));
    return !isNaN(value) && value >= MIN_SCALE && value <= MAX_SCALE ? value : DEFAULT_SCALE;
  }
  function applyScale(value) {
    var clamped = Math.max(MIN_SCALE, Math.min(MAX_SCALE, Math.round(value * 100) / 100));
    document.documentElement.style.setProperty("--text-scale", clamped);
    document.documentElement.setAttribute("data-text-scale", clamped.toFixed(2));
    set(SCALE_KEY, clamped);
    return clamped;
  }
  function applyFlag(attr, key, on) {
    document.documentElement.setAttribute(attr, on ? "true" : "false");
    set(key, on);
    return on;
  }

  var scale = applyScale(readScale());
  var reduced = applyFlag("data-reduced-motion", MOTION_KEY, get(MOTION_KEY) === "true");
  var contrast = applyFlag("data-high-contrast", CONTRAST_KEY, get(CONTRAST_KEY) === "true");
  var oled = applyFlag("data-oled", OLED_KEY, get(OLED_KEY) === "true");

  function init() {
    var panel = document.getElementById("settings-panel");
    var toggle = document.getElementById("settings-toggle-button");
    var motionBox = document.getElementById("reduced-motion-checkbox");
    var contrastBox = document.getElementById("high-contrast-checkbox");
    var oledBox = document.getElementById("oled-checkbox");
    var magBox = document.getElementById("magnifier-checkbox");
    if (motionBox) motionBox.checked = reduced;
    if (contrastBox) contrastBox.checked = contrast;
    if (oledBox) oledBox.checked = oled;
    if (magBox) magBox.checked = get(MAGNIFIER_KEY) !== "off";
    if (toggle && panel) toggle.addEventListener("click", function () { panel.hidden = !panel.hidden; });
    function on(id, handler) {
      var el = document.getElementById(id);
      if (el) el.addEventListener("click", handler);
    }
    on("text-size-decrease-button", function () { scale = applyScale(scale - STEP); });
    on("text-size-increase-button", function () { scale = applyScale(scale + STEP); });
    on("text-size-reset-button", function () { scale = applyScale(DEFAULT_SCALE); });
    if (motionBox) motionBox.addEventListener("change", function () { reduced = applyFlag("data-reduced-motion", MOTION_KEY, motionBox.checked); });
    if (contrastBox) contrastBox.addEventListener("change", function () { contrast = applyFlag("data-high-contrast", CONTRAST_KEY, contrastBox.checked); });
    if (oledBox) oledBox.addEventListener("change", function () { oled = applyFlag("data-oled", OLED_KEY, oledBox.checked); });
    if (magBox) magBox.addEventListener("change", function () { set(MAGNIFIER_KEY, magBox.checked ? "on" : "off"); });
    on("display-reset-button", function () {
      scale = applyScale(DEFAULT_SCALE);
      reduced = applyFlag("data-reduced-motion", MOTION_KEY, false);
      contrast = applyFlag("data-high-contrast", CONTRAST_KEY, false);
      oled = applyFlag("data-oled", OLED_KEY, false);
      if (motionBox) motionBox.checked = false;
      if (contrastBox) contrastBox.checked = false;
      if (oledBox) oledBox.checked = false;
      set(MAGNIFIER_KEY, "on");
      if (magBox) magBox.checked = true;
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();

  window.SignalSettings = { applyScale: applyScale, MIN_SCALE: MIN_SCALE, MAX_SCALE: MAX_SCALE };
})();
