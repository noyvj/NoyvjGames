/* Chronicle, part 3 of 5: the five other boards: cause web, myth or record, whose account?, decision points, review. */
(function () {
  "use strict";

  var A = window.ChronicleApp;
  var $ = A.$, act = A.act, announce = A.announce, claimBlock = A.claimBlock, clear = A.clear,
      currentMode = A.currentMode, el = A.el;

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
    var w = A.view.web;
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
    if (A.webPick && !w.cards.some(function (c) { return c.id === A.webPick; })) A.webPick = null;
    w.cards.forEach(function (c) {
      var li = el("li", "web-item");
      var b = el("button", "web-card");
      b.type = "button";
      b.setAttribute("data-wcard", c.id);
      b.setAttribute("data-fk", "wcard-" + c.id);
      var picked = A.webPick === c.id;
      b.setAttribute("aria-pressed", String(picked));
      b.setAttribute("aria-label", "Moment " + c.n + " of " + w.size + ": " + c.title + (picked ? ". Picked up as the cause. Now pick the moment it led to." : ""));
      b.appendChild(el("span", "web-num", String(c.n)));
      b.appendChild(el("span", "web-title", c.title));
      b.appendChild(el("span", "web-state", picked ? "▶ Cause picked up" : (A.webPick ? "Tap: it led to this" : "Tap to pick as the cause")));
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
    $("web-message").textContent = w.message || (A.view.first_run ? "Pick the earlier moment first, then the one it led to." : "");
    $("web-show-button").hidden = finished;
    $("web-cancel-button").hidden = !A.webPick;
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
    if (!A.view || !A.view.web || A.view.web.status !== "playing") return;
    if (!A.webPick) { A.webPick = id; renderWeb(); announce("Picked up " + cardTitle(id) + " as the cause. Now pick the moment it led to, or press Escape."); return; }
    if (A.webPick === id) { A.webPick = null; renderWeb(); announce("Put the card down."); return; }
    var from = A.webPick;
    A.webPick = null;
    var resp = act({ action: "web_link", from: from, to: id });
    if (resp && resp.ok) announce(A.view.web.message);
  }

  function cardTitle(id) {
    var c = A.view.web.cards.filter(function (x) { return x.id === id; })[0];
    return c ? c.title : id;
  }

  // ---- myth or record -----------------------------------------------------------------------------------------
  // The three bins are written out (symbol + words) and drawn with three border styles, so colour is never needed.
  function renderMyth() {
    if (currentMode() !== "myth") return;
    var m = A.view.myth;
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
    $("myth-message").textContent = m.message || (A.view.first_run ? "Pick a bin under each statement, then press Check." : "");
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
    if (!A.view || !A.view.myth || A.view.myth.status !== "playing") return;
    var resp = act({ action: "myth_sort", claim: claimId, bin: bin });
    if (resp && resp.ok) announce("Sorted as " + binLabel(A.view.myth, bin) + ".");
  }


  // ---- whose account? -----------------------------------------------------------------------------------------
  // Every question is a choice from a fixed list the engine built from the passage's own metadata (no typing).
  // State is written ("Right answer (locked)", "Not this one yet") and drawn with border styles, never colour alone.
  function renderAccount() {
    if (currentMode() !== "account") return;
    var a = A.view.account;
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
    $("account-message").textContent = a.message || (A.view.first_run ? "Read the passages, then answer each question about the one marked with a diamond." : "");
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
    if (!A.view || !A.view.account || A.view.account.status !== "playing") return;
    var resp = act({ action: "account_answer", question: qid, choice: opt });
    if (resp && resp.ok) announce("Chosen.");
  }

  // ---- decision points ----------------------------------------------------------------------------------------
  function renderDecision() {
    if (currentMode() !== "decision") return;
    var d = A.view.decision;
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
    $("decision-message").textContent = d.decided ? "You made your choice. What happened is below." : (A.view.first_run ? "Pick an option. There is no right answer." : "");
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
    if (!A.view || !A.view.decision || A.view.decision.decided) return;
    var resp = act({ action: "decision_pick", option: optId });
    if (resp && resp.ok) announce("Choice made. What they chose and what followed are shown below.");
  }

  // ---- review ----------------------------------------------------------------------------------------------------
  // One question at a time, in the order the schedule gives. Everything is written in words and nothing is timed.
  function renderReview() {
    if (currentMode() !== "review") return;
    var r = A.view.review;
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
    if (!A.view || !A.view.review || !A.view.review.question) return;
    var resp = act({ action: "review_answer", key: key, choice: opt });
    if (resp && resp.ok && A.view.review.feedback) {
      announce(A.view.review.feedback.message);
      var n = $("review-next-button");
      if (n && !n.hidden) n.focus();
    }
  }

  // what the other parts use (see the File map in CLAUDE.md)
  A.answerAccount = answerAccount; A.answerReview = answerReview; A.onWebCard = onWebCard;
  A.passageReveal = passageReveal; A.pickDecision = pickDecision; A.renderAccount = renderAccount;
  A.renderDecision = renderDecision; A.renderMyth = renderMyth; A.renderReview = renderReview;
  A.renderWeb = renderWeb; A.sortClaim = sortClaim; A.threadBlock = threadBlock;
})();
