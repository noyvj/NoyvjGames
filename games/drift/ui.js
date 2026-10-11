/* Drift, page-level helpers shared by the Classic and Desktop pages. No game state here (all of it is in
   game.py): this file only presses buttons the game already wires up.

   I-13  Game keys: 1 / 2 / 3 buy Housing / Integration Services / Infrastructure, Enter Advance Round,
         U Reset this round, P Play 5 rounds, L Round Ledger, C Region Collection. They are listed in the
         shared "?" overlay (index.html passes them as `extra`) and in the Desktop hint bar.
   I-16  Trend graph crosshair: game.py draws invisible `.trend-hit` columns carrying the exact values per
         round (data-tip); hovering, touching, or pressing the left and right arrow keys (Home and End jump)
         while the graph has focus moves a crosshair line and shows that round's values. */
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

  // ---- I-16: trend graph crosshair --------------------------------------------------------------
  (function trendCrosshair() {
    const host = document.getElementById("trend-graph");
    const tip = document.getElementById("trend-tooltip");
    const live = document.getElementById("trend-sr");
    if (!host || !tip) return;
    let index = -1;

    function columns() {
      return Array.from(host.querySelectorAll(".trend-hit"));
    }

    function hide() {
      index = -1;
      tip.hidden = true;
      const line = host.querySelector(".trend-crosshair");
      if (line) line.style.display = "none";
    }

    function show(rect, speak) {
      const svg = rect.ownerSVGElement;
      const line = svg && svg.querySelector(".trend-crosshair");
      const x = rect.getAttribute("data-x") || "0";
      if (line) {
        line.setAttribute("x1", x);
        line.setAttribute("x2", x);
        line.style.display = "block";
      }
      const text = rect.getAttribute("data-tip") || "";
      tip.textContent = text;
      tip.hidden = false;
      // Keep the tooltip over the graph, flipping to the left half's right edge near the right side.
      const box = host.getBoundingClientRect();
      const viewWidth = svg && svg.viewBox && svg.viewBox.baseVal ? svg.viewBox.baseVal.width : 280;
      const px = (parseFloat(x) / viewWidth) * box.width;
      tip.style.left = Math.max(0, Math.min(box.width - tip.offsetWidth, px - tip.offsetWidth / 2)) + "px";
      if (speak && live) live.textContent = text;
    }

    host.addEventListener("pointermove", function (event) {
      const rect = event.target && event.target.closest ? event.target.closest(".trend-hit") : null;
      if (!rect) return;
      index = columns().indexOf(rect);
      show(rect, false);
    });
    host.addEventListener("pointerleave", function () {
      if (document.activeElement !== host) hide();
    });
    host.addEventListener("blur", hide);
    host.addEventListener("keydown", function (event) {
      const cols = columns();
      if (!cols.length) return;
      let next = index;
      if (event.key === "ArrowLeft") next = index < 0 ? cols.length - 1 : Math.max(0, index - 1);
      else if (event.key === "ArrowRight") next = index < 0 ? cols.length - 1 : Math.min(cols.length - 1, index + 1);
      else if (event.key === "Home") next = 0;
      else if (event.key === "End") next = cols.length - 1;
      else if (event.key === "Escape") { hide(); return; }
      else return;
      event.preventDefault();
      event.stopPropagation();
      index = next;
      show(cols[index], true);
    });
    // game.py redraws the graph on every action: a crosshair left over from the old drawing is gone, so
    // clear the state when the host's content changes.
    new MutationObserver(function () { index = -1; tip.hidden = true; }).observe(host, { childList: true });
  })();
})();
