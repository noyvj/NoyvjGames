/* Robot Script -- R4-RSMO-4: swipe an instruction in the list to the left to delete it, with an undo bar.
 * The x button on every step is still the keyboard path. The delete is an ordinary `remove` edit (app.js listens for
 * robotScriptSwipeDelete on document) and Undo is the engine's own undo, so nothing can be lost. */
(function () {
  "use strict";
  var THRESHOLD = 70;       // px of leftward travel that counts as a swipe
  var drag = null;
  var bar = null;

  function ensureBar() {
    if (bar) return bar;
    bar = document.createElement("div");
    bar.id = "undo-bar";
    bar.className = "undo-bar";
    bar.setAttribute("role", "status");
    bar.hidden = true;
    var text = document.createElement("span");
    text.textContent = "Step removed.";
    var btn = document.createElement("button");
    btn.type = "button";
    btn.id = "undo-bar-button";
    btn.textContent = "Undo";
    btn.addEventListener("click", function () {
      hideBar();
      document.dispatchEvent(new CustomEvent("robotScriptSwipeUndo"));
    });
    bar.appendChild(text);
    bar.appendChild(btn);
    document.body.appendChild(bar);
    return bar;
  }
  function showBar() { ensureBar().hidden = false; }
  function hideBar() { if (bar) bar.hidden = true; }

  function reset(node) {
    if (node) node.style.removeProperty("transform");
  }

  function onDown(e) {
    var node = e.target.closest && e.target.closest("#program .node");
    if (!node || e.target.closest("button, select, input, a") || !node.dataset.a) return;
    if (e.pointerType === "mouse" && e.button !== 0) return;
    drag = { node: node, x: e.clientX, y: e.clientY, id: e.pointerId, moved: false };
    try { node.setPointerCapture(e.pointerId); } catch (err) { /* only keeps the drag alive outside the row */ }
  }
  function onMove(e) {
    if (!drag || e.pointerId !== drag.id) return;
    var dx = e.clientX - drag.x;
    var dy = e.clientY - drag.y;
    if (!drag.moved && Math.abs(dy) > Math.abs(dx) && Math.abs(dy) > 10) { drag = null; return; }   // a vertical scroll
    if (dx < -6) {
      drag.moved = true;
      drag.node.style.transform = "translateX(" + Math.max(dx, -120) + "px)";
    } else {
      reset(drag.node);
    }
  }
  function onUp(e) {
    if (!drag || e.pointerId !== drag.id) return;
    var dx = e.clientX - drag.x;
    var node = drag.node;
    drag = null;
    reset(node);
    if (dx <= -THRESHOLD && node.dataset.a) {
      document.dispatchEvent(new CustomEvent("robotScriptSwipeDelete", { detail: node.dataset.a }));
      showBar();
    }
  }
  function onCancel() {
    if (drag) reset(drag.node);
    drag = null;
  }

  document.addEventListener("DOMContentLoaded", function () {
    var program = document.getElementById("program");
    if (!program) return;
    program.addEventListener("pointerdown", onDown);
    program.addEventListener("pointermove", onMove);
    program.addEventListener("pointerup", onUp);
    program.addEventListener("pointercancel", onCancel);
    // any other edit or tap elsewhere closes the bar (nothing is timed)
    document.addEventListener("pointerdown", function (e) {
      if (bar && !bar.hidden && !(e.target.closest && e.target.closest("#undo-bar")) && !(e.target.closest && e.target.closest("#program .node"))) hideBar();
    });
  });
})();
