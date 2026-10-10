/* Aftermath, page-level helpers shared by the Classic and Desktop pages. No game state here (that is
   all in game.py): this file only clicks buttons the game already wires up, focuses the skill tree,
   and animates one number.

   E-14  Game keys: 1 / 2 invest in Resilience / Growth at the chosen step, Enter Face Next Event,
         U undo the last investment click, T jump to the skill tree, H Past Runs, C Disaster Codex,
         S Lifetime Stats. Listed in the shared "?" overlay (index.html passes them as `extra`).
   E-5   Focus moves to a panel when it opens and back to its button when it closes (Classic layout);
         the skill tree moves with the arrow keys, Enter unlocks, P pins. E-30 keeps the "Saved Ns ago" age fresh.
   GE-13 The "-58 damage prevented!" line counts up from 0 when a new event resolves (skipped under
         reduced motion; the final text is always already in the page, so this is only a flourish). */
(function () {
  "use strict";

  function isTyping(target) {
    if (!target || !target.tagName) return false;
    return /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName) || Boolean(target.isContentEditable);
  }

  // Anything modal in front of the game: the opening screen, tutorial, a confirm dialog or the "?" list.
  function modalShown() {
    const selectors = "#opening-screen, #tutorial-card, #confirm-dialog-overlay:not([hidden]), .confirm-dialog-overlay, #kb-shortcuts-panel:not([hidden])";
    return Array.from(document.querySelectorAll(selectors)).some(function (node) {
      return node.getBoundingClientRect().width > 0;
    });
  }

  // On the Desktop page an open window sits over the game: the turn keys stay off so nothing happens
  // behind it, while the panel keys still toggle their own panels.
  function windowOpen() {
    const backdrop = document.getElementById("pc-backdrop");
    return Boolean(backdrop && !backdrop.hidden);
  }

  function press(id) {
    const button = document.getElementById(id);
    if (button && !button.disabled && !button.hidden) button.click();
  }

  function focusTree() {
    const tree = document.getElementById("skill-tree");
    if (!tree) return;
    const target = tree.querySelector("button:not([disabled]):not([hidden])") || tree;
    target.focus({ preventScroll: true });
    if (target.scrollIntoView) target.scrollIntoView({ block: "center" });
  }

  const TURN_KEYS = { 1: "resilience-invest-button", 2: "growth-invest-button", u: "undo-allocation-button" };
  const PANEL_KEYS = { h: "past-runs-toggle-button", c: "codex-toggle-button", s: "stats-toggle-button" };

  document.addEventListener("keydown", function (event) {
    if (event.defaultPrevented || event.ctrlKey || event.metaKey || event.altKey) return;
    if (isTyping(event.target) || modalShown()) return;
    const key = String(event.key || "").toLowerCase();
    if (PANEL_KEYS[key]) {
      event.preventDefault();
      press(PANEL_KEYS[key]);
      return;
    }
    if (windowOpen()) return;
    if (TURN_KEYS[key]) {
      event.preventDefault();
      press(TURN_KEYS[key]);
    } else if (key === "t") {
      event.preventDefault();
      focusTree();
    } else if (key === "enter") {
      // Enter on a focused button or link already activates it; only act from the bare page.
      const tag = event.target && event.target.tagName;
      if (tag && /^(BUTTON|A|SUMMARY|DETAILS)$/.test(tag)) return;
      event.preventDefault();
      press("resolve-event-button");
    }
  });

  // ---- GE-13 count-up --------------------------------------------------------------------------
  function reducedMotion() {
    const root = document.documentElement;
    if (root.getAttribute("data-reduced-motion") === "true") return true;
    return Boolean(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  }

  let lastKey = "";
  function watchPopup() {
    const popup = document.getElementById("damage-prevented-popup");
    if (!popup) return;
    lastKey = popup.dataset.eventKey || "";
    function check() {
      const key = popup.dataset.eventKey;
      if (!key || key === lastKey) return;
      lastKey = key;
      if (reducedMotion()) return; // static number
      const target = Number(popup.dataset.prevented);
      const finalText = popup.textContent;
      if (!(target >= 1)) return;
      const steps = 12;
      let step = 0;
      const timer = window.setInterval(function () {
        step += 1;
        if (step >= steps) {
          window.clearInterval(timer);
          popup.textContent = finalText;
          return;
        }
        popup.textContent = "-" + Math.round((target * step) / steps) + " damage prevented!";
      }, 40);
    }
    new MutationObserver(check).observe(popup, { attributes: true, attributeFilter: ["data-event-key"] });
  }

  // E-17: hovering or focusing a chip in the schedule strip shows that event's details in the line
  // under it; leaving the strip restores the next event's details. The same text is on each chip as
  // its title and aria-label, so nothing depends on this script.
  function watchSchedule() {
    const strip = document.getElementById("schedule-strip");
    const detail = document.getElementById("schedule-detail");
    if (!strip || !detail) return;
    function show(event) {
      const chip = event.target && event.target.closest ? event.target.closest("li[data-detail]") : null;
      if (chip) detail.textContent = chip.getAttribute("data-detail");
    }
    function reset() {
      detail.textContent = detail.getAttribute("data-default") || "";
    }
    strip.addEventListener("mouseover", show);
    strip.addEventListener("focusin", show);
    strip.addEventListener("mouseleave", reset);
    strip.addEventListener("focusout", reset);
  }

  // E-5: focus management for the Classic layout. When a panel opens, focus moves to it (so a keyboard or
  // screen-reader user lands on what they asked for); when it closes, focus goes back to the button that
  // opened it. The Desktop layout (shared/pc-shell.js) already does this for its windows, so this stays off there.
  const PANEL_PAIRS = [
    ["howto-toggle-button", "howto-panel"],
    ["settings-toggle-button", "settings-panel"],
    ["info-page-toggle-button", "info-page-panel"],
    ["achievements-toggle-button", "achievements-panel"],
    ["past-runs-toggle-button", "past-runs-panel"],
    ["codex-toggle-button", "codex-panel"],
    ["stats-toggle-button", "stats-panel"],
    ["changelog-toggle-button", "changelog-panel"],
  ];

  function isDesktopLayout() {
    return window.NOYVJ_LAYOUT === "pc" || document.documentElement.getAttribute("data-layout") === "pc";
  }

  function watchPanelFocus() {
    if (isDesktopLayout()) return;
    PANEL_PAIRS.forEach(function (pair) {
      const toggle = document.getElementById(pair[0]);
      const panel = document.getElementById(pair[1]);
      if (!toggle || !panel) return;
      panel.setAttribute("tabindex", "-1");
      panel.setAttribute("role", "region");
      let wasHidden = panel.hidden;
      function label() {
        const text = (toggle.textContent || "").replace(/^[^A-Za-z0-9]+/, "").replace(/^(Hide|Review|Show)\s+/i, "").replace(/^[^A-Za-z0-9]+/, "").replace(/\s*\(\d[^)]*\)\s*$/, "").trim();
        panel.setAttribute("aria-label", text || pair[1]);
      }
      label();
      new MutationObserver(function () {
        const hiddenNow = panel.hidden;
        if (hiddenNow === wasHidden) return;
        wasHidden = hiddenNow;
        if (!hiddenNow) {
          label();
          panel.focus();
        } else {
          const active = document.activeElement;
          if (!active || active === document.body || panel.contains(active)) toggle.focus({ preventScroll: true });
        }
      }).observe(panel, { attributes: true, attributeFilter: ["hidden"] });
    });
  }

  // E-5: keyboard operation of the skill tree. Each skill is a labelled group; Up and Down (or Home and End)
  // move between the visible ones, Enter unlocks the focused skill if it can be bought, P pins or unpins it.
  // Every Unlock and Pin button is still a plain button reachable with Tab.
  function watchTree() {
    const tree = document.getElementById("skill-tree");
    if (!tree) return;
    Array.prototype.forEach.call(tree.querySelectorAll(".skill-row"), function (row) {
      const id = row.getAttribute("data-skill");
      row.setAttribute("tabindex", "-1");
      row.setAttribute("role", "group");
      row.setAttribute("aria-labelledby", "skill-" + id + "-status");
    });
    function visibleRows() {
      return Array.prototype.filter.call(tree.querySelectorAll(".skill-row"), function (row) { return !row.hidden; });
    }
    tree.addEventListener("keydown", function (event) {
      if (event.defaultPrevented || event.ctrlKey || event.metaKey || event.altKey) return;
      if (isTyping(event.target)) return;
      const row = event.target && event.target.closest ? event.target.closest(".skill-row") : null;
      if (!row) return;
      const rows = visibleRows();
      const at = rows.indexOf(row);
      let next = null;
      if (event.key === "ArrowDown") next = rows[Math.min(rows.length - 1, at + 1)];
      else if (event.key === "ArrowUp") next = rows[Math.max(0, at - 1)];
      else if (event.key === "Home") next = rows[0];
      else if (event.key === "End") next = rows[rows.length - 1];
      if (next) {
        event.preventDefault();
        next.focus();
        return;
      }
      if (event.target !== row) return; // Enter and P act only from the row itself, never on a button inside it
      const id = row.getAttribute("data-skill");
      if (event.key === "Enter") {
        event.preventDefault();
        const unlock = row.querySelector("[id$='-unlock-button']");
        if (unlock && !unlock.hidden && !unlock.disabled) unlock.click();
      } else if (event.key === "p" || event.key === "P") {
        event.preventDefault();
        const pin = row.querySelector("[id$='-pin-button']");
        if (pin && !pin.hidden) pin.click();
      }
    });
  }

  // E-30: the save badge says "Saved 12s ago"; game.py writes the moment of the last save into
  // data-saved-at, and this keeps the age fresh between renders (only while the state is "saved").
  function watchSaveHealth() {
    const badge = document.getElementById("save-health");
    const text = document.getElementById("save-health-text");
    if (!badge || !text) return;
    function age(seconds) {
      seconds = Math.max(0, Math.floor(seconds));
      if (seconds < 5) return "just now";
      if (seconds < 60) return seconds + "s ago";
      if (seconds < 3600) return Math.floor(seconds / 60) + " min ago";
      return Math.floor(seconds / 3600) + " h ago";
    }
    window.setInterval(function () {
      if (badge.getAttribute("data-state") !== "saved") return;
      const at = Number(badge.getAttribute("data-saved-at"));
      if (!at) return;
      text.textContent = "\u2713 Saved " + age((Date.now() - at) / 1000);
    }, 5000);
  }

  function start() {
    watchPopup();
    watchSchedule();
    watchPanelFocus();
    watchTree();
    watchSaveHealth();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
