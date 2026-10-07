/*
 * Chronicle -- browser glue. Contains NO game rules.
 *
 * Every rule (set validation, puzzle generation, grading, learning, the archive, achievements, save merge)
 * lives in game.py and runs in Pyodide. This file only:
 *   - paints the static shell and, for a returning player, the last engine view cached in localStorage
 *     ("chronicle:lastview") before the engine exists;
 *   - loads Pyodide lazily after first paint (or on the first tap or key), writes the set's JSON files and the
 *     engine modules into Pyodide's file system, and runs game.py;
 *   - forwards taps to the engine as JSON and draws whatever view it sends back.
 * The only logic here is presentation: which card is picked up, where things are drawn, and the nuance strip.
 * Nothing in this file posts to a backend. "Report a problem" builds a payload with the engine, saves a draft
 * on this device and says reporting opens soon.
 */
(function () {
  "use strict";

  var GAME = "chronicle";
  var PYODIDE_URL = "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js";
  var ENGINE_MODULES = ["setdata.py", "puzzle.py", "achievements.py", "report.py"];
  var SET_FILES = ["meta", "sources", "entities", "claims", "relations", "sections", "readings"];
  var LS_STATE = "chronicle:state";
  var LS_VIEW = "chronicle:lastview";
  var LS_REPORTS = "chronicle:report-drafts";

  var $ = function (id) { return document.getElementById(id); };
  var api = null, getStateFn = null;
  var engineReady = false, engineStarting = false;
  var view = null;
  var selected = null;               // { id, slot } : the card picked up (slot is null when it is in the tray)
  var catalog = { ach: [], log: [] };
  var toastQueue = [], toastBusy = false;
  var currentReport = null;
  var lastFocusKey = null;

  function lsGet(key) { try { return window.localStorage.getItem(key); } catch (e) { return null; } }
  function lsSet(key, value) { try { window.localStorage.setItem(key, value); } catch (e) { /* convenience only */ } }
  function lsRemove(key) { try { window.localStorage.removeItem(key); } catch (e) { /* convenience only */ } }
  function jsonParse(text) { try { return JSON.parse(text); } catch (e) { return null; } }
  function el(tag, cls, text) {
    var node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  }
  function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); return node; }
  function announce(text) { $("announce").textContent = ""; setTimeout(function () { $("announce").textContent = text; }, 30); }

  // ---- static catalogs (the shared whats-new banner reads window.CHANGELOG_JSON) --------------------------
  var catalogPromise = Promise.all([
    fetch("achievements.json").then(function (r) { return r.text(); }),
    fetch("changelog.json").then(function (r) { return r.text(); }),
  ]).then(function (texts) {
    window.ACHIEVEMENTS_JSON = texts[0];
    window.CHANGELOG_JSON = texts[1];
    var a = jsonParse(texts[0]), l = jsonParse(texts[1]);
    catalog.ach = a && a.achievements ? a.achievements : [];
    var list = Array.isArray(l) ? l : (l && l.changelog) || [];
    catalog.log = list.slice().sort(function (x, y) { return x.date < y.date ? 1 : -1; });
    renderChangelog();
    renderAchievements();
  }).catch(function (err) { console.error("chronicle: catalog fetch failed", err); });

  function renderChangelog() {
    var box = clear($("changelog-entries"));
    catalog.log.forEach(function (e) {
      var d = el("div", "changelog-entry");
      d.appendChild(el("span", "changelog-date", e.date));
      d.appendChild(el("p", null, e.entry));
      box.appendChild(d);
    });
  }

  function renderAchievements() {
    var earned = (view && view.achievements_earned) || [];
    var list = clear($("achievements-list"));
    catalog.ach.forEach(function (a) {
      var got = earned.indexOf(a.id) >= 0;
      var li = el("li", got ? "earned" : "");
      li.appendChild(el("span", "tick", got ? "✔ Earned" : "Not yet"));
      li.appendChild(el("strong", null, " " + a.label + ": "));
      li.appendChild(document.createTextNode(a.description));
      list.appendChild(li);
    });
  }

  function showToast(text) {
    toastQueue.push(text);
    if (toastBusy) return;
    toastBusy = true;
    (function next() {
      var t = toastQueue.shift();
      if (!t) { toastBusy = false; $("toast").textContent = ""; return; }
      $("toast").textContent = t;
      announce(t);
      setTimeout(next, 3200);
    })();
  }

  // ---- engine ---------------------------------------------------------------------------------------------
  function loadScript(src) {
    return new Promise(function (resolve, reject) {
      var s = document.createElement("script");
      s.src = src; s.onload = resolve; s.onerror = function () { reject(new Error("could not load " + src)); };
      document.head.appendChild(s);
    });
  }

  function send(req) {
    var text = api(JSON.stringify(req));
    return JSON.parse(text);
  }

  function persistState() {
    if (!getStateFn) return;
    try {
      var proxy = getStateFn();
      var obj = proxy.toJs({ dict_converter: Object.fromEntries });
      if (proxy.destroy) proxy.destroy();
      lsSet(LS_STATE, JSON.stringify(obj));
    } catch (e) { console.error("chronicle: could not persist state", e); }
  }

  async function startEngine() {
    if (engineStarting || engineReady) return;
    engineStarting = true;
    setStatus("Warming up the archive...");
    try {
      await catalogPromise;
      await loadScript(PYODIDE_URL);
      var pyodide = await window.loadPyodide();
      var index = await (await fetch("sets/index.json")).text();
      var root = pyodide.FS.cwd();       // Python's relative paths (sets/..., the engine modules) resolve here
      pyodide.FS.mkdirTree(root + "/sets");
      pyodide.FS.writeFile(root + "/sets/index.json", index, { encoding: "utf8" });
      var folders = (jsonParse(index) || { sets: [] }).sets.map(function (s) { return s.folder; });
      for (var f = 0; f < folders.length; f++) {
        pyodide.FS.mkdirTree(root + "/sets/" + folders[f]);
        for (var n = 0; n < SET_FILES.length; n++) {
          var path = "sets/" + folders[f] + "/" + SET_FILES[n] + ".json";
          var body = await (await fetch(path)).text();
          pyodide.FS.writeFile(root + "/" + path, body, { encoding: "utf8" });
        }
      }
      for (var i = 0; i < ENGINE_MODULES.length; i++) {
        var source = await (await fetch(ENGINE_MODULES[i])).text();
        pyodide.FS.writeFile(root + "/" + ENGINE_MODULES[i], source, { encoding: "utf8" });
      }
      await pyodide.runPythonAsync(await (await fetch("game.py")).text());
      window.pyodide = pyodide;          // the shared save widget looks for it
      api = pyodide.globals.get("handle");
      getStateFn = pyodide.globals.get("get_state");
      var saved = jsonParse(lsGet(LS_STATE) || "null");
      if (saved) {
        try {
          var proxy = pyodide.toPy(saved);
          pyodide.globals.get("load_state")(proxy);
          if (proxy.destroy) proxy.destroy();
        } catch (e) { console.error("chronicle: saved state ignored", e); }
      }
      engineReady = true;
      setStatus("");
      applyResponse(send({ action: "boot" }));
      persistState();
      startTutorial();
    } catch (err) {
      console.error("chronicle: engine failed to start", err);
      engineStarting = false;
      setStatus("The archive could not load (offline for the first time?). The page is still readable; try reloading.");
    }
  }

  function startTutorial() {
    if (!window.GameTutorial) return;
    window.GameTutorial.init(TUTORIAL_STEPS, { gameId: GAME });
  }
  var TUTORIAL_STEPS = [
    { title: "Pick a set", selector: "#set-picker", text: "A set is a topic. Today there is one: a sample of the American presidency. The meter shows how much of its archive you have found." },
    { title: "Sections unlock in order", selector: "#sections", text: "Each section is a group of moments with its own difficulty. Clear one to open the next. Locked sections say what unlocks them." },
    { title: "Order the cards", selector: "#slots", text: "Pick up a card from the tray, then tap a slot. The slots run from earliest to latest. You can also drag cards, or use the number keys." },
    { title: "Check your order", selector: "#check-button", text: "When every slot is full, press Check. Cards in the right place lock and are added to your archive; the others tell you whether to move earlier or later." },
    { title: "Every fact has sources", selector: "#puzzle-panel", text: "Once a puzzle is solved you see each date with the claim, how sure the sources are, and three linked sources. If something looks wrong, use Report a problem." },
    { title: "Your archive", selector: "#archive-toggle-button", text: "Everything you place correctly fills in the archive: moments, what else was happening, people and places. It is easy to reach 100%." },
  ];

  function setStatus(text) {
    $("engine-status").textContent = text;
    $("engine-status").hidden = !text;
  }

  function act(req, opts) {
    opts = opts || {};
    if (!engineReady) {
      startEngine();
      setStatus("The archive is still warming up. Try again in a moment.");
      return null;
    }
    var resp;
    try { resp = send(req); } catch (err) { console.error(err); setStatus("Something went wrong in the engine."); return null; }
    if (!resp.ok && resp.error) {
      $("message-line").textContent = resp.error;
      announce(resp.error);
    }
    if (resp.view) {
      view = resp.view;
      lsSet(LS_VIEW, JSON.stringify(slimView(view)));
    }
    if (resp.dirty) persistState();
    (resp.new || []).forEach(function (id) {
      var a = catalog.ach.filter(function (x) { return x.id === id; })[0];
      showToast("Achievement earned: " + (a ? a.label : id));
    });
    if (opts.render !== false) render();
    else renderMeterAndPicker();
    if ((resp.new || []).length) renderAchievements();
    return resp;
  }

  function applyResponse(resp) {
    if (resp.view) { view = resp.view; lsSet(LS_VIEW, JSON.stringify(slimView(view))); }
    render();
  }

  // the cached view omits the heavy reveal blocks: a returning player only needs the board and the meter
  function slimView(v) {
    var copy = JSON.parse(JSON.stringify(v));
    copy.result = null;
    return copy;
  }

  // ---- rendering ------------------------------------------------------------------------------------------
  function captureFocus() {
    var a = document.activeElement;
    lastFocusKey = a && a.getAttribute ? a.getAttribute("data-fk") : null;
  }
  function restoreFocus() {
    if (!lastFocusKey) return;
    var n = document.querySelector('[data-fk="' + lastFocusKey + '"]');
    if (n && n !== document.activeElement) n.focus();
  }

  function render() {
    if (!view) return;
    captureFocus();
    if (view.empty) {
      setStatus("No sets could be loaded. " + (view.problems || []).join(" "));
      return;
    }
    renderMeterAndPicker();
    renderSections();
    renderPuzzle();
    renderResult();
    renderAchievements();
    var hints = $("hints-checkbox");
    if (hints) hints.checked = !!view.settings.hints;
    restoreFocus();
  }

  function renderMeterAndPicker() {
    if (!view || view.empty) return;
    var sel = $("set-select");
    if (sel.options.length !== view.sets.length || sel.getAttribute("data-built") !== view.sets.map(function (s) { return s.id; }).join(",")) {
      clear(sel);
      view.sets.forEach(function (s) {
        var o = el("option", null, s.title);
        o.value = s.id;
        sel.appendChild(o);
      });
      sel.setAttribute("data-built", view.sets.map(function (s) { return s.id; }).join(","));
    }
    sel.value = view.set.id;
    var badge = $("set-status");
    badge.textContent = view.set.status_label;
    badge.className = "badge" + (view.set.draft ? "" : " reviewed");
    $("draft-banner").hidden = !view.set.draft;
    $("set-summary").textContent = view.set.description;
    $("meter").value = view.set.percent;
    $("meter-text").textContent = view.set.found + " of " + view.set.total + " found (" + view.set.percent + "%)";
  }

  function renderSections() {
    var nav = clear($("sections"));
    var current = view.puzzle.section;
    view.sections.forEach(function (s) {
      var b = el("button", "section-card");
      b.type = "button";
      b.setAttribute("data-fk", "section-" + s.id);
      b.setAttribute("data-section", s.id);
      if (s.id === current) b.setAttribute("aria-current", "true");
      if (!s.unlocked) b.setAttribute("aria-disabled", "true");
      var diff = "Difficulty " + s.difficulty + " of 3";
      b.appendChild(el("span", "sc-title", (s.cleared ? "✔ " : (s.unlocked ? "" : "🔒 ")) + s.title));
      b.appendChild(el("span", "sc-meta", s.unlocked ? (s.progress + (s.cleared ? " (cleared)" : "")) : "Locked: clear " + s.requires.join(" and ") + " first"));
      b.appendChild(el("span", "sc-meta", diff + ", " + s.size + " cards"));
      nav.appendChild(b);
    });
  }

  function slotLabel(p, s) {
    var base = "Slot " + (s.index + 1) + " of " + p.size + ", " + (s.index === 0 ? "earliest" : (s.index === p.size - 1 ? "latest" : "in between"));
    if (!s.card) return base + ", empty";
    var t = p.cards[s.card].title;
    if (s.locked) return base + ", " + t + ", right place, locked";
    if (s.status === "wrong") return base + ", " + t + ", not here yet" + (s.direction && p.hints ? ", move " + s.direction : "");
    return base + ", " + t;
  }

  function renderPuzzle() {
    var p = view.puzzle;
    var finished = p.status !== "playing";
    $("puzzle-meta").textContent = p.section_title + " · " + p.round_label + " · difficulty " + p.difficulty + " of 3 · " + p.size + " cards" + (p.min_gap_years ? " · moments at least " + p.min_gap_years + " years apart" : " · some moments are close together");
    var slots = clear($("slots"));
    slots.style.setProperty("--cols", p.size <= 4 ? p.size : 3);
    p.slots.forEach(function (s) {
      var li = el("li", "slot-item");
      var b = el("button", "slot");
      b.type = "button";
      b.setAttribute("data-slot", s.index);
      b.setAttribute("data-fk", "slot-" + s.index);
      b.setAttribute("aria-label", slotLabel(p, s));
      var cls = "slot " + (s.card ? (s.locked ? "right" : (s.status === "wrong" ? "wrong" : "filled")) : "empty");
      if (selected && !s.locked) cls += " target";
      b.className = cls;
      b.appendChild(el("span", "slot-num", "" + (s.index + 1) + (s.index === 0 ? " · earliest" : (s.index === p.size - 1 ? " · latest" : ""))));
      b.appendChild(el("span", "slot-card", s.card ? p.cards[s.card].title : "Empty"));
      var state = "";
      if (s.locked) state = "✔ Right place (locked)";
      else if (s.status === "wrong") state = "✖ Not here yet" + (p.hints && s.direction ? ": try " + (s.direction === "earlier" ? "◀ earlier" : "later ▶") : "");
      else if (s.card) state = "Placed";
      else state = "Tap to place the picked-up card here";
      b.appendChild(el("span", "slot-state", state));
      if (s.card && !s.locked && !finished) {
        b.draggable = true;
        b.addEventListener("dragstart", function (ev) { startDrag(ev, s.card, s.index); });
      }
      if (selected && selected.id === s.card) b.setAttribute("aria-pressed", "true");
      li.appendChild(b);
      slots.appendChild(li);
    });

    var tray = clear($("tray"));
    if (!p.tray.length) tray.appendChild(el("span", "tray-empty", finished ? "Every card is in place." : "Every card is placed. Press Check."));
    p.tray.forEach(function (id) {
      var b = el("button", "card", p.cards[id].title);
      b.type = "button";
      b.setAttribute("data-card", id);
      b.setAttribute("data-fk", "card-" + id);
      b.setAttribute("aria-pressed", String(!!(selected && selected.id === id)));
      if (!finished) {
        b.draggable = true;
        b.addEventListener("dragstart", function (ev) { startDrag(ev, id, null); });
      }
      tray.appendChild(b);
    });
    if (selected && !(p.tray.indexOf(selected.id) >= 0 || p.slots.some(function (s) { return s.card === selected.id && !s.locked; }))) selected = null;

    $("message-line").textContent = p.message || (view.first_run && p.checks === 0 ? "Pick up a card, then tap a slot. Earliest goes in slot 1." : "");
    var check = $("check-button");
    check.hidden = finished;
    check.setAttribute("aria-disabled", String(!p.all_placed));
    check.textContent = p.all_placed ? "Check" : "Check (fill every slot first)";
    $("show-answer-button").hidden = finished;
    $("next-button").hidden = !finished;
    $("next-button").textContent = p.status === "solved" ? "Next puzzle" : "Next puzzle";
    $("return-button").hidden = !(selected && selected.slot !== null);
  }

  // ---- sources and claims ------------------------------------------------------------------------------------
  function sourcesDetails(claim) {
    var d = el("details", "sources");
    d.appendChild(el("summary", null, "Sources (" + claim.sources.length + ")"));
    var ul = el("ul", "source-list");
    claim.sources.forEach(function (s) {
      var li = el("li");
      var a = el("a", null, s.title);
      a.href = s.url; a.target = "_blank"; a.rel = "noopener noreferrer";
      li.appendChild(a);
      li.appendChild(el("span", "source-meta", s.institution + " · read " + s.read));
      if (s.note) li.appendChild(el("span", "source-meta", "Confirms: " + s.note));
      ul.appendChild(li);
    });
    d.appendChild(ul);
    d.addEventListener("toggle", function () {
      if (d.open && !claim.viewed) {
        claim.viewed = true;
        act({ action: "view_claim", set: claim.set, claim: claim.id }, { render: false });
      }
    });
    return d;
  }

  function claimBlock(claim, showText) {
    var box = el("div", "claim");
    var conf = el("span", "conf " + claim.confidence, claim.symbol + " " + claim.confidence_label);
    conf.setAttribute("title", "How sure the sources are");
    box.appendChild(conf);
    if (showText !== false) box.appendChild(el("p", null, claim.text));
    if (claim.alternatives && claim.alternatives.length) {
      box.appendChild(el("p", "note", claim.confidence === "disputed" ? "The sources differ:" : "What the sources support instead:"));
      var ul = el("ul", "alts");
      claim.alternatives.forEach(function (a) { ul.appendChild(el("li", null, a)); });
      box.appendChild(ul);
    }
    box.appendChild(sourcesDetails(claim));
    var actions = el("div", "claim-actions");
    var rb = el("button", "small-btn", "Report a problem");
    rb.type = "button";
    rb.addEventListener("click", function () { openReport(claim, rb); });
    actions.appendChild(rb);
    box.appendChild(actions);
    return box;
  }

  function eventBlock(e, opts) {
    opts = opts || {};
    var li = el("li", "reveal" + (e.new ? " fresh" : ""));
    var when = el("div", "when", (opts.number ? opts.number + ". " : "") + e.date_label);
    li.appendChild(when);
    var h = el("h3", null, e.title);
    if (e.new) h.appendChild(el("span", "new-tag", "New in archive"));
    li.appendChild(h);
    var where = [];
    if (e.place) where.push(e.place);
    if (e.region) where.push(e.region);
    if (opts.near) where.push("around the time of: " + opts.near + (opts.years ? " (" + opts.years + (opts.years === 1 ? " year" : " years") + " apart)" : ""));
    if (where.length) li.appendChild(el("p", "note", where.join(" · ")));
    li.appendChild(claimBlock(e.claim));
    (e.other_claims || []).forEach(function (c) { li.appendChild(claimBlock(c)); });
    return li;
  }

  function glyph(kind) {
    var paths = {
      event: '<rect x="4" y="6" width="24" height="22" rx="3"/><path d="M4 13h24M10 3v6M22 3v6"/>',
      context: '<circle cx="16" cy="16" r="12"/><path d="M4 16h24M16 4c-6 6-6 18 0 24M16 4c6 6 6 18 0 24"/>',
      person: '<circle cx="16" cy="10" r="6"/><path d="M5 28c1-8 6-11 11-11s10 3 11 11z"/>',
      place: '<path d="M16 29C9 20 6 16 6 12a10 10 0 0 1 20 0c0 4-3 8-10 17z"/><circle cx="16" cy="12" r="3.5"/>',
    };
    var ns = "http://www.w3.org/2000/svg";
    var svg = document.createElementNS(ns, "svg");
    svg.setAttribute("viewBox", "0 0 32 32");
    svg.setAttribute("class", "glyph");
    svg.setAttribute("aria-hidden", "true");
    svg.innerHTML = paths[kind] || paths.event;
    return svg;
  }

  // ---- result panel + nuance strip -------------------------------------------------------------------------
  function renderResult() {
    var r = view.result;
    var panel = $("result-panel");
    if (!r) { panel.hidden = true; clear($("result-body")); return; }
    panel.hidden = false;
    $("result-heading").textContent = r.solved ? "What happened" : "The answer";
    var body = clear($("result-body"));
    if (r.new_count) body.appendChild(el("p", "note", r.new_count + (r.new_count === 1 ? " entry" : " entries") + " added to your archive from this puzzle."));
    var ol = el("ol", "reveal-list");
    r.reveal.forEach(function (e, i) { ol.appendChild(eventBlock(e, { number: i + 1 })); });
    body.appendChild(ol);

    if (r.nuance.length) {
      var strip = el("div", "nuance");
      strip.appendChild(el("h3", null, "What else was happening"));
      strip.appendChild(el("p", "legend", "Circles are this puzzle's moments (numbered). Diamonds are things that happened elsewhere (lettered). They sit on one scale of years, from " + r.span[0] + " to " + r.span[1] + "."));
      strip.appendChild(nuanceSvg(r));
      var ul = el("ol", "reveal-list");
      r.nuance.forEach(function (e, i) { ul.appendChild(eventBlock(e, { number: String.fromCharCode(65 + i), near: e.near, years: e.years })); });
      strip.appendChild(ul);
      body.appendChild(strip);
    }
    if (r.readings && r.readings.length) {
      r.readings.forEach(function (rd) {
        var box = el("div", "reading");
        box.appendChild(el("h3", null, "Reading: " + rd.title));
        box.appendChild(el("p", null, rd.text));
        box.appendChild(el("p", "note", "Every statement above comes from the claims in this section; open a moment's sources to check."));
        body.appendChild(box);
      });
    }
    if (r.section_cleared) body.insertBefore(el("p", "message-line", "✔ Section cleared."), body.firstChild);
  }

  function yearOf(label) {
    var m = /(\d{1,4})(?!.*\d)/.exec(label);
    var y = m ? parseInt(m[1], 10) : 0;
    return /BCE/.test(label) ? -y : y;
  }

  function nuanceSvg(r) {
    var ns = "http://www.w3.org/2000/svg";
    var items = [];
    r.reveal.forEach(function (e, i) { items.push({ kind: "event", y: yearOf(e.date_label), label: String(i + 1) }); });
    r.nuance.forEach(function (e, i) { items.push({ kind: "else", y: yearOf(e.date_label), label: String.fromCharCode(65 + i) }); });
    var min = Math.min.apply(null, items.map(function (i) { return i.y; }));
    var max = Math.max.apply(null, items.map(function (i) { return i.y; }));
    var pad = Math.max(2, Math.round((max - min) * 0.06));
    var W = 600, H = 112, L = 24, R = W - 24;
    var scale = function (y) { return L + (y - (min - pad)) / ((max + pad) - (min - pad)) * (R - L); };
    var svg = document.createElementNS(ns, "svg");
    svg.setAttribute("viewBox", "0 0 " + W + " " + H);
    svg.setAttribute("aria-hidden", "true");
    svg.setAttribute("focusable", "false");
    function add(tag, attrs, text) {
      var n = document.createElementNS(ns, tag);
      Object.keys(attrs).forEach(function (k) { n.setAttribute(k, attrs[k]); });
      if (text) n.textContent = text;
      svg.appendChild(n);
      return n;
    }
    add("line", { x1: L, y1: 56, x2: R, y2: 56, "stroke-width": 2, "class": "stroke" });
    add("text", { x: L, y: 14, "class": "axis-text" }, String(min));
    add("text", { x: R, y: 14, "class": "axis-text", "text-anchor": "end" }, String(max));
    items.forEach(function (it) {
      var x = scale(it.y);
      if (it.kind === "event") {
        add("circle", { cx: x, cy: 56, r: 8, "stroke-width": 2, "class": "m-event" });
        add("text", { x: x, y: 40, "text-anchor": "middle", "class": "mark-text" }, it.label);
      } else {
        add("rect", { x: x - 6, y: 74, width: 12, height: 12, transform: "rotate(45 " + x + " 80)", "class": "m-else" });
        add("text", { x: x, y: 106, "text-anchor": "middle", "class": "mark-text" }, it.label);
      }
    });
    return svg;
  }

  // ---- drag and drop (the same actions as tapping) -----------------------------------------------------------
  function startDrag(ev, cardId, slot) {
    try { ev.dataTransfer.setData("text/plain", cardId); ev.dataTransfer.effectAllowed = "move"; } catch (e) { /* ok */ }
    ev.target.classList.add("dragging");
    ev.target.addEventListener("dragend", function () { ev.target.classList.remove("dragging"); }, { once: true });
  }

  // ---- actions ---------------------------------------------------------------------------------------------------
  function placeCard(cardId, slot) {
    var resp = act({ action: "place", event: cardId, slot: slot }, { render: false });
    if (resp && resp.ok) {
      selected = null;
      if (view.first_run) act({ action: "ack" }, { render: false });
      render();
      announce("Placed in slot " + (slot + 1) + ".");
    } else if (resp) render();
  }

  function unplaceSlot(slot) {
    var resp = act({ action: "unplace", slot: slot }, { render: false });
    if (resp && resp.ok) selected = null;
    if (resp) render();
  }

  function onSlot(index) {
    if (!view || view.puzzle.status !== "playing") return;
    var s = view.puzzle.slots[index];
    if (s.locked) { $("message-line").textContent = "That card is locked: it is already in its right place."; return; }
    if (selected) { placeCard(selected.id, index); return; }
    if (s.card) { selected = { id: s.card, slot: index }; render(); announce("Picked up " + view.puzzle.cards[s.card].title + ". Choose a slot, or press Escape."); return; }
    $("message-line").textContent = "Pick up a card from the tray first.";
  }

  function onCard(id) {
    if (!view || view.puzzle.status !== "playing") return;
    if (selected && selected.id === id) selected = null;
    else selected = { id: id, slot: null };
    render();
    if (selected) announce("Picked up " + view.puzzle.cards[id].title + ". Choose a slot, or press Escape.");
  }

  // ---- report a problem (UI only) ----------------------------------------------------------------------------------
  function openReport(claim, opener) {
    currentReport = { claim: claim, opener: opener };
    $("report-claim").textContent = claim.text;
    var reasonSel = clear($("report-reason"));
    var reasons = [
      ["wrong_fact", "The fact looks wrong"], ["wrong_date", "The date looks wrong"],
      ["source_mismatch", "A source does not support the claim"], ["broken_link", "A source link is broken"],
      ["unbalanced", "The wording is unbalanced or unfair"], ["other", "Something else"],
    ];
    reasons.forEach(function (r) { var o = el("option", null, r[1]); o.value = r[0]; reasonSel.appendChild(o); });
    $("report-note").value = "";
    $("report-notice").textContent = "Reporting opens soon. Until then you can prepare a report here; it is saved on this device only and nothing is sent.";
    $("report-payload").hidden = true;
    $("report-copy-button").hidden = true;
    var dlg = $("report-dialog");
    if (dlg.showModal) dlg.showModal(); else dlg.setAttribute("open", "");
    reasonSel.focus();
  }

  function buildReport() {
    if (!currentReport) return;
    var resp = act({ action: "report", set: currentReport.claim.set, claim: currentReport.claim.id, reason: $("report-reason").value, note: $("report-note").value }, { render: false });
    if (!resp) return;
    if (!resp.ok) { $("report-notice").textContent = resp.error; return; }
    var drafts = jsonParse(lsGet(LS_REPORTS) || "[]") || [];
    drafts.push({ saved: new Date().toISOString(), payload: resp.report });
    lsSet(LS_REPORTS, JSON.stringify(drafts.slice(-50)));
    var pre = $("report-payload");
    pre.textContent = JSON.stringify(resp.report, null, 2);
    pre.hidden = false;
    $("report-copy-button").hidden = false;
    $("report-notice").textContent = resp.notice + " (" + Math.min(drafts.length, 50) + " saved draft" + (drafts.length === 1 ? "" : "s") + " on this device.)";
  }

  // ---- archive, info -----------------------------------------------------------------------------------------------
  function openArchive() {
    var resp = act({ action: "archive" }, { render: false });
    if (!resp || !resp.archive) return;
    renderArchive(resp.archive);
  }

  function renderArchive(a) {
    var body = clear($("archive-body"));
    var head = el("div", "meter-wrap");
    var prog = el("progress");
    prog.max = 100; prog.value = a.percent;
    prog.setAttribute("aria-label", "Archive completion");
    head.appendChild(prog);
    head.appendChild(el("span", "meter-text", a.title + ": " + a.found + " of " + a.total + " found (" + a.percent + "%)"));
    body.appendChild(head);
    a.groups.forEach(function (g) {
      var found = g.entries.filter(function (e) { return e.found; }).length;
      var sec = el("div", "arch-group");
      sec.appendChild(el("h3", null, g.title + " (" + found + " of " + g.entries.length + ")"));
      var ul = el("ul", "arch-grid");
      g.entries.forEach(function (e) {
        var li = el("li");
        var b = el("button", "tile " + (e.found ? "found" : "locked"));
        b.type = "button";
        b.setAttribute("data-fk", "tile-" + e.id);
        b.appendChild(glyph(e.kind === "context" ? "context" : e.kind));
        b.appendChild(el("span", "t-title", e.found ? e.title : "Not found yet"));
        b.appendChild(el("span", "t-sub", e.found ? (e.date_label || (e.appears_in && e.appears_in.length ? "In: " + e.appears_in.join(", ") : "")) : "Look in: " + e.hint));
        if (e.found) b.addEventListener("click", function () { openEntry(e.id, sec); });
        else b.setAttribute("aria-disabled", "true");
        li.appendChild(b);
        ul.appendChild(li);
      });
      sec.appendChild(ul);
      body.appendChild(sec);
    });
    if (a.readings.length || a.locked_readings) {
      var rs = el("div", "arch-group");
      rs.appendChild(el("h3", null, "Readings (" + a.readings.length + " of " + (a.readings.length + a.locked_readings) + " unlocked)"));
      a.readings.forEach(function (rd) {
        var box = el("div", "reading");
        box.appendChild(el("strong", null, rd.title));
        box.appendChild(el("p", null, rd.text));
        rd.claims.forEach(function (c) { box.appendChild(claimBlock(c, false)); });
        rs.appendChild(box);
      });
      if (a.locked_readings) rs.appendChild(el("p", "note", a.locked_readings + " more unlock when you clear their sections."));
      body.appendChild(rs);
    }
    body.appendChild(el("div", "arch-detail-slot"));
  }

  function openEntry(id, groupEl) {
    var resp = act({ action: "entry", id: id }, { render: false });
    if (!resp || !resp.entry) return;
    var slot = document.querySelector("#archive-body .arch-detail-slot");
    var box = clear(slot);
    var d = el("div", "arch-detail");
    d.setAttribute("tabindex", "-1");
    var e = resp.entry;
    if (e.kind === "person" || e.kind === "place") {
      d.appendChild(el("h3", null, e.title));
      d.appendChild(el("p", "note", (e.kind === "person" ? "Appears in these moments:" : "Where these moments happened:")));
      var ol = el("ol", "reveal-list");
      e.events.forEach(function (ev) { ol.appendChild(eventBlock(ev)); });
      d.appendChild(ol);
    } else {
      var ol2 = el("ol", "reveal-list");
      ol2.appendChild(eventBlock(e));
      d.appendChild(ol2);
    }
    box.appendChild(d);
    d.focus();
    d.scrollIntoView({ block: "nearest" });
  }

  function openInfo() {
    var resp = act({ action: "info" }, { render: false });
    if (!resp || !resp.info) return;
    var i = resp.info;
    var box = clear($("info-dynamic"));
    box.appendChild(el("h3", null, "This set: " + i.set.title));
    box.appendChild(el("p", "note", i.set.status_label + " · version " + i.set.version + (i.set.drafted ? " · drafted " + i.set.drafted : "") + " · " + i.counts.events + " events (presidential moments plus things that happened elsewhere), " + i.counts.claims + " claims, " + i.counts.sources + " different sources."));
    box.appendChild(el("h3", null, "How sure are the sources?"));
    var ul = el("ul", "info-list");
    i.legend.forEach(function (l) { var li = el("li"); li.appendChild(el("strong", null, l.symbol + " " + l.label + ": ")); li.appendChild(document.createTextNode(l.meaning)); ul.appendChild(li); });
    box.appendChild(ul);
    box.appendChild(el("h3", null, "Sources for what you have found (" + i.found_claims.length + " moments)"));
    if (!i.found_claims.length) box.appendChild(el("p", "note", "Nothing found yet. Solve a puzzle and its claims and sources appear here."));
    i.found_claims.forEach(function (f) {
      var wrap = el("div", "reveal");
      wrap.appendChild(el("div", "when", f.date_label));
      wrap.appendChild(el("h3", null, f.title));
      f.claims.forEach(function (c) { wrap.appendChild(claimBlock(c)); });
      box.appendChild(wrap);
    });
  }

  // ---- wiring -----------------------------------------------------------------------------------------------------
  function togglePanel(btnId, panelId, onOpen) {
    $(btnId).addEventListener("click", function () {
      var panel = $(panelId);
      panel.hidden = !panel.hidden;
      $(btnId).setAttribute("aria-expanded", String(!panel.hidden));
      if (!panel.hidden) {
        if (onOpen) onOpen();
        if (!engineReady) startEngine();
      }
    });
  }

  function wire() {
    togglePanel("archive-toggle-button", "archive-panel", function () { if (engineReady) openArchive(); });
    togglePanel("achievements-toggle-button", "achievements-panel", renderAchievements);
    togglePanel("changelog-toggle-button", "changelog-panel");
    togglePanel("info-page-toggle-button", "info-page-panel", function () { if (engineReady) openInfo(); });

    $("slots").addEventListener("click", function (ev) {
      var b = ev.target.closest(".slot");
      if (b) onSlot(parseInt(b.getAttribute("data-slot"), 10));
    });
    $("slots").addEventListener("dragover", function (ev) { if (ev.target.closest(".slot")) ev.preventDefault(); });
    $("slots").addEventListener("drop", function (ev) {
      var b = ev.target.closest(".slot");
      if (!b) return;
      ev.preventDefault();
      var id = ev.dataTransfer.getData("text/plain");
      if (id && view && view.puzzle.status === "playing" && !view.puzzle.slots[parseInt(b.getAttribute("data-slot"), 10)].locked) placeCard(id, parseInt(b.getAttribute("data-slot"), 10));
    });
    $("tray").addEventListener("click", function (ev) {
      var c = ev.target.closest(".card");
      if (c) { onCard(c.getAttribute("data-card")); return; }
      if (selected && selected.slot !== null) unplaceSlot(selected.slot);
    });
    $("tray").addEventListener("dragover", function (ev) { ev.preventDefault(); });
    $("tray").addEventListener("drop", function (ev) {
      ev.preventDefault();
      var id = ev.dataTransfer.getData("text/plain");
      if (!id || !view) return;
      var s = view.puzzle.slots.filter(function (x) { return x.card === id && !x.locked; })[0];
      if (s) unplaceSlot(s.index);
    });
    $("return-button").addEventListener("click", function () { if (selected && selected.slot !== null) unplaceSlot(selected.slot); });

    $("check-button").addEventListener("click", function () {
      if (!view) return;
      if (!view.puzzle.all_placed) { $("message-line").textContent = "Fill every slot before checking."; announce("Fill every slot before checking."); return; }
      selected = null;
      var resp = act({ action: "check" });
      if (resp && resp.ok) announce(view.puzzle.message);
      if (view.result) $("result-panel").scrollIntoView({ block: "nearest" });
    });
    $("show-answer-button").addEventListener("click", function () {
      var go = function () { selected = null; act({ action: "show_answer" }); };
      if (window.ConfirmDialog) window.ConfirmDialog.ask({ id: "chronicle-show-answer", message: "Show the answer? Nothing from this puzzle will be added to your archive.", confirmLabel: "Show the answer", allowSkip: true, onConfirm: go });
      else go();
    });
    $("next-button").addEventListener("click", function () { selected = null; act({ action: "next" }); $("puzzle-panel").scrollIntoView({ block: "nearest" }); });

    $("sections").addEventListener("click", function (ev) {
      var b = ev.target.closest(".section-card");
      if (!b) return;
      if (b.getAttribute("aria-disabled") === "true") { $("message-line").textContent = "That section is locked. " + b.querySelectorAll(".sc-meta")[0].textContent + "."; return; }
      selected = null;
      act({ action: "start", section: b.getAttribute("data-section") });
    });
    $("set-select").addEventListener("change", function (ev) { selected = null; act({ action: "choose_set", set: ev.target.value }); });

    $("report-build-button").addEventListener("click", buildReport);
    $("report-copy-button").addEventListener("click", function () {
      var text = $("report-payload").textContent;
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(function () { $("report-notice").textContent = "Report text copied."; }, function () { $("report-notice").textContent = "Select the text above and copy it by hand."; });
      else $("report-notice").textContent = "Select the text above and copy it by hand.";
    });
    $("report-dialog").addEventListener("close", function () { if (currentReport && currentReport.opener && document.body.contains(currentReport.opener)) currentReport.opener.focus(); });

    $("hints-checkbox").addEventListener("change", function (ev) { act({ action: "settings", hints: ev.target.checked }); });
    $("reset-progress-button").addEventListener("click", function () {
      var go = function () {
        lsRemove(LS_STATE); lsRemove(LS_VIEW);
        selected = null;
        if (act({ action: "reset" })) { persistState(); showToast("Progress erased."); }
      };
      if (window.ConfirmDialog) window.ConfirmDialog.ask({ id: "chronicle-reset", message: "Erase ALL Chronicle progress in this browser (archive, solved puzzles, achievements)? A save code you already made can still restore it.", confirmLabel: "Erase everything", allowSkip: false, onConfirm: go });
      else go();
    });

    document.addEventListener("keydown", onKey);
    var kick = function () { startEngine(); };
    document.addEventListener("pointerdown", kick, { once: true });
    document.addEventListener("keydown", kick, { once: true });
  }

  function onKey(ev) {
    if (ev.ctrlKey || ev.metaKey || ev.altKey || !view || view.empty) return;
    var tag = (ev.target && ev.target.tagName) || "";
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
    if (ev.target.closest && ev.target.closest("dialog[open]")) return;
    if (ev.key === "Escape" && selected) { selected = null; render(); announce("Put the card down."); return; }
    if (/^[1-8]$/.test(ev.key) && selected) {
      var n = parseInt(ev.key, 10) - 1;
      if (n < view.puzzle.size) { ev.preventDefault(); onSlot(n); }
      return;
    }
    if ((ev.key === "Delete" || ev.key === "Backspace") && ev.target.classList && ev.target.classList.contains("slot")) {
      var i = parseInt(ev.target.getAttribute("data-slot"), 10);
      var s = view.puzzle.slots[i];
      if (s && s.card && !s.locked && view.puzzle.status === "playing") { ev.preventDefault(); unplaceSlot(i); }
      return;
    }
    if (ev.target.classList && ev.target.classList.contains("slot") && /^Arrow/.test(ev.key)) {
      var cur = parseInt(ev.target.getAttribute("data-slot"), 10);
      var next = (ev.key === "ArrowRight" || ev.key === "ArrowDown") ? cur + 1 : cur - 1;
      var t = document.querySelector('[data-slot="' + next + '"]');
      if (t) { ev.preventDefault(); t.focus(); }
    }
  }

  // Called by game.py's load_state() after the save widget loads a save.
  window.chronicleOnStateLoaded = function () {
    if (!engineReady) return;
    selected = null;
    applyResponse(send({ action: "boot" }));
    persistState();
    showToast("Save loaded.");
  };

  function init() {
    wire();
    var cached = jsonParse(lsGet(LS_VIEW) || "null");
    if (cached && cached.puzzle && cached.set) {
      view = cached;
      render();
      setStatus("Warming up the archive... (showing where you left off)");
    } else {
      setStatus("Warming up the archive...");
      renderStaticPlaceholder();
    }
    setTimeout(startEngine, 0);
  }

  function renderStaticPlaceholder() {
    $("puzzle-meta").textContent = "The first puzzle appears when the archive has warmed up.";
    $("check-button").setAttribute("aria-disabled", "true");
    $("show-answer-button").hidden = true;
  }

  window.ChronicleApp = { act: act, getView: function () { return view; }, startEngine: startEngine, isReady: function () { return engineReady; } };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
