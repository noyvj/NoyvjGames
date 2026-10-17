/* Hull Repair, Desktop boot only (loaded by pc.html). The guided tutorial for the Desktop layout: the Classic walkthrough
   names toolbar buttons, which the Desktop layout turns into icons, the Menu and windows. index.html uses these steps when
   they exist (window.HULL_REPAIR_PC_TUTORIAL_STEPS) and its own otherwise. */
window.HULL_REPAIR_PC_TUTORIAL_STEPS = [
  {
    title: "Welcome to the station",
    text: "Tern is dark and needs its power and pipes laid again, one room at a time. Join each pair of matching ports with a line. Nothing is timed, and a wrong line only costs you a tap to take it back. This walkthrough covers the Desktop layout. Skip it any time, and reopen it from the Menu.",
  },
  {
    selector: "#board-holder",
    title: "The board",
    text: "Solid shapes are sources and ringed shapes are sinks; a source and sink with the same shape and letter belong together. Drag from a port to lay a line and drop it on its partner. Lines never cross or share a cell. Holes are hull that is gone.",
  },
  {
    selector: "#line-chips",
    title: "Your lines",
    text: "Each line shows whether it is joined. Click one to clear just that line. Dragging back along a line shortens it, dragging across another line cuts it, and clicking the end of a line takes one cell back. The arrow keys, Enter and Backspace draw without the mouse.",
  },
  {
    selector: "#board-line",
    title: "Patched and restored",
    text: "Joining every line patches the room and lights it dimly. Covering every cell as well restores it fully. The dots mark cells nothing covers yet; every board has exactly one way to cover them all.",
  },
  {
    selector: "#hint-button",
    title: "Hints are free",
    text: "A nudge says where to start, a hint draws the opening of one line as a dotted ghost, and the answer draws the whole layout. Using them never costs anything, and the room still counts.",
  },
  {
    selector: "#goals",
    title: "Your goals",
    text: "Three goals stay in view, in any order. Every line you lay, erase or hint you ask for counts toward something on the screen.",
  },
  {
    selector: "#pc-menu-button",
    title: "Icons and the Menu",
    text: "The icons open the Station map, the Repair log, Achievements and Settings. The Menu, or Escape when nothing else is open, holds the rest: this tutorial, About and What's New. Each opens as a window over the game, and Escape closes the top one.",
  },
  {
    title: "You are ready",
    text: "Take your time. Your repairs are saved as you go.",
  },
];

/* Desktop-only extras (R4-HRPC-2, 6, 7, 9, 10). pc.js loads in the page head and the Desktop shell builds #pc-side and
   #pc-stagebar on DOMContentLoaded, so everything here waits for the window load event. */
window.addEventListener("load", function () {
  var root = document.documentElement;
  var holder = document.getElementById("board-holder");
  if (!holder) return;
  function lsGet(key) { try { return localStorage.getItem(key); } catch (e) { return null; } }
  function lsSet(key, value) {
    try { localStorage.setItem(key, value); } catch (e) { /* not kept */ }
  }
  function boardSvg() { return holder.querySelector("svg"); }
  function reducedMotion() {
    var attr = root.getAttribute("data-reduced-motion");
    if (attr) return attr === "true";
    return Boolean(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  }

  /* R4-HRPC-2: hover a port to light its twin and its line; hover a line for its length. The board's shapes have
     pointer-events: none (the holder takes the pointer), so the pointer is hit-tested against the SVG geometry. */
  var tip = document.createElement("div");
  tip.id = "pc-hover-tip";
  tip.className = "pc-hover-tip";
  tip.setAttribute("role", "status");
  tip.hidden = true;
  document.body.appendChild(tip);

  function clearHover() {
    holder.querySelectorAll(".highlighted").forEach(function (n) { n.classList.remove("highlighted"); });
    tip.hidden = true;
  }
  function letterOf(node) {
    var m = (node.getAttribute("class") || "").match(/hr-c-([A-Za-z])/);
    return m ? m[1] : "";
  }
  function lineName(svg, letter) {
    var port = svg.querySelector("g.hr-port.hr-c-" + letter + " title");
    return port ? port.textContent.replace(/ (source|sink) port$/, "") : letter;
  }
  function distToSegment(p, a, b) {
    var dx = b[0] - a[0];
    var dy = b[1] - a[1];
    var t = dx || dy ? Math.max(0, Math.min(1, ((p.x - a[0]) * dx + (p.y - a[1]) * dy) / (dx * dx + dy * dy))) : 0;
    return Math.hypot(p.x - (a[0] + t * dx), p.y - (a[1] + t * dy));
  }
  function lineCells(group) {
    var pipe = group.querySelector(".hr-pipe");
    var raw = ((pipe && pipe.getAttribute("points")) || "").trim();
    if (!raw) return [];
    return raw.split(/\s+/).map(function (pair) { return pair.split(",").map(Number); });
  }
  holder.addEventListener("mousemove", function (e) {
    var svg = boardSvg();
    if (!svg || !svg.getScreenCTM || e.buttons) { clearHover(); return; }
    var pt = svg.createSVGPoint();
    pt.x = e.clientX;
    pt.y = e.clientY;
    var p = pt.matrixTransform(svg.getScreenCTM().inverse());
    var letter = "";
    var what = "";
    svg.querySelectorAll("g.hr-port").forEach(function (g) {
      var box = g.getBBox();
      if (p.x >= box.x && p.x <= box.x + box.width && p.y >= box.y && p.y <= box.y + box.height) { letter = letterOf(g); what = "port"; }
    });
    if (!letter) {
      svg.querySelectorAll("#hr-lines g.hr-line[data-line]").forEach(function (g) {
        var cells = lineCells(g);
        for (var i = 0; i + 1 < cells.length; i++) {
          if (distToSegment(p, cells[i], cells[i + 1]) < 10) { letter = g.getAttribute("data-line"); what = "line"; return; }
        }
      });
    }
    clearHover();
    if (!letter) return;
    var group = svg.querySelector('#hr-lines g.hr-line[data-line="' + letter + '"]');
    var count = group ? lineCells(group).length : 0;
    svg.querySelectorAll("g.hr-port.hr-c-" + letter).forEach(function (g) { g.classList.add("highlighted"); });
    if (group) group.classList.add("highlighted");
    tip.textContent = lineName(svg, letter) + " line " + letter + ": " + (count > 1 ? count + " cells" : "not drawn yet") + (what === "port" ? ". Its twin port is lit." : "");
    tip.style.left = (e.clientX + 14) + "px";
    tip.style.top = (e.clientY + 14) + "px";
    tip.hidden = false;
  });
  holder.addEventListener("mouseleave", clearHover);

  /* R4-HRPC-6: C (with the board focused) pulses the cells no line covers yet. The dots live in CSS, so a redraw keeps the pulse. */
  holder.addEventListener("keydown", function (e) {
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    if (e.key === "c" || e.key === "C") holder.classList.toggle("pulse-on");
  });

  /* R4-HRPC-7: when the result card appears (the room is patched or restored) the lines draw in order. Never with reduced motion. */
  var lastReplayed = null;
  function replay() {
    var layer = holder.querySelector("#hr-lines");
    if (!layer || reducedMotion() || root.getAttribute("data-effects") === "off") return;
    var groups = layer.querySelectorAll("g.hr-line");
    if (!groups.length) return;
    groups.forEach(function (g, i) {
      g.style.setProperty("--i", i);
      g.querySelectorAll(".hr-pipe, .hr-core").forEach(function (n) { n.setAttribute("pathLength", "1"); });
    });
    layer.classList.add("hr-replaying");
    function stop() {
      layer.classList.remove("hr-replaying");
      layer.removeEventListener("animationend", done);
      holder.removeEventListener("pointerdown", stop);
    }
    function done(ev) {
      var all = layer.querySelectorAll("g.hr-line");
      if (!all.length || ev.target === all[all.length - 1].querySelector(".hr-core")) stop();
    }
    layer.addEventListener("animationend", done);
    holder.addEventListener("pointerdown", stop);   // drawing again always ends the replay at once
  }
  var card = document.getElementById("result-card");
  if (card) {
    new MutationObserver(function () {
      if (card.hidden) { lastReplayed = null; return; }
      if (lastReplayed !== card.className) { lastReplayed = card.className; replay(); }
    }).observe(card, { attributes: true, attributeFilter: ["hidden", "class"] });
  }

  /* R4-HRPC-9: board size slider and the F focus key (hides the side column and the stats strip) */
  var tools = document.createElement("div");
  tools.className = "pc-board-tools";
  tools.innerHTML = '<label for="board-scale-slider">Board size</label>' +
    '<input type="range" id="board-scale-slider" min="0.6" max="1.4" step="0.05" value="1">' +
    '<button type="button" id="focus-button" aria-pressed="false">Focus: hide side panels (F)</button>';
  var side = document.getElementById("pc-side");
  if (side) side.insertBefore(tools, side.firstChild);
  var slider = document.getElementById("board-scale-slider");
  var focusBtn = document.getElementById("focus-button");
  var exitBtn = document.createElement("button");
  exitBtn.type = "button";
  exitBtn.id = "focus-exit-button";
  exitBtn.className = "pc-focus-exit";
  exitBtn.textContent = "Show panels (F)";
  exitBtn.hidden = true;
  document.body.appendChild(exitBtn);
  function setScale(v) {
    var n = Math.max(0.6, Math.min(1.4, Number(v) || 1));
    root.style.setProperty("--board-scale", String(n));
    if (slider) slider.value = String(n);
    lsSet("hull-repair-pc-scale", String(n));
  }
  function setFocus(on) {
    root.classList.toggle("focus-mode", on);
    exitBtn.hidden = !on;
    if (focusBtn) focusBtn.setAttribute("aria-pressed", on ? "true" : "false");
  }
  setScale(lsGet("hull-repair-pc-scale") || 1);
  if (slider) slider.addEventListener("input", function () { setScale(slider.value); });
  if (focusBtn) focusBtn.addEventListener("click", function () { setFocus(true); exitBtn.focus(); });
  exitBtn.addEventListener("click", function () { setFocus(false); });
  document.addEventListener("keydown", function (e) {
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    var t = e.target && e.target.tagName;
    if (t === "INPUT" || t === "TEXTAREA" || t === "SELECT" || (e.target && e.target.isContentEditable)) return;
    if (e.key === "f" || e.key === "F") setFocus(!root.classList.contains("focus-mode"));
  });

  /* R4-HRPC-4: Tab on the board picks the next unjoined line (Shift+Tab the previous one); app.js does the picking, so the
     arrow keys, Backspace, Enter and Escape keep their meaning from the Classic layout. When no further line is left, Tab is
     not intercepted, so keyboard focus can always leave the board. */
  holder.addEventListener("keydown", function (e) {
    if (e.key !== "Tab" || e.ctrlKey || e.metaKey || e.altKey) return;
    if (typeof window.hullRepairPickLine !== "function") return;
    if (window.hullRepairPickLine(e.shiftKey ? -1 : 1)) e.preventDefault();
  });

  /* R4-HRPC-10: the station map as a keyboard grid. Each room becomes a button (roving tabindex); arrows move,
     Enter or Space opens the room. The map is redrawn by the game, so the rooms are prepared again after every redraw. */
  var mapHolder = document.getElementById("map-holder");
  function rooms() { return Array.prototype.slice.call(mapHolder.querySelectorAll("g.hr-room[data-id]")); }
  function prepareRooms() {
    var list = rooms();
    var keep = mapHolder.querySelector('g.hr-room[tabindex="0"]');
    list.forEach(function (g, i) {
      var t = g.querySelector("title");
      g.setAttribute("role", "button");
      g.setAttribute("aria-label", t ? t.textContent : g.getAttribute("data-id"));
      g.setAttribute("tabindex", (keep ? g === keep : i === 0) ? "0" : "-1");
    });
  }
  function neighbour(from, key) {
    var list = rooms();
    var i = list.indexOf(from);
    if (key === "ArrowRight") return list[Math.min(i + 1, list.length - 1)];
    if (key === "ArrowLeft") return list[Math.max(i - 1, 0)];
    var a = from.getBoundingClientRect();
    var best = null;
    var bestScore = Infinity;
    list.forEach(function (g) {
      var b = g.getBoundingClientRect();
      var dy = key === "ArrowDown" ? b.top - a.top : a.top - b.top;
      if (dy < 5) return;
      var score = dy * 1000 + Math.abs((b.left + b.width / 2) - (a.left + a.width / 2));
      if (score < bestScore) { bestScore = score; best = g; }
    });
    return best || from;
  }
  if (mapHolder) {
    new MutationObserver(prepareRooms).observe(mapHolder, { childList: true });
    prepareRooms();
    mapHolder.addEventListener("keydown", function (e) {
      var room = e.target.closest ? e.target.closest("g.hr-room[data-id]") : null;
      if (!room) return;
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        room.dispatchEvent(new MouseEvent("click", { bubbles: true }));
      } else if (e.key.indexOf("Arrow") === 0) {
        e.preventDefault();
        var next = neighbour(room, e.key);
        rooms().forEach(function (g) { g.setAttribute("tabindex", g === next ? "0" : "-1"); });
        next.focus();
      }
    });
  }
});
