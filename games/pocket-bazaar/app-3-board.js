/* Pocket Bazaar, part 3 of 5: the counter grid and shelf, crates, merge haptics, the selection line, the stats and
   render(). Glue only; every rule is in the engine. */
(function () {
  "use strict";

  var A = window.PocketBazaarApp;
  var $ = A.$, el = A.el, goodNode = A.goodNode, lsGet = A.lsGet, renderAbout = A.renderAbout,
      renderAchievements = A.renderAchievements, renderClosed = A.renderClosed, renderQueue = A.renderQueue,
      renderRegulars = A.renderRegulars, renderSeed = A.renderSeed, send = A.send, setText = A.setText;

  var shelfEl = null;

  function makeCell(i, label) {
    var b = el("button", "cell");
    b.type = "button";
    b.dataset.cell = i;
    b.dataset.drop = "cell:" + i;
    b.dataset.testid = "pocket-bazaar-cell-" + i;
    b.dataset.label = label;
    b.tabIndex = -1;
    b.addEventListener("click", function (e) { if (A.suppressClick) return; if (e.shiftKey && cellAt(i)) { A.toggleMulti(i); return; } A.onCell(i); });
    return b;
  }

  function ensureGrid(b) {
    var grid = $("board");
    var sig = b.w + "x" + b.h + (b.shelf ? "s" : "");
    if (grid.dataset.signature === sig) return;
    grid.textContent = "";
    A.cellEls = [];
    grid.style.setProperty("--cols", b.w);
    for (var i = 0; i < b.w * b.h; i++) {
      var row = Math.floor(i / b.w) + 1, col = (i % b.w) + 1;
      var c = makeCell(i, "Row " + row + ", column " + col);
      A.cellEls.push(c);
      grid.appendChild(c);
    }
    var slot = $("shelf-slot");
    slot.textContent = "";
    shelfEl = null;
    if (b.shelf) {
      slot.hidden = false;
      slot.appendChild(el("div", null, "Shelf"));
      shelfEl = makeCell(b.w * b.h, "Shelf");
      shelfEl.tabIndex = 0;
      slot.appendChild(shelfEl);
    } else {
      slot.hidden = true;
    }
    grid.dataset.signature = sig;
    A.cursor = Math.min(A.cursor, b.w * b.h - 1);
  }

  function cellButton(i) { return i < A.cellEls.length ? A.cellEls[i] : shelfEl; }
  function cellAt(i) { return A.view && A.view.board && A.view.board.cells[i] ? A.view.board.cells[i] : null; }

  function renderBoard() {
    var b = A.view.board;
    ensureGrid(b);
    var partners = A.selected !== null && A.view.partners[String(A.selected)] ? A.view.partners[String(A.selected)] : [];
    if (A.selected !== null && !cellAt(A.selected)) A.selected = null;
    b.cells.forEach(function (cell, i) {
      var btn = cellButton(i);
      if (!btn) return;
      var sig = cell ? cell.code : "";
      if (btn.dataset.sig !== sig) {
        btn.textContent = "";
        if (cell) btn.appendChild(goodNode(cell));
        btn.dataset.sig = sig;
      }
      btn.classList.toggle("has-good", Boolean(cell));
      btn.classList.toggle("selected", A.selected === i);
      btn.classList.toggle("multi", A.multi.indexOf(i) !== -1);
      btn.classList.toggle("partner", partners.indexOf(i) !== -1);
      btn.classList.toggle("broom-armed", A.broomArmed);
      var label = btn.dataset.label + ": " + (cell ? cell.label : "empty");
      if (A.selected === i) label += ", picked up";
      if (A.multi.indexOf(i) !== -1) label += ", chosen to hand over together";
      if (partners.indexOf(i) !== -1) label += ", would merge";
      btn.setAttribute("aria-label", label);
      btn.setAttribute("aria-pressed", A.selected === i ? "true" : "false");
      if (i < A.cellEls.length) btn.tabIndex = i === A.cursor ? 0 : -1;
    });
  }

  function renderCrates() {
    var holder = $("crates");
    var sig = A.view.crates.map(function (c) { return c.family; }).join(",");
    if (holder.dataset.signature !== sig) {
      holder.textContent = "";
      A.view.crates.forEach(function (crate, n) {
        var btn = el("button", "crate-btn");
        btn.type = "button";
        btn.dataset.family = crate.family;
        btn.dataset.testid = "pocket-bazaar-crate-" + crate.family;
        var icon = el("span", "crate-icon good shape-" + crate.shape + " fam-" + crate.family);
        icon.setAttribute("aria-hidden", "true");
        icon.appendChild(el("span", "good-shape"));
        icon.appendChild(el("span", "good-text", crate.letter));
        btn.appendChild(icon);
        btn.appendChild(el("span", "crate-name", crate.name));
        btn.setAttribute("aria-label", crate.name + " crate, key " + (n + 1));
        btn.addEventListener("click", function () { A.activeCrate = n; send({ action: "crate", family: crate.family }); });
        holder.appendChild(btn);
      });
      holder.dataset.signature = sig;
    }
    holder.dataset.many = A.view.crates.length > 3 ? "1" : "0";
    Array.prototype.forEach.call(holder.children, function (btn, n) { btn.classList.toggle("active", n === A.activeCrate); });
  }

  // R4-PBMO-2: a short buzz on a merge, stronger with the tier, one pulse per link of a chain, where the browser has
  // navigator.vibrate (most phones; never iOS Safari). Off with the Settings switch or with reduced motion.
  var HAPTICS_KEY = "pocket-bazaar-haptics";
  function hapticsAllowed() {
    if (!navigator.vibrate || document.documentElement.getAttribute("data-reduced-motion") === "true") return false;
    return lsGet(HAPTICS_KEY) !== "false";   // settings.js writes "true" or "false"
  }
  function mergeHaptic(tier, links) {
    if (!hapticsAllowed()) return;
    var pulse = 10 + 8 * Math.max(1, Math.min(5, tier));
    var pattern = [];
    for (var n = 0; n < Math.max(1, Math.min(4, links)); n++) {
      if (n) pattern.push(45);
      pattern.push(pulse);
    }
    try { navigator.vibrate(pattern); } catch (e) { /* a buzz is a nicety */ }
  }

  function renderInfo() {
    var info = $("selection-info");
    var cell = A.selected !== null ? cellAt(A.selected) : null;
    var text;
    if (A.multi.length) {
      text = A.multi.length + (A.multi.length === 1 ? " good chosen" : " goods chosen") + " to hand over together: press Shift+D to give them all to one customer. Shift+click a chosen good again to drop it, Esc clears.";
    } else if (A.broomArmed) {
      text = "Broom ready: tap a good to sweep it away for free. Esc puts the broom down.";
    } else if (cell) {
      text = cell.label + " picked up.";
      if (cell.family !== "wild" && cell.tier < 5) {
        var has = (A.view.partners[String(A.selected)] || []).length > 0;
        text += has ? " Tap a marked match (+) to merge it into " + cell.next + "." : " No match yet: it needs another " + cell.name + " to become " + cell.next + ".";
      } else if (cell.family === "wild") {
        text += " A wildcard merges with any good below a showpiece.";
      } else {
        text += " A showpiece: it does not merge any further.";
      }
      if ((A.view.deliverable[String(A.selected)] || []).length) text += " A customer wants it: tap them to hand it over.";
      text += " Sells for " + cell.sell + (cell.sell === 1 ? " coin." : " coins.");
    } else {
      text = A.view.full ? "The counter is full. Merge, sell or sweep something to make room." : "Open a crate to put a basic good on the counter. Two identical goods merge into a better one.";
    }
    setText(info, text);
    var sell = $("sell-button");
    setText(sell, cell ? "Sell (" + cell.sell + ")" : "Sell");
    $("broom-button").setAttribute("aria-pressed", A.broomArmed ? "true" : "false");
    var dockSell = document.querySelector('#mobile-dock [data-action="sell"]');
    var dockBroom = document.querySelector('#mobile-dock [data-action="broom"]');
    if (dockSell) setText(dockSell, cell ? "Sell (" + cell.sell + ")" : "Sell");
    if (dockBroom) dockBroom.setAttribute("aria-pressed", A.broomArmed ? "true" : "false");
  }

  function bumpStat(id, value) {
    var node = $(id);
    var next = String(value);
    if (node.textContent === next) return;
    var had = node.textContent !== "" && node.dataset.seen === "1";
    node.textContent = next;
    node.dataset.seen = "1";
    if (had) {
      node.classList.remove("bump");
      void node.offsetWidth;
      node.classList.add("bump");
    }
  }
  function renderStats() {
    bumpStat("stat-coins", A.view.coins);
    bumpStat("stat-day", A.view.day ? A.view.day.number : A.view.next_day);
    bumpStat("stat-served", A.view.day ? A.view.day.served + "/" + A.view.day.total : (A.view.summary ? A.view.summary.served + "/" + A.view.summary.total : "0"));
    bumpStat("stat-combo", "x" + (A.view.day ? A.view.day.mult : 1));
    var pips = $("stat-combo-pips");
    var pipText = "";
    if (A.view.day && A.view.day.mult < 3) {
      var need = 2, have = need - A.view.day.to_next;
      pipText = "\u25CF".repeat(have) + "\u25CB".repeat(need - have);
    } else if (A.view.day) { pipText = "max"; }
    setText(pips, pipText);
    $("stat-combo").parentNode.title = A.view.day ? "Order combo x" + A.view.day.mult + (A.view.day.to_next ? ": " + A.view.day.to_next + " more in a row for the next step" : ": the highest") : "";
    bumpStat("stat-orders", A.view.tally.orders);
    bumpStat("stat-crates", A.view.tally.crates);
    bumpStat("stat-merges", A.view.tally.merges);
    bumpStat("stat-chain", A.view.best_chain);
    bumpStat("stat-sold", A.view.tally.sold);
    bumpStat("stat-swept", A.view.tally.swept);
  }

  function render(event) {
    renderView(event);
    // The Desktop page (pc.js) redraws its hover and selection marks here, because every redraw above rebuilds the cells.
    if (typeof window.pocketBazaarAfterRender === "function") window.pocketBazaarAfterRender();
  }
  function renderView(event) {
    renderSeed();
    renderAbout();
    renderAchievements();
    renderRegulars();
    var open = A.view.phase === "open";
    $("game").dataset.phase = A.view.phase;
    $("closed-card").hidden = open;
    $("open-area").hidden = !open;
    renderStats();
    if (!open) { renderClosed(); if (window.PocketBazaarMarket) window.PocketBazaarMarket.render(A.view, send); return; }
    if (window.PocketBazaarMarket) window.PocketBazaarMarket.render(A.view, send);
    renderQueue();
    renderBoard();
    renderCrates();
    renderInfo();
    if (event && (event.kind === "merge" || event.kind === "crate")) {
      var target = cellButton(event.kind === "merge" ? event.dst : event.at);
      if (target) {
        if (event.kind === "merge") mergeHaptic(event.good ? event.good[1] : 1, event.links || 1);
        target.classList.remove("pop");
        void target.offsetWidth;
        target.classList.add("pop");
        setTimeout(function () { target.classList.remove("pop"); }, 600);
      }
    }
  }

  // what the other parts use
  A.cellAt = cellAt;
  A.render = render;
  A.renderBoard = renderBoard;
  A.renderCrates = renderCrates;
})();
