/* Heist Committee view: glue only. The engine (game.py and its modules) holds every rule; this file draws what
   handle() returns and forwards what the player does. No game logic lives here.
   Shared pieces live on window.HC so plan.js (the timeline) and play.js (playback and payout) can use them. */
(function () {
  "use strict";
  var ENGINE_MODULES = ["content.py", "engine.py", "plancheck.py", "planops.py", "writeup.py", "info.py", "achievements.py", "story.py", "bots.py", "daily.py"];
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
  // The engine never reads the clock: every request carries the UTC date the view sees.
  HC.utcToday = function () { return new Date().toISOString().slice(0, 10); };
  HC.send = function (request) {
    if (!HC.engine) return null;
    request.today = HC.utcToday();
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
    HC.setText($("hud-cash"), view.daily ? "free" : String(view.cash));
    HC.setText($("hud-rep"), view.daily ? "-" : String(view.reputation));
    var hudJob = $("hud-job");
    hudJob.textContent = "";
    if (view.target) {
      hudJob.appendChild(el("span", { "class": "hud-label" }, [view.daily ? "Daily job " + view.daily.number + ": " : "Job "]));
      hudJob.appendChild(el("b", {}, [view.target.name]));
    }
    var status = { board: "Contract board", scout: "Case file", recruit: "Hiring", plan: "Planning",
      payout: "Payout" }[view.phase];
    if (view.phase === "playback") status = "Beat " + Math.max(1, view.playback.cursor) + " of " + view.playback.n + ", heat " + view.playback.heat;
    HC.setText($("hud-status"), status);
    PHASES.forEach(function (p) { $("phase-" + p).hidden = p !== view.phase; });
    var changed = lastPhase !== null && lastPhase !== view.phase;
    var render = HC.renderers[view.phase];
    if (render) render(view);
    HC.onRender.forEach(function (fn) { fn(view); });
    if (changed) {
      var heading = $("phase-" + view.phase).querySelector("h2");
      HC.announce(heading ? heading.textContent : view.phase);
      if (window.scrollY > 120) window.scrollTo(0, 0);
      $("main-stage").scrollTop = 0;       // the Desktop layout scrolls the stage itself
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

  // ---- achievements and the committee's minutes ------------------------------------------------
  var knownEarned = null;
  function renderAchievements(view) {
    var list = $("achievements-list");
    var earnedNow = [];
    var sig = JSON.stringify(view.achievements);
    HC.fillOnce(list, sig, function (ul) {
      view.achievements.forEach(function (a) {
        ul.appendChild(el("li", { "class": a.earned ? "earned" : "", "data-achievement-id": a.id }, [
          el("span", { "class": "tick", text: a.earned ? "Earned" : "Not yet" }),
          el("strong", { "data-achievement-label": "", text: " " + a.label + " " }),
          el("span", { text: a.description })]));
      });
    });
    view.achievements.forEach(function (a) { if (a.earned) earnedNow.push(a.id); });
    $("achievements-toggle-button").textContent = "Achievements (" + earnedNow.length + "/" + view.achievements.length + ")";
    if (knownEarned !== null) {
      earnedNow.filter(function (id) { return knownEarned.indexOf(id) === -1; }).forEach(function (id) {
        var a = view.achievements.filter(function (x) { return x.id === id; })[0];
        HC.toast("Achievement unlocked: " + a.label + ".");
        HC.announce("Achievement unlocked: " + a.label + ".");
      });
    }
    knownEarned = earnedNow;
  }
  function renderMinutes(view) {
    var m = view.minutes;
    HC.fillOnce($("minutes-entries"), JSON.stringify(m), function (box) {
      m.entries.slice().reverse().forEach(function (e) {
        box.appendChild(el("article", { "class": "changelog-entry story-line" }, [el("div", { "class": "changelog-date", text: e.title }), el("p", { text: e.text })]));
      });
      box.appendChild(el("p", { "class": "note", text: m.next_at === null ? "That is every meeting on the books, for now." : "The next meeting opens once you have finished " + m.next_at + (m.next_at === 1 ? " job" : " jobs") + " (so far: " + m.jobs_done + ")." }));
    });
  }
  HC.onRender.push(function (view) { renderAchievements(view); renderMinutes(view); });

  // ---- the board -------------------------------------------------------------------------------
  HC.renderers.board = function (view) {
    HC.renderers.board_extra(view);
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

  HC.renderers.board_extra = function (view) {
    HC.fillOnce($("board-standing"), JSON.stringify([view.reputation, view.next_unlock, view.relationships, view.jobs_done]), function (box) {
      box.appendChild(el("h3", { text: "The committee's standing" }));
      box.appendChild(el("p", { text: "Reputation " + view.reputation + ", " + view.jobs_done + (view.jobs_done === 1 ? " job" : " jobs") + " done." }));
      if (view.next_unlock) {
        box.appendChild(el("p", { "class": "note", text: "At reputation " + view.next_unlock.at + " this opens: " + view.next_unlock.names.join(", ") + "." }));
      } else {
        box.appendChild(el("p", { "class": "note", text: "Everything on the books is open." }));
      }
      if (view.relationships.length) {
        var ul = el("ul", { "class": "list-plain" });
        view.relationships.forEach(function (r) {
          ul.appendChild(el("li", { text: (r.kind === "friends" ? "♥ " + r.a + " and " + r.b + " are friends (a small bonus when they share a beat)." : "⚡ " + r.a + " and " + r.b + " are feuding (a penalty when they share a beat).") }));
        });
        box.appendChild(ul);
      }
      box.appendChild(el("button", { type: "button", "data-testid": "heist-new-career", text: "Start a new career",
        onclick: function () { HC.ask("heist-new-career", "Start a brand new career? Cash, reputation and friendships go back to the start. Your Daily Job results stay.", "Start over", function () { HC.send({ action: "new_career" }); }); } }));
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
    HC.fillOnce(root, JSON.stringify([view.scout, view.cash, view.target.id, view.daily && view.daily.date]), function (box) {
      if (view.daily) {
        box.appendChild(el("p", { "class": "note daily-note", "data-testid": "heist-daily-banner",
          text: "Daily Job " + view.daily.number + " (" + view.daily.date + "). Scouting, the crew and the van are free today, and every crew member's quirk is on the file." }));
      }
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
    c.relations.forEach(function (r) { rel.push((r.kind === "friends" ? "♥ Friends with " : "⚡ Feuding with ") + r.short + "."); });
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
        (c.quirk_known || view.daily) ? null : el("button", { type: "button", "data-testid": "heist-check-" + c.id, text: "Background check (" + view.background_fee + ")",
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
      box.appendChild(el("h3", { text: view.daily ? "Today's van (take up to 2, used once each heist)" : "Gear (up to 2, used once each heist)" }));
      var gear = el("div", { "class": "row", style: "display:flex;gap:.5rem;flex-wrap:wrap" });
      view.gear.forEach(function (g) {
        gear.appendChild(el("button", { type: "button", "aria-pressed": g.equipped ? "true" : "false", title: g.text, "data-testid": "heist-gear-" + g.id,
          "aria-disabled": g.locked ? "true" : null,
          text: g.icon + " " + g.name + (g.locked ? " (opens at reputation " + g.unlock + ")" : (view.daily ? "" : " (" + g.cost + ")") + (g.equipped ? " - packed" : "")),
          onclick: function () { if (!g.locked) HC.send({ action: "gear", gear: g.id }); } }));
      });
      box.appendChild(gear);
      box.appendChild(el("ul", { "class": "list-plain" }, view.gear.filter(function (g) { return g.equipped; }).map(function (g) { return el("li", { text: g.name + ": " + g.text }); })));
      box.appendChild(el("p", { text: view.daily ? "Today's crew and van are on the house." :
        "Crew fees " + view.fees + " + gear " + view.gear_cost + " = " + total + ". The committee has " + view.cash + "." }));
      box.appendChild(el("div", { "class": "phase-actions" }, [
        el("button", { type: "button", "class": "primary", "data-testid": "heist-confirm-crew", "aria-disabled": ready && total <= view.cash ? null : "true",
          text: view.daily ? "Start planning" : "Pay the crew and start planning",
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
    panelToggle("minutes-toggle-button", "minutes-panel");
    panelToggle("achievements-toggle-button", "achievements-panel");
    panelToggle("changelog-toggle-button", "changelog-panel");
    panelToggle("info-page-toggle-button", "info-page-panel");
    // The save widget loads a save directly into the engine; this redraws the page afterwards.
    window.heistRefresh = function () { knownEarned = null; if (HC.engine) HC.send({ action: "open" }); };
  }

  // ---- info panel, changelog, tutorial ----------------------------------------------------------
  function renderInfo(info) {
    $("info-page-framing").textContent = info.framing;
    var list = $("info-page-sources");
    list.textContent = "";
    info.sections.forEach(function (s) {
      list.appendChild(el("li", { "class": "info-page-source" }, [el("h3", { text: s.heading }), el("p", { text: s.body })]));
    });
  }
  function renderChangelog(entries) {
    var holder = $("changelog-entries");
    holder.textContent = "";
    entries.forEach(function (entry) {
      holder.appendChild(el("article", { "class": "changelog-entry" }, [el("div", { "class": "changelog-date", text: entry.date }), el("p", { text: entry.entry })]));
    });
    $("changelog-toggle-button").textContent = "What's New (" + entries.length + ")";
  }
  function loadChangelog() {
    return fetch("changelog.json").then(function (r) { return r.text(); }).then(function (text) {
      window.CHANGELOG_JSON = text;
      var data = JSON.parse(text);
      var list = Array.isArray(data) ? data : (data && data.changelog) || [];
      renderChangelog(list.slice().sort(function (x, y) { return x.date < y.date ? 1 : -1; }));
    }).catch(function () { renderChangelog([]); });
  }

  var TUTORIAL_STEPS = [
    { title: "Welcome to the committee", text: "You never control the heist itself. You control the plan: who does what, and when. Then you watch it play out, and whatever goes wrong goes wrong for a reason you can read. Skip any time and reopen this from the Tutorial button." },
    { selector: "#board-cards", title: "Pick a job", text: "Each job is a target with a prize. A bad night still pays a little, nobody is ever eliminated, and more jobs open as your reputation grows." },
    { selector: "#hud", title: "Cash and reputation", text: "Cash pays the crew and buys gear. Reputation opens new jobs, new crew and new gear, and only goes up when a job goes better than you managed before." },
    { title: "Scout and hire", text: "Before hiring, scout the place to learn what might go wrong. Then choose five of eight crew: each has a visible trait and a hidden quirk you learn by watching them work, or by paying for a background check." },
    { title: "The timeline", text: "Rows are crew, columns are beats. Pick an action from the tray and tap cells, or tap a cell then an action, or drag. Arrow keys and Enter work too. Tap any filled cell to see exactly why its odds are what they are." },
    { title: "The checklist", text: "The list beside the timeline tells you which goals your plan covers, which actions are missing something they need (a Lookout for a lockpick, say), and which crew will clash. Warnings never block you: you may run a broken plan on purpose." },
    { title: "Standby and slack", text: "A crew member on Standby for one kind of trouble absorbs it. A crew member with nothing to do and the right skill can help too. Standing around costs a turn, so use it where you expect trouble." },
    { title: "Watch it play", text: "Press Next beat to reveal the job one beat at a time. Every line says why it happened. At the end the payout shows the chain of events and which link started it. Retry the same night with a better plan any time." },
    { selector: "#settings-toggle-button", title: "Settings", text: "Text size, reduced motion, an effects switch, high contrast, optional auto-advance for the playback, and the light or dark theme." },
    { selector: "#info-page-toggle-button", title: "How it works", text: "The rules behind the odds, written out. The game is fiction, so there are no real-world facts to cite." },
    { title: "You are ready", text: "Have fun, and keep the plan flexible." }
  ];

  HC.afterBoot = async function () {
    wirePanelsAfter();
    await loadChangelog();
    var reply = HC.send({ action: "info" });
    if (reply && reply.info) renderInfo(reply.info);
    if (window.GameTutorial) window.GameTutorial.init(window.heistTutorialSteps ? window.heistTutorialSteps(TUTORIAL_STEPS) : TUTORIAL_STEPS, { gameId: "heist-committee" });
    if (window.MobileHud) window.MobileHud.init([{ selector: "#hud-cash", label: "Cash" }, { selector: "#hud-rep", label: "Rep" }, { selector: "#hud-status", label: "Now" }]);
    if (window.MobileDock) window.MobileDock.init("#tray-panel");
  };
  function wirePanelsAfter() { /* panels are wired in wireGlobal; kept for symmetry */ }

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
    var choice = "continue";
    try { if (window.NoyvjOpeningScreen && window.NoyvjOpeningScreen.choice) choice = await window.NoyvjOpeningScreen.choice; } catch (e) { /* continue */ }
    if (choice === "new") { try { localStorage.removeItem(STORE_KEY); } catch (e) { /* ok */ } }
    var saved = choice === "new" ? null : lsGet(STORE_KEY);
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
