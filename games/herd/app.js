/* R4-HEMO-7: Calm barn mode toggle */
(function() {
  var STORAGE_KEY = "herd-calm-barn";
  var CALM_BARN_CLASS = "calm-barn-mode";

  function applyCalmBarn(enabled) {
    var gameEl = document.getElementById("game");
    if (gameEl) {
      gameEl.classList.toggle(CALM_BARN_CLASS, enabled);
    }
    localStorage.setItem(STORAGE_KEY, enabled ? "true" : "false");
  }

  function init() {
    var toggle = document.getElementById("calm-barn-toggle");
    if (!toggle) return;

    var saved = localStorage.getItem(STORAGE_KEY);
    var initialState = saved === "true";
    applyCalmBarn(initialState);

    toggle.addEventListener("click", function() {
      var gameEl = document.getElementById("game");
      var newState = !gameEl.classList.contains(CALM_BARN_CLASS);
      applyCalmBarn(newState);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
