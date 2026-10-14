/* Pocket Bazaar, Desktop boot only (loaded by pc.html). The guided tutorial for the Desktop layout: the Classic
   walkthrough names the toolbar buttons, which the Desktop layout turns into icons, the Menu and windows, and the
   crates and tools sit in a side column. index.html uses these steps when they exist
   (window.POCKET_BAZAAR_PC_TUTORIAL_STEPS) and its own otherwise. */
window.POCKET_BAZAAR_PC_TUTORIAL_STEPS = [
  {
    title: "Welcome to the stall",
    text: "Customers ask for goods; you make them by merging and hand them over. Nothing here runs on a clock: customers wait in beats, which are your own actions, so you can stop and think as long as you like. This walkthrough covers the Desktop layout. Skip it any time, and reopen it from the Menu.",
  },
  {
    selector: "#stats",
    title: "Your numbers",
    text: "Coins, the day, how many customers you have served, and your combo. Every action you take moves one of these, or the tally in the side column.",
  },
  {
    selector: "#queue",
    title: "The customers",
    text: "Up to three customers stand at the stall with their orders and a patience bar counted in beats. Pick up a good, then click a customer who wants it (they get a dashed outline), or drag the good onto them.",
  },
  {
    selector: "#board",
    title: "The counter",
    text: "Click a good to pick it up and click an identical one (marked with a +) to merge them into the next tier. Three together jump two tiers, and a merge that lines up with a neighbour keeps going as a chain. Drag works too.",
  },
  {
    selector: "#pc-side",
    title: "Crates, Sell and Broom",
    text: "Crates are free and never run out. Sell turns any good into coins and Broom sweeps it away, so the counter can never jam. Only crates, merges, sweeps and hand-overs are beats; moving and selling are free.",
  },
  {
    selector: "#start-day-button",
    title: "Open the stall",
    text: "Each market day has a festival that changes one rule, and it says plainly whether it makes the day easier or harder. Between days you can spend coins on permanent upgrades and decorations.",
  },
  {
    selector: "#pc-menu-button",
    title: "Icons and the Menu",
    text: "The icons open Achievements, the Regulars and Settings. The Menu, or Escape when nothing else is open, holds the rest: this tutorial, About Pocket Bazaar with the pledge, and What's New. Each opens as a window over the game, and Escape closes the top one.",
  },
  {
    title: "You are ready",
    text: "Take your time. Your stall is saved after every action, and nothing is lost by leaving.",
  },
];

/* Desktop extras. pc.js is loaded in the head, before the board exists, so every block waits for DOMContentLoaded or
   for the game's own redraw hook, and reads the game through window.pocketBazaarApi (set by app.js). */
function pbPcView() {
  return window.pocketBazaarApi ? window.pocketBazaarApi.view() : null;
}
function pbPcCell(i) {
  return document.querySelector('#board .cell[data-cell="' + i + '"]');
}
/* Blocks add their redraw work here; app.js calls it after every redraw (the cells are rebuilt each time). */
window.pbPcAfterRender = [];
window.pocketBazaarAfterRender = function () {
  window.pbPcAfterRender.forEach(function (fn) { fn(); });
};

/* R4-PBPC-1: hover a piece to see every piece it can merge with and what the merge makes. */
(function () {
  "use strict";
  var hovered = null;

  function clearHover() {
    document.querySelectorAll("#board .cell[data-hover-target]").forEach(function (el) {
      el.removeAttribute("data-hover-target");
      el.removeAttribute("data-result");
    });
  }

  function showHover() {
    clearHover();
    var view = pbPcView();
    if (hovered === null || !view || view.phase !== "open" || !view.board) return;
    var mine = view.board.cells[hovered];
    var partners = view.partners[String(hovered)] || [];
    if (!mine) return;
    partners.forEach(function (p) {
      var el = pbPcCell(p);
      var other = view.board.cells[p];
      if (!el || !other) return;
      el.setAttribute("data-hover-target", "true");
      el.setAttribute("data-result", "Makes " + (mine.next || other.next || "a showpiece"));
    });
  }

  window.pbPcAfterRender.push(showHover);

  document.addEventListener("DOMContentLoaded", function () {
    var board = document.getElementById("board");
    if (!board) return;
    board.addEventListener("mouseover", function (e) {
      var cell = e.target.closest(".cell");
      hovered = cell && cell.classList.contains("has-good") ? Number(cell.dataset.cell) : null;
      showHover();
    });
    board.addEventListener("mouseleave", function () {
      hovered = null;
      showHover();
    });
  });
})();

/* The keys in use: the defaults, or the ones the player set in Settings, Controls (R4-PBPC-9, window.NOYVJ_PC_CUSTOM_KEYS).
   crates is null until the player sets one: the number keys always open crates, a set key opens the highlighted one. */
function pbPcKeys() {
  var c = window.NOYVJ_PC_CUSTOM_KEYS || {};
  return {
    handover: (c.handover || "d").toUpperCase(),
    sell: (c.sell || "s").toUpperCase(),
    broom: (c.broom || "b").toUpperCase(),
    crates: c.crates ? c.crates.toUpperCase() : null,
  };
}

/* R4-PBPC-8: hold Alt to see the key for every crate and tool. Labels come from data-hotkey on the buttons (set after
   every redraw, since the crates are rebuilt) and are drawn by CSS only while html has pc-show-keys. */
(function () {
  "use strict";

  function mark() {
    var keys = pbPcKeys();
    document.querySelectorAll("#crates .crate-btn").forEach(function (btn, n) {
      btn.setAttribute("data-hotkey", String(n + 1));
    });
    var sell = document.getElementById("sell-button");
    var broom = document.getElementById("broom-button");
    if (sell) sell.setAttribute("data-hotkey", keys.sell);
    if (broom) broom.setAttribute("data-hotkey", keys.broom);
  }
  function show() {
    mark();
    document.documentElement.classList.add("pc-show-keys");
  }
  function hide() {
    document.documentElement.classList.remove("pc-show-keys");
  }

  window.pbPcAfterRender.push(mark);
  document.addEventListener("keydown", function (e) { if (e.key === "Alt") show(); });
  document.addEventListener("keyup", function (e) { if (e.key === "Alt") hide(); });
  window.addEventListener("blur", hide);
})();

/* R4-PBPC-7: board size slider (80 to 160 percent) in Settings. A per-device display choice: localStorage, never the save. */
(function () {
  "use strict";
  var KEY = "pocket-bazaar-board-scale";
  var MIN = 0.8;
  var MAX = 1.6;

  function read() {
    var raw = null;
    try { raw = window.localStorage.getItem(KEY); } catch (e) { raw = null; }
    var val = raw === null ? NaN : parseFloat(raw);
    return isFinite(val) && val >= MIN && val <= MAX ? val : 1;
  }
  function apply(val, remember) {
    document.documentElement.style.setProperty("--board-scale", String(val));
    if (!remember) return;
    try { window.localStorage.setItem(KEY, String(val)); } catch (e) { /* convenience only */ }
  }

  apply(read(), false);

  document.addEventListener("DOMContentLoaded", function () {
    var reset = document.getElementById("display-reset-button");
    var panel = document.getElementById("settings-panel");
    if (!panel || !reset) return;
    var row = document.createElement("div");
    row.className = "settings-row board-size-row";
    var label = document.createElement("label");
    label.setAttribute("for", "board-scale-slider");
    label.textContent = "Board size ";
    var slider = document.createElement("input");
    slider.type = "range";
    slider.id = "board-scale-slider";
    slider.min = String(MIN);
    slider.max = String(MAX);
    slider.step = "0.05";
    var out = document.createElement("span");
    out.id = "board-scale-value";
    function show(val) {
      slider.value = String(val);
      out.textContent = Math.round(val * 100) + "%";
      slider.setAttribute("aria-valuetext", out.textContent);
    }
    show(read());
    slider.addEventListener("input", function () {
      var val = Math.min(MAX, Math.max(MIN, parseFloat(slider.value) || 1));
      show(val);
      apply(val, true);
    });
    row.appendChild(label);
    row.appendChild(slider);
    row.appendChild(out);
    reset.parentNode.parentNode.insertBefore(row, reset.parentNode);
    reset.addEventListener("click", function () {
      try { window.localStorage.removeItem(KEY); } catch (e) { /* convenience only */ }
      apply(1, false);
      show(1);
    });
  });
})();

/* R4-PBPC-6: a large combo counter under the stats. It grows with the multiplier and says how many orders in a row.
   It only restates what the Combo stat already says (aria-hidden) and has no animation of its own. */
(function () {
  "use strict";
  var big = null;

  function refresh() {
    var view = pbPcView();
    var stats = document.getElementById("stats");
    if (!stats || !view) return;
    if (!big) {
      big = document.createElement("div");
      big.id = "combo-display";
      big.setAttribute("aria-hidden", "true");
      stats.insertAdjacentElement("afterend", big);
    }
    var day = view.phase === "open" ? view.day : null;
    if (!day || !day.streak) {
      big.textContent = "";
      big.className = "";
      return;
    }
    big.className = "active combo-x" + day.mult;
    big.textContent = "";
    var num = document.createElement("span");
    num.className = "combo-num";
    num.textContent = "x" + day.mult;
    var line = document.createElement("span");
    line.className = "combo-line";
    line.textContent = day.streak + (day.streak === 1 ? " order in a row" : " orders in a row");
    big.appendChild(num);
    big.appendChild(line);
  }

  window.pbPcAfterRender.push(refresh);
})();

/* R4-PBPC-3: hover a customer to read what they want and their patience in beats. The card's own aria-label already
   says the same, so the tip is a visual extra (aria-hidden). */
(function () {
  "use strict";
  var tip = null;
  var current = null;

  function tipText(c) {
    var wants = c.items.map(function (i) { return i.label + (i.done ? " (handed over)" : ""); }).join(", ");
    return c.name + " (" + c.kind + ") wants " + wants + ". Patience: " + c.patience + " of " + c.max + " beats. Pays " + c.pay + " coins.";
  }

  function place(card) {
    var r = card.getBoundingClientRect();
    tip.hidden = false;
    var w = tip.getBoundingClientRect().width;
    var left = r.right + 8;
    if (left + w > window.innerWidth - 8) left = Math.max(8, r.left - w - 8);
    tip.style.left = left + "px";
    tip.style.top = Math.max(8, r.top) + "px";
  }

  function refresh() {
    var view = pbPcView();
    if (!tip || current === null || !view || view.phase !== "open" || !view.customers[current]) {
      if (tip) tip.hidden = true;
      return;
    }
    tip.textContent = tipText(view.customers[current]);
    var card = document.querySelector('#queue .customer[data-drop="customer:' + current + '"]');
    if (card) place(card); else tip.hidden = true;
  }

  window.pbPcAfterRender.push(refresh);

  document.addEventListener("DOMContentLoaded", function () {
    var queue = document.getElementById("queue");
    if (!queue) return;
    tip = document.createElement("div");
    tip.id = "pc-customer-tip";
    tip.setAttribute("aria-hidden", "true");
    tip.hidden = true;
    document.body.appendChild(tip);
    queue.addEventListener("mouseover", function (e) {
      var card = e.target.closest(".customer");
      current = card && !card.classList.contains("empty") ? Number(card.dataset.drop.slice(9)) : null;
      refresh();
    });
    queue.addEventListener("mouseleave", function () { current = null; refresh(); });
  });
})();

/* R4-PBPC-2: right-click a piece for Pick up, Sell and Hand over at the cursor. app.js does the work (pb-action). */
(function () {
  "use strict";
  var menu = null;
  var board = null;
  var forCell = null;
  var handBtn = null;

  function hideMenu() {
    if (menu) menu.hidden = true;
    forCell = null;
  }

  // Escape closes this menu first. Registered at once (before the shell's own capture listener) and marking the event
  // as handled with the shell's flag, so the same Escape does not also open the shell's Menu window.
  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape" || !menu || menu.hidden) return;
    e.preventDefault();
    e.__pcMenuOpened = true;
    hideMenu();
  }, true);

  function build() {
    menu = document.createElement("div");
    menu.id = "pc-context-menu";
    menu.setAttribute("role", "menu");
    menu.setAttribute("aria-label", "Piece actions");
    menu.hidden = true;
    [["pick-up", "Pick up"], ["sell", "Sell"], ["hand-over", "Hand over"]].forEach(function (pair) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = pair[1];
      btn.dataset.action = pair[0];
      btn.setAttribute("role", "menuitem");
      btn.addEventListener("click", function () {
        var cell = forCell;
        hideMenu();
        if (cell !== null) board.dispatchEvent(new CustomEvent("pb-action", { detail: { action: pair[0], cell: cell } }));
      });
      if (pair[0] === "hand-over") handBtn = btn;
      menu.appendChild(btn);
    });
    menu.addEventListener("keydown", function (e) {
      var items = Array.prototype.slice.call(menu.querySelectorAll("button"));
      var at = items.indexOf(document.activeElement);
      if (e.key === "ArrowDown") { e.preventDefault(); items[(at + 1) % items.length].focus(); }
      else if (e.key === "ArrowUp") { e.preventDefault(); items[(at + items.length - 1) % items.length].focus(); }
    });
    document.body.appendChild(menu);
  }

  document.addEventListener("DOMContentLoaded", function () {
    board = document.getElementById("board");
    if (!board) return;
    build();
    board.addEventListener("contextmenu", function (e) {
      var cell = e.target.closest(".cell.has-good");
      var view = pbPcView();
      if (!cell || !view || view.phase !== "open") return;
      e.preventDefault();
      forCell = Number(cell.dataset.cell);
      var takers = view.deliverable[String(forCell)] || [];
      var who = takers.length && view.customers[takers[0]] ? view.customers[takers[0]].name : "";
      handBtn.textContent = who ? "Hand over to " + who : "Hand over";
      menu.hidden = false;
      var rect = menu.getBoundingClientRect();
      menu.style.left = Math.max(0, Math.min(e.clientX, window.innerWidth - rect.width - 8)) + "px";
      menu.style.top = Math.max(0, Math.min(e.clientY, window.innerHeight - rect.height - 8)) + "px";
      menu.querySelector("button").focus();
    });
    document.addEventListener("click", function (e) { if (menu && !menu.contains(e.target)) hideMenu(); });
    window.addEventListener("resize", hideMenu);
    window.addEventListener("scroll", hideMenu, true);
  });
})();
