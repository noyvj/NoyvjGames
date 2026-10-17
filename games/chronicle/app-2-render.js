/* Chronicle, part 2 of 5: render(), mode tabs, chapter cards, the timeline board, claim and source blocks, glyphs,
 * the result panel and the nuance strip. Browser glue only; every rule is in the Python engine. */
(function () {
  "use strict";

  var A = window.ChronicleApp;
  var $ = A.$, act = A.act, clear = A.clear, el = A.el, renderAchievements = A.renderAchievements,
      setStatus = A.setStatus;
  var lastFocusKey = null;

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
    if (!A.view) return;
    captureFocus();
    if (A.view.empty) {
      setStatus("No sets could be loaded. " + (A.view.problems || []).join(" "));
      return;
    }
    renderMeterAndPicker();
    renderModeTabs();
    renderSections();
    renderPuzzle();
    renderResult();
    A.renderWeb();
    A.renderMyth();
    A.renderAccount();
    A.renderDecision();
    A.renderReview();
    renderAchievements();
    var hints = $("hints-checkbox");
    if (hints) hints.checked = !!A.view.settings.hints;
    restoreFocus();
  }

  function renderMeterAndPicker() {
    if (!A.view || A.view.empty) return;
    var sel = $("set-select");
    if (sel.options.length !== A.view.sets.length || sel.getAttribute("data-built") !== A.view.sets.map(function (s) { return s.id; }).join(",")) {
      clear(sel);
      A.view.sets.forEach(function (s) {
        var o = el("option", null, s.title);
        o.value = s.id;
        sel.appendChild(o);
      });
      sel.setAttribute("data-built", A.view.sets.map(function (s) { return s.id; }).join(","));
    }
    sel.value = A.view.set.id;
    var badge = $("set-status");
    badge.textContent = A.view.set.status_label;
    badge.className = "badge" + (A.view.set.draft ? "" : " reviewed");
    $("draft-banner").hidden = !A.view.set.draft;
    $("set-summary").textContent = A.view.set.description;
    $("meter").value = A.view.set.percent;
    $("meter-text").textContent = A.view.set.found + " of " + A.view.set.total + " found (" + A.view.set.percent + "%)";
  }

  function currentMode() { return (A.view && A.view.mode) || "timeline"; }

  var MODE_IDS = ["timeline", "web", "myth", "account", "decision", "review"];
  var MODE_KEYS = { t: "timeline", w: "web", m: "myth", a: "account", d: "decision", r: "review" };
  var MODE_LABELS = { timeline: "Timeline", web: "Cause web", myth: "Myth or record", account: "Whose account?", decision: "Decision points", review: "Review" };
  var MODE_PANELS = { timeline: "puzzle-panel", web: "web-panel", myth: "myth-panel", account: "account-panel", decision: "decision-panel", review: "review-panel" };
  var MODE_SKIP = { timeline: "Skip to the timeline", web: "Skip to the cause web", myth: "Skip to myth or record", account: "Skip to whose account", decision: "Skip to decision points", review: "Skip to review" };

  function renderModeTabs() {
    var mode = currentMode();
    var modes = A.view.modes || [{ id: "timeline", label: "Timeline", available: true }];
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
    var board = kind === "web" ? A.view.web : (kind === "myth" ? A.view.myth : (kind === "account" ? A.view.account : A.view.decision));
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
    if (mode === "web") { renderChapters(A.view.webs, "web"); return; }
    if (mode === "myth") { renderChapters(A.view.myths, "myth"); return; }
    if (mode === "account") { renderChapters(A.view.accounts, "account"); return; }
    if (mode === "decision") { renderChapters(A.view.decisions, "decision"); return; }
    if (mode === "review") { clear($("sections")).hidden = true; return; }
    $("sections").hidden = false;
    var nav = clear($("sections"));
    nav.setAttribute("aria-label", "Sections");
    var current = A.view.puzzle.section;
    A.view.sections.forEach(function (s) {
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
    var p = A.view.puzzle;
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
      if (A.selected && !s.locked) cls += " target";
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
        b.addEventListener("dragstart", function (ev) { A.startDrag(ev, s.card, s.index); });
      }
      if (A.selected && A.selected.id === s.card) b.setAttribute("aria-pressed", "true");
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
      b.setAttribute("aria-pressed", String(!!(A.selected && A.selected.id === id)));
      if (!finished) {
        b.draggable = true;
        b.addEventListener("dragstart", function (ev) { A.startDrag(ev, id, null); });
      }
      tray.appendChild(b);
    });
    if (A.selected && !(p.tray.indexOf(A.selected.id) >= 0 || p.slots.some(function (s) { return s.card === A.selected.id && !s.locked; }))) A.selected = null;

    $("message-line").textContent = p.message || (A.view.first_run && p.checks === 0 ? "Pick up a card, then tap a slot. Earliest goes in slot 1." : "");
    var check = $("check-button");
    check.hidden = finished;
    check.setAttribute("aria-disabled", String(!p.all_placed));
    check.textContent = p.all_placed ? "Check" : "Check (fill every slot first)";
    $("show-answer-button").hidden = finished;
    $("next-button").hidden = !finished;
    $("next-button").textContent = p.status === "solved" ? "Next puzzle" : "Next puzzle";
    $("return-button").hidden = !(A.selected && A.selected.slot !== null);
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
    rb.addEventListener("click", function () { A.openReport(claim, rb); });
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
    var r = A.view.result;
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

  // what the other parts use (see the File map in CLAUDE.md)
  A.MODE_IDS = MODE_IDS; A.MODE_KEYS = MODE_KEYS; A.MODE_LABELS = MODE_LABELS; A.claimBlock = claimBlock;
  A.currentMode = currentMode; A.eventBlock = eventBlock; A.glyph = glyph; A.render = render;
  A.renderMeterAndPicker = renderMeterAndPicker;
})();
