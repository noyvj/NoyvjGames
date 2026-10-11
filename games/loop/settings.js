/*
 * Loop — settings panel: text-scale + reduced-motion toggle.
 *
 * Deliberately independent of Pyodide entirely, same discipline Continuum's
 * Phase 5 accessibility.js established (see games/continuum/CLAUDE.md's
 * Phase 5 build notes) and Aftermath/Herd/Thaw's own settings.js already
 * carried over -- this file has no Python dependency, so the panel works
 * even if game.py never boots, and it's wired up before game.py's own
 * <script> runs.
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

  const TEXT_SCALE_KEY = "loop-text-scale";
  const MOTION_KEY = "loop-reduced-motion";
  // H-16 / H-17 / H-18: three more browser-level display preferences, stored the same way.
  const CONTRAST_KEY = "loop-high-contrast";
  const DYSLEXIA_KEY = "loop-dyslexia-font";
  const FLOW_SPEED_KEY = "loop-flow-speed";
  const FLOW_SPEEDS = ["off", "slow", "normal", "fast"];
  const DEFAULT_FLOW_SPEED = "normal";
  // H-20: ask "Spend 120 of 140 funds?" when one purchase takes more than this percent of the funds (0 = never).
  const CONFIRM_KEY = "loop-confirm-threshold";
  const CONFIRM_CHOICES = ["0", "50", "75", "90"];
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

  function readFlag(key) {
    try {
      return window.localStorage.getItem(key) === "true";
    } catch (e) {
      return false;
    }
  }

  function writeStored(key, value) {
    try {
      window.localStorage.setItem(key, String(value));
    } catch (e) {
      // Losing persistence is not worth breaking the control.
    }
  }

  function applyContrast(on) {
    document.documentElement.setAttribute("data-high-contrast", on ? "true" : "false");
    writeStored(CONTRAST_KEY, on);
    return on;
  }

  function applyDyslexia(on) {
    document.documentElement.setAttribute("data-dyslexia-font", on ? "true" : "false");
    writeStored(DYSLEXIA_KEY, on);
    return on;
  }

  function readFlowSpeed() {
    try {
      const raw = window.localStorage.getItem(FLOW_SPEED_KEY);
      if (FLOW_SPEEDS.indexOf(raw) !== -1) return raw;
    } catch (e) {
      // fall through to the default
    }
    return DEFAULT_FLOW_SPEED;
  }

  function applyFlowSpeed(speed) {
    const value = FLOW_SPEEDS.indexOf(speed) !== -1 ? speed : DEFAULT_FLOW_SPEED;
    document.documentElement.setAttribute("data-flow-speed", value);
    writeStored(FLOW_SPEED_KEY, value);
    FLOW_SPEEDS.forEach(function (name) {
      const button = document.getElementById("flow-speed-" + name + "-button");
      if (button) button.setAttribute("aria-pressed", name === value ? "true" : "false");
    });
    return value;
  }

  // GH-13 / GH-16 / H-19 / GH-29: four more browser-level display preferences. `fallback` is the
  // value when nothing is stored, so purchase effects and cracks default ON, shapes and haptics OFF.
  const TOGGLES = [
    { key: "loop-effects", attr: "data-effects", box: "effects-checkbox", fallback: true, on: "on", off: "off" },
    { key: "loop-cracks", attr: "data-cracks", box: "cracks-checkbox", fallback: true, on: "on", off: "off" },
    { key: "loop-particle-shapes", attr: "data-particle-shapes", box: "particle-shapes-checkbox", fallback: false, on: "on", off: "off" },
    { key: "loop-haptics", attr: "data-haptics", box: "haptics-checkbox", fallback: false, on: "on", off: "off" },
  ];

  function readToggle(toggle) {
    try {
      const raw = window.localStorage.getItem(toggle.key);
      if (raw === "true") return true;
      if (raw === "false") return false;
    } catch (e) {
      // fall through to the default
    }
    return toggle.fallback;
  }

  function applyToggle(toggle, on) {
    document.documentElement.setAttribute(toggle.attr, on ? toggle.on : toggle.off);
    writeStored(toggle.key, on);
    const box = document.getElementById(toggle.box);
    if (box) box.checked = on;
    return on;
  }

  function isOn(attr) {
    return document.documentElement.getAttribute(attr) === "on";
  }

  // What game.py asks: are purchase effects wanted right now (switched on and not under reduced motion)?
  function effectsOn() {
    const reduced = document.documentElement.getAttribute("data-reduced-motion") === "true"
      || (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
    return isOn("data-effects") && !reduced;
  }

  // GH-29: a short vibration where the browser allows it and the player opted in.
  function haptic(pattern) {
    try {
      if (isOn("data-haptics") && navigator.vibrate) navigator.vibrate(pattern);
    } catch (e) {
      // not allowed here: nothing to do
    }
  }

  function readConfirmThreshold() {
    try {
      const raw = window.localStorage.getItem(CONFIRM_KEY);
      if (CONFIRM_CHOICES.indexOf(raw) !== -1) return parseInt(raw, 10);
    } catch (e) {
      // fall through to "never"
    }
    return 0;
  }

  function applyConfirmThreshold(value) {
    const text = CONFIRM_CHOICES.indexOf(String(value)) !== -1 ? String(value) : "0";
    writeStored(CONFIRM_KEY, text);
    const select = document.getElementById("confirm-threshold-select");
    if (select) select.value = text;
    return parseInt(text, 10);
  }

  // H-21: every fold-out with an id remembers whether it was left open, and (Classic layout only) the main
  // panels get a chevron that collapses them. Browser preferences, kept in localStorage, never in a save.
  const PANEL_PREFIX = "loop-panel-open:";
  const COLLAPSE_PREFIX = "loop-panel-collapsed:";
  const CHEVRON_PANELS = [
    ["chain-flow-section", "The chain"],
    ["status", "Dashboard"],
    ["circularity", "Investments"],
    ["trade-network", "Trade network"],
    ["pool-section", "Regional pool"],
  ];

  function storedFlag(key) {
    try {
      const raw = window.localStorage.getItem(key);
      if (raw === "1") return true;
      if (raw === "0") return false;
    } catch (e) {
      // no storage: the panel keeps its markup default
    }
    return null;
  }

  function rememberFoldouts() {
    document.querySelectorAll("details[id]").forEach(function (details) {
      const saved = storedFlag(PANEL_PREFIX + details.id);
      if (saved !== null) details.open = saved;
      details.addEventListener("toggle", function () {
        writeStored(PANEL_PREFIX + details.id, details.open ? "1" : "0");
      });
    });
  }

  function addChevrons() {
    if (document.documentElement.getAttribute("data-layout") === "pc") return;
    CHEVRON_PANELS.forEach(function (entry) {
      const section = document.getElementById(entry[0]);
      if (!section || section.querySelector(":scope > .panel-chevron")) return;
      const button = document.createElement("button");
      button.type = "button";
      button.className = "panel-chevron";
      button.setAttribute("aria-controls", entry[0]);
      const icon = document.createElement("span");
      icon.className = "panel-chevron-icon";
      icon.setAttribute("aria-hidden", "true");
      const label = document.createElement("span");
      label.className = "panel-chevron-label";
      label.textContent = entry[1];
      button.appendChild(icon);
      button.appendChild(label);
      function paint(collapsed) {
        section.classList.toggle("is-collapsed", collapsed);
        button.setAttribute("aria-expanded", collapsed ? "false" : "true");
        button.setAttribute("aria-label", (collapsed ? "Expand " : "Collapse ") + entry[1]);
        icon.textContent = collapsed ? "\u25B8" : "\u25BE";
      }
      paint(storedFlag(COLLAPSE_PREFIX + entry[0]) === true);
      button.addEventListener("click", function () {
        const collapsed = !section.classList.contains("is-collapsed");
        paint(collapsed);
        writeStored(COLLAPSE_PREFIX + entry[0], collapsed ? "1" : "0");
      });
      section.insertBefore(button, section.firstChild);
    });
  }

  function init() {
    rememberFoldouts();
    addChevrons();
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

    const contrastCheckbox = document.getElementById("high-contrast-checkbox");
    const dyslexiaCheckbox = document.getElementById("dyslexia-font-checkbox");
    applyContrast(readFlag(CONTRAST_KEY));
    applyDyslexia(readFlag(DYSLEXIA_KEY));
    applyFlowSpeed(readFlowSpeed());
    if (contrastCheckbox) {
      contrastCheckbox.checked = readFlag(CONTRAST_KEY);
      contrastCheckbox.addEventListener("change", function () {
        applyContrast(contrastCheckbox.checked);
      });
    }
    if (dyslexiaCheckbox) {
      dyslexiaCheckbox.checked = readFlag(DYSLEXIA_KEY);
      dyslexiaCheckbox.addEventListener("change", function () {
        applyDyslexia(dyslexiaCheckbox.checked);
      });
    }
    FLOW_SPEEDS.forEach(function (name) {
      const button = document.getElementById("flow-speed-" + name + "-button");
      if (button) {
        button.addEventListener("click", function () {
          applyFlowSpeed(name);
        });
      }
    });

    TOGGLES.forEach(function (toggle) {
      applyToggle(toggle, readToggle(toggle));
      const box = document.getElementById(toggle.box);
      if (box) {
        box.addEventListener("change", function () {
          applyToggle(toggle, box.checked);
        });
      }
    });

    const confirmSelect = document.getElementById("confirm-threshold-select");
    if (confirmSelect) {
      confirmSelect.value = String(readConfirmThreshold());
      confirmSelect.addEventListener("change", function () {
        applyConfirmThreshold(confirmSelect.value);
      });
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
        applyContrast(false);
        applyDyslexia(false);
        applyFlowSpeed(DEFAULT_FLOW_SPEED);
        applyConfirmThreshold(0);
        TOGGLES.forEach(function (toggle) {
          applyToggle(toggle, toggle.fallback);
        });
        if (contrastCheckbox) contrastCheckbox.checked = false;
        if (dyslexiaCheckbox) dyslexiaCheckbox.checked = false;
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  window.LoopSettings = {
    applyScale: applyScale,
    applyMotion: applyMotion,
    applyContrast: applyContrast,
    applyDyslexia: applyDyslexia,
    applyFlowSpeed: applyFlowSpeed,
    applyConfirmThreshold: applyConfirmThreshold,
    confirmThreshold: readConfirmThreshold,
    effectsOn: effectsOn,
    haptic: haptic,
    MIN_SCALE: MIN_SCALE,
    MAX_SCALE: MAX_SCALE,
  };
})();
