/* Heist Committee -- playback and payout. Playback reveals the engine's event log one beat at a time (the whole heist
   is already decided by the plan and the seed; this only controls what has been shown). An optional auto-advance
   only calls "step" at a human pace and is never needed. No game logic here. */
(function () {
  "use strict";
  var HC = window.HC, $ = HC.$, el = HC.el;

  var playing = false;
  var timer = null;
  var lastCursor = -1;
  var STEP_MS = 2800;

  function clearTimer() { if (timer) { clearTimeout(timer); timer = null; } }

  var TAGS = {
    crit: ["★", "Perfect"], success: ["✓", "Success"], partial: ["~", "Messy"], fail: ["✗", "Failed"]
  };
  function tagFor(ev) {
    if (ev.type === "action" || ev.type === "support") return TAGS[ev.outcome] || ["·", ""];
    return {
      complication: ["⚡", "Trouble"], absorb: ["🛡", "Absorbed"], goal: ["★", "Done"], pair: ["⚡", "Relationship"],
      trait: ["●", "Quirk"], sidelined: ["🩹", "Out"], note: ["…", ""], action_start: ["·", "Starts"]
    }[ev.type] || ["·", ""];
  }

  function eventNode(ev, fresh) {
    if (ev.type === "beat") {
      return el("li", { "class": "beat-line" + (fresh ? " fresh" : ""), "data-beat": ev.beat }, [ev.text,
        ev.note ? el("span", { "class": "ev-why", text: ev.note }) : null]);
    }
    var t = tagFor(ev);
    var cls = "t-" + ev.type + (ev.outcome ? " out-" + ev.outcome : "") + (fresh ? " fresh" : "");
    return el("li", { "class": cls, "data-testid": "heist-event-" + ev.i }, [
      el("span", { "class": "ev-text" }, [el("span", { "class": "ev-tag", text: t[0] + (t[1] ? " " + t[1] : "") + ":" }), ev.text]),
      ev.why ? el("span", { "class": "ev-why", text: "Why: " + ev.why }) : null,
      ev.flavor ? el("span", { "class": "ev-flavor", text: ev.flavor }) : null]);
  }

  function ensureSkeleton() {
    var body = $("playback-body");
    if (body.dataset.built) return;
    body.dataset.built = "1";
    body.appendChild(el("p", { id: "pb-status", "class": "note", "aria-live": "polite" }));
    body.appendChild(el("div", { "class": "timeline-wrap" }, [el("div", { id: "pb-timeline", "class": "timeline", role: "grid", "aria-label": "Heist timeline, results so far" })]));
    body.appendChild(el("div", { "class": "pb-controls" }, [
      el("button", { id: "pb-next", type: "button", "class": "primary", "data-testid": "heist-next-beat", text: "Next beat",
        onclick: function () { playing = false; HC.send({ action: "step" }); } }),
      el("button", { id: "pb-play", type: "button", "aria-pressed": "false", "data-testid": "heist-play", text: "Play",
        onclick: function () { playing = !playing; schedule(); updateButtons(); } }),
      el("button", { id: "pb-skip", type: "button", "data-testid": "heist-skip", text: "Skip to the end",
        onclick: function () { playing = false; HC.send({ action: "skip" }); } }),
      el("button", { id: "pb-finish", type: "button", "class": "primary", "data-testid": "heist-finish", text: "See the payout", hidden: true,
        onclick: function () { playing = false; HC.send({ action: "finish" }); } })]));
    body.appendChild(el("ol", { id: "pb-log", "class": "log", "aria-label": "What happened" }));
  }

  function updateButtons() {
    var view = HC.view;
    if (!view || view.phase !== "playback") return;
    var done = view.playback.done;
    $("pb-next").hidden = done;
    $("pb-play").hidden = done;
    $("pb-skip").hidden = done;
    $("pb-finish").hidden = !done;
    $("pb-play").textContent = playing ? "Pause" : "Play";
    $("pb-play").setAttribute("aria-pressed", playing ? "true" : "false");
  }

  function schedule() {
    clearTimer();
    var view = HC.view;
    if (!playing || !view || view.phase !== "playback" || view.playback.done) { playing = false; return; }
    timer = setTimeout(function () {
      timer = null;
      if (playing) HC.send({ action: "step" });
    }, STEP_MS);
  }

  function renderPlayback(view) {
    ensureSkeleton();
    var pb = view.playback;
    if (lastCursor === -1 || pb.cursor < lastCursor) {
      playing = !!(window.HeistSettings && window.HeistSettings.autoplay());
    }
    HC.setText($("pb-status"), pb.cursor === 0 ? "The crew are in position. Press Next beat to begin." :
      pb.done ? "That was the last beat." : "Beat " + pb.cursor + " of " + pb.n + " done: " + pb.beat_name + ".");
    HC.buildTimeline($("pb-timeline"), view, "playback", { results: pb.results, now: pb.cursor === 0 ? undefined : pb.cursor - 1 });
    var log = $("pb-log");
    var grew = pb.cursor > lastCursor && lastCursor !== -1;
    log.textContent = "";
    var announceBits = [];
    pb.events.forEach(function (ev) {
      var fresh = grew && ev.beat === pb.cursor - 1;
      log.appendChild(eventNode(ev, fresh));
      if (fresh && ev.type !== "beat" && announceBits.length < 4) announceBits.push(ev.text);
    });
    if (grew) {
      HC.announce("Beat " + pb.cursor + ", " + pb.beat_name + ". " + announceBits.join(" "));
      var firstFresh = log.querySelector(".fresh");
      if (firstFresh && firstFresh.scrollIntoView) firstFresh.scrollIntoView({ block: "nearest" });
    }
    lastCursor = pb.cursor;
    updateButtons();
    schedule();
  }
  HC.renderers.playback = renderPlayback;

  HC.onRender.push(function (view) {
    if (view.phase !== "playback") { clearTimer(); playing = false; lastCursor = -1; }
  });
  document.addEventListener("heist-autoplay-change", function () {
    var view = HC.view;
    if (view && view.phase === "playback") { playing = window.HeistSettings.autoplay(); schedule(); updateButtons(); }
  });

  // ---- payout --------------------------------------------------------------------------------------
  function line(label, value, total) {
    return el("div", { "class": "money-line" + (total ? " total" : "") }, [el("span", { text: label }), el("span", { text: value })]);
  }
  function sign(n) { return (n >= 0 ? "+" : "-") + Math.abs(n); }

  var BANNERS = {
    clean: ["★", "A clean getaway"], loud: ["⚠", "Got it, loudly"], stranded: ["🚶", "Stranded with the loot"], bust: ["✗", "Came home empty-handed"]
  };

  HC.renderers.payout = function (view) {
    var p = view.payout;
    var root = $("payout-body");
    HC.fillOnce(root, JSON.stringify([p, view.cash]), function (box) {
      var b = BANNERS[p.cls];
      box.appendChild(el("div", { "class": "banner", "data-testid": "heist-banner" }, [
        el("h3", { text: b[0] + " " + b[1] + ": " + p.title }),
        el("p", { "class": "note", text: view.target.name + ", attempt " + p.attempt })]));
      box.appendChild(el("div", { "class": "stats-grid" }, [
        stat("Loot", String(p.loot)), stat("Souvenirs", String(p.souvenirs)), stat("Heat", p.heat + " of 10"),
        stat("Damages", String(p.damages)), stat("Chain", p.chain_links ? p.chain_links + " links" : "none"),
        stat("Absorbed", String(p.absorbed))]));
      var money = el("div", { "class": "panel" }, [el("h3", { text: "The take" })]);
      money.appendChild(line("Loot and souvenirs", String(p.loot + p.souvenirs)));
      if (p.heat_cost) money.appendChild(line("Heat (" + p.heat + ") takes a cut", "-" + p.heat_cost));
      p.bonuses.forEach(function (bn) { money.appendChild(line(bn.label, sign(bn.amount))); });
      if (p.damages) money.appendChild(line("Damages and plasters", "-" + p.damages));
      money.appendChild(line(p.net === p.consolation && !p.escaped ? "Payout (the committee's consolation minimum)" : "Payout for this attempt", String(p.net), true));
      if (p.attempt > 1) {
        money.appendChild(line("Best earlier attempt", String(p.best_net - p.credited)));
      }
      money.appendChild(line("Added to the purse", sign(p.credited), true));
      money.appendChild(line("Reputation", sign(p.rep_gained) + " (now " + p.reputation + ")"));
      if (p.attempt > 1) money.appendChild(el("p", { "class": "note", text: "A retry only pays what it adds beyond your best earlier attempt, so you can keep improving without grinding." }));
      box.appendChild(money);
      var req = el("div", { "class": "panel" }, [el("h3", { text: "Goals" })]);
      var ul = el("ul", { "class": "list-plain" });
      view.requirements.forEach(function (r) {
        var done = p.completed.indexOf(r.id) !== -1;
        ul.appendChild(el("li", { text: (done ? "✓ Done: " : (r.optional ? "○ Skipped: " : "✗ Missed: ")) + r.label }));
      });
      req.appendChild(ul);
      if (p.sidelined.length) req.appendChild(el("p", { "class": "note", text: "Sidelined: " + p.sidelined.join(", ") + "." }));
      box.appendChild(req);
      var chain = el("div", { "class": "panel" }, [el("h3", { text: "What happened: the chain" })]);
      if (p.chain.length >= 2) {
        var ol = el("ol", { "class": "chain", "aria-label": "Chain of events, first to last" });
        p.chain.forEach(function (c, i) {
          ol.appendChild(el("li", { "class": i === 0 ? "first" : "" }, [(c.icon || "·") + " Beat " + (c.beat + 1) + ": " + c.text]));
        });
        chain.appendChild(ol);
        chain.appendChild(el("p", { "class": "note", text: "Fix the first link and the rest never happens." }));
      } else {
        chain.appendChild(el("p", { text: "No chain this time: nothing led to anything else." }));
      }
      box.appendChild(chain);
      if (p.new_unlocks.length || p.relations_changed.length) {
        var news = el("div", { "class": "panel" }, [el("h3", { text: "News from the committee" })]);
        var nl = el("ul", { "class": "list-plain" });
        p.new_unlocks.forEach(function (n) { nl.appendChild(el("li", { text: "New: " + n + " is now open." })); });
        p.relations_changed.forEach(function (r) {
          nl.appendChild(el("li", { text: r.a + " and " + r.b + (r.kind === "friends" ? " are now friends. They work well in the same beat." : " are now feuding. Keep them apart.") }));
        });
        news.appendChild(nl);
        box.appendChild(news);
      }
      box.appendChild(el("div", { "class": "panel" }, [el("h3", { text: "The write-up" }), el("p", { "class": "writeup", "data-testid": "heist-writeup", text: p.writeup })]));
      box.appendChild(el("div", { "class": "phase-actions" }, [
        el("button", { type: "button", "class": "primary", "data-testid": "heist-retry", text: "Retry this target (same crew, same night)",
          onclick: function () { HC.send({ action: "retry" }); } }),
        el("button", { type: "button", "data-testid": "heist-back-to-board", text: "Back to the board",
          onclick: function () { HC.send({ action: "back_to_board" }); } })]));
    });
  };
  function stat(k, v) { return el("div", { "class": "stat" }, [el("span", { "class": "k", text: k }), el("span", { "class": "v", text: v })]); }
})();
