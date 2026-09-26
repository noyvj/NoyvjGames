/*
 * SOL — "hold to repeat" for the mining click and the Auto-Miner/Recycler
 * buy buttons (planning/TODO.md U11).
 *
 * Holding one of those buttons (mouse, touch, or Enter/Space) repeats its
 * click at a deliberately gentle pace: after a short initial pause, one
 * extra click every HOLD_INTERVAL_MS (4 a second). That is meant to spare
 * hands during a big buying/mining session without ever beating a player
 * who clicks manually (a quick manual clicker easily exceeds 4/s). A plain
 * tap is unchanged: one press, one click.
 *
 * Pure DOM, no Pyodide dependency, same discipline as settings.js: it
 * clicks the real buttons, so every cost/disabled/achievement rule inside
 * game.py still applies exactly as for a manual click. Browser-level
 * preference (a Settings checkbox, on by default), persisted to
 * localStorage, never part of the save code.
 */
(function () {
  "use strict";

  const STORAGE_KEY = "sol-hold-repeat";
  const HOLD_DELAY_MS = 450;
  const HOLD_INTERVAL_MS = 250;
  // Every world's mining button and its two buy buttons share these id suffixes.
  const SELECTOR = '[id$="click-button"], [id$="buy-generator-button"], [id$="buy-recycler-button"]';

  let enabled = true;
  let delayTimer = null;
  let repeatTimer = null;
  let heldButton = null;
  let repeated = false;
  let synthetic = false;

  function readEnabled() {
    try {
      return window.localStorage.getItem(STORAGE_KEY) !== "false";
    } catch (e) {
      return true;
    }
  }

  function writeEnabled(value) {
    try {
      window.localStorage.setItem(STORAGE_KEY, String(value));
    } catch (e) {
      // Losing persistence isn't worth breaking the control for this load.
    }
  }

  function stop() {
    if (delayTimer !== null) {
      window.clearTimeout(delayTimer);
      delayTimer = null;
    }
    if (repeatTimer !== null) {
      window.clearInterval(repeatTimer);
      repeatTimer = null;
    }
    heldButton = null;
  }

  function fire(button) {
    if (button.disabled || !document.body.contains(button)) {
      return;
    }
    repeated = true;
    synthetic = true;
    try {
      button.click();
    } finally {
      synthetic = false;
    }
  }

  function start(button) {
    stop();
    repeated = false;
    heldButton = button;
    delayTimer = window.setTimeout(function () {
      delayTimer = null;
      fire(button);
      repeatTimer = window.setInterval(function () {
        fire(button);
      }, HOLD_INTERVAL_MS);
    }, HOLD_DELAY_MS);
  }

  function targetButton(event) {
    return event.target && event.target.closest ? event.target.closest(SELECTOR) : null;
  }

  function init() {
    enabled = readEnabled();
    const checkbox = document.getElementById("hold-repeat-checkbox");
    if (checkbox) {
      checkbox.checked = enabled;
      checkbox.addEventListener("change", function () {
        enabled = checkbox.checked;
        writeEnabled(enabled);
        if (!enabled) {
          stop();
        }
      });
    }
    const resetButton = document.getElementById("settings-reset-button");
    if (resetButton) {
      resetButton.addEventListener("click", function () {
        enabled = true;
        writeEnabled(true);
        if (checkbox) {
          checkbox.checked = true;
        }
      });
    }

    document.addEventListener("pointerdown", function (event) {
      const button = targetButton(event);
      if (!enabled || !button || button.disabled || (event.button !== undefined && event.button !== 0)) {
        return;
      }
      start(button);
    });
    ["pointerup", "pointercancel", "pointerleave", "dragstart"].forEach(function (name) {
      document.addEventListener(name, function (event) {
        if (name === "pointerleave" && event.target !== heldButton) {
          return;
        }
        stop();
      }, true);
    });
    window.addEventListener("blur", stop);
    document.addEventListener("visibilitychange", stop);

    // Keyboard: Enter/Space held on a focused button. Native key-repeat on
    // Enter clicks far faster than the gentle pace above, so repeats are
    // swallowed and this file's own timer takes over instead.
    document.addEventListener("keydown", function (event) {
      if (event.key !== "Enter" && event.key !== " ") {
        return;
      }
      const button = targetButton(event);
      if (!enabled || !button || button.disabled) {
        return;
      }
      if (event.repeat) {
        event.preventDefault();
        return;
      }
      start(button);
    });
    document.addEventListener("keyup", function (event) {
      if (event.key === "Enter" || event.key === " ") {
        stop();
      }
    });

    // After a real hold, the release that ends it must not count as one
    // more click on top of the repeats (a tap with no hold is untouched).
    document.addEventListener("click", function (event) {
      if (synthetic || !repeated) {
        return;
      }
      if (targetButton(event)) {
        repeated = false;
        event.stopPropagation();
        event.preventDefault();
      }
    }, true);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  window.SolHoldRepeat = { HOLD_DELAY_MS: HOLD_DELAY_MS, HOLD_INTERVAL_MS: HOLD_INTERVAL_MS };
})();
