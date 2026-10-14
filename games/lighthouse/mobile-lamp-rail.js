/*
 * Lighthouse -- R4-LHMO-9: four lamp-level buttons as a one-thumb rail along the bottom edge (phones, night only, when
 * "A rail of four buttons" is chosen under Settings > On a phone). One tap sends the same {action: "level"} the dock's
 * lamp buttons send, and the pressed one follows the engine's own beam level, so the two always agree.
 */
(function () {
  "use strict";
  var rail = document.getElementById("lamp-rail");
  if (!rail) return;
  var buttons = Array.prototype.slice.call(rail.querySelectorAll(".lamp-rail-btn"));

  function wanted() { return window.LighthousePhonePrefs && window.LighthousePhonePrefs.get("lamp") === "rail"; }

  function sync(v) {
    var api = window.lighthouseApi;
    v = v || (api && api.view());
    var show = Boolean(v) && v.phase === "night" && wanted();
    rail.hidden = !show;
    if (!v || !show) return;
    buttons.forEach(function (btn) {
      btn.setAttribute("aria-pressed", String(v.beam.level === btn.dataset.level));
      btn.setAttribute("aria-disabled", String(!(v.oil > 0)));
    });
  }

  buttons.forEach(function (btn) {
    btn.addEventListener("click", function () {
      if (btn.getAttribute("aria-disabled") === "true" || !window.lighthouseApi) return;
      window.lighthouseApi.send({ action: "level", level: btn.dataset.level });
    });
  });

  document.addEventListener("lighthouse-view", function (e) { sync(e.detail); });
  document.addEventListener("lighthouse-phone-pref", function (e) { if (e.detail.name === "lamp") sync(); });
  sync();
})();
