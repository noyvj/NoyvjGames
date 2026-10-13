(function () {
  "use strict";
  var PANEL = document.getElementById("letters-panel");
  if (!PANEL) return;

  var TRIGGER = document.createElement("div");
  TRIGGER.className = "swipe-trigger";
  TRIGGER.setAttribute("aria-hidden", "true");
  document.body.appendChild(TRIGGER);

  var startX = 0;
  var isSwiping = false;

  function open() { PANEL.setAttribute("data-open", "true"); }
  function close() { PANEL.removeAttribute("data-open"); }

  TRIGGER.addEventListener("touchstart", function (e) {
    startX = e.touches[0].clientX;
    isSwiping = true;
  }, { passive: true });

  TRIGGER.addEventListener("touchend", function (e) {
    if (!isSwiping) return;
    isSwiping = false;
    var dx = e.changedTouches[0].clientX - startX;
    if (dx > 50 && !PANEL.hasAttribute("data-open")) open();
    else if (dx < -50 && PANEL.hasAttribute("data-open")) close();
  });

  document.addEventListener("click", function (e) {
    if (window.innerWidth > 600 || !PANEL.hasAttribute("data-open")) return;
    if (!PANEL.contains(e.target) && e.target !== TRIGGER) close();
  });
})();
