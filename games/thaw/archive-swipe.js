// R4-THMO-10: on phones the Climate archive is a bottom sheet. Pull down with one finger at the very top of the page, or
// press the usual "Climate archive" button, and the sheet slides up; pull it down, press Close, tap outside it or press Esc
// to put it away. The game (game.py) still owns whether the archive is open: this file only ever presses its own toggle
// button, so the open state, the button text and the data are the game's. Settings > "No pull down to open the Climate
// archive" turns the gesture off (the button still works). Reduced motion and lite mode skip the slide (style.css).
(function () {
  "use strict";
  var panel = document.getElementById("archive-panel");
  var toggle = document.getElementById("archive-toggle-button");
  var closeButton = document.getElementById("archive-sheet-close");
  if (!panel || !toggle || !closeButton) return;
  var root = document.documentElement;
  var phone = window.matchMedia("(max-width: 600px)");
  var home = document.createComment("archive-panel");   // where the panel lives on a wide screen

  function isPhone() {
    return phone.matches && root.getAttribute("data-layout") !== "pc";
  }

  function isOpen() {
    return !panel.hidden;
  }

  // A sheet has to be fixed to the screen, which a child of the blurred #game card cannot be: so on a phone the panel
  // lives directly under <body>, and goes back under its button on a wide screen.
  function place() {
    if (isPhone() && panel.parentNode !== document.body) {
      panel.parentNode.insertBefore(home, panel);
      document.body.appendChild(panel);
    } else if (!isPhone() && panel.parentNode === document.body && home.parentNode) {
      home.parentNode.insertBefore(panel, home);
      home.parentNode.removeChild(home);
    }
  }

  function openSheet() {
    if (!isOpen()) toggle.click();
  }

  function closeSheet() {
    if (isOpen()) toggle.click();
  }

  closeButton.addEventListener("click", closeSheet);

  // Tap outside the sheet to put it away (the toggle button handles itself).
  document.addEventListener("click", function (event) {
    if (!isPhone() || !isOpen() || panel.contains(event.target) || toggle.contains(event.target)) return;
    closeSheet();
  });

  // Keep focus sensible: into the sheet when it opens on a phone, back to the button when it closes.
  new MutationObserver(function () {
    if (!isPhone()) return;
    if (isOpen()) {
      panel.scrollTop = 0;
      try { closeButton.focus({ preventScroll: true }); } catch (e) { /* focus is a nicety */ }
    } else if (panel.contains(document.activeElement)) {
      toggle.focus({ preventScroll: true });
    }
  }).observe(panel, { attributes: true, attributeFilter: ["hidden"] });

  // --- gestures: pull down on the page to open; pull the open sheet down to close -------------------------------
  var PULL = 90;           // px of downward travel that counts as a pull
  var startX = 0, startY = 0, mode = "";   // mode: "page" (maybe opening), "sheet" (maybe closing) or ""

  function pageAtTop() {
    var scroller = document.scrollingElement || document.documentElement;
    return scroller.scrollTop <= 0;
  }

  function interactive(target) {
    return Boolean(target && target.closest && target.closest("input, select, textarea, button, a, summary, [role='slider'], [data-pts], .mobile-invest-track"));
  }

  document.addEventListener("touchstart", function (event) {
    mode = "";
    if (!isPhone() || event.touches.length !== 1) return;
    var touch = event.touches[0];
    startX = touch.clientX;
    startY = touch.clientY;
    if (isOpen() && panel.contains(event.target)) {
      if (panel.scrollTop <= 0) mode = "sheet";
    } else if (!isOpen() && root.getAttribute("data-no-pull-archive") !== "true" && pageAtTop() && !interactive(event.target)) {
      mode = "page";
    }
  }, { passive: true });

  document.addEventListener("touchmove", function (event) {
    if (!mode || event.touches.length !== 1) return;
    var touch = event.touches[0];
    var dy = touch.clientY - startY;
    var dx = Math.abs(touch.clientX - startX);
    if (dy < -10 || dx > dy) {
      if (dx > 24 || dy < -10) mode = "";    // sideways or upwards: an ordinary scroll or swipe, not a pull
      return;
    }
    if (dy >= PULL && dy > dx * 1.5) {
      if (mode === "page" && pageAtTop()) openSheet();
      else if (mode === "sheet") closeSheet();
      mode = "";
    }
  }, { passive: true });

  ["touchend", "touchcancel"].forEach(function (name) {
    document.addEventListener(name, function () { mode = ""; }, { passive: true });
  });

  phone.addEventListener("change", place);
  new MutationObserver(place).observe(root, { attributes: true, attributeFilter: ["data-layout"] });
  place();
})();
