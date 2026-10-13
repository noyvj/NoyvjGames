/* Logic Gates view: glue only. The engine (game.py and its modules) holds every rule; this file draws what handle() returns and forwards
   what the player does. No arithmetic about circuits happens here. */
(function () {
  "use strict";
  var ENGINE_MODULES = ["chips.py", "net.py", "sim.py", "levels_a.py", "levels_b.py", "levels_c.py", "levels.py", "check.py", "words.py", "render.py",
    "state.py", "achievements.py", "info.py"];
  var STORE_KEY = "logic-gates:state";
  var DIFF_GAME = "logic-gates";
  var DIFF_TEXT = {
    easy: "The first hint press opens the nudge and the hint together, and the answer is one press away. One chip over the reference still earns par.",
    normal: "The game as designed: three hint steps, then the answer.",
    hard: "No answer step (nudge and hint only), fewer free undos, and par is kept on its own Hard record.",
  };

  var $ = function (id) { return document.getElementById(id); };
  var engine = null;
  var view = null;

  function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* convenience only */ } }
  function setText(node, text) { if (node.textContent !== text) node.textContent = text; }
  function announce(text) {
    var live = $("announce");
    live.textContent = "";
    setTimeout(function () { live.textContent = text; }, 40);
  }
  function el(tag, text, className) {
    var node = document.createElement(tag);
    if (text !== undefined && text !== null) node.textContent = text;
    if (className) node.className = className;
    return node;
  }
  function btn(text, id, onClick, extra) {
    var b = el("button", text);
    b.type = "button";
    if (id) b.id = id;
    if (extra) Object.keys(extra).forEach(function (k) { b.setAttribute(k, extra[k]); });
    b.addEventListener("click", onClick);
    return b;
  }

  // ---- toast ---------------------------------------------------------------------------------------
  var toastTimer = 0;
  function showToast(text) {
    var toast = $("toast");
    toast.textContent = text;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toast.textContent = ""; }, 8000);
  }

  // ---- panels --------------------------------------------------------------------------------------
  function setToggle(buttonId, panelId) { $(buttonId).setAttribute("aria-expanded", String(!$(panelId).hidden)); }
  function wirePanelToggle(buttonId, panelId) {
    $(buttonId).addEventListener("click", function () {
      $(panelId).hidden = !$(panelId).hidden;
      setToggle(buttonId, panelId);
    });
  }
  function closePanel(buttonId, panelId) { $(panelId).hidden = true; setToggle(buttonId, panelId); }

  // ---- stats, goals, level ---------------------------------------------------------------------------
  function renderStats() {
    var s = view.stats;
    setText($("stat-solved"), String(s.solved));
    setText($("stat-total"), String(s.total));
    setText($("stat-par"), String(s.par));
    setText($("stat-chips"), String(s.chips));
    setText($("stat-wires"), String(s.wires));
    setText($("stat-flips"), String(s.flips));
    var list = $("goals-list");
    list.textContent = "";
    view.goals.forEach(function (g) {
      var li = el("li");
      li.appendChild(el("span", g.label + ": " + g.description + " "));
      li.appendChild(el("b", "(" + g.have + "/" + g.need + ")"));
      list.appendChild(li);
    });
    $("goals").hidden = !view.goals.length;
  }

  function nextOpenLevel() {
    var found = null;
    view.picker.forEach(function (ch) {
      ch.levels.forEach(function (lv) { if (!found && lv.open && !lv.solved && lv.id !== view.level.id) found = lv; });
    });
    return found;
  }

  function renderLevel() {
    var lv = view.level;
    setText($("level-title"), lv.name);
    setText($("level-chapter"), lv.sandbox ? "Sandbox" : "Chapter " + lv.chapter + ": " + lv.chapter_name + " · level " + lv.index + " of " + view.stats.total);
    setText($("level-goal"), lv.goal);
    var rec = lv.record || {};
    var unlock = "";
    var easyNote = view.difficulty === "easy" && lv.par !== null ? " (on Easy, " + (lv.par + 1) + " still earns par)" : "";
    if (lv.unlock) unlock = rec.solved ? "You keep the " + lv.unlock + " chip from this level." : "Solving this level hands you the " + lv.unlock + " chip. " + (lv.par !== null ? "Par is " + lv.par + " chips" + easyNote + "." : "");
    else if (!lv.sandbox) unlock = "Par is " + lv.par + " chips" + easyNote + ".";
    setText($("level-unlock"), unlock + (lv.sandbox ? "" : " Board space: " + lv.cap + " chips."));
    setText($("level-intro"), lv.intro || "");
    $("level-intro").hidden = !lv.intro;
    setText($("level-log"), rec.solved && lv.log ? lv.log : "");
    $("level-log").hidden = !(rec.solved && lv.log);
    var banner = $("solved-banner");
    var ok = view.table && view.table.ok;
    banner.hidden = !ok;
    if (ok) {
      var text = "Solved with " + view.board.count + " chips" + (rec.par ? " (par)" : " (par is " + lv.par + ")") + ".";
      if (lv.unlock) text += " The " + lv.unlock + " chip is yours.";
      setText($("solved-text"), text);
      $("next-level-button").hidden = !nextOpenLevel();
    }
  }

  // ---- board --------------------------------------------------------------------------------------
  function renderBoard() {
    var holder = $("board-holder");
    if (holder.dataset.signature !== view.svg) {
      holder.innerHTML = view.svg;              // the engine's own markup: no player text goes in
      holder.dataset.signature = view.svg;
    }
    var status = "";
    if (view.armed) status = "Picked up " + view.armed.replace("in:", "switch ").replace("const:", "tie ") + ". Tap an input pin to connect it, or press Escape to let go.";
    else if (view.target) status = "Picked input " + view.target.replace("out:", "lamp ") + ". Tap a source pin to connect it, or press Escape to let go.";
    setText($("wiring-status"), status);
    var sw = $("switches");
    var sig = JSON.stringify(view.probe.inputs);
    sw.textContent = "";
    view.level.ins.forEach(function (name) {
      var on = view.probe.inputs[name] === 1;
      var b = btn(name + " = " + (on ? "1" : "0"), "switch-" + name, function () { send({ action: "flip", name: name }); }, { "aria-pressed": String(on), "aria-label": "Switch " + name + ", now " + (on ? "1" : "0") });
      sw.appendChild(b);
    });
    var seq = view.level.kind === "seq";
    $("script-box").hidden = !seq;
    if (seq) {
      var st = view.probe.step;
      setText($("script-status"), st === null ? "Flipping by hand (the circuit remembers between flips)." : "Showing step " + (st + 1) + " of " + view.level.steps + " of the script.");
    }
    var words = $("words-list");
    words.textContent = "";
    view.text.forEach(function (line) { words.appendChild(el("li", line)); });
    if (!view.text.length) words.appendChild(el("li", "The board is empty."));
    void sig;
  }

  // ---- parts ---------------------------------------------------------------------------------------
  function selectFor(id, label, current, options, onChange, floating) {
    var wrap = el("div", undefined, "pin-row" + (floating ? " floating" : ""));
    var lab = el("label", label);
    lab.setAttribute("for", id);
    var sel = el("select");
    sel.id = id;
    options.forEach(function (o) {
      var opt = el("option", o.label);
      opt.value = o.value;
      if (o.value === current) opt.selected = true;
      sel.appendChild(opt);
    });
    sel.addEventListener("change", function () { onChange(sel.value); });
    wrap.appendChild(lab);
    wrap.appendChild(sel);
    return wrap;
  }

  function renderParts() {
    var active = document.activeElement && document.activeElement.id;
    var pal = $("palette");
    pal.textContent = "";
    var built = el("details", undefined, "more-chips");
    var holder = el("div", undefined, "palette");
    var builtCount = 0;
    view.palette.forEach(function (p) {
      var b = btn("+ " + p.label, "add-" + p.type, function () { send({ action: "add", type: p.type }); }, { title: p.blurb, "aria-label": "Add a " + p.label + " chip" });
      if (p.built) { holder.appendChild(b); builtCount += 1; } else pal.appendChild(b);
    });
    if (builtCount) {
      built.id = "built-chips";
      built.open = lsGet("logic-gates:built-open") === "1";
      built.appendChild(el("summary", "Chips you built (" + builtCount + ")"));
      built.appendChild(holder);
      built.addEventListener("toggle", function () { lsSet("logic-gates:built-open", built.open ? "1" : "0"); });
      pal.appendChild(built);
    }
    if (!view.palette.length) pal.appendChild(el("span", "No chips yet: this board is only switches and lamps. Solve it to earn the first chip.", "note"));
    setText($("board-count"), "Chips on the board: " + view.board.count + " of " + view.board.cap + ". Wires: " + view.board.wires + ".");
    $("undo-button").setAttribute("aria-disabled", String(!view.can_undo));
    $("restore-button").setAttribute("aria-disabled", String(!view.can_restore));
    var cards = $("chip-cards");
    cards.textContent = "";
    view.board.chips.forEach(function (c) {
      var card = el("article", undefined, "card");
      var head = el("header");
      head.appendChild(el("h3", "Chip " + c.id + ": " + c.label));
      head.appendChild(btn("Remove", "remove-" + c.id, function () { send({ action: "remove", id: c.id }); }, { "aria-label": "Remove chip " + c.id + ", " + c.label }));
      card.appendChild(head);
      c.ins.forEach(function (p) {
        card.appendChild(selectFor("pin-" + p.dest, "Input " + p.pin, p.src, p.options, function (v) { send({ action: "wire", dest: p.dest, src: v }); }, !p.src));
      });
      card.appendChild(el("p", c.blurb + (c.outs.length > 1 ? " Outputs: " + c.outs.join(", ") + "." : ""), "blurb"));
      cards.appendChild(card);
    });
    var lamps = $("lamp-cards");
    lamps.textContent = "";
    view.board.lamps.forEach(function (l) {
      var card = el("article", undefined, "card");
      card.appendChild(el("h3", "Lamp " + l.name + " is " + (l.value ? "on (1)" : "off (0)")));
      card.appendChild(selectFor("pin-" + l.dest, "Source", l.src, l.options, function (v) { send({ action: "wire", dest: l.dest, src: v }); }, !l.src));
      lamps.appendChild(card);
    });
    if (active) {
      var again = $(active);
      if (again && document.activeElement !== again) again.focus();
    }
  }

  // ---- the table -----------------------------------------------------------------------------------
  function cell(tag, text, className) { return el(tag, text, className); }

  function renderTable() {
    var holder = $("table-holder");
    holder.textContent = "";
    var t = view.table;
    if (!t) {
      setText($("result-summary"), "The sandbox has no target. Flip the switches and watch the lamps; new truth tables are logged under Sandbox.");
      return;
    }
    var summary;
    if (t.ok) summary = t.kind === "comb" ? "Every row matches (" + t.total + " of " + t.total + ")." : "Every checked step matches (" + t.total + " of " + t.total + ").";
    else summary = (t.kind === "comb" ? "Rows right: " : "Steps right: ") + t.right + " of " + t.total + ". " + t.message;
    setText($("result-summary"), summary);
    var table = el("table", undefined, "truth");
    var cap = el("caption", t.kind === "comb" ? (t.total > 32 ? "The first rows that are wrong (" + t.total + " rows in all)" : "Every row of the truth table") : "The script, step by step");
    cap.className = "sr-only";
    table.appendChild(cap);
    var head = el("tr");
    if (t.kind === "seq") head.appendChild(cell("th", "Step"));
    t.ins.forEach(function (n) { head.appendChild(cell("th", n)); });
    t.outs.forEach(function (n) { head.appendChild(cell("th", "Wanted " + n)); });
    t.outs.forEach(function (n) { head.appendChild(cell("th", "Lamp " + n)); });
    head.appendChild(cell("th", "Result"));
    table.appendChild(head);
    t.rows.forEach(function (r) {
      var tr = el("tr", undefined, r.ok === null ? "note-row" : (r.ok ? "right" : "wrong"));
      if (t.kind === "seq") {
        var c0 = el("td");
        var sb = btn(String(r.step), null, function () { send({ action: "script", step: r.step - 1 }); }, { "aria-label": "Show step " + r.step + " on the board" });
        sb.className = "step-button";
        c0.appendChild(sb);
        tr.appendChild(c0);
        if (view.probe.step === r.step - 1) tr.className += " current";
      }
      r.inputs.forEach(function (v) { tr.appendChild(cell("td", String(v))); });
      t.outs.forEach(function (n, i) { tr.appendChild(cell("td", r.want && r.want[i] !== null && r.want[i] !== undefined ? String(r.want[i]) : "-")); });
      t.outs.forEach(function (n, i) {
        var differs = r.want && r.want[i] !== null && r.want[i] !== undefined && r.want[i] !== r.got[i];
        tr.appendChild(cell("td", String(r.got[i]), differs ? "want-differs" : ""));
      });
      tr.appendChild(cell("td", "", "verdict"));
      table.appendChild(tr);
    });
    holder.appendChild(table);
    if (window.NoyvjResultSheet) window.NoyvjResultSheet.render(view.table);
  }

  // ---- hints ---------------------------------------------------------------------------------------
  function renderHints() {
    var h = view.hints;
    $("hints-panel").hidden = !h;
    if (!h) return;
    var labels = ["Would you like a suggestion?", "Another hint", "Another hint: the answer", "That is every hint"];
    var b = $("hint-button");
    var last = h.rung >= h.max;
    setText(b, labels[last ? 3 : h.rung]);
    b.setAttribute("aria-disabled", String(last));
    $("answer-button").hidden = !h.answer_ready;
    setText($("answer-button"), view.difficulty === "easy" ? "Put the answer on the board (this level then will not count for par)" : "Put the answer on the board");
    setText($("hint-rung"), h.rung === 0 ? "No hints used on this level." : "Hints shown: " + h.rung + " of " + h.max + "." + (h.max < 3 ? " Hard has no answer step." : "") + (h.answer_used ? " The answer was put on the board, so this level does not count for par." : ""));
    var list = $("hint-list");
    list.textContent = "";
    if (h.nudge) list.appendChild(el("li", "Nudge: " + h.nudge));
    if (h.hint) list.appendChild(el("li", "Hint: " + h.hint));
    if (h.answer) {
      var li = el("li", "Answer, in words:");
      var ul = el("ul");
      h.answer.forEach(function (line) { ul.appendChild(el("li", line)); });
      li.appendChild(ul);
      list.appendChild(li);
    }
  }

  // ---- picker, shelf, sandbox, achievements, log ------------------------------------------------------
  function renderPicker() {
    var body = $("picker-body");
    var sig = JSON.stringify(view.picker);
    if (body.dataset.signature === sig) return;
    body.dataset.signature = sig;
    body.textContent = "";
    view.picker.forEach(function (ch) {
      var wrap = el("section", undefined, "picker-chapter");
      wrap.appendChild(el("h3", "Chapter " + ch.id + ": " + ch.name + " (" + ch.cleared + " of " + ch.total + " solved)"));
      wrap.appendChild(el("p", ch.intro, "note"));
      var list = el("ul", undefined, "picker-list");
      ch.levels.forEach(function (lv) {
        var li = el("li");
        var mark = lv.solved ? (lv.par ? "✓ PAR" : "✓") : (lv.open ? "open" : "needs " + lv.missing.join(", "));
        var b = el("button", undefined, lv.open ? "" : "locked");
        b.type = "button";
        b.appendChild(el("span", lv.index + ". " + lv.name));
        b.appendChild(el("span", mark, "mark"));
        b.setAttribute("aria-label", "Level " + lv.index + ", " + lv.name + ", " + (lv.solved ? (lv.par ? "solved at par" : "solved") : (lv.open ? "open" : "locked, needs " + lv.missing.join(", "))) + (lv.current ? ", open now" : ""));
        if (lv.current) b.setAttribute("aria-current", "true");
        b.addEventListener("click", function () { openLevel(lv.id); });
        li.appendChild(b);
        list.appendChild(li);
      });
      wrap.appendChild(list);
      body.appendChild(wrap);
    });
  }

  function openLevel(id) {
    send({ action: "start", level: id });
    if (!view.note || view.level.id === id) closePanel("picker-toggle-button", "picker-panel");
  }

  function renderShelf() {
    var list = $("shelf-list");
    list.textContent = "";
    view.shelf.forEach(function (c) {
      var li = el("li", undefined, c.unlocked ? "" : "locked");
      li.appendChild(el("strong", c.label + (c.unlocked ? "" : " (locked)")));
      li.appendChild(el("span", c.ins.join(", ") + " → " + c.outs.join(", ")));
      li.appendChild(el("span", c.blurb));
      list.appendChild(li);
    });
  }

  function renderSandbox() {
    var s = view.sandbox;
    setText($("sandbox-progress"), "Truth tables found: " + s.found + " of " + s.total + ". The Sixteen: " + view.stats.sixteen + " of 16.");
    var list = $("sixteen-list");
    list.textContent = "";
    s.sixteen.forEach(function (f) { list.appendChild(el("li", f.name, f.found ? "found" : "")); });
  }

  var knownEarned = null;
  function renderAchievements() {
    var list = $("achievements-list");
    list.textContent = "";
    var earnedNow = [];
    view.achievements.forEach(function (a) {
      var li = el("li", undefined, a.earned ? "earned" : "");
      li.setAttribute("data-achievement-id", a.id);
      li.appendChild(el("span", a.earned ? "Earned" : "Not yet", "tick"));
      var name = el("strong", " " + a.label + " ");
      name.setAttribute("data-achievement-label", "");
      li.appendChild(name);
      li.appendChild(el("span", a.description + " (" + a.have + "/" + a.need + ")"));
      list.appendChild(li);
      if (a.earned) earnedNow.push(a.id);
    });
    $("achievements-toggle-button").textContent = "Achievements (" + earnedNow.length + "/" + view.achievements.length + ")";
    if (knownEarned !== null) {
      earnedNow.filter(function (id) { return knownEarned.indexOf(id) === -1; }).forEach(function (id) {
        var a = view.achievements.filter(function (x) { return x.id === id; })[0];
        showToast("Achievement unlocked: " + a.label + ".");
      });
    }
    knownEarned = earnedNow;
  }

  function renderLog() {
    var holder = $("log-entries");
    holder.textContent = "";
    view.story.forEach(function (e) {
      var wrap = el("article", undefined, "log-entry");
      wrap.appendChild(el("h3", e.name));
      wrap.appendChild(el("p", e.text, "story-text"));
      holder.appendChild(wrap);
    });
    if (!view.story.length) holder.appendChild(el("p", "Nothing logged yet. Solve a board.", "note"));
  }

  // ---- about, what's new ---------------------------------------------------------------------------
  function renderInfo() {
    var info = view.info;
    if (!info || $("info-page-sources").dataset.drawn) return;
    $("info-page-sources").dataset.drawn = "1";
    $("info-page-framing").textContent = info.framing;
    var list = $("info-page-sources");
    list.textContent = "";
    info.facts.forEach(function (fact) {
      var item = el("li", undefined, "info-page-source");
      item.appendChild(el("strong", fact.heading));
      item.appendChild(el("p", fact.fact, "info-page-framing"));
      item.appendChild(el("p", fact.tie_in, "info-page-tie-in"));
      var link = el("a", fact.source.title);
      link.href = fact.source.url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      var src = el("p", undefined, "info-page-source-note");
      src.appendChild(document.createTextNode("Source: "));
      src.appendChild(link);
      src.appendChild(document.createTextNode(", " + fact.source.publisher + ". Read on " + fact.source.date_read + "."));
      item.appendChild(src);
      list.appendChild(item);
    });
  }

  function renderChangelog(entries) {
    var holder = $("changelog-entries");
    holder.textContent = "";
    entries.forEach(function (entry) {
      var row = el("article", undefined, "changelog-entry");
      row.appendChild(el("div", entry.date, "changelog-date"));
      row.appendChild(el("p", entry.entry, "changelog-text"));
      holder.appendChild(row);
    });
    $("changelog-toggle-button").textContent = "What's New (" + entries.length + ")";
  }
  function loadChangelog() {
    return fetch("changelog.json").then(function (r) { return r.text(); }).then(function (text) {
      window.CHANGELOG_JSON = text;
      var data = JSON.parse(text);
      var list = Array.isArray(data) ? data : (data && data.changelog) || [];
      renderChangelog(list.slice().sort(function (a, b) { return a.date < b.date ? 1 : -1; }));
    }).catch(function () { renderChangelog([]); });
  }

  var TUTORIAL_STEPS = [
    { title: "Welcome to Meridian Relay", text: "Each board has switches on the left, lamps on the right, and a table the lamps must match. You wire chips between them. Nothing is timed. Skip any time and reopen this from the Tutorial button." },
    { selector: "#level-goal", title: "The goal", text: "This sentence says what the lamps must do. The table further down checks every case at once and tells you the first one that is wrong." },
    { selector: "#board-panel", title: "The board", text: "Solid thick wires carry 1, thin dashed wires carry 0. Tap a round pin on a source, then a round pin on an input, to connect them. Flip the switches to see what your circuit does." },
    { selector: "#board-panel", title: "Tie 1 and tie 0", text: "The two small boxes marked tie 1 and tie 0 are fixed inputs: a wire tied to 1 or to 0 for good. Use one when a chip needs a constant, for example tie one input of a NAND chip to 1 and it becomes an inverter. Hover a tie box for the same note." },
    { selector: "#parts-panel", title: "Parts", text: "Add chips here. Every connection can also be chosen from a list on each chip, which works from the keyboard. Undo, Clear and Restore mean nothing is ever lost." },
    { selector: "#check-panel", title: "Does it match?", text: "Every row must say Right. When they all do, the level is solved and the circuit becomes a chip you keep." },
    { selector: "#hints-panel", title: "Stuck?", text: "A nudge, then a hint, then the answer in words with a button that puts it on the board. Asking takes nothing away." },
    { selector: "#picker-toggle-button", title: "Levels", text: "Forty boards in five chapters. A level opens when you own the chips its answer needs, so you can often pick your own order." },
    { selector: "#sandbox-toggle-button", title: "Sandbox", text: "A free board. Every new truth table you make is logged, and the sixteen ways two switches can decide a lamp are a collection to fill." },
    { title: "You are ready", text: "Take your time. The station has waited eleven years." },
  ];

  // ---- mobile chapter cards ----------------------------------------------------------------------
  var _mobileChaptersInitialized = false;
  function renderMobileChapters() {
    var container = $("mobile-chapter-cards");
    if (!container || !view.picker) return;
    
    var reducedMotion = false;
    try { reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch(e) {}
    
    container.textContent = "";
    var totalChips = (view.board && view.board.count) || 0;
    view.picker.forEach(function(ch) {
      var card = el("div", undefined, "chapter-card");
      card.appendChild(el("h3", ch.name));
      
      var solvedCount = 0;
      ch.levels.forEach(function(lv) { if (lv.solved) solvedCount++; });
      var totalLevels = ch.total || ch.levels.length;
      var progress = totalLevels > 0 ? solvedCount / totalLevels : 0;
      var circumference = 2 * Math.PI * 24;
      var offset = reducedMotion ? 0 : circumference * (1 - progress);
      
      var ringWrap = el("div", undefined, "chapter-progress-ring");
      var svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      svg.setAttribute("viewBox", "0 0 60 60");
      var bg = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      bg.setAttribute("cx", "30"); bg.setAttribute("cy", "30"); bg.setAttribute("r", "24"); bg.className = "bg";
      var fg = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      fg.setAttribute("cx", "30"); fg.setAttribute("cy", "30"); fg.setAttribute("r", "24"); fg.className = "fg"; 
      fg.setAttribute("stroke-dasharray", circumference); 
      fg.setAttribute("stroke-dashoffset", offset);
      svg.appendChild(bg);
      svg.appendChild(fg);
      ringWrap.appendChild(svg);
      card.appendChild(ringWrap);
      
      var chipText = el("span", "Chips: " + totalChips, "chapter-chip-count");
      card.appendChild(chipText);
      
      var list = el("div", undefined, "chapter-levels-list");
      ch.levels.forEach(function(lv) {
        var btn = el("button", lv.index + ".", "chapter-level-btn" + (lv.solved ? " solved" : "") + (!lv.open ? " locked" : ""));
        btn.type = "button";
        btn.setAttribute("aria-label", "Level " + lv.index + ": " + lv.name + (lv.solved ? ", solved" : (lv.open ? ", open" : ", locked")));
        if (lv.open) {
          btn.addEventListener("click", function() { openLevel(lv.id); });
        }
        list.appendChild(btn);
      });
      card.appendChild(list);
      container.appendChild(card);
    });

    // Swipe handling (only once, and only if reduced motion is off)
    if (!_mobileChaptersInitialized && !reducedMotion) {
      var startX = 0;
      function onPointerDown(e) { startX = e.clientX; }
      function onPointerUp(e) {
        var dx = e.clientX - startX;
        if (Math.abs(dx) > 50) {
          container.scrollLeft += dx > 0 ? -container.clientWidth : container.clientWidth;
        }
      }
      container.addEventListener("pointerdown", onPointerDown);
      container.addEventListener("pointerup", onPointerUp);
      _mobileChaptersInitialized = true;
    }
  }

  // ---- render / talk to the engine -----------------------------------------------------------------
  function render() {
    renderStats();
    renderLevel();
    renderBoard();
    renderParts();
    renderTable();
    renderHints();
    renderPicker();
    renderShelf();
    renderSandbox();
    renderAchievements();
    renderLog();
    renderInfo();
    if (view.note) { showToast(view.note); announce(view.note); }
  }

  // ---- sound (shared/sfx.js: generated in code, off unless the player turns it on, never the only signal) ----
  // Soft gate clicks as wires are made and broken, a gentle confirm when the circuit first matches and a bell for a new chip.
  function soundFor(request, previous) {
    if (!window.NoyvjSfx || !previous || !view || previous.level.id !== view.level.id) return;
    var sfx = window.NoyvjSfx;
    var passedNow = Boolean(view.table && view.table.ok) && !(previous.table && previous.table.ok);
    if (passedNow) {
      sfx.play("confirm");
      var was = previous.level.record || {};
      var now = view.level.record || {};
      if (view.level.unlock && now.solved && !was.solved) sfx.play("bell", { delay: 0.3 });
      return;
    }
    if (view.board.wires > previous.board.wires) sfx.play("click_high");
    else if (view.board.wires < previous.board.wires) sfx.play("click_low");
  }

  function persist() {
    try {
      var proxy = engine.getState();
      var obj = proxy.toJs({ dict_converter: Object.fromEntries });
      if (proxy.destroy) proxy.destroy();
      lsSet(STORE_KEY, JSON.stringify(obj));
    } catch (e) { /* the save widget is the real save */ }
  }
  function send(request) {
    var result = JSON.parse(engine.handle(JSON.stringify(request)));
    if (result.error) { $("engine-status").textContent = "Something went wrong: " + result.error; return null; }
    $("engine-status").textContent = "";
    var previous = view;
    view = result;
    render();
    soundFor(request, previous);
    persist();
    return result;
  }
  function guard(id, handler) {
    $(id).addEventListener("click", function () {
      if ($(id).getAttribute("aria-disabled") === "true") return;
      if (!view) return;
      handler();
    });
  }

  // ---- difficulty (AN-17, shared/difficulty.js): the page keeps the choice, the engine applies it and is never told to save it ----
  function sendDifficulty() {
    if (!engine) return null;
    if (!window.NoyvjDifficulty) return send({ action: "open" });
    return send({ action: "difficulty", level: window.NoyvjDifficulty.get(DIFF_GAME) });
  }
  function wireDifficulty() {
    if (!window.NoyvjDifficulty) return;
    window.NoyvjDifficulty.mount("#difficulty-slot", { game: DIFF_GAME, collapsible: true, descriptions: DIFF_TEXT });
    window.NoyvjDifficulty.onChange(function (d) { if (d.game === DIFF_GAME) sendDifficulty(); });
  }

  // ---- mobile pin magnet ---------------------------------------------------------------------------------------
  var _magnetPin = null;
  function onPointerMove(e) {
    if (!view || (!view.armed && !view.target)) {
      if (_magnetPin) { _magnetPin.classList.remove("lg-pin--magnet-active"); _magnetPin = null; }
      $("board-holder").style.cursor = "";
      return;
    }
    var holder = $("board-holder");
    var rect = holder.getBoundingClientRect();
    var mx = e.clientX - rect.left;
    var my = e.clientY - rect.top;
    var pins = holder.querySelectorAll(".lg-pin");
    var nearest = null;
    var minDist = 60;
    for (var i = 0; i < pins.length; i++) {
      var pRect = pins[i].getBoundingClientRect();
      var cx = pRect.left + pRect.width / 2 - rect.left;
      var cy = pRect.top + pRect.height / 2 - rect.top;
      var dx = mx - cx, dy = my - cy;
      var dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < minDist) {
        minDist = dist;
        nearest = pins[i];
      }
    }
    if (_magnetPin !== nearest) {
      if (_magnetPin) _magnetPin.classList.remove("lg-pin--magnet-active");
      if (nearest) nearest.classList.add("lg-pin--magnet-active");
      _magnetPin = nearest;
      holder.style.cursor = nearest ? "pointer" : "";
    }
  }

  // ---- mobile fit/centre and snap -----------------------------------------------------------
  var SNAP_KEY = "logic-gates-snap";
  var SNAP_STEP = 20;

  function getSnap() {
    try { return localStorage.getItem(SNAP_KEY) === "true"; } catch(e) { return false; }
  }
  function toggleSnap() {
    var on = !getSnap();
    try { localStorage.setItem(SNAP_KEY, String(on)); } catch(e) {}
    var btn = $("lg-snap-btn");
    if (btn) btn.setAttribute("aria-pressed", on ? "true" : "false");
    applySnap(on);
  }
  function applySnap(on) {
    var holder = $("board-holder");
    if (!holder) return;
    if (on) holder.classList.add("lg-snap-grid");
    else holder.classList.remove("lg-snap-grid");
  }

  function doFitAndCentre() {
    var reducedMotion = false;
    try { reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch(e) {}
    var holder = $("board-holder");
    if (!holder || !holder.firstElementChild) return;
    var svg = holder.firstElementChild;
    var bbox = svg.getBBox();
    var pad = 20;
    var availW = window.innerWidth - pad * 2;
    var availH = window.innerHeight - pad * 2;
    if (availW <= 0 || availH <= 0) return;
    var scale = Math.min(availW / bbox.width, availH / bbox.height);
    scale = Math.max(0.5, Math.min(scale, 3));
    var tx = (availW - bbox.width * scale) / 2 - bbox.x * scale;
    var ty = (availH - bbox.height * scale) / 2 - bbox.y * scale;
    svg.style.transformOrigin = "0 0";
    svg.style.transition = reducedMotion ? "none" : "transform 0.2s ease-out";
    svg.style.transform = "translate(" + tx + "px, " + ty + "px) scale(" + scale + ")";
  }

  function initMobileTools() {
    var panel = $("board-panel");
    if (!panel) return;
    var tools = document.createElement("div");
    tools.id = "lg-mobile-tools";
    tools.className = "lg-mobile-tools";
    
    var fitBtn = btn("Fit", "lg-fit-btn", function () { doFitAndCentre(); });
    fitBtn.type = "button";
    fitBtn.className = "lg-fit-btn";
    tools.appendChild(fitBtn);
    
    var snapBtn = btn("Snap", "lg-snap-btn", function () { toggleSnap(); });
    snapBtn.type = "button";
    snapBtn.className = "lg-snap-btn";
    snapBtn.setAttribute("aria-pressed", getSnap() ? "true" : "false");
    tools.appendChild(snapBtn);
    
    panel.insertBefore(tools, panel.firstChild);
    if (getSnap()) applySnap(true);
  }

  function wire() {
    wireDifficulty();
    window.logicGatesRefresh = function () { if (engine) send({ action: "open" }); };
    $("board-holder").addEventListener("pointermove", onPointerMove);
    $("board-holder").addEventListener("pointerleave", function () {
      if (_magnetPin) { _magnetPin.classList.remove("lg-pin--magnet-active"); _magnetPin = null; }
      $("board-holder").style.cursor = "";
    });
    $("board-holder").addEventListener("click", function (e) {
      if (!view) return;
      var pin = e.target.closest && e.target.closest("[data-pin]");
      if (pin) { send({ action: "pick", pin: pin.getAttribute("data-pin") }); return; }
      var sw = e.target.closest && e.target.closest("[data-flip]");
      if (sw) send({ action: "flip", name: sw.getAttribute("data-flip") });
    });
    $("board-holder").addEventListener("lg-place-chip", function (e) {
      send({ action: "add", type: e.detail.type });
    });
    guard("undo-button", function () { send({ action: "undo" }); });
    guard("restore-button", function () { send({ action: "restore" }); });
    guard("clear-button", function () {
      var go = function () { send({ action: "clear" }); };
      if (view.board.count || view.board.wires) {
        if (window.ConfirmDialog) window.ConfirmDialog.ask({ id: "logic-gates-clear", message: "Clear the board? You can bring it back with Restore.", confirmLabel: "Clear", onConfirm: go });
        else go();
      }
    });
    guard("hint-button", function () { send({ action: "hint" }); });
    guard("answer-button", function () {
      var go = function () { send({ action: "answer" }); };
      if (view.difficulty === "easy") go();      // Easy: no extra question (the button already says what it costs)
      else if (window.ConfirmDialog) window.ConfirmDialog.ask({ id: "logic-gates-answer", message: "Put the answer on the board? It replaces what is there (Undo brings yours back) and this level will not count for par.", confirmLabel: "Put it on the board", onConfirm: go });
      else go();
    });
    guard("next-level-button", function () { send({ action: "next" }); });
    guard("script-prev-button", function () { var s = view.probe.step === null ? 1 : view.probe.step; send({ action: "script", step: Math.max(0, s - 1) }); });
    guard("script-next-button", function () { var s = view.probe.step === null ? -1 : view.probe.step; send({ action: "script", step: Math.min(view.level.steps - 1, s + 1) }); });
    guard("script-manual-button", function () { send({ action: "manual" }); });
    guard("sandbox-open-button", function () { send({ action: "start", level: "sandbox" }); closePanel("sandbox-toggle-button", "sandbox-panel"); });
    wirePanelToggle("picker-toggle-button", "picker-panel");
    wirePanelToggle("shelf-toggle-button", "shelf-panel");
    wirePanelToggle("sandbox-toggle-button", "sandbox-panel");
    wirePanelToggle("log-toggle-button", "log-panel");
    wirePanelToggle("info-page-toggle-button", "info-page-panel");
    wirePanelToggle("changelog-toggle-button", "changelog-panel");
    wirePanelToggle("achievements-toggle-button", "achievements-panel");
    var drawer = $("chip-drawer");
    if (drawer) {
      drawer.addEventListener("chip-drawer:place", function (e) {
        send({ action: "add", type: e.detail.type });
      });
    }
    // ---- mobile landscape layout (R4-LGMO-7) ---------------------------------------------------
    function updateLandscapeLayout() {
      if (!window.matchMedia || !window.matchMedia("(orientation: landscape)").matches) return;
      if (window.innerWidth < 600) $("game").setAttribute("data-lg-landscape", "true");
      else $("game").removeAttribute("data-lg-landscape");
    }
    updateLandscapeLayout();
    window.addEventListener("resize", updateLandscapeLayout);
    window.addEventListener("orientationchange", updateLandscapeLayout);

    // R4-LGMO-9: two-finger tap undo (mobile)
    var _twoFingerDown = false;
    function onTouchStart(e) { if (e.touches.length === 2) _twoFingerDown = true; }
    function onTouchEnd(e) { if (_twoFingerDown && e.changedTouches.length === 2) { send({ action: "undo" }); _twoFingerDown = false; } }
    document.addEventListener("touchstart", onTouchStart, { passive: true });
    document.addEventListener("touchend", onTouchEnd, { passive: true });
    
    var reducedMotion = false;
    try { reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch(e) {}
    if (window.innerWidth <= 600 && !reducedMotion) {
      var hint = el("p", "Two-finger tap to undo", "lg-gesture-hint");
      $("board-holder").appendChild(hint);
    }

    initMobileTools();
    document.addEventListener("keydown", onKey);
  }

  function onKey(e) {
    if (e.altKey || e.ctrlKey || e.metaKey || !view) return;
    var tag = e.target && e.target.tagName;
    if (/^(INPUT|TEXTAREA|SELECT|BUTTON|SUMMARY)$/.test(tag)) return;
    var key = e.key.toLowerCase();
    if (key === "u") { e.preventDefault(); if (view.can_undo) send({ action: "undo" }); }
    else if (key === "n") { e.preventDefault(); if (nextOpenLevel()) send({ action: "next" }); }
    else if (key === "escape" && (view.armed || view.target)) { e.preventDefault(); send({ action: "cancel" }); }
  }

  function setBusy(busy) {
    ["undo-button", "restore-button", "clear-button", "hint-button", "answer-button", "next-level-button", "sandbox-open-button"].forEach(function (id) { $(id).disabled = busy; });
  }

  async function boot() {
    setBusy(true);
    var changelog = loadChangelog();
    var pyodide = await window.loadPyodide();
    for (var i = 0; i < ENGINE_MODULES.length; i++) {
      var response = await fetch(ENGINE_MODULES[i]);
      if (!response.ok) continue;        // a module not written yet is skipped; the engine imports what it needs
      pyodide.FS.writeFile(ENGINE_MODULES[i], await response.text(), { encoding: "utf8" });
    }
    await pyodide.runPythonAsync(await (await fetch("game.py")).text());
    window.pyodide = pyodide;   // the shared save widget looks for it
    engine = { handle: pyodide.globals.get("handle"), getState: pyodide.globals.get("get_state"), loadState: pyodide.globals.get("load_state") };
    var saved = lsGet(STORE_KEY);
    if (saved) {
      try { engine.loadState(pyodide.toPy(JSON.parse(saved))); } catch (e) { /* a bad save never blocks play */ }
    }
    $("engine-status").textContent = "";
    setBusy(false);
    sendDifficulty();
    await changelog;
    if (window.GameTutorial) window.GameTutorial.init(window.logicGatesTutorialSteps ? window.logicGatesTutorialSteps(TUTORIAL_STEPS) : TUTORIAL_STEPS, { gameId: "logic-gates" });
  }

  wire();
  boot().catch(function (err) {
    $("engine-status").textContent = "The workshop could not start (" + err + "). Reload to try again.";
  });
})();
