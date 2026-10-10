/*
 * Herd — settings panel: text-scale + reduced-motion toggle.
 *
 * Deliberately independent of Pyodide entirely, same discipline Continuum's
 * Phase 5 accessibility.js established (see games/continuum/CLAUDE.md's
 * Phase 5 build notes) and Aftermath's own settings.js already carried
 * over -- this file has no Python dependency, so the panel works even if
 * game.py never boots, and it's wired up before game.py's own <script>
 * runs.
 *
 * Consolidates text-scale (A-/A/A+, same clamp/step shape as Continuum's
 * control) and a reduced-motion checkbox into one panel, per
 * planning/TODO.md's "per-game settings panel" site-wide goal (origin A9).
 * Deliberately NO sound toggle -- this hub has no audio system built
 * anywhere yet (see planning/LATER.md's "what can you actually do with
 * audio" standing question), so a sound control here would control
 * nothing real.
 *
 * Both settings are browser-level UI preferences, not game state --
 * persisted to localStorage so they survive a reload, but deliberately
 * never touching get_state()/load_state(), since a save code is meant to
 * be portable across devices/browsers and a local browser's accessibility
 * preference shouldn't silently override another device's.
 */
(function () {
  "use strict";

  const TEXT_SCALE_KEY = "herd-text-scale";
  const MOTION_KEY = "herd-reduced-motion";
  const MIN_SCALE = 0.85;
  const MAX_SCALE = 1.5;
  const STEP = 0.1;
  const DEFAULT_SCALE = 1.0;

  function readStoredScale() {
    try {
      const raw = window.localStorage.getItem(TEXT_SCALE_KEY);
      const value = parseFloat(raw);
      if (!isNaN(value) && value >= MIN_SCALE && value <= MAX_SCALE) {
        return value;
      }
    } catch (e) {
      // Storage can throw in a locked-down/private-browsing context --
      // fall back to the default rather than failing the whole page.
    }
    return DEFAULT_SCALE;
  }

  function writeStoredScale(value) {
    try {
      window.localStorage.setItem(TEXT_SCALE_KEY, String(value));
    } catch (e) {
      // Losing persistence isn't worth breaking the control for this load.
    }
  }

  function applyScale(value) {
    const clamped = Math.max(MIN_SCALE, Math.min(MAX_SCALE, value));
    document.documentElement.style.setProperty("--text-scale", clamped);
    document.documentElement.setAttribute("data-text-scale", clamped.toFixed(2));
    writeStoredScale(clamped);
    return clamped;
  }

  function readStoredMotion() {
    try {
      return window.localStorage.getItem(MOTION_KEY) === "true";
    } catch (e) {
      return false;
    }
  }

  function writeStoredMotion(value) {
    try {
      window.localStorage.setItem(MOTION_KEY, String(value));
    } catch (e) {
      // Same as above.
    }
  }

  function applyMotion(reduced) {
    document.documentElement.setAttribute("data-reduced-motion", reduced ? "true" : "false");
    writeStoredMotion(reduced);
    return reduced;
  }

  // F-15 / F-14: extra display preferences, each a plain on/off stored in localStorage and
  // mirrored as a data attribute on <html> that style.css reads. Browser-level, never in a save.
  const DISPLAY_PREFS = [
    { key: "herd-high-contrast", attr: "data-high-contrast", checkbox: "high-contrast-checkbox" },
    { key: "herd-dyslexia-font", attr: "data-dyslexia-font", checkbox: "dyslexia-font-checkbox" },
    { key: "herd-hatch-patterns", attr: "data-hatch-patterns", checkbox: "hatch-patterns-checkbox" },
  ];

  function readPref(key) {
    try {
      return window.localStorage.getItem(key) === "true";
    } catch (e) {
      return false;
    }
  }

  function applyPref(pref, on) {
    document.documentElement.setAttribute(pref.attr, on ? "true" : "false");
    try {
      window.localStorage.setItem(pref.key, String(on));
    } catch (e) {
      // Losing persistence is fine; the toggle still works for this page load.
    }
    return on;
  }

  function initDisplayPrefs() {
    DISPLAY_PREFS.forEach(function (pref) {
      const on = applyPref(pref, readPref(pref.key));
      const box = document.getElementById(pref.checkbox);
      if (!box) return;
      box.checked = on;
      box.addEventListener("change", function () {
        applyPref(pref, box.checked);
      });
    });
  }

  function resetDisplayPrefs() {
    DISPLAY_PREFS.forEach(function (pref) {
      applyPref(pref, false);
      const box = document.getElementById(pref.checkbox);
      if (box) box.checked = false;
    });
  }

  // F-10: keyboard play. Up/Down (and Home/End) move between the buy buttons, Left/Right moves
  // inside the x1 / x5 / Max stepper, and the How to Play panel ends with a plain cheat sheet.
  // Disabled buttons are skipped because the browser cannot focus them; Tab still reaches
  // everything in page order, so the arrows are a shortcut, never the only way.
  const LEVER_SELECTOR = [
    "#grow-herd-button", "#feed-invest-button", "#caps-invest-button", "#capture-invest-button",
    "#plant-pivot-invest-button", "#genetics-invest-button", "#supply-chain-invest-button",
    "#poultry-grow-button", "#litter-invest-button", "#biofilter-invest-button",
    "#satellite-open-button", "#satellite-grow-button", "#satellite-retrofit-button",
  ].join(",");
  const STEPPER_SELECTOR = "#bulk-stepper button";

  function usable(el) {
    return !el.disabled && !el.hidden && el.getClientRects().length > 0;
  }

  function moveFocus(list, current, key) {
    const items = list.filter(usable);
    if (!items.length) return false;
    const at = items.indexOf(current);
    let next;
    if (key === "Home") next = items[0];
    else if (key === "End") next = items[items.length - 1];
    else if (key === "ArrowDown" || key === "ArrowRight") next = items[(at + 1) % items.length];
    else next = items[(at - 1 + items.length) % items.length];
    next.focus();
    return true;
  }

  function onLeverKey(event) {
    if (event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey) return;
    const target = event.target;
    if (!target || target.nodeType !== 1) return;
    const key = event.key;
    if (target.matches && target.matches(STEPPER_SELECTOR)) {
      if (["ArrowLeft", "ArrowRight", "Home", "End"].indexOf(key) === -1) return;
      const stepper = Array.prototype.slice.call(document.querySelectorAll(STEPPER_SELECTOR));
      if (moveFocus(stepper, target, key)) event.preventDefault();
      return;
    }
    if (target.matches && target.matches(LEVER_SELECTOR)) {
      if (["ArrowUp", "ArrowDown", "Home", "End"].indexOf(key) === -1) return;
      const levers = Array.prototype.slice.call(document.querySelectorAll(LEVER_SELECTOR));
      if (moveFocus(levers, target, key)) event.preventDefault();
    }
  }

  const CHEAT_SHEET_ITEMS = [
    ["Tab / Shift + Tab", "move to the next or previous button; Enter or Space presses it"],
    ["Up / Down arrow", "on a buy button (Grow Herd, Feed Additives, Herd Caps, ...): move to the next or previous buy button"],
    ["Home / End", "on a buy button: jump to the first or last one"],
    ["Left / Right arrow", "on x1, x5 or Max: choose how many units each purchase buys"],
    ["?", "show or hide the list of shortcuts"],
    ["Esc", "close the panel that is open"],
  ];

  function buildCheatSheet() {
    const box = document.createElement("div");
    box.className = "howto-keys";
    const heading = document.createElement("h3");
    heading.textContent = "Keyboard play";
    box.appendChild(heading);
    const list = document.createElement("ul");
    CHEAT_SHEET_ITEMS.forEach(function (item) {
      const li = document.createElement("li");
      const kbd = document.createElement("kbd");
      kbd.textContent = item[0];
      li.appendChild(kbd);
      li.appendChild(document.createTextNode(" " + item[1]));
      list.appendChild(li);
    });
    box.appendChild(list);
    const note = document.createElement("p");
    note.textContent = "A screen reader reads out the result of each round after you press Advance Round.";
    box.appendChild(note);
    return box;
  }

  function initKeyboardPlay() {
    document.addEventListener("keydown", onLeverKey);
    const howto = document.getElementById("howto-panel");
    if (!howto) return;
    function ensure() {
      if (howto.querySelector(":scope > .howto-keys")) return;
      howto.appendChild(buildCheatSheet());
    }
    ensure();
    new MutationObserver(ensure).observe(howto, { childList: true });
  }

  function init() {
    initDisplayPrefs();
    initKeyboardPlay();
    let scale = readStoredScale();
    applyScale(scale);
    let reduced = readStoredMotion();
    applyMotion(reduced);

    const panel = document.getElementById("settings-panel");
    const toggleButton = document.getElementById("settings-toggle-button");
    const decreaseButton = document.getElementById("text-size-decrease-button");
    const increaseButton = document.getElementById("text-size-increase-button");
    const resetButton = document.getElementById("text-size-reset-button");
    const motionCheckbox = document.getElementById("reduced-motion-checkbox");

    if (motionCheckbox) {
      motionCheckbox.checked = reduced;
    }

    if (toggleButton && panel) {
      toggleButton.addEventListener("click", function () {
        panel.hidden = !panel.hidden;
      });
    }
    if (decreaseButton) {
      decreaseButton.addEventListener("click", function () {
        scale = applyScale(scale - STEP);
      });
    }
    if (increaseButton) {
      increaseButton.addEventListener("click", function () {
        scale = applyScale(scale + STEP);
      });
    }
    if (resetButton) {
      resetButton.addEventListener("click", function () {
        scale = applyScale(DEFAULT_SCALE);
      });
    }
    if (motionCheckbox) {
      motionCheckbox.addEventListener("change", function () {
        reduced = applyMotion(motionCheckbox.checked);
      });
    }

    const settingsResetButton = document.getElementById("settings-reset-button");
    if (settingsResetButton) {
      settingsResetButton.addEventListener("click", function () {
        scale = applyScale(DEFAULT_SCALE);
        reduced = applyMotion(false);
        if (motionCheckbox) {
          motionCheckbox.checked = false;
        }
        resetDisplayPrefs();
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  window.HerdSettings = {
    applyScale: applyScale, applyMotion: applyMotion, MIN_SCALE: MIN_SCALE, MAX_SCALE: MAX_SCALE,
    cheatSheetItems: CHEAT_SHEET_ITEMS,
  };
})();
