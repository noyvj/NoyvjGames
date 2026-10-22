/* Pocket Bazaar view: glue only. The engine (game.py and its modules) holds every rule; this file draws what
   handle() returns and forwards what the player does. No game logic lives here (the one exception is "which
   cells could this good merge with", which the engine sends as `partners`).

   The page script is cut into five classic scripts that share ONE object, window.PocketBazaarApp (see the File map
   in CLAUDE.md). They load in this order and each is wrapped in its own function, so no new global names exist:
     app-1-core.js     constants, shared state, helpers, drawing a good, toast and message, send() and askThen()
     app-2-stall.js    the customer queue, About and What's New, achievements, regulars, goals, decorations,
                       the closed stall and the upgrade shop, the stall seed
     app-3-board.js    the counter grid, crates, merge haptics, the selection line, stats, render()
     app-4-actions.js  what taps do (pick up, sell, broom, hand over), dragging and flicks, the keyboard
     app.js            the peek panel, wire(), the tutorial steps, boot() and the phone dock (loads last)
   State that more than one part reads or writes lives on the object: A.engine, A.view, A.selected, A.multi,
   A.cursor, A.broomArmed, A.activeCrate, A.cellEls, A.suppressClick. Functions another part calls are exported as
   A.name at the end of their own part. */
(function () {
  "use strict";

  var A = window.PocketBazaarApp = {};
  A.engine = null;
  A.view = null;
  A.selected = null;
  A.multi = [];
  A.cursor = 0;
  A.broomArmed = false;
  A.activeCrate = 0;
  A.cellEls = [];
  A.suppressClick = false;

  var ENGINE_MODULES = ["goods.py", "rng.py", "board.py", "orders.py", "days.py", "festival.py", "renown.py", "shop.py", "pledge.py", "info.py", "achievements.py", "decorations.py", "regulars.py", "day.py", "marketbot.py", "market.py"];
  var STORE_KEY = "pocket-bazaar:state";
  var BACKUP_KEY = "pocket-bazaar:state-backup";
  var DRAG_THRESHOLD = 8;

  var $ = function (id) { return document.getElementById(id); };

  function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* convenience only */ } }

  function setText(node, text) { if (node.textContent !== text) node.textContent = text; }
  function announce(text) {
    var live = $("announce");
    live.textContent = "";
    setTimeout(function () { live.textContent = text; }, 40);
  }
  function el(tag, cls, text) {
    var node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  // ---- drawing a good ------------------------------------------------------------------------
  function goodNode(cell) {
    var wrap = el("span", "good shape-" + cell.shape + " fam-" + cell.family + " t" + cell.tier);
    wrap.appendChild(el("span", "good-shape"));
    wrap.appendChild(el("span", "good-text", cell.letter + (cell.family === "wild" ? "" : cell.tier)));
    var pips = el("span", "pips");
    pips.setAttribute("aria-hidden", "true");
    if (cell.tier >= 5) pips.appendChild(el("span", "pip star", "★"));
    else for (var i = 0; i < cell.tier; i++) pips.appendChild(el("span", "pip"));
    wrap.appendChild(pips);
    return wrap;
  }

  function itemNode(item) {
    var wrap = el("span", "item" + (item.done ? " done" : ""));
    var good = el("span", "good shape-" + item.shape + " fam-" + item.family + " t" + item.tier);
    good.appendChild(el("span", "good-shape"));
    good.appendChild(el("span", "good-text", item.letter + (item.tier_text || item.tier)));
    wrap.appendChild(good);
    return wrap;
  }

  function showToast(text) {
    var t = $("toast");
    t.textContent = text;
    t.classList.toggle("on", Boolean(text));
  }

  function showMessage(text, ok, flavor) {
    var m = $("message");
    var extra = (flavor || []).join(" ");
    var sig = (text || "") + "|" + extra;
    if (m.dataset.sig !== sig) {
      m.dataset.sig = sig;
      m.textContent = text || "";
      if (extra) m.appendChild(el("span", "msg-flavor", extra));
    }
    m.classList.toggle("refused", ok === false && Boolean(text));
  }

  // ---- talking to the engine -----------------------------------------------------------------
  function persist() {
    try {
      var proxy = A.engine.getState();
      var obj = proxy.toJs({ dict_converter: Object.fromEntries });
      if (proxy.destroy) proxy.destroy();
      lsSet(STORE_KEY, JSON.stringify(obj));
    } catch (e) { /* the save is a convenience until the save widget is wired */ }
  }
  function send(request) {
    if (!A.engine) return null;
    if (window.PocketBazaarMarket) request.today = window.PocketBazaarMarket.today();     // the view passes the date in
    var result = JSON.parse(A.engine.handle(JSON.stringify(request)));
    if (result.error) { $("engine-status").textContent = "Something went wrong: " + result.error; return null; }
    A.view = result;
    showToast("");
    if (request.action === "drop" || request.action === "sell" || request.action === "start_day") A.multi = [];
    if (request.action === "drop" || request.action === "sell" || request.action === "broom" || request.action === "deliver" || request.action === "start_day") A.selected = null;
    if (request.action === "start_day") { A.cursor = 0; A.broomArmed = false; }
    A.render(result.event);
    showMessage(result.message, result.ok, result.flavor);
    if (result.message) announce(result.message + " " + (result.flavor || []).join(" "));
    persist();
    return result;
  }

  // The only two questions the game ever asks: selling a tier-4 or tier-5 good, and wiping the stall. Neither
  // is a guilt prompt; both can be switched off with "don't ask again".
  function askThen(id, message, confirmLabel, go) {
    if (window.ConfirmDialog) window.ConfirmDialog.ask({ id: id, message: message, confirmLabel: confirmLabel, allowSkip: id !== "pocket-bazaar-reset", onConfirm: go });
    else go();
  }

  // what the other parts use
  A.$ = $;
  A.announce = announce;
  A.askThen = askThen;
  A.BACKUP_KEY = BACKUP_KEY;
  A.DRAG_THRESHOLD = DRAG_THRESHOLD;
  A.el = el;
  A.ENGINE_MODULES = ENGINE_MODULES;
  A.goodNode = goodNode;
  A.itemNode = itemNode;
  A.lsGet = lsGet;
  A.lsSet = lsSet;
  A.send = send;
  A.setText = setText;
  A.showMessage = showMessage;
  A.showToast = showToast;
  A.STORE_KEY = STORE_KEY;
})();
