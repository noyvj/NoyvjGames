/* Herd, Desktop boot only (loaded by pc.html). The guided tutorial for the Desktop layout: the
   Classic walkthrough points at the single "status" panel, which the Desktop boot turns into
   readout chips and a Menu window. index.html uses these steps when they exist
   (window.HERD_PC_TUTORIAL_STEPS) and its own otherwise. */
window.HERD_PC_TUTORIAL_STEPS = [
  {
    title: "Welcome to Herd",
    text: "You're running a farm. Growing your herd earns income, but it also raises methane emissions automatically, in direct proportion to herd size, from turn one. This walkthrough covers the Desktop layout and the whole loop, including how to break that coupling. Skip any time, and reopen it later from the Menu.",
  },
  {
    selector: "#pc-readouts",
    title: "Your Farm at a Glance",
    text: "The chips across the top are the round, your Funds, Herd size, total accumulated Methane, the Coupling ratio (methane per herd unit), market/regulatory Pressure and your Score. Methane never resets and keeps climbing every round you have any herd. Pressure permanently eats into income (capped at 80% loss), and Score is funds minus a penalty on total methane, so a big bank balance built on unchecked emissions can still score low. The Menu opens the full Status window.",
  },
  {
    selector: "#actions",
    title: "Grow Your Herd",
    text: "Spend funds to add one unit to your herd. A bigger herd earns more income each round, but every unit also emits methane per round, automatically, for as long as it's alive. The line underneath previews exactly what the next unit costs and does. That coupling is the default; nothing else has to happen for it to kick in.",
  },
  {
    selector: "#gauge-section",
    title: "The Coupling Gauge",
    text: "This dial tracks methane produced per herd unit, not your total emissions. CLEAN (green) means low emissions per unit, HIGH (red) means baseline, fully-coupled agriculture. It only falls when you invest in the decoupling measures in the column on the right; it never falls just from having a bigger herd. Below it you can compare yourself with the documented real-world reduction, and the methane graph shows the shape of your run.",
  },
  {
    selector: "#decoupling",
    title: "Decoupling Investments",
    text: "Feed Additives, Herd Caps, and Capture Systems all reduce your coupling ratio (same herd size, lower emissions per unit), and their effects stack. There's a floor, though: past a certain point, further investment stops helping. Worked example: a herd of 10 at the 1.00 baseline ratio emits 10 methane/round. Five Capture Systems investments (10% reduction each) cut the ratio to 0.50, so that same 10-herd farm now emits only 5 methane/round: half the emissions, same herd size, same income per unit.",
  },
  {
    selector: "#plant-pivot",
    title: "Alternative Protein Pivot",
    text: "A different kind of decoupling: shift part of your output to plant-based production instead of making animal production more efficient. It cuts methane per unit much further, but plant-based output earns slightly less income, and it can only replace up to 60% of production.",
  },
  {
    selector: "#advance-round-button",
    title: "Advance Round",
    text: "Nothing happens until you click this (it stays pinned at the top of the column). Growing your herd or investing doesn't generate income or emit methane by itself. Advancing the round applies your herd's income (minus pressure) and adds this round's methane to your running total.",
  },
  {
    selector: "#pc-menu-button",
    title: "Icons and the Menu",
    text: "The three icons are Achievements, the Report Card and Settings. The Menu (or Escape, when nothing else is open) holds the rest: the full Status and score, the pure-growth baseline farm comparison, the community leaderboard, About Herd, the tutorial, How to Play, the real-world story, What's New and feedback. Each opens as a window over the farm, and Escape closes the top one.",
  },
  {
    title: "You're ready",
    text: "That's the loop: grow, watch methane rise automatically, invest to decouple growth from emissions, and advance the round to see it play out. A farm that grows larger and stays more profitable while cutting emissions per unit beats one that just grows unchecked. That's the whole point. Good luck out there.",
  },
];

// The "?" shortcuts list (shared/keyboard-shortcuts.js) is its own overlay, not a shell window, so
// without this an Escape that closes it would also open the Menu. Flagging the event first (the
// shell checks this flag in its own capture listener) lets Escape just close the list.
document.addEventListener("keydown", (e) => {
  if (e.key !== "Escape") return;
  const help = document.getElementById("kb-shortcuts-panel");
  if (help && !help.hidden) e.__pcMenuOpened = true;
}, true);

// R4-HEPC-4: hold I to label every part of the pasture. The labels are built while the key is down and
// removed when it comes up (or the window loses focus), so nothing is left on screen and the pasture's
// own markup is untouched. Nothing is looked up at the top level: the Desktop shell builds the page later.
(function () {
  var PARTS = [
    { sel: ".pasture-visual-sky", name: "Sky and weather", note: "Season swings change income (Farm operations: market and weather)", at: "top" },
    { sel: ".pasture-visual-cloud--a", name: "Clouds", note: "Plant-based demand surges (same option)" },
    { sel: ".pasture-visual-hill--front", name: "Pasture", note: "Welfare: Feed Additives, Herd Caps and Breeding raise it", at: "bottom" },
    { sel: "#pasture-barn", name: "Barn", note: "Barn styles unlock with achievements" },
    { sel: ".pasture-fence", name: "Fence", note: "The regional methane cap (option) stops growth past a limit" },
    { sel: ".pasture-visual-cow:not([hidden])", name: "Cows", note: "Grow Herd adds one; Feed Additives, Herd Caps and Capture Systems cut what each emits" },
    { sel: "#pasture-herd-count:not([hidden])", name: "Herd size", note: "Grow Herd" },
    { sel: "#golden-cow-glider:not([hidden])", name: "Golden cow", note: "Welcome it for bonus funds" }
  ];

  function typing(target) {
    var tag = target && target.tagName;
    return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || (target && target.isContentEditable);
  }

  function hideLabels() {
    document.querySelectorAll(".pasture-label").forEach(function (el) { el.remove(); });
  }

  function showLabels() {
    var pasture = document.getElementById("pasture-visual");
    if (!pasture || pasture.querySelector(".pasture-label")) return;
    var box = pasture.getBoundingClientRect();
    var placed = [];
    PARTS.forEach(function (part) {
      var el = pasture.querySelector(part.sel);
      if (!el) return;
      var r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) return;
      var label = document.createElement("div");
      label.className = "pasture-label";
      var name = document.createElement("strong");
      name.textContent = part.name;
      label.appendChild(name);
      label.appendChild(document.createTextNode(part.note));
      label.style.left = "0px";
      label.style.top = "0px";
      pasture.appendChild(label);
      // Measure at the pasture's own edge, then fix the width so moving the label cannot re-wrap it.
      var w = Math.ceil(label.getBoundingClientRect().width) + 1;
      label.style.width = w + "px";
      var h = label.offsetHeight;
      var x = r.left + r.width / 2 - box.left;
      var y = part.at === "top" ? h / 2 + 6 : part.at === "bottom" ? box.height - h / 2 - 6 : r.top + r.height / 2 - box.top;
      x = Math.max(w / 2 + 2, Math.min(box.width - w / 2 - 2, x));
      // Nudge a label down until it no longer sits on one already placed, then keep it inside the pasture.
      for (var tries = 0; tries < 12; tries++) {
        var hit = placed.some(function (p) { return Math.abs(p.x - x) < (p.w + w) / 2 && Math.abs(p.y - y) < (p.h + h) / 2; });
        if (!hit) break;
        y += h + 4;
      }
      y = Math.max(h / 2 + 2, Math.min(box.height - h / 2 - 2, y));
      label.style.left = x + "px";
      label.style.top = y + "px";
      placed.push({ x: x, y: y, w: w, h: h });
    });
  }

  document.addEventListener("keydown", function (e) {
    if (e.key.toLowerCase() !== "i" || e.ctrlKey || e.altKey || e.metaKey || e.repeat || typing(e.target)) return;
    showLabels();
  });
  document.addEventListener("keyup", function (e) { if (e.key.toLowerCase() === "i") hideLabels(); });
  window.addEventListener("blur", hideLabels);
})();

// R4-HEPC-3: right-click menu on a lever (Buy, Pin as a goal, Show cost over time, Compare with the
// baseline farm). Desktop page only. Every action uses something the game already has: Buy presses the
// lever's own button (so confirm dialogs and bulk mode apply), the history and baseline actions open the
// existing Menu windows, and a pin is a per-device mark kept in localStorage (never in a save).
(function () {
  if (window.NOYVJ_LAYOUT !== "pc") return;
  var PIN_KEY = "herd-pinned-goals";
  var LOG_KEYS = { feed: "feed", caps: "caps", capture: "capture", "plant-pivot": "pivot" };
  var menu = null, current = null, toast = null, toastTimer = null;

  function pinned() {
    try {
      var list = JSON.parse(localStorage.getItem(PIN_KEY) || "[]");
      return Array.isArray(list) ? list.filter(function (k) { return typeof k === "string"; }) : [];
    } catch (e) { return []; }
  }
  function savePins(list) {
    try { localStorage.setItem(PIN_KEY, JSON.stringify(list)); } catch (e) { /* not kept this session */ }
  }

  // The lever under the cursor: its button, its row, the name to show and its key in the lever history.
  function leverFor(target) {
    var button = target.closest("#grow-herd-button, .invest-row button");
    if (!button) return null;
    var row = button.closest(".invest-row") || document.getElementById("actions");
    var measure = row.getAttribute("data-measure");
    var nameEl = row.querySelector(".invest-name");
    return {
      button: button,
      row: row,
      pinKey: measure || "herd",
      logKey: measure ? LOG_KEYS[measure] || "all" : "herd",
      name: (nameEl ? nameEl.textContent : "Grow Herd").trim()
    };
  }

  function say(message) {
    if (!toast) {
      toast = document.createElement("div");
      toast.id = "lever-toast";
      toast.className = "context-menu-toast";
      toast.setAttribute("role", "status");
      toast.setAttribute("aria-live", "polite");
      document.body.appendChild(toast);
    }
    toast.hidden = false;
    toast.textContent = message;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toast.hidden = true; }, 4500);
  }

  function applyPins() {
    var list = pinned();
    document.querySelectorAll(".goal-pinned-badge").forEach(function (b) { b.remove(); });
    document.querySelectorAll(".goal-pinned").forEach(function (r) { r.classList.remove("goal-pinned"); });
    list.forEach(function (key) {
      var row = key === "herd" ? document.getElementById("actions") : document.querySelector('.invest-row[data-measure="' + key + '"]');
      if (!row) return;
      row.classList.add("goal-pinned");
      var badge = document.createElement("span");
      badge.className = "goal-pinned-badge";
      badge.textContent = "Goal";
      var host = row.querySelector(".invest-name");
      if (host) host.appendChild(badge); else row.insertBefore(badge, row.firstChild);
    });
  }

  function openWindow(openerId) {
    var opener = document.getElementById(openerId);
    if (!opener) { say("Open the Menu to find it."); return false; }
    opener.click();
    return true;
  }

  function act(action) {
    var lever = current;
    hideMenu(false);
    if (!lever) return;
    if (action === "buy") {
      if (!lever.button.disabled) lever.button.click();
    } else if (action === "pin") {
      var list = pinned();
      var at = list.indexOf(lever.pinKey);
      if (at >= 0) list.splice(at, 1); else list.push(lever.pinKey);
      savePins(list);
      applyPins();
      say(at >= 0 ? "Goal removed: " + lever.name : "Goal pinned: " + lever.name + ". It is marked on the lever until you unpin it.");
    } else if (action === "history") {
      if (!openWindow("pc-open-pc-collection-panel")) return;
      var filter = document.getElementById("lever-history-filter");
      if (filter) {
        filter.value = lever.logKey;
        filter.dispatchEvent(new Event("change", { bubbles: true }));
      }
      say("Lever history, filtered to " + lever.name + ": every price you paid, round by round.");
    } else if (action === "baseline") {
      if (!openWindow("pc-open-pc-baseline-panel")) return;
      var panel = document.getElementById("pc-baseline-panel");
      if (panel) {
        panel.classList.add("highlighted");
        setTimeout(function () { panel.classList.remove("highlighted"); }, 2000);
      }
    }
  }

  function buildMenu() {
    menu = document.createElement("div");
    menu.id = "lever-context-menu";
    menu.className = "lever-context-menu";
    menu.setAttribute("role", "menu");
    menu.hidden = true;
    [["buy", "Buy"], ["pin", "Pin as a goal"], ["history", "Show cost over time"], ["baseline", "Compare with baseline farm"]].forEach(function (item) {
      var b = document.createElement("button");
      b.type = "button";
      b.setAttribute("role", "menuitem");
      b.dataset.action = item[0];
      b.textContent = item[1];
      menu.appendChild(b);
    });
    menu.addEventListener("click", function (e) {
      var b = e.target.closest("button");
      if (b && !b.disabled) act(b.dataset.action);
    });
    menu.addEventListener("keydown", function (e) {
      var items = Array.prototype.filter.call(menu.querySelectorAll("button"), function (b) { return !b.disabled; });
      var at = items.indexOf(document.activeElement);
      if (e.key === "ArrowDown") { items[(at + 1) % items.length].focus(); e.preventDefault(); }
      else if (e.key === "ArrowUp") { items[(at - 1 + items.length) % items.length].focus(); e.preventDefault(); }
    });
    document.body.appendChild(menu);
  }

  function hideMenu(refocus) {
    if (!menu || menu.hidden) return;
    menu.hidden = true;
    if (refocus && current && current.button) current.button.focus();
    if (!refocus) return;
    current = null;
  }

  function showMenu(x, y, lever) {
    if (!menu) buildMenu();
    current = lever;
    var buy = menu.querySelector('[data-action="buy"]');
    buy.disabled = !!lever.button.disabled;
    menu.querySelector('[data-action="pin"]').textContent = pinned().indexOf(lever.pinKey) >= 0 ? "Unpin goal" : "Pin as a goal";
    menu.hidden = false;
    var w = menu.offsetWidth, h = menu.offsetHeight;
    menu.style.left = Math.max(4, Math.min(x, window.innerWidth - w - 4)) + "px";
    menu.style.top = Math.max(4, Math.min(y, window.innerHeight - h - 4)) + "px";
    var first = menu.querySelector("button:not(:disabled)");
    if (first) first.focus();
  }

  document.addEventListener("contextmenu", function (e) {
    var lever = leverFor(e.target);
    if (!lever) return;
    e.preventDefault();
    var r = lever.button.getBoundingClientRect();
    // A keyboard-opened menu (the Menu key or Shift+F10) reports no pointer position: use the button.
    showMenu(e.clientX || r.left, e.clientY || r.bottom, lever);
  });
  document.addEventListener("click", function (e) { if (menu && !menu.hidden && !menu.contains(e.target)) hideMenu(false); });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && menu && !menu.hidden) { hideMenu(true); e.__pcMenuOpened = true; }
  }, true);
  window.addEventListener("blur", function () { hideMenu(false); });
  window.addEventListener("resize", function () { hideMenu(false); });
  window.addEventListener("load", applyPins);
})();
