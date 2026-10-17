/* Herd, phone-view helpers (loaded at the end of index.html and pc.html, after the DOM exists).
   Plain JS, no Pyodide: each piece only reads text the game already writes into the page.
   - R4-HEMO-2: the thin top strip (round, funds, methane, and a word for how hard methane is pressing).
   - R4-HEMO-4: the methane thermometer on the screen edge; a tap opens "Why this number?" on methane.
   - R4-HEMO-7: Calm barn, a quiet bedtime view (a per-device setting in localStorage, never in a save).
   The layout of all three lives in style.css inside the max-width 600px block, so they do nothing on
   a wide screen. */
(function () {
  "use strict";

  function text(id) {
    var el = document.getElementById(id);
    return el ? el.textContent || "" : "";
  }

  // The first number in a readout such as "Methane: 12.5" or "Market/regulatory pressure: 8% income loss".
  function numberIn(value) {
    var match = /-?\d+(?:\.\d+)?/.exec(value);
    return match ? parseFloat(match[0]) : NaN;
  }

  function reducedMotion() {
    var root = document.documentElement;
    if (root.getAttribute("data-reduced-motion") === "true" || root.getAttribute("data-lite") === "true") return true;
    return !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  }

  function watch(ids, callback) {
    if (!window.MutationObserver) return;
    var observer = new MutationObserver(callback);
    ids.forEach(function (id) {
      var el = document.getElementById(id);
      if (el) observer.observe(el, { childList: true, characterData: true, subtree: true });
    });
  }

  // How hard methane is pressing on income: three bands (Stable, Rising, High), read from the
  // pressure line the game already writes. 25 percent is the same line the pressure nudge uses.
  function pressureBand(percent) {
    if (isNaN(percent) || percent < 10) return { name: "Stable", css: "band-low" };
    if (percent < 25) return { name: "Rising", css: "band-mid" };
    return { name: "High", css: "band-high" };
  }

  // ---- R4-HEMO-2: top strip ----
  function initTopStrip() {
    var round = document.getElementById("mobile-round");
    var funds = document.getElementById("mobile-funds");
    var methane = document.getElementById("mobile-methane");
    var label = document.getElementById("mobile-strip-label");
    if (!round || !funds || !methane || !label) return;
    function update() {
      round.textContent = text("round-display") || "Round 1";
      funds.textContent = text("funds-display") || "Funds: 300";
      methane.textContent = text("methane-display") || "Methane: 0";
      var band = pressureBand(numberIn(text("pressure-display")));
      if (label.textContent !== band.name) label.textContent = band.name;
      label.className = "mobile-strip-label " + band.css;
      label.title = "Methane pressure on income: " + band.name.toLowerCase();
    }
    watch(["round-display", "funds-display", "methane-display", "pressure-display"], update);
    update();
  }

  // ---- R4-HEMO-4: methane thermometer ----
  function initThermometer() {
    var thermo = document.getElementById("methane-thermometer");
    var fill = document.getElementById("methane-thermo-fill");
    if (!thermo || !fill) return;
    // Pressure stops growing at this income loss (the game's own cap), so the tube is full there.
    var FULL_AT_PERCENT = 80;
    function update() {
      var methane = numberIn(text("methane-display"));
      if (isNaN(methane)) methane = 0;
      var percent = numberIn(text("pressure-display"));
      if (isNaN(percent)) percent = 0;
      thermo.hidden = methane <= 0;
      fill.style.height = Math.max(0, Math.min(100, (percent / FULL_AT_PERCENT) * 100)) + "%";
      var words = "Methane " + Math.round(methane) + ", " + pressureBand(percent).name.toLowerCase() +
        " pressure on income. Open the methane breakdown";
      thermo.setAttribute("aria-label", words);
      thermo.title = words;
    }
    thermo.addEventListener("click", function () {
      var panel = document.getElementById("explain-panel");
      var button = document.getElementById("explain-methane-button");
      if (!panel) return;
      panel.open = true;
      if (button) button.click();
      panel.scrollIntoView({ block: "start", behavior: reducedMotion() ? "auto" : "smooth" });
    });
    watch(["methane-display", "pressure-display"], update);
    update();
  }

  // ---- R4-HEMO-7: Calm barn ----
  var CALM_KEY = "herd-calm-barn";

  function storedCalm() {
    try { return localStorage.getItem(CALM_KEY) === "true"; } catch (e) { return false; }
  }

  function storeCalm(on) {
    try {
      if (on) localStorage.setItem(CALM_KEY, "true"); else localStorage.removeItem(CALM_KEY);
    } catch (e) { /* private browsing: the mode just does not persist */ }
  }

  function initCalmBarn() {
    var game = document.getElementById("game");
    var toggle = document.getElementById("calm-barn-toggle");
    var exit = document.getElementById("calm-barn-exit");
    var word = document.getElementById("calm-barn-word");
    if (!game || !toggle) return;
    function setCalm(on) {
      game.classList.toggle("calm-barn-mode", on);
      toggle.setAttribute("aria-pressed", on ? "true" : "false");
      storeCalm(on);
      if (on) { updateWord(); if (exit) exit.focus(); } else { toggle.focus(); }
    }
    // One honest word: the farm is healthy while methane pressure on income is below 25 percent.
    function updateWord() {
      if (!word) return;
      var healthy = !(numberIn(text("pressure-display")) >= 25);
      var next = healthy ? "Healthy farm" : "Methane is rising";
      if (word.textContent !== next) word.textContent = next;
    }
    toggle.addEventListener("click", function () { setCalm(!game.classList.contains("calm-barn-mode")); });
    if (exit) exit.addEventListener("click", function () { setCalm(false); });
    // Settings > Reset to Default also leaves the calm barn.
    document.addEventListener("click", function (e) {
      if (e.target.closest && e.target.closest("#settings-reset-button") && game.classList.contains("calm-barn-mode")) {
        game.classList.remove("calm-barn-mode");
        toggle.setAttribute("aria-pressed", "false");
        storeCalm(false);
      }
    });
    watch(["pressure-display"], updateWord);
    updateWord();
    if (storedCalm()) {
      game.classList.add("calm-barn-mode");
      toggle.setAttribute("aria-pressed", "true");
    }
  }

  function init() {
    initTopStrip();
    initThermometer();
    initCalmBarn();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
})();
