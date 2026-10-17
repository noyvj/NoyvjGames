// R4-THMO-7: one-region focus mode for phones. The buttons (All, A, B, C) only show under 600px
// (style.css). "All" is the normal page. A hides the Region B/C comparison; B or C show just that
// region's card instead of Region A's status and investments. The choice is a per-device setting
// kept in localStorage, never in a save, and nothing in the game changes.
(function () {
  "use strict";
  var KEY = "thaw-focus-region";
  var VALID = ["all", "a", "b", "c"];
  var game = document.getElementById("game");
  var buttons = Array.prototype.slice.call(document.querySelectorAll(".focus-dot"));
  if (!game || !buttons.length) return;

  function read() {
    try {
      var value = window.localStorage.getItem(KEY);
      return VALID.indexOf(value) >= 0 ? value : "all";
    } catch (e) {
      return "all";
    }
  }

  function write(value) {
    try {
      window.localStorage.setItem(KEY, value);
    } catch (e) {
      // The choice just will not survive a reload.
    }
  }

  function setFocus(region) {
    if (VALID.indexOf(region) < 0) region = "all";
    if (region === "all") {
      game.removeAttribute("data-focus");
    } else {
      game.setAttribute("data-focus", region);
    }
    buttons.forEach(function (button) {
      var on = button.id === "focus-dot-" + region;
      button.classList.toggle("focus-dot--active", on);
      button.setAttribute("aria-pressed", on ? "true" : "false");
    });
  }

  buttons.forEach(function (button) {
    button.addEventListener("click", function () {
      var region = button.id.replace("focus-dot-", "");
      setFocus(region);
      write(region);
    });
  });

  setFocus(read());
})();
