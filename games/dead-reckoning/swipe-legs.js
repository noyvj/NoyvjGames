/* Dead Reckoning, R4-DEMO-5: swipe a leg card to the left to remove it. This file is only the gesture; app.js removes the leg through the
   engine (one undoable step) and shows the undo bar. Touch and pen only (a mouse has the Remove button); the card follows the finger with no
   animation, so there is nothing for Reduce motion to switch off. The Remove button on every leg stays the keyboard and screen-reader way. */
(function () {
  "use strict";
  var THRESHOLD = 80;      // px to the left that count as a swipe
  var drag = null;

  function init() {
    var list = document.getElementById("legs-list");
    if (!list) return;

    list.addEventListener("pointerdown", function (e) {
      if (e.pointerType === "mouse" || !e.isPrimary) return;
      if (e.target.closest("input, button, select, textarea")) return;       // fields and buttons keep their own touch behaviour
      var li = e.target.closest("li.leg:not(.sailed)");
      if (!li || li.parentNode !== list) return;
      drag = { li: li, id: e.pointerId, x: e.clientX, y: e.clientY, dx: 0, active: false };
    });

    list.addEventListener("pointermove", function (e) {
      if (!drag || e.pointerId !== drag.id) return;
      var dx = e.clientX - drag.x;
      var dy = e.clientY - drag.y;
      if (!drag.active) {
        if (Math.abs(dx) < 10 || Math.abs(dx) < 2 * Math.abs(dy)) return;      // not clearly a sideways drag yet
        drag.active = true;
        drag.li.classList.add("swiping");
        try { drag.li.setPointerCapture(e.pointerId); } catch (err) { /* capture is only a convenience */ }
      }
      drag.dx = Math.min(0, dx);                                                // only leftwards
      drag.li.style.transform = "translateX(" + drag.dx + "px)";
    });

    function finish(e, cancelled) {
      if (!drag || e.pointerId !== drag.id) return;
      var li = drag.li;
      var swiped = drag.active && !cancelled && drag.dx <= -THRESHOLD;
      li.classList.remove("swiping");
      li.style.transform = "";
      var index = Array.prototype.indexOf.call(list.children, li);
      drag = null;
      if (swiped && index >= 0) document.dispatchEvent(new CustomEvent("dead-reckoning-leg-swipe", { detail: { index: index } }));
    }
    list.addEventListener("pointerup", function (e) { finish(e, false); });
    list.addEventListener("pointercancel", function (e) { finish(e, true); });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
