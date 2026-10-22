/* Pocket Bazaar, part 4 of 5: what taps do (pick up, sell, broom, choose several, hand over), dragging and flicks
   with pointer events, and the keyboard. Glue only; every rule is in the engine. */
(function () {
  "use strict";

  var A = window.PocketBazaarApp;
  var $ = A.$, announce = A.announce, askThen = A.askThen, cellAt = A.cellAt, DRAG_THRESHOLD = A.DRAG_THRESHOLD,
      goodNode = A.goodNode, render = A.render, renderBoard = A.renderBoard, renderCrates = A.renderCrates,
      send = A.send, showMessage = A.showMessage;

  var drag = null;

  // ---- what taps do --------------------------------------------------------------------------
  function select(i) {
    A.selected = i;
    A.broomArmed = false;
    if (i !== null && i < A.cellEls.length) A.cursor = i;
    render();
    if (i !== null) announce((cellAt(i) ? cellAt(i).label : "") + " picked up");
  }
  function onCell(i) {
    var g = cellAt(i);
    A.cursor = i < A.cellEls.length ? i : A.cursor;
    if (A.broomArmed) {
      if (g) send({ action: "broom", at: i }); else showMessage("There is nothing there to sweep.", false);
      return;
    }
    if (A.selected === null) { if (g) select(i); return; }
    if (A.selected === i) { select(null); return; }
    var partners = A.view.partners[String(A.selected)] || [];
    if (!g || partners.indexOf(i) !== -1) { send({ action: "drop", from: A.selected, to: i }); return; }
    select(i);                                   // a different good: change the pick instead of swapping by accident
  }

  function sellAt(at) {
    var cell = cellAt(at);
    if (cell && cell.tier >= 4 && cell.family !== "wild") {
      askThen("pocket-bazaar-sell-high", "Sell " + cell.label + " for only " + cell.sell + " coins? A customer would pay far more.", "Sell it", function () { send({ action: "sell", at: at }); });
      return;
    }
    send({ action: "sell", at: at });
  }
  function doSell() {
    if (A.selected === null) { showMessage("Pick up a good first (tap it), then press Sell.", false); return; }
    sellAt(A.selected);
  }
  function doBroom() {
    if (A.selected !== null) { send({ action: "broom", at: A.selected }); return; }
    A.broomArmed = !A.broomArmed;
    render();
    announce(A.broomArmed ? "Broom ready. Tap a good to sweep it away." : "Broom put down.");
  }
  function letGo() {
    A.broomArmed = false;
    A.multi = [];
    select(null);
  }
  // R4-PBPC-5: Shift+click chooses several goods; Shift+D hands every one a chosen customer still wants to that one customer.
  function toggleMulti(i) {
    if (!A.view || A.view.phase !== "open" || !cellAt(i)) return;
    var at = A.multi.indexOf(i);
    if (at === -1) A.multi.push(i); else A.multi.splice(at, 1);
    A.selected = null;
    A.broomArmed = false;
    render();
    announce(A.multi.length + (A.multi.length === 1 ? " good chosen" : " goods chosen") + " to hand over together");
  }
  function handOverMulti() {
    var first = A.multi.length ? A.view.deliverable[String(A.multi[0])] || [] : [];
    if (!first.length) { showMessage("Nobody wants the first chosen good. Esc clears the choice.", false); return; }
    var to = first[0];
    var who = A.view.customers[to] ? A.view.customers[to].name : "";
    var chosen = A.multi.slice();
    var given = 0;
    chosen.forEach(function (from) {
      if (!A.view || A.view.phase !== "open" || !A.view.customers[to] || A.view.customers[to].name !== who) return;
      if ((A.view.deliverable[String(from)] || []).indexOf(to) === -1) return;
      send({ action: "deliver", from: from, to: to });
      given += 1;
    });
    A.multi = [];
    if (A.view && A.view.phase === "open") render();
    if (!given) showMessage("Nobody wanted those goods.", false);
  }

  // ---- dragging (pointer events: the same code serves a mouse, a finger and a pen) -----------------
  function dropTargetAt(x, y) {
    var node = document.elementFromPoint(x, y);
    return node ? node.closest("[data-drop]") : null;
  }
  function clearOver() {
    Array.prototype.forEach.call(document.querySelectorAll(".drop-over"), function (n) { n.classList.remove("drop-over"); });
  }
  function onPointerDown(e) {
    if (e.pointerType === "mouse" && e.button !== 0) return;
    var btn = e.target.closest("[data-cell]");
    if (!btn || A.broomArmed) return;
    var i = Number(btn.dataset.cell);
    if (!cellAt(i)) return;
    drag = { from: i, x: e.clientX, y: e.clientY, dx: 0, dy: 0, lastTarget: null, active: false, id: e.pointerId, ghost: null };
  }
  function onPointerMove(e) {
    if (!drag || e.pointerId !== drag.id) return;
    drag.dx = e.clientX - drag.x;
    drag.dy = e.clientY - drag.y;
    if (!drag.active) {
      if (Math.abs(drag.dx) + Math.abs(drag.dy) < DRAG_THRESHOLD) return;
      drag.active = true;
      select(drag.from);
      var cell = cellAt(drag.from);
      drag.ghost = goodNode(cell);
      drag.ghost.classList.add("dragging-ghost");
      document.body.appendChild(drag.ghost);
    }
    e.preventDefault();
    drag.ghost.style.left = e.clientX + "px";
    drag.ghost.style.top = e.clientY + "px";
    clearOver();
    var target = dropTargetAt(e.clientX, e.clientY);
    drag.lastTarget = target;
    if (target) target.classList.add("drop-over");
  }
  function endDrag(e, cancelled) {
    if (!drag || (e && e.pointerId !== drag.id)) return;
    var d = drag;
    drag = null;
    if (!d.active) return;
    if (d.ghost && d.ghost.parentNode) d.ghost.parentNode.removeChild(d.ghost);
    clearOver();
    A.suppressClick = true;
    setTimeout(function () { A.suppressClick = false; }, 0);
    if (cancelled) return;

    var spec = d.lastTarget ? d.lastTarget.dataset.drop : "";
    // R4-PBMO-1, a flick. A short push that ends on nothing (or back on its own cell) moves the
    // good one cell the way it was pushed, onto an empty cell or a match. A real drop on a cell, customer or tool is untouched.
    if (spec === "" || spec === "cell:" + d.from) {
      var flick = flickTarget(d);
      if (flick !== null) {
        var partners = A.view.partners[String(d.from)] || [];
        if (!cellAt(flick) || partners.indexOf(flick) !== -1) send({ action: "drop", from: d.from, to: flick });
        else { select(d.from); showMessage("Something is in the way there. Flick toward an empty cell or a match.", false); }
        return;
      }
    }
    if (spec === "sell") sellAt(d.from);
    else if (spec === "broom") send({ action: "broom", at: d.from });
    else if (spec.indexOf("customer:") === 0) send({ action: "deliver", from: d.from, to: Number(spec.slice(9)) });
    else if (spec.indexOf("cell:") === 0) {
      var to = Number(spec.slice(5));
      if (to === d.from) select(d.from); else send({ action: "drop", from: d.from, to: to });
    } else select(null);
  }
  var FLICK_MIN = 24;
  // The cell one step from d.from in the direction of the push, or null when the push was too short or leaves the grid.
  function flickTarget(d) {
    var b = A.view && A.view.board;
    if (!b || d.from >= b.w * b.h) return null;
    var ax = Math.abs(d.dx), ay = Math.abs(d.dy);
    if (Math.max(ax, ay) < FLICK_MIN) return null;
    var row = Math.floor(d.from / b.w), col = d.from % b.w;
    if (ax >= ay) col += d.dx > 0 ? 1 : -1; else row += d.dy > 0 ? 1 : -1;
    if (col < 0 || col >= b.w || row < 0 || row >= b.h) return null;
    return row * b.w + col;
  }

  // ---- the keyboard --------------------------------------------------------------------------
  function moveCursor(dx, dy) {
    var b = A.view.board;
    var row = Math.floor(A.cursor / b.w), col = A.cursor % b.w;
    row = Math.max(0, Math.min(b.h - 1, row + dy));
    col = Math.max(0, Math.min(b.w - 1, col + dx));
    A.cursor = row * b.w + col;
    renderBoard();
    A.cellEls[A.cursor].focus();
  }
  function onKey(e) {
    if (!A.view || A.view.phase !== "open" || e.ctrlKey || e.metaKey || e.altKey) return;
    var tag = e.target && e.target.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
    var onGrid = e.target && e.target.closest && e.target.closest("#board");
    var key = e.key;
    if (onGrid && key.indexOf("Arrow") === 0) {
      e.preventDefault();
      moveCursor(key === "ArrowRight" ? 1 : key === "ArrowLeft" ? -1 : 0, key === "ArrowDown" ? 1 : key === "ArrowUp" ? -1 : 0);
      return;
    }
    if (key === "Escape") { letGo(); return; }

    // R4-PBPC-9: keys the player set in Settings, Controls (pc.js, window.NOYVJ_PC_CUSTOM_KEYS), else the defaults
    function getCustom(action, fallback) {
      var k = window.NOYVJ_PC_CUSTOM_KEYS;
      return (k && k[action]) ? k[action].toLowerCase() : (fallback || "").toLowerCase();
    }

    var broomKey = getCustom("broom", "b");
    if (key.toLowerCase() === broomKey) { e.preventDefault(); if (onGrid && A.selected === null && cellAt(A.cursor)) send({ action: "broom", at: A.cursor }); else doBroom(); return; }

    var sellKey = getCustom("sell", "s");
    if (key.toLowerCase() === sellKey) { e.preventDefault(); if (A.selected === null && onGrid && cellAt(A.cursor)) select(A.cursor); doSell(); return; }

    var handoverKey = getCustom("handover", "d");
    if (e.shiftKey && A.multi.length && key.toLowerCase() === handoverKey) { e.preventDefault(); handOverMulti(); return; }
    if (key.toLowerCase() === handoverKey) {
      e.preventDefault();
      if (A.selected === null && onGrid && cellAt(A.cursor)) select(A.cursor);
      if (A.selected === null) { showMessage("Pick up a good first, then press " + ((handoverKey || "D").toUpperCase()) + " to hand it over.", false); return; }
      var takers = A.view.deliverable[String(A.selected)] || [];
      send({ action: "deliver", from: A.selected, to: takers.length ? takers[0] : 0 });
      return;
    }

    if (key === "c" || key === "C") {
      e.preventDefault();
      A.activeCrate = (A.activeCrate + 1) % A.view.crates.length;
      renderCrates();
      $("crates").children[A.activeCrate].focus();
      return;
    }

    // A key set in Settings, Controls opens the highlighted crate (C moves the highlight); the number keys always work.
    var cratesKey = getCustom("crates", "");
    if (cratesKey && key.toLowerCase() === cratesKey) {
      e.preventDefault();
      send({ action: "crate", family: A.view.crates[A.activeCrate].family });
      return;
    }
    if (/^[1-9]$/.test(key) && Number(key) <= A.view.crates.length) {
      e.preventDefault();
      A.activeCrate = Number(key) - 1;
      send({ action: "crate", family: A.view.crates[A.activeCrate].family });
    }
  }

  // what the other parts use
  A.doBroom = doBroom;
  A.doSell = doSell;
  A.endDrag = endDrag;
  A.onCell = onCell;
  A.onKey = onKey;
  A.onPointerDown = onPointerDown;
  A.onPointerMove = onPointerMove;
  A.select = select;
  A.sellAt = sellAt;
  A.toggleMulti = toggleMulti;
})();
