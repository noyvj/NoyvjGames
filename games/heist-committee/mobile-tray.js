(function () {
  "use strict";
  var TRAY_ID = "mobile-tray";
  var KEY = "heist-mobile-tray-armed";

  /**
   * @param {Array<{id: string, name: string, odds?: string, oddsLabel?: string}>} actions
   * @param {function(string): void} onSelect Called when the player picks an action.
   */
  function init(actions, onSelect) {
    if (document.getElementById(TRAY_ID)) return;
    var container = document.createElement("div");
    container.id = TRAY_ID;
    container.setAttribute("role", "toolbar");
    container.setAttribute("aria-label", "Actions");

    var armedId = localStorage.getItem(KEY);
    actions.forEach(function (action) {
      var item = document.createElement("button");
      item.className = "tray-carousel-item";
      item.setAttribute("role", "radio");
      item.setAttribute("aria-pressed", action.id === armedId ? "true" : "false");
      item.dataset.actionId = action.id;

      var nameEl = document.createElement("div");
      nameEl.className = "t-name";
      nameEl.textContent = action.name;

      var oddsVal = (action.odds || "none").toLowerCase();
      var oddsEl = document.createElement("div");
      oddsEl.className = "t-odds " + oddsVal;
      oddsEl.textContent = action.oddsLabel || oddsVal.charAt(0).toUpperCase() + oddsVal.slice(1);

      item.appendChild(nameEl);
      item.appendChild(oddsEl);

      item.addEventListener("click", function () {
        var prev = container.querySelector("[aria-pressed='true']");
        if (prev) prev.setAttribute("aria-pressed", "false");
        item.setAttribute("aria-pressed", "true");
        localStorage.setItem(KEY, action.id);
        if (onSelect) onSelect(action.id);
      });

      container.appendChild(item);
    });

    document.body.appendChild(container);
  }

  window.MobileTray = { init: init };
})();
