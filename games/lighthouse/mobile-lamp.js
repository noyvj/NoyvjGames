(function () {
  "use strict";
  var WRAP = document.createElement("div");
  WRAP.className = "lamp-slider-wrap";
  WRAP.setAttribute("aria-label", "Lamp level slider");
  var SLIDER = document.createElement("input");
  SLIDER.type = "range";
  SLIDER.min = "0";
  SLIDER.max = "3";
  SLIDER.step = "1";
  SLIDER.className = "lamp-slider";
  SLIDER.setAttribute("aria-valuemin", "0");
  SLIDER.setAttribute("aria-valuemax", "3");
  var NOTCHES = ["Dim", "Standard", "Bright", "Storm"];
  for (var i = 0; i < 4; i++) {
    var N = document.createElement("span");
    N.className = "lamp-notch";
    N.textContent = NOTCHES[i];
    WRAP.appendChild(N);
  }
  WRAP.appendChild(SLIDER);
  document.body.appendChild(WRAP);

  function sync() {
    var active = document.querySelector(".scale-cell[data-in='true']");
    if (active) SLIDER.value = active.getAttribute("data-level") || "1";
  }

  SLIDER.addEventListener("input", function () {
    var lvl = parseInt(SLIDER.value, 10);
    document.querySelectorAll(".scale-cell").forEach(function(c) { c.removeAttribute("data-in"); });
    var target = document.querySelector('.scale-cell[data-level="' + lvl + '"]');
    if (target) target.setAttribute("data-in", "true");
    if (typeof window.lighthouseSetLamp === "function") window.lighthouseSetLamp(lvl);
    else document.dispatchEvent(new CustomEvent("lighthouse-lamp-change", { detail: lvl }));
  });

  sync();
  var obs = new MutationObserver(sync);
  obs.observe(document.body, { attributes: true, subtree: true, attributeFilter: ["data-in"] });
})();
