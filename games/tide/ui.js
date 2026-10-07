/* Tide, page-level helpers shared by the Classic and Desktop pages. No game state here (that is
   all in game.py): this file only clicks buttons the game already wires up, moves keyboard focus
   between coastline rows, and remembers which <details> panels were left open.

   D-14  Game keys: A advance, X advance up to 5 quiet seasons, 1/2/3 invest, R session report,
         L Harbor Ledger. Listed in the shared "?" overlay (index.html passes them as `extra`).
   D-7   Up/Down move keyboard focus between the coastline rows (one focus stop per row).
   D-27  Each <details> panel remembers its open/closed state across reloads (this browser only). */
(function () {
  "use strict";

  function safeGet(key) {
    try { return window.localStorage.getItem(key); } catch (e) { return null; }
  }
  function safeSet(key, value) {
    try { window.localStorage.setItem(key, value); } catch (e) { /* a convenience only */ }
  }

  // ---- D-14 game keys ------------------------------------------------------------------------
  function isTyping(target) {
    if (!target || !target.tagName) return false;
    return /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName) || Boolean(target.isContentEditable);
  }

  // Anything modal in front of the game: the opening screen, tutorial, a confirm dialog or the
  // "?" list. Keys do nothing until it is gone.
  function modalShown() {
    const selectors = "#opening-screen, #tutorial-card, #confirm-dialog-overlay:not([hidden]), .confirm-dialog-overlay, #kb-shortcuts-panel:not([hidden])";
    return Array.from(document.querySelectorAll(selectors)).some(function (node) {
      return node.getBoundingClientRect().width > 0;
    });
  }

  // On the Desktop page an open window sits over the game: the turn and invest keys stay off
  // so nothing happens behind it, while R and L still toggle their own panels.
  function windowOpen() {
    const backdrop = document.getElementById("pc-backdrop");
    return Boolean(backdrop && !backdrop.hidden);
  }

  function press(id) {
    const button = document.getElementById(id);
    if (button && !button.disabled && !button.hidden) button.click();
  }

  const TURN_KEYS = {
    a: "advance-season-button",
    x: "advance-x5-button",
    1: "output-invest-button",
    2: "reduction-invest-button",
    3: "adaptation-invest-button",
  };
  const PANEL_KEYS = { r: "session-summary-toggle-button", l: "ledger-toggle-button" };

  document.addEventListener("keydown", function (event) {
    if (event.defaultPrevented || event.ctrlKey || event.metaKey || event.altKey) return;
    if (isTyping(event.target) || modalShown()) return;
    const key = String(event.key || "").toLowerCase();
    if (PANEL_KEYS[key]) {
      event.preventDefault();
      press(PANEL_KEYS[key]);
    } else if (TURN_KEYS[key] && !windowOpen()) {
      event.preventDefault();
      press(TURN_KEYS[key]);
    }
  });

  // ---- D-7 coastline rows: Up/Down between the focusable row tiles ---------------------------
  document.addEventListener("keydown", function (event) {
    if (event.key !== "ArrowUp" && event.key !== "ArrowDown") return;
    const current = event.target && event.target.closest ? event.target.closest(".coastline-tile") : null;
    if (!current || !current.id) return;
    const match = /^coastline-tile-(\d+)-/.exec(current.id);
    if (!match) return;
    const next = Number(match[1]) + (event.key === "ArrowDown" ? 1 : -1);
    const target = document.getElementById("coastline-tile-" + next + "-0");
    if (target) {
      event.preventDefault();
      target.focus();
    }
  });

  // ---- D-27 remember each <details> panel ---------------------------------------------------
  // Keyed by the summary text, which is unique per panel and survives the Desktop layout moving
  // panels into windows. The small "i" help bubbles are not panels worth remembering.
  function detailsKey(details) {
    const summary = details.querySelector(":scope > summary");
    const label = summary ? summary.textContent.trim() : "";
    return !label || label === "i" ? null : "tide-details-open:" + label;
  }

  function restoreDetails() {
    document.querySelectorAll("details").forEach(function (details) {
      const key = detailsKey(details);
      if (!key) return;
      const saved = safeGet(key);
      if (saved === "1") details.open = true;
      else if (saved === "0") details.open = false;
    });
  }

  // `toggle` does not bubble, so listen in the capture phase on the document.
  document.addEventListener("toggle", function (event) {
    const details = event.target;
    if (!details || details.tagName !== "DETAILS") return;
    const key = detailsKey(details);
    if (key) safeSet(key, details.open ? "1" : "0");
  }, true);

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", restoreDetails);
  else restoreDetails();
})();
