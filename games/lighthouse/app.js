/* Lighthouse view: glue only. The engine (game.py and its modules) holds every rule; this file draws what
   handle() returns and forwards what the player does. No game logic lives here (the one exception is the oil
   estimate in the evening plan, which only repeats the engine's published burn rates as a hint). */
(function () {
  "use strict";
  var ENGINE_MODULES = ["rng.py", "data.py", "clock.py", "weather.py", "ships.py", "state.py", "sim.py", "day.py", "achievements.py", "goals.py", "lore.py", "cast.py", "story.py", "mysteries.py", "unease.py", "info.py", "view.py"];
  var STORE_KEY = "lighthouse:state";
  var QUIET_KEY = "lighthouse-quiet";
  var EERIE_KEY = "lighthouse-eerie";
  var NOTE_KEY = "lighthouse-content-note";
  var GAME_ID = "lighthouse";
  var BASE_MS = 4000;
  var SVG_NS = "http://www.w3.org/2000/svg";

  var $ = function (id) { return document.getElementById(id); };
  var engine = null;     // { handle, getState, loadState }
  var view = null;
  var busy = false;
  var knownEarned = null;
  var lastPhase = null;
  var lastLogCount = 0;
  var orderDraft = null;
  var reducedMotion = false;

  function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* convenience only */ } }
  function lsRemove(k) { try { localStorage.removeItem(k); } catch (e) { /* convenience only */ } }

  // ---- small helpers ---------------------------------------------------------------------------------
  function el(tag, text, className) {
    var node = document.createElement(tag);
    if (text !== undefined && text !== null) node.textContent = text;
    if (className) node.className = className;
    return node;
  }
  function svgEl(tag, attrs) {
    var node = document.createElementNS(SVG_NS, tag);
    Object.keys(attrs || {}).forEach(function (k) { node.setAttribute(k, attrs[k]); });
    return node;
  }
  function setText(node, text) { if (node.textContent !== text) node.textContent = text; }
  function setEnabled(node, enabled) {
    if (typeof node === "string") node = $(node);
    if (enabled) node.removeAttribute("aria-disabled"); else node.setAttribute("aria-disabled", "true");
  }
  function isOff(btn) { return btn.disabled || btn.getAttribute("aria-disabled") === "true"; }
  function guard(id, handler) { $(id).addEventListener("click", function () { if (!isOff($(id))) handler(); }); }
  function announce(text) {
    var live = $("announce");
    live.textContent = "";
    setTimeout(function () { live.textContent = text; }, 40);
  }
  function showToast(text) {
    var toast = $("toast");
    toast.textContent = toast.textContent ? toast.textContent + " " + text : text;
    setTimeout(function () { if (toast.textContent.indexOf(text) !== -1) toast.textContent = ""; }, 6000);
  }
  // Rebuild a group only when WHAT it holds changes, so a focused control survives the redraw that follows
  // every tick and every action.
  function fillOnce(container, signature, build) {
    if (container.dataset.signature === signature) return false;
    container.textContent = "";
    build(container);
    container.dataset.signature = signature;
    return true;
  }
  function plural(n, one, many) { return n + " " + (n === 1 ? one : (many || one + "s")); }
  function clockLabel(startMin, tickMin, tick) {
    var m = (startMin + tick * tickMin) % 1440;
    return ("0" + Math.floor(m / 60)).slice(-2) + ":" + ("0" + (m % 60)).slice(-2);
  }
  function lerp(a, b, t) { return a + (b - a) * t; }
  function hexToRgb(h) { return [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)]; }
  function mix(h1, h2, t) {
    var a = hexToRgb(h1), b = hexToRgb(h2);
    return "#" + [0, 1, 2].map(function (i) { return ("0" + Math.round(lerp(a[i], b[i], t)).toString(16)).slice(-2); }).join("");
  }
  function isLight() { return document.documentElement.getAttribute("data-theme") === "light"; }

  // ---- scene palettes (dark theme; the light theme uses a paler day-scene variant) -------------------------
  var PAL = {
    dark: {
      day: { top: "#5fb4e8", mid: "#9bd3f2", low: "#d7eefa", sea: "#2b86b0", sea2: "#1c6489" },
      dusk: { top: "#2a2d66", mid: "#8a4f7d", low: "#f0996a", sea: "#223a62", sea2: "#16264a" },
      dawn: { top: "#3a5894", mid: "#d99a88", low: "#ffd9a0", sea: "#34507a", sea2: "#20365a" },
      night: { top: "#060a1a", mid: "#0d1836", low: "#19294e", sea: "#0a1c32", sea2: "#050f1c" },
      ink: { moon: "#f4efd8", sun: "#ffe9a8", wave: "#5b8db3", tower: "#eeeae0", band: "#b8402f", dark: "#56626e", rock: "#222d37", rockLine: "#364554", ship: "#10181f", shipLine: "#9db4c6", fog: "#cfd9e2", fogWash: "#9aa9b9", rain: "#b9d6ee", haze: "#b8c4d0", lanternOff: "#34414c", lanternOn: "#ffe08a", dock: "#7a5a3a" },
    },
    light: {
      day: { top: "#9fd2f2", mid: "#c6e6f8", low: "#eef8fd", sea: "#5fa8cc", sea2: "#3f86ae" },
      dusk: { top: "#8e8fc4", mid: "#d6a3b8", low: "#f6c8a0", sea: "#6d8fb8", sea2: "#4d6e98" },
      dawn: { top: "#8fb0e0", mid: "#efc3b0", low: "#fde6c2", sea: "#7a9cc4", sea2: "#587aa4" },
      night: { top: "#506a9a", mid: "#6f8ab8", low: "#a6bddc", sea: "#4f7aa6", sea2: "#35597f" },
      ink: { moon: "#fffaf0", sun: "#ffd966", wave: "#2e5f86", tower: "#fbf8f0", band: "#b8402f", dark: "#3b4752", rock: "#4a5864", rockLine: "#2f3b46", ship: "#1c2833", shipLine: "#0f1a22", fog: "#ffffff", fogWash: "#dfe8f0", rain: "#2f5d86", haze: "#e4edf4", lanternOff: "#6b7a87", lanternOn: "#ffd45c", dock: "#6a4a2a" },
    },
  };

  function scenePalette(v) {
    var set = PAL[isLight() ? "light" : "dark"];
    var base, deep = 0;
    if (v.phase === "night") {
      base = v.tick < v.length / 2 ? set.dusk : set.dawn;
      deep = Math.pow(v.darkness, 0.8);
    } else if (v.phase === "evening") { base = set.dusk; deep = 0.12; }
    else if (v.phase === "morning") { base = set.dawn; deep = 0; }
    else { base = set.day; deep = 0; }
    var k = ["top", "mid", "low", "sea", "sea2"];
    var out = {};
    k.forEach(function (name) { out[name] = deep ? mix(base[name], set.night[name], deep) : base[name]; });
    out.ink = set.ink;
    return out;
  }

  // ---- the scene -------------------------------------------------------------------------------------
  var shipNodes = {};
  var starsBuilt = false;
  var KIND_LANE = { fisher: 296, ferry: 282, cargo: 258, yacht: 306, mail: 290 };
  var HULLS = {
    fisher: [["path", { d: "M-22 0 L22 0 L16 10 L-16 10 Z" }], ["path", { d: "M0 -30 L16 -4 L0 -4 Z" }], ["path", { d: "M0 -32 L0 0" }]],
    ferry: [["path", { d: "M-34 0 L34 0 L28 11 L-28 11 Z" }], ["rect", { x: -20, y: -14, width: 40, height: 14 }], ["rect", { x: -4, y: -25, width: 8, height: 11 }]],
    cargo: [["path", { d: "M-48 0 L48 0 L42 12 L-42 12 Z" }], ["rect", { x: -42, y: -13, width: 16, height: 13 }], ["rect", { x: -24, y: -13, width: 16, height: 13 }], ["rect", { x: -6, y: -13, width: 16, height: 13 }], ["rect", { x: 26, y: -20, width: 14, height: 20 }]],
    yacht: [["path", { d: "M-24 0 L24 0 L14 8 L-18 8 Z" }], ["path", { d: "M-2 -44 L-2 -3 L20 -3 Z" }], ["path", { d: "M-5 -36 L-5 -3 L-24 -3 Z" }]],
    mail: [["path", { d: "M-26 0 L26 0 L20 9 L-20 9 Z" }], ["rect", { x: -10, y: -13, width: 20, height: 13 }], ["path", { d: "M12 -13 L12 -30" }]],
  };

  function buildStars() {
    if (starsBuilt) return;
    starsBuilt = true;
    var g = $("stars"), seed = 7;
    function rnd() { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed / 0x7fffffff; }
    for (var i = 0; i < 46; i++) {
      var x = rnd() * 900, y = rnd() * 190;
      if (x > 640 && x < 760 && y > 60) continue;
      g.appendChild(svgEl("circle", { cx: x.toFixed(1), cy: y.toFixed(1), r: (0.7 + rnd() * 1.1).toFixed(2), fill: "#fff" }));
    }
  }

  function shipNode(ship) {
    var g = svgEl("g", { class: "ship", "data-id": ship.id });
    var title = svgEl("title"); title.textContent = ship.label + " " + ship.name; g.appendChild(title);
    var body = svgEl("g", { class: "ship-body" });
    var inner = svgEl("g", { class: "ship-inner" });
    HULLS[ship.kind].forEach(function (part) {
      var shape = svgEl(part[0], Object.assign({ "stroke-width": 2, "stroke-linejoin": "round" }, part[1]));
      shape.style.fill = "var(--ship-fill, #10181f)"; shape.style.stroke = "var(--ship-line, #9db4c6)";
      inner.appendChild(shape);
    });
    body.appendChild(inner);
    g.appendChild(body);
    var mark = svgEl("text", { class: "ship-flag", x: 0, y: -50, "text-anchor": "middle" });
    mark.textContent = "";
    g.appendChild(mark);
    if (ship.kind === "mail") {
      var env = svgEl("text", { class: "ship-flag", x: 12, y: -33, "text-anchor": "middle" }); env.textContent = "✉"; g.appendChild(env);
    }
    return { g: g, inner: inner, mark: mark, body: body };
  }

  function renderShips(v) {
    var layer = $("ships-layer");
    var live = {};
    v.ships.forEach(function (s) { if (s.present) live[s.id] = s; });
    Object.keys(shipNodes).forEach(function (id) {
      if (!live[id]) { layer.removeChild(shipNodes[id].g); delete shipNodes[id]; }
    });
    var ink = scenePalette(v).ink;
    Object.keys(live).forEach(function (id) {
      var s = live[id];
      var node = shipNodes[id];
      if (!node) {
        node = shipNodes[id] = shipNode(s);
        node.g.style.transform = "translate(" + (s.dir > 0 ? -60 : 960) + "px," + KIND_LANE[s.kind] + "px)";
        layer.appendChild(node.g);
        // force a style flush so the first move animates from the edge
        void node.g.getBoundingClientRect();
      }
      var x = s.dir > 0 ? -60 + s.pos * 1020 : 960 - s.pos * 1020;
      node.g.style.transform = "translate(" + x.toFixed(1) + "px," + KIND_LANE[s.kind] + "px)";
      node.inner.setAttribute("transform", "scale(" + s.dir + ",1)");
      node.g.classList.toggle("lit", s.lit);
      setText(node.mark, s.lit ? "◉" : "");
      var fog = view && view.cond === 2;
      node.body.style.opacity = fog && !s.lit ? "0.55" : "1";
      node.g.style.setProperty("--ship-fill", ink.ship);
      node.g.style.setProperty("--ship-line", ink.shipLine);
    });
  }

  function describeScene(v) {
    var parts = [];
    if (v.phase === "night") {
      parts.push("Night " + v.night + ", " + v.clock + ". " + v.cond_label + ", wind " + v.wind + " of 4.");
      if (!v.beam.lit) parts.push("The lamp is out.");
      else parts.push("Lamp " + v.beam.level_label.toLowerCase() + ", the beam reaches " + v.beam.reach + (v.beam.stopped ? " and is fixed because the clockwork has stopped." : " and is sweeping."));
      var near = v.ships.filter(function (s) { return s.present; }).map(function (s) { return s.label + " " + s.name + (s.lit ? " (in the beam)" : ""); });
      if (near.length) parts.push("Ships near: " + near.join(", ") + ".");
      if (v.story.odd && v.story.odd.some(function (o) { return o.light; })) parts.push("A small steady light that is on no chart shows far off on the water.");
    } else if (v.phase === "evening") parts.push("Evening on the rock. The lamp is not yet lit.");
    else if (v.phase === "morning") parts.push("Dawn over the rock.");
    else parts.push("Daylight on the rock.");
    return parts.join(" ");
  }

  function renderScene(v) {
    buildStars();
    var svg = $("scene");
    var pal = scenePalette(v);
    var set = [["--sky-top", pal.top], ["--sky-mid", pal.mid], ["--sky-low", pal.low], ["--sea-top", pal.sea], ["--sea-low", pal.sea2],
      ["--moon", pal.ink.moon], ["--sun", pal.ink.sun], ["--wave-ink", pal.ink.wave], ["--tower", pal.ink.tower], ["--tower-band", pal.ink.band],
      ["--tower-dark", pal.ink.dark], ["--rock", pal.ink.rock], ["--rock-line", pal.ink.rockLine], ["--fog-ink", pal.ink.fog], ["--fog-wash", pal.ink.fogWash],
      ["--rain-ink", pal.ink.rain], ["--haze-ink", pal.ink.haze], ["--dock", pal.ink.dock]];
    set.forEach(function (p) { svg.style.setProperty(p[0], p[1]); });
    var night = v.phase === "night", evening = v.phase === "evening", day = v.phase === "day";
    var fogged = v.cond >= 2;
    var starOp = night ? Math.pow(v.darkness, 1.6) * (fogged ? 0.2 : 1) : evening ? 0.25 : 0;
    $("stars").style.opacity = isLight() ? starOp * 0.25 : starOp;
    $("moon").style.opacity = night ? Math.min(0.9, v.darkness * (fogged ? 0.3 : 1)) : evening ? 0.35 : 0;
    $("sun").style.opacity = day ? 1 : v.phase === "morning" ? 0.55 : 0;
    $("haze-layer").style.opacity = v.cond === 1 ? 0.8 : v.cond >= 3 ? 0.55 : 0;
    $("fog-layer").style.opacity = v.cond === 2 ? 0.8 : v.cond >= 3 ? 0.25 : 0;
    $("fog-wash").style.opacity = v.cond === 2 ? 0.34 : v.cond === 4 ? 0.2 : 0;
    $("rain-layer").style.opacity = v.cond === 3 ? 0.4 : v.cond === 4 ? 0.8 : 0;
    $("fog-layer").classList.toggle("drifting", v.cond === 2 && !reducedMotion);
    $("rain-layer").classList.toggle("falling", v.cond >= 3 && !reducedMotion);
    $("dock-rect").style.opacity = v.structure[3].value < 30 ? 0.45 : 1;
    // waves heave with the wind
    var k = 1 + v.wind * 0.35, bases = [238, 268, 312];
    ["wave-row-1", "wave-row-2", "wave-row-3"].forEach(function (cls, i) {
      var path = document.querySelector("." + cls + " path");
      if (path) path.setAttribute("transform", "translate(0," + bases[i] + ") scale(1," + k.toFixed(2) + ") translate(0," + (-bases[i]) + ")");
    });
    // lantern and beam
    var lit = v.beam.lit;
    var glassOn = lit ? pal.ink.lanternOn : pal.ink.lanternOff;
    $("lantern-glass").style.fill = glassOn;
    var level = { dim: 0.35, standard: 0.55, bright: 0.8, storm: 1 }[v.beam.level] || 0;
    $("lantern-glow").style.opacity = lit ? level : 0;
    var beam = $("beam"), poly = $("beam-poly"), edge = $("beam-edge");
    var reach = v.beam.reach;
    if (lit && reach > 0) {
      var L = Math.round(reach * 52), w = Math.round(L * 0.13);
      poly.setAttribute("points", "700,119 " + (700 - L) + "," + (119 - w) + " " + (700 - L) + "," + (119 + w));
      poly.style.opacity = v.beam.stopped ? 0.55 : 0.85;
      poly.setAttribute("stroke", v.beam.stopped ? "#fff3c4" : "none");
      poly.setAttribute("stroke-dasharray", v.beam.stopped ? "8 6" : "none");
      poly.setAttribute("stroke-width", v.beam.stopped ? "3" : "0");
      var sweeping = !v.beam.stopped && !reducedMotion && v.phase === "night";
      beam.classList.toggle("sweeping", sweeping);
      if (!sweeping) beam.style.transform = "rotate(-14deg)"; else beam.style.transform = "";
      // reduce motion: a tick mark at the far end of the cone shows where the sweep would be
      if (reducedMotion && !v.beam.stopped) {
        var off = Math.sin(v.tick * 0.9) * w * 0.8;
        edge.setAttribute("points", (700 - L) + "," + (119 + off - 7) + " " + (700 - L) + "," + (119 + off + 7));
        edge.style.opacity = 1;
      } else edge.style.opacity = 0;
      var pool = $("light-pool");
      pool.setAttribute("cx", 700 - L * 0.8); pool.setAttribute("cy", 262);
      pool.setAttribute("rx", Math.max(18, L * 0.16)); pool.setAttribute("ry", 16);
      pool.style.opacity = 0.7;
    } else {
      poly.style.opacity = 0; edge.style.opacity = 0; beam.classList.remove("sweeping");
      $("light-pool").style.opacity = 0;
    }
    renderShips(v);
    $("scene").setAttribute("aria-label", describeScene(v));
    // caption tags: icon + word, never colour alone
    setText($("cap-weather"), night ? v.cond_icon + " " + v.cond_label : "");
    setText($("cap-wind"), night ? "Wind " + v.wind + " of 4" : "");
    setText($("cap-beam"), night ? (lit ? "Beam: " + v.beam.level_label + ", reach " + reach + (v.beam.stopped ? " (fixed)" : "") : "Lamp out") : "");
    setText($("cap-clock"), night ? v.clock : "");
  }

  // ---- status strip ----------------------------------------------------------------------------------
  function meter(id, pct, state) {
    var m = $(id);
    m.setAttribute("data-state", state);
    m.firstElementChild.style.setProperty("--pct", Math.max(0, Math.min(100, pct)) + "%");
  }
  function renderHud(v) {
    setText($("hud-night"), String(v.night));
    setText($("hud-season"), v.season + " " + v.night_in_season + " of 10" + (v.mode === "endless" ? ", year " + v.year : ""));
    setText($("hud-clock"), v.phase === "night" ? v.clock : v.phase === "evening" ? clockLabel(v.start_min, v.tick_minutes, 0) : "--:--");
    var oilPct = v.oil / v.oil_cap * 100;
    var oilState = v.oil <= 0 ? "empty" : oilPct < 20 ? "low" : "ok";
    setText($("hud-oil"), String(Math.round(v.oil)));
    meter("hud-oil-meter", oilPct, oilState);
    setText($("hud-oil-state"), oilState === "empty" ? "Empty" : oilState === "low" ? "Low" : oilPct > 60 ? "Plenty" : "Enough");
    setText($("hud-energy"), String(v.energy));
    var eState = v.energy < 20 ? "low" : "ok";
    meter("hud-energy-meter", v.energy, eState);
    setText($("hud-energy-state"), v.energy < 20 ? "Tired" : v.energy < 50 ? "Weary" : "Rested");
    setText($("hud-rep"), String(v.reputation));
    setText($("hud-rep-title"), v.rep_title + (v.rep_next ? " (next at " + v.rep_next.at + ")" : ""));
    setText($("hud-salvage"), String(v.salvage));
  }

  function renderGoals(v) {
    var holder = $("goals-list");
    fillOnce(holder, JSON.stringify(v.goals), function (h) {
      v.goals.forEach(function (g) {
        var li = el("li"); li.dataset.done = String(g.done);
        li.appendChild(el("span", g.label, "goal-label"));
        var m = el("span", null, "meter"); m.setAttribute("data-state", g.done ? "ok" : "ok");
        var f = el("span", null, "meter-fill"); f.style.setProperty("--pct", Math.round(g.have / g.need * 100) + "%"); m.appendChild(f);
        li.appendChild(m);
        li.appendChild(el("span", g.have + " of " + g.need, "goal-num"));
        h.appendChild(li);
      });
    });
  }


  // ---- letters, sailors, gifts, the room ------------------------------------------------------------------
  function roomPart(tag, attrs, cls) { var n = svgEl(tag, attrs); if (cls) n.setAttribute("class", cls); return n; }
  var GIFT_DRAW = {
    brass_key: function (x, y) { var g = svgEl("g"); g.appendChild(roomPart("circle", { cx: x, cy: y - 10, r: 5 }, "room-accent")); g.appendChild(roomPart("path", { d: "M" + x + " " + (y - 5) + " V" + y + " M" + x + " " + (y - 2) + " h4" }, "room-ink")); return g; },
    odd_cork: function (x, y) { var g = svgEl("g"); g.appendChild(roomPart("rect", { x: x - 5, y: y - 11, width: 10, height: 11, rx: 2 }, "room-accent")); return g; },
    pressed_flower: function (x, y) { var g = svgEl("g"); g.appendChild(roomPart("path", { d: "M" + x + " " + y + " V" + (y - 11) }, "room-ink")); g.appendChild(roomPart("circle", { cx: x, cy: y - 13, r: 4 }, "room-accent")); return g; },
    lens_cloth: function (x, y) { var g = svgEl("g"); g.appendChild(roomPart("path", { d: "M" + (x - 8) + " " + y + " q4 -12 8 -4 q4 -8 8 4 z" }, "room-fill")); return g; },
    tin_fish: function (x, y) { var g = svgEl("g"); g.appendChild(roomPart("rect", { x: x - 9, y: y - 9, width: 18, height: 9, rx: 2 }, "room-fill")); g.appendChild(roomPart("path", { d: "M" + (x - 4) + " " + (y - 5) + " q4 -4 8 0 q-4 4 -8 0" }, "room-ink")); return g; },
    walnuts: function (x, y) { var g = svgEl("g"); g.appendChild(roomPart("rect", { x: x - 6, y: y - 16, width: 12, height: 16, rx: 3 }, "room-fill")); g.appendChild(roomPart("rect", { x: x - 7, y: y - 19, width: 14, height: 4, rx: 1 }, "room-accent")); return g; },
    biscuits: function (x, y) { var g = svgEl("g"); g.appendChild(roomPart("rect", { x: x - 12, y: y - 12, width: 24, height: 12, rx: 2 }, "room-accent")); g.appendChild(roomPart("path", { d: "M" + (x - 12) + " " + (y - 8) + " h24" }, "room-ink")); return g; },
    chart: function (x, y) { var g = svgEl("g"); g.appendChild(roomPart("rect", { x: x - 18, y: y, width: 36, height: 26 }, "room-fill")); g.appendChild(roomPart("path", { d: "M" + (x - 12) + " " + (y + 18) + " q6 -14 12 -4 t12 -6" }, "room-ink")); g.appendChild(roomPart("circle", { cx: x + 6, cy: y + 8, r: 2 }, "room-accent")); return g; },
    pip_drawing: function (x, y) { var g = svgEl("g"); g.appendChild(roomPart("rect", { x: x - 14, y: y, width: 28, height: 28 }, "room-fill")); g.appendChild(roomPart("path", { d: "M" + (x - 4) + " " + (y + 24) + " L" + (x - 2) + " " + (y + 6) + " h4 L" + (x + 4) + " " + (y + 24) + " z M" + (x - 1) + " " + (y + 10) + " h2 M" + (x - 1) + " " + (y + 14) + " h2 M" + (x - 1) + " " + (y + 18) + " h2" }, "room-ink")); return g; },
    postcard: function (x, y) { var g = svgEl("g"); g.appendChild(roomPart("rect", { x: x - 12, y: y, width: 24, height: 17 }, "room-fill")); g.appendChild(roomPart("path", { d: "M" + (x - 7) + " " + (y + 8) + " h8 M" + (x - 7) + " " + (y + 12) + " h12" }, "room-ink")); return g; },
    stair_shell: function (x, y) { var g = svgEl("g"); g.appendChild(roomPart("path", { d: "M" + x + " " + y + " v14" }, "room-ink")); g.appendChild(roomPart("path", { d: "M" + (x - 6) + " " + (y + 26) + " q0 -12 6 -12 q6 0 6 12 q-6 4 -12 0 z M" + (x - 3) + " " + (y + 22) + " h6" }, "room-accent")); return g; },
  };
  var SLOT_POS = { shelf: function (i) { return [100 + i * 30, 88]; }, table: function (i) { return [168 + i * 34, 150]; }, wall: function (i) { return [70 + i * 52, 22]; }, window: function () { return [276, 36]; }, floor: function (i) { return [60 + i * 30, 185]; } };

  function drawRoom(v) {
    var svg = $("room-svg");
    svg.textContent = "";
    svg.appendChild(roomPart("rect", { x: 0, y: 0, width: 360, height: 140 }, "room-wall"));
    svg.appendChild(roomPart("rect", { x: 0, y: 140, width: 360, height: 60 }, "room-floor"));
    var win = roomPart("g");
    win.appendChild(roomPart("rect", { x: 240, y: 16, width: 72, height: 70 }, "room-fill"));
    win.appendChild(roomPart("path", { d: "M276 16 V86 M240 51 H312" }, "room-ink"));
    svg.appendChild(win);
    svg.appendChild(roomPart("path", { d: "M80 92 H210" }, "room-ink"));                               // the shelf
    svg.appendChild(roomPart("path", { d: "M150 150 H300 M158 150 V196 M292 150 V196" }, "room-ink"));   // the table
    svg.appendChild(roomPart("path", { d: "M20 150 H64 M20 150 V196 M64 150 V196 M20 128 H64 V150" }, "room-ink"));   // the bed
    var chair = roomPart("g", { id: "room-chair", class: "room-chair" });
    chair.appendChild(roomPart("path", { d: "M318 190 V160 H338 V190 M318 160 V140 H328" }, "room-ink"));
    svg.appendChild(chair);
    var ro = v.story.room_odd || { chair: 0, cup: false };
    var chairG = $("room-chair");
    if (ro.chair) chairG.setAttribute("transform", "rotate(" + ro.chair + " 328 175)");
    if (ro.cup) {
      var cup = roomPart("g", { class: "odd-detail" });
      cup.appendChild(roomPart("path", { d: "M222 150 v-12 h14 v12 z M236 142 q6 0 0 6" }, "room-fill"));
      svg.appendChild(cup);
    }
    var used = {};
    v.story.room.forEach(function (gid) {
      var g = v.story.gifts.filter(function (x) { return x.id === gid; })[0];
      if (!g || !GIFT_DRAW[gid]) return;
      var i = used[g.slot] = (used[g.slot] || 0) + 1;
      var pos = SLOT_POS[g.slot](i - 1);
      var node = GIFT_DRAW[gid](pos[0], pos[1]);
      var t = svgEl("title"); t.textContent = g.name; node.insertBefore(t, node.firstChild);
      svg.appendChild(node);
    });
    $("room-svg").setAttribute("aria-label", "The keeper's room" + (v.story.room.length ? ", with " + v.story.room.length + " keepsake" + (v.story.room.length === 1 ? "" : "s") : ", still bare"));
  }

  function letterItem(l) {
    var li = el("li"); li.dataset.read = String(l.read);
    var head = el("div", null, "letter-head");
    head.appendChild(el("strong", l.from_name + ": " + l.subject));
    head.appendChild(el("span", "night " + l.night, "note"));
    if (!l.read) head.appendChild(el("span", "New", "letter-new"));
    li.appendChild(head);
    if (!l.read) {
      var open = el("button", "Open the letter"); open.type = "button";
      open.addEventListener("click", function () { var r = send({ action: "read_letter", id: l.id }, false); if (r && r.message) { showToast(r.message); announce(r.message); } });
      li.appendChild(open);
      return li;
    }
    li.appendChild(el("p", l.text, "letter-text"));
    if (l.gift) li.appendChild(el("p", "In the envelope: " + l.gift.name + ".", "letter-gift"));
    if (l.reply) {
      li.appendChild(el("p", "You answered: " + l.reply, "letter-reply"));
      li.appendChild(el("p", l.answer ? l.from_name + " writes back: " + l.answer : "Your reply goes out with the next boat.", l.answer ? "letter-answer" : "note"));
    } else if (l.replies.length) {
      var row = el("div", null, "reply-buttons"); row.setAttribute("role", "group"); row.setAttribute("aria-label", "Reply to " + l.from_name);
      l.replies.forEach(function (r) {
        var b = el("button", r.label); b.type = "button";
        b.addEventListener("click", function () { var res = send({ action: "reply", id: l.id, reply: r.id }, false); if (res && res.message) announce(res.message); });
        row.appendChild(b);
      });
      li.appendChild(row);
    }
    return li;
  }

  var KIND_WORD = { odd: "Odd", moment: "The moment", kind: "Kind", resolve: "Explained" };
  function renderNotebook(s) {
    var nb = s.notebook;
    setText($("notebook-counts"), "Mysteries solved " + nb.mysteries.filter(function (m) { return m.solved; }).length + " of " + nb.mysteries_total + ". Small oddities explained " + nb.trifles.filter(function (t) { return t.explained; }).length + " of " + nb.trifles_total + ".");
    fillOnce($("notebook-list"), JSON.stringify(nb.mysteries), function (h) {
      nb.mysteries.forEach(function (m) {
        var li = el("li"); li.dataset.begun = String(m.begun); li.dataset.solved = String(m.solved);
        var head = el("div"); head.appendChild(el("strong", m.title));
        head.appendChild(el("span", m.solved ? "Solved" : m.begun ? "Still a mystery" : "", "nb-status"));
        li.appendChild(head);
        if (m.summary) li.appendChild(el("p", m.summary, "note"));
        if (m.entries.length) {
          var ol = el("ol");
          m.entries.forEach(function (e) {
            var item = el("li"); item.appendChild(el("span", KIND_WORD[e.kind] + ", night " + e.night + ": ", "nb-technique")); item.appendChild(document.createTextNode(e.text));
            ol.appendChild(item);
          });
          li.appendChild(ol);
        }
        h.appendChild(li);
      });
    });
    fillOnce($("oddities-list"), JSON.stringify(nb.trifles), function (h) {
      nb.trifles.forEach(function (t) {
        var li = el("li"); li.dataset.begun = "true"; li.dataset.solved = String(t.explained);
        li.appendChild(el("div", t.odd + " (night " + t.night + ")"));
        li.appendChild(el("div", t.explained ? "Explained: " + t.resolve : "Not explained yet.", "note"));
        h.appendChild(li);
      });
    });
  }
  function renderOdd(s) {
    var layer = $("off-chart");
    var want = {};
    (s.odd || []).forEach(function (o) { if (o.light || o.phantom) want[o.mystery] = o; });
    Array.prototype.slice.call(layer.children).forEach(function (n) { if (!want[n.dataset.mystery]) layer.removeChild(n); });
    Object.keys(want).forEach(function (m) {
      var o = want[m], node = layer.querySelector('[data-mystery="' + m + '"]');
      if (!node) {
        node = svgEl("g", { "data-mystery": m, class: "odd-light odd-detail" });
        if (o.phantom) {
          var hull = svgEl("g", { opacity: 0.55 });
          hull.appendChild(svgEl("path", { d: "M-70 0 L70 0 L60 14 L-60 14 Z", style: "fill: var(--ship-fill, #10181f); stroke: var(--ship-line, #9db4c6)", "stroke-width": 2 }));
          hull.appendChild(svgEl("rect", { x: -48, y: -16, width: 96, height: 16, style: "fill: var(--ship-fill, #10181f); stroke: var(--ship-line, #9db4c6)", "stroke-width": 2 }));
          for (var w = 0; w < 12; w++) hull.appendChild(svgEl("rect", { x: -44 + w * 8, y: -11, width: 4, height: 6, style: "fill: var(--on, #ffd866)" }));
          node.appendChild(hull);
        } else {
          node.appendChild(svgEl("circle", { r: 11, fill: "url(#glow-grad)", opacity: 0.7 }));
          node.appendChild(svgEl("circle", { r: 3.4, style: "fill: var(--on, #ffd866)" }));
        }
        layer.appendChild(node);
      }
      if (o.phantom) node.setAttribute("transform", "translate(" + o.phantom[0] + "," + o.phantom[1] + ") scale(" + o.phantom[2] + ")");
      else node.setAttribute("transform", "translate(" + o.light[0] + "," + o.light[1] + ")");
      node.classList.toggle("blinking", Boolean(o.blink));
    });
  }

  var knownUnread = null;
  function renderStory(v) {
    var s = v.story;
    $("letters-toggle-button").hidden = !s.on;
    if (!s.on) { $("letters-panel").hidden = true; setToggleState("letters-toggle-button", "letters-panel"); return; }
    $("letters-toggle-button").textContent = s.unread ? "Letters (" + s.unread + " new)" : "Letters";
    if (knownUnread !== null && s.unread > knownUnread) showToast("A letter has come.");
    knownUnread = s.unread;
    setText($("letters-counts"), "Sailors met " + s.counts.met + " of " + s.counts.sailors + ". Letters read " + s.counts.letters + " of " + s.counts.letters_total + ". Gifts found " + s.counts.gifts + " of " + s.counts.gifts_total + ".");
    $("letters-empty").hidden = s.inbox.length > 0;
    fillOnce($("letters-list"), JSON.stringify(s.inbox), function (h) { s.inbox.forEach(function (l) { h.appendChild(letterItem(l)); }); });
    fillOnce($("sailors-list"), JSON.stringify(s.sailors), function (h) {
      s.sailors.forEach(function (x) {
        var li = el("li"); li.dataset.met = String(x.met);
        li.appendChild(el("span", x.name, "sailor-name"));
        if (x.met) {
          li.appendChild(el("div", x.role, "note"));
          li.appendChild(el("div", x.blurb));
          li.appendChild(el("div", (x.ashore ? "Writes from ashore. " : "Boat got safely by " + plural(x.passes, "time") + ". ") + "Letters: " + x.letters_got + " of " + x.letters, "note"));
        } else li.appendChild(el("div", "Not met yet.", "note"));
        h.appendChild(li);
      });
    });
    fillOnce($("gifts-list"), JSON.stringify(s.gifts), function (h) {
      s.gifts.forEach(function (g) {
        var li = el("li"); li.dataset.have = String(g.have);
        li.appendChild(el("strong", g.have || g.ever ? g.name : "Not found yet"));
        if (g.have) li.appendChild(el("div", g.text, "note"));
        h.appendChild(li);
      });
    });
    renderNotebook(s);
    renderOdd(s);
    fillOnce($("room-svg"), JSON.stringify([s.room, s.room_odd]), function () { drawRoom(v); });
    setText($("room-text"), s.room.length ? "Everything on the shelf, the table and the walls came in an envelope." : "Nothing on the shelf yet. Letters sometimes bring something small.");
  }

  // ---- the evening -----------------------------------------------------------------------------------
  var LEVEL_IDS = ["dim", "standard", "bright", "storm"];
  function buildPlan(v) {
    fillOnce($("plan-blocks"), "plan", function (holder) {
      v.blocks.forEach(function (name, b) {
        var row = el("div", null, "block-row");
        row.appendChild(el("span", name, "block-name"));
        row.id = "plan-block-" + b;
        var seg = el("div", null, "seg");
        seg.setAttribute("role", "group");
        seg.setAttribute("aria-label", "Lamp level for " + name.toLowerCase());
        v.level_options.forEach(function (opt) {
          var btn = el("button", opt.label);
          btn.type = "button";
          btn.dataset.level = opt.id;
          btn.dataset.block = String(b);
          btn.appendChild(el("small", "reach " + opt.reach + ", oil " + opt.burn.toFixed(1) + "/tick"));
          btn.addEventListener("click", function () {
            var levels = view.plan.levels.slice();
            levels[b] = opt.id;
            send({ action: "plan", levels: levels });
          });
          seg.appendChild(btn);
        });
        row.appendChild(seg);
        holder.appendChild(row);
      });
    });
    v.plan.levels.forEach(function (lvl, b) {
      $("plan-block-" + b).querySelectorAll("button").forEach(function (btn) {
        btn.setAttribute("aria-pressed", String(btn.dataset.level === lvl));
      });
    });
  }

  function blockSizes(length) {
    var ends = [0, 1, 2].map(function (b) { return b < 2 ? Math.floor((length * (b + 1) + 2) / 3) : length; });
    return [ends[0], ends[1] - ends[0], ends[2] - ends[1]];
  }
  function estimate(v) {
    var sizes = blockSizes(v.length), total = 0, dryAt = null, left = v.oil, tick = 0;
    for (var b = 0; b < 3; b++) {
      var burn = v.level_options[LEVEL_IDS.indexOf(v.plan.levels[b])].burn;
      for (var i = 0; i < sizes[b]; i++) {
        var rate = v.plan.ration && total >= v.plan.ration ? v.level_options[0].burn : burn;
        left -= rate; total += rate; tick++;
        if (left <= 0 && dryAt === null) dryAt = tick;
      }
    }
    return { total: Math.round(total), dryAt: dryAt };
  }

  function renderEvening(v) {
    setText($("evening-night"), String(v.night));
    setText($("evening-note"), (v.festival ? "Tonight is the Lamplighters' Supper: every boat stays in harbour. " : "") + v.season + ", night " + v.night_in_season + " of 10. The night is " + (v.length * v.tick_minutes / 60).toFixed(1).replace(".0", "") + " hours long.");
    // barometer
    var f = v.forecast, labels = ["Calm", "Unsettled", "Rough", "Dangerous"];
    var scale = $("barometer-scale");
    fillOnce(scale, "scale", function (holder) {
      labels.forEach(function (name) {
        var cell = el("div", null, "scale-cell");
        cell.appendChild(el("span", "", "scale-mark"));
        cell.appendChild(document.createTextNode(name));
        holder.appendChild(cell);
      });
    });
    Array.prototype.forEach.call(scale.children, function (cell, i) {
      var inside = i >= f.lo && i <= f.hi;
      cell.dataset.in = String(inside);
      cell.firstElementChild.textContent = inside ? "●" : "○";
    });
    scale.setAttribute("aria-label", "Barometer: " + (f.narrow ? f.lo_label : f.lo_label + " to " + f.hi_label));
    setText($("barometer-text"), (f.narrow ? "The glass points to " + f.lo_label.toLowerCase() + " weather." : "The glass says " + f.lo_label.toLowerCase() + " to " + f.hi_label.toLowerCase() + ".") +
      (f.vane ? " With the wind vane it is right about 19 nights in 20." : " It is right about 9 nights in 10, so treat it as a hint."));
    // harbour board
    var list = $("board-list");
    fillOnce(list, JSON.stringify(v.notice) + v.plan.levels.join(), function (holder) {
      v.notice.forEach(function (n) {
        var li = el("li");
        li.appendChild(el("span", n.icon, "ico"));
        li.lastChild.setAttribute("aria-hidden", "true");
        li.appendChild(el("strong", n.label + " " + n.name));
        if (n.who_name) li.appendChild(el("span", n.who_name, "sailor-note"));
        if (n.chalked) li.className = "odd-detail";
        li.appendChild(el("span", "about " + n.at + " (" + n.block_label.toLowerCase() + "), needs reach " + n.need + " or more" + (n.chalked ? " (chalked on the board)" : ""), "board-detail"));
        holder.appendChild(li);
      });
      if (!v.notice.length) holder.appendChild(el("li", "No ships are expected tonight."));
    });
    setText($("board-note"), "The weather takes reach away: haze 1, fog 2, squall 2, storm 3. A cracked lantern glass takes 1 or 2 more.");
    buildPlan(v);
    var est = estimate(v);
    var msg = "About " + est.total + " measures of oil if the plan holds (you have " + Math.round(v.oil) + ").";
    if (est.dryAt !== null) msg += " That is not enough: the lamp would go out about " + clockLabel(v.start_min, v.tick_minutes, est.dryAt) + ".";
    setText($("plan-estimate"), msg);
    $("ration-select").value = String(v.plan.ration);
    if ($("ration-select").value !== String(v.plan.ration)) {
      var opt = el("option", v.plan.ration + " measures"); opt.value = String(v.plan.ration); $("ration-select").appendChild(opt); $("ration-select").value = String(v.plan.ration);
    }
    ["wind", "watch", "repair"].forEach(function (t) { $("task-" + t).checked = Boolean(v.plan.tasks[t]); });
    var focus = $("focus-select");
    fillOnce(focus, "focus", function (holder) {
      var worst = el("option", "the worst part first"); worst.value = "worst"; holder.appendChild(worst);
      v.structure.forEach(function (p) { var o = el("option", "the " + p.label.toLowerCase()); o.value = p.id; holder.appendChild(o); });
    });
    focus.value = v.plan.focus;
    var notes = [];
    if (v.boat.tonight) notes.push(v.structure[3].value < 30 ? "The mail boat is due tonight but the dock is too damaged for her to tie up." : "The mail boat is due tonight with your order.");
    if (v.supplies[0].count === 0) notes.push("The larder is empty: you will go hungry tomorrow.");
    if (v.structure[1].value < 50) notes.push("The lantern glass is cracked, so the beam is shorter than the table says.");
    if (v.structure[0].value < 40) notes.push("The tower is shaken: the clockwork will run down faster.");
    if (v.tired) notes.push("You are tired. Rest in the day if you can.");
    setText($("evening-reminders"), notes.join(" "));
  }

  // ---- the night -------------------------------------------------------------------------------------
  function renderNight(v) {
    fillOnce($("lamp-controls"), "lamp", function (holder) {
      v.level_options.forEach(function (opt, i) {
        var btn = el("button", (i + 1) + " " + opt.label);
        btn.type = "button";
        btn.dataset.level = opt.id;
        btn.title = "Reach " + opt.reach + ", oil " + opt.burn.toFixed(1) + " per tick (key " + (i + 1) + ")";
        btn.addEventListener("click", function () { if (!isOff(btn)) send({ action: "level", level: opt.id }); });
        holder.appendChild(btn);
      });
    });
    Array.prototype.forEach.call($("lamp-controls").children, function (btn) {
      btn.setAttribute("aria-pressed", String(v.beam.level === btn.dataset.level));
      setEnabled(btn, v.oil > 0);
    });
    var pct = v.clockwork.left / v.clockwork.max * 100;
    meter("clock-meter", pct, v.beam.stopped ? "empty" : pct < 25 ? "low" : "ok");
    setText($("clock-state"), v.beam.stopped ? "Stopped: the beam holds a fixed cone" : Math.round(v.clockwork.left) + " of " + v.clockwork.max + " ticks left");
    setEnabled("wind-button", v.clockwork.left < v.clockwork.max - 1);
    $("incident-row").hidden = !v.incident;
    if (v.incident) setText($("incident-text"), v.incident.text + " (" + plural(v.incident.left, "tick") + " before it costs you)");
    var patch = $("patch-select");
    var damaged = v.structure.filter(function (p) { return p.value < 100; });
    fillOnce(patch, damaged.map(function (p) { return p.id; }).join(), function (holder) {
      damaged.forEach(function (p) { var o = el("option", p.label); o.value = p.id; holder.appendChild(o); });
      if (!damaged.length) { var none = el("option", "Nothing needs patching"); none.value = ""; holder.appendChild(none); }
    });
    setEnabled("patch-button", damaged.length > 0);
    // ships
    var ships = $("ship-list");
    fillOnce(ships, JSON.stringify(v.ships.map(function (s) { return [s.id, s.state, s.arrived, s.lit, s.present]; })), function (holder) {
      v.ships.forEach(function (s) {
        var li = el("li");
        li.dataset.lit = String(s.lit);
        var icon = el("span", s.icon, "ico"); icon.setAttribute("aria-hidden", "true");
        li.appendChild(icon);
        li.appendChild(el("strong", s.label + " " + s.name));
        if (s.who_name) li.appendChild(el("span", s.who_name, "sailor-note"));
        var status = s.state !== "pending" ? { passed: "Passed safely", delayed: "Turned back", damaged: "On the shoals, safe" }[s.state] :
          s.present ? (s.lit ? "Near the rock, in the beam" : "Near the rock, looking for the light") : "Expected about " + s.at;
        var st = el("span", status, "ship-state");
        st.dataset.state = s.state === "pending" && s.present ? "pending" : s.state;
        li.appendChild(st);
        holder.appendChild(li);
      });
      if (!v.ships.length) holder.appendChild(el("li", "No ships tonight."));
    });
    setText($("night-note"), v.beam.lit ? "" : "The lamp is out. Ships cannot see you until morning.");
  }

  // ---- the morning -----------------------------------------------------------------------------------
  function fact(label, value) {
    var d = el("div"); d.appendChild(el("dt", label)); d.appendChild(el("dd", String(value))); return d;
  }
  function renderMorning(v) {
    var r = v.report;
    if (!r) return;
    setText($("morning-night"), String(r.night));
    setText($("report-summary"), r.summary);
    var ships = $("report-ships");
    fillOnce(ships, JSON.stringify(r.ships), function (holder) {
      r.ships.forEach(function (s) {
        var li = el("li");
        li.appendChild(el("strong", s.name));
        var st = el("span", { passed: "Passed safely", delayed: "Turned back to wait", damaged: "Ran on the shoals; everyone is safe", unrecorded: "Never came" }[s.outcome], "ship-state");
        st.dataset.state = s.outcome;
        li.appendChild(st);
        holder.appendChild(li);
      });
      if (!r.ships.length) holder.appendChild(el("li", "No ships came by."));
    });
    var facts = $("report-facts");
    fillOnce(facts, JSON.stringify([r.lamp_hours, r.oil_used, r.damage, r.rep, r.salvage, r.incidents]), function (holder) {
      holder.appendChild(fact("Lamp-hours", r.lamp_hours));
      holder.appendChild(fact("Oil burnt", r.oil_used));
      holder.appendChild(fact("Damage taken", r.damage));
      holder.appendChild(fact("Reputation", (r.rep >= 0 ? "+" : "") + r.rep));
      holder.appendChild(fact("Salvage", "+" + r.salvage));
      holder.appendChild(fact("Troubles", r.incidents));
    });
    var lines = $("report-lines");
    fillOnce(lines, JSON.stringify(r.lines), function (holder) { r.lines.forEach(function (t) { holder.appendChild(el("li", t)); }); });
    var beats = $("report-beats");
    fillOnce(beats, JSON.stringify(r.beats || []) + String(v.story.on), function (h) {
      (r.beats || []).forEach(function (b) {
        var odd = b.kind === "odd" || b.kind === "moment" || b.kind === "trifle";
        h.appendChild(el("li", b.text, odd ? "odd-detail" : "story-line"));
      });
    });
    beats.hidden = !v.story.on || !(r.beats || []).length;
    var post = $("report-letters");
    var postText = (r.letters || []).map(function (l) { return "A letter from " + l.from_name + " has come: " + l.subject + "."; }).concat((r.met || []).map(function (n) { return "You have met " + n + "."; })).join(" ");
    setText(post, postText); post.hidden = !postText || !v.story.on;
    setText($("report-delivery"), v.delivery ? v.delivery.text : (v.boat.due ? "The mail boat could not land and will come again." : ""));
  }

  // ---- the day ---------------------------------------------------------------------------------------
  function costText(cost) { return Object.keys(cost).map(function (k) { return cost[k] + " " + k; }).join(" + "); }
  function canAfford(v, cost) { return Object.keys(cost).every(function (k) { return v.supplies.filter(function (s) { return s.id === k; })[0].count >= cost[k]; }); }
  function renderDay(v) {
    setText($("day-night"), String(v.night));
    setText($("day-slots"), "Daylight left: " + v.day.slots + " of " + v.day.max_slots + " tasks");
    var list = $("repair-list");
    fillOnce(list, "repair", function (holder) {
      v.structure.forEach(function (p) {
        var li = el("li"); li.dataset.part = p.id;
        var name = el("span"); name.appendChild(el("strong", p.icon + " " + p.label)); name.appendChild(el("span", "", "cost"));
        li.appendChild(name);
        var m = el("span", null, "meter"); m.appendChild(el("span", null, "meter-fill")); li.appendChild(m);
        var btn = el("button", "Mend"); btn.type = "button";
        btn.addEventListener("click", function () { if (!isOff(btn)) daySend({ action: "day", task: "repair", part: p.id }); });
        li.appendChild(btn);
        holder.appendChild(li);
      });
    });
    v.structure.forEach(function (p, i) {
      var li = list.children[i];
      var cost = v.day.repair_cost[p.id];
      meter(li.querySelector(".meter").id || (li.querySelector(".meter").id = "repair-meter-" + p.id), p.value, p.state === "failing" ? "empty" : p.state === "poor" ? "low" : "ok");
      setText(li.querySelector(".cost"), " " + p.value + "/100 (" + costText(cost) + ")" + (v.day.repaired.indexOf(p.id) !== -1 ? " mended today" : ""));
      var btn = li.querySelector("button");
      setEnabled(btn, v.day.slots > 0 && p.value < 100 && canAfford(v, cost));
    });
    var tasks = $("task-buttons");
    fillOnce(tasks, "tasks", function (holder) {
      [["rest", "Sleep in the day"], ["tidy", "Tidy the room"], ["beachcomb", "Walk the tideline"], ["garden", "Tend the greenhouse box"]].forEach(function (t) {
        var btn = el("button", t[1]); btn.type = "button"; btn.id = "task-" + t[0] + "-button";
        btn.addEventListener("click", function () { if (!isOff(btn)) daySend({ action: "day", task: t[0] }); });
        holder.appendChild(btn);
      });
    });
    setEnabled("task-rest-button", v.day.slots > 0 && v.energy < 100);
    setEnabled("task-tidy-button", v.day.slots > 0 && v.comfort < v.comfort_max);
    setEnabled("task-beachcomb-button", v.day.slots > 0);
    $("task-garden-button").hidden = !v.day.greenhouse;
    setEnabled("task-garden-button", v.day.slots > 0);
    $("task-rest-button").title = "Restores about " + v.day.rest_gain + " energy";
    $("task-tidy-button").title = "Comfort " + v.comfort + " of " + v.comfort_max + ": a cosier room restores more when you sleep";
    $("task-beachcomb-button").title = "Once a day: +1 salvage and a useful find";
    var rescue = $("rescue-list");
    fillOnce(rescue, JSON.stringify(v.waiting) + String(canAfford(v, v.day.rescue_cost)) + v.day.slots, function (holder) {
      v.waiting.forEach(function (w) {
        var li = el("li");
        li.appendChild(el("span", w.name + " is waiting on the shoals, all hands safe (" + costText(v.day.rescue_cost) + ")"));
        li.appendChild(el("span"));
        var btn = el("button", "Help her off"); btn.type = "button";
        setEnabled(btn, v.day.slots > 0 && canAfford(v, v.day.rescue_cost));
        btn.addEventListener("click", function () { if (!isOff(btn)) daySend({ action: "day", task: "rescue", id: w.id }); });
        li.appendChild(btn);
        holder.appendChild(li);
      });
    });
    setText($("workshop-salvage"), String(v.salvage));
    var ups = $("upgrade-list");
    fillOnce(ups, JSON.stringify(v.upgrades.map(function (u) { return [u.id, u.owned, u.affordable]; })), function (holder) {
      v.upgrades.forEach(function (u) {
        var li = el("li"); li.dataset.owned = String(u.owned);
        var info = el("span"); info.appendChild(el("span", u.name, "up-name")); info.appendChild(document.createTextNode(" " + (u.owned ? "(fitted) " : "(" + u.cost + " salvage) ") + u.text));
        li.appendChild(info);
        var btn = el("button", u.owned ? "Fitted" : "Buy"); btn.type = "button";
        setEnabled(btn, !u.owned && u.affordable);
        btn.addEventListener("click", function () {
          if (isOff(btn)) return;
          var go = function () { daySend({ action: "upgrade", id: u.id }); };
          if (u.rare && window.ConfirmDialog) window.ConfirmDialog.ask({ id: GAME_ID + "-upgrade-" + u.id, message: "Spend " + u.cost + " salvage on " + u.name + "?", confirmLabel: "Fit it", onConfirm: go });
          else go();
        });
        li.appendChild(btn);
        holder.appendChild(li);
      });
    });
    renderOrder(v);
    var f = v.forecast;
    setText($("day-forecast"), (f.narrow ? f.lo_label : f.lo_label + " to " + f.hi_label) + " expected tonight (night " + v.forecast.night + "). " + (v.notice.length ? plural(v.notice.length, "ship") + " listed on the harbour board." : "No ships listed."));
    setText($("boat-text"), v.boat.due ? "The mail boat is still due: she waits offshore and comes again tomorrow night." :
      "The mail boat is next expected on night " + v.boat.next_night + ". She brings " + v.boat.crates + " crates, split the way you order them.");
  }

  var ORDER_LABELS = { oil: "Oil", food: "Food", timber: "Timber", tar: "Tar", glass: "Glass" };
  function renderOrder(v) {
    var order = orderDraft || v.boat.order;
    var holder = $("order-grid");
    fillOnce(holder, "order", function (h) {
      Object.keys(ORDER_LABELS).forEach(function (k) {
        var cell = el("div", null, "order-cell"); cell.dataset.kind = k;
        cell.appendChild(el("strong", ORDER_LABELS[k]));
        var step = el("span", null, "stepper");
        var minus = el("button", "−"); minus.type = "button"; minus.setAttribute("aria-label", "One crate less " + ORDER_LABELS[k].toLowerCase());
        var out = el("output", "0"); out.setAttribute("aria-live", "polite");
        var plus = el("button", "+"); plus.type = "button"; plus.setAttribute("aria-label", "One crate more " + ORDER_LABELS[k].toLowerCase());
        minus.addEventListener("click", function () { if (!isOff(minus)) changeOrder(k, -1); });
        plus.addEventListener("click", function () { if (!isOff(plus)) changeOrder(k, 1); });
        step.appendChild(minus); step.appendChild(out); step.appendChild(plus);
        cell.appendChild(step);
        cell.appendChild(el("span", "", "note"));
        h.appendChild(cell);
      });
    });
    var total = 0;
    Object.keys(ORDER_LABELS).forEach(function (k) { total += order[k]; });
    Array.prototype.forEach.call(holder.children, function (cell) {
      var k = cell.dataset.kind;
      setText(cell.querySelector("output"), String(order[k]));
      setText(cell.querySelector(".note"), "= " + order[k] * v.boat.units[k] + (k === "oil" ? " oil" : " " + k));
      var btns = cell.querySelectorAll("button");
      setEnabled(btns[0], order[k] > 0);
      setEnabled(btns[1], total < v.boat.crates);
    });
    setText($("order-total"), total === v.boat.crates ? "Crates ordered: " + total + " of " + v.boat.crates + "." : "Crates ordered: " + total + " of " + v.boat.crates + ". Place " + plural(v.boat.crates - total, "more crate") + " to send the order.");
  }
  function changeOrder(kind, delta) {
    var order = Object.assign({}, orderDraft || view.boat.order);
    order[kind] += delta;
    var total = 0;
    Object.keys(order).forEach(function (k) { total += order[k]; });
    if (order[kind] < 0 || total > view.boat.crates) return;
    if (total === view.boat.crates) { orderDraft = null; send({ action: "order", order: order }); }
    else { orderDraft = order; renderOrder(view); }
  }

  // ---- year end, station, log ---------------------------------------------------------------------------
  function renderYearEnd(v) {
    setText($("yearend-text"), "Forty nights are kept. The light is lit, the log is full and the harbour knows your name. You may close the book here or keep the light as long as you like.");
    var facts = $("yearend-facts");
    fillOnce(facts, JSON.stringify(v.meta) + v.reputation, function (holder) {
      holder.appendChild(fact("Nights kept", v.meta.nights_kept));
      holder.appendChild(fact("Ships passed safely", v.meta.ships_passed));
      holder.appendChild(fact("Ships turned back", v.meta.ships_delayed));
      holder.appendChild(fact("Ships helped off the shoals", v.meta.rescues));
      holder.appendChild(fact("Lamp-hours", v.meta.lamp_hours));
      holder.appendChild(fact("The Light", v.reputation + " (" + v.rep_title + ")"));
    });
  }
  function renderStation(v) {
    var list = $("structure-list");
    fillOnce(list, "structure", function (holder) {
      v.structure.forEach(function (p) {
        var li = el("li"); li.dataset.part = p.id;
        var ic = el("span", p.icon, "ico"); ic.setAttribute("aria-hidden", "true"); li.appendChild(ic);
        li.appendChild(el("span", p.label));
        var m = el("span", null, "meter"); m.appendChild(el("span", null, "meter-fill")); li.appendChild(m);
        li.appendChild(el("span", "", "part-num"));
        li.appendChild(el("span", "", "part-state"));
        holder.appendChild(li);
      });
    });
    v.structure.forEach(function (p, i) {
      var li = list.children[i];
      var m = li.querySelector(".meter");
      m.setAttribute("data-state", p.state);
      m.firstElementChild.style.setProperty("--pct", p.value + "%");
      setText(li.querySelector(".part-num"), p.value + "/100");
      setText(li.querySelector(".part-state"), { sound: "Sound", worn: "Worn", poor: "Poor", failing: "Failing" }[p.state]);
    });
    var sup = $("supplies-list");
    fillOnce(sup, JSON.stringify(v.supplies), function (holder) {
      v.supplies.forEach(function (s) {
        var li = el("li"); li.dataset.count = String(s.count);
        li.appendChild(el("span", s.label)); li.appendChild(el("strong", String(s.count)));
        holder.appendChild(li);
      });
    });
    setText($("station-extra"), "Comfort " + v.comfort + " of " + v.comfort_max + ". Upgrades fitted: " + (v.upgrades.filter(function (u) { return u.owned; }).map(function (u) { return u.name; }).join(", ") || "none yet") + ".");
  }

  var KIND_ICON = { ship: "\u2693", weather: "\u2601", incident: "\u26A0", damage: "\u2716", lamp: "\u2738", clock: "\u23F2", keeper: "\u270B", note: "\u2022", story: "\u270E", odd: "\u2754", hand: "\u270D" };
  function clauses(text) { return text.match(/[^,;.:]+[,;.:]?\s*/g) || [text]; }
  function renderLog(v) {
    var list = $("log-list");
    var sig = v.log.length + "|" + (v.log.length ? v.log[v.log.length - 1].text : "");
    $("log-empty").hidden = v.log.length > 0;
    var total = v.log.length;
    fillOnce(list, sig, function (holder) {
      v.log.slice().reverse().forEach(function (e, i) {
        var li = el("li");
        if (e.kind === "odd") li.className = "odd-detail"; else if (e.kind === "hand") li.className = "odd-detail hand"; else if (e.kind === "story") li.className = "story-line";
        li.appendChild(el("span", clockLabel(v.start_min, v.tick_minutes, e.t), "log-time"));
        var k = el("span", KIND_ICON[e.kind] || "\u2022", "log-kind"); k.setAttribute("aria-hidden", "true"); li.appendChild(k);
        var body = el("span", null, "log-text");
        var fresh = (e.kind === "odd" || e.kind === "hand" || e.kind === "story") && i === 0 && v.phase === "night" && total > lastLogCount && lastLogCount > 0;
        if (fresh) {
          li.classList.add("reveal");
          clauses(e.text).forEach(function (clause, n) { var s = el("span", clause, "clause"); s.style.setProperty("--i", String(n)); body.appendChild(s); });
        } else body.textContent = e.text;
        li.appendChild(body);
        holder.appendChild(li);
      });
    });
    // read out what is new (ships, trouble, weather, damage), never the lamp-lighting line
    if (v.phase === "night" && v.log.length > lastLogCount) {
      var fresh = v.log.slice(lastLogCount).filter(function (e) { return e.kind !== "keeper" || e.text.indexOf("patch") === -1; }).map(function (e) { return e.text; });
      if (fresh.length) announce(fresh.slice(-3).join(" "));
    }
    lastLogCount = v.phase === "night" ? v.log.length : 0;
  }

  var infoShown = false;
  function renderInfo(v) {
    if (infoShown) return;
    infoShown = true;
    $("info-page-framing").textContent = v.info.framing;
    var how = $("info-page-how");
    v.info.how.forEach(function (t) { how.appendChild(el("li", t)); });
    var list = $("info-page-sources");
    v.info.facts.forEach(function (fact) {
      var item = el("li", null, "info-page-source");
      item.appendChild(el("strong", fact.heading));
      item.appendChild(el("p", fact.fact, "info-page-framing"));
      item.appendChild(el("p", fact.tie_in, "info-page-tie-in"));
      var link = el("a", fact.source.title);
      link.href = fact.source.url; link.target = "_blank"; link.rel = "noopener noreferrer";
      var src = el("p", null, "info-page-source-note");
      src.appendChild(document.createTextNode("Source: "));
      src.appendChild(link);
      src.appendChild(document.createTextNode(", " + fact.source.publisher + ". Read on " + fact.source.date_read + "."));
      item.appendChild(src);
      list.appendChild(item);
    });
    $("info-page-note").textContent = v.story.note;
  }

  // ---- achievements, changelog, panels ----------------------------------------------------------------
  function renderAchievements(v) {
    var list = $("achievements-list");
    list.textContent = "";
    var earnedNow = [];
    (v.achievements || []).forEach(function (a) {
      var li = el("li", null, a.earned ? "earned" : "");
      li.setAttribute("data-achievement-id", a.id);
      li.appendChild(el("span", a.earned ? "Earned" : "Not yet", "tick"));
      var name = el("strong", " " + a.label + " "); name.setAttribute("data-achievement-label", "");
      li.appendChild(name);
      li.appendChild(el("span", a.description));
      list.appendChild(li);
      if (a.earned) earnedNow.push(a.id);
    });
    $("achievements-toggle-button").textContent = "Achievements (" + earnedNow.length + "/" + (v.achievements || []).length + ")";
    var keepingAll = (v.achievements || []).filter(function (x) { return !x.story; }), storyAll = (v.achievements || []).filter(function (x) { return x.story; });
    setText($("ach-summary"), "Keeping the light: " + keepingAll.filter(function (x) { return x.earned; }).length + " of " + keepingAll.length + ". The story layer: " + storyAll.filter(function (x) { return x.earned; }).length + " of " + storyAll.length + ". A Quiet year can reach every one of the first group.");
    if (knownEarned !== null) {
      earnedNow.filter(function (id) { return knownEarned.indexOf(id) === -1; }).forEach(function (id) {
        var a = v.achievements.filter(function (x) { return x.id === id; })[0];
        showToast("Achievement unlocked: " + a.label + ".");
      });
    }
    knownEarned = earnedNow;
  }
  function renderChangelog(entries) {
    var holder = $("changelog-entries");
    holder.textContent = "";
    entries.forEach(function (entry) {
      var row = el("article", null, "changelog-entry");
      row.appendChild(el("div", entry.date, "changelog-date"));
      row.appendChild(el("p", entry.entry, "changelog-text"));
      holder.appendChild(row);
    });
    $("changelog-toggle-button").textContent = "What's New (" + entries.length + ")";
  }
  function loadChangelog() {
    return fetch("changelog.json").then(function (r) { return r.text(); }).then(function (text) {
      window.CHANGELOG_JSON = text;
      var data = JSON.parse(text);
      var list = Array.isArray(data) ? data : (data && data.changelog) || [];
      renderChangelog(list.slice().sort(function (a, b) { return a.date < b.date ? 1 : -1; }));
    }).catch(function () { renderChangelog([]); });
  }
  function setToggleState(buttonId, panelId) { $(buttonId).setAttribute("aria-expanded", String(!$(panelId).hidden)); }
  function wirePanelToggle(buttonId, panelId) {
    $(buttonId).addEventListener("click", function () {
      $(panelId).hidden = !$(panelId).hidden;
      setToggleState(buttonId, panelId);
    });
  }

  // ---- phases -----------------------------------------------------------------------------------------
  var PHASE_PANELS = { evening: "evening-panel", night: "night-panel", morning: "morning-panel", day: "day-panel", yearend: "yearend-panel" };
  function renderPhase(v, userMoved) {
    Object.keys(PHASE_PANELS).forEach(function (p) { $(PHASE_PANELS[p]).hidden = v.phase !== p; });
    $("night-controls").hidden = v.phase !== "night";
    if (v.phase === "evening") renderEvening(v);
    if (v.phase === "night") renderNight(v);
    if (v.phase === "morning") renderMorning(v);
    if (v.phase === "day") renderDay(v);
    if (v.phase === "yearend") renderYearEnd(v);
    if (lastPhase !== null && lastPhase !== v.phase) {
      var panel = $(PHASE_PANELS[v.phase]);
      var heading = panel.querySelector("h2");
      heading.setAttribute("tabindex", "-1");
      if (userMoved) heading.focus({ preventScroll: false });
      announce({ evening: "Evening. Plan the night.", night: "The lamp is lit.", morning: "Dawn. The morning report is ready.", day: "Day. Choose your tasks.", yearend: "The year is complete." }[v.phase]);
    }
    lastPhase = v.phase;
  }

  function syncTime(v) {
    var ctl = window.NoyvjTime && window.NoyvjTime.get(GAME_ID);
    if (!ctl) return;
    if (v.phase === "night") ctl.release("planning"); else ctl.hold("planning");
  }

  function render(v, userMoved) {
    view = v;
    renderHud(v);
    renderGoals(v);
    renderInfo(v);
    renderStory(v);
    renderScene(v);
    renderPhase(v, userMoved);
    renderStation(v);
    renderLog(v);
    renderAchievements(v);
    syncTime(v);
  }

  // ---- talking to the engine -------------------------------------------------------------------------
  function persist() {
    try {
      var proxy = engine.getState();
      var obj = proxy.toJs({ dict_converter: Object.fromEntries });
      if (proxy.destroy) proxy.destroy();
      lsSet(STORE_KEY, JSON.stringify(obj));
    } catch (e) { /* the save widget is the real save */ }
  }
  function send(request, userMoved) {
    if (!engine) return null;
    var result = JSON.parse(engine.handle(JSON.stringify(request)));
    if (result.error) { $("engine-status").textContent = "Something went wrong: " + result.error; return null; }
    var before = view && view.phase;
    render(result, userMoved === undefined ? (before !== result.phase && request.action !== "step") : userMoved);
    if (result.message) { setText($("day-message"), result.message); }
    persist();
    return result;
  }
  function daySend(request) {
    var result = send(request, false);
    if (result) { setText($("day-message"), result.message || ""); announce(result.message || ""); }
  }
  function tick() {
    if (!engine || !view || view.phase !== "night") return;
    send({ action: "step", n: 1 });
  }

  function randomSeed() {
    try { var a = new Uint32Array(1); window.crypto.getRandomValues(a); return a[0] % 2147483646 + 1; } catch (e) { return Math.floor(Math.random() * 2147483646) + 1; }
  }
  function quietPref() { return lsGet(QUIET_KEY) === "on"; }
  function eeriePref() { return lsGet(EERIE_KEY) !== "off"; }
  function applyEerie(on, tell) {
    lsSet(EERIE_KEY, on ? "on" : "off");
    var btn = $("eerie-toggle-button");
    btn.setAttribute("aria-pressed", String(on));
    btn.textContent = "Eerie details: " + (on ? "on" : "off");
    $("eerie-checkbox").checked = on;
    if (tell && engine) send({ action: "settings", eerie: on }, false);
  }
  function maybeContentNote() {
    if (lsGet(NOTE_KEY) || !view || !view.story.on) return;
    $("content-note-text").textContent = view.story.note;
    $("content-note-panel").hidden = false;
  }

  function shareFields() {
    var v = view;
    if (!v) return {};
    return {
      game: "Lighthouse",
      score: v.mode === "endless" || v.phase === "yearend" ? "Year " + v.year + ", night " + v.night : "Night " + v.night,
      stats: [
        { n: v.meta.ships_passed, one: "ship brought safely past", many: "ships brought safely past" },
        { n: v.meta.nights_kept, one: "night kept", many: "nights kept" },
        v.rep_title + " to the harbour"
      ]
    };
  }
  function mountCopyResult() {
    if (!window.NoyvjCopyResult) return;
    ["#yearend-copy-result", "#report-copy-result"].forEach(function (sel) {
      if (document.querySelector(sel)) window.NoyvjCopyResult.mountButton(sel, { getResult: shareFields });
    });
  }

  // ---- wiring -----------------------------------------------------------------------------------------
  function wire() {
    mountCopyResult();
    guard("light-lamp-button", function () { send({ action: "start_night" }, true); });
    guard("morning-continue-button", function () { send({ action: "end_morning" }, true); });
    guard("end-day-button", function () { orderDraft = null; send({ action: "end_day" }, true); });
    guard("continue-button", function () { send({ action: "continue" }, true); });
    guard("wind-button", function () { send({ action: "wind" }); });
    guard("tend-button", function () { send({ action: "tend" }); });
    guard("patch-button", function () { var part = $("patch-select").value; if (part) send({ action: "patch", part: part }); });
    $("ration-select").addEventListener("change", function () { send({ action: "plan", ration: parseInt($("ration-select").value, 10) || 0 }); });
    ["wind", "watch", "repair"].forEach(function (t) {
      $("task-" + t).addEventListener("change", function () { var tasks = {}; tasks[t] = $("task-" + t).checked; send({ action: "plan", tasks: tasks }); });
    });
    $("focus-select").addEventListener("change", function () { send({ action: "plan", focus: $("focus-select").value }); });
    wirePanelToggle("achievements-toggle-button", "achievements-panel");
    wirePanelToggle("letters-toggle-button", "letters-panel");
    wirePanelToggle("changelog-toggle-button", "changelog-panel");
    wirePanelToggle("info-page-toggle-button", "info-page-panel");
    $("quiet-checkbox").checked = quietPref();
    applyEerie(eeriePref(), false);
    $("eerie-toggle-button").addEventListener("click", function () { applyEerie(!eeriePref(), true); announce("Eerie details " + (eeriePref() ? "on" : "off") + "."); });
    $("eerie-checkbox").addEventListener("change", function () { applyEerie($("eerie-checkbox").checked, true); });
    $("content-note-ok").addEventListener("click", function () { lsSet(NOTE_KEY, "seen"); $("content-note-panel").hidden = true; });
    $("content-note-eerie-off").addEventListener("click", function () { lsSet(NOTE_KEY, "seen"); $("content-note-panel").hidden = true; applyEerie(false, true); });
    $("quiet-checkbox").addEventListener("change", function () { lsSet(QUIET_KEY, $("quiet-checkbox").checked ? "on" : "off"); });
    guard("abandon-button", function () {
      var go = function () { orderDraft = null; lastPhase = null; send({ action: "abandon", seed: randomSeed(), quiet: quietPref() }, true); showToast("A fresh year begins. Your records are kept."); };
      if (window.ConfirmDialog) window.ConfirmDialog.ask({ id: GAME_ID + "-abandon", message: "Abandon this year and start another? Your lifetime records and achievements are kept.", confirmLabel: "Abandon the year", allowSkip: false, onConfirm: go });
      else go();
    });
    guard("reset-button", function () {
      var go = function () { orderDraft = null; lastPhase = null; knownEarned = null; send({ action: "reset", seed: randomSeed(), quiet: quietPref() }, true); lsRemove(STORE_KEY); showToast("Everything is reset."); };
      if (window.ConfirmDialog) window.ConfirmDialog.ask({ id: GAME_ID + "-reset", message: "Reset all progress, including records and achievements? This cannot be undone.", confirmLabel: "Reset everything", allowSkip: false, onConfirm: go });
      else go();
    });
    // the save widget loads a save directly into the engine; this redraws the page afterwards
    window.lighthouseRefresh = function () {
      if (!engine) return;
      orderDraft = null; lastPhase = null; knownEarned = null; knownUnread = null; lastLogCount = 0;
      send({ action: "open" }, false);
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("noyvj-theme-change", function () { if (view) renderScene(view); });
  }

  var TUTORIAL_STEPS = [
    { title: "The keeper's life", text: "You keep one light on one rock. Each evening you plan the night, the night plays out, and each morning you read how the ships fared. Nothing you do can end the game, and everything can be paused. Skip any time and reopen this from the Tutorial button." },
    { selector: "#hud", title: "The station at a glance", text: "Oil feeds the lamp, energy is yours, The Light is the harbour's opinion of you, and salvage buys upgrades. Every meter has a number and a word as well as a bar." },
    { selector: "#goals-panel", title: "Three goals, no order", text: "Three goals are always on show: the next title the harbour could give you, the upgrade nearest your salvage, and something to try. Do them in any order; each is replaced when it is done." },
    { selector: "#scene-panel", title: "The rock", text: "The beam sweeps the sea and ships pass by. A ship that is lit up by your beam gets a ring and a mark in the list below. Fog, haze, squalls and storms all shorten how far the beam reaches." },
    { selector: "#barometer-card", title: "The barometer", text: "Tonight's weather as a band of two steps. It is right about nine nights in ten, so it is a hint, not a promise." },
    { selector: "#board-card", title: "The harbour board", text: "The ships expected tonight, roughly when, and how far the beam must reach for each to find you. Plan your lamp around them." },
    { selector: "#plan-blocks", title: "The lamp plan", text: "Choose a lamp level for dusk, deep night and dawn. Brighter reaches further and burns more oil; the estimate under it tells you whether the oil will last." },
    { selector: "#task-wind", title: "The keeper's rounds", text: "Tick the rounds you want: winding the clockwork when it runs low, keeping watch, patching between rounds. Each costs energy or supplies." },
    { selector: "#light-lamp-button", title: "Light the lamp", text: "When you are ready. In the night you can pause, speed up to 2x or 4x, change the lamp for the rest of the current part of the night (keys 1 to 4), wind the clockwork (W) and see to trouble (T)." },
    { selector: "#station-panel", title: "The station", text: "Storms wear the tower, the lantern glass, the rail, the dock and the cistern. In the day you mend them with supplies from the supply boat, whose twelve crates you order yourself." },
    { selector: "#letters-toggle-button", title: "Letters", text: "Passing sailors write once their boat has got safely by often enough, and some send gifts. Odd things happen too, and every one of them has a kind explanation." },
    { selector: "#eerie-toggle-button", title: "Eerie details", text: "This switch is always here. Off keeps the letters and the cosy cast but skips the odd happenings. The Story button at bottom left hides the whole story layer." },
    { selector: "#info-page-toggle-button", title: "About the Light", text: "How the rules work, and a few real facts about lighthouses with their sources named." },
    { title: "You are ready", text: "Set the lamp, light it, and keep the sea company. Take your time." },
  ];


  function onKey(e) {
    if (e.altKey || e.ctrlKey || e.metaKey || !view || view.phase !== "night") return;
    var t = e.target;
    if (!t || !t.closest || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName)) return;
    if (document.querySelector("#opening-screen, #confirm-dialog-overlay:not([hidden]), #tutorial-overlay:not([hidden])")) return;
    var k = e.key.toLowerCase();
    if (k >= "1" && k <= "4") { e.preventDefault(); send({ action: "level", level: LEVEL_IDS[parseInt(k, 10) - 1] }); }
    else if (k === "w") { e.preventDefault(); send({ action: "wind" }); }
    else if (k === "t") { e.preventDefault(); send({ action: "tend" }); }
  }

  function setBusy(on) {
    ["light-lamp-button", "morning-continue-button", "end-day-button", "continue-button", "wind-button", "tend-button", "patch-button", "abandon-button", "reset-button"].forEach(function (id) { $(id).disabled = on; });
  }

  async function boot() {
    setBusy(true);
    var changelog = loadChangelog();
    var pyodide = await window.loadPyodide();
    for (var i = 0; i < ENGINE_MODULES.length; i++) {
      var source = await (await fetch(ENGINE_MODULES[i])).text();
      pyodide.FS.writeFile(ENGINE_MODULES[i], source, { encoding: "utf8" });
    }
    await pyodide.runPythonAsync(await (await fetch("game.py")).text());
    window.pyodide = pyodide;   // the shared save widget looks for it
    engine = { handle: pyodide.globals.get("handle"), getState: pyodide.globals.get("get_state"), loadState: pyodide.globals.get("load_state") };
    var choice = "continue";
    try { if (window.NoyvjOpeningScreen && window.NoyvjOpeningScreen.choice) choice = await window.NoyvjOpeningScreen.choice; } catch (e) { choice = "continue"; }
    var saved = choice === "new" ? null : lsGet(STORE_KEY);
    var restored = false;
    if (saved) {
      try { engine.loadState(pyodide.toPy(JSON.parse(saved))); restored = true; } catch (e) { restored = false; }
    }
    $("engine-status").textContent = "";
    setBusy(false);
    reducedMotion = document.documentElement.getAttribute("data-reduced-motion") === "true";
    engine.handle(JSON.stringify({ action: "settings", eerie: eeriePref() }));
    if (!restored) send({ action: "new_game", seed: randomSeed(), quiet: quietPref() }, false);
    else {
      send({ action: "open" }, false);
      if (view.meta.nights_kept > 0 || view.night > 1) showToast("Welcome back. The light is just as you left it.");
    }
    maybeContentNote();
    if (window.NoyvjTime) {
      window.NoyvjTime.start(GAME_ID, tick, BASE_MS);
      var ctl = window.NoyvjTime.get(GAME_ID);
      var setTickMs = function () { var s = ctl.snapshot(); $("scene").style.setProperty("--tick-ms", (s.intervalMs || BASE_MS) + "ms"); };
      ctl.subscribe(setTickMs); setTickMs();
      syncTime(view);
    }
    new MutationObserver(function () {
      reducedMotion = document.documentElement.getAttribute("data-reduced-motion") === "true";
      if (view) renderScene(view);
    }).observe(document.documentElement, { attributes: true, attributeFilter: ["data-reduced-motion"] });
    await changelog;
    if (window.GameTutorial) window.GameTutorial.init(window.lighthouseTutorialSteps ? window.lighthouseTutorialSteps(TUTORIAL_STEPS) : TUTORIAL_STEPS, { gameId: GAME_ID });
    if (window.MobileHud) window.MobileHud.init([{ selector: "#hud-night", label: "Night" }, { selector: "#hud-oil", label: "Oil" }, { selector: "#hud-energy", label: "Energy" }]);
    if (window.MobileDock) window.MobileDock.init("#night-controls", { breakpoint: 640 });
    watchDock();
  }

  // On a phone the night controls are pinned to the bottom of the screen; keep the floating pills clear of them.
  function watchDock() {
    var dock = $("night-controls");
    function measure() {
      var h = dock.classList.contains("mobile-docked") && !dock.hidden ? dock.getBoundingClientRect().height : 0;
      document.documentElement.style.setProperty("--dock-h", Math.round(h) + "px");
    }
    if (window.ResizeObserver) new ResizeObserver(measure).observe(dock);
    window.addEventListener("resize", measure);
    document.addEventListener("noyvj-time-change", measure);
    measure();
  }

  wire();
  boot().catch(function (err) {
    $("engine-status").textContent = "The lamp room could not start (" + err + "). Reload to try again.";
  });
})();
