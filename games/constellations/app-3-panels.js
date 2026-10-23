/* Constellations, part 3 of 4: the suggestion ladder, goals and difficulty, achievements, the charts panel, the atlas and its cards,
   About (with the live Wikipedia and Stellarium reads) and What's New. Glue only; every rule is in the engine. */
(function () {
  "use strict";

  var A = window.ConstellationsApp;
  var $ = A.$, askThen = A.askThen, el = A.el, lsGet = A.lsGet, plural = A.plural, send = A.send,
      setPanel = A.setPanel, setText = A.setText, showToast = A.showToast, svgEl = A.svgEl;

  var infoLiveDone = false;    // the live Wikipedia read has been tried for this page load
  var stelData = null;         // today's Stellarium file of constellation lines once it has been read (kept for this page load)
  var stelTried = false;

  // ---- the suggestion ladder (the engine decides every rung; this shows what it sent) --------------------------------
  var RUNG_LABELS = { 1: "Nudge", 2: "Hint", 3: "Answer" };
  function renderHints() {
    var ui = A.view.hint_ui;
    var shown = lsGet("constellations:hints-hidden") !== "1";
    $("hint-box").hidden = !shown || !ui.available;
    $("hints-checkbox").checked = shown;
    var button = $("hint-button");
    button.hidden = ui.next === 0;
    setText(button, ui.label || "Would you like a suggestion?");
    $("hint-draw-button").hidden = !ui.can_draw;
    var note = "";
    if (ui.next === 1) note = ui.opens_two ? "On Easy this opens the nudge and the hint together. Nothing is shown until you press." : "Nothing is shown until you press.";
    else if (ui.next === 3) note = ui.confirm ? "This shows the whole shape as a dotted guide. It asks first." : "This shows the whole shape as a dotted guide.";
    else if (ui.limit) note = "Hard has no answer step: the nudge and the hint are all the help there is.";
    else if (ui.can_draw) note = "Draw it puts the guide on the chart as one step; Undo takes it back, and Done is still yours to press.";
    setText($("hint-note"), note);
    var list = $("hint-list");
    var h = A.view.hint;
    var sig = h ? [h.rung, h.nudge, h.detail, h.answer].join("|") : "";
    if (list.dataset.sig === sig) return;
    list.dataset.sig = sig;
    list.textContent = "";
    list.hidden = !h;
    if (!h) return;
    [[1, h.nudge], [2, h.detail], [3, h.answer]].forEach(function (pair) {
      if (pair[0] > h.rung || !pair[1]) return;
      var li = el("li", "hint-item hint-rung-" + pair[0]);
      li.appendChild(el("span", "hint-label", RUNG_LABELS[pair[0]]));
      li.appendChild(el("span", "hint-text", pair[1]));
      list.appendChild(li);
    });
  }
  function pressHint(confirmed) {
    if (!A.view || A.view.hint_ui.next === 0) return;
    if (A.view.hint_ui.next === 3 && A.view.hint_ui.confirm && !confirmed) {
      askThen("constellations-hint-answer", "Show the whole answer? It draws the finished shape as a dotted guide, and you can then draw it with one press. Nothing is lost.", "Show it", function () { pressHint(true); });
      return;
    }
    var result = send({ action: "hint", confirm: confirmed === true });
    if (result && result.hint) {
      var items = $("hint-list").querySelectorAll(".hint-item");
      if (items.length) { items[items.length - 1].setAttribute("tabindex", "-1"); items[items.length - 1].focus({ preventScroll: true }); }
    }
  }

  // ---- goals, difficulty -----------------------------------------------------------------------------------------
  var DIFF_GAME = "constellations";
  var DIFF_TEXT = {
    easy: "The suggestion button opens the nudge and the hint together on its first press, and the answer needs no extra question.",
    normal: "The game as designed: a nudge, then a hint, then (after a question) the whole answer, each only when you press.",
    hard: "No answer step: the nudge and the hint are all the suggestions there are. Charts, numbers and records are the same."
  };
  function sendDifficulty() {
    if (!A.engine) return null;
    if (!window.NoyvjDifficulty) return send({ action: "open" });
    return send({ action: "difficulty", level: window.NoyvjDifficulty.get(DIFF_GAME) });
  }
  function wireDifficulty() {
    if (!window.NoyvjDifficulty) return;
    window.NoyvjDifficulty.mount("#difficulty-slot", { game: DIFF_GAME, collapsible: true, descriptions: DIFF_TEXT });
    window.NoyvjDifficulty.onChange(function (d) { if (d.game === DIFF_GAME) sendDifficulty(); });
  }
  function wireGoals() {
    if (!window.NoyvjGoals) return;
    A.goalsPanel = window.NoyvjGoals.mount("#goals", { game: "constellations", title: "Goals", getGoals: function () { return A.view ? A.view.goals : []; } });
    if (A.goalsPanel && window.NoyvjGoals.bindCheckbox) window.NoyvjGoals.bindCheckbox(A.goalsPanel, "#goals-checkbox");
  }

  // ---- achievements (the engine decides what is earned; this lists them and says so once when one is new) ------------

  function renderAchievements() {
    var list = $("achievements-list");
    var items = A.view.achievements;
    var sig = items.map(function (a) { return a.id + ":" + a.have; }).join(",");
    if (list.dataset.sig !== sig) {
      list.dataset.sig = sig;
      list.textContent = "";
      items.forEach(function (a) {
        var li = el("li", a.earned ? "earned" : "");
        li.setAttribute("data-achievement-id", a.id);
        li.appendChild(el("span", "tick", a.earned ? "Earned" : a.have + " of " + a.need));
        var name = el("strong", null, " " + a.label + " ");
        name.setAttribute("data-achievement-label", "");
        li.appendChild(name);
        li.appendChild(el("span", null, a.description));
        list.appendChild(li);
      });
    }
    var earnedNow = items.filter(function (a) { return a.earned; }).map(function (a) { return a.id; });
    var count = earnedNow.length + " of " + items.length;
    setText($("achievements-count"), count + " achievements earned.");
    var button = $("achievements-toggle-button");
    button.setAttribute("aria-label", "Achievements, " + count + " earned");
    setText(button.querySelector(".btn-long"), "Achievements (" + earnedNow.length + "/" + items.length + ")");
    setText(button.querySelector(".btn-short"), "Trophies " + earnedNow.length + "/" + items.length);
    if (A.knownEarned !== null) {
      var fresh = items.filter(function (a) { return a.earned && A.knownEarned.indexOf(a.id) === -1; });
      if (fresh.length) {
        A.achText = fresh.map(function (a) { return "Achievement unlocked: " + a.label + "."; }).join(" ");     // send() shows and announces it after the move's own message
      }
    }
    A.knownEarned = earnedNow;
  }

  // ---- charts panel, atlas and cards -----------------------------------------------------------------------------
  function allCharts() {
    var list = [];
    A.view.seasons.forEach(function (s) { s.charts.forEach(function (c) { list.push({ id: c.id, open: s.open, solved: c.solved, current: c.current }); }); });
    return list;
  }
  function renderSeasons() {
    var sig = JSON.stringify(A.view.seasons);
    if (sig === A.chartsSig) return;
    A.chartsSig = sig;
    var holder = $("season-list");
    holder.textContent = "";
    A.view.seasons.forEach(function (season) {
      var block = el("section", "season-block" + (season.open ? "" : " locked"));
      block.setAttribute("aria-label", season.name);
      block.appendChild(el("h3", null, season.name + " - " + season.done + " of " + season.total + " found"));
      block.appendChild(el("p", "note blurb", season.open ? season.blurb : "Opens when " + season.need_total + " charts in " + season.after + " are found (" + season.need + " more)."));
      var list = el("ul", "chart-list");
      season.charts.forEach(function (c) {
        var item = el("li");
        var btn = el("button", "chart-btn" + (c.solved ? " found" : "") + (c.current ? " current" : ""));
        btn.type = "button";
        btn.setAttribute("data-chart", c.id);
        if (!season.open) btn.setAttribute("aria-disabled", "true");
        if (c.current) btn.setAttribute("aria-current", "true");
        btn.appendChild(el("span", "cb-name", c.solved ? "✓ " + c.name : "Chart " + c.number));
        btn.appendChild(el("span", "cb-meta", c.solved ? c.meaning + " - " + plural(c.stars, "star", "stars") : plural(c.stars, "star", "stars") + (season.open ? "" : " - locked")));
        btn.addEventListener("click", function () {
          if (!season.open) { showToast("That page opens when " + season.need_total + " charts in " + season.after + " are found."); return; }
          send({ action: "pick", chart: c.id });
          setPanel("charts-panel", "charts-toggle-button", false);
          if ($("chart-panel").scrollIntoView) $("chart-panel").scrollIntoView({ block: "start" });
          $("board").focus({ preventScroll: true });
        });
        item.appendChild(btn);
        list.appendChild(item);
      });
      block.appendChild(list);
      holder.appendChild(block);
    });
  }

  function renderAtlas() {
    var atlas = A.view.atlas;
    var sig = JSON.stringify(atlas.items.map(function (i) { return [i.id, i.solved, i.current]; }));
    if (sig === A.atlasSig) return;
    A.atlasSig = sig;
    var svg = $("atlas");
    svg.textContent = "";
    svg.setAttribute("viewBox", "0 0 " + atlas.w + " " + atlas.h);
    svgEl("rect", { x: 0, y: 0, width: atlas.w, height: atlas.h, fill: "var(--sky-b)" }, svg);
    for (var h = 0; h <= 24; h += 2) {
      var gx = (24 - h) / 24 * atlas.w;
      svgEl("line", { x1: gx, y1: 0, x2: gx, y2: atlas.h, "class": "a-grid" }, svg);
      if (h < 24) svgEl("text", { x: gx - 4, y: 16, "class": "a-label", "text-anchor": "end" }, svg).textContent = h + "h";
    }
    [60, 30, 0, -30, -60].forEach(function (dec) {
      var gy = (90 - dec) / 180 * atlas.h;
      svgEl("line", { x1: 0, y1: gy, x2: atlas.w, y2: gy, "class": "a-grid" + (dec === 0 ? " eq" : "") }, svg);
      svgEl("text", { x: 6, y: gy - 4, "class": "a-label" }, svg).textContent = (dec > 0 ? "+" : "") + dec + "°";
    });
    var seasonOpen = {};
    A.view.seasons.forEach(function (s, i) { seasonOpen[i] = s.open; });
    atlas.items.forEach(function (it) {
      var g = svgEl("g", { "class": "a-item" + (it.solved ? " found" : " locked") + (it.current ? " current" : ""), tabindex: "0", role: "button", "data-chart": it.id }, svg);
      var seasonName = A.view.seasons[it.season].name;
      if (it.solved) {
        g.setAttribute("aria-label", it.name + ", found. Open its card.");
        it.lines.forEach(function (l) {
          var coords = { x1: it.pts[l[0]][0], y1: it.pts[l[0]][1], x2: it.pts[l[1]][0], y2: it.pts[l[1]][1] };
          svgEl("line", Object.assign({ "class": "a-line" }, coords), g);
          svgEl("line", Object.assign({ "class": "a-hit" }, coords), g);
        });
        it.pts.forEach(function (p) { svgEl("circle", { cx: p[0], cy: p[1], r: 3.6, "class": "a-dot" }, g); });
        svgEl("text", { x: it.x, y: it.y + it.r + 18, "class": "a-title" }, g).textContent = it.name;
      } else {
        g.setAttribute("aria-label", seasonName + " chart " + it.number + ", not found yet" + (seasonOpen[it.season] ? ". Go to the chart." : ". That page is not open yet."));
        svgEl("circle", { cx: it.x, cy: it.y, r: 13, "class": "a-ring" }, g);
        svgEl("circle", { cx: it.x, cy: it.y, r: 22, "class": "a-hit" }, g);
        svgEl("text", { x: it.x, y: it.y + 30, "class": "a-tag" }, g).textContent = seasonName.split(" ")[0] + " " + it.number;
      }
      var go = function () {
        if (it.solved) openCard(it.id);
        else if (seasonOpen[it.season]) {
          send({ action: "pick", chart: it.id });
          setPanel("atlas-panel", "atlas-toggle-button", false);
          if ($("chart-panel").scrollIntoView) $("chart-panel").scrollIntoView({ block: "start" });
        } else showToast("That page opens when " + A.view.seasons[it.season].need_total + " charts in " + A.view.seasons[it.season].after + " are found.");
      };
      g.addEventListener("click", go);
      g.addEventListener("keydown", function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); go(); } });
    });
  }

  function renderCards() {
    var sig = JSON.stringify(A.view.cards.map(function (c) { return c.id; }));
    if (sig === A.cardsSig) return;
    A.cardsSig = sig;
    var holder = $("atlas-cards");
    holder.textContent = "";
    $("cards-empty").hidden = A.view.cards.length > 0;
    A.view.cards.forEach(function (c) {
      var d = el("details", "card");
      d.id = "card-" + c.id;
      d.appendChild(el("summary", null, c.name + " - " + c.meaning));
      var dl = el("dl");
      [["Page", c.season + ", chart " + c.number], ["Stars", String(c.stars)],
       ["Brightest star", c.brightest.name + " (magnitude " + c.brightest.mag + ")"], ["Best seen", c.best.charAt(0).toUpperCase() + c.best.slice(1)],
       ["Line changes it took", String(c.moves)]].forEach(function (row) {
        dl.appendChild(el("dt", null, row[0]));
        dl.appendChild(el("dd", null, row[1]));
      });
      d.appendChild(dl);
      d.appendChild(el("p", "card-note", c.note));
      c.sources.forEach(function (s) { d.appendChild(el("p", "card-src", s)); });
      holder.appendChild(d);
    });
  }
  function openCard(id) {
    setPanel("atlas-panel", "atlas-toggle-button", true);
    var d = $("card-" + id) || document.getElementById("card-" + id);
    if (d) { d.open = true; if (d.scrollIntoView) d.scrollIntoView({ block: "center" }); var s = d.querySelector("summary"); if (s) s.focus({ preventScroll: true }); }
  }

  // ---- About (with the live Wikipedia read), What's New ---------------------------------------------------------
  function listFill(id, items) {
    var node = $(id);
    node.textContent = "";
    items.forEach(function (text) { node.appendChild(el("li", null, text)); });
  }
  function renderInfo() {
    var info = A.view.info;
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
    if (infoLiveDone || !A.view || !A.view.info) return;
    infoLiveDone = true;
    var box = $("info-live");
    var live = A.view.info.live;
    setText(box.firstChild || box.appendChild(el("p", "note")), "Reading the article summary...");
    var fallback = function () {
      box.textContent = "";
      box.appendChild(el("p", "note", "Wikipedia could not be reached just now, so the notes above stand. They were read on " + A.view.info.date_read + "."));
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
  function renderLiveLines(box, data) {
    var live = {};
    var count = 0;
    (data && data.constellations || []).forEach(function (con) {
      var code = String(con.id || "").split(" ").pop();
      var set = {};
      (con.lines || []).forEach(function (chain) { chain.forEach(function (hip) { set[hip] = true; }); });
      live[code] = set;
      count++;
    });
    if (!count) throw new Error("empty");
    var cards = A.view.cards;
    var same = cards.filter(function (card) { return live[card.code] && card.hips.every(function (hip) { return live[card.code][hip]; }); }).length;
    box.textContent = "";
    var text = cards.length === 0 ?
      "Today's file lists lines for " + count + " constellations. Finish a chart and this check will compare your constellation with it." :
      "Today's file lists lines for " + count + " constellations. " + same + " of your " + plural(cards.length, "finished constellation", "finished constellations") + " use only stars that the live lines also use" +
      (same === cards.length ? "." : "; the rest differ a little from the dated snapshot the charts were built from.");
    box.appendChild(el("p", "info-live-text", text));
    var src = el("p", "info-page-source-note");
    src.appendChild(document.createTextNode("Source: "));
    var link = el("a", null, A.view.info.live_lines.title);
    link.href = A.view.info.live_lines.url; link.target = "_blank"; link.rel = "noopener noreferrer";
    src.appendChild(link);
    src.appendChild(document.createTextNode(", " + A.view.info.live_lines.publisher + ". Read live on " + today() + ". Star positions and brightness stay as read on " + A.view.info.date_read + ": the whole star database is too large to read each time."));
    box.appendChild(src);
  }
  function loadLiveLines() {
    if (!A.view || !A.view.info || !A.view.info.live_lines) return;
    var box = $("info-live-lines");
    var fallback = function () {
      box.textContent = "";
      box.appendChild(el("p", "note", "Stellarium's lines could not be reached just now, so the charts stand as read on " + A.view.info.date_read + "."));
    };
    if (stelData) { try { renderLiveLines(box, stelData); } catch (e) { fallback(); } return; }
    if (stelTried || typeof fetch !== "function") { if (!stelTried) fallback(); return; }
    stelTried = true;
    setText(box.firstChild || box.appendChild(el("p", "note")), "Reading today's lines...");
    fetch(A.view.info.live_lines.api, { headers: { Accept: "application/json" } }).then(function (r) {
      if (!r.ok) throw new Error("status " + r.status);
      return r.json();
    }).then(function (data) { stelData = data; renderLiveLines(box, data); }).catch(function () { stelTried = false; fallback(); });
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
      renderChangelog(list.slice().sort(function (a, b) { return a.date < b.date ? 1 : -1; }));
    }).catch(function () { renderChangelog([]); });
  }

  // what the other parts use
  A.allCharts = allCharts;
  A.loadChangelog = loadChangelog;
  A.loadLiveInfo = loadLiveInfo;
  A.loadLiveLines = loadLiveLines;
  A.pressHint = pressHint;
  A.renderAchievements = renderAchievements;
  A.renderAtlas = renderAtlas;
  A.renderCards = renderCards;
  A.renderHints = renderHints;
  A.renderInfo = renderInfo;
  A.renderSeasons = renderSeasons;
  A.sendDifficulty = sendDifficulty;
  A.wireDifficulty = wireDifficulty;
  A.wireGoals = wireGoals;
})();
