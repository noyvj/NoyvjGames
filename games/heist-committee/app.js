/* Heist Committee view: glue only. The engine (game.py and its modules) holds every rule; this file draws what
   handle() returns and forwards what the player does. No game logic lives here.
   Shared pieces live on window.HC so plan.js (the timeline) and play.js (playback and payout) can use them. */
(function () {
  "use strict";
  var ENGINE_MODULES = ["content.py", "engine.py", "plancheck.py", "planops.py"];
  var CONTENT_FILES = ["tags", "actions", "traits", "crew", "gear", "complications", "targets", "lines", "writeups"];
  var STORE_KEY = "heist-committee:state";
  var PHASES = ["board", "scout", "recruit", "plan", "playback", "payout"];

  var HC = window.HC = { view: null, engine: null, renderers: {}, onRender: [] };
  var $ = HC.$ = function (id) { return document.getElementById(id); };

  function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* convenience only */ } }
  HC.lsGet = lsGet;
  HC.lsSet = lsSet;

  // ---- tiny DOM builder ---------------------------------------------------------------------
  HC.el = function (tag, attrs, children) {
    var node = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      var v = attrs[k];
      if (v === null || v === undefined || v === false) return;
      if (k === "class") node.className = v;
      else if (k === "text") node.textContent = v;
      else if (k.indexOf("on") === 0 && typeof v === "function") node.addEventListener(k.slice(2), v);
      else node.setAttribute(k, v === true ? "" : v);
    });
    (children || []).forEach(function (c) {
      if (c === null || c === undefined || c === false) return;
      node.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
    });
    return node;
  };
  var el = HC.el;
  HC.setText = function (node, text) { if (node.textContent !== text) node.textContent = text; };
  HC.announce = function (text) {
    var live = $("announce");
    live.textContent = "";
    setTimeout(function () { live.textContent = text; }, 40);
  };
  var toastTimer = null;
  HC.toast = function (text) {
    var t = $("toast");
    t.textContent = text || "";
    clearTimeout(toastTimer);
    if (text) toastTimer = setTimeout(function () { t.textContent = ""; }, 6000);
  };

  // ---- glyphs: a role is a shape AND a letter AND a word, never colour ---------------------------
  var NS = "http://www.w3.org/2000/svg";
  var SHAPES = {
    circle: function () { var s = document.createElementNS(NS, "circle"); s.setAttribute("cx", 20); s.setAttribute("cy", 20); s.setAttribute("r", 17); return s; },
    square: function () { var s = document.createElementNS(NS, "rect"); ["x", "y"].forEach(function (k) { s.setAttribute(k, 4); }); s.setAttribute("width", 32); s.setAttribute("height", 32); s.setAttribute("rx", 4); return s; },
    triangle: function () { var s = document.createElementNS(NS, "polygon"); s.setAttribute("points", "20,3 37,36 3,36"); return s; },
    diamond: function () { var s = document.createElementNS(NS, "polygon"); s.setAttribute("points", "20,2 38,20 20,38 2,20"); return s; },
    hexagon: function () { var s = document.createElementNS(NS, "polygon"); s.setAttribute("points", "20,2 36,11 36,29 20,38 4,29 4,11"); return s; }
  };
  HC.glyph = function (card) {
    var wrap = el("span", { "class": "glyph", "aria-hidden": "true" });
    var svg = document.createElementNS(NS, "svg");
    svg.setAttribute("viewBox", "0 0 40 40");
    var shape = (SHAPES[card.shape] || SHAPES.circle)();
    shape.setAttribute("class", "shape");
    svg.appendChild(shape);
    var text = document.createElementNS(NS, "text");
    text.setAttribute("x", 20);
    text.setAttribute("y", card.shape === "triangle" ? 26 : 21);
    text.textContent = card.letter;
    svg.appendChild(text);
    wrap.appendChild(svg);
    return wrap;
  };
  HC.pips = function (n) {
    var wrap = el("span", { "class": "pips", "aria-hidden": "true" });
    for (var i = 0; i < 3; i++) wrap.appendChild(el("span", { "class": "pip" + (i < n ? " on" : "") }));
    return wrap;
  };
  HC.skillLine = function (s) {
    return el("span", { "class": "skill-line" }, [s.icon + " " + s.label + " " + s.pips, HC.pips(s.pips)]);
  };
  HC.traitChip = function (t, label) {
    return el("span", { "class": "chip", title: t.text }, [t.icon + " " + (label ? label + ": " : "") + t.name]);
  };
  HC.kindChip = function (k) { return el("span", { "class": "kind-chip" }, [k.icon + " " + k.label]); };
  HC.ODDS_GLYPH = { solid: "●", risky: "◐", "long": "○", none: "✕" };
  HC.oddsChip = function (odds) {
    return el("span", { "class": "odds odds-" + odds.word }, [HC.ODDS_GLYPH[odds.word] + " " + odds.label]);
  };

  // ---- talking to the engine -------------------------------------------------------------------
  HC.send = function (request) {
    if (!HC.engine) return null;
    var reply;
    try {
      reply = JSON.parse(HC.engine.handle(JSON.stringify(request)));
    } catch (e) {
      HC.toast("Something went wrong: " + e);
      return null;
    }
    if (reply.error && !reply.view) { HC.toast(reply.error); return null; }
    if (reply.error) HC.toast(reply.error);
    HC.view = reply.view;
    if (reply.view && reply.view.note) HC.toast(reply.view.note);
    HC.persist();
    HC.render();
    return reply;
  };
  HC.persist = function () {
    if (!HC.engine) return;
    try { lsSet(STORE_KEY, HC.engine.getStateJson()); } catch (e) { /* the save widget is the real save */ }
  };

  // ---- render ----------------------------------------------------------------------------------
  var lastPhase = null;
  HC.render = function () {
    var view = HC.view;
    if (!view) return;
    HC.setText($("hud-cash"), String(view.cash));
    var hudJob = $("hud-job");
    hudJob.textContent = "";
    if (view.target) {
      hudJob.appendChild(el("span", { "class": "hud-label" }, ["Job "]));
      hudJob.appendChild(el("b", {}, [view.target.name]));
    }
    PHASES.forEach(function (p) { $("phase-" + p).hidden = p !== view.phase; });
    var changed = lastPhase !== null && lastPhase !== view.phase;
    var render = HC.renderers[view.phase];
    if (render) render(view);
    HC.onRender.forEach(function (fn) { fn(view); });
    if (changed) {
      var heading = $("phase-" + view.phase).querySelector("h2");
      HC.announce(heading ? heading.textContent : view.phase);
      if (window.scrollY > 120) window.scrollTo(0, 0);
    }
    lastPhase = view.phase;
  };

  // The shared signature trick: rebuild a container only when its contents change, so focus survives redraws.
  HC.fillOnce = function (container, signature, build) {
    if (container.dataset.signature === signature) return false;
    container.textContent = "";
    build(container);
    container.dataset.signature = signature;
    return true;
  };
  HC.ask = function (id, message, confirmLabel, onConfirm) {
    if (window.ConfirmDialog) {
      window.ConfirmDialog.ask({ id: id, message: message, confirmLabel: confirmLabel, allowSkip: false, onConfirm: onConfirm });
    } else if (window.confirm(message)) {
      onConfirm();
    }
  };

  // ---- the board -------------------------------------------------------------------------------
  HC.renderers.board = function (view) {
    var root = $("board-cards");
    HC.fillOnce(root, JSON.stringify(view.board), function (box) {
      view.board.forEach(function (t) {
        box.appendChild(el("article", { "class": "card", "data-testid": "heist-target-" + t.id }, [
          el("h3", { text: t.name }),
          el("span", { "class": "tier", text: "Tier " + t.tier + " · " + t.beats + " beats" }),
          el("p", { text: t.blurb }),
          el("p", { "class": "note", text: "The prize is worth about " + t.prize + ". A bad night still pays " + t.consolation + "." }),
          el("div", { "class": "actions" }, [
            el("button", { type: "button", "class": "primary", "data-testid": "heist-take-" + t.id, text: "Take the job",
              onclick: function () { HC.send({ action: "take_job", target: t.id }); } })])]));
      });
    });
  };

  // ---- the case file (scouting) -----------------------------------------------------------------
  function scoutPanel(view, withButtons, withIntro) {
    var s = view.scout;
    var box = el("div", {});
    if (withIntro) box.appendChild(el("p", { "class": "note", text: view.target.intro }));
    var details = el("ul", {});
    s.details.forEach(function (d) { details.appendChild(el("li", { text: d })); });
    box.appendChild(el("h3", { text: "What you know about the building" }));
    box.appendChild(details);
    box.appendChild(el("h3", { text: "What might go wrong" }));
    var list = el("ul", { "class": "comp-list" });
    s.complications.forEach(function (c) {
      var kinds = c.kinds.map(HC.kindChip);
      var beats = c.beats[0] === c.beats[1] ? "beat " + c.beats[0] : "beats " + c.beats[0] + " to " + c.beats[1];
      list.appendChild(el("li", {}, [el("b", { text: c.name }), " ", el("span", { "class": "note", text: "(" + beats + (c.met_before ? ", you have met this one" : "") + ") " })].concat(kinds)));
    });
    box.appendChild(list);
    if (s.unknown_count > 0) {
      box.appendChild(el("p", { "class": "note", text: s.unknown_count === 1 ? "There is at least one more thing you have not heard about." : "There are at least " + s.unknown_count + " more things you have not heard about." }));
    }
    if (withButtons && s.next) {
      box.appendChild(el("button", { type: "button", "data-testid": "heist-scout-more",
        text: "Scout the place: +" + s.next.reveal + " more, costs " + s.next.cost,
        onclick: function () { HC.send({ action: "scout", level: s.next.level }); } }));
    }
    return box;
  }
  HC.scoutPanel = scoutPanel;

  HC.renderers.scout = function (view) {
    var root = $("scout-body");
    HC.fillOnce(root, JSON.stringify([view.scout, view.cash, view.target.id]), function (box) {
      box.appendChild(el("div", { "class": "panel" }, [el("h3", { text: view.target.name }),
        el("p", { text: view.target.blurb }), scoutPanel(view, true, true)]));
      box.appendChild(el("div", { "class": "phase-actions" }, [
        el("button", { type: "button", "class": "primary", "data-testid": "heist-to-recruit", text: "Choose the crew",
          onclick: function () { HC.send({ action: "to_recruit" }); } }),
        el("button", { type: "button", text: "Back to the board", onclick: function () { HC.send({ action: "back_to_board" }); } })]));
    });
  };

  // ---- recruiting -------------------------------------------------------------------------------
  function crewCard(c, view) {
    var hired = view.crew_ids.indexOf(c.id) !== -1;
    var lane = view.crew_ids.indexOf(c.id) + 1;
    var skills = el("div", {}, c.skills.map(HC.skillLine));
    var traitRow = el("div", { "class": "row" }, [HC.traitChip(c.trait, "Trait")]);
    traitRow.appendChild(c.quirk ? HC.traitChip(c.quirk, "Quirk") :
      el("span", { "class": "chip quirk-hidden", title: "Show up for work and find out, or pay for a background check." }, ["? Quirk: unknown"]));
    var rel = [];
    if (c.rivals.length) rel.push("Does not get along with " + c.rivals.join(", ") + ".");
    if (c.mentors.length) rel.push("Mentors " + c.mentors.join(", ") + ".");
    var card = el("article", { "class": "card" + (hired ? " hired" : ""), "data-testid": "heist-crew-" + c.id }, [
      el("div", { "class": "row" }, [HC.glyph(c), el("div", {}, [el("h3", { text: c.name }), el("span", { "class": "tier", text: c.role_icon + " " + c.role_label })]),
        el("span", { "class": "fee", text: "Fee " + c.fee })]),
      skills, traitRow,
      rel.length ? el("p", { "class": "note", text: rel.join(" ") }) : null,
      el("p", { "class": "voice", text: "“" + c.voice + "”" }),
      el("div", { "class": "actions" }, [
        el("button", { type: "button", "class": hired ? "primary" : "", "aria-pressed": hired ? "true" : "false", "data-testid": "heist-hire-" + c.id,
          text: hired ? "Hired (lane " + lane + ")" : "Hire",
          onclick: function () { HC.send({ action: "hire", crew: c.id }); } }),
        c.quirk_known ? null : el("button", { type: "button", "data-testid": "heist-check-" + c.id, text: "Background check (" + view.background_fee + ")",
          onclick: function () { HC.send({ action: "background", crew: c.id }); } })])]);
    return card;
  }

  HC.renderers.recruit = function (view) {
    HC.fillOnce($("recruit-cards"), JSON.stringify([view.offer, view.crew_ids]), function (box) {
      view.offer.forEach(function (c) { box.appendChild(crewCard(c, view)); });
    });
    var total = view.fees + view.gear_cost;
    var ready = view.crew_ids.length === 5;
    HC.fillOnce($("recruit-summary"), JSON.stringify([view.crew_ids, view.gear, view.cash, view.fees]), function (box) {
      var names = view.crew_ids.map(function (id, i) { return (i + 1) + ". " + view.offer.filter(function (c) { return c.id === id; })[0].short; });
      box.appendChild(el("h3", { text: "Your crew: " + view.crew_ids.length + " of 5" }));
      box.appendChild(el("p", { text: names.length ? "Lane order: " + names.join(", ") : "Nobody hired yet." }));
      box.appendChild(el("h3", { text: "Gear (up to 2, used once each heist)" }));
      var gear = el("div", { "class": "row", style: "display:flex;gap:.5rem;flex-wrap:wrap" });
      view.gear.forEach(function (g) {
        gear.appendChild(el("button", { type: "button", "aria-pressed": g.equipped ? "true" : "false", title: g.text, "data-testid": "heist-gear-" + g.id,
          text: g.icon + " " + g.name + " (" + g.cost + ")" + (g.equipped ? " - packed" : ""),
          onclick: function () { HC.send({ action: "gear", gear: g.id }); } }));
      });
      box.appendChild(gear);
      box.appendChild(el("ul", { "class": "list-plain" }, view.gear.filter(function (g) { return g.equipped; }).map(function (g) { return el("li", { text: g.name + ": " + g.text }); })));
      box.appendChild(el("p", { text: "Crew fees " + view.fees + " + gear " + view.gear_cost + " = " + total + ". The committee has " + view.cash + "." }));
      box.appendChild(el("div", { "class": "phase-actions" }, [
        el("button", { type: "button", "class": "primary", "data-testid": "heist-confirm-crew", "aria-disabled": ready && total <= view.cash ? null : "true",
          text: "Pay the crew and start planning",
          onclick: function () { if (ready) HC.send({ action: "confirm_crew" }); else HC.toast("Choose exactly five crew."); } }),
        el("button", { type: "button", text: "Back to the case file", onclick: function () { HC.send({ action: "back_to_board" }); } })]));
    });
  };

  // ---- boot --------------------------------------------------------------------------------------
  function setBusy(busy) {
    document.querySelectorAll("#game button[data-testid]").forEach(function (b) { b.disabled = busy; });
  }
  HC.setBusy = setBusy;

  function wireGlobal() {
    function panelToggle(buttonId, panelId) {
      var btn = $(buttonId), panel = $(panelId);
      if (!btn || !panel) return;
      btn.addEventListener("click", function () {
        panel.hidden = !panel.hidden;
        btn.setAttribute("aria-expanded", String(!panel.hidden));
      });
    }
    panelToggle("achievements-toggle-button", "achievements-panel");
    panelToggle("changelog-toggle-button", "changelog-panel");
    panelToggle("info-page-toggle-button", "info-page-panel");
    // The save widget loads a save directly into the engine; this redraws the page afterwards.
    window.heistRefresh = function () { if (HC.engine) HC.send({ action: "open" }); };
  }

  async function boot() {
    var pyodide = await window.loadPyodide();
    for (var i = 0; i < ENGINE_MODULES.length; i++) {
      var source = await (await fetch(ENGINE_MODULES[i])).text();
      pyodide.FS.writeFile(ENGINE_MODULES[i], source, { encoding: "utf8" });
    }
    for (var j = 0; j < CONTENT_FILES.length; j++) {
      var name = CONTENT_FILES[j] + ".json";
      var res = await fetch("content/" + name);
      if (res.ok) pyodide.FS.writeFile(name, await res.text(), { encoding: "utf8" });
    }
    await pyodide.runPythonAsync(await (await fetch("game.py")).text());
    window.pyodide = pyodide;   // the shared save widget looks for it
    HC.engine = { handle: pyodide.globals.get("handle"), getStateJson: pyodide.globals.get("get_state_json"), loadState: pyodide.globals.get("load_state") };
    var saved = lsGet(STORE_KEY);
    if (saved) {
      try { HC.engine.loadState(pyodide.toPy(JSON.parse(saved))); } catch (e) { /* a bad save never blocks play */ }
    }
    $("engine-status").textContent = "";
    setBusy(false);
    HC.send({ action: "open" });
    if (window.HC.afterBoot) await window.HC.afterBoot();
  }

  wireGlobal();
  setBusy(true);
  boot().catch(function (err) {
    $("engine-status").textContent = "The van would not start (" + err + "). Reload to try again.";
  });
})();
