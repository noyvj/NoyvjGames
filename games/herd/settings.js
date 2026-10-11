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

  // F-18: "ask before a big purchase" threshold, a percentage of current funds (0 = never).
  // game.py reads the same localStorage key each time a purchase button is pressed.
  const CONFIRM_KEY = "herd-confirm-percent";
  const CONFIRM_CHOICES = ["0", "25", "50", "75"];

  function readConfirmChoice() {
    try {
      const raw = window.localStorage.getItem(CONFIRM_KEY);
      return CONFIRM_CHOICES.indexOf(raw) === -1 ? "0" : raw;
    } catch (e) {
      return "0";
    }
  }

  function writeConfirmChoice(value) {
    try {
      window.localStorage.setItem(CONFIRM_KEY, value);
    } catch (e) {
      // The choice still applies until the page is reloaded.
    }
  }

  function initConfirmThreshold() {
    const select = document.getElementById("confirm-threshold-select");
    if (!select) return;
    select.value = readConfirmChoice();
    select.addEventListener("change", function () {
      writeConfirmChoice(select.value);
    });
  }

  function resetConfirmThreshold() {
    writeConfirmChoice("0");
    const select = document.getElementById("confirm-threshold-select");
    if (select) select.value = "0";
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

  // F-29: plain-language glossary. The first mention of each hard word in the explainer text
  // (the "i" notes, the intro blurb, the How to Play steps) gets a dotted underline; hover, focus or
  // tap opens a short definition, and How to Play ends with the whole glossary. The words are found
  // in static text only, so the game's own live readouts are never rewritten.
  const GLOSSARY = [
    { key: "coupling", name: "Coupling ratio", pattern: /coupling ratio/i,
      text: "How much methane one herd unit gives off in a round. 1.00 is the starting level; every decoupling investment pushes it down." },
    { key: "decoupling", name: "Decoupling", pattern: /decoupl(?:ing|ed|e)\b/i,
      text: "Cutting the methane each animal gives off without shrinking the herd, so the farm can grow without its emissions growing at the same rate." },
    { key: "baseline", name: "Baseline farm (counterfactual)", pattern: /baseline farm|counterfactual|pure-growth/i,
      text: "An imaginary second farm with the same herd that never spent anything on decoupling. Comparing with it shows whether your spending paid off." },
    { key: "welfare", name: "Welfare", pattern: /welfare/i,
      text: "A 0 to 100 score for how well the animals are kept. Better feed, herd caps and breeding raise it, and above 50 it lifts income by up to 10%." },
    { key: "capture", name: "Capture systems", pattern: /capture systems?/i,
      text: "Equipment that traps methane from manure and barns. The first two units are used on the farm itself; extra units let you sell biogas." },
    { key: "pressure", name: "Pressure", pattern: /(?:market\/regulatory )?pressure/i,
      text: "Income lost to market and regulator pushback. It grows with all the methane you have ever added, never resets, and stops at 80%." },
    { key: "certification", name: "Sustainable certification", pattern: /(?:sustainable )?certif\w+/i,
      text: "A permanent +10% price premium, earned by holding a coupling ratio of 0.50 or lower for 5 rounds in a row." },
    { key: "equivalent", name: "Methane-equivalent", pattern: /methane-equivalent/i,
      text: "Poultry emissions are mostly other gases, so the game turns them into one methane-like number you can compare with cattle." },
  ];
  const GLOSSARY_SCOPE = ".info-toggle p, .context-blurb, #howto-panel .howto-step p";
  let glossaryPopover = null;
  let glossaryOwner = null;

  function glossaryEntry(key) {
    for (let i = 0; i < GLOSSARY.length; i++) if (GLOSSARY[i].key === key) return GLOSSARY[i];
    return null;
  }

  function markGlossaryTerms(container) {
    if (container.dataset.glossaryDone === "1") return;
    container.dataset.glossaryDone = "1";
    const nodes = [];
    const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) nodes.push(walker.currentNode);
    const used = {};
    nodes.forEach(function (node) {
      let current = node;
      GLOSSARY.forEach(function (entry) {
        if (used[entry.key] || !current || !current.parentNode) return;
        const match = entry.pattern.exec(current.nodeValue);
        if (!match) return;
        used[entry.key] = true;
        const after = current.splitText(match.index + match[0].length);
        const hit = current.splitText(match.index);
        const span = document.createElement("span");
        span.className = "glossary-term";
        span.setAttribute("tabindex", "0");
        span.setAttribute("role", "button");
        span.setAttribute("data-glossary", entry.key);
        span.setAttribute("aria-label", entry.name + ": " + entry.text);
        hit.parentNode.replaceChild(span, hit);
        span.appendChild(hit);
        current = after;
      });
    });
  }

  function scanGlossary() {
    document.querySelectorAll(GLOSSARY_SCOPE).forEach(markGlossaryTerms);
  }

  function hideGlossaryPopover() {
    if (glossaryPopover) glossaryPopover.hidden = true;
    glossaryOwner = null;
  }

  function showGlossaryPopover(term) {
    const entry = glossaryEntry(term.getAttribute("data-glossary"));
    if (!entry) return;
    if (!glossaryPopover) {
      glossaryPopover = document.createElement("div");
      glossaryPopover.id = "glossary-popover";
      glossaryPopover.setAttribute("role", "tooltip");
      glossaryPopover.hidden = true;
      document.body.appendChild(glossaryPopover);
    }
    glossaryPopover.textContent = "";
    const title = document.createElement("strong");
    title.textContent = entry.name;
    glossaryPopover.appendChild(title);
    glossaryPopover.appendChild(document.createElement("br"));
    glossaryPopover.appendChild(document.createTextNode(entry.text));
    glossaryPopover.hidden = false;
    glossaryOwner = term;
    const rect = term.getBoundingClientRect();
    const width = Math.min(280, window.innerWidth - 16);
    glossaryPopover.style.width = width + "px";
    const left = Math.max(8, Math.min(rect.left, window.innerWidth - width - 8));
    glossaryPopover.style.left = left + "px";
    const below = rect.bottom + 6;
    const height = glossaryPopover.offsetHeight;
    glossaryPopover.style.top = (below + height > window.innerHeight ? Math.max(8, rect.top - height - 6) : below) + "px";
  }

  function buildGlossaryBlock() {
    const box = document.createElement("div");
    box.className = "howto-glossary";
    const heading = document.createElement("h3");
    heading.textContent = "Glossary";
    box.appendChild(heading);
    const list = document.createElement("dl");
    GLOSSARY.forEach(function (entry) {
      const dt = document.createElement("dt");
      dt.textContent = entry.name;
      const dd = document.createElement("dd");
      dd.textContent = entry.text;
      list.appendChild(dt);
      list.appendChild(dd);
    });
    box.appendChild(list);
    return box;
  }

  function initGlossary() {
    scanGlossary();
    document.addEventListener("mouseover", function (event) {
      const term = event.target.closest && event.target.closest(".glossary-term");
      if (term) showGlossaryPopover(term);
    });
    document.addEventListener("mouseout", function (event) {
      const term = event.target.closest && event.target.closest(".glossary-term");
      if (term && term === glossaryOwner && document.activeElement !== term) hideGlossaryPopover();
    });
    document.addEventListener("focusin", function (event) {
      const term = event.target.closest && event.target.closest(".glossary-term");
      if (term) showGlossaryPopover(term);
    });
    document.addEventListener("focusout", function (event) {
      if (event.target.closest && event.target.closest(".glossary-term")) hideGlossaryPopover();
    });
    document.addEventListener("click", function (event) {
      const term = event.target.closest && event.target.closest(".glossary-term");
      if (term) {
        if (glossaryOwner === term && !glossaryPopover.hidden) hideGlossaryPopover();
        else showGlossaryPopover(term);
      } else {
        hideGlossaryPopover();
      }
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && glossaryPopover && !glossaryPopover.hidden) {
        hideGlossaryPopover();
        event.stopPropagation();
      }
    }, true);
    const howto = document.getElementById("howto-panel");
    if (howto) {
      new MutationObserver(function () {
        scanGlossary();
        if (!howto.querySelector(":scope > .howto-glossary")) howto.appendChild(buildGlossaryBlock());
      }).observe(howto, { childList: true });
      if (!howto.querySelector(":scope > .howto-glossary")) howto.appendChild(buildGlossaryBlock());
    }
  }

  // GF-14: a round celebration. After Advance Round game.py calls HerdFx.roundGain(earned, beat): the
  // income of the round counts up under the button, and a small confetti burst plays when the round
  // earned more than the one before. On by default, switched off in Settings (stored as "false" in
  // localStorage["herd-cha-ching"]). With reduced motion, lite mode or the OS reduced-motion setting
  // the number simply appears (no count-up, no confetti). Decorative only: the round result is already
  // read out by the polite live region, so this element is aria-hidden.
  const CHA_KEY = "herd-cha-ching";
  let chaTimer = null;

  function chaChingOn() {
    try {
      return window.localStorage.getItem(CHA_KEY) !== "false";
    } catch (e) {
      return true;
    }
  }

  function setChaChing(on) {
    try {
      window.localStorage.setItem(CHA_KEY, on ? "true" : "false");
    } catch (e) {
      // The choice still applies until the page is reloaded.
    }
  }

  function motionAllowed() {
    const root = document.documentElement;
    if (root.getAttribute("data-reduced-motion") === "true") return false;
    if (root.getAttribute("data-lite") === "true") return false;
    return !(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  }

  function chaChingElement() {
    let el = document.getElementById("cha-ching");
    if (el) return el;
    const anchor = document.getElementById("advance-round-button");
    if (!anchor || !anchor.parentNode) return null;
    el = document.createElement("div");
    el.id = "cha-ching";
    el.className = "cha-ching";
    el.setAttribute("aria-hidden", "true");
    el.hidden = true;
    anchor.parentNode.insertBefore(el, anchor.nextSibling);
    return el;
  }

  function confettiBurst(host) {
    const colours = ["#e0c24c", "#7fd6a3", "#56b4e9", "#e69f00", "#d98bd0"];
    for (let i = 0; i < 16; i++) {
      const piece = document.createElement("span");
      piece.className = "cha-confetti" + (i % 2 ? " cha-confetti--round" : "");
      piece.style.left = (6 + Math.random() * 88) + "%";
      piece.style.background = colours[i % colours.length];
      piece.style.animationDelay = (Math.random() * 0.2) + "s";
      piece.style.setProperty("--cha-drift", (Math.random() * 60 - 30) + "px");
      host.appendChild(piece);
    }
    window.setTimeout(function () {
      Array.prototype.slice.call(host.querySelectorAll(".cha-confetti")).forEach(function (n) { n.remove(); });
    }, 1500);
  }

  function roundGain(earned, beat) {
    if (!chaChingOn()) return false;
    const el = chaChingElement();
    if (!el || !isFinite(earned)) return false;
    if (chaTimer) window.clearTimeout(chaTimer);
    const target = Math.max(0, Math.round(earned));
    const label = function (n) { return "Earned +" + n + " funds" + (beat ? " \u2014 more than last round!" : ""); };
    el.hidden = false;
    el.textContent = "";
    const text = document.createElement("span");
    el.appendChild(text);
    if (!motionAllowed()) {
      text.textContent = label(target);
    } else {
      const start = window.performance.now();
      const span = 700;
      const step = function (now) {
        const t = Math.min(1, (now - start) / span);
        text.textContent = label(Math.round(target * (1 - Math.pow(1 - t, 3))));
        if (t < 1) window.requestAnimationFrame(step);
      };
      window.requestAnimationFrame(step);
      if (beat) confettiBurst(el);
    }
    chaTimer = window.setTimeout(function () { el.hidden = true; }, 3500);
    return true;
  }

  function initChaChing() {
    const box = document.getElementById("cha-ching-checkbox");
    if (!box) return;
    box.checked = chaChingOn();
    box.addEventListener("change", function () { setChaChing(box.checked); });
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
    initConfirmThreshold();
    initKeyboardPlay();
    initChaChing();
    initGlossary();
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
        resetConfirmThreshold();
        setChaChing(true);
        const chaBox = document.getElementById("cha-ching-checkbox");
        if (chaBox) chaBox.checked = true;
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
    glossary: GLOSSARY,
  };
  window.HerdFx = { roundGain: roundGain, chaChingOn: chaChingOn };
})();
