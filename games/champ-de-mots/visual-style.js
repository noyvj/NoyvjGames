/*
 * Le Champ de Mots — visual style switcher.
 *
 * planning/TODO.md's "Big standalone features" list: a low-poly / text-based
 * / cartoon / high-def visual-style switcher, chosen on first load and
 * changeable in settings, desktop-only. Deliberately independent of Pyodide
 * entirely, same discipline games/aftermath/settings.js and Continuum's
 * Phase 5 accessibility.js already established for this hub: this file has
 * no Python dependency, so the control works even if game.py never boots,
 * and it's wired up before game.py's own <script> runs.
 *
 * This is a browser-level UI preference, not game state -- same category
 * this game's own ACCENT_SENSITIVE toggle and plot.last_variant already
 * established (see CLAUDE.md's Milestone 4/8 build notes): persisted to
 * localStorage so it survives a reload on this browser, but deliberately
 * never touching the save-code payload's own read/write functions, since a
 * save code is meant to be portable across devices/browsers and a local
 * browser's visual preference shouldn't silently override another device's.
 *
 * "Chosen on first load": when nothing is stored (and the viewport is
 * desktop-width) a small modal picker offers the four styles once, with a
 * Skip button that takes High-def; either way the answer is stored, so it
 * never reappears, and the Settings control changes it later. The page is
 * already styled High-def behind the dialog (applied but not persisted until
 * an answer), so nothing flashes. Narrow/mobile viewports skip the picker
 * (the switcher is desktop-only) and simply keep High-def.
 */
(function () {
  "use strict";

  const STORAGE_KEY = "champ-de-mots-visual-style";
  const STYLES = ["highdef", "lowpoly", "textbased", "cartoon"];
  const DEFAULT_STYLE = "highdef";

  function readStoredStyle() {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (STYLES.indexOf(raw) !== -1) {
        return raw;
      }
    } catch (e) {
      // Storage can throw in a locked-down/private-browsing context --
      // fall back to the default rather than failing the whole page.
    }
    return DEFAULT_STYLE;
  }

  function writeStoredStyle(value) {
    try {
      window.localStorage.setItem(STORAGE_KEY, value);
    } catch (e) {
      // Losing persistence isn't worth breaking the control for this load.
    }
  }

  function updateButtons(style) {
    STYLES.forEach(function (name) {
      const button = document.getElementById("visual-style-" + name + "-button");
      if (button) {
        button.classList.toggle("selected", name === style);
        button.setAttribute("aria-pressed", name === style ? "true" : "false");
      }
    });
  }

  function applyStyleUnsaved(value) {
    const style = STYLES.indexOf(value) !== -1 ? value : DEFAULT_STYLE;
    document.documentElement.setAttribute("data-visual-style", style);
    updateButtons(style);
    return style;
  }

  function applyStyle(value) {
    const style = STYLES.indexOf(value) !== -1 ? value : DEFAULT_STYLE;
    document.documentElement.setAttribute("data-visual-style", style);
    writeStoredStyle(style);
    updateButtons(style);
    return style;
  }

  const DESKTOP_QUERY = "(min-width: 641px)";
  let pickerOpen = false;
  const pickerCallbacks = [];

  function isDesktop() {
    try {
      return !window.matchMedia || window.matchMedia(DESKTOP_QUERY).matches;
    } catch (e) {
      return true;
    }
  }

  function hasStoredStyle() {
    try {
      return STYLES.indexOf(window.localStorage.getItem(STORAGE_KEY)) !== -1;
    } catch (e) {
      // Storage unreadable: treat as answered so a blocked-storage browser
      // isn't nagged on every load with a choice it can't remember.
      return true;
    }
  }

  function settlePicker() {
    pickerOpen = false;
    while (pickerCallbacks.length) {
      const callback = pickerCallbacks.shift();
      try {
        callback();
      } catch (e) {
        // A misbehaving callback must not block the others.
      }
    }
  }

  // Runs `callback` now if no picker is showing, else once it is dismissed.
  function whenPickerDone(callback) {
    if (pickerOpen) {
      pickerCallbacks.push(callback);
    } else {
      callback();
    }
  }

  function openPicker(onChoose) {
    const picker = document.getElementById("visual-style-picker");
    if (!picker) {
      return false;
    }
    const options = Array.prototype.slice.call(picker.querySelectorAll(".visual-style-picker-option"));
    const skip = document.getElementById("visual-style-picker-skip");
    const focusable = options.concat(skip ? [skip] : []);
    const previouslyFocused = document.activeElement;
    pickerOpen = true;
    picker.hidden = false;

    function close(style) {
      picker.hidden = true;
      picker.removeEventListener("keydown", onKeydown);
      onChoose(style);
      if (previouslyFocused && previouslyFocused.focus) {
        try {
          previouslyFocused.focus();
        } catch (e) {
          // Element may be gone; nothing to restore.
        }
      }
      settlePicker();
    }

    function onKeydown(event) {
      if (event.key === "Escape") {
        event.preventDefault();
        close(DEFAULT_STYLE);
      } else if (event.key === "Tab" && focusable.length) {
        // Keep Tab inside the dialog while it is modal.
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    }

    picker.addEventListener("keydown", onKeydown);
    options.forEach(function (button) {
      button.addEventListener("click", function () {
        close(button.getAttribute("data-style"));
      });
    });
    if (skip) {
      skip.addEventListener("click", function () {
        close(DEFAULT_STYLE);
      });
    }
    if (options[0]) {
      options[0].focus();
    }
    return true;
  }

  function init() {
    const firstRun = !hasStoredStyle();
    // Apply the stored style (or High-def) immediately. On a first run the
    // choice is only persisted once the picker is answered.
    let current = firstRun ? applyStyleUnsaved(DEFAULT_STYLE) : applyStyle(readStoredStyle());
    if (firstRun && isDesktop()) {
      openPicker(function (style) {
        current = applyStyle(style);
      });
    } else if (firstRun) {
      current = applyStyle(DEFAULT_STYLE);
    }

    const panel = document.getElementById("settings-panel");
    const toggleButton = document.getElementById("settings-toggle-button");
    if (toggleButton && panel) {
      toggleButton.addEventListener("click", function () {
        panel.hidden = !panel.hidden;
      });
    }

    STYLES.forEach(function (name) {
      const button = document.getElementById("visual-style-" + name + "-button");
      if (button) {
        button.addEventListener("click", function () {
          current = applyStyle(name);
        });
      }
    });

    const settingsResetButton = document.getElementById("settings-reset-button");
    if (settingsResetButton) {
      settingsResetButton.addEventListener("click", function () {
        current = applyStyle(DEFAULT_STYLE);
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  // Exposed for anything that wants to read/set the style programmatically
  // (and so a live check in the browser console can confirm behaviour).
  window.ChampDeMotsVisualStyle = {
    applyStyle: applyStyle,
    whenPickerDone: whenPickerDone,
    STYLES: STYLES,
    DEFAULT_STYLE: DEFAULT_STYLE,
  };
})();
