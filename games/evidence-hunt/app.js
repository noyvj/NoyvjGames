/* Evidence Hunt view: glue only. The engine (game.py and its modules) holds every rule; this file draws what handle() returns
   and forwards what the player does. No game logic lives here. */
(function () {
  "use strict";
  var ENGINE_MODULES = ["lexicon.py", "houses.py", "casework.py", "solver.py", "casekit.py", "cases_1.py", "cases_2.py", "cases_3.py", "cases_4.py", "cases_5.py", "cases.py", "progress.py", "gen.py", "codex.py", "achievements.py", "render.py", "hints.py", "info.py"];
  var STORE_KEY = "evidence-hunt:state";
  var BACKUP_KEY = "evidence-hunt:state-backup";
  var SHORT = ["Cold", "Charge", "Writing", "Lights", "Prints", "Glow"];

  var $ = function (id) { return document.getElementById(id); };
  var engine = null;
  var view = null;
  var caseId = null;
  var picked = [];

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
  // Rebuilding a row of buttons would drop keyboard focus; remember which keyed button had it and give it back.
  function keepFocus(build) {
    var active = document.activeElement;
    var key = active && active.dataset ? active.dataset.key : null;
    build();
    if (key) {
      var again = document.querySelector('[data-key="' + key + '"]');
      if (again && again !== document.activeElement) again.focus();
    }
  }

  // ---- panels --------------------------------------------------------------------------------------
  function wirePanelToggle(buttonId, panelId) {
    $(buttonId).addEventListener("click", function () {
      $(panelId).hidden = !$(panelId).hidden;
      $(buttonId).setAttribute("aria-expanded", String(!$(panelId).hidden));
    });
  }
  function renderAbout() {
    var about = view.about;
    if (!about || $("pledge-list").dataset.done) return;
    $("pledge-list").dataset.done = "1";
    setText($("info-page-framing"), about.framing);
    setText($("info-page-notice"), about.notice);
    setText($("pledge-heading"), about.pledge_heading);
    setText($("how-heading"), about.how_heading);
    about.pledge.forEach(function (line) { $("pledge-list").appendChild(el("li", null, line)); });
    about.how.forEach(function (line) { $("how-list").appendChild(el("li", null, line)); });
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
    var t = view.totals;
    bumpStat("stat-cases", t.done + "/" + t.cases);
    bumpStat("stat-clean", t.clean);
    bumpStat("stat-readings", view.tally.readings);
    bumpStat("stat-pages", view.guide.found + "/" + view.guide.total);
    bumpStat("stat-rooms", view.tally.rooms);
    bumpStat("stat-accusations", view.tally.accusations);
    bumpStat("stat-wrong", view.tally.wrong);
    bumpStat("stat-restores", view.tally.restores);
    bumpStat("stat-trips", view.tally.trips);
    bumpStat("stat-hints", view.tally.hints);
    bumpStat("stat-steady", t.steady);
    bumpStat("stat-rough", t.rough);
  }
  function sealNode(name) {
    return el("span", "seal seal-" + name.toLowerCase(), name);
  }

  // ---- the case ---------------------------------------------------------------------------------------
  function renderCaseHead() {
    var c = view.case;
    setText($("case-chapter"), c.chapter + (c.number ? " · case " + c.number + " of " + c.of : "") + (c.best ? " · best seal: " + c.best_name : ""));
    setText($("case-heading"), c.title);
    setText($("case-client"), "The client: " + c.client);
    setText($("case-intro"), c.intro);
    if ($("scene-holder").dataset.sig !== c.id) {
      $("scene-holder").dataset.sig = c.id;
      $("scene-holder").innerHTML = c.scene;
    }
    setText($("presence-line"), c.presence_line);
    $("case-code").hidden = !c.practice;
    setText($("case-code-text"), c.code);
    var acc = view.accounts;
    $("accounts").hidden = !acc.length;
    var list = $("accounts-list");
    list.textContent = "";
    acc.forEach(function (a) { list.appendChild(el("li", null, (a.room ? "In the " + a.room + ": " : "") + a.line)); });
    var entered = 0, total = 0;
    view.house.forEach(function (f) { f.rooms.forEach(function (r) { total += 1; if (r.entered) entered += 1; }); });
    setText($("house-count"), "(" + entered + " of " + total + " rooms entered)");
    var cost = c.cost;
    setText($("cost-line"), "Cost so far: " + cost + (cost === 0 ? " (clean so far)" : " (" + c.grade_now_name.toLowerCase() + ")"));
  }
  function buildHouse() {
    var plan = $("house-plan");
    plan.textContent = "";
    view.house.forEach(function (f) {
      var sec = el("section", "floor");
      sec.appendChild(el("h4", null, f.name));
      var grid = el("div", "floor-grid");
      grid.style.gridTemplateColumns = "repeat(" + f.cols + ", minmax(0, 1fr))";
      f.rooms.forEach(function (r) {
        var b = el("button", "room unknown");
        b.type = "button";
        b.dataset.key = "room-" + r.i;
        b.dataset.testid = "evidence-hunt-room-" + r.i;
        b.style.gridColumn = String(r.col + 1);
        b.style.gridRow = String(r.row + 1);
        b.appendChild(el("span", "rname", r.name));
        b.appendChild(el("span", "rstate"));
        b.appendChild(el("span", "rtag"));
        b.addEventListener("click", function () { act({ action: "go", room: r.i }); });
        grid.appendChild(b);
      });
      sec.appendChild(grid);
      plan.appendChild(sec);
    });
  }
  function renderHouse() {
    if ($("house-plan").dataset.sig !== view.case.id) {
      $("house-plan").dataset.sig = view.case.id;
      buildHouse();
    }
    view.house.forEach(function (f) {
      f.rooms.forEach(function (r) {
        var b = document.querySelector('[data-key="room-' + r.i + '"]');
        if (!b) return;
        b.className = "room " + (!r.entered ? "unknown" : (r.restless ? "restless" : "still")) + (r.here ? " here" : "");
        var state = !r.entered ? "Not entered yet" : (r.restless ? "◆ Restless" : "◇ Still");
        if (r.here) state += " · you are here";
        setText(b.children[1], state);
        var tags = r.tags.slice();
        if (r.reads) tags.push(plural(r.reads, "reading", "readings"));
        setText(b.children[2], tags.join(" · "));
        b.setAttribute("aria-label", r.name + ". " + state + (tags.length ? ". " + tags.join(", ") : ""));
      });
    });
  }
  function renderBag() {
    var bag = view.bag;
    setText($("bag-count"), "(" + bag.count + " of " + bag.size + ")");
    var row = $("gear-row");
    if (!row.children.length) {
      bag.gear.forEach(function (g) {
        var b = el("button", "gear");
        b.type = "button";
        b.dataset.key = "gear-" + g.e;
        b.dataset.testid = "evidence-hunt-gear-" + g.e;
        b.appendChild(el("span", "letter", g.letter));
        var body = el("span");
        body.appendChild(el("span", "gname", g.name));
        body.appendChild(el("span", "gev"));
        b.appendChild(body);
        b.addEventListener("click", function () { act({ action: "pack", e: g.e }); });
        row.appendChild(b);
      });
    }
    bag.gear.forEach(function (g) {
      var b = row.children[g.e];
      b.setAttribute("aria-pressed", String(g.packed));
      b.className = "gear" + (g.ok ? "" : " unavailable");
      b.title = g.ok ? g.how : g.why;
      setText(b.querySelector(".gev"), g.ev + " · " + (g.packed ? "In the bag" : "Not packed"));
      b.setAttribute("aria-label", g.name + ", reads " + g.ev.toLowerCase() + ". " + (g.packed ? "In the bag" : "Not packed") + (g.ok ? "" : ". Not available: " + g.why));
    });
    setText($("van-note"), bag.van_cost ? "Readings are taken, so a different bag is a second trip (cost 1). Your notebook keeps every reading." : (bag.at_van ? "You are at the van." : "Nothing is read yet, so this costs nothing."));
  }
  function renderRoom() {
    var room = view.room;
    var use = $("use-row");
    keepFocus(function () {
      use.textContent = "";
      if (!room) {
        setText($("room-name"), "At the van");
        setText($("room-text"), "Pack your bag, then tap a room on the plan to walk in.");
        $("keepsake-row").hidden = true;
        return;
      }
      setText($("room-name"), room.name);
      setText($("room-text"), room.text);
      if (room.none_packed) use.appendChild(el("span", "note", "Nothing is packed yet. Pack the equipment you want to use."));
      room.uses.forEach(function (u) {
        var b = el("button", u.ok ? "" : "unavailable");
        b.type = "button";
        b.dataset.key = "use-" + u.e;
        b.dataset.testid = "evidence-hunt-use-" + u.e;
        b.appendChild(document.createTextNode(u.state ? u.name + ": " + u.word : "Use the " + u.name));
        b.appendChild(el("span", "left", u.ev));
        if (!u.ok) { b.setAttribute("aria-disabled", "true"); b.title = u.why; }
        b.setAttribute("aria-label", (u.state ? u.name + ": " + u.word : "Use the " + u.name + " here") + ", " + u.ev + (u.ok ? "" : ". " + u.why));
        b.addEventListener("click", function () { act({ action: "use", e: u.e }); });
        use.appendChild(b);
      });
      $("keepsake-row").hidden = !(room.keep && !room.looked);
      if (room.keep && !room.looked) setText($("look-button"), "Look at " + room.keep_name);
    });
  }
  function renderCould() {
    var holder = $("could-list");
    holder.textContent = "";
    if (!view.could.length) {
      holder.appendChild(el("p", "note", "Walk into the rooms to find where the house is restless. Then take readings there."));
    }
    view.could.forEach(function (g) {
      var box = el("div", "could-group");
      box.appendChild(el("div", "clabel", g.label + (g.certain ? " (only one fits)" : " (" + g.kinds.length + " fit)")));
      var ul = el("ul", "chips");
      g.kinds.forEach(function (k) { ul.appendChild(el("li", g.certain ? "certain" : "", k.name)); });
      box.appendChild(ul);
      holder.appendChild(box);
    });
  }
  function renderAccuse() {
    var n = view.accuse.n;
    if (picked.length > n) picked = picked.slice(0, n);
    var fits = {};
    view.sheet.forEach(function (s) { fits[s.id] = s.fits; });
    setText($("accuse-help"), n === 1 ? "Pick the one kind that fits, then name it. A wrong name costs 1 and nothing else." : "Pick two different kinds, one for each presence, then name them both. A wrong pair costs 1 and nothing else.");
    var box = $("accuse-options");
    keepFocus(function () {
      box.textContent = "";
      view.accuse.options.forEach(function (o) {
        var b = el("button", "suspect" + (fits[o.id] ? "" : " ruled-out"));
        b.type = "button";
        b.dataset.key = "suspect-" + o.i;
        b.dataset.testid = "evidence-hunt-suspect-" + o.i;
        var sheetEntry = view.sheet.filter(function (s) { return s.id === o.id; })[0];
        var em = el("span");
        em.innerHTML = sheetEntry.emblem;
        b.appendChild(em);
        b.appendChild(el("span", "sname", o.name));
        b.setAttribute("aria-pressed", String(picked.indexOf(o.i) !== -1));
        b.setAttribute("aria-label", o.name + (fits[o.id] ? "" : ", ruled out by your notebook") + (picked.indexOf(o.i) !== -1 ? ", picked" : ""));
        b.addEventListener("click", function () {
          var at = picked.indexOf(o.i);
          if (at !== -1) picked.splice(at, 1);
          else if (n === 1) picked = [o.i];
          else if (picked.length < n) picked.push(o.i);
          else picked = [picked[1], o.i];
          renderAccuse();
        });
        box.appendChild(b);
      });
    });
    var btn = $("accuse-button");
    var ready = picked.length === n;
    btn.setAttribute("aria-disabled", String(!ready));
    btn.classList.toggle("unavailable", !ready);
    setText(btn, n === 1 ? "Name the spirit" : "Name both");
    btn.disabled = false;
    $("accuse-box").hidden = view.case.done;
  }
  function renderNotebook() {
    var nb = view.notebook;
    var table = $("notebook-table");
    table.textContent = "";
    var head = el("tr");
    var corner = el("th", "roomcol", "Room");
    corner.setAttribute("scope", "col");
    head.appendChild(corner);
    nb.evidence.forEach(function (ev) {
      var th = el("th");
      th.setAttribute("scope", "col");
      th.title = ev.name + " (" + ev.gear + ")";
      th.appendChild(el("span", "letter", ev.letter));
      th.appendChild(document.createTextNode(SHORT[ev.e]));
      head.appendChild(th);
    });
    var thead = el("thead");
    thead.appendChild(head);
    table.appendChild(thead);
    var body = el("tbody");
    nb.rows.forEach(function (r) {
      var tr = el("tr");
      var th = el("td", "roomcell", r.name);
      th.appendChild(el("span", "rtag", r.restless ? "◆ Restless" : "◇ Still"));
      tr.appendChild(th);
      r.cells.forEach(function (c) {
        var td = el("td", "r-" + c.state, c.state === 0 ? "-" : (c.state === 3 ? "Doubt" : c.word));
        td.setAttribute("aria-label", r.name + ", " + nb.evidence[c.e].name + ": " + c.word);
        tr.appendChild(td);
      });
      body.appendChild(tr);
    });
    table.appendChild(body);
    setText($("notebook-empty"), nb.rows.length ? "" : "Nothing is noted yet. Walk into a room, then take a reading.");
    setText($("notebook-keepsake"), nb.keepsake_line);
  }
  function renderSheet() {
    var list = $("sheet-list");
    list.textContent = "";
    view.sheet.forEach(function (s) {
      var li = el("li", s.fits ? "" : "ruled-out");
      var em = el("span");
      em.innerHTML = s.emblem;
      li.appendChild(em);
      var body = el("span");
      body.appendChild(el("span", "cname", s.name));
      if (s.covered) {
        body.appendChild(el("span", "cline", "Covered: your guide already holds this page."));
      } else {
        body.appendChild(el("span", "cline", "Evidence: " + s.evidence.join(", ")));
        body.appendChild(el("span", "cline", "Habits: " + s.habits.join(" ")));
      }
      li.appendChild(body);
      list.appendChild(li);
    });
  }
  function renderLog() {
    var list = $("log-list");
    list.textContent = "";
    view.log.forEach(function (l) {
      var cls = l.kind === "refused" ? "refused" : (l.kind === "wrong" || l.kind === "van" ? "cost" : (l.kind === "right" ? "cure" : ""));
      list.appendChild(el("li", cls, l.msg));
    });
    list.scrollTop = list.scrollHeight;
  }
  function renderResult() {
    var r = view.result;
    var card = $("result-card");
    card.hidden = !r;
    if (!r) return;
    setText($("result-title"), "Case solved");
    var g = $("result-grade");
    g.textContent = "";
    g.appendChild(sealNode(r.grade_name));
    g.appendChild(document.createTextNode(" Cost " + r.cost + (r.new_best ? ". A new best seal for this case." : ". Your best here is " + r.best_name + ".")));
    setText($("result-text"), r.line);
    setText($("result-ending"), r.ending);
    $("again-button").hidden = !r.again;
    if (r.again) setText($("again-button"), "Another: " + r.again.name.toLowerCase());
    var ret = $("return-button");
    ret.hidden = !(r.keepsake && !r.keepsake.returned);
    if (r.keepsake) setText(ret, "Return " + r.keepsake.what);
    $("next-button").hidden = !r.next;
    setText($("next-button"), r.next ? "Next case: " + r.next_name : "Next case");
  }
  function renderHints() {
    var h = view.hint;
    var btn = $("hint-button");
    var done = view.case.done;
    btn.hidden = done || h.rung >= 3;
    setText(btn, h.rung === 0 ? "Would you like a suggestion?" : (h.rung === 1 ? "Another hint" : "Another hint: the answer"));
    $("hint-nudge").hidden = !h.nudge;
    setText($("hint-nudge"), h.nudge ? "Nudge: " + h.nudge : "");
    $("hint-hint").hidden = !h.hint;
    setText($("hint-hint"), h.hint ? "Hint: " + h.hint : "");
    $("hint-answer").hidden = !h.answer;
    if (h.answer) {
      setText($("hint-answer-text"), "Answer: " + h.answer);
      setText($("hint-do-button"), h.kind === "restore" ? "Restore the case" : "Do it for me");
    }
  }
  function renderGoalStrip() {
    var list = $("goals-list");
    var sig = view.goals.map(function (g) { return g.id + g.have; }).join(",");
    if (list.dataset.sig === sig) return;
    list.dataset.sig = sig;
    list.textContent = "";
    if (!view.goals.length) { list.appendChild(el("li", null, "Every goal you can reach right now is done. New ones appear as new chapters open.")); return; }
    view.goals.forEach(function (g) {
      var li = el("li");
      li.appendChild(el("strong", null, g.label + ": "));
      li.appendChild(document.createTextNode(g.description + " "));
      var bar = el("span", "bar");
      bar.setAttribute("aria-hidden", "true");
      var fill = el("span", "bar-fill");
      fill.style.width = Math.round(100 * g.have / g.need) + "%";
      bar.appendChild(fill);
      li.appendChild(bar);
      li.appendChild(el("span", "goal-count", " " + g.have + "/" + g.need));
      list.appendChild(li);
    });
  }
  function renderGuide() {
    var g = view.guide;
    var sig = g.found + ":" + g.complete + ":" + g.sections.map(function (s) { return s.found; }).join(",");
    if ($("guide-body").dataset.sig === sig) return;
    $("guide-body").dataset.sig = sig;
    setText($("guide-notice"), g.notice);
    setText($("guide-summary"), g.found + " of " + g.total + " pages filed, " + g.complete + " of 12 spirit pages complete. Pages are filed by playing: nothing is missable and nothing runs out.");
    var body = $("guide-body");
    body.textContent = "";
    g.sections.forEach(function (sec) {
      var d = el("details", "guide-section");
      if (sec.found < sec.total && sec.id === "spirits") d.open = true;
      d.appendChild(el("summary", null, sec.name + " (" + sec.found + "/" + sec.total + ")"));
      var ul = el("ul", "guide-list");
      sec.entries.forEach(function (e) {
        var li = el("li", e.unlocked ? "filed" : "unfiled");
        li.appendChild(el("strong", null, e.title));
        li.appendChild(el("span", "rtext", e.text));
        e.lines.forEach(function (l) { li.appendChild(el("span", "rline", l)); });
        ul.appendChild(li);
      });
      d.appendChild(ul);
      body.appendChild(d);
    });
  }
  var knownEarned = null;
  function renderAchievements() {
    var list = $("achievements-list");
    var earnedNow = [];
    var sig = view.achievements.map(function (x) { return x.id + x.have; }).join(",");
    if (list.dataset.sig !== sig) {
      list.dataset.sig = sig;
      list.textContent = "";
      view.achievements.forEach(function (x) {
        var li = el("li", x.earned ? "earned" : "");
        li.setAttribute("data-achievement-id", x.id);
        li.appendChild(el("span", "tick", x.earned ? "Earned" : x.have + "/" + x.need));
        var name = el("strong", null, " " + x.label + " ");
        name.setAttribute("data-achievement-label", "");
        li.appendChild(name);
        li.appendChild(el("span", null, x.description));
        list.appendChild(li);
      });
    }
    view.achievements.forEach(function (x) { if (x.earned) earnedNow.push(x.id); });
    $("achievements-toggle-button").textContent = "Achievements (" + earnedNow.length + "/" + view.achievements.length + ")";
    if (knownEarned !== null) {
      earnedNow.filter(function (id) { return knownEarned.indexOf(id) === -1; }).forEach(function (id) {
        var x = view.achievements.filter(function (y) { return y.id === id; })[0];
        showToast("Achievement unlocked: " + x.label + ".");
        announce("Achievement unlocked: " + x.label + ".");
      });
    }
    knownEarned = earnedNow;
  }
  function renderPractice() {
    var levels = $("practice-levels");
    if (!levels.children.length) {
      view.practice.levels.forEach(function (l) {
        var b = el("button", null, l.difficulty + ". " + l.name);
        b.type = "button";
        b.dataset.testid = "evidence-hunt-practice-" + l.difficulty;
        b.addEventListener("click", function () {
          send({ action: "practice", difficulty: l.difficulty });
          closePanel("practice-panel", "practice-toggle-button");
        });
        levels.appendChild(b);
      });
    }
    var p = view.practice;
    setText($("practice-note"), p.done ? "You have solved " + plural(p.done, "practice house", "practice houses") + ". " + (view.case.practice ? "You are in " + view.case.code + " now." : "") : "A new house each time you pick a size. Every size can be done without a wrong guess.");
  }
  function closePanel(panelId, buttonId) {
    $(panelId).hidden = true;
    $(buttonId).setAttribute("aria-expanded", "false");
    var anchor = $("case-panel");
    if (anchor.scrollIntoView) anchor.scrollIntoView({ block: "start" });
  }
  function renderCover() {
    var covered = view.case.covered;
    var btn = $("cover-button");
    btn.setAttribute("aria-pressed", String(covered));
    setText(btn, covered ? "Uncover the sheet" : "Cover the sheet");
    var full = view.guide.complete;
    setText($("cover-note"), full ? "From memory: hides the kinds whose guide page is complete. Nothing is lost." : "From memory: hides the kinds whose guide page is complete. None is complete yet, so nothing is hidden.");
  }
  function renderCases() {
    var holder = $("cases-body");
    holder.textContent = "";
    view.chapters.forEach(function (c) {
      var sec = el("section", "chapter" + (c.open ? "" : " locked"));
      sec.appendChild(el("h3", null, c.name + " (" + c.done + "/" + c.total + ")"));
      sec.appendChild(el("p", "note", c.open ? c.blurb : "Locked: finish " + c.need + " cases of " + c.prev_name + " to open this."));
      var ul = el("ul", "case-grid");
      c.cases.forEach(function (r) {
        var li = el("li");
        var b = el("button", "case-btn" + (r.current ? " current" : ""));
        b.type = "button";
        b.dataset.testid = "evidence-hunt-case-" + r.id;
        b.appendChild(el("span", "rname", r.number + ". " + r.name));
        var meta = el("span", "rmeta");
        var facts = plural(r.rooms, "room", "rooms") + (r.presences === 2 ? ", two presences" : "");
        if (r.grade) { meta.appendChild(sealNode(r.grade_name)); meta.appendChild(document.createTextNode(" " + facts)); }
        else meta.textContent = r.open ? (r.started ? "Started, " : "Not done, ") + facts : "Locked";
        b.appendChild(meta);
        b.setAttribute("aria-label", r.number + ", " + r.name + ". " + (r.grade ? r.grade_name + " seal" : (r.open ? "Not done" : "Locked")) + (r.current ? ". Current case" : ""));
        if (!r.open) b.setAttribute("aria-disabled", "true");
        b.addEventListener("click", function () {
          if (!r.open) { showToast("That chapter opens once " + c.need + " cases of " + c.prev_name + " are done."); return; }
          send({ action: "pick", case: r.id });
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

  // ---- render everything ----------------------------------------------------------------------------------
  function render() {
    renderAbout();
    if (view.case.id !== caseId) {
      caseId = view.case.id;
      picked = [];
      $("house-plan").dataset.sig = "";
    }
    renderStats();
    renderCaseHead();
    renderHouse();
    renderBag();
    renderRoom();
    renderCould();
    renderAccuse();
    renderNotebook();
    renderSheet();
    renderLog();
    renderResult();
    renderHints();
    renderCases();
    renderGoalStrip();
    renderGuide();
    renderCover();
    renderPractice();
    renderAchievements();
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
  function send(request) {
    if (!engine) return null;
    var result = JSON.parse(engine.handle(JSON.stringify(request)));
    if (result.error) { $("engine-status").textContent = "Something went wrong: " + result.error; return null; }
    view = result;
    showToast("");
    render();
    setText($("action-line"), result.result ? "Case solved." : (result.message || ""));
    if (result.message) announce(result.result ? "Case solved." : result.message);
    persist();
    return result;
  }
  function act(request) { return send(request); }

  // ---- keyboard ------------------------------------------------------------------------------------------
  function onKey(e) {
    if (!view || e.ctrlKey || e.metaKey || e.altKey) return;
    var tag = e.target && e.target.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
    if (document.querySelector("dialog[open], .confirm-dialog, [role='dialog']")) return;
    var n = parseInt(e.key, 10);
    if (n >= 1 && n <= 6 && e.key.length === 1) act({ action: "pack", e: n - 1 });
  }

  function askThen(id, message, confirmLabel, go, allowSkip) {
    if (window.ConfirmDialog) window.ConfirmDialog.ask({ id: id, message: message, confirmLabel: confirmLabel, allowSkip: Boolean(allowSkip), onConfirm: go });
    else go();
  }

  function wire() {
    $("toast").addEventListener("click", function () { showToast(""); });
    wirePanelToggle("cases-toggle-button", "cases-panel");
    wirePanelToggle("achievements-toggle-button", "achievements-panel");
    wirePanelToggle("practice-toggle-button", "practice-panel");
    wirePanelToggle("guide-toggle-button", "guide-panel");
    wirePanelToggle("changelog-toggle-button", "changelog-panel");
    wirePanelToggle("info-page-toggle-button", "info-page-panel");
    $("van-button").addEventListener("click", function () { act({ action: "van" }); });
    $("cover-button").addEventListener("click", function () { act({ action: "cover" }); });
    $("practice-open-button").addEventListener("click", function () {
      var code = $("practice-code").value.trim();
      if (!code) { showToast("Type a code first, such as EH3-1K9X2."); return; }
      var result = send({ action: "practice", code: code });
      if (result && result.ok) { $("practice-code").value = ""; closePanel("practice-panel", "practice-toggle-button"); }
    });
    $("practice-code").addEventListener("keydown", function (e) { if (e.key === "Enter") $("practice-open-button").click(); });
    $("again-button").addEventListener("click", function () { send({ action: "practice", difficulty: view.result.again.difficulty }); });
    $("code-copy-button").addEventListener("click", function () {
      var code = view.case.code;
      try {
        navigator.clipboard.writeText(code).then(function () { showToast("Code " + code + " copied."); }, function () { showToast("Select the code to copy it: " + code); });
      } catch (e) { showToast("Select the code to copy it: " + code); }
    });
    $("look-button").addEventListener("click", function () { act({ action: "look" }); });
    $("accuse-button").addEventListener("click", function () {
      var n = view.accuse.n;
      if (picked.length !== n) { showToast(n === 1 ? "Pick a kind from the sheet first." : "Pick two different kinds first."); return; }
      var names = picked.map(function (i) {
        return view.accuse.options.filter(function (o) { return o.i === i; })[0].name;
      });
      askThen("evidence-hunt-accuse", "Name " + names.join(" and ") + "? A wrong name costs 1 on this case's seal, and nothing else. Your notebook stays.", "Name them", function () {
        act({ action: "accuse", kinds: picked.slice() });
      }, true);
    });
    $("hint-button").addEventListener("click", function () { send({ action: "hint" }); });
    $("hint-do-button").addEventListener("click", function () { act({ action: "hint_do" }); });
    $("return-button").addEventListener("click", function () { send({ action: "return" }); });
    $("next-button").addEventListener("click", function () { send({ action: "next" }); });
    $("restore-button").addEventListener("click", function () {
      var started = view && (view.log.length > 1 || view.case.cost > 0 || view.result);
      if (!started) { send({ action: "restore" }); return; }
      askThen("evidence-hunt-restore", "Restore this case to its start? Your seals are kept; only this case's notebook and bag are cleared.", "Restore it", function () { send({ action: "restore" }); });
    });
    $("reset-button").addEventListener("click", function () {
      askThen("evidence-hunt-reset", "Start the whole book over? Your seals, guide pages and tally will be erased.", "Erase it", function () { caseId = null; send({ action: "reset" }); });
    });
    document.addEventListener("keydown", onKey);
    document.addEventListener("evidence-hunt-narrow-change", function () { if (view) { renderAccuse(); renderSheet(); } });
    // The save widget loads a save straight into the engine; this redraws afterwards.
    window.evidenceHuntRefresh = function () { if (engine) { caseId = null; send({ action: "open" }); } };
  }

  var TUTORIAL_STEPS = [
    { title: "Welcome to the notebook", text: "You are the quiet investigator a client calls when a house feels wrong. Each case is a house drawn as a floor plan, and you work out which kind of spirit is in it. Nothing is timed, nobody is harmed, and a wrong name only costs a point. The spirits and rules are invented. Skip any time and reopen this from the Tutorial button." },
    { selector: "#house-plan", title: "The house", text: "Tap a room to walk in. Walking is free. The moment you step in, the room tells you whether it is restless (a spirit is there) or still. Walk every room first." },
    { selector: "#gear-row", title: "Your bag", text: "Pack a few pieces of equipment before your first reading. The bag holds only a few, so pick the ones that tell the suspects apart. Once you take a reading the bag is locked, and a different bag is a second trip that costs 1." },
    { selector: "#room-box", title: "A reading", text: "In a restless room, use a piece of equipment from your bag. A reading is yes, no, or doubtful. Doubtful means the house fooled it (a draught, old wiring, a keepsake), so it tells you nothing about the spirit." },
    { selector: "#notebook-panel", title: "The notebook", text: "Every reading is written here, room by room. A restless room is marked with a thick border and the word Restless." },
    { selector: "#sheet-panel", title: "The book of visitors", text: "These are the kinds that might be in this house, each with three pieces of evidence and two habits. Kinds your notebook rules out are struck through. The client's account and any keepsake line are true." },
    { selector: "#accuse-box", title: "Name the spirit", text: "When only one kind fits, pick it and name it. A wrong name costs 1 and nothing else: your notebook stays and you can try again. The case always ends with a quiet note about who the spirit was." },
    { selector: "#restore-button", title: "Restore", text: "You can restore a case to its start at any time, for free, and try a different plan. Your seals are kept." },
    { selector: "#hint-button", title: "Hints", text: "Stuck? Ask for a nudge, then a hint, then the answer. Hints are free, only when you ask, and never touch a seal." },
    { selector: "#goals", title: "Your goals", text: "Three goals stay in view, in any order. Every room, reading and name counts toward something on the screen." },
    { selector: "#guide-toggle-button", title: "The field guide", text: "Every spirit you name, every kind of evidence you read, every piece of equipment you use and every keepsake you return is filed in the guide. Nothing is missable." },
    { selector: "#practice-toggle-button", title: "Practice houses", text: "Pick a size, or type a code, for a house made from that code. The same code always makes the same house." },
    { title: "You are ready", text: "Take your time. Your seals and guide pages are saved as you go." }
  ];

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
    if (window.GameTutorial) window.GameTutorial.init(window.evidenceHuntTutorialSteps ? window.evidenceHuntTutorialSteps(TUTORIAL_STEPS) : TUTORIAL_STEPS, { gameId: "evidence-hunt" });
  }

  wire();
  boot().catch(function (err) {
    $("engine-status").textContent = "The lamps would not light (" + err + "). Reload to try again.";
  });
})();
