/* Rule Finder view: glue only. The engine (game.py and its modules) holds every rule; this file draws what handle() returns,
   turns the item builder and the Rule Builder into test / preview / name requests, and forwards what the player does. No game
   logic lives here: whether an item goes Through is always the engine's answer. */
(function () {
  "use strict";
  var ENGINE_MODULES = ["lang.py", "cases_numbers.py", "cases_shapes.py", "cases_two.py", "cases_not.py", "cases.py", "progress.py", "codex.py", "render.py"];
  var STORE_KEY = "rule-finder:state";
  var BACKUP_KEY = "rule-finder:state-backup";
  var SHAPE_NAMES = { c: "circle", s: "square", t: "triangle", d: "diamond" };
  var SHAPE_ORDER = ["c", "s", "t", "d"];
  var MEDAL_WORDS = { gold: "Gold", silver: "Silver", bronze: "Bronze" };

  var $ = function (id) { return document.getElementById(id); };
  var engine = null;
  var view = null;
  var caseId = null;       // the case the page is currently drawn for
  var menu = [];           // the clause menu of that case
  var rows = [];           // the Rule Builder rows: {op, neg, cid}
  var work = { num: "", shape: [], grid: [] };   // the item being built

  function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* convenience only */ } }
  function setText(node, text) { if (node.textContent !== text) node.textContent = text; }
  function announce(text) {
    var live = $("announce");
    live.textContent = "";
    setTimeout(function () { live.textContent = text; }, 40);
  }
  function el(tag, cls, text) {
    var node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function showToast(text) {
    var t = $("toast");
    t.textContent = text;
    t.classList.toggle("on", Boolean(text));
  }
  function plural(n, one, many) { return n + " " + (n === 1 ? one : many); }
  function verdictWord(yes) { return yes ? "Through" : "Stopped"; }

  // ---- panels --------------------------------------------------------------------------------------
  function wirePanelToggle(buttonId, panelId) {
    $(buttonId).addEventListener("click", function () {
      $(panelId).hidden = !$(panelId).hidden;
      $(buttonId).setAttribute("aria-expanded", String(!$(panelId).hidden));
    });
  }
  function renderChangelog(entries) {
    var holder = $("changelog-entries");
    holder.textContent = "";
    entries.forEach(function (entry) {
      var row = el("article", "changelog-entry");
      row.appendChild(el("div", "changelog-date", entry.date));
      row.appendChild(el("p", "changelog-text", entry.entry));
      holder.appendChild(row);
    });
    document.querySelector("#changelog-toggle-button .btn-long").textContent = "What's New (" + entries.length + ")";
  }
  function loadChangelog() {
    return fetch("changelog.json").then(function (r) { return r.text(); }).then(function (text) {
      window.CHANGELOG_JSON = text;
      var data = JSON.parse(text);
      var list = Array.isArray(data) ? data : (data && data.changelog) || [];
      renderChangelog(list.slice().sort(function (a, b) { return a.date < b.date ? 1 : -1; }));
    }).catch(function () { renderChangelog([]); });
  }

  // ---- items: a number, a string of tiles or a 3 by 3 pattern, drawn as small SVGs -----------------------------
  function glyph(letter, cx) {
    if (letter === "c") return '<circle class="sh-c" cx="' + cx + '" cy="17" r="5"/>';
    if (letter === "s") return '<rect class="sh-s" x="' + (cx - 7) + '" y="10" width="14" height="14" rx="1"/>';
    if (letter === "t") return '<polygon class="sh-t" points="' + cx + ",7 " + (cx + 9.5) + ",25 " + (cx - 9.5) + ',25"/>';
    return '<polygon class="sh-d" points="' + cx + ",3 " + (cx + 11) + ",17 " + cx + ",31 " + (cx - 11) + ',17"/>';
  }
  function itemSvg(kind, key, label) {
    var open = function (w, h, cls) {
      return '<svg class="rf-item ' + cls + '" viewBox="0 0 ' + w + " " + h + '" role="img" aria-label="' + (label || key) + '" focusable="false">';
    };
    if (kind === "num") {
      return open(46, 34, "rf-num") + '<rect class="tile" x="1" y="1" width="44" height="32" rx="7"/><text class="num-text" x="23" y="18">' + key + "</text></svg>";
    }
    if (kind === "shape") {
      var out = open(30 * key.length + 2, 34, "rf-shape");
      for (var i = 0; i < key.length; i++) {
        out += '<rect class="tile" x="' + (2 + i * 30) + '" y="1" width="28" height="32" rx="6"/>' + glyph(key.charAt(i), 16 + i * 30);
      }
      return out + "</svg>";
    }
    var g = open(40, 40, "rf-grid-item");
    for (var n = 0; n < 9; n++) {
      g += '<rect class="' + (key.charAt(n) === "#" ? "cell-on" : "cell-off") + '" x="' + (3 + (n % 3) * 12) + '" y="' + (3 + Math.floor(n / 3) * 12) + '" width="11" height="11" rx="2"/>';
    }
    return g + "</svg>";
  }
  function itemWords(kind, key) {
    if (kind === "num") return key;
    if (kind === "shape") return key.split("").map(function (c) { return SHAPE_NAMES[c]; }).join(" ");
    var filled = key.split("").filter(function (c) { return c === "#"; }).length;
    return filled + " filled squares: " + [0, 1, 2].map(function (r) {
      return "row " + (r + 1) + " " + [0, 1, 2].map(function (c) { return key.charAt(r * 3 + c) === "#" ? "filled" : "empty"; }).join(" ");
    }).join(", ");
  }

  // ---- stats ---------------------------------------------------------------------------------------
  function bumpStat(id, value) {
    var node = $(id);
    var next = String(value);
    if (node.textContent === next) return;
    var had = node.dataset.seen === "1";
    node.textContent = next;
    node.dataset.seen = "1";
    if (had) {
      node.classList.remove("bump");
      void node.offsetWidth;
      node.classList.add("bump");
    }
  }
  function renderStats() {
    bumpStat("stat-named", view.totals.named + "/" + view.totals.cases);
    bumpStat("stat-tests", view.tally.tests);
    bumpStat("stat-codex", view.totals.pages + "/" + view.totals.cases);
    bumpStat("stat-clean", view.totals.clean);
    bumpStat("stat-near", view.tally.near);
  }

  // ---- the case, the gate and your log ------------------------------------------------------------------
  function renderCase() {
    var c = view.case;
    setText($("case-drawer"), c.drawer + " · case " + c.number + " of " + c.of + (c.status === "named" ? " · named" : ""));
    setText($("case-heading"), c.name);
    setText($("here-line"), "Tests here: " + c.tests + " · par " + c.par + (c.free ? " · free counter-examples: " + c.free : "") + (c.best !== null ? " · your best: " + c.best : ""));
    setText($("case-brief"), c.blurb + " " + (c.max_clauses === 1 ? "A rule here is one property of a " + c.subject + "." : "A rule here is up to " + c.max_clauses + " properties joined together."));
  }
  function renderGate(animate) {
    var gate = $("gate-svg");
    var line = $("gate-line");
    var chip = $("gate-item");
    var last = view.last;
    if (!last) {
      gate.setAttribute("data-verdict", "idle");
      chip.className = "gate-item";
      chip.textContent = "";
      line.className = "gate-line";
      setText(line, "Build an item below and send it to see what the gate does.");
      return;
    }
    var word = verdictWord(last.yes);
    gate.setAttribute("data-verdict", last.yes ? "through" : "stopped");
    chip.innerHTML = itemSvg(view.case.kind, last.item, last.label);
    if (animate) {
      chip.className = "gate-item";
      void chip.offsetWidth;
    }
    chip.className = "gate-item on " + (last.yes ? "through" : "stopped");
    line.className = "gate-line " + (last.yes ? "through" : "stopped");
    var who = view.case.kind === "num" ? last.item : "This " + view.case.subject;
    setText(line, (last.repeat ? "Already sent. " : "") + who + " goes " + word + (last.yes ? " ✓" : " ✕"));
  }
  function renderLog() {
    var c = view.case;
    var through = $("through-list");
    var stopped = $("stopped-list");
    var sig = c.id + "|" + c.log.map(function (e) { return e.item + e.src; }).join(",");
    var counts = [0, 0];
    c.log.forEach(function (e) { counts[e.yes ? 0 : 1] += 1; });
    setText($("through-count"), "(" + counts[0] + ")");
    setText($("stopped-count"), "(" + counts[1] + ")");
    if (through.dataset.sig === sig) return;
    through.dataset.sig = sig;
    through.textContent = "";
    stopped.textContent = "";
    var newest = null;
    c.log.forEach(function (e, i) { if (e.src !== "given") newest = i; });
    c.log.forEach(function (e, i) {
      var li = el("li", i === newest ? "newest" : "");
      li.innerHTML = itemSvg(c.kind, e.item, e.label + ", " + (e.yes ? "Through" : "Stopped") + (e.src === "given" ? ", a starting example" : e.src === "free" ? ", a counter-example" : ""));
      if (e.src !== "given") li.appendChild(el("span", "tag", e.src === "free" ? "free" : "test"));
      else li.appendChild(el("span", "tag", "given"));
      (e.yes ? through : stopped).appendChild(li);
    });
  }

  // ---- the item builder ---------------------------------------------------------------------------------
  function workKey() {
    var kind = view ? view.case.kind : "num";
    if (kind === "num") return /^\d{1,2}$/.test(work.num.trim()) ? String(parseInt(work.num, 10)) : null;
    if (kind === "shape") return work.shape.length >= 3 && work.shape.length <= 6 ? work.shape.join("") : null;
    return work.grid.map(function (v) { return v ? "#" : "."; }).join("");
  }
  function renderBuilder() {
    var kind = view.case.kind;
    $("builder-num").hidden = kind !== "num";
    $("builder-shape").hidden = kind !== "shape";
    $("builder-grid").hidden = kind !== "grid";
    if (kind === "shape") {
      var prev = $("shape-preview");
      prev.textContent = "";
      if (work.shape.length) prev.innerHTML = itemSvg("shape", work.shape.join(""), itemWords("shape", work.shape.join("")));
      else prev.appendChild(el("span", "empty", "No tiles yet. Tap a shape to add it."));
      $("shape-back-button").disabled = !work.shape.length;
      $("shape-clear-button").disabled = !work.shape.length;
      var full = work.shape.length >= 6;
      Array.prototype.forEach.call($("shape-palette").children, function (b) { b.disabled = full; });
    }
    if (kind === "grid") {
      Array.prototype.forEach.call($("grid-cells").children, function (b, i) {
        b.setAttribute("aria-pressed", String(Boolean(work.grid[i])));
        b.textContent = work.grid[i] ? "■" : "";
      });
      $("grid-clear-button").disabled = !work.grid.some(Boolean);
    }
    $("send-button").disabled = workKey() === null;
  }
  function buildStaticBuilder() {
    var palette = $("shape-palette");
    SHAPE_ORDER.forEach(function (letter) {
      var b = el("button");
      b.type = "button";
      b.dataset.testid = "rule-finder-shape-" + letter;
      b.setAttribute("aria-label", "Add a " + SHAPE_NAMES[letter]);
      b.innerHTML = itemSvg("shape", letter, SHAPE_NAMES[letter]).replace('class="rf-item rf-shape"', 'class="rf-item rf-shape" style="height:1.6rem"');
      b.appendChild(el("span", null, SHAPE_NAMES[letter]));
      b.addEventListener("click", function () {
        if (work.shape.length < 6) work.shape.push(letter);
        renderBuilder();
        announce("Added a " + SHAPE_NAMES[letter] + ". " + plural(work.shape.length, "tile", "tiles") + ".");
      });
      palette.appendChild(b);
    });
    var cells = $("grid-cells");
    for (var i = 0; i < 9; i++) {
      (function (n) {
        var b = el("button");
        b.type = "button";
        b.dataset.testid = "rule-finder-cell-" + n;
        b.setAttribute("aria-label", "Square " + (Math.floor(n / 3) + 1) + "," + (n % 3 + 1));
        b.setAttribute("aria-pressed", "false");
        b.addEventListener("click", function () { work.grid[n] = !work.grid[n]; renderBuilder(); });
        cells.appendChild(b);
      })(i);
      work.grid.push(false);
    }
    $("shape-back-button").addEventListener("click", function () { work.shape.pop(); renderBuilder(); });
    $("shape-clear-button").addEventListener("click", function () { work.shape = []; renderBuilder(); });
    $("grid-clear-button").addEventListener("click", function () { work.grid = work.grid.map(function () { return false; }); renderBuilder(); });
    $("num-input").addEventListener("input", function () { work.num = $("num-input").value; renderBuilder(); });
    $("num-input").addEventListener("keydown", function (e) { if (e.key === "Enter") { e.preventDefault(); onSend(); } });
    $("send-button").addEventListener("click", onSend);
  }
  function onSend() {
    var key = workKey();
    if (key === null) { announce("Finish the item first."); return; }
    var res = send({ action: "test", item: key });
    if (res && res.ok === false && res.message) showToast(res.message);
    if (view && view.case.kind === "num") { var input = $("num-input"); input.focus(); input.select(); }
  }

  // ---- the Rule Builder ---------------------------------------------------------------------------------
  function ruleFromRows() {
    if (!rows.length || rows.some(function (r) { return !r.cid; })) return null;
    return { lits: rows.map(function (r) { return [r.cid, r.neg ? 1 : 0]; }), ops: rows.slice(1).map(function (r) { return r.op; }) };
  }
  function renderRows() {
    var ul = $("rule-rows");
    ul.textContent = "";
    rows.forEach(function (row, i) {
      var li = el("li");
      if (i > 0) {
        var join = el("select", "join");
        join.setAttribute("aria-label", "How clause " + (i + 1) + " joins the ones before it");
        [["and", "and"], ["or", "or"]].forEach(function (o) {
          var opt = el("option", null, o[1]);
          opt.value = o[0];
          if (row.op === o[0]) opt.selected = true;
          join.appendChild(opt);
        });
        join.addEventListener("change", function () { row.op = join.value; onRulesChanged(); });
        li.appendChild(join);
      }
      var notLabel = el("label", "not");
      var box = el("input");
      box.type = "checkbox";
      box.checked = Boolean(row.neg);
      box.setAttribute("aria-label", "Not, for clause " + (i + 1));
      box.addEventListener("change", function () { row.neg = box.checked; onRulesChanged(); });
      notLabel.appendChild(box);
      notLabel.appendChild(document.createTextNode(" Not"));
      li.appendChild(notLabel);
      var sel = el("select", "clause");
      sel.setAttribute("aria-label", "Property for clause " + (i + 1));
      sel.dataset.testid = "rule-finder-clause-" + i;
      var none = el("option", null, "Choose a property...");
      none.value = "";
      sel.appendChild(none);
      menu.forEach(function (group) {
        var og = el("optgroup");
        og.label = group.label;
        group.clauses.forEach(function (c) {
          var opt = el("option", null, c.yes);
          opt.value = c.id;
          if (row.cid === c.id) opt.selected = true;
          og.appendChild(opt);
        });
        sel.appendChild(og);
      });
      sel.addEventListener("change", function () { row.cid = sel.value; onRulesChanged(); });
      li.appendChild(sel);
      if (i > 0) {
        var rm = el("button", null, "Remove");
        rm.type = "button";
        rm.setAttribute("aria-label", "Remove clause " + (i + 1));
        rm.addEventListener("click", function () { rows.splice(i, 1); renderRows(); onRulesChanged(); });
        li.appendChild(rm);
      }
      ul.appendChild(li);
    });
    $("add-clause-button").hidden = !view || rows.length >= view.case.max_clauses;
  }
  function onRulesChanged() {
    var rule = ruleFromRows();
    if (rule) send({ action: "preview", rule: rule }, true);
    else { setText($("rule-words"), ""); setText($("rule-check"), ""); }
    $("name-button").disabled = !rule;
  }
  function renderDraft() {
    var d = view.draft;
    if (!d) return;
    setText($("rule-words"), d.valid ? d.words : "");
    if (!d.valid) setText($("rule-check"), "");
    else if (d.conflict) setText($("rule-check"), "Careful: " + conflictText(d.conflict));
    else setText($("rule-check"), "Matches every item you have seen so far.");
  }
  function conflictText(cf) {
    var c = view.case;
    var who = c.kind === "num" ? cf.item : "an item in your log (" + cf.label + ")";
    return "your rule disagrees with " + who + ": the Sorter says " + cf.sorter + ", your rule says " + cf.rule + ".";
  }

  // ---- the verdict ----------------------------------------------------------------------------------------
  function medalNode(medal) {
    return el("span", "medal " + medal, MEDAL_WORDS[medal] + " medal");
  }
  function renderVerdict() {
    var card = $("verdict-card");
    var v = view.verdict;
    var c = view.case;
    var next = $("next-button");
    var restart = $("restart-button");
    var pageBtn = $("page-button");
    var item = $("verdict-item");
    var line = $("verdict-line");
    item.textContent = "";
    line.hidden = true;
    next.hidden = true;
    restart.hidden = true;
    pageBtn.hidden = true;
    if (!v && c.status !== "named") { card.hidden = true; return; }
    card.hidden = false;
    var text = $("verdict-text");
    text.textContent = "";
    if (v && v.kind === "near") {
      card.className = "verdict-card near";
      setText($("verdict-title"), "Not quite.");
      text.appendChild(document.createTextNode("Your rule and the Sorter disagree on this one: the Sorter says " + v.conflict.sorter + ", your rule says " + v.conflict.rule + ". It is in your log now, free, and did not count as a test."));
      item.innerHTML = itemSvg(c.kind, v.conflict.item, v.conflict.label);
      return;
    }
    if (v && v.kind === "conflict") {
      card.className = "verdict-card conflict";
      setText($("verdict-title"), "Not yet.");
      text.appendChild(document.createTextNode("Your rule already disagrees with something you have seen: " + conflictText(v.conflict).replace(/^your/, "Your")));
      return;
    }
    var best = v ? v.best : c.best;
    var medal = v ? v.medal : c.medal;
    card.className = "verdict-card named";
    setText($("verdict-title"), v && v.first ? "Named. You found it." : "Named.");
    text.appendChild(document.createTextNode(c.words + " "));
    text.appendChild(document.createTextNode("Tests used here: " + (v ? v.tests : c.tests) + ". Best: " + best + ". Par: " + c.par + ". "));
    text.appendChild(medalNode(medal));
    if (c.line) { line.hidden = false; setText(line, "Log: " + c.line); }
    var nextCase = v ? v.next : null;
    if (!v) {
      var cases = view.cases;
      var order = [];
      cases.forEach(function (d) { d.cases.forEach(function (x) { order.push(x); }); });
      var at = order.findIndex(function (x) { return x.id === c.id; });
      for (var k = 1; k < order.length; k++) {
        var cand = order[(at + k) % order.length];
        if (!cand.named) { nextCase = cand.id; break; }
      }
    }
    next.hidden = !nextCase;
    restart.hidden = false;
    pageBtn.hidden = false;
  }

  // ---- the drawers --------------------------------------------------------------------------------------
  function renderCases() {
    var holder = $("cases-body");
    var sig = JSON.stringify(view.cases.map(function (d) { return d.cases.map(function (x) { return (x.named ? x.best + x.medal : "-") + (x.current ? "c" : ""); }); }));
    if (holder.dataset.sig === sig) return;
    holder.dataset.sig = sig;
    holder.textContent = "";
    view.cases.forEach(function (d) {
      if (!d.total) return;
      var sec = el("section", "chapter");
      sec.appendChild(el("h3", null, d.name + " (" + d.named + "/" + d.total + " named)"));
      sec.appendChild(el("p", "note", d.blurb));
      var ul = el("ul", "room-grid");
      d.cases.forEach(function (x) {
        var li = el("li");
        var b = el("button", "room-btn" + (x.named ? " s1" : "") + (x.current ? " current" : ""));
        b.type = "button";
        b.dataset.testid = "rule-finder-case-" + x.id;
        b.appendChild(el("span", "rname", x.number + ". " + x.name));
        b.appendChild(el("span", "rmeta", x.named ? "Named · best " + plural(x.best, "test", "tests") + " · " + MEDAL_WORDS[x.medal] : "Not named yet"));
        b.setAttribute("aria-label", x.number + ", " + x.name + ". " + (x.named ? "Named, best " + plural(x.best, "test", "tests") + ", " + MEDAL_WORDS[x.medal] + " medal" : "Not named yet") + (x.current ? ". Current case" : ""));
        b.addEventListener("click", function () {
          send({ action: "pick", case: x.id });
          $("cases-panel").hidden = true;
          $("cases-toggle-button").setAttribute("aria-expanded", "false");
          var anchor = $("case-panel");
          if (anchor.scrollIntoView) anchor.scrollIntoView({ block: "start" });
        });
        li.appendChild(b);
        ul.appendChild(li);
      });
      sec.appendChild(ul);
      holder.appendChild(sec);
    });
  }

  function renderMap() {
    var holder = $("map-holder");
    if (holder.dataset.sig === view.map) return;
    holder.dataset.sig = view.map;
    holder.innerHTML = view.map;
  }
  function onMapActivate(e) {
    if (e.type === "keydown" && e.key !== "Enter" && e.key !== " ") return;
    var slot = e.target.closest ? e.target.closest(".rf-slot[data-id]") : null;
    if (!slot) return;
    e.preventDefault();
    send({ action: "pick", case: slot.getAttribute("data-id") });
    $("cases-panel").hidden = true;
    $("cases-toggle-button").setAttribute("aria-expanded", "false");
    var anchor = $("case-panel");
    if (anchor.scrollIntoView) anchor.scrollIntoView({ block: "start" });
  }
  function renderCodex() {
    var counts = view.totals;
    setText($("codex-summary"), counts.pages + " of " + counts.cases + " pages filled, " + counts.read + " read. A page fills when you name its case, in any order, and shows the shortest path: the fewest tests that would have proved the rule.");
    $("codex-toggle-button").textContent = "Codex (" + counts.pages + "/" + counts.cases + ")";
    var list = $("codex-list");
    var shown = view.page ? view.page.id : "";
    var sig = view.codex.map(function (e) { return (e.filled ? (e.read ? "r" : "f") : "e") + (e.id === shown ? "*" : ""); }).join("");
    if (list.dataset.sig !== sig) {
      list.dataset.sig = sig;
      list.textContent = "";
      var drawer = "";
      view.codex.forEach(function (e) {
        if (e.drawer !== drawer) { drawer = e.drawer; list.appendChild(el("h3", null, drawer)); }
        var b = el("button", e.filled ? "filled" : "empty");
        if (e.id === shown) b.className += " current";
        b.type = "button";
        b.dataset.testid = "rule-finder-page-" + e.id;
        b.textContent = e.number + ". " + (e.filled ? e.name + (e.read ? "" : " (new)") : "Empty page");
        b.setAttribute("aria-label", e.filled ? "Page " + e.number + ", " + e.name + (e.read ? "" : ", not read yet") : "Page " + e.number + " of " + e.drawer + ", empty until its case is named");
        if (e.filled) b.addEventListener("click", function () { send({ action: "page", case: e.id }); });
        else b.setAttribute("aria-disabled", "true");
        list.appendChild(b);
      });
    }
    var holder = $("codex-page");
    var p = view.page;
    var psig = p ? p.id + p.best : "";
    if (holder.dataset.sig === psig) return;
    holder.dataset.sig = psig;
    holder.textContent = "";
    if (!p) { holder.appendChild(el("p", "note", "Choose a filled page to read it. Every page you fill stays here.")); return; }
    holder.appendChild(el("h3", null, p.name));
    holder.appendChild(el("p", "note", p.drawer + " · case " + p.number));
    holder.appendChild(el("p", null, p.words));
    holder.appendChild(el("p", null, "Family: " + p.families.join(", ") + " (" + plural(p.clauses, "property", "properties") + ")."));
    holder.appendChild(el("p", "note", "Shortest path: " + plural(p.shortest.length, "test", "tests") + " would have proved it, next to the starting examples."));
    var path = el("ul", "path");
    p.shortest.forEach(function (t) {
      var li = el("li");
      li.innerHTML = itemSvg(p.kind, t.item, t.label + ", " + (t.yes ? "Through" : "Stopped"));
      li.appendChild(el("span", "ans " + (t.yes ? "yes" : "no"), verdictWord(t.yes)));
      path.appendChild(li);
    });
    holder.appendChild(path);
    var best = el("p", null, "Your best: " + plural(p.best, "test", "tests") + " (par " + p.par + ") ");
    best.appendChild(medalNode(p.medal));
    holder.appendChild(best);
    holder.appendChild(el("p", "line story-text", "Log: " + p.line));
  }

  function resetForCase() {
    caseId = view.case.id;
    if (view.menu) menu = view.menu;
    rows = [{ op: "and", neg: false, cid: "" }];
    work.num = "";
    work.shape = [];
    work.grid = work.grid.map(function () { return false; });
    $("num-input").value = "";
    $("rule-words").textContent = "";
    $("rule-check").textContent = "";
    renderRows();
    $("name-button").disabled = true;
    setText($("rule-lead"), "Pick the property the gate looks at. Tick Not to turn it around" + (view.case.max_clauses > 1 ? ", and add a clause to join two or three" : "") + ".");
  }
  function render(animate) {
    if (view.case.id !== caseId) resetForCase();
    renderCase();
    renderGate(animate);
    renderLog();
    renderBuilder();
    renderStats();
    renderDraft();
    renderVerdict();
    renderCases();
    renderMap();
    renderCodex();
  }

  // ---- talking to the engine --------------------------------------------------------------------------------
  function persist() {
    try {
      var proxy = engine.getState();
      var obj = proxy.toJs({ dict_converter: Object.fromEntries });
      if (proxy.destroy) proxy.destroy();
      lsSet(STORE_KEY, JSON.stringify(obj));
    } catch (e) { /* the save widget keeps the real copy */ }
  }
  function send(request, quiet) {
    if (!engine) return null;
    var result = JSON.parse(engine.handle(JSON.stringify(request)));
    if (result.error) { $("engine-status").textContent = "Something went wrong: " + result.error; return null; }
    var previous = view;
    view = result;
    if (!quiet) showToast("");
    if (!view.menu && previous && previous.case.id === view.case.id) view.menu = null;
    render(request.action === "test");
    if (request.action === "test" && view.last && !(previous && previous.last === view.last)) {
      announce((view.last.repeat ? "Already sent. " : "") + view.last.label + " goes " + verdictWord(view.last.yes) + ".");
    }
    if (request.action === "name") {
      var v = view.verdict;
      if (v && v.kind === "named") announce("Named. " + view.case.words);
      else if (v && v.kind === "near") announce("Not quite. The Sorter says " + v.conflict.sorter + " for " + v.conflict.label + ", your rule says " + v.conflict.rule + ".");
      else if (v && v.kind === "conflict") announce("Not yet. " + conflictText(v.conflict));
    }
    if (["test", "name", "restart", "pick", "next", "reset", "page"].indexOf(request.action) >= 0) persist();
    return result;
  }

  function askThen(id, message, confirmLabel, go) {
    if (window.ConfirmDialog) window.ConfirmDialog.ask({ id: id, message: message, confirmLabel: confirmLabel, allowSkip: false, onConfirm: go });
    else go();
  }

  function wire() {
    $("toast").addEventListener("click", function () { showToast(""); });
    wirePanelToggle("cases-toggle-button", "cases-panel");
    wirePanelToggle("codex-toggle-button", "codex-panel");
    $("map-holder").addEventListener("click", onMapActivate);
    $("map-holder").addEventListener("keydown", onMapActivate);
    $("page-button").addEventListener("click", function () {
      send({ action: "page", case: view.case.id });
      $("codex-panel").hidden = false;
      $("codex-toggle-button").setAttribute("aria-expanded", "true");
      if ($("codex-panel").scrollIntoView) $("codex-panel").scrollIntoView({ block: "start" });
    });
    wirePanelToggle("changelog-toggle-button", "changelog-panel");
    buildStaticBuilder();
    $("add-clause-button").addEventListener("click", function () {
      if (view && rows.length < view.case.max_clauses) { rows.push({ op: "and", neg: false, cid: "" }); renderRows(); onRulesChanged(); }
    });
    $("name-button").addEventListener("click", function () {
      var rule = ruleFromRows();
      if (rule) send({ action: "name", rule: rule });
    });
    $("next-button").addEventListener("click", function () { send({ action: "next" }); });
    $("restart-button").addEventListener("click", function () { send({ action: "restart" }); });
    $("reset-button").addEventListener("click", function () {
      askThen("rule-finder-reset", "Start the whole drawer wall over? Your named cases, test logs and tally will be erased.", "Erase it", function () { send({ action: "reset" }); });
    });
    // The save widget loads a save straight into the engine; this redraws afterwards.
    window.ruleFinderRefresh = function () { if (engine) { caseId = null; send({ action: "open" }); } };
  }

  async function boot() {
    var changelog = loadChangelog();
    var pyodide = await window.loadPyodide();
    for (var i = 0; i < ENGINE_MODULES.length; i++) {
      var source = await (await fetch(ENGINE_MODULES[i], { cache: "no-cache" })).text();
      pyodide.FS.writeFile(ENGINE_MODULES[i], source, { encoding: "utf8" });
    }
    await pyodide.runPythonAsync(await (await fetch("game.py", { cache: "no-cache" })).text());
    window.pyodide = pyodide;   // the shared save widget looks for it
    engine = { handle: pyodide.globals.get("handle"), getState: pyodide.globals.get("get_state"), loadState: pyodide.globals.get("load_state") };
    var saved = lsGet(STORE_KEY);
    if (saved && saved !== "{}") {
      lsSet(BACKUP_KEY, saved);      // kept until the next good save, so a load problem can never cost the player a game
      try { engine.loadState(pyodide.toPy(JSON.parse(saved))); } catch (e) { /* a bad save never blocks play */ }
    }
    $("engine-status").textContent = "";
    send({ action: "open" });
    await changelog;
  }

  wire();
  boot().catch(function (err) {
    $("engine-status").textContent = "The relay could not start (" + err + "). Reload to try again.";
  });
})();
