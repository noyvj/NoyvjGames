/* Tide, page-level helpers shared by the Classic and Desktop pages. No game state here (that is
   all in game.py): this file only clicks buttons the game already wires up, moves keyboard focus
   between coastline rows, and remembers which <details> panels were left open.

   D-14  Game keys: A advance, X advance up to 5 quiet seasons, 1/2/3 invest, R session report,
         L Harbor Ledger. Listed in the shared "?" overlay (index.html passes them as `extra`).
   D-7   Arrow keys (and Home/End) move keyboard focus around the coastline tiles, row by row and
         column by column (one Tab stop per row, every tile focusable and labelled).
   D-21  Graph crosshair: hover, tap or Left/Right on a focused graph shows a vertical line and
         a readout for that season (the text comes from game.py in the graph's data-crosshair).
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

  // ---- D-7 coastline tiles: arrows between rows and columns ---------------------------------
  const TILE_ID = /^coastline-tile-(\d+)-(\d+)$/;
  const MOVES = { ArrowUp: [-1, 0], ArrowDown: [1, 0], ArrowLeft: [0, -1], ArrowRight: [0, 1] };

  document.addEventListener("keydown", function (event) {
    if (event.ctrlKey || event.metaKey || event.altKey) return;
    const current = event.target && event.target.closest ? event.target.closest(".coastline-tile") : null;
    const match = current && current.id ? TILE_ID.exec(current.id) : null;
    if (!match) return;
    let row = Number(match[1]);
    let col = Number(match[2]);
    if (MOVES[event.key]) {
      row += MOVES[event.key][0];
      col += MOVES[event.key][1];
    } else if (event.key === "Home") {
      col = 0;
    } else if (event.key === "End") {
      col = 1e6; // clamped below to the last column that exists
    } else {
      return;
    }
    let target = document.getElementById("coastline-tile-" + row + "-" + col);
    if (!target && event.key === "End") {
      col = Number(match[2]);
      while (document.getElementById("coastline-tile-" + row + "-" + (col + 1))) col += 1;
      target = document.getElementById("coastline-tile-" + row + "-" + col);
    }
    if (target) {
      event.preventDefault();
      target.focus();
    }
  });

  // ---- D-21 graph crosshair ------------------------------------------------------------------
  // game.py puts one readout string per x position in the svg's data-crosshair attribute. The
  // line is drawn in the svg and the text in a small overlay inside the graph's container.
  const SVG_NS = "http://www.w3.org/2000/svg";

  function crosshairLines(svg) {
    if (svg.__crosshairLines) return svg.__crosshairLines;
    let lines = null;
    try { lines = JSON.parse(svg.getAttribute("data-crosshair") || "null"); } catch (e) { lines = null; }
    svg.__crosshairLines = Array.isArray(lines) && lines.length ? lines : null;
    return svg.__crosshairLines;
  }

  function hideCrosshair(svg) {
    const line = svg.querySelector(".graph-crosshair");
    if (line) line.remove();
    const holder = svg.parentNode;
    const readout = holder ? holder.querySelector(".graph-readout") : null;
    if (readout) readout.remove();
    svg.__crosshairIndex = null;
  }

  function showCrosshair(svg, index) {
    const lines = crosshairLines(svg);
    if (!lines) return;
    const last = lines.length - 1;
    index = Math.max(0, Math.min(last, index));
    svg.__crosshairIndex = index;
    const width = svg.viewBox && svg.viewBox.baseVal ? svg.viewBox.baseVal.width : 260;
    const height = svg.viewBox && svg.viewBox.baseVal ? svg.viewBox.baseVal.height : 60;
    const x = last > 0 ? (index / last) * width : width / 2;
    let line = svg.querySelector(".graph-crosshair");
    if (!line) {
      line = document.createElementNS(SVG_NS, "line");
      line.setAttribute("class", "graph-crosshair");
      line.setAttribute("aria-hidden", "true");
      svg.appendChild(line);
    }
    line.setAttribute("x1", x);
    line.setAttribute("x2", x);
    line.setAttribute("y1", 0);
    line.setAttribute("y2", height);
    const holder = svg.parentNode;
    if (!holder) return;
    let readout = holder.querySelector(".graph-readout");
    if (!readout) {
      readout = document.createElement("div");
      readout.className = "graph-readout";
      readout.setAttribute("role", "status");
      holder.appendChild(readout);
    }
    readout.textContent = lines[index];
    readout.classList.toggle("graph-readout--left", index > last / 2);
  }

  function indexFromPointer(svg, event) {
    const lines = crosshairLines(svg);
    if (!lines) return 0;
    const width = svg.viewBox && svg.viewBox.baseVal ? svg.viewBox.baseVal.width : 260;
    let viewX;
    const matrix = svg.getScreenCTM ? svg.getScreenCTM() : null;
    if (matrix && svg.createSVGPoint) {
      const point = svg.createSVGPoint();
      point.x = event.clientX;
      point.y = event.clientY;
      viewX = point.matrixTransform(matrix.inverse()).x;
    } else {
      const box = svg.getBoundingClientRect();
      viewX = ((event.clientX - box.left) / Math.max(1, box.width)) * width;
    }
    return Math.round((viewX / width) * (lines.length - 1));
  }

  function graphOf(event) {
    const node = event.target && event.target.closest ? event.target.closest("svg[data-crosshair]") : null;
    return node && crosshairLines(node) ? node : null;
  }

  function onPointer(event) {
    const svg = graphOf(event);
    if (svg) showCrosshair(svg, indexFromPointer(svg, event));
  }
  document.addEventListener("pointermove", onPointer);
  document.addEventListener("pointerdown", onPointer);
  document.addEventListener("pointerout", function (event) {
    const svg = graphOf(event);
    // A finger lifting must not wipe the reading the person just took; a mouse leaving does.
    if (svg && event.pointerType === "mouse" && !svg.contains(event.relatedTarget)) hideCrosshair(svg);
  });

  document.addEventListener("keydown", function (event) {
    const svg = graphOf(event);
    if (!svg || event.ctrlKey || event.metaKey || event.altKey) return;
    const lines = crosshairLines(svg);
    const at = svg.__crosshairIndex == null ? lines.length - 1 : svg.__crosshairIndex;
    let next = null;
    if (event.key === "ArrowLeft") next = at - 1;
    else if (event.key === "ArrowRight") next = at + 1;
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = lines.length - 1;
    else if (event.key === "Escape" && svg.__crosshairIndex != null) {
      hideCrosshair(svg);
      event.stopPropagation();
      return;
    }
    if (next == null) return;
    event.preventDefault();
    showCrosshair(svg, next);
  });
  document.addEventListener("focusout", function (event) {
    const svg = graphOf(event);
    if (svg) hideCrosshair(svg);
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
