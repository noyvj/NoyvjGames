(function () {
  "use strict";
  var DIVIDER_ID = "split-divider";
  var ROOM_PANEL = "room-panel";
  var EDITOR_PANEL = "editor-panel";
  var MIN_HEIGHT = 60;

  function init() {
    if (window.matchMedia("(max-width: 600px)").matches === false) return;
    var game = document.getElementById("game");
    if (!game) return;
    var roomPanel = document.getElementById(ROOM_PANEL);
    var editorPanel = document.getElementById(EDITOR_PANEL);
    if (!roomPanel || !editorPanel) return;

    var divider = document.createElement("div");
    divider.id = DIVIDER_ID;
    divider.setAttribute("role", "separator");
    divider.setAttribute("aria-orientation", "vertical");
    divider.setAttribute("tabindex", "0");
    game.insertBefore(divider, editorPanel);

    var isDragging = false;
    var startY = 0;
    var startHeight = 0;

    function onPointerDown(e) {
      if (document.documentElement.dataset.reducedMotion === "true" || document.documentElement.dataset.effects === "off") return;
      isDragging = true;
      startY = e.clientY ?? e.touches[0].clientY;
      startHeight = roomPanel.offsetHeight;
      document.addEventListener("mousemove", onPointerMove);
      document.addEventListener("touchmove", onPointerMove, { passive: false });
      document.addEventListener("mouseup", onPointerUp);
      document.addEventListener("touchend", onPointerUp);
    }

    function onPointerMove(e) {
      if (!isDragging) return;
      e.preventDefault();
      var clientY = e.clientY ?? e.touches[0].clientY;
      var delta = clientY - startY;
      var maxH = game.offsetHeight - MIN_HEIGHT;
      var newHeight = Math.max(MIN_HEIGHT, Math.min(maxH, startHeight + delta));
      roomPanel.style.height = newHeight + "px";
    }

    function onPointerUp() {
      isDragging = false;
      document.removeEventListener("mousemove", onPointerMove);
      document.removeEventListener("touchmove", onPointerMove);
      document.removeEventListener("mouseup", onPointerUp);
      document.removeEventListener("touchend", onPointerUp);
    }

    divider.addEventListener("mousedown", onPointerDown);
    divider.addEventListener("touchstart", onPointerDown, { passive: false });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
