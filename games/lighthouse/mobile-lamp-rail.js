(function () {
  "use strict";
  var RAIL = document.getElementById("lamp-rail");
  if (!RAIL) return;
  var BUTTONS = RAIL.querySelectorAll(".lamp-rail-btn");

  function sync() {
    var active = document.querySelector(".scale-cell[data-in='true']");
    var level = active ? (active.getAttribute("data-level") || "1") : "1";
    BUTTONS.forEach(function(btn) {
      btn.setAttribute("data-active", btn.getAttribute("data-level") === level ? "true" : "false");
    });
  }

  function setLevel(level) {
    BUTTONS.forEach(function(btn) {
      btn.setAttribute("data-active", btn.getAttribute("data-level") === level ? "true" : "false");
    });
    if (typeof window.setLampLevel === "function") {
      window.setLampLevel(level);
    } else {
      document.dispatchEvent(new CustomEvent("lamp-change", { detail: level }));
    }
  }

  BUTTONS.forEach(function(btn) {
    btn.addEventListener("click", function() {
      setLevel(btn.getAttribute("data-level"));
    });
  });

  document.addEventListener("lamp-change", function(e) {
    if (e.detail !== undefined) setLevel(e.detail);
  });

  setTimeout(sync, 100);
})();
