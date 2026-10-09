/* Aftermath, page-level helpers shared by the Classic and Desktop pages. No game state here (that is
   all in game.py): this file only clicks buttons the game already wires up, focuses the skill tree,
   and animates one number.

   E-14  Game keys: 1 / 2 invest in Resilience / Growth at the chosen step, Enter Face Next Event,
         U undo the last investment click, T jump to the skill tree, H Past Runs, C Disaster Codex,
         S Lifetime Stats. Listed in the shared "?" overlay (index.html passes them as `extra`).
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

  function start() {
    watchPopup();
    watchSchedule();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
