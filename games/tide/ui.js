/* Tide, page-level helpers shared by the Classic and Desktop pages. No game state here (that is
   all in game.py): this file only clicks buttons the game already wires up, moves keyboard focus
   between coastline rows, and remembers which <details> panels were left open.

   D-14  Game keys: A advance, X advance up to 5 quiet seasons, 1/2/3 invest, R session report,
         L Harbor Ledger. Listed in the shared "?" overlay (index.html passes them as `extra`).
   D-7   Arrow keys (and Home/End) move keyboard focus around the coastline tiles, row by row and
         column by column (one Tab stop per row, every tile focusable and labelled).
   D-21  Graph crosshair: hover, tap or Left/Right on a focused graph shows a vertical line and
         a readout for that season (the text comes from game.py in the graph's data-crosshair).
   D-27  Each <details> panel remembers its open/closed state across reloads (this browser only).
   D-12  Dashboard: choose, pin and reorder the main panels (Standard, Compact, Analyst and Postcard presets),
         remembered in localStorage. Classic page only.
   D-26  Phone view: a Coast / Meters / Log switch (All is the default and hides nothing) that a swipe left
         or right also moves, and a tap on a coastline tile writes that row's note under the grid. */
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

  // ---- D-30 pause the looping animations while nobody is looking, or when the device is low on power ----
  // Sets data-anim-paused on <html>; style.css turns every animation off under it. Both signals only ever
  // pause: the page works the same with them unavailable.
  var lowPower = false;
  function syncAnimationPause() {
    var paused = document.visibilityState === "hidden" || lowPower;
    document.documentElement.setAttribute("data-anim-paused", paused ? "true" : "false");
  }
  document.addEventListener("visibilitychange", syncAnimationPause);
  if (navigator.getBattery) {
    navigator.getBattery().then(function (battery) {
      function update() { lowPower = !battery.charging && battery.level <= 0.2; syncAnimationPause(); }
      battery.addEventListener("levelchange", update);
      battery.addEventListener("chargingchange", update);
      update();
    }).catch(function () { /* no battery info: only the hidden-tab rule applies */ });
  }
  syncAnimationPause();



  // ---- D-12 dashboard: show, pin and reorder the main panels ---------------------------------------
  // Six panels, each one or two existing elements. Hiding is a data attribute (CSS: display none) and ordering moves the
  // real elements between two comment markers, so game.py keeps finding every id and the default order is untouched until
  // a player chooses something. Pinned panels always sit above the others. Never applied on the Desktop page, where the
  // same panels are windows.
  const DASH_KEY = "tide-dashboard-v1";
  const DASH_PANELS = [
    { id: "meters", label: "Status, meters and ticker", sel: ["#status"] },
    { id: "sea", label: "Sea level and adaptation", sel: ["#sea-level-section"] },
    { id: "coast", label: "Coastline", sel: [".coastline-scene", "#community-index"] },
    { id: "compare", label: "Then vs. now", sel: ["#coastline-comparison"] },
    { id: "settlement", label: "Settlement and chronicle", sel: ["#settlement-section"] },
    { id: "programmes", label: "Coastal programmes", sel: ["#programmes-section"] },
  ];
  const DASH_DEFAULT_ORDER = DASH_PANELS.map(function (panel) { return panel.id; });
  const DASH_PRESETS = {
    standard: { label: "Standard", note: "Every panel, in the original order.", order: DASH_DEFAULT_ORDER.slice(), hidden: [], pinned: [] },
    compact: {
      label: "Compact", note: "Coastline, meters and programmes; the rest is hidden.",
      order: ["coast", "meters", "programmes", "sea", "compare", "settlement"], hidden: ["sea", "compare", "settlement"], pinned: [],
    },
    analyst: {
      label: "Analyst", note: "Every panel, numbers first: meters and sea level pinned on top, then then-vs-now.",
      order: ["meters", "sea", "compare", "coast", "programmes", "settlement"], hidden: [], pinned: ["meters", "sea"],
    },
    postcard: {
      label: "Postcard", note: "A scenic view: coastline, then-vs-now and the chronicle. Meters, sea level and programmes are hidden.",
      order: ["coast", "compare", "settlement", "meters", "sea", "programmes"], hidden: ["meters", "sea", "programmes"], pinned: ["coast"],
    },
  };
  let dash = null;       // {preset, order, hidden, pinned}
  let dashMarkers = null; // {start, end}

  function dashClone(preset, name) {
    const p = DASH_PRESETS[preset];
    return { preset: name || preset, order: p.order.slice(), hidden: p.hidden.slice(), pinned: p.pinned.slice() };
  }

  // Anything unreadable or unknown falls back to Standard; unknown ids are dropped and missing ones appended.
  function dashClean(raw) {
    if (!raw || typeof raw !== "object") return dashClone("standard");
    const known = function (list) {
      const out = [];
      (Array.isArray(list) ? list : []).forEach(function (id) {
        if (DASH_DEFAULT_ORDER.indexOf(id) >= 0 && out.indexOf(id) < 0) out.push(id);
      });
      return out;
    };
    const order = known(raw.order);
    DASH_DEFAULT_ORDER.forEach(function (id) { if (order.indexOf(id) < 0) order.push(id); });
    const preset = typeof raw.preset === "string" && (raw.preset === "custom" || DASH_PRESETS[raw.preset]) ? raw.preset : "custom";
    return { preset: preset, order: order, hidden: known(raw.hidden), pinned: known(raw.pinned) };
  }

  function dashLoad() {
    let raw = null;
    try { raw = JSON.parse(safeGet(DASH_KEY) || "null"); } catch (e) { raw = null; }
    return dashClean(raw);
  }

  // Pinned panels first (in the saved order), then the rest.
  function dashDisplayOrder(d) {
    return d.order.filter(function (id) { return d.pinned.indexOf(id) >= 0; })
      .concat(d.order.filter(function (id) { return d.pinned.indexOf(id) < 0; }));
  }

  function dashElements(panel) {
    return panel.sel.map(function (selector) { return document.querySelector(selector); }).filter(Boolean);
  }

  function dashEnsureMarkers() {
    if (dashMarkers) return dashMarkers;
    const first = document.querySelector(DASH_PANELS[0].sel[0]);
    const lastEls = dashElements(DASH_PANELS[DASH_PANELS.length - 1]);
    const last = lastEls[lastEls.length - 1];
    if (!first || !last || first.parentNode !== last.parentNode) return null;
    const start = document.createComment("dashboard-start");
    const end = document.createComment("dashboard-end");
    first.parentNode.insertBefore(start, first);
    last.parentNode.insertBefore(end, last.nextSibling);
    dashMarkers = { start: start, end: end };
    return dashMarkers;
  }

  function dashApply() {
    if (document.documentElement.getAttribute("data-layout") === "pc") return;
    const markers = dashEnsureMarkers();
    if (markers) {
      dashDisplayOrder(dash).forEach(function (id) {
        const panel = DASH_PANELS.filter(function (p) { return p.id === id; })[0];
        dashElements(panel).forEach(function (el) { markers.end.parentNode.insertBefore(el, markers.end); });
      });
    }
    DASH_PANELS.forEach(function (panel) {
      const hide = dash.hidden.indexOf(panel.id) >= 0;
      dashElements(panel).forEach(function (el) {
        if (hide) el.setAttribute("data-dash-hidden", "true"); else el.removeAttribute("data-dash-hidden");
      });
    });
  }

  function dashSave() {
    safeSet(DASH_KEY, JSON.stringify(dash));
    dashApply();
    dashRender();
  }

  function dashSetPreset(name) {
    dash = dashClone(name);
    dashSave();
  }

  function dashEdited() {
    // A manual change turns the preset into "custom" unless it still matches one exactly.
    dash.preset = "custom";
    Object.keys(DASH_PRESETS).forEach(function (name) {
      const p = DASH_PRESETS[name];
      const same = function (a, b) { return JSON.stringify(a.slice().sort()) === JSON.stringify(b.slice().sort()); };
      if (JSON.stringify(dash.order) === JSON.stringify(p.order) && same(dash.hidden, p.hidden) && same(dash.pinned, p.pinned)) dash.preset = name;
    });
    dashSave();
  }

  function dashLabel() {
    return dash.preset === "custom" ? "Custom" : DASH_PRESETS[dash.preset].label;
  }

  function dashButton(text, label, pressed, onClick, disabled) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "secondary dashboard-small";
    button.textContent = text;
    button.setAttribute("aria-label", label);
    if (pressed !== null) button.setAttribute("aria-pressed", pressed ? "true" : "false");
    if (disabled) button.disabled = true;
    button.addEventListener("click", onClick);
    return button;
  }

  function dashRender() {
    const toggle = document.getElementById("dashboard-toggle-button");
    const panel = document.getElementById("dashboard-panel");
    if (!toggle || !panel || !dash) return;
    const hiddenCount = dash.hidden.length;
    toggle.textContent = "🧩 Dashboard: " + dashLabel();
    const note = document.getElementById("dashboard-note");
    if (note) note.textContent = hiddenCount ? hiddenCount + (hiddenCount === 1 ? " panel is" : " panels are") + " hidden." : "";
    const showAll = document.getElementById("dashboard-show-all");
    if (showAll) showAll.hidden = hiddenCount === 0;
    if (panel.hidden) return;

    const focused = document.activeElement && panel.contains(document.activeElement) ? document.activeElement.getAttribute("data-dash-focus") : null;
    panel.textContent = "";
    const heading = document.createElement("h2");
    heading.className = "settings-panel-heading";
    heading.textContent = "Dashboard";
    panel.appendChild(heading);
    const intro = document.createElement("p");
    intro.className = "comparison-message";
    intro.textContent = "Choose which panels to show, pin the ones you want on top and move the rest up or down. Saved in this browser only. The Desktop layout keeps its own windows.";
    panel.appendChild(intro);

    const presets = document.createElement("div");
    presets.className = "graph-controls";
    presets.setAttribute("role", "group");
    presets.setAttribute("aria-label", "Dashboard presets");
    Object.keys(DASH_PRESETS).forEach(function (name) {
      const button = dashButton(DASH_PRESETS[name].label, "Use the " + DASH_PRESETS[name].label + " preset. " + DASH_PRESETS[name].note,
        dash.preset === name, function () { dashSetPreset(name); announceDash("Dashboard preset " + DASH_PRESETS[name].label + ". " + DASH_PRESETS[name].note); });
      button.classList.add("graph-chip");
      button.setAttribute("data-dash-focus", "preset-" + name);
      presets.appendChild(button);
    });
    panel.appendChild(presets);
    const presetNote = document.createElement("p");
    presetNote.className = "comparison-message";
    presetNote.textContent = dash.preset === "custom" ? "Custom: your own choices." : DASH_PRESETS[dash.preset].label + ": " + DASH_PRESETS[dash.preset].note;
    panel.appendChild(presetNote);

    const list = document.createElement("ol");
    list.className = "dashboard-list";
    const shown = dashDisplayOrder(dash);
    shown.forEach(function (id, index) {
      const def = DASH_PANELS.filter(function (p) { return p.id === id; })[0];
      const pinned = dash.pinned.indexOf(id) >= 0;
      const hidden = dash.hidden.indexOf(id) >= 0;
      const row = document.createElement("li");
      row.className = "dashboard-row" + (hidden ? " dashboard-row--hidden" : "");
      const check = document.createElement("label");
      check.className = "dashboard-show";
      const box = document.createElement("input");
      box.type = "checkbox";
      box.checked = !hidden;
      box.setAttribute("data-dash-focus", "show-" + id);
      box.addEventListener("change", function () {
        dash.hidden = box.checked ? dash.hidden.filter(function (x) { return x !== id; }) : dash.hidden.concat([id]);
        dashEdited();
        announceDash(def.label + (box.checked ? " shown." : " hidden."));
      });
      check.appendChild(box);
      check.appendChild(document.createTextNode(" " + def.label + (hidden ? " (hidden)" : "")));
      row.appendChild(check);
      const pin = dashButton(pinned ? "📌 Pinned" : "📌 Pin", (pinned ? "Unpin " : "Pin ") + def.label + (pinned ? "" : " to the top"), pinned, function () {
        dash.pinned = pinned ? dash.pinned.filter(function (x) { return x !== id; }) : dash.pinned.concat([id]);
        dashEdited();
        announceDash(def.label + (pinned ? " unpinned." : " pinned to the top."));
      });
      pin.setAttribute("data-dash-focus", "pin-" + id);
      row.appendChild(pin);
      // Moving works inside the pinned group or the unpinned group, in the full saved order.
      const group = shown.filter(function (x) { return (dash.pinned.indexOf(x) >= 0) === pinned; });
      const at = group.indexOf(id);
      const move = function (delta) {
        const neighbour = group[at + delta];
        const i = dash.order.indexOf(id);
        const j = dash.order.indexOf(neighbour);
        dash.order[i] = neighbour;
        dash.order[j] = id;
        dashEdited();
        announceDash(def.label + " moved " + (delta < 0 ? "up" : "down") + ".");
      };
      const up = dashButton("▲", "Move " + def.label + " up", null, function () { move(-1); }, at === 0);
      up.setAttribute("data-dash-focus", "up-" + id);
      const down = dashButton("▼", "Move " + def.label + " down", null, function () { move(1); }, at === group.length - 1);
      down.setAttribute("data-dash-focus", "down-" + id);
      row.appendChild(up);
      row.appendChild(down);
      list.appendChild(row);
    });
    panel.appendChild(list);
    const live = document.createElement("p");
    live.id = "dashboard-live";
    live.className = "sr-only";
    live.setAttribute("role", "status");
    live.setAttribute("aria-live", "polite");
    panel.appendChild(live);
    if (dashAnnouncement) { live.textContent = dashAnnouncement; dashAnnouncement = ""; }
    if (focused) {
      const again = panel.querySelector('[data-dash-focus="' + focused + '"]');
      if (again && !again.disabled) again.focus();
      else {
        const fallback = panel.querySelector('[data-dash-focus="' + focused.replace(/^(up|down)-/, "pin-") + '"]');
        if (fallback) fallback.focus();
      }
    }
  }

  let dashAnnouncement = "";
  function announceDash(text) {
    dashAnnouncement = text;
    const live = document.getElementById("dashboard-live");
    if (live) { live.textContent = ""; live.textContent = text; dashAnnouncement = ""; }
  }

  function initDashboard() {
    const toggle = document.getElementById("dashboard-toggle-button");
    const panel = document.getElementById("dashboard-panel");
    if (!toggle || !panel) return;
    dash = dashLoad();
    toggle.addEventListener("click", function () {
      panel.hidden = !panel.hidden;
      toggle.setAttribute("aria-expanded", panel.hidden ? "false" : "true");
      dashRender();
    });
    const showAll = document.getElementById("dashboard-show-all");
    if (showAll) showAll.addEventListener("click", function () {
      dash.hidden = [];
      dashEdited();
    });
    dashApply();
    dashRender();
    window.TideDashboard = { panels: DASH_PANELS, presets: DASH_PRESETS, current: function () { return JSON.parse(JSON.stringify(dash)); } };
  }

  // ---- D-26 phone view: All / Coast / Meters / Log, swipe between them, tap a tile for its note -----
  const MVIEW_ORDER = ["coast", "meters", "log"];
  const MVIEW_LABEL = { all: "Everything", coast: "Coast", meters: "Meters", log: "Log" };
  const MVIEW_KEY = "tide-mobile-view";
  const phoneQuery = window.matchMedia ? window.matchMedia("(max-width: 640px)") : null;

  function phoneViewUsable() {
    const bar = document.getElementById("mobile-views");
    return Boolean(bar && phoneQuery && phoneQuery.matches && document.documentElement.getAttribute("data-layout") !== "pc");
  }

  function setMobileView(view, announce) {
    if (view !== "all" && MVIEW_ORDER.indexOf(view) < 0) view = "all";
    document.documentElement.setAttribute("data-mview-active", view);
    document.querySelectorAll("[data-mview-pick]").forEach(function (button) {
      button.setAttribute("aria-pressed", button.getAttribute("data-mview-pick") === view ? "true" : "false");
    });
    safeSet(MVIEW_KEY, view);
    const status = document.getElementById("mobile-view-status");
    if (status && announce) {
      status.textContent = view === "all" ? "Showing everything." : "Showing " + MVIEW_LABEL[view] + ". Swipe left or right for the next part.";
    }
  }

  function initMobileViews() {
    const bar = document.getElementById("mobile-views");
    if (!bar) return;
    bar.addEventListener("click", function (event) {
      const button = event.target.closest ? event.target.closest("[data-mview-pick]") : null;
      if (button) setMobileView(button.getAttribute("data-mview-pick"), true);
    });
    const saved = safeGet(MVIEW_KEY);
    setMobileView(saved && (saved === "all" || MVIEW_ORDER.indexOf(saved) >= 0) ? saved : "all", false);
  }

  // A swipe moves one step along Coast, Meters, Log. It does nothing on "All", and it never starts on
  // something that already scrolls or drags sideways (graphs, sliders, text fields, tables).
  const SWIPE_BLOCK = "input, select, textarea, svg[data-crosshair], .mini-graph, table, [role=slider], #actions-dock, #kb-shortcuts-panel, dialog";
  let swipeStart = null;

  function scrollsSideways(node) {
    for (let el = node; el && el !== document.body && el.nodeType === 1; el = el.parentElement) {
      const style = window.getComputedStyle(el);
      if ((style.overflowX === "auto" || style.overflowX === "scroll") && el.scrollWidth > el.clientWidth + 2) return true;
    }
    return false;
  }

  function onSwipeStart(event) {
    swipeStart = null;
    if (!phoneViewUsable() || event.touches.length !== 1) return;
    const view = document.documentElement.getAttribute("data-mview-active");
    if (view === "all" || !view) return;
    const target = event.target;
    if (target && target.closest && target.closest(SWIPE_BLOCK)) return;
    if (scrollsSideways(target)) return;
    const touch = event.touches[0];
    swipeStart = { x: touch.clientX, y: touch.clientY, time: Date.now() };
  }

  function onSwipeEnd(event) {
    const start = swipeStart;
    swipeStart = null;
    if (!start || !event.changedTouches.length) return;
    const touch = event.changedTouches[0];
    const dx = touch.clientX - start.x;
    const dy = touch.clientY - start.y;
    if (Date.now() - start.time > 900 || Math.abs(dx) < 60 || Math.abs(dx) < Math.abs(dy) * 1.6) return;
    const at = MVIEW_ORDER.indexOf(document.documentElement.getAttribute("data-mview-active"));
    const next = at + (dx < 0 ? 1 : -1);
    if (at < 0 || next < 0 || next >= MVIEW_ORDER.length) return;
    setMobileView(MVIEW_ORDER[next], true);
    const bar = document.getElementById("mobile-views");
    // Leave room for the fixed funds / acidity / yield strip at the top of the screen.
    if (bar && window.scrollTo) window.scrollTo(0, Math.max(0, bar.getBoundingClientRect().top + window.pageYOffset - 52));
  }

  // Native tooltips never show on a touch screen, so a tap on a coastline tile writes the same note here.
  function onTileTap(event) {
    const tile = event.target && event.target.closest ? event.target.closest(".coastline-tile") : null;
    const grid = tile ? tile.closest("#coastline-grid") : null;
    if (!tile || !grid) return;
    let readout = document.getElementById("coastline-tap-readout");
    if (!readout) {
      readout = document.createElement("p");
      readout.id = "coastline-tap-readout";
      readout.className = "comparison-message coastline-tap-readout";
      readout.setAttribute("role", "status");
      grid.parentNode.insertBefore(readout, grid.nextSibling);
    }
    readout.textContent = tile.title || tile.getAttribute("aria-label") || "";
  }

  document.addEventListener("touchstart", onSwipeStart, { passive: true });
  document.addEventListener("touchend", onSwipeEnd, { passive: true });
  document.addEventListener("click", onTileTap);
  if (phoneQuery && phoneQuery.addEventListener) phoneQuery.addEventListener("change", function () {
    if (!phoneQuery.matches) document.documentElement.removeAttribute("data-mview-active");
    else initMobileViews();
  });

  // The grid is rebuilt on every render, so a tapped note would go stale: clear it when the tiles are replaced.
  function watchTileNote() {
    const grid = document.getElementById("coastline-grid");
    if (!grid || !window.MutationObserver) return;
    new MutationObserver(function () {
      const readout = document.getElementById("coastline-tap-readout");
      if (readout) readout.textContent = "";
    }).observe(grid, { childList: true });
  }

  function initPage() { restoreDetails(); initDashboard(); initMobileViews(); watchTileNote(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initPage);
  else initPage();
})();

