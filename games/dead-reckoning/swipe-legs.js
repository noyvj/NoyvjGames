(function () {
  "use strict";
  var LEG_SELECTOR = ".leg";
  var UNDO_THRESHOLD = 60;
  var undoTimeout = null;
  var lastDeleted = null;

  function init() {
    var container = document.querySelector(".legs");
    if (!container) return;

    container.addEventListener("touchstart", onLegStart, { passive: true });
    container.addEventListener("touchmove", onLegMove, { passive: false });
    container.addEventListener("touchend", onLegEnd);
    window.addEventListener("mousemove", onLegMove);
    window.addEventListener("mouseup", onLegEnd);
  }

  var startX = 0, startY = 0, currentX = 0;
  var activeLeg = null;

  function onLegStart(e) {
    var leg = e.target.closest(LEG_SELECTOR);
    if (!leg || leg.classList.contains("deleted")) return;
    startX = e.type === "touchstart" ? e.touches[0].clientX : e.clientX;
    startY = e.type === "touchstart" ? e.touches[0].clientY : e.clientY;
    activeLeg = leg;
    currentX = startX;
  }

  function onLegMove(e) {
    if (!activeLeg) return;
    var clientX = e.type === "touchmove" ? e.touches[0].clientX : e.clientX;
    var clientY = e.type === "touchmove" ? e.touches[0].clientY : e.clientY;
    currentX = clientX;

    var dx = currentX - startX;
    var dy = Math.abs(clientY - startY);

    if (dx > dy) {
      e.preventDefault();
      activeLeg.style.transform = "translateX(" + dx + "px)";
      if (dx < -UNDO_THRESHOLD) {
        activeLeg.classList.add("swiping");
      } else {
        activeLeg.classList.remove("swiping");
      }
    }
  }

  function onLegEnd() {
    if (!activeLeg) return;
    var dx = currentX - startX;

    if (dx < -UNDO_THRESHOLD) {
      activeLeg.classList.add("deleted");
      activeLeg.style.transform = "translateX(-100%)";
      lastDeleted = { leg: activeLeg, index: Array.from(activeLeg.parentNode.children).indexOf(activeLeg) };
      showUndoBar();
      setTimeout(function () {
        if (lastDeleted && lastDeleted.leg.parentNode) {
          lastDeleted.leg.remove();
        }
        lastDeleted = null;
      }, 300);
    } else {
      activeLeg.style.transform = "";
      activeLeg.classList.remove("swiping");
    }
    activeLeg = null;
  }

  function showUndoBar() {
    var bar = document.getElementById("undo-bar");
    if (!bar) return;
    bar.classList.add("visible");
    clearTimeout(undoTimeout);
    undoTimeout = setTimeout(function () {
      bar.classList.remove("visible");
      lastDeleted = null;
    }, 4000);

    var btn = bar.querySelector("#undo-button");
    if (btn) {
      btn.onclick = function () {
        if (lastDeleted && lastDeleted.leg) {
          var container = document.querySelector(".legs");
          if (container) {
            var refNode = container.children[lastDeleted.index];
            container.insertBefore(lastDeleted.leg, refNode || null);
            lastDeleted.leg.style.transform = "";
            lastDeleted.leg.classList.remove("deleted", "swiping");
          }
        }
        bar.classList.remove("visible");
        lastDeleted = null;
      };
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
