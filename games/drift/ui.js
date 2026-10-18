/* Drift, page-level helpers shared by the Classic and Desktop pages. No game state here (all of it is in
   game.py): this file only presses buttons the game already wires up.

   I-13  Game keys: 1 / 2 / 3 buy Housing / Integration Services / Infrastructure, Enter Advance Round,
         U Reset this round, P Play 5 rounds, L Round Ledger, C Region Collection. They are listed in the
         shared "?" overlay (index.html passes them as `extra`) and in the Desktop hint bar.
   I-16  Trend graph crosshair: game.py draws invisible `.trend-hit` columns carrying the exact values per
         round (data-tip); hovering, touching, or pressing the left and right arrow keys (Home and End jump)
         while the graph has focus moves a crosshair line and shows that round's values.
   R4-DRMO-9  Phone term sheet: a long-press on a Terms chip opens a bottom sheet (see termSheet below). */
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

  // R4-DRMO-3: update strain ring on the Advance Round button for mobile view.
  (function advanceRing() {
    const btn = document.getElementById("advance-round-button");
    const strainBar = document.getElementById("strain-bar");
    if (!btn || !strainBar) return;

    function update() {
      const cls = strainBar.className || "";
      let level = "stable";
      if (cls.includes("strain--critical")) level = "critical";
      else if (cls.includes("strain--strained")) level = "strained";
      btn.setAttribute("data-strain", level);
      // The ring colour is never the only cue: the tooltip carries the word (the strain meter shows it too).
      btn.title = level === "stable" ? "" : "Strain is " + level + " in your region";
    }

    update();
    new MutationObserver(update).observe(strainBar, { attributes: true, attributeFilter: ["class"] });
  })();

  // R4-DRMO-2: on phones the region and the neighbouring district are two snap-scrolling cards (CSS does
  // the swiping). These two buttons are the non-touch way across; the one on the region card only shows
  // while the neighbour panel is available (game.py toggles that panel's hidden attribute).
  (function mobileSwipe() {
    const container = document.getElementById("mobile-swipe-container");
    const panel = document.getElementById("neighbor-panel");
    const toNeighbor = document.getElementById("swipe-to-neighbor");
    const toRegion = document.getElementById("swipe-to-region");
    const game = document.getElementById("game");
    if (!container || !panel || !toNeighbor || !toRegion || !game) return;

    function reduced() {
      return document.documentElement.classList.contains("reduce-motion")
        || window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    }
    function go(card, focusButton) {
      card.scrollIntoView({ inline: "center", block: "nearest", behavior: reduced() ? "auto" : "smooth" });
      focusButton.focus({ preventScroll: true });
    }
    function syncVisibility() { toNeighbor.hidden = panel.hidden; }

    toNeighbor.addEventListener("click", function () { go(panel, toRegion); });
    toRegion.addEventListener("click", function () { go(game, toNeighbor); });
    syncVisibility();
    new MutationObserver(syncVisibility).observe(panel, { attributes: true, attributeFilter: ["hidden"] });
  })();

  // R4-DRMO-9: on phones a long-press on a term (the Terms chips) opens its definition in a bottom sheet with
  // a way on to The Real Story. Nothing here uses a timer: the press length is the difference between the
  // pointerdown and pointerup event.timeStamp values, so the sheet opens when the finger lifts after a hold
  // of HOLD_MS or more (and on touch screens also on the browser's own long-press "contextmenu" event).
  // A short tap still reaches game.py's own click handler untouched. The keyboard path is the term's own
  // Enter/Space (pins the popover) followed by its "Show as bottom sheet" button, or the Menu key /
  // Shift+F10 on a focused term. Escape, the Close button or a tap outside close it, and focus goes back
  // to the term that opened it.
  (function termSheet() {
    const HOLD_MS = 500;
    const MOVE_LIMIT = 10;
    const row = document.querySelector(".glossary-row");
    const sheet = document.getElementById("glossary-sheet");
    const titleEl = document.getElementById("glossary-sheet-title");
    const textEl = document.getElementById("glossary-sheet-text");
    const moreBtn = document.getElementById("glossary-sheet-more");
    const closeBtn = document.getElementById("glossary-sheet-close");
    const openBtn = document.getElementById("glossary-sheet-open");
    const storyBtn = document.getElementById("glossary-more-button");
    if (!row || !sheet || !titleEl || !textEl || !moreBtn || !closeBtn) return;

    let press = null;        // the pointerdown being timed: { chip, id, x, y, t }
    let swallowClick = false; // the click that follows a long-press must not also toggle the popover
    let opener = null;       // the term that opened the sheet, to give focus back to

    function phone() {
      return window.matchMedia("(max-width: 600px)").matches;
    }
    function chipOf(target) {
      const chip = target && target.closest ? target.closest(".chip") : null;
      return chip && row.contains(chip) && chip.hasAttribute("data-term-def") ? chip : null;
    }
    function isOpen() { return !sheet.hidden; }

    function open(chip) {
      if (!phone() || !chip) return;
      if (isOpen() && opener === chip) return;
      opener = chip;
      titleEl.textContent = chip.getAttribute("data-term-label") || chip.textContent;
      textEl.textContent = chip.getAttribute("data-term-def") || "";
      moreBtn.hidden = !chip.hasAttribute("data-real-story");
      sheet.hidden = false;
      sheet.focus({ preventScroll: true });
    }
    function close(giveFocusBack) {
      if (!isOpen()) return;
      sheet.hidden = true;
      if (giveFocusBack && opener && document.contains(opener)) opener.focus({ preventScroll: true });
      opener = null;
    }

    row.addEventListener("pointerdown", function (event) {
      swallowClick = false;
      const chip = chipOf(event.target);
      if (!chip || event.button > 0 || event.isPrimary === false) { press = null; return; }
      press = { chip: chip, id: event.pointerId, x: event.clientX, y: event.clientY, t: event.timeStamp };
    });
    row.addEventListener("pointermove", function (event) {
      if (!press || event.pointerId !== press.id) return;
      if (Math.abs(event.clientX - press.x) > MOVE_LIMIT || Math.abs(event.clientY - press.y) > MOVE_LIMIT) press = null;
    });
    row.addEventListener("pointercancel", function () { press = null; });
    row.addEventListener("pointerup", function (event) {
      const started = press;
      press = null;
      if (!started || event.pointerId !== started.id) return;
      if (event.timeStamp - started.t >= HOLD_MS && phone()) {
        swallowClick = true;
        open(started.chip);
      }
    });
    // Touch browsers send this after about half a second of holding; the keyboard sends it for Menu / Shift+F10.
    row.addEventListener("contextmenu", function (event) {
      const chip = chipOf(event.target);
      if (!chip || !phone()) return;
      event.preventDefault();
      swallowClick = true;
      press = null;
      open(chip);
    });
    // Runs before game.py's click handler on the term (capture phase on the row), and never for the keyboard.
    row.addEventListener("click", function (event) {
      if (swallowClick && event.detail !== 0) {
        event.stopPropagation();
        event.preventDefault();
        // Touch browsers focus the term after the press ends, which would take focus off the sheet and
        // show the popover as well: put focus back on the sheet (the term's blur hides the popover).
        if (isOpen()) sheet.focus({ preventScroll: true });
      }
      swallowClick = false;
    }, true);
    row.addEventListener("keydown", function () { swallowClick = false; });

    if (openBtn) {
      openBtn.addEventListener("click", function () {
        const shown = row.querySelector('.chip[aria-expanded="true"]');
        if (shown) open(shown);
      });
    }
    closeBtn.addEventListener("click", function () { close(true); });
    moreBtn.addEventListener("click", function () {
      close(false);
      // The popover's own Real Story button opens the page (and the Desktop window) the same way as ever.
      if (storyBtn) storyBtn.click();
      const panel = document.getElementById("info-page-panel");
      if (panel && !panel.hidden && panel.scrollIntoView) {
        panel.scrollIntoView({ block: "start", behavior: "auto" });
      }
    });
    sheet.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        close(true);
        return;
      }
      if (event.key !== "Tab") return;
      const stops = [closeBtn, moreBtn].filter(function (b) { return !b.hidden; });
      const first = stops[0];
      const last = stops[stops.length - 1];
      const active = document.activeElement;
      if (event.shiftKey && (active === first || active === sheet)) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && active === last) {
        event.preventDefault();
        first.focus();
      }
    });
    document.addEventListener("pointerdown", function (event) {
      if (isOpen() && !sheet.contains(event.target) && !(openBtn && openBtn.contains(event.target))) close(false);
    });
    // Going wider than a phone (rotating a tablet) leaves nothing to show the sheet with.
    window.addEventListener("resize", function () { if (isOpen() && !phone()) close(false); });
  })();
})();
