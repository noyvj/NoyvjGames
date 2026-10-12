/* Teach the Machine view: glue only. The engine (game.py and its modules) holds every rule; this file draws what handle() returns as text,
   switches and lists, and turns clicks and keys into requests. It never grows a tree, decides an answer is right or says which kind of
   mistake a wrong answer was: it asks the engine, and draws the reply. */
(function () {
  "use strict";
  var ENGINE_MODULES = ["learner.py", "lessonkit.py", "lessons_s1.py", "lessons_s2.py", "lessons_s3.py", "lessons.py", "why.py", "info.py"];
  var STORE_KEY = "teach-the-machine:state";
  var BACKUP_KEY = "teach-the-machine:state-backup";
  var BEFORE_NEW_KEY = "teach-the-machine:state-before-new-game";

  var $ = function (id) { return document.getElementById(id); };
  var engine = null;
  var view = null;
  var featureSig = "", trainSig = "", shelfSig = "", notebookSig = "", gallerySig = "", resultSig = "";
  var infoLiveDone = false;
  var lastWhyButton = null;
  var knownCleared = null;

  function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* convenience only */ } }
  function setText(node, text) { if (node.textContent !== text) node.textContent = text; }
  function announce(text) {
    if (!text) return;
    if (window.NoyvjAnnounce) { window.NoyvjAnnounce.say(text); return; }
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

  // ---- panels --------------------------------------------------------------------------------------
  function setPanel(panelId, buttonId, open) {
    $(panelId).hidden = !open;
    $(buttonId).setAttribute("aria-expanded", String(open));
  }
  function wirePanelToggle(buttonId, panelId) {
    $(buttonId).addEventListener("click", function () { setPanel(panelId, buttonId, $(panelId).hidden); });
  }

  // ---- the stats -------------------------------------------------------------------------------------
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
    var t = view.totals;
    bumpStat("stat-cleared", t.cleared + "/" + t.lessons);
    bumpStat("stat-shelves", t.shelves_open + "/" + t.shelves);
    bumpStat("stat-whys", t.whys);
    bumpStat("stat-notebook", t.notebook + "/" + t.notebook_total);
    bumpStat("stat-trains", t.trains);
  }

  // ---- cases and chips --------------------------------------------------------------------------------
  function kindOf(fid) {
    var f = view.lesson.features.filter(function (x) { return x.id === fid; })[0];
    return f ? f.kind : "number";
  }
  function chipRow(chips) {
    var row = el("div", "chips");
    chips.forEach(function (c) {
      var chip = el("span", "chip k-" + kindOf(c.feature) + (c.on ? "" : " off"), c.text);
      row.appendChild(chip);
    });
    return row;
  }

  // ---- the workshop ------------------------------------------------------------------------------------
  function renderHead() {
    var l = view.lesson;
    setText($("lesson-kicker"), l.shelf + " - lesson " + l.number + " of " + l.of + (l.cleared ? " - cleared" : ""));
    setText($("lesson-heading"), l.title);
    setText($("lesson-task"), l.task + " Pip must get " + l.need + " of the " + l.unseen + " unseen " + l.noun.toLowerCase() + "s right (" + l.target + " percent).");
    setText($("lamp-words"), l.lamp.words);
    $("pip").setAttribute("data-state", l.lamp.state);
    $("test-button").disabled = !l.trained;
    $("train-button").textContent = l.trained ? "Train again" : "Train";
    $("reset-switches-button").disabled = l.at_start;
    $("prev-lesson-button").disabled = !prevLesson();
    var card = $("done-card");
    var cleared = view.just && view.just.id === l.id;
    card.hidden = !(l.cleared && l.result && l.result.passed) && !cleared;
    if (!card.hidden) {
      setText($("done-title"), l.title + (l.best_mark ? " - cleared with the best features" : " - cleared"));
      setText($("done-text"), l.learned + " Pip looked at: " + l.cleared_with.join(", ") + "." +
        (l.best_mark ? "" : " Clear it again with exactly the right features to earn the best mark."));
      if (cleared && view.just.first) {
        card.classList.remove("fresh");
        void card.offsetWidth;
        card.classList.add("fresh");
      }
    }
  }

  function renderFeatures() {
    var l = view.lesson;
    var sig = l.id + "|" + l.features.length;
    var list = $("feature-list");
    if (sig !== featureSig) {
      featureSig = sig;
      list.textContent = "";
      l.features.forEach(function (f) {
        var li = el("li");
        var btn = el("button", "switch");
        btn.type = "button";
        btn.setAttribute("role", "switch");
        btn.dataset.feature = f.id;
        btn.setAttribute("aria-keyshortcuts", String(f.key));
        btn.setAttribute("data-testid", "ttm-switch-" + f.id);
        btn.appendChild(el("span", "sw-key", String(f.key)));
        btn.appendChild(el("span", "sw-name", f.label));
        btn.appendChild(el("span", "sw-state", ""));
        btn.appendChild(el("span", "sw-about", f.about + " (" + f.range + ")"));
        btn.addEventListener("click", function () { send({ action: "toggle", feature: f.id }); });
        li.appendChild(btn);
        list.appendChild(li);
      });
    }
    l.features.forEach(function (f, i) {
      var btn = list.children[i].firstChild;
      btn.setAttribute("aria-checked", String(f.on));
      setText(btn.querySelector(".sw-state"), f.on ? "ON" : "OFF");
      btn.setAttribute("aria-label", f.label + ", " + (f.on ? "on" : "off") + ". " + f.about + ". Key " + f.key + ".");
    });
  }

  function renderTrainList() {
    var l = view.lesson;
    var sig = l.id + "|" + l.features.map(function (f) { return f.on ? 1 : 0; }).join("");
    setText($("train-summary"), "Pip's training " + l.noun.toLowerCase() + "s (" + l.train.length + ")");
    if (sig === trainSig) return;
    trainSig = sig;
    var list = $("train-list");
    list.textContent = "";
    l.train.forEach(function (c) {
      var li = el("li", "case");
      var head = el("div", "case-head");
      head.appendChild(el("span", "case-name", c.name));
      head.appendChild(el("span", "case-answer", "Answer: " + c.answer));
      li.appendChild(head);
      li.appendChild(chipRow(c.chips));
      list.appendChild(li);
    });
  }

  function renderTree() {
    var l = view.lesson;
    var box = $("tree-box");
    box.hidden = !l.tree;
    if (!l.tree) return;
    setText($("tree-score"), "Pip got " + l.train_score.right + " of the " + l.train_score.total + " training " + l.noun.toLowerCase() + "s right. It looked at: " + l.looking_at.join(", ") + ".");
    var list = $("tree-list");
    list.textContent = "";
    l.tree.forEach(function (line) {
      var li = el("li", /^(first |yes, then |no, then )/.test(line.text) ? "ask" : "end", line.text);
      li.style.setProperty("--d", String(line.d));
      list.appendChild(li);
    });
  }

  function renderResult() {
    var l = view.lesson;
    var box = $("result-box");
    box.hidden = !l.result;
    if (!l.result) { resultSig = ""; return; }
    var r = l.result;
    setText($("result-heading"), "Unseen " + l.noun.toLowerCase() + "s");
    setText($("result-score"), "Pip got " + r.right + " of " + r.total + " right. It needs " + r.need + (r.passed ? ". Lesson cleared." : "."));
    var sig = l.id + JSON.stringify(r.cases.map(function (c) { return [c.id, c.right, c.pip, c.explained]; })) + l.features.map(function (f) { return f.on ? 1 : 0; }).join("");
    if (sig === resultSig) return;
    resultSig = sig;
    var list = $("result-list");
    list.textContent = "";
    r.cases.forEach(function (c) {
      var li = el("li", "case " + (c.right ? "right" : "wrong"));
      var main = el("div");
      var head = el("div", "case-head");
      head.appendChild(el("span", "case-name", c.name));
      head.appendChild(el("span", "verdict " + (c.right ? "right" : "wrong"), c.right ? "Right" : "Wrong"));
      head.appendChild(el("span", "case-answer", c.right ? "Pip said " + c.pip + "." : "Pip said " + c.pip + ". The answer is " + c.truth + "."));
      main.appendChild(head);
      main.appendChild(chipRow(c.chips));
      li.appendChild(main);
      if (!c.right) {
        var btn = el("button", "why-btn", c.explained ? "Why? (seen)" : "Why?");
        btn.type = "button";
        btn.setAttribute("aria-label", "Why did Pip get " + c.name + " wrong?" + (c.explained ? " Already explained." : ""));
        btn.setAttribute("data-testid", "ttm-why-" + c.id);
        btn.addEventListener("click", function () { lastWhyButton = btn; send({ action: "why", case: c.id }); });
        li.appendChild(btn);
      }
      list.appendChild(li);
    });
  }

  function renderWhy() {
    var l = view.lesson;
    var w = l.why;
    var box = $("why-box");
    var wasHidden = box.hidden;
    box.hidden = !w;
    if (!w) return;
    setText($("why-heading"), "Why did Pip say " + w.pip + " for " + w.name + "?");
    setText($("why-sum"), "Pip said " + w.pip + ". The answer is " + w.truth + ".");
    setText($("why-category"), "Kind of mistake: " + w.category_name);
    setText($("why-because"), w.because);
    var steps = $("why-steps");
    steps.textContent = "";
    if (!w.steps.length) steps.appendChild(el("li", null, "Pip asked no questions. With what it was looking at, it answers " + w.pip + " for everything."));
    w.steps.forEach(function (s) { steps.appendChild(el("li", null, s.question + " " + s.value + ", so " + s.answer + "." )); });
    setText($("why-decisive"), w.decisive ? "The question that decided it: " + w.decisive.question + " (" + w.decisive.feature + ")." : "No single question decided it.");
    setText($("why-looking"), "Pip was looking at: " + (w.looking_at.join(", ") || "nothing") + ".");
    var total = w.group.n;
    setText($("why-group"), "The path ends in a group of " + plural(total, "training case", "training cases") + ": " +
      w.group.counts.map(function (g) { return g.n + " " + g.bin; }).join(", ") + ". These look most like this case:");
    var list = $("why-neighbours");
    list.textContent = "";
    w.neighbours.forEach(function (n) {
      var li = el("li", "case");
      var head = el("div", "case-head");
      head.appendChild(el("span", "case-name", n.name));
      head.appendChild(el("span", "case-answer", "Answer: " + n.label));
      li.appendChild(head);
      li.appendChild(chipRow(n.chips));
      list.appendChild(li);
    });
    if (wasHidden || box.dataset.case !== w.case) {
      box.dataset.case = w.case;
      if (box.scrollIntoView) box.scrollIntoView({ block: "nearest" });
      box.focus({ preventScroll: true });
    }
  }

  // ---- lessons panel, notebook, gallery --------------------------------------------------------------------
  function allLessons() {
    var out = [];
    view.shelves.forEach(function (s) { if (s.open) s.lessons.forEach(function (l) { out.push(l); }); });
    return out;
  }
  function prevLesson() {
    var list = allLessons();
    var idx = list.findIndex(function (l) { return l.current; });
    return idx > 0 ? list[idx - 1] : null;
  }
  function renderShelves() {
    var sig = JSON.stringify(view.shelves);
    if (sig === shelfSig) return;
    shelfSig = sig;
    var holder = $("shelf-list");
    holder.textContent = "";
    view.shelves.forEach(function (s) {
      var block = el("div", "shelf-block" + (s.open ? "" : " locked"));
      block.appendChild(el("h3", null, s.name + " - " + s.done + " of " + s.total + " cleared"));
      block.appendChild(el("p", "note blurb", s.open ? s.blurb : "Locked. Clear " + plural(s.need, "more lesson", "more lessons") + " on " + s.after + " to open this shelf (" + s.need_total + " in all)."));
      var grid = el("ul", "lesson-grid");
      s.lessons.forEach(function (l) {
        var li = el("li");
        var btn = el("button", "lesson-btn" + (l.cleared ? " cleared" : "") + (l.current ? " current" : ""));
        btn.type = "button";
        btn.appendChild(el("span", "lb-name", l.number + ". " + l.title));
        btn.appendChild(el("span", "lb-meta", !s.open ? "Locked" : l.cleared ? (l.best ? "Cleared, best features" : "Cleared") : "Open"));
        btn.setAttribute("data-testid", "ttm-lesson-" + l.id);
        if (!s.open) btn.setAttribute("aria-disabled", "true");
        btn.addEventListener("click", function () {
          if (!s.open) { showToast("Clear " + plural(s.need, "more lesson", "more lessons") + " on " + s.after + " first."); return; }
          send({ action: "pick", lesson: l.id });
          setPanel("lessons-panel", "lessons-toggle-button", false);
          $("lesson-panel").focus({ preventScroll: true });
          $("lesson-panel").scrollIntoView({ block: "start" });
        });
        li.appendChild(btn);
        grid.appendChild(li);
      });
      block.appendChild(grid);
      holder.appendChild(block);
    });
  }

  function renderNotebook() {
    var sig = JSON.stringify(view.notebook);
    setText($("notebook-count"), plural(view.totals.notebook, "entry", "entries") + " of " + view.totals.notebook_total + " found.");
    var short = document.querySelector("#notebook-toggle-button .btn-long");
    if (short) short.textContent = "Failure Notebook (" + view.totals.notebook + "/" + view.totals.notebook_total + ")";
    if (sig === notebookSig) return;
    notebookSig = sig;
    var holder = $("notebook-list");
    holder.textContent = "";
    view.notebook.forEach(function (e) {
      var d = el("details", "entry " + (e.found ? "found" : "empty"));
      d.id = "entry-" + e.id;
      var sum = el("summary", null, e.name);
      sum.appendChild(el("span", "tag", e.found ? "Found" : "Not found yet"));
      d.appendChild(sum);
      if (e.found) {
        d.appendChild(el("p", null, e.about));
        d.appendChild(el("p", null, "An example: " + e.example));
        d.appendChild(el("p", "card-src", "You found this in: " + e.lessons.join(", ") + "."));
      } else {
        d.appendChild(el("p", null, e.later ? "Examples turn up on a later shelf." : "Open a Why on a wrong answer to look for this kind of mistake."));
      }
      holder.appendChild(d);
    });
  }

  function renderGallery() {
    var sig = JSON.stringify(view.gallery);
    $("gallery-empty").hidden = view.gallery.length > 0;
    setText($("gallery-heading"), "Pip's lessons (" + view.gallery.length + " of " + view.totals.lessons + ")");
    if (sig === gallerySig) return;
    gallerySig = sig;
    var holder = $("gallery-list");
    holder.textContent = "";
    view.gallery.forEach(function (c) {
      var d = el("details", "entry found");
      d.id = "card-" + c.id;
      var sum = el("summary", null, c.title);
      sum.appendChild(el("span", "tag", c.best ? "Best features" : "Cleared"));
      d.appendChild(sum);
      d.appendChild(el("p", null, c.learned));
      d.appendChild(el("p", "card-src", c.shelf + ", lesson " + c.number + ". Pip looked at: " + c.looked_at.join(", ") + "."));
      var tree = el("ul", "tree-list");
      c.tree.forEach(function (line) {
        var li = el("li", /^(first |yes, then |no, then )/.test(line.text) ? "ask" : "end", line.text);
        li.style.setProperty("--d", String(line.d));
        tree.appendChild(li);
      });
      d.appendChild(tree);
      holder.appendChild(d);
    });
  }

  // ---- About (with the live Wikipedia read), What's New ---------------------------------------------------------
  function listFill(id, items) {
    var node = $(id);
    node.textContent = "";
    items.forEach(function (text) { node.appendChild(el("li", null, text)); });
  }
  function renderInfo() {
    var info = view.info;
    if (!info) return;
    setText($("info-page-framing"), info.framing);
    setText($("pledge-heading"), info.pledge_heading);
    listFill("pledge-list", info.pledge);
    setText($("how-heading"), info.how_heading);
    listFill("how-list", info.how);
    setText($("facts-heading"), info.facts_heading);
    var list = $("info-page-sources");
    if (list.dataset.drawn) return;
    list.dataset.drawn = "1";
    info.facts.forEach(function (fact) {
      var item = el("li", "info-page-source");
      item.appendChild(el("strong", null, fact.heading));
      item.appendChild(el("p", "info-page-framing", fact.fact));
      item.appendChild(el("p", "info-page-tie-in", fact.tie_in));
      var link = el("a", null, fact.source.title);
      link.href = fact.source.url; link.target = "_blank"; link.rel = "noopener noreferrer";
      var src = el("p", "info-page-source-note");
      src.appendChild(document.createTextNode("Source: "));
      src.appendChild(link);
      src.appendChild(document.createTextNode(", " + fact.source.publisher + ". Read on " + fact.source.date_read + "."));
      item.appendChild(src);
      list.appendChild(item);
    });
  }
  function firstSentences(text, max) {
    var out = "";
    var parts = String(text).split(/(?<=[.!?])\s+/);
    for (var i = 0; i < parts.length; i++) {
      if ((out + " " + parts[i]).length > max && out) break;
      out = out ? out + " " + parts[i] : parts[i];
    }
    return out;
  }
  function today() { var d = new Date(); return d.getFullYear() + "-" + ("0" + (d.getMonth() + 1)).slice(-2) + "-" + ("0" + d.getDate()).slice(-2); }
  function loadLiveInfo() {
    if (infoLiveDone || !view || !view.info) return;
    infoLiveDone = true;
    var box = $("info-live");
    var live = view.info.live;
    setText(box.firstChild || box.appendChild(el("p", "note")), "Reading the article summary...");
    var fallback = function () {
      box.textContent = "";
      box.appendChild(el("p", "note", "Wikipedia could not be reached just now, so the notes above stand. They were read on " + view.info.date_read + "."));
    };
    if (typeof fetch !== "function") { fallback(); return; }
    fetch(live.api, { headers: { Accept: "application/json" } }).then(function (r) {
      if (!r.ok) throw new Error("status " + r.status);
      return r.json();
    }).then(function (data) {
      var extract = data && typeof data.extract === "string" ? data.extract.trim() : "";
      if (!extract) throw new Error("empty");
      box.textContent = "";
      box.appendChild(el("p", "info-live-text", firstSentences(extract, 420)));
      var src = el("p", "info-page-source-note");
      src.appendChild(document.createTextNode("Source: "));
      var link = el("a", null, live.title);
      link.href = live.url; link.target = "_blank"; link.rel = "noopener noreferrer";
      src.appendChild(link);
      src.appendChild(document.createTextNode(", " + live.publisher + ", text under CC BY-SA. Read live on " + today() + "."));
      box.appendChild(src);
    }).catch(fallback);
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
    var long = document.querySelector("#changelog-toggle-button .btn-long");
    if (long) long.textContent = "What's New (" + entries.length + ")";
  }
  function loadChangelog() {
    return fetch("changelog.json").then(function (r) { return r.text(); }).then(function (text) {
      window.CHANGELOG_JSON = text;       // shared/whats-new-banner.js reads this to show a returning player only what is new
      var data = JSON.parse(text);
      var list = Array.isArray(data) ? data : (data && data.changelog) || [];
      renderChangelog(list.slice().sort(function (a, b) { return a.date < b.date ? 1 : a.date > b.date ? -1 : 0; }));
    }).catch(function () { renderChangelog([]); });
  }

  // ---- the tutorial (shared/tutorial.js; offered from the opening screen, restartable from the toolbar) ----------------
  // A step whose element is hidden at that moment (the unseen cases before a Test) is shown as a centred card instead.
  var TUTORIAL_STEPS = [
    { title: "Welcome to the workshop", text: "Pip is a small sorting machine. You choose what Pip may look at, press Train, and see how it does on cases it has never seen. Nothing is timed, nothing can fail and nothing is lost. You can skip this tour at any time." },
    { selector: "#feature-list", title: "What may Pip look at?", text: "Each switch lets Pip see one thing about a case. ON means Pip may use it, OFF means it is blind to it. Fewer, better-chosen features often teach Pip more than all of them. Keys 1 to 8 flip the switches." },
    { selector: "#train-button", title: "Train", text: "Train makes Pip study its training cases and grow a tree of questions from only the features that are on. You can change the switches and train again as often as you like." },
    { selector: "#test-button", title: "Test", text: "Test asks Pip about cases it has never seen. Each one is marked Right or Wrong, and Pip needs enough right to clear the lesson." },
    { selector: "#result-box", title: "Why was it wrong?", text: "Every wrong answer has a Why button. It shows the exact questions the case went through, the training cases that looked alike, and which of five kinds of mistake it was." },
    { selector: "#lamp-words", title: "Pip's lamp", text: "The lamp on Pip's head and the sentence under it say how the lesson stands: waiting, trained, puzzled or pleased. The sentence always says it in words as well." },
    { selector: "#lessons-toggle-button", title: "Lessons and shelves", text: "Lessons sit on shelves of eight. Clear any five on a shelf to open the next shelf, and inside a shelf you can go in any order. Clearing a lesson with exactly the right features earns the best mark." },
    { selector: "#notebook-toggle-button", title: "The Failure Notebook", text: "The first time you open a Why on an example of a kind of mistake, it is written into the notebook. Cleared lessons also keep a card of what Pip learned." },
    { selector: "#settings-toggle-button", title: "Settings", text: "Text size, reduced motion, effects, high contrast and the light theme are in Settings, and Start over asks before it clears anything." },
    { title: "That is all", text: "Press ? at any time for the keyboard help. The Tutorial button in the toolbar brings this tour back." }
  ];

  // ---- render ---------------------------------------------------------------------------------------
  function render() {
    renderStats();
    renderHead();
    renderFeatures();
    renderTrainList();
    renderTree();
    renderResult();
    renderWhy();
    renderShelves();
    renderNotebook();
    renderGallery();
    renderInfo();
    setText($("status-line"), view.lesson.result ? "" : view.message || "");
  }

  // ---- talking to the engine --------------------------------------------------------------------------
  function persist() {
    try {
      var proxy = engine.getState();
      var obj = proxy.toJs({ dict_converter: Object.fromEntries });
      if (proxy.destroy) proxy.destroy();
      lsSet(STORE_KEY, JSON.stringify(obj));
    } catch (e) { /* the save widget keeps the real copy */ }
  }
  function send(request) {
    if (!engine) return null;
    var reply;
    try { reply = JSON.parse(engine.handle(JSON.stringify(request))); } catch (err) { showToast("Something went wrong. Reload to try again."); return null; }
    if (reply.error) { showToast(reply.error); return null; }
    view = reply;
    render();
    showToast(view.message || "");
    var text = view.say || view.message;
    if (request.action === "pick" || request.action === "next") {
      var l = view.lesson;
      text = l.shelf + ", lesson " + l.number + " of " + l.of + ", " + l.title + (l.cleared ? ", cleared" : "") + ". " + l.task;
    }
    announce(text);
    if (request.action === "test" && view.lesson.result) {
      var rb = $("result-box");
      if (rb.scrollIntoView) rb.scrollIntoView({ block: "nearest" });
    }
    if (request.action === "close_why" && lastWhyButton && document.body.contains(lastWhyButton)) lastWhyButton.focus({ preventScroll: true });
    persist();
    return view;
  }

  function askThen(id, message, confirmLabel, go) {
    if (window.ConfirmDialog) window.ConfirmDialog.ask({ id: id, message: message, confirmLabel: confirmLabel, allowSkip: false, onConfirm: go });
    else go();
  }
  // True while something modal is on screen (the opening screen, the tutorial, the shortcuts list or a confirm dialog), so the
  // workshop's own keys stay quiet and the dialog gets the keystroke.
  function modalOpen() {
    var nodes = document.querySelectorAll("[role='dialog'], #tutorial-overlay, #confirm-dialog-overlay, .confirm-dialog");
    for (var i = 0; i < nodes.length; i++) {
      var n = nodes[i];
      if (n.hidden) continue;
      var cs = window.getComputedStyle(n);
      if (cs.display !== "none" && cs.visibility !== "hidden") return true;
    }
    return false;
  }
  function closePanels() {
    var closed = false;
    ["lessons", "notebook", "changelog", "settings", "info-page"].forEach(function (name) {
      var panel = $(name + "-panel");
      if (panel && !panel.hidden) { setPanel(name + "-panel", name + "-toggle-button", false); closed = true; }
    });
    return closed;
  }

  function wire() {
    $("toast").addEventListener("click", function () { showToast(""); });
    $("train-button").addEventListener("click", function () { send({ action: "train" }); });
    $("test-button").addEventListener("click", function () { send({ action: "test" }); });
    $("reset-switches-button").addEventListener("click", function () { send({ action: "reset_switches" }); });
    $("why-close-button").addEventListener("click", function () { send({ action: "close_why" }); });
    $("prev-lesson-button").addEventListener("click", function () { var p = prevLesson(); if (p) send({ action: "pick", lesson: p.id }); });
    $("next-lesson-button").addEventListener("click", function () { send({ action: "next" }); });
    $("done-next-button").addEventListener("click", function () { send({ action: "next" }); $("lesson-panel").focus({ preventScroll: true }); });
    $("done-lessons-button").addEventListener("click", function () {
      setPanel("lessons-panel", "lessons-toggle-button", true);
      if ($("lessons-panel").scrollIntoView) $("lessons-panel").scrollIntoView({ block: "start" });
    });
    wirePanelToggle("lessons-toggle-button", "lessons-panel");
    wirePanelToggle("notebook-toggle-button", "notebook-panel");
    wirePanelToggle("changelog-toggle-button", "changelog-panel");
    wirePanelToggle("info-page-toggle-button", "info-page-panel");
    $("info-page-toggle-button").addEventListener("click", function () { if (!$("info-page-panel").hidden) loadLiveInfo(); });
    $("reset-button").addEventListener("click", function () {
      askThen("teach-the-machine-reset", "Start over? Every cleared lesson, your Failure Notebook and your tally will be cleared.", "Clear it all", function () {
        shelfSig = notebookSig = gallerySig = trainSig = resultSig = ""; send({ action: "reset" });
      });
    });
    // The save widget loads a save straight into the engine; this redraws afterwards.
    window.teachTheMachineRefresh = function () {
      if (engine) { featureSig = trainSig = shelfSig = notebookSig = gallerySig = resultSig = ""; send({ action: "open" }); }
    };
    document.addEventListener("keydown", function (e) {
      if (modalOpen()) return;
      if (e.key === "Escape") {
        if (closePanels()) return;
        if (view && view.lesson.why) send({ action: "close_why" });
        return;
      }
      if (e.ctrlKey || e.metaKey || e.altKey || !view) return;
      var tag = e.target && e.target.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
      var key = e.key.toLowerCase();
      if (key >= "1" && key <= "8") {
        var f = view.lesson.features[parseInt(key, 10) - 1];
        if (f) { e.preventDefault(); send({ action: "toggle", feature: f.id }); }
      } else if (key === "t") {
        e.preventDefault(); send({ action: "train" });
      } else if (key === "e" && view.lesson.trained) {
        e.preventDefault(); send({ action: "test" });
      }
    });
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
    // The opening screen (shared/opening-screen.js) answers first. "New Game" starts a clean workshop; the old local copy is kept under
    // its own key so a mis-click never costs a game (the save widget also snapshots before a New Game).
    var choice = "continue";
    try { if (window.NoyvjOpeningScreen && window.NoyvjOpeningScreen.choice) choice = await window.NoyvjOpeningScreen.choice; } catch (e) { choice = "continue"; }
    var saved = lsGet(STORE_KEY);
    if (choice === "new") {
      if (saved && saved !== "{}") lsSet(BEFORE_NEW_KEY, saved);
      try { localStorage.removeItem(STORE_KEY); } catch (e) { /* ok */ }
      saved = null;
    }
    if (saved && saved !== "{}") {
      lsSet(BACKUP_KEY, saved);      // kept until the next good save, so a load problem can never cost the player a game
      try { engine.loadState(pyodide.toPy(JSON.parse(saved))); } catch (e) { /* a bad save never blocks play */ }
    }
    $("engine-status").textContent = "";
    send({ action: "open" });
    await changelog;
    if (window.GameTutorial) window.GameTutorial.init(window.teachTheMachineTutorialSteps ? window.teachTheMachineTutorialSteps(TUTORIAL_STEPS) : TUTORIAL_STEPS, { gameId: "teach-the-machine" });
  }

  wire();
  boot().catch(function (err) {
    $("engine-status").textContent = "The workshop could not open (" + err + "). Reload to try again.";
  });
})();
