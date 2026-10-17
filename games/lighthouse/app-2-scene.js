/* Lighthouse, part 2 of 6: scene palettes, the SVG scene (sky, beam, ships), the status strip and the goals. */
(function () {
  "use strict";

  var A = window.LighthouseApp;
  var $ = A.$, clockLabel = A.clockLabel, el = A.el, fillOnce = A.fillOnce, isLight = A.isLight, mix = A.mix,
      setText = A.setText, svgEl = A.svgEl;

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
      var fog = A.view && A.view.cond === 2;
      node.body.style.opacity = fog && !s.lit ? "0.55" : "1";
      node.g.style.setProperty("--ship-fill", ink.ship);
      node.g.style.setProperty("--ship-line", ink.shipLine);
      // Data attributes for the Desktop hover card
      node.g.setAttribute("data-ship-id", s.id);
      node.g.setAttribute("data-name", (s.label || "") + " " + (s.name || ""));
      node.g.setAttribute("data-cargo", s.cargo || "None");
      node.g.setAttribute("data-mood", s.mood || "Neutral");
      node.g.setAttribute("data-letter", s.last_letter || "No letters yet");
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
    $("fog-layer").classList.toggle("drifting", v.cond === 2 && !A.reducedMotion);
    $("rain-layer").classList.toggle("falling", v.cond >= 3 && !A.reducedMotion);
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
      var sweeping = !v.beam.stopped && !A.reducedMotion && v.phase === "night";
      beam.classList.toggle("sweeping", sweeping);
      if (!sweeping) beam.style.transform = "rotate(-14deg)"; else beam.style.transform = "";
      // reduce motion: a tick mark at the far end of the cone shows where the sweep would be
      if (A.reducedMotion && !v.beam.stopped) {
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
    // R4-LHMO-10: Repair is how sound the station's weakest part is (0 to 100); both Oil and Repair carry a calm "low" state
    // for the phone's big icon chips (style.css), always with the words as well
    var worst = Math.round(Math.min.apply(null, v.structure.map(function (p) { return p.value; })));
    var repairState = worst < 40 ? "low" : "ok";
    setText($("hud-repair"), String(worst));
    setText($("hud-repair-state"), worst < 40 ? "Needs mending" : worst < 70 ? "Worn" : "Sound");
    $("hud-repair-chip").setAttribute("data-state", repairState);
    $("hud-oil-chip").setAttribute("data-state", oilState === "ok" ? "ok" : "low");
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

  // what the other parts use (see the File map in CLAUDE.md)
  A.meter = meter; A.renderGoals = renderGoals; A.renderHud = renderHud; A.renderScene = renderScene;
})();
