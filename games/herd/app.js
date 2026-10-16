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

/* R4-HEMO-4: Mobile methane thermometer */
(function() {
  var MAX_METHANE = 300;
  var thermo = document.getElementById("methane-thermometer");
  var fill = document.getElementById("methane-thermo-fill");
  var label = document.getElementById("methane-thermo-label");
  var detail = document.getElementById("methane-thermo-detail");
  var pressureEl = document.getElementById("methane-thermo-pressure");

  if (!thermo) return;

  function updateThermo() {
    var text = document.getElementById("methane-display")?.textContent || "0";
    var num = parseFloat(text.replace(/[^0-9.-]/g, ""));
    if (isNaN(num)) num = 0;
    
    thermo.hidden = num <= 0;
    label.textContent = Math.round(num);
    detail.textContent = "Methane: " + Math.round(num);
    
    var pct = Math.min(100, (num / MAX_METHANE) * 100);
    fill.style.height = pct + "%";

    var pressText = document.getElementById("pressure-display")?.textContent || "0%";
    var pressNum = parseFloat(pressText.replace(/[^0-9.-]/g, ""));
    if (!isNaN(pressNum)) {
      pressureEl.textContent = "Pressure: " + Math.round(pressNum) + "%";
    }
  }

  thermo.addEventListener("click", function() {
    thermo.classList.toggle("open");
  });

  var observer = new MutationObserver(updateThermo);
  observer.observe(document.getElementById("methane-display"), { childList: true, characterData: true, subtree: true });
  if (document.getElementById("pressure-display")) {
    observer.observe(document.getElementById("pressure-display"), { childList: true, characterData: true, subtree: true });
  }

  updateThermo();
})();
