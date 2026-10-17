/* Chronicle, part 4 of 5: switching modes, placing cards (tap and drag), report a problem (UI only), the archive and the Info page. */
(function () {
  "use strict";

  var A = window.ChronicleApp;
  var $ = A.$, MODE_LABELS = A.MODE_LABELS, act = A.act, announce = A.announce, claimBlock = A.claimBlock,
      clear = A.clear, el = A.el, eventBlock = A.eventBlock, glyph = A.glyph, jsonParse = A.jsonParse,
      lsGet = A.lsGet, lsSet = A.lsSet, passageReveal = A.passageReveal, plural = A.plural, render = A.render,
      startEngine = A.startEngine, threadBlock = A.threadBlock;
  var LS_REPORTS = "chronicle:report-drafts";

  function switchMode(mode) {
    var info = ((A.view && A.view.modes) || []).filter(function (m) { return m.id === mode; })[0];
    if (!A.view) { startEngine(); return; }
    if (info && !info.available) { $("message-line").textContent = "This set does not have that mode yet."; announce("This set does not have that mode yet."); return; }
    A.selected = null; A.webPick = null;
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
      A.selected = null;
      if (A.view.first_run) act({ action: "ack" }, { render: false });
      render();
      announce("Placed in slot " + (slot + 1) + ".");
    } else if (resp) render();
  }

  function unplaceSlot(slot) {
    var resp = act({ action: "unplace", slot: slot }, { render: false });
    if (resp && resp.ok) A.selected = null;
    if (resp) render();
  }

  function onSlot(index) {
    if (!A.view || A.view.puzzle.status !== "playing") return;
    var s = A.view.puzzle.slots[index];
    if (s.locked) { $("message-line").textContent = "That card is locked: it is already in its right place."; return; }
    if (A.selected) { placeCard(A.selected.id, index); return; }
    if (s.card) { A.selected = { id: s.card, slot: index }; render(); announce("Picked up " + A.view.puzzle.cards[s.card].title + ". Choose a slot, or press Escape."); return; }
    $("message-line").textContent = "Pick up a card from the tray first.";
  }

  function onCard(id) {
    if (!A.view || A.view.puzzle.status !== "playing") return;
    if (A.selected && A.selected.id === id) A.selected = null;
    else A.selected = { id: id, slot: null };
    render();
    if (A.selected) announce("Picked up " + A.view.puzzle.cards[id].title + ". Choose a slot, or press Escape.");
  }

  // ---- report a problem (UI only) ----------------------------------------------------------------------------------
  function openReport(claim, opener) {
    A.currentReport = { claim: claim, opener: opener };
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
    if (!A.currentReport) return;
    var resp = act({ action: "report", set: A.currentReport.claim.set, claim: A.currentReport.claim.id, reason: $("report-reason").value, note: $("report-note").value }, { render: false });
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

  // what the other parts use (see the File map in CLAUDE.md)
  A.buildReport = buildReport; A.onCard = onCard; A.onSlot = onSlot; A.openArchive = openArchive;
  A.openInfo = openInfo; A.openReport = openReport; A.placeCard = placeCard; A.startDrag = startDrag;
  A.switchMode = switchMode; A.unplaceSlot = unplaceSlot;
})();
