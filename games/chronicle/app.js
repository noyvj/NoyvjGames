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
 * The only logic here is presentation: which card is picked up, where things are drawn, the nuance strip, the
 * cause web's arcs, the myth-or-record bins, the whose-account questions, the decision options and the review card.
 * Nothing in this file posts to a backend. "Report a problem" builds a payload with the engine, saves a draft
 * on this device and says reporting opens soon.
 */
(function () {
  "use strict";

  var GAME = "chronicle";
  var PYODIDE_URL = "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js";
  var ENGINE_MODULES = ["setdata.py", "puzzle.py", "web.py", "myth.py", "account.py", "decision.py", "review.py", "achievements.py", "report.py"];
  var SET_FILES = ["meta", "sources", "entities", "claims", "relations", "sections", "readings"];
  var OPTIONAL_SET_FILES = ["chapters", "accounts", "decisions"];   // chapters, accounts and decision points: a set may have none of them
  var LS_STATE = "chronicle:state";
  var LS_VIEW = "chronicle:lastview";
  var LS_REPORTS = "chronicle:report-drafts";

  var $ = function (id) { return document.getElementById(id); };
  var api = null, getStateFn = null;
  var engineReady = false, engineStarting = false;
  var view = null;
  var selected = null;               // { id, slot } : the card picked up (slot is null when it is in the tray)
  var webPick = null;                // the cause-web card picked up as the cause (the next card is the effect)
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
  function plural(n, word) { return n + " " + word + (n === 1 ? "" : "s"); }
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
        for (var o = 0; o < OPTIONAL_SET_FILES.length; o++) {
          var optPath = "sets/" + folders[f] + "/" + OPTIONAL_SET_FILES[o] + ".json";
          var optResp = await fetch(optPath);
          if (optResp.ok) pyodide.FS.writeFile(root + "/" + optPath, await optResp.text(), { encoding: "utf8" });
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
    { title: "Six ways to play", selector: "#mode-tabs", text: "Timeline puts moments in order. Cause web asks which moment helped lead to which. Myth or record sorts statements by how sure the sources are. Whose account? weighs who is telling the story. Decision points show a choice someone really faced. Review brings back what you have learned. Most have chapters that open as you find the moments they use." },
    { title: "Cause web", selector: "#mode-web-button", text: "Pick the earlier moment, then the one it led to. The game confirms a thread only if the set's sources link them, and says how strong the evidence is. Causes are plural: most moments have more than one." },
    { title: "Myth or record", selector: "#mode-myth-button", text: "Each statement is documented, disputed, or a story the sources do not support. Sort them, check, and read why from the sources themselves. Number keys 1, 2 and 3 sort the claim you are on." },
    { title: "Whose account?", selector: "#mode-account-button", text: "Read short passages about one event, each a summary of a different real source. Say who wrote the one marked with a diamond, what they could see, what they wanted, and what the passage leaves out. Primary sources were made at the time; secondary ones were written afterwards." },
    { title: "Decision points", selector: "#mode-decision-button", text: "See a choice a historical figure really faced, only where the sources document the options. Pick what you would do. Nothing is graded: the game then shows what they chose and what followed, never what might have happened." },
    { title: "Review", selector: "#mode-review-button", text: "Facts you have learned come back after gaps that grow each time you remember one. Days only move when you press Let a day pass, so there is no clock and nothing runs out while you are away. A fact you miss simply comes back tomorrow." },
    { title: "Your archive", selector: "#archive-toggle-button", text: "Everything you find fills in the archive: moments, what else was happening, people, places, cause links and sorted claims. It is easy to reach 100%." },
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
    if (copy.web && copy.web.result) copy.web.result = null;
    if (copy.myth && copy.myth.result) copy.myth.result = null;
    if (copy.account && copy.account.result) copy.account.result = null;
    if (copy.decision && copy.decision.result) copy.decision.result = null;
    if (copy.review && copy.review.feedback) copy.review.feedback = null;
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
    renderModeTabs();
    renderSections();
    renderPuzzle();
    renderResult();
    renderWeb();
    renderMyth();
    renderAccount();
    renderDecision();
    renderReview();
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

  function currentMode() { return (view && view.mode) || "timeline"; }

  var MODE_IDS = ["timeline", "web", "myth", "account", "decision", "review"];
  var MODE_KEYS = { t: "timeline", w: "web", m: "myth", a: "account", d: "decision", r: "review" };
  var MODE_LABELS = { timeline: "Timeline", web: "Cause web", myth: "Myth or record", account: "Whose account?", decision: "Decision points", review: "Review" };
  var MODE_PANELS = { timeline: "puzzle-panel", web: "web-panel", myth: "myth-panel", account: "account-panel", decision: "decision-panel", review: "review-panel" };
  var MODE_SKIP = { timeline: "Skip to the timeline", web: "Skip to the cause web", myth: "Skip to myth or record", account: "Skip to whose account", decision: "Skip to decision points", review: "Skip to review" };

  function renderModeTabs() {
    var mode = currentMode();
    var modes = view.modes || [{ id: "timeline", label: "Timeline", available: true }];
    MODE_IDS.forEach(function (id) {
      var b = $("mode-" + id + "-button");
      var info = modes.filter(function (m) { return m.id === id; })[0];
      var available = !!(info && info.available);
      b.setAttribute("aria-selected", String(mode === id));
      b.setAttribute("tabindex", mode === id ? "0" : "-1");
      b.setAttribute("aria-disabled", String(!available));
      b.textContent = MODE_LABELS[id] + (available ? "" : " (not in this set)");
    });
    $("puzzle-panel").hidden = mode !== "timeline";
    $("web-panel").hidden = mode !== "web";
    $("myth-panel").hidden = mode !== "myth";
    $("account-panel").hidden = mode !== "account";
    $("decision-panel").hidden = mode !== "decision";
    $("review-panel").hidden = mode !== "review";
    var panelId = MODE_PANELS[mode] || "puzzle-panel";
    $("skip-link").setAttribute("href", "#" + panelId);
    $("skip-link").textContent = MODE_SKIP[mode] || "Skip to the timeline";
  }

  var CHAPTER_LABELS = { web: "Cause web chapters", myth: "Myth or record chapters", account: "Accounts", decision: "Decision points" };

  function renderChapters(list, kind) {
    var nav = clear($("sections"));
    nav.setAttribute("aria-label", CHAPTER_LABELS[kind]);
    var board = kind === "web" ? view.web : (kind === "myth" ? view.myth : (kind === "account" ? view.account : view.decision));
    var current = board && (kind === "account" ? board.account : (kind === "decision" ? board.id : board.chapter));
    (list || []).forEach(function (c) {
      var b = el("button", "section-card");
      b.type = "button";
      b.setAttribute("data-fk", "chapter-" + c.id);
      b.setAttribute("data-chapter", c.id);
      b.setAttribute("data-kind", kind);
      if (c.id === current) b.setAttribute("aria-current", "true");
      if (!c.unlocked) b.setAttribute("aria-disabled", "true");
      b.appendChild(el("span", "sc-title", (c.cleared ? "✔ " : (c.unlocked ? "" : "🔒 ")) + c.title));
      b.appendChild(el("span", "sc-meta", c.unlocked ? (c.progress + (c.cleared ? " (cleared)" : "")) : "Locked: " + c.requires_text));
      b.appendChild(el("span", "sc-meta", c.blurb));
      nav.appendChild(b);
    });
  }

  function renderSections() {
    var mode = currentMode();
    $("sections").hidden = false;
    if (mode === "web") { renderChapters(view.webs, "web"); return; }
    if (mode === "myth") { renderChapters(view.myths, "myth"); return; }
    if (mode === "account") { renderChapters(view.accounts, "account"); return; }
    if (mode === "decision") { renderChapters(view.decisions, "decision"); return; }
    if (mode === "review") { clear($("sections")).hidden = true; return; }
    $("sections").hidden = false;
    var nav = clear($("sections"));
    nav.setAttribute("aria-label", "Sections");
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
    var who = (claim.institutions || []).join("; ");
    d.appendChild(el("summary", null, "Sources (" + claim.sources.length + ")" + (who ? ": " + who : "")));
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
      if (d.open && d.getAttribute("data-skip-view") === "1") return;   // opened in bulk by the Info page: not a deliberate read
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
      relation: '<circle cx="7" cy="22" r="4"/><circle cx="25" cy="10" r="4"/><path d="M10 19C14 14 17 12 20 11M17 8l4 3-3 4"/>',
      record: '<path d="M16 4v22M7 26h18M6 10h20M6 10l-3 8h6zM26 10l-3 8h6z"/>',
      account: '<rect x="4" y="5" width="15" height="21" rx="2"/><rect x="13" y="9" width="15" height="19" rx="2"/><path d="M17 15h8M17 20h8"/>',
      decision: '<path d="M16 28V16M16 16L7 7M16 16l9-9M7 7v6M7 7h6M25 7v6M25 7h-6"/>',
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
    if (!r || currentMode() !== "timeline") { panel.hidden = true; clear($("result-body")); return; }
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

  // ---- cause web ----------------------------------------------------------------------------------------------
  // Strength is drawn three ways at once, never by colour alone: a symbol (⇒ direct, ⇢ contributing), the words
  // "Direct cause" / "Contributing cause", and a line style (solid thick against dashed) in the diagram.
  function threadBlock(t, opts) {
    opts = opts || {};
    var li = el("li", "thread " + t.strength);
    var head = el("div", "thread-head");
    head.appendChild(el("strong", null, (opts.numbers ? opts.numbers[t.from] + ". " : "") + t.from_title + " " + t.strength_symbol + " " + (opts.numbers ? opts.numbers[t.to] + ". " : "") + t.to_title));
    li.appendChild(head);
    var tags = el("div", "thread-tags");
    var st = el("span", "strength " + t.strength, t.strength_symbol + " " + t.strength_label);
    st.setAttribute("title", t.strength_note);
    tags.appendChild(st);
    li.appendChild(tags);
    li.appendChild(el("p", "note", t.strength_note));
    li.appendChild(el("p", "plural", t.plural_note));
    li.appendChild(claimBlock(t.claim));
    return li;
  }

  function renderWeb() {
    var panel = $("web-panel");
    if (currentMode() !== "web") return;
    var w = view.web;
    var body = clear($("web-cards"));
    clear($("web-diagram"));
    clear($("web-threads"));
    clear($("web-result"));
    var meta = $("web-meta");
    if (!w || w.locked) {
      meta.textContent = (w && w.message) || "The cause web opens when you have found the moments a chapter uses.";
      $("web-board").hidden = true;
      return;
    }
    $("web-board").hidden = false;
    meta.textContent = w.chapter_title + " · " + w.round_label + " · " + w.size + " moments · " + w.links_total + (w.links_total === 1 ? " link" : " links") + " to find, " + w.links_found + " found" + (w.misses ? " · " + w.misses + " unconfirmed " + (w.misses === 1 ? "thread" : "threads") : "");
    var finished = w.status !== "playing";
    var numbers = {};
    w.cards.forEach(function (c) { numbers[c.id] = c.n; });
    if (webPick && !w.cards.some(function (c) { return c.id === webPick; })) webPick = null;
    w.cards.forEach(function (c) {
      var li = el("li", "web-item");
      var b = el("button", "web-card");
      b.type = "button";
      b.setAttribute("data-wcard", c.id);
      b.setAttribute("data-fk", "wcard-" + c.id);
      var picked = webPick === c.id;
      b.setAttribute("aria-pressed", String(picked));
      b.setAttribute("aria-label", "Moment " + c.n + " of " + w.size + ": " + c.title + (picked ? ". Picked up as the cause. Now pick the moment it led to." : ""));
      b.appendChild(el("span", "web-num", String(c.n)));
      b.appendChild(el("span", "web-title", c.title));
      b.appendChild(el("span", "web-state", picked ? "▶ Cause picked up" : (webPick ? "Tap: it led to this" : "Tap to pick as the cause")));
      if (finished) b.setAttribute("aria-disabled", "true");
      li.appendChild(b);
      body.appendChild(li);
    });
    var found = w.status === "playing" ? w.found : ((w.result && w.result.threads) || w.found);
    $("web-diagram").appendChild(webSvg(w, found, numbers));
    var tl = $("web-threads");
    if (!found.length) tl.appendChild(el("li", "note", "No thread drawn yet."));
    found.forEach(function (t) { tl.appendChild(threadBlock(t, { numbers: numbers })); });
    (w.tries || []).forEach(function (t) {
      var li = el("li", "thread tried");
      li.appendChild(el("span", "strength", "✖ Not confirmed"));
      li.appendChild(document.createTextNode(" " + numbers[t.from] + ". " + t.from_title + " → " + numbers[t.to] + ". " + t.to_title + (t.verdict === "reversed" ? ": the sources link them the other way round." : ": none of this set's sources join them. That does not mean they are unrelated.")));
      tl.appendChild(li);
    });
    $("web-message").textContent = w.message || (view.first_run ? "Pick the earlier moment first, then the one it led to." : "");
    $("web-show-button").hidden = finished;
    $("web-cancel-button").hidden = !webPick;
    $("web-next-button").hidden = !finished;
    if (finished && w.result) {
      var res = $("web-result");
      res.appendChild(el("h3", null, w.result.solved ? "Every link in this puzzle is found" : "The links"));
      if (w.result.chapter_cleared) res.appendChild(el("p", "message-line", "✔ Chapter cleared: every link in it is in your archive."));
      res.appendChild(el("p", "note", "Causes are plural. Each link above is one cause among several, and a link marked disputed is one where the sources differ on how much it mattered."));
    }
  }

  // The board as arcs over a line of numbered moments (earliest left): arrowhead at the effect; solid thick line =
  // direct cause, dashed line = contributing cause. aria-hidden: the same facts are written out in the thread list.
  function webSvg(w, threads, numbers) {
    var ns = "http://www.w3.org/2000/svg";
    var W = 600, H = 150, L = 50, R = W - 50, base = 112;
    var svg = document.createElementNS(ns, "svg");
    svg.setAttribute("viewBox", "0 0 " + W + " " + H);
    svg.setAttribute("aria-hidden", "true");
    svg.setAttribute("focusable", "false");
    svg.setAttribute("class", "web-svg");
    function add(tag, attrs, text, parent) {
      var n = document.createElementNS(ns, tag);
      Object.keys(attrs).forEach(function (k) { n.setAttribute(k, attrs[k]); });
      if (text) n.textContent = text;
      (parent || svg).appendChild(n);
      return n;
    }
    var defs = add("defs", {});
    var mk = add("marker", { id: "web-arrow", viewBox: "0 0 10 10", refX: "8", refY: "5", markerWidth: "7", markerHeight: "7", orient: "auto-start-reverse" }, null, defs);
    add("path", { d: "M0 0 L10 5 L0 10 z", "class": "arrow-fill" }, null, mk);
    var xs = {};
    var n = w.cards.length;
    w.cards.forEach(function (c, i) { xs[c.id] = n === 1 ? W / 2 : L + (R - L) * i / (n - 1); });
    add("line", { x1: L - 20, y1: base, x2: R + 20, y2: base, "class": "stroke", "stroke-width": 2 });
    threads.forEach(function (t, idx) {
      var x1 = xs[t.from], x2 = xs[t.to];
      var mid = (x1 + x2) / 2;
      var rise = 20 + Math.min(70, Math.abs(x2 - x1) * 0.28);
      var cls = "arc " + t.strength + (idx === threads.length - 1 ? " fresh" : "");
      add("path", { d: "M" + x1 + " " + (base - 10) + " Q" + mid + " " + (base - 10 - rise * 2) + " " + (x2 - (x2 > x1 ? 4 : -4)) + " " + (base - 12), "class": cls, "marker-end": "url(#web-arrow)", fill: "none" });
    });
    w.cards.forEach(function (c) {
      add("circle", { cx: xs[c.id], cy: base, r: 11, "class": "m-event", "stroke-width": 2 });
      add("text", { x: xs[c.id], y: base + 4, "text-anchor": "middle", "class": "mark-text" }, String(c.n));
    });
    return svg;
  }

  function onWebCard(id) {
    if (!view || !view.web || view.web.status !== "playing") return;
    if (!webPick) { webPick = id; renderWeb(); announce("Picked up " + cardTitle(id) + " as the cause. Now pick the moment it led to, or press Escape."); return; }
    if (webPick === id) { webPick = null; renderWeb(); announce("Put the card down."); return; }
    var from = webPick;
    webPick = null;
    var resp = act({ action: "web_link", from: from, to: id });
    if (resp && resp.ok) announce(view.web.message);
  }

  function cardTitle(id) {
    var c = view.web.cards.filter(function (x) { return x.id === id; })[0];
    return c ? c.title : id;
  }

  // ---- myth or record -----------------------------------------------------------------------------------------
  // The three bins are written out (symbol + words) and drawn with three border styles, so colour is never needed.
  function renderMyth() {
    if (currentMode() !== "myth") return;
    var m = view.myth;
    var list = clear($("myth-cards"));
    clear($("myth-result"));
    var legend = clear($("myth-legend"));
    if (!m || m.locked) {
      $("myth-meta").textContent = (m && m.message) || "Myth or record opens when you have found the moments a chapter uses.";
      $("myth-board").hidden = true;
      return;
    }
    $("myth-board").hidden = false;
    $("myth-meta").textContent = m.chapter_title + " · " + m.round_label + " · " + m.size + " statements" + (m.checks ? " · " + m.checks + (m.checks === 1 ? " check" : " checks") : "");
    m.bins.forEach(function (b) {
      var li = el("li");
      li.appendChild(el("strong", null, b.symbol + " " + b.label + ": "));
      li.appendChild(document.createTextNode(b.meaning));
      legend.appendChild(li);
    });
    var finished = m.status !== "playing";
    m.claims.forEach(function (c, i) {
      var li = el("li", "myth-card" + (c.locked ? " right" : (c.status === "wrong" ? " wrong" : "")));
      li.setAttribute("data-claim", c.id);
      li.setAttribute("tabindex", "0");
      li.setAttribute("data-fk", "mcard-" + c.id);
      li.setAttribute("aria-label", "Statement " + (i + 1) + " of " + m.size + ": " + c.text + (c.bin ? " Sorted as " + binLabel(m, c.bin) + (c.locked ? ", right, locked" : (c.status === "wrong" ? ", not right yet" : "")) : " Not sorted yet. Press 1, 2 or 3 to sort it."));
      li.appendChild(el("span", "myth-about", "Statement " + (i + 1) + " · about: " + c.subject_title));
      li.appendChild(el("p", "myth-text", c.text));
      var group = el("div", "bin-row");
      group.setAttribute("role", "group");
      group.setAttribute("aria-label", "Sort statement " + (i + 1));
      m.bins.forEach(function (b, bi) {
        var btn = el("button", "bin-btn " + b.id, (bi + 1) + ". " + b.symbol + " " + b.label);
        btn.type = "button";
        btn.setAttribute("data-bin", b.id);
        btn.setAttribute("data-claim", c.id);
        btn.setAttribute("data-fk", "mbin-" + c.id + "-" + b.id);
        btn.setAttribute("aria-pressed", String(c.bin === b.id));
        if (c.locked || finished) btn.setAttribute("aria-disabled", "true");
        group.appendChild(btn);
      });
      li.appendChild(group);
      var state = c.locked ? "✔ Right bin (locked)" : (c.status === "wrong" ? "✖ Not this bin yet" : (c.bin ? "Sorted, not checked" : "Not sorted yet"));
      li.appendChild(el("span", "slot-state", state));
      list.appendChild(li);
    });
    $("myth-message").textContent = m.message || (view.first_run ? "Pick a bin under each statement, then press Check." : "");
    var check = $("myth-check-button");
    check.hidden = finished;
    check.setAttribute("aria-disabled", String(!m.all_sorted));
    check.textContent = m.all_sorted ? "Check" : "Check (sort every statement first)";
    $("myth-show-button").hidden = finished;
    $("myth-next-button").hidden = !finished;
    if (finished && m.result) {
      var res = $("myth-result");
      res.appendChild(el("h3", null, m.result.solved ? "What the sources say" : "The answer"));
      if (m.result.new_count) res.appendChild(el("p", "note", m.result.new_count + (m.result.new_count === 1 ? " claim" : " claims") + " added to your archive from this puzzle."));
      if (m.result.chapter_cleared) res.appendChild(el("p", "message-line", "✔ Chapter cleared: every claim in it is sorted."));
      var ol = el("ol", "reveal-list");
      m.result.claims.forEach(function (c) {
        var li = el("li", "reveal" + (c.new ? " fresh" : ""));
        if (c.short) li.appendChild(el("div", "when", c.short));
        li.appendChild(claimBlock(c));
        li.appendChild(el("p", "why", "Why: " + c.explanation));
        ol.appendChild(li);
      });
      res.appendChild(ol);
    }
  }

  function binLabel(m, id) {
    var b = m.bins.filter(function (x) { return x.id === id; })[0];
    return b ? b.label : id;
  }

  function sortClaim(claimId, bin) {
    if (!view || !view.myth || view.myth.status !== "playing") return;
    var resp = act({ action: "myth_sort", claim: claimId, bin: bin });
    if (resp && resp.ok) announce("Sorted as " + binLabel(view.myth, bin) + ".");
  }


  // ---- whose account? -----------------------------------------------------------------------------------------
  // Every question is a choice from a fixed list the engine built from the passage's own metadata (no typing).
  // State is written ("Right answer (locked)", "Not this one yet") and drawn with border styles, never colour alone.
  function renderAccount() {
    if (currentMode() !== "account") return;
    var a = view.account;
    var plist = clear($("account-passages"));
    var qlist = clear($("account-questions"));
    clear($("account-result"));
    if (!a || a.locked) {
      $("account-meta").textContent = (a && a.message) || "Whose account? opens when you have found the moment an account is about.";
      $("account-board").hidden = true;
      return;
    }
    $("account-board").hidden = false;
    $("account-meta").textContent = a.account_title + " · " + a.round_label + " · about: " + a.event_title + " (" + a.event_date + ")" + (a.checks ? " · " + a.checks + (a.checks === 1 ? " check" : " checks") : "");
    a.passages.forEach(function (ps) {
      var li = el("li", "passage" + (ps.focus ? " focus" : ""));
      li.appendChild(el("h3", null, "Passage " + ps.letter + (ps.focus ? " ◆ the questions are about this one" : "")));
      li.appendChild(el("p", null, ps.text));
      plist.appendChild(li);
    });
    var finished = a.status !== "playing";
    a.questions.forEach(function (q, i) {
      var li = el("li", "acct-q" + (q.locked ? " right" : (q.status === "wrong" ? " wrong" : "")));
      li.setAttribute("data-q", q.id);
      li.setAttribute("tabindex", "0");
      li.setAttribute("data-fk", "aq-" + q.id);
      var chosen = q.options.filter(function (o) { return o.id === q.choice; })[0];
      li.setAttribute("aria-label", "Question " + (i + 1) + " of " + a.size + ": " + q.prompt + (chosen ? " Chosen: " + chosen.label + (q.locked ? ", right, locked" : (q.status === "wrong" ? ", not right yet" : "")) : " Not answered yet. Press 1 to " + q.options.length + " to choose."));
      li.appendChild(el("p", "acct-prompt", (i + 1) + ". " + q.prompt));
      var group = el("div", "opt-row");
      group.setAttribute("role", "group");
      group.setAttribute("aria-label", q.prompt);
      q.options.forEach(function (o, oi) {
        var btn = el("button", "opt-btn", (oi + 1) + ". " + o.label);
        btn.type = "button";
        btn.setAttribute("data-q", q.id);
        btn.setAttribute("data-opt", o.id);
        btn.setAttribute("data-fk", "aopt-" + q.id + "-" + o.id);
        btn.setAttribute("aria-pressed", String(q.choice === o.id));
        if (q.locked || finished) btn.setAttribute("aria-disabled", "true");
        group.appendChild(btn);
      });
      li.appendChild(group);
      li.appendChild(el("span", "slot-state", q.locked ? "✔ Right answer (locked)" : (q.status === "wrong" ? "✖ Not this one yet" : (q.choice ? "Chosen, not checked" : "Not answered yet"))));
      qlist.appendChild(li);
    });
    $("account-message").textContent = a.message || (view.first_run ? "Read the passages, then answer each question about the one marked with a diamond." : "");
    var check = $("account-check-button");
    check.hidden = finished;
    check.setAttribute("aria-disabled", String(!a.all_answered));
    check.textContent = a.all_answered ? "Check" : "Check (answer every question first)";
    $("account-show-button").hidden = finished;
    $("account-next-button").hidden = !finished;
    if (finished && a.result) renderAccountResult($("account-result"), a.result, a);
  }

  function passageReveal(p, focusLetter) {
    var box = el("div", "reveal passage-reveal" + (p.letter === focusLetter ? " focus" : ""));
    box.appendChild(el("div", "when", "Passage " + p.letter + (p.letter === focusLetter ? " ◆" : "")));
    box.appendChild(el("h3", null, p.author + ", " + p.written_label));
    box.appendChild(el("p", "note", p.kind_label));
    box.appendChild(el("p", null, "What the writer could see: " + p.vantage_label + "."));
    box.appendChild(el("p", null, "What the writer was trying to do: " + p.purpose_label + "."));
    box.appendChild(el("p", "why", "Why we say so: " + p.purpose_note));
    var src = el("p", "note");
    src.appendChild(document.createTextNode("Source: "));
    var link = el("a", null, p.source.title);
    link.href = p.source.url; link.target = "_blank"; link.rel = "noopener noreferrer";
    src.appendChild(link);
    src.appendChild(document.createTextNode(" (" + p.source.institution + ", read " + p.source.read + ")"));
    box.appendChild(src);
    box.appendChild(el("p", "note", "This passage mentions: " + (p.mentions.length ? p.mentions.join("; ") : "none of the listed facts") + "."));
    box.appendChild(el("p", "note", "This passage leaves out: " + (p.leaves_out.length ? p.leaves_out.join("; ") : "nothing on the list") + "."));
    return box;
  }

  function renderAccountResult(res, r, a) {
    res.appendChild(el("h3", null, r.solved ? "The sources behind the passages" : "The answers"));
    if (r.solved) res.appendChild(el("p", "message-line", "✔ Source judged: Passage " + r.focus_letter + " is added to your archive."));
    if (r.account_cleared) res.appendChild(el("p", "message-line", "✔ Every source of this account is judged."));
    var answers = el("ul", "info-list");
    a.questions.forEach(function (q) {
      var c = r.correct.filter(function (x) { return x.id === q.id; })[0];
      if (c) answers.appendChild(el("li", null, q.prompt + " " + c.label));
    });
    res.appendChild(answers);
    var wrap = el("div", "reveal-list");
    r.passages.forEach(function (p) { wrap.appendChild(passageReveal(p, r.focus_letter)); });
    res.appendChild(wrap);
    res.appendChild(el("p", "note", "The passages are short summaries written for this game, not quotations. \"Leaves out\" is judged against the summary you read; the full source usually says more, so open it to read for yourself."));
    res.appendChild(el("h3", null, "The facts these accounts are about"));
    var ul = el("ul", "info-list");
    r.points.forEach(function (pt) {
      var li = el("li");
      li.appendChild(el("strong", null, pt.label));
      li.appendChild(claimBlock(pt.claim));
      ul.appendChild(li);
    });
    res.appendChild(ul);
  }

  function answerAccount(qid, opt) {
    if (!view || !view.account || view.account.status !== "playing") return;
    var resp = act({ action: "account_answer", question: qid, choice: opt });
    if (resp && resp.ok) announce("Chosen.");
  }

  // ---- decision points ----------------------------------------------------------------------------------------
  function renderDecision() {
    if (currentMode() !== "decision") return;
    var d = view.decision;
    var opts = clear($("decision-options"));
    clear($("decision-situation"));
    clear($("decision-result"));
    if (!d || d.locked) {
      $("decision-meta").textContent = (d && d.message) || "Decision points open when you have found the moment they are about.";
      $("decision-board").hidden = true;
      return;
    }
    $("decision-board").hidden = false;
    $("decision-meta").textContent = d.title + " · " + d.who + ", " + d.when;
    var sit = $("decision-situation");
    sit.appendChild(el("h3", null, "The situation"));
    sit.appendChild(claimBlock(d.situation));
    $("decision-question").textContent = d.question;
    d.options.forEach(function (o, i) {
      var li = el("li");
      var b = el("button", "opt-btn", (i + 1) + ". " + o.text);
      b.type = "button";
      b.setAttribute("data-opt", o.id);
      b.setAttribute("data-fk", "dopt-" + o.id);
      b.setAttribute("aria-pressed", String(!!o.picked));
      if (d.decided) b.setAttribute("aria-disabled", "true");
      li.appendChild(b);
      var marks = [];
      if (o.picked) marks.push("◆ You chose this");
      if (d.result && d.result.chosen === o.id) marks.push("★ " + d.result.chose_label + " (labelled as what they chose, not as the best choice)");
      if (marks.length) li.appendChild(el("span", "slot-state", marks.join(" · ")));
      opts.appendChild(li);
    });
    $("decision-message").textContent = d.decided ? "You made your choice. What happened is below." : (view.first_run ? "Pick an option. There is no right answer." : "");
    var r = d.result;
    if (d.decided && r) {
      var res = $("decision-result");
      res.appendChild(el("h3", null, r.chose_label + ": " + r.chosen_text));
      res.appendChild(claimBlock(r.choice_claim));
      res.appendChild(el("h3", null, r.after_label));
      res.appendChild(claimBlock(r.after_claim));
      res.appendChild(el("p", "note", r.note));
    }
  }

  function pickDecision(optId) {
    if (!view || !view.decision || view.decision.decided) return;
    var resp = act({ action: "decision_pick", option: optId });
    if (resp && resp.ok) announce("Choice made. What they chose and what followed are shown below.");
  }

  // ---- review ----------------------------------------------------------------------------------------------------
  // One question at a time, in the order the schedule gives. Everything is written in words and nothing is timed.
  function renderReview() {
    if (currentMode() !== "review") return;
    var r = view.review;
    var box = clear($("review-question"));
    var ex = clear($("review-explainer"));
    if (!r) return;
    var c = r.counts;
    $("review-meta").textContent = "Day " + r.day + " · " + c.ready + " ready now · " + c.later + " coming back later · " + c.settled + " at the longest gap · " + c.total + " facts learned";
    (r.explainer || []).forEach(function (line) { ex.appendChild(el("li", null, line)); });
    var next = $("review-next-button");
    next.hidden = !r.feedback;
    if (r.feedback) {
      var f = r.feedback;
      box.appendChild(el("h3", null, f.prompt));
      box.appendChild(el("p", "review-context", f.context));
      box.appendChild(el("p", null, "You chose: " + f.choice_label));
      box.appendChild(el("p", "message-line", (f.right ? "✔ " : "↺ ") + f.message));
      if (f.settled) box.appendChild(el("p", "note", "This fact has reached the longest gap."));
      if (f.claim) box.appendChild(claimBlock(f.claim));
      $("review-message").textContent = "";
      return;
    }
    if (r.question) {
      var q = r.question;
      box.appendChild(el("p", "note", q.new ? "A new one to remember" : "Coming back to this one"));
      box.appendChild(el("h3", null, q.prompt));
      box.appendChild(el("p", "review-context", q.context));
      var group = el("div", "opt-row review-options");
      group.setAttribute("role", "group");
      group.setAttribute("aria-label", q.prompt);
      q.options.forEach(function (o, i) {
        var b = el("button", "opt-btn", (i + 1) + ". " + o.label);
        b.type = "button";
        b.setAttribute("data-key", q.key);
        b.setAttribute("data-opt", o.id);
        b.setAttribute("data-fk", "ropt-" + o.id);
        b.setAttribute("aria-pressed", "false");
        group.appendChild(b);
      });
      box.appendChild(group);
      $("review-message").textContent = "";
      return;
    }
    box.appendChild(el("p", null, r.idle || ""));
    $("review-message").textContent = "";
  }

  function answerReview(key, opt) {
    if (!view || !view.review || !view.review.question) return;
    var resp = act({ action: "review_answer", key: key, choice: opt });
    if (resp && resp.ok && view.review.feedback) {
      announce(view.review.feedback.message);
      var n = $("review-next-button");
      if (n && !n.hidden) n.focus();
    }
  }

  function switchMode(mode) {
    var info = ((view && view.modes) || []).filter(function (m) { return m.id === mode; })[0];
    if (!view) { startEngine(); return; }
    if (info && !info.available) { $("message-line").textContent = "This set does not have that mode yet."; announce("This set does not have that mode yet."); return; }
    selected = null; webPick = null;
    var resp = act({ action: "mode", mode: mode });
    if (resp && resp.ok) announce(MODE_LABELS[mode] + " mode.");
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
    if (e.kind === "relation") {
      var tl = el("ul", "thread-list");
      tl.appendChild(threadBlock(e.thread));
      d.appendChild(tl);
    } else if (e.kind === "record") {
      d.appendChild(el("h3", null, e.title));
      d.appendChild(claimBlock(e.claim));
      d.appendChild(el("p", "why", "Why: " + e.claim.explanation));
    } else if (e.kind === "account") {
      d.appendChild(el("h3", null, e.title));
      d.appendChild(passageReveal(e.passage, null));
      d.appendChild(el("p", "note", "The passage is a short summary written for this game; open the source to read the whole thing."));
      d.appendChild(el("h3", null, "The facts this account is about"));
      e.points.forEach(function (pt) { d.appendChild(el("p", "note", pt.label)); d.appendChild(claimBlock(pt.claim)); });
    } else if (e.kind === "decision") {
      d.appendChild(el("h3", null, e.title));
      d.appendChild(el("p", "note", e.decision.who + ", " + e.decision.when));
      d.appendChild(claimBlock(e.decision.situation));
      var dr = e.decision.result;
      d.appendChild(el("p", null, "You chose: " + dr.picked_text));
      d.appendChild(el("h3", null, dr.chose_label + ": " + dr.chosen_text));
      d.appendChild(claimBlock(dr.choice_claim));
      d.appendChild(el("h3", null, dr.after_label));
      d.appendChild(claimBlock(dr.after_claim));
      d.appendChild(el("p", "note", dr.note));
    } else if (e.kind === "person" || e.kind === "place") {
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
    box.appendChild(el("p", "note", i.set.status_label + " · version " + i.set.version + (i.set.drafted ? " · drafted " + i.set.drafted : "") + " · " + i.counts.events + " events (presidential moments plus things that happened elsewhere), " + i.counts.claims + " claims (" + i.counts.levels.documented + " documented, " + i.counts.levels.disputed + " disputed, " + i.counts.levels["traditional-but-doubtful"] + " traditional but doubtful), " + i.counts.relations + " cause links, " + i.counts.passages + " passages to weigh in " + i.counts.accounts + " accounts, " + i.counts.decisions + " decision points, " + i.counts.sources + " different sources."));
    box.appendChild(el("h3", null, "How sure are the sources?"));
    var ul = el("ul", "info-list");
    i.legend.forEach(function (l) { var li = el("li"); li.appendChild(el("strong", null, l.symbol + " " + l.label + ": ")); li.appendChild(document.createTextNode(l.meaning)); ul.appendChild(li); });
    box.appendChild(ul);
    box.appendChild(el("h3", null, "How strong is a cause link?"));
    var sl = el("ul", "info-list");
    i.strengths.forEach(function (l) { var li = el("li"); li.appendChild(el("strong", null, l.symbol + " " + l.label + ": ")); li.appendChild(document.createTextNode(l.meaning)); sl.appendChild(li); });
    box.appendChild(sl);
    box.appendChild(el("p", "note", "A cause link also carries the confidence labels above, so a link can be strong and still disputed. Causes are plural: a link is one cause among several."));
    box.appendChild(el("h3", null, "Sources for what you have found (" + i.found_claims.length + " moments, " + i.found_relations.length + " cause links, " + plural((i.found_accounts || []).length, "account") + ", " + plural((i.found_decisions || []).length, "decision") + ")"));
    box.appendChild(el("p", "note", i.coverage.note));
    var bar = el("div", "settings-row");
    var openAll = el("button", "small-btn", "Show every source list below");
    openAll.type = "button";
    openAll.addEventListener("click", function () {
      box.querySelectorAll("details.sources").forEach(function (d) { d.setAttribute("data-skip-view", "1"); d.open = true; });
      announce("Every source list is open.");
    });
    bar.appendChild(openAll);
    box.appendChild(bar);
    if (!i.found_claims.length && !i.found_relations.length && !(i.found_accounts || []).length && !(i.found_decisions || []).length) box.appendChild(el("p", "note", "Nothing found yet. Solve a puzzle and its claims and sources appear here."));
    i.found_claims.forEach(function (f) {
      var wrap = el("div", "reveal");
      wrap.appendChild(el("div", "when", f.date_label));
      wrap.appendChild(el("h3", null, f.title));
      f.claims.forEach(function (c) { wrap.appendChild(claimBlock(c)); });
      box.appendChild(wrap);
    });
    if (i.found_accounts && i.found_accounts.length) {
      box.appendChild(el("h3", null, "Accounts you have weighed"));
      box.appendChild(el("p", "note", "Primary sources were made at the time by someone who took part or watched; secondary sources were written afterwards from other sources. Each passage is a short summary written for this game."));
      i.found_accounts.forEach(function (a) {
        var wrap2 = el("div", "reveal");
        wrap2.appendChild(el("h3", null, a.title + " (" + a.judged + " of " + a.total + " sources judged)"));
        a.passages.forEach(function (ps) { wrap2.appendChild(passageReveal(ps, null)); });
        a.points.forEach(function (pt) { wrap2.appendChild(el("p", "note", pt.label)); wrap2.appendChild(claimBlock(pt.claim)); });
        box.appendChild(wrap2);
      });
    }
    if (i.found_decisions && i.found_decisions.length) {
      box.appendChild(el("h3", null, "Decision points you have made"));
      i.found_decisions.forEach(function (d) {
        var wrap3 = el("div", "reveal");
        wrap3.appendChild(el("h3", null, d.title));
        wrap3.appendChild(el("p", "note", d.who + ", " + d.when));
        wrap3.appendChild(claimBlock(d.situation));
        wrap3.appendChild(el("h3", null, d.result.chose_label + ": " + d.result.chosen_text));
        wrap3.appendChild(claimBlock(d.result.choice_claim));
        wrap3.appendChild(el("h3", null, d.result.after_label));
        wrap3.appendChild(claimBlock(d.result.after_claim));
        box.appendChild(wrap3);
      });
    }
    if (i.found_relations.length) {
      box.appendChild(el("h3", null, "Cause links you have found"));
      var rl = el("ul", "thread-list");
      i.found_relations.forEach(function (t) { rl.appendChild(threadBlock(t)); });
      box.appendChild(rl);
    }
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
      var kind = b.getAttribute("data-kind");
      if (b.getAttribute("aria-disabled") === "true") {
        var why = (kind ? "That chapter" : "That section") + " is locked. " + b.querySelectorAll(".sc-meta")[0].textContent + ".";
        var line = { web: "web-message", myth: "myth-message", account: "account-message", decision: "decision-message" }[kind] || "message-line";
        $(line).textContent = why;
        announce(why);
        return;
      }
      selected = null; webPick = null;
      if (kind === "web") act({ action: "web_start", chapter: b.getAttribute("data-chapter") });
      else if (kind === "myth") act({ action: "myth_start", chapter: b.getAttribute("data-chapter") });
      else if (kind === "account") act({ action: "account_start", account: b.getAttribute("data-chapter") });
      else if (kind === "decision") act({ action: "decision_start", decision: b.getAttribute("data-chapter") });
      else act({ action: "start", section: b.getAttribute("data-section") });
    });

    // mode tabs (a tablist: arrow keys, Home and End move between the three)
    var tabs = MODE_IDS;
    tabs.forEach(function (id) {
      $("mode-" + id + "-button").addEventListener("click", function () { switchMode(id); });
      $("mode-" + id + "-button").addEventListener("keydown", function (ev) {
        var i = tabs.indexOf(id), j = null;
        if (ev.key === "ArrowRight" || ev.key === "ArrowDown") j = (i + 1) % tabs.length;
        else if (ev.key === "ArrowLeft" || ev.key === "ArrowUp") j = (i + tabs.length - 1) % tabs.length;
        else if (ev.key === "Home") j = 0;
        else if (ev.key === "End") j = tabs.length - 1;
        if (j === null) return;
        ev.preventDefault();
        $("mode-" + tabs[j] + "-button").focus();
        switchMode(tabs[j]);
        $("mode-" + tabs[j] + "-button").focus();
      });
    });

    // cause web
    $("web-cards").addEventListener("click", function (ev) {
      var b = ev.target.closest(".web-card");
      if (b) onWebCard(b.getAttribute("data-wcard"));
    });
    $("web-cancel-button").addEventListener("click", function () { webPick = null; renderWeb(); announce("Put the card down."); });
    $("web-show-button").addEventListener("click", function () {
      var go = function () { webPick = null; act({ action: "web_show" }); };
      if (window.ConfirmDialog) window.ConfirmDialog.ask({ id: "chronicle-web-show", message: "Show the links? Nothing from this puzzle will be added to your archive.", confirmLabel: "Show the links", allowSkip: true, onConfirm: go });
      else go();
    });
    $("web-next-button").addEventListener("click", function () { webPick = null; act({ action: "web_next" }); $("web-panel").scrollIntoView({ block: "nearest" }); });

    // myth or record
    $("myth-cards").addEventListener("click", function (ev) {
      var b = ev.target.closest(".bin-btn");
      if (!b || b.getAttribute("aria-disabled") === "true") return;
      sortClaim(b.getAttribute("data-claim"), b.getAttribute("data-bin"));
    });
    $("myth-check-button").addEventListener("click", function () {
      if (!view || !view.myth) return;
      if (!view.myth.all_sorted) { $("myth-message").textContent = "Sort every statement before checking."; announce("Sort every statement before checking."); return; }
      var resp = act({ action: "myth_check" });
      if (resp && resp.ok) announce(view.myth.message);
      if (view.myth && view.myth.result) $("myth-result").scrollIntoView({ block: "nearest" });
    });
    $("myth-show-button").addEventListener("click", function () {
      var go = function () { act({ action: "myth_show" }); };
      if (window.ConfirmDialog) window.ConfirmDialog.ask({ id: "chronicle-myth-show", message: "Show the answer? Nothing from this puzzle will be added to your archive.", confirmLabel: "Show the answer", allowSkip: true, onConfirm: go });
      else go();
    });
    $("myth-next-button").addEventListener("click", function () { act({ action: "myth_next" }); $("myth-panel").scrollIntoView({ block: "nearest" }); });
    // whose account?
    $("account-questions").addEventListener("click", function (ev) {
      var b = ev.target.closest(".opt-btn");
      if (!b || b.getAttribute("aria-disabled") === "true") return;
      answerAccount(b.getAttribute("data-q"), b.getAttribute("data-opt"));
    });
    $("account-check-button").addEventListener("click", function () {
      if (!view || !view.account) return;
      if (!view.account.all_answered) { $("account-message").textContent = "Answer every question before checking."; announce("Answer every question before checking."); return; }
      var resp = act({ action: "account_check" });
      if (resp && resp.ok) announce(view.account.message);
      if (view.account && view.account.result) $("account-result").scrollIntoView({ block: "nearest" });
    });
    $("account-show-button").addEventListener("click", function () {
      var go = function () { act({ action: "account_show" }); };
      if (window.ConfirmDialog) window.ConfirmDialog.ask({ id: "chronicle-account-show", message: "Show the answers? Nothing from this puzzle will be added to your archive.", confirmLabel: "Show the answers", allowSkip: true, onConfirm: go });
      else go();
    });
    $("account-next-button").addEventListener("click", function () { act({ action: "account_next" }); $("account-panel").scrollIntoView({ block: "nearest" }); });

    // decision points
    $("decision-options").addEventListener("click", function (ev) {
      var b = ev.target.closest(".opt-btn");
      if (!b || b.getAttribute("aria-disabled") === "true") return;
      pickDecision(b.getAttribute("data-opt"));
    });

    // review
    $("review-question").addEventListener("click", function (ev) {
      var b = ev.target.closest(".opt-btn");
      if (b) answerReview(b.getAttribute("data-key"), b.getAttribute("data-opt"));
    });
    $("review-next-button").addEventListener("click", function () { act({ action: "review_next" }); var first = document.querySelector("#review-question .opt-btn"); if (first) first.focus(); });
    $("review-day-button").addEventListener("click", function () {
      var resp = act({ action: "review_day" });
      if (resp && resp.ok) announce("A day passed. It is now day " + view.review.day + ".");
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
    var mode = currentMode();
    if (mode === "web") {
      if (ev.key === "Escape" && webPick) { webPick = null; renderWeb(); announce("Put the card down."); return; }
      if (/^[1-9]$/.test(ev.key) && view.web && !view.web.locked && view.web.status === "playing") {
        var wc = view.web.cards[parseInt(ev.key, 10) - 1];
        if (wc) { ev.preventDefault(); onWebCard(wc.id); }
        return;
      }
    } else if (mode === "account") {
      var aq = ev.target.closest && ev.target.closest(".acct-q");
      if (/^[1-5]$/.test(ev.key) && aq && view.account && !view.account.locked) {
        ev.preventDefault();
        var qrow = view.account.questions.filter(function (x) { return x.id === aq.getAttribute("data-q"); })[0];
        if (qrow && !qrow.locked && qrow.options[parseInt(ev.key, 10) - 1]) answerAccount(qrow.id, qrow.options[parseInt(ev.key, 10) - 1].id);
        return;
      }
    } else if (mode === "decision") {
      if (/^[1-4]$/.test(ev.key) && view.decision && !view.decision.locked && !view.decision.decided) {
        var dopt = view.decision.options[parseInt(ev.key, 10) - 1];
        if (dopt) { ev.preventDefault(); pickDecision(dopt.id); }
        return;
      }
    } else if (mode === "review") {
      if (/^[1-4]$/.test(ev.key) && view.review && view.review.question) {
        var ropt = view.review.question.options[parseInt(ev.key, 10) - 1];
        if (ropt) { ev.preventDefault(); answerReview(view.review.question.key, ropt.id); }
        return;
      }
    } else if (mode === "myth") {
      var card = ev.target.closest && ev.target.closest(".myth-card");
      if (/^[1-3]$/.test(ev.key) && card && view.myth && !view.myth.locked) {
        ev.preventDefault();
        var claimId = card.getAttribute("data-claim");
        var bins = view.myth.bins;
        var row = view.myth.claims.filter(function (c) { return c.id === claimId; })[0];
        if (row && !row.locked) sortClaim(claimId, bins[parseInt(ev.key, 10) - 1].id);
        return;
      }
    }
    if (!(ev.target.closest && ev.target.closest(".myth-card, .web-card")) && /^[twmadr]$/i.test(ev.key)) {
      ev.preventDefault();
      switchMode(MODE_KEYS[ev.key.toLowerCase()]);
      return;
    }
    if (ev.key === "Escape" && selected) { selected = null; render(); announce("Put the card down."); return; }
    if (mode === "timeline" && /^[1-8]$/.test(ev.key) && selected) {
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
    selected = null; webPick = null;
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
