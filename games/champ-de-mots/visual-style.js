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
 * "Chosen on first load" is read as: a sensible default (High-def, i.e.
 * exactly the game's pre-existing look) is applied automatically the first
 * time this file ever runs in a given browser, and a settings control lets
 * that choice be changed at any time afterward -- not a forced first-run
 * picker dialog, which would be one more thing standing between opening the
 * game and actually playing it.
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

  function applyStyle(value) {
    const style = STYLES.indexOf(value) !== -1 ? value : DEFAULT_STYLE;
    document.documentElement.setAttribute("data-visual-style", style);
    writeStoredStyle(style);
    updateButtons(style);
    return style;
  }

  function init() {
    let current = applyStyle(readStoredStyle());

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
    STYLES: STYLES,
    DEFAULT_STYLE: DEFAULT_STYLE,
  };
})();
