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
 *
 * The page script is cut into five classic scripts that share ONE object, window.ChronicleApp (see the File map in
 * CLAUDE.md). They load in this order and each is wrapped in its own function, so no new global names exist:
 *   app-1-core.js    constants, helpers, catalogs, toasts, engine boot, act()      (creates window.ChronicleApp)
 *   app-2-render.js  render(), mode tabs, chapter cards, the timeline board, claim and source blocks, nuance strip
 *   app-3-modes.js   cause web, myth or record, whose account, decision points and review
 *   app-4-panels.js  mode switch, card placing, report a problem, archive, Info page
 *   app.js           wiring (clicks, keys), save-loaded hook, copy result, init (loads last)
 * State that more than one part reads or writes lives on the object: A.view, A.selected, A.webPick, A.engineReady,
 * A.currentReport. Functions another part calls are exported as A.name at the end of their own part.
 */
(function () {
  "use strict";

  var A = window.ChronicleApp = {};
  var engineStarting = false;
  A.engineReady = false;
  A.view = null;
  A.selected = null;               // { id, slot } : the card picked up (slot is null when it is in the tray)
  A.webPick = null;                // the cause-web card picked up as the cause (the next card is the effect)
  A.currentReport = null;

  var GAME = "chronicle";
  var PYODIDE_URL = "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js";
  var ENGINE_MODULES = ["setdata.py", "core.py", "views.py", "actions.py", "puzzle.py", "web.py", "myth.py", "account.py", "decision.py", "review.py", "achievements.py", "report.py"];
  var SET_FILES = ["meta", "sources", "entities", "claims", "relations", "sections", "readings"];
  var OPTIONAL_SET_FILES = ["chapters", "accounts", "decisions"];   // chapters, accounts and decision points: a set may have none of them
  var LS_STATE = "chronicle:state";
  var LS_VIEW = "chronicle:lastview";

  var $ = function (id) { return document.getElementById(id); };
  var api = null, getStateFn = null;
  var catalog = { ach: [], log: [] };
  var toastQueue = [], toastBusy = false;

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
    var earned = (A.view && A.view.achievements_earned) || [];
    var list = clear($("achievements-list"));
    catalog.ach.forEach(function (a) {
      var got = earned.indexOf(a.id) >= 0;
      var li = el("li", got ? "earned" : "");
      li.setAttribute("data-achievement-id", a.id);
      li.appendChild(el("span", "tick", got ? "✔ Earned" : "Not yet"));
      var name = el("strong", null, " ");
      var labelSpan = el("span", null, a.label);
      labelSpan.setAttribute("data-achievement-label", "");
      name.appendChild(labelSpan);
      name.appendChild(document.createTextNode(": "));
      li.appendChild(name);
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
    if (engineStarting || A.engineReady) return;
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
      A.engineReady = true;
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
    if (!A.engineReady) {
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
      A.view = resp.view;
      lsSet(LS_VIEW, JSON.stringify(slimView(A.view)));
    }
    if (resp.dirty) persistState();
    (resp.new || []).forEach(function (id) {
      var a = catalog.ach.filter(function (x) { return x.id === id; })[0];
      showToast("Achievement earned: " + (a ? a.label : id));
    });
    if (opts.render !== false) A.render();
    else A.renderMeterAndPicker();
    if ((resp.new || []).length) renderAchievements();
    return resp;
  }

  function applyResponse(resp) {
    if (resp.view) { A.view = resp.view; lsSet(LS_VIEW, JSON.stringify(slimView(A.view))); }
    A.render();
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

  // what the other parts use (see the File map in CLAUDE.md)
  A.$ = $; A.LS_STATE = LS_STATE; A.LS_VIEW = LS_VIEW; A.act = act; A.announce = announce;
  A.applyResponse = applyResponse; A.catalog = catalog; A.clear = clear; A.el = el; A.jsonParse = jsonParse;
  A.lsGet = lsGet; A.lsRemove = lsRemove; A.lsSet = lsSet; A.persistState = persistState; A.plural = plural;
  A.renderAchievements = renderAchievements; A.send = send; A.setStatus = setStatus; A.showToast = showToast;
  A.startEngine = startEngine;
})();
