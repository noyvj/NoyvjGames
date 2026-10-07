/* Drift, page-level helpers shared by the Classic and Desktop pages. No game state here (all of it is in
   game.py): this file only presses buttons the game already wires up.

   I-13  Game keys: 1 / 2 / 3 buy Housing / Integration Services / Infrastructure, Enter Advance Round,
         U Reset this round, P Play 5 rounds, L Round Ledger, C Region Collection. They are listed in the
         shared "?" overlay (index.html passes them as `extra`) and in the Desktop hint bar. */
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

  const TURN_KEYS = {
    1: "housing-invest-button",
    2: "services-invest-button",
    3: "infrastructure-invest-button",
    u: "reset-round-button",
    p: "play-rounds-button",
  };
  const PANEL_KEYS = { l: "ledger-toggle-button", c: "collection-toggle-button" };

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
    } else if (key === "enter") {
      // Enter on a focused button or link already activates it; only act from the bare page.
      const tag = event.target && event.target.tagName;
      if (tag && /^(BUTTON|A|SUMMARY|DETAILS)$/.test(tag)) return;
      event.preventDefault();
      press("advance-round-button");
    }
  });
})();
