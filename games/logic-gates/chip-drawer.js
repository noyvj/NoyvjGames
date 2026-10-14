/* R4-LGMO-2: the phone chip drawer. app.js fills #chip-drawer-content with the same add-a-chip buttons as the Parts panel
   (renderParts); this file only opens and closes the drawer. CSS shows it at max-width 600px on the Classic page only. */
(function () {
  "use strict";

  function init() {
    var drawer = document.getElementById("chip-drawer");
    var handle = document.getElementById("chip-drawer-handle");
    if (!drawer || !handle) return;

    function setOpen(open) {
      drawer.classList.toggle("open", open);
      handle.setAttribute("aria-expanded", String(open));
    }

    handle.addEventListener("click", function () { setOpen(!drawer.classList.contains("open")); });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && drawer.classList.contains("open")) setOpen(false);
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
