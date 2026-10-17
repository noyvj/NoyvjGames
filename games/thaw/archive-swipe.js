(function () {
  const PANEL = document.getElementById("archive-panel");
  const TOGGLE = document.getElementById("archive-toggle-button");
  if (!PANEL || !TOGGLE) return;

  let startY = 0;
  let panelStartY = 0;
  let isDraggingPanel = false;

  function openSheet() {
    PANEL.classList.add("archive-sheet-open");
    PANEL.hidden = false;
  }

  function closeSheet() {
    PANEL.classList.remove("archive-sheet-open");
  }

  document.addEventListener("touchstart", function (e) {
    const touch = e.touches[0];
    if (touch.clientY < 50 && !PANEL.classList.contains("archive-sheet-open")) {
      startY = touch.clientY;
    }
    if (PANEL.contains(e.target)) {
      const rect = PANEL.getBoundingClientRect();
      if (touch.clientY - rect.top < 40) {
        isDraggingPanel = true;
        panelStartY = touch.clientY;
      }
    }
  }, { passive: true });

  document.addEventListener("touchmove", function (e) {
    const touch = e.touches[0];
    if (!PANEL.classList.contains("archive-sheet-open") && startY > 0 && touch.clientY - startY > 100) {
      openSheet();
      startY = 0;
    }
    if (isDraggingPanel && PANEL.classList.contains("archive-sheet-open")) {
      if (panelStartY - touch.clientY > 50) {
        closeSheet();
        isDraggingPanel = false;
      }
    }
  }, { passive: true });

  document.addEventListener("touchend", function () {
    startY = 0;
    isDraggingPanel = false;
  });

  // Tap outside to close
  document.addEventListener("click", function (e) {
    if (PANEL.classList.contains("archive-sheet-open") && !PANEL.contains(e.target) && e.target !== TOGGLE) {
      closeSheet();
    }
  });
})();
