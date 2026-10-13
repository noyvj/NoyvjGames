(function () {
  "use strict";
  var HTML_EL = document.documentElement;
  var TOGGLE_BTN = null;
  var PANEL = null;
  var KEY = "dead-reckoning-mobile-layout";

  function init() {
    TOGGLE_BTN = document.getElementById("planner-toggle");
    PANEL = document.getElementById("planner-panel");
    if (!TOGGLE_BTN || !PANEL) return;

    // Restore user choice or default to landscape (floating)
    var saved = localStorage.getItem(KEY);
    if (saved === "table") {
      HTML_EL.setAttribute("data-layout", "table");
    } else {
      applyLandscape();
    }

    TOGGLE_BTN.addEventListener("click", function () {
      var isTable = HTML_EL.getAttribute("data-layout") === "table";
      if (isTable) {
        applyLandscape();
      } else {
        applyTable();
      }
    });

    window.addEventListener("orientationchange", handleOrientation, false);
    window.addEventListener("resize", handleResize, false);
  }

  function applyLandscape() {
    HTML_EL.removeAttribute("data-layout");
    localStorage.setItem(KEY, "landscape");
  }

  function applyTable() {
    HTML_EL.setAttribute("data-layout", "table");
    localStorage.setItem(KEY, "table");
  }

  function handleOrientation() {
    handleResize();
  }

  function handleResize() {
    if (window.innerWidth > 600) return;
    var isLandscape = window.matchMedia("(orientation: landscape)").matches;
    if (isLandscape) {
      applyLandscape();
    } else {
      // Only auto-switch to table on portrait if user hasn't explicitly chosen landscape
      if (localStorage.getItem(KEY) !== "landscape") {
        applyTable();
      }
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
