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
 *
 * L2 (planning/TODO.md): two independent presets, one per CONTEXT ("farm"
 * while browsing the dashboard/farm grid, "review" while a review session
 * is open), each with its own localStorage key -- e.g. Cartoon for casual
 * farm browsing, Text-based (fewer distractions) for a focused review.
 * `setContext()` is called from game.py's render_review() (the one place
 * that knows whether #review-panel is actually showing) whenever the
 * context genuinely changes, and swaps which stored style is applied to
 * the page -- exactly the same "Python owns state, JS owns the one
 * external thing it needs" hook shape Continuum's `_notify_visual_layer()`
 * already established for this hub, just naming a mode instead of pushing
 * a data snapshot. A player who never sets a review-specific preset sees
 * no behavior change at all: reading an unset review key falls back to
 * whatever the farm key holds.
 */
(function () {
  "use strict";

  const CONTEXTS = ["farm", "review"];
  const STORAGE_KEYS = {
    farm: "champ-de-mots-visual-style",
    review: "champ-de-mots-visual-style-review",
  };
  const STYLES = ["highdef", "lowpoly", "textbased", "cartoon"];
  const DEFAULT_STYLE = "highdef";
  let currentContext = "farm";

  function readStoredStyle(context) {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEYS[context]);
      if (STYLES.indexOf(raw) !== -1) {
        return raw;
      }
    } catch (e) {
      // Storage can throw in a locked-down/private-browsing context --
      // fall back below rather than failing the whole page.
    }
    // An unset review preset inherits whatever the farm preset currently
    // is, so a returning player who never touches the new review row sees
    // the exact same single-style behavior this switcher always had.
    return context === "review" ? readStoredStyle("farm") : DEFAULT_STYLE;
  }

  function writeStoredStyle(context, value) {
    try {
      window.localStorage.setItem(STORAGE_KEYS[context], value);
    } catch (e) {
      // Losing persistence isn't worth breaking the control for this load.
    }
  }

  function updateButtons(context, style) {
    STYLES.forEach(function (name) {
      const button = document.getElementById("visual-style-" + name + "-" + context + "-button");
      if (button) {
        button.classList.toggle("selected", name === style);
        button.setAttribute("aria-pressed", name === style ? "true" : "false");
      }
    });
  }

  function applyStyleUnsaved(value) {
    const style = STYLES.indexOf(value) !== -1 ? value : DEFAULT_STYLE;
    document.documentElement.setAttribute("data-visual-style", style);
    return style;
  }

  // Sets the preset for one context (farm/review) and, if that context is
  // the one currently showing, applies it to the page immediately.
  function applyStyleForContext(context, value) {
    const style = STYLES.indexOf(value) !== -1 ? value : DEFAULT_STYLE;
    writeStoredStyle(context, style);
    updateButtons(context, style);
    if (context === currentContext) {
      document.documentElement.setAttribute("data-visual-style", style);
    }
    return style;
  }

  // Switches which context is live (farm/review) and paints its own
  // stored preset -- does not touch storage, since nothing was chosen.
  function applyContextStyle(context) {
    currentContext = context;
    const style = readStoredStyle(context);
    document.documentElement.setAttribute("data-visual-style", style);
    return style;
  }

  // Exposed for game.py's render_review() to call whenever
  // #review-panel's shown/hidden state actually changes.
  function setContext(context) {
    if (CONTEXTS.indexOf(context) === -1 || context === currentContext) {
      return;
    }
    applyContextStyle(context);
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
      // Only the farm key gates the first-run picker -- review's own
      // preset always has a valid fallback (readStoredStyle's own
      // recursion onto "farm"), so it never needs its own first-run ask.
      return STYLES.indexOf(window.localStorage.getItem(STORAGE_KEYS.farm)) !== -1;
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
    currentContext = "farm"; // the page always loads showing the farm first
    // Apply the stored style (or High-def) immediately. On a first run the
    // choice is only persisted once the picker is answered.
    if (firstRun) {
      applyStyleUnsaved(DEFAULT_STYLE);
      if (isDesktop()) {
        openPicker(function (style) {
          applyStyleForContext("farm", style);
        });
      } else {
        applyStyleForContext("farm", DEFAULT_STYLE);
      }
    } else {
      applyContextStyle("farm");
    }

    const panel = document.getElementById("settings-panel");
    const toggleButton = document.getElementById("settings-toggle-button");
    if (toggleButton && panel) {
      toggleButton.addEventListener("click", function () {
        panel.hidden = !panel.hidden;
      });
    }

    CONTEXTS.forEach(function (context) {
      STYLES.forEach(function (name) {
        const button = document.getElementById("visual-style-" + name + "-" + context + "-button");
        if (button) {
          button.addEventListener("click", function () {
            applyStyleForContext(context, name);
          });
        }
      });
      // Reflects each row's own saved preset in its button highlighting,
      // independent of which context happens to be live right now.
      updateButtons(context, readStoredStyle(context));
    });

    const settingsResetButton = document.getElementById("settings-reset-button");
    if (settingsResetButton) {
      settingsResetButton.addEventListener("click", function () {
        CONTEXTS.forEach(function (context) {
          applyStyleForContext(context, DEFAULT_STYLE);
        });
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  // Exposed for anything that wants to read/set the style programmatically
  // (and so a live check in the browser console can confirm behaviour), plus
  // setContext() for game.py's render_review() to call.
  window.ChampDeMotsVisualStyle = {
    applyStyle: function (value) {
      return applyStyleForContext("farm", value);
    },
    setContext: setContext,
    whenPickerDone: whenPickerDone,
    STYLES: STYLES,
    DEFAULT_STYLE: DEFAULT_STYLE,
  };
})();
