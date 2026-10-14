/* Robot Script -- R4-RSMO-9: pinch to zoom a large room on a phone, double-tap (or double-click) to fit again.
 * The zoom is one CSS variable on #room-holder (--room-zoom), so it survives the engine redrawing the room's SVG; the
 * holder scrolls when the room is bigger than the screen. Nothing animates, so reduced motion needs no special case.
 * Pinch only works on a touch screen; the Fit button is the keyboard path (and the zoom buttons) for everyone else. */
(function () {
  "use strict";
  var MIN = 1;
  var MAX = 3;
  var scale = 1;
  var holder = null;
  var pointers = {};
  var startDist = 0;
  var startScale = 1;

  function apply(next) {
    scale = Math.max(MIN, Math.min(MAX, next));
    holder.style.setProperty("--room-zoom", String(Math.round(scale * 100) / 100));
    holder.classList.toggle("room-zoomed", scale > 1);
    var fit = document.getElementById("zoom-fit-button");
    if (fit) fit.hidden = scale <= 1;
  }
  function distance() {
    var ids = Object.keys(pointers);
    var a = pointers[ids[0]], b = pointers[ids[1]];
    return Math.hypot(a.x - b.x, a.y - b.y);
  }

  document.addEventListener("DOMContentLoaded", function () {
    holder = document.getElementById("room-holder");
    if (!holder) return;
    // a Fit button: the way back to the whole room without a double tap
    var fit = document.createElement("button");
    fit.type = "button";
    fit.id = "zoom-fit-button";
    fit.className = "zoom-fit";
    fit.textContent = "Fit room";
    fit.hidden = true;
    fit.addEventListener("click", function () { apply(1); });
    holder.parentNode.insertBefore(fit, holder.nextSibling);

    holder.addEventListener("pointerdown", function (e) {
      if (e.pointerType !== "touch") return;
      pointers[e.pointerId] = { x: e.clientX, y: e.clientY };
      if (Object.keys(pointers).length === 2) { startDist = distance(); startScale = scale; }
    });
    holder.addEventListener("pointermove", function (e) {
      if (!pointers[e.pointerId]) return;
      pointers[e.pointerId] = { x: e.clientX, y: e.clientY };
      if (Object.keys(pointers).length === 2 && startDist > 10) apply(startScale * distance() / startDist);
    });
    function up(e) { delete pointers[e.pointerId]; }
    holder.addEventListener("pointerup", up);
    holder.addEventListener("pointercancel", up);
    holder.addEventListener("dblclick", function () { if (scale > 1) apply(1); });
  });
})();
