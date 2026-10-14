/*
 * Lighthouse -- R4-LHMO-1: the lamp level as a tall slider at the right edge (phones, night only, when the player has
 * chosen "Slider" under Settings > On a phone). It sends the same {action: "level"} the four dock buttons send and
 * follows the engine's own lamp level, so the two always agree. A real <input type="range">, so the arrow keys,
 * Home/End and screen readers work; the four notches are labels beside it.
 */
(function () {
  "use strict";
  var wrap = document.getElementById("lamp-slider-wrap");
  var slider = document.getElementById("lamp-slider");
  if (!wrap || !slider) return;
  var IDS = ["dim", "standard", "bright", "storm"];
  var LABELS = ["Dim", "Standard", "Bright", "Storm"];

  function wanted() { return window.LighthousePhonePrefs && window.LighthousePhonePrefs.get("lamp") === "slider"; }

  function sync(v) {
    var api = window.lighthouseApi;
    v = v || (api && api.view());
    var show = Boolean(v) && v.phase === "night" && wanted();
    wrap.hidden = !show;
    if (!v || !show) return;
    var i = IDS.indexOf(v.beam.level);
    if (i < 0) i = 0;
    if (String(i) !== slider.value) slider.value = String(i);
    slider.setAttribute("aria-valuetext", LABELS[i]);
    slider.disabled = !(v.oil > 0);
  }

  slider.addEventListener("input", function () {
    var i = parseInt(slider.value, 10);
    if (!(i >= 0 && i <= 3) || !window.lighthouseApi) return;
    slider.setAttribute("aria-valuetext", LABELS[i]);
    window.lighthouseApi.send({ action: "level", level: IDS[i] });
  });

  document.addEventListener("lighthouse-view", function (e) { sync(e.detail); });
  document.addEventListener("lighthouse-phone-pref", function (e) { if (e.detail.name === "lamp") sync(); });
  sync();
})();
