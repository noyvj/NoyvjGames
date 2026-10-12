/* Signal, Desktop boot only (loaded by pc.html). The guided tutorial for the Desktop layout: the Classic
   walkthrough points at sections the Desktop layout rearranges (the status line becomes readout chips, the
   tool toggle and answer buttons move to a side column). index.html uses these steps when they exist
   (window.SIGNAL_PC_TUTORIAL_STEPS) and its own otherwise. */
window.SIGNAL_PC_TUTORIAL_STEPS = [
  {
    title: "Welcome to Signal",
    text: "Hidden transmitters are broadcasting somewhere on this grid. You can only listen at a few tiles, and each listen returns one number: the summed signal of every transmitter at that tile. This walkthrough covers the Desktop layout. Skip it any time, and reopen it later from the Menu (or press Escape).",
  },
  {
    selector: "#pc-readouts",
    title: "Your puzzle at a glance",
    text: "The chips show which puzzle you are on, how many pings you have left, par (how many pings a solver needed) and how many markers you have placed against how many transmitters there are. The mode tabs above the grid switch between the Easy and Hard dailies, the archive of past days and endless practice.",
  },
  {
    selector: "#board",
    title: "Ping a tile",
    text: "Click a tile to ping it, or move with the arrow keys and press Enter (or type a column letter and a row number, like D4, to jump). Each ping spends one from your budget. Nothing broadcasts from the outer ring. A single transmitter reads its radius minus the distance, and nothing beyond that, so a 5 could be one close transmitter or several far ones.",
  },
  {
    selector: "#waterfall-section",
    title: "Read the number",
    text: "Every reading appears here in the order you pinged. The number, the bar glyph and the fill height all say the same thing, so you never need colour to read them. Compare readings to work out where the transmitters must be: tiles your readings have ruled out are hatched in Easy.",
  },
  {
    selector: "#tool-toggle-button",
    title: "Mark your suspects",
    text: "Switch the tool to Mark (or press Space on a tile, or right-click it) to drop a diamond where you think a transmitter is. You need exactly one marker per transmitter.",
  },
  {
    selector: "#commit-button",
    title: "Commit",
    text: "When your markers match the transmitter count, commit. Every transmitter must be exactly right to win. Fewer pings than par is the boast. Then copy a spoiler-free result to share.",
  },
  {
    selector: "#pc-menu-button",
    title: "Icons and the Menu",
    text: "The four icons are the Archive of past days, Stats, Achievements and Settings. The Menu (or Escape, when nothing else is open) holds the rest: this tutorial, How to Play, About Signal, What's New, the community leaderboard and feedback. Each opens as a window over the game, and Escape closes the top one.",
  },
  {
    title: "You're ready",
    text: "That's the loop: ping, read, narrow it down, mark, commit. A new daily puzzle goes on the air every UTC midnight, and endless practice has bigger boards if you want more. Good luck.",
  },
];

// The Desktop layout is for wide windows, so the shared mobile dock (which would lift the answer buttons
// out of the side column into a fixed bar below 640px, and drop them back in the wrong place on widening)
// is switched off here. shared/mobile-dock.js assigns window.MobileDock after this file runs; the setter
// below keeps this inert stand-in in its place.
Object.defineProperty(window, "MobileDock", { configurable: true, get() { return { init() {} }; }, set() {} });

// Hover preview for R4-SIPC-1
(function () {
  var preview = document.createElement("div");
  preview.id = "hover-preview";
  preview.hidden = true;
  document.body.appendChild(preview);

  function updatePreview(cell) {
    var activeBtn = document.querySelector("#mode-tabs button[aria-pressed='true']");
    var r = 4;
    if (activeBtn) {
      var mode = activeBtn.getAttribute("data-mode-tab");
      if (mode === "wide") r = 5;
      else if (mode === "bigsky") r = 6;
    }
    var lines = [];
    for (var d = 0; d <= r; d++) {
      var val = Math.max(0, r - d);
      lines.push("d" + d + ": +" + val);
    }
    preview.innerHTML = lines.join("<br>");

    var rect = cell.getBoundingClientRect();
    var stage = document.querySelector("#pc-stage");
    if (stage) {
      var stageRect = stage.getBoundingClientRect();
      preview.style.left = (rect.right - stageRect.left + 8) + "px";
      preview.style.top = (rect.top - stageRect.top) + "px";
    }
    preview.hidden = false;
  }

  function hidePreview() {
    preview.hidden = true;
  }

  document.addEventListener("DOMContentLoaded", function () {
    var stage = document.querySelector("#pc-stage");
    if (!stage) return;
    stage.addEventListener("mouseover", function (e) {
      var cell = e.target.closest(".cell");
      if (cell) updatePreview(cell);
    });
    stage.addEventListener("mouseout", function (e) {
      var cell = e.target.closest(".cell");
      if (cell && !stage.contains(e.relatedTarget)) hidePreview();
    });
    // R4-SIPC-2: right-click toggles a "maybe" pencil note on the tile
    stage.addEventListener("contextmenu", function (e) {
      var cell = e.target.closest(".cell");
      if (cell) {
        e.preventDefault();
        cell.classList.toggle("maybe");
      }
    });
  });
})();

// R4-SIPC-6: Archive hover previews
(function () {
  var preview = null;
  var MODE_SIZES = { easy: "9×9", hard: "9×9", wide: "13×13", bigsky: "15×15" };

  function showPreview(dayEl) {
    if (!preview) {
      preview = document.createElement("div");
      preview.className = "cal-hover-preview";
      dayEl.appendChild(preview);
    }
    var date = dayEl.getAttribute("data-date") || "";
    var mode = (dayEl.getAttribute("data-mode") || "").toLowerCase();
    var result = (dayEl.getAttribute("data-result") || "").toLowerCase();
    var lines = [];
    if (date) lines.push(date);
    if (mode) {
      var size = MODE_SIZES[mode] || "?×?";
      lines.push(size + " " + mode.charAt(0).toUpperCase() + mode.slice(1));
    }
    if (result) {
      var resText = result === "won" ? "✔ Won" : result === "lost" ? "✖ Lost" : result === "in-progress" ? "… In progress" : "";
      if (resText) lines.push(resText);
    }
    preview.textContent = lines.join(" • ");
    preview.hidden = false;
  }

  function hidePreview() {
    if (preview && preview.parentNode) {
      preview.parentNode.removeChild(preview);
    }
    preview = null;
  }

  document.addEventListener("DOMContentLoaded", function () {
    var grid = document.getElementById("calendar-grid");
    if (!grid) return;

    grid.addEventListener("mouseover", function (e) {
      var day = e.target.closest(".cal-day");
      if (day) showPreview(day);
    });
    grid.addEventListener("mouseout", function (e) {
      var day = e.target.closest(".cal-day");
      if (day && !grid.contains(e.relatedTarget)) hidePreview();
    });
  });
})();

// R4-SIPC-7: Mouse-wheel zoom and drag pan for large boards (PC view)
(function () {
  var board = document.getElementById("board");
  if (!board) return;
  var wrap = board.parentElement;
  var SCALE_KEY = "signal-zoom-scale";
  var PAN_X_KEY = "signal-zoom-x";
  var PAN_Y_KEY = "signal-zoom-y";

  function getScale() {
    var v = parseFloat(localStorage.getItem(SCALE_KEY));
    return (!isNaN(v) && v >= 0.5 && v <= 3.0) ? v : 1.0;
  }
  function getX() {
    var v = parseFloat(localStorage.getItem(PAN_X_KEY));
    return isNaN(v) ? 0 : v;
  }
  function getY() {
    var v = parseFloat(localStorage.getItem(PAN_Y_KEY));
    return isNaN(v) ? 0 : v;
  }

  var s = getScale();
  var x = getX();
  var y = getY();
  board.style.transform = "translate(" + x + "px, " + y + "px) scale(" + s + ")";

  function applyTransform() {
    board.style.transform = "translate(" + x + "px, " + y + "px) scale(" + s + ")";
  }

  function recentre() {
    s = 1.0; x = 0; y = 0;
    applyTransform();
    localStorage.setItem(SCALE_KEY, "1");
    localStorage.setItem(PAN_X_KEY, "0");
    localStorage.setItem(PAN_Y_KEY, "0");
  }

  // Wheel zoom
  wrap.addEventListener("wheel", function (e) {
    if (document.documentElement.getAttribute("data-reduced-motion") === "true") return;
    e.preventDefault();
    var delta = e.deltaY > 0 ? 0.9 : 1.1;
    var newS = Math.max(0.5, Math.min(3.0, s * delta));
    var rect = wrap.getBoundingClientRect();
    var cx = e.clientX - rect.left - rect.width / 2;
    var cy = e.clientY - rect.top - rect.height / 2;
    x += (cx - x) * (1 - newS / s);
    y += (cy - y) * (1 - newS / s);
    s = newS;
    applyTransform();
    localStorage.setItem(SCALE_KEY, s.toFixed(3));
    localStorage.setItem(PAN_X_KEY, x.toFixed(2));
    localStorage.setItem(PAN_Y_KEY, y.toFixed(2));
  }, { passive: false });

  // Drag pan
  var dragging = false;
  var startX, startY, startPanX, startPanY;
  wrap.addEventListener("mousedown", function (e) {
    if (document.documentElement.getAttribute("data-reduced-motion") === "true") return;
    if (e.button !== 0) return;
    dragging = true;
    startX = e.clientX;
    startY = e.clientY;
    startPanX = x;
    startPanY = y;
    wrap.classList.add("grabbing");
  });
  document.addEventListener("mousemove", function (e) {
    if (!dragging) return;
    x = startPanX + (e.clientX - startX);
    y = startPanY + (e.clientY - startY);
    applyTransform();
    localStorage.setItem(PAN_X_KEY, x.toFixed(2));
    localStorage.setItem(PAN_Y_KEY, y.toFixed(2));
  });
  document.addEventListener("mouseup", function () {
    if (dragging) {
      dragging = false;
      wrap.classList.remove("grabbing");
    }
  });

  // Recentre key 'R' or double-click
  document.addEventListener("keydown", function (e) {
    if ((e.key === "r" || e.key === "R") && !e.ctrlKey && !e.altKey && !e.metaKey) {
      var target = e.target;
      if (target.closest("#pc-stage")) recentre();
    }
  });
  wrap.addEventListener("dblclick", function () {
    recentre();
  });
})();

// R4-SIPC-9: Held mouse button sweeps marks across tiles
(function () {
  var board = document.getElementById("board");
  if (!board) return;
  var sweeping = false;
  var lastCell = null;

  function toggleSweep(cell) {
    if (cell && cell.classList.contains("cell")) {
      cell.classList.toggle("marked");
      lastCell = cell;
    }
  }

  board.addEventListener("mousedown", function (e) {
    if (document.documentElement.getAttribute("data-reduced-motion") === "true") return;
    if (e.button !== 0) return;
    var cell = e.target.closest(".cell");
    if (cell) {
      e.preventDefault();
      sweeping = true;
      toggleSweep(cell);
    }
  });

  document.addEventListener("mousemove", function (e) {
    if (!sweeping) return;
    var cell = e.target.closest(".cell");
    if (cell !== lastCell) {
      toggleSweep(cell);
    }
  });

  document.addEventListener("mouseup", function () {
    sweeping = false;
    lastCell = null;
  });
})();

// R4-SIPC-8: Shift ruler line
(function () {
  var overlay = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  overlay.id = "ruler-overlay";
  overlay.innerHTML = '<line id="ruler-line" x1="0" y1="0" x2="0" y2="0" />' +
                      '<text id="ruler-label" x="0" y="0"></text>';
  var stage = document.getElementById("pc-stage");
  if (!stage) return;
  stage.appendChild(overlay);

  function getCellCenter(cell) {
    var rect = cell.getBoundingClientRect();
    return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
  }

  function updateRuler() {
    var cursor = document.querySelector("#board .cursor, #board .active, #board .cell[aria-current='true']");
    if (!cursor) return;
    var pings = Array.from(document.querySelectorAll("#board .cell:has(.cell-num)"));
    if (pings.length === 0) return;

    var cRect = getCellCenter(cursor);
    var board = document.getElementById("board");
    var n = parseInt(board.style.getPropertyValue("--n") || "9", 10);
    var cols = n + 1; // includes axis column
    var cells = Array.from(board.querySelectorAll(".cell"));
    var cursorIdx = cells.indexOf(cursor);
    var r1 = Math.floor(cursorIdx / cols);
    var c1 = cursorIdx % cols;
    var cursorReading = parseInt(cursor.querySelector(".cell-num")?.textContent || "0", 10);

    var nearest = null;
    var minDist = Infinity;
    var diff = 0;

    for (var i = 0; i < pings.length; i++) {
      var pIdx = cells.indexOf(pings[i]);
      var r2 = Math.floor(pIdx / cols);
      var c2 = pIdx % cols;
      var manhattan = Math.abs(r1 - r2) + Math.abs(c1 - c2);
      if (manhattan < minDist) {
        minDist = manhattan;
        nearest = pings[i];
        diff = Math.abs(cursorReading - parseInt(pings[i].querySelector(".cell-num")?.textContent || "0", 10));
      }
    }

    if (!nearest) return;

    var nRect = getCellCenter(nearest);
    overlay.classList.add("active");
    document.getElementById("ruler-line").setAttribute("x1", cRect.x);
    document.getElementById("ruler-line").setAttribute("y1", cRect.y);
    document.getElementById("ruler-line").setAttribute("x2", nRect.x);
    document.getElementById("ruler-line").setAttribute("y2", nRect.y);

    var label = "d=" + minDist;
    if (cursorReading !== 0 || parseInt(nearest.querySelector(".cell-num").textContent, 10) !== 0) {
      label += " | Δ=" + diff;
    }
    var textEl = document.getElementById("ruler-label");
    textEl.textContent = label;
    textEl.setAttribute("x", (cRect.x + nRect.x) / 2);
    textEl.setAttribute("y", (cRect.y + nRect.y) / 2 - 5);
    textEl.setAttribute("text-anchor", "middle");
    textEl.setAttribute("dominant-baseline", "middle");
  }

  document.addEventListener("keydown", function (e) {
    if (e.key === "Shift") updateRuler();
  });
  document.addEventListener("keyup", function (e) {
    if (e.key === "Shift") overlay.classList.remove("active");
  });
})();

// R4-SIPC-10: History panel beside the board
(function () {
  var panel = document.createElement("div");
  panel.id = "history-panel";
  panel.className = "history-panel";
  panel.innerHTML = '<h3>History</h3><div id="hist-streak" class="history-chart"></div><div id="hist-par" class="history-chart"></div>';

  function render() {
    var stateStr = localStorage.getItem("signal:state");
    if (!stateStr) return;
    try {
      var state = JSON.parse(stateStr);
      var mode = (document.querySelector("#mode-tabs button[aria-pressed='true']") || {}).getAttribute("data-mode-tab") || "easy";
      var days = state.days || {};
      var streak = 0;
      var parBars = "";
      
      for (var i = 0; i < 7; i++) {
        var d = new Date();
        d.setDate(d.getDate() - i);
        var ds = d.toISOString().split("T")[0];
        var res = days[ds] ? days[ds][mode] : null;
        if (res === "won") streak++; else if (res) streak = 0;
        
        var cls = res === "won" ? "won" : res === "lost" ? "lost" : "empty";
        parBars += '<span class="hist-bar ' + cls + '" title="' + ds + '"></span>';
      }
      
      document.getElementById("hist-streak").textContent = "Streak: " + streak;
      document.getElementById("hist-par").innerHTML = parBars;
    } catch(e) {}
  }

  document.addEventListener("DOMContentLoaded", function () {
    var side = document.getElementById("pc-side") || document.querySelector("#pc-body");
    if (side) side.appendChild(panel);
    render();
    
    // Update when mode tabs change
    document.addEventListener("click", function(e) {
      if (e.target.closest("[data-mode-tab]")) render();
    });
  });
})();
