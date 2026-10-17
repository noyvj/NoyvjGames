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
    }

    update();
    new MutationObserver(update).observe(strainBar, { attributes: true, attributeFilter: ["class"] });
  })();

  // R4-DRMO-2: Swipe between region and neighbouring district on mobile.
  (function mobileSwipe() {
    const container = document.getElementById("mobile-swipe-container");
    if (!container) return;
    let startX = 0;
    let isSwiping = false;

    function handleStart(e) {
      startX = e.touches ? e.touches[0].clientX : e.clientX;
      isSwiping = true;
    }
    function handleEnd(e) {
      if (!isSwiping) return;
      isSwiping = false;
      const endX = e.changedTouches ? e.changedTouches[0].clientX : e.clientX;
      const diff = startX - endX;
      const threshold = 50;
      if (Math.abs(diff) > threshold) {
        const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        container.scrollBy({ left: diff > 0 ? container.clientWidth : -container.clientWidth, behavior: prefersReduced ? "auto" : "smooth" });
      }
    }
    container.addEventListener("touchstart", handleStart, { passive: true });
    container.addEventListener("touchend", handleEnd);
    container.addEventListener("mousedown", handleStart);
    container.addEventListener("mouseup", handleEnd);
  })();

  // R4-DRMO-9: Long-press on glossary terms opens a bottom-sheet definition.
  (function glossaryLongPress() {
    const sheet = document.getElementById("glossary-bottom-sheet");
    const titleEl = document.getElementById("glossary-bottom-sheet-title");
    const defEl = document.getElementById("glossary-bottom-sheet-def");
    const moreBtn = document.getElementById("glossary-bottom-sheet-more");
    if (!sheet || !titleEl || !defEl || !moreBtn) return;

    const GLOSSARY_DEFS = {
      capacity: "Total housing, services, and infrastructure capacity built so far. Counts against arrival pressure.",
      strain: "How far cumulative arrivals have outrun cumulative capacity over the whole run. Higher strain cuts income each round.",
      integration: "Only Integration Services moves people from pending to integrated. Integrated people contribute funds back every round.",
      control: "An unmanaged passive region experiencing the same background pressure, with zero investment. Shown for contrast.",
    };

    let timer = null;
    const terms = document.querySelectorAll(".glossary-row .chip");

    function showSheet(term) {
      titleEl.textContent = term.charAt(0).toUpperCase() + term.slice(1);
      defEl.textContent = GLOSSARY_DEFS[term] || "Definition not available.";
      sheet.classList.add("visible");
      sheet.hidden = false;
      const infoBtn = document.getElementById("info-page-toggle-button");
      if (infoBtn) {
        moreBtn.onclick = function () {
          infoBtn.click();
          sheet.classList.remove("visible");
          setTimeout(function () { sheet.hidden = true; }, 300);
        };
      }
    }

    terms.forEach(function (btn) {
      const term = btn.id.replace("glossary-", "").replace("-button", "");
      btn.addEventListener("touchstart", function (e) {
        timer = setTimeout(function () { showSheet(term); }, 500);
      });
      btn.addEventListener("touchend", function () { clearTimeout(timer); });
      btn.addEventListener("touchmove", function () { clearTimeout(timer); });
      btn.addEventListener("mousedown", function (e) {
        if (e.button !== 0) return;
        timer = setTimeout(function () { showSheet(term); }, 500);
      });
      btn.addEventListener("mouseup", function () { clearTimeout(timer); });
      btn.addEventListener("mouseleave", function () { clearTimeout(timer); });
    });

    document.addEventListener("click", function (e) {
      if (!sheet.classList.contains("visible")) return;
      if (sheet.contains(e.target)) return;
      sheet.classList.remove("visible");
      setTimeout(function () { sheet.hidden = true; }, 300);
    });
  })();
})();
