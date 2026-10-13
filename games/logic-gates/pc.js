/* Logic Gates, Desktop boot only (loaded by pc.html). The guided tutorial for the Desktop layout: the Classic walkthrough points at
   buttons the Desktop layout moves into icons, the Menu and windows. index.html uses these steps when they exist
   (window.LOGIC_GATES_PC_TUTORIAL_STEPS) and its own otherwise. */
window.LOGIC_GATES_PC_TUTORIAL_STEPS = [
  {
    title: "Welcome to Meridian Relay",
    text: "Each board has switches on the left, lamps on the right, and a table the lamps must match. You wire chips between them. Nothing is timed. This walkthrough covers the Desktop layout. Skip it any time, and reopen it later from the Menu.",
  },
  {
    selector: "#level-goal",
    title: "The goal",
    text: "This sentence says what the lamps must do. The result table on the right checks every case at once and names the first one that is wrong.",
  },
  {
    selector: "#board-panel",
    title: "The board",
    text: "Solid thick wires carry 1, thin dashed wires carry 0. Click a round pin on a source, then a round pin on an input, to connect them. Flip the switches to see what your circuit does.",
  },
  {
    selector: "#board-panel",
    title: "Tie 1 and tie 0",
    text: "The two small boxes marked tie 1 and tie 0 are fixed inputs: a wire tied to 1 or to 0 for good. Use one when a chip needs a constant, for example tie one input of a NAND chip to 1 and it becomes an inverter. Hover a tie box for the same note.",
  },
  {
    selector: "#parts-panel",
    title: "Parts",
    text: "Add chips here. Every connection can also be chosen from a list on each chip. Undo, Clear and Restore mean nothing is ever lost. U undoes, N goes to the next level.",
  },
  {
    selector: "#check-panel",
    title: "Does it match?",
    text: "Every row must say Right. When they all do, the level is solved and the circuit becomes a chip you keep.",
  },
  {
    selector: "#hints-panel",
    title: "Stuck?",
    text: "A nudge, then a hint, then the answer in words with a button that puts it on the board. Asking takes nothing away.",
  },
  {
    selector: "#pc-menu-button",
    title: "Icons and the Menu",
    text: "The icons open the Levels (forty boards in five chapters), your Chips, Achievements and Settings. The Menu, or Escape when nothing else is open, holds the Sandbox, this tutorial, About Logic Gates with its named sources, the Station log and What's New. Each opens as a window over the game.",
  },
  {
    title: "You are ready",
    text: "Take your time. The station has waited eleven years.",
  },
];

/* Wire hover card (R4-LGPC-3) */
(function () {
  "use strict";
  var card = null;
  var visible = false;

  function showCard(el) {
    if (!card) return;
    var val = el.dataset.value || "?";
    var rows = el.dataset.rows || "";
    card.querySelector(".lg-wire-value").textContent = "Value: " + val;
    card.querySelector(".lg-wire-rows").textContent = "Rows high: " + (rows || "none");
    card.classList.add("visible");
    visible = true;
  }

  function hideCard() {
    if (!card) return;
    card.classList.remove("visible");
    visible = false;
  }

  function moveCard(e) {
    if (!visible || !card) return;
    var x = e.clientX + 12;
    var y = e.clientY + 12;
    var rect = card.getBoundingClientRect();
    if (x + rect.width > window.innerWidth) x = e.clientX - rect.width - 12;
    if (y + rect.height > window.innerHeight) y = e.clientY - rect.height - 12;
    card.style.left = x + "px";
    card.style.top = y + "px";
  }

  document.addEventListener("DOMContentLoaded", function () {
    card = document.createElement("div");
    card.className = "lg-wire-hover-card";
    card.innerHTML = '<span class="lg-wire-value"></span><span class="lg-wire-rows"></span>';
    document.body.appendChild(card);

    document.addEventListener("mouseover", function (e) {
      var wire = e.target.closest(".lg-wire");
      if (wire) showCard(wire);
    });
    document.addEventListener("mouseout", function (e) {
      var wire = e.target.closest(".lg-wire");
      if (wire && (!e.relatedTarget || !e.relatedTarget.closest(".lg-wire"))) hideCard();
    });
    document.addEventListener("mousemove", moveCard);
  });
})();

/* Drag-box selection (R4-LGPC-5) */
(function () {
  "use strict";
  var box = null;
  var startX, startY;
  var selected = [];
  var buffer = "";
  var dragging = false;

  function init() {
    var board = document.getElementById("board-holder");
    if (!board) return;

    board.addEventListener("mousedown", function (e) {
      if (e.button !== 0) return;
      if (e.target.closest(".lg-pin, .lg-chip-handle, .lg-tie")) return;
      startX = e.clientX;
      startY = e.clientY;
      box = document.createElement("div");
      box.className = "lg-drag-box";
      document.body.appendChild(box);
      dragging = true;
    });

    document.addEventListener("mousemove", function (e) {
      if (!dragging || !box) return;
      var x = Math.min(startX, e.clientX);
      var y = Math.min(startY, e.clientY);
      var w = Math.abs(e.clientX - startX);
      var h = Math.abs(e.clientY - startY);
      box.style.left = x + "px";
      box.style.top = y + "px";
      box.style.width = w + "px";
      box.style.height = h + "px";
    });

    document.addEventListener("mouseup", function (e) {
      if (!dragging || !box) return;
      dragging = false;
      var x = Math.min(startX, e.clientX);
      var y = Math.min(startY, e.clientY);
      var w = Math.abs(e.clientX - startX);
      var h = Math.abs(e.clientY - startY);

      if (w > 5 && h > 5) {
        selected = [];
        Array.from(board.children).forEach(function (el) {
          var rect = el.getBoundingClientRect();
          if (rect.right > x && rect.left < x + w && rect.bottom > y && rect.top < y + h) {
            el.classList.add("lg-selected");
            selected.push(el);
          }
        });
      }
      box.remove();
      box = null;
    });

    document.addEventListener("keydown", function (e) {
      if ((e.ctrlKey || e.metaKey) && e.key === "c" && selected.length > 0) {
        buffer = selected.map(function (el) { return el.outerHTML; }).join("\n");
        e.preventDefault();
      }
      if ((e.ctrlKey || e.metaKey) && e.key === "v") {
        if (buffer) {
          var frag = document.createDocumentFragment();
          var temp = document.createElement("div");
          temp.innerHTML = buffer;
          while (temp.firstChild) frag.appendChild(temp.firstChild);
          var pasteX = startX || 50, pasteY = startY || 50;
          Array.from(frag.children).forEach(function (el) {
            el.style.position = "absolute";
            el.style.left = (pasteX + Math.random() * 20) + "px";
            el.style.top = (pasteY + Math.random() * 20) + "px";
            board.appendChild(el);
          });
          e.preventDefault();
        }
      }
    });
  }

  document.addEventListener("DOMContentLoaded", init);
})();

/* R4-LGPC-10: Controls rebinding */
(function () {
  "use strict";
  var STORAGE_KEY = "logic-gates-controls";
  var defaults = {
    "Undo": "u",
    "Next level": "n",
    "Let go / menu / close window": "Escape",
    "All shortcuts": "?",
    "Wire toggle": " "
  };
  var bindings = {};
  var rebindingAction = null;

  function load() {
    try {
      var saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
      for (var k in defaults) {
        bindings[k] = saved[k] !== undefined ? saved[k] : defaults[k];
      }
    } catch (e) {
      bindings = Object.assign({}, defaults);
    }
  }

  function save() {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(bindings)); } catch (e) {}
  }

  function render() {
    var panel = document.getElementById("settings-panel");
    if (!panel) return;
    if (document.getElementById("controls-list")) return;

    var container = document.createElement("div");
    container.id = "controls-container";
    container.innerHTML = '<h3 class="settings-sub">Controls</h3><p class="note">Click a key to rebind it. Press any key to set it.</p>';
    var list = document.createElement("ul");
    list.id = "controls-list";
    list.className = "controls-list";

    for (var action in bindings) {
      var li = document.createElement("li");
      li.className = "control-row";
      var label = document.createElement("span");
      label.className = "control-label";
      label.textContent = action + ":";
      var keyBtn = document.createElement("button");
      keyBtn.className = "control-key";
      keyBtn.setAttribute("data-action", action);
      keyBtn.setAttribute("aria-label", "Rebind " + action);
      keyBtn.textContent = bindings[action] === " " ? "Space" : bindings[action];
      li.appendChild(label);
      li.appendChild(keyBtn);
      list.appendChild(li);
    }
    container.appendChild(list);
    panel.appendChild(container);
  }

  function handleKeydown(e) {
    if (!rebindingAction) return;
    var key = e.key === " " ? " " : e.key;
    bindings[rebindingAction] = key;
    save();
    var btn = document.querySelector('.control-key[data-action="' + rebindingAction + '"]');
    if (btn) {
      btn.textContent = key === " " ? "Space" : key;
      btn.classList.remove("active");
    }
    rebindingAction = null;
  }

  function init() {
    load();
    document.addEventListener("DOMContentLoaded", render);
    document.addEventListener("keydown", handleKeydown);
    document.addEventListener("click", function (e) {
      var btn = e.target.closest(".control-key");
      if (!btn) return;
      rebindingAction = btn.getAttribute("data-action");
      document.querySelectorAll(".control-key").forEach(function (b) { b.classList.remove("active"); });
      btn.classList.add("active");
      btn.textContent = "Press key...";
    });
    window.LG_CONTROLS = bindings;
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();

/* R4-LGPC-6: Docked truth table helper */
(function () {
  "use strict";
  var tableHolder = null;
  var rows = [];

  function getSwitchStates() {
    var states = [];
    var sws = document.querySelectorAll("#switches input[type='checkbox'], #switches [data-switch]");
    for (var i = 0; i < sws.length; i++) {
      states.push(sws[i].checked ? 1 : 0);
    }
    return states;
  }

  function highlightCurrent() {
    if (!tableHolder || !rows.length) return;
    var current = getSwitchStates();
    rows.forEach(function(row) {
      var rowVals = row.dataset.rowValues ? row.dataset.rowValues.split(",").map(Number) : [];
      if (rowVals.length === current.length && rowVals.every(function(v, i) { return v === current[i]; })) {
        row.classList.add("lg-current");
      } else {
        row.classList.remove("lg-current");
      }
    });
  }

  function init() {
    tableHolder = document.getElementById("table-holder");
    if (!tableHolder) return;

    var observer = new MutationObserver(function() {
      rows = Array.from(tableHolder.querySelectorAll(".lg-table-row, tr"));
      highlightCurrent();
    });
    observer.observe(tableHolder, { childList: true, subtree: true });

    rows = Array.from(tableHolder.querySelectorAll(".lg-table-row, tr"));
    highlightCurrent();

    tableHolder.addEventListener("click", function(e) {
      var row = e.target.closest(".lg-table-row, tr");
      if (!row) return;
      var vals = row.dataset.rowValues ? row.dataset.rowValues.split(",").map(Number) : [];
      if (vals.length === 0) return;

      var sws = document.querySelectorAll("#switches input[type='checkbox'], #switches [data-switch]");
      for (var i = 0; i < sws.length && i < vals.length; i++) {
        if (sws[i].type === "checkbox") {
          sws[i].checked = vals[i] === 1;
        } else {
          sws[i].dataset.switch = String(vals[i]);
        }
      }
      highlightCurrent();
    });

    document.addEventListener("change", function(e) {
      if (e.target.closest("#switches")) highlightCurrent();
    });
  }

  document.addEventListener("DOMContentLoaded", init);
})();
