(function () {
  "use strict";
  var drawer = null;
  var handle = null;

  function init() {
    drawer = document.getElementById("chip-drawer");
    handle = document.getElementById("chip-drawer-handle");
    if (!drawer || !handle) return;

    handle.addEventListener("click", function () {
      drawer.classList.toggle("open");
    });

    drawer.addEventListener("click", function (e) {
      var btn = e.target.closest(".chip-drawer-content button");
      if (btn && drawer.classList.contains("open")) {
        var type = btn.getAttribute("data-chip-type");
        if (type) {
          drawer.dispatchEvent(new CustomEvent("chip-drawer:place", { detail: { type: type } }));
        }
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
