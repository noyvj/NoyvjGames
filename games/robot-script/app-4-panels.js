/* Robot Script, part 4 of 5: About and What's New, the room picker and the sandbox, the medals table, goals,
   achievements, the workshop, hints and render(). Glue only; every rule is in the engine. */
(function () {
  "use strict";

  var A = window.RobotScriptApp;
  var $ = A.$, announce = A.announce, el = A.el, invalidateRun = A.invalidateRun, medalNode = A.medalNode,
      onSkip = A.onSkip, renderGoals = A.renderGoals, renderProgram = A.renderProgram,
      renderRoomHead = A.renderRoomHead, renderStats = A.renderStats, send = A.send, setText = A.setText,
      showToast = A.showToast, smallButton = A.smallButton, svgEl = A.svgEl, syncPlayButtons = A.syncPlayButtons,
      TILE = A.TILE, tools = A.tools;

  // ---- panels --------------------------------------------------------------------------------------
  function wirePanelToggle(buttonId, panelId) {
    $(buttonId).addEventListener("click", function () {
      $(panelId).hidden = !$(panelId).hidden;
      $(buttonId).setAttribute("aria-expanded", String(!$(panelId).hidden));
    });
  }
  function renderAbout() {
    var about = A.view.about;
    if (!about || $("pledge-list").dataset.done) return;
    $("pledge-list").dataset.done = "1";
    setText($("info-page-framing"), about.framing);
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

  // ---- the room picker -------------------------------------------------------------------------------
  function renderSandboxEntry() {
    var s = A.view.sandbox;
    var holder = $("sandbox-entry");
    var sig = String(s.open) + String(s.current);
    if (holder.dataset.sig === sig) return;
    holder.dataset.sig = sig;
    holder.textContent = "";
    holder.appendChild(el("h3", null, "Sandbox"));
    holder.appendChild(el("p", "note", s.open ? "Paint any room, write any list, run it as often as you like. Nothing is scored." : "Opens when every room of " + s.need + " is cleared."));
    var b = el("button", s.current ? "room-btn current" : "room-btn", s.open ? (s.current ? "In the sandbox" : "Open the sandbox") : "Locked");
    b.type = "button";
    b.dataset.testid = "robot-script-sandbox-open";
    if (!s.open) b.setAttribute("aria-disabled", "true");
    b.addEventListener("click", function () {
      if (!s.open) { showToast("The sandbox opens once every room of " + s.need + " is cleared."); return; }
      send({ action: "sandbox" });
      $("rooms-panel").hidden = true;
      $("rooms-toggle-button").setAttribute("aria-expanded", "false");
    });
    holder.appendChild(b);
  }
  function renderSandboxTools() {
    var s = A.view.sandbox;
    var tools = $("sandbox-tools");
    if (tools.dataset.built) return;
    tools.dataset.built = "1";
    s.tiles.forEach(function (t, i) {
      var b = el("button", "tile-tool", t.label);
      b.type = "button";
      b.dataset.tile = t.tile;
      b.dataset.testid = "robot-script-tile-" + i;
      b.setAttribute("aria-pressed", String(i === 1));
      b.addEventListener("click", function () { A.sandboxTile = t.tile; syncTileTools(); });
      tools.appendChild(b);
    });
    s.presets.forEach(function (p) {
      var o = el("option", null, p.label);
      o.value = p.id;
      $("sbx-preset").appendChild(o);
    });
    $("sbx-col").max = s.size; $("sbx-row").max = s.size;
    syncTileTools();
  }
  function syncTileTools() {
    Array.prototype.forEach.call($("sandbox-tools").querySelectorAll("button"), function (b) { b.setAttribute("aria-pressed", String(b.dataset.tile === A.sandboxTile)); });
  }
  function onRoomClick(e) {
    if (!A.view) return;
    if (A.play.running && !A.view.room.sandbox) {      // R4-RSMO-6: a tap on the room while a run plays skips to the end
      onSkip();
      return;
    }
    if (!A.view.room.sandbox) return;
    var svg = svgEl();
    if (!svg || !svg.getScreenCTM) return;
    var pt = svg.createSVGPoint();
    pt.x = e.clientX; pt.y = e.clientY;
    var p = pt.matrixTransform(svg.getScreenCTM().inverse());
    var x = Math.floor(p.x / TILE), y = Math.floor(p.y / TILE);
    if (x < 0 || y < 0 || x >= A.view.room.w || y >= A.view.room.h) return;
    send({ action: "sbx_paint", x: x, y: y, tile: A.sandboxTile }, true);
  }
  function renderRooms() {
    renderSandboxEntry();
    renderSandboxTools();
    var holder = $("rooms-body");
    var sig = A.view.difficulty + JSON.stringify(A.view.rooms.map(function (c) { return c.rooms.map(function (r) { return r.medal + (r.current ? "c" : ""); }); }));
    if (holder.dataset.sig === sig) return;
    holder.dataset.sig = sig;
    holder.textContent = "";
    var list = el("div", "chapter-list");
    A.view.rooms.forEach(function (c) {
      var sec = el("section", "chapter");
      var medalCount = c.rooms.filter(function(r) { return r.medal === 3; }).length;
      var h3 = el("h3", null, c.name + " (" + c.cleared + "/" + c.total + ")");
      if (medalCount > 0) {
        h3.appendChild(el("span", "medal-count", medalCount + " gold"));
      } else {
        h3.appendChild(el("span", "medal-count", "No gold yet"));
      }
      sec.appendChild(h3);
      sec.appendChild(el("p", "note", c.blurb));
      var ul = el("ul", "room-grid");
      c.rooms.forEach(function (r) {
        var li = el("li");
        var b = el("button", "room-btn" + (r.current ? " current" : ""));
        b.type = "button";
        b.dataset.testid = "robot-script-room-" + r.id;
        b.appendChild(el("span", "rname", r.number + ". " + r.name));
        var meta = el("span", "rmeta");
        if (r.medal) {
          meta.appendChild(medalNode(["", "bronze", "silver", "gold"][r.medal]));
          meta.appendChild(document.createTextNode(" " + r.best + " steps, par " + r.par));
        } else {
          meta.textContent = (A.view.difficulty === "hard" ? "Not cleared on Hard, par " : "Not cleared, par ") + r.par;
        }
        b.appendChild(meta);
        b.setAttribute("aria-label", r.number + ", " + r.name + ". " + (r.medal ? ["", "Bronze", "Silver", "Gold"][r.medal] + " medal, " + r.best + " steps, par " + r.par : ((A.view.difficulty === "hard" ? "Not cleared on Hard, par " : "Not cleared, par ") + r.par)) + (r.current ? ". Current room" : ""));
        b.addEventListener("click", function () {
          send({ action: "pick", room: r.id });
          $("rooms-panel").hidden = true;
          $("rooms-toggle-button").setAttribute("aria-expanded", "false");
          var anchor = $("room-panel");
          if (anchor.scrollIntoView) anchor.scrollIntoView({ block: "start" });
        });
        li.appendChild(b);
        ul.appendChild(li);
      });
      sec.appendChild(ul);
      list.appendChild(sec);
    });
    holder.appendChild(list);
  }

  // ---- goals, the workshop and the hint ladder ----------------------------------------------------------
  // R4-RSPC-8: the medals table, every room by its length against par (furthest over par first, uncleared last)
  var MEDAL_WORDS = ["none", "bronze", "silver", "gold"];
  function renderMedals() {
    var holder = $("medals-body");
    var rows = [];
    A.view.rooms.forEach(function (c) {
      c.rooms.forEach(function (r) { rows.push({ id: r.id, name: r.name, chapter: c.name, par: r.par, best: r.best, medal: r.medal, order: rows.length }); });
    });
    rows.sort(function (a, b) {
      var ao = a.best === null ? null : a.best - a.par;
      var bo = b.best === null ? null : b.best - b.par;
      if (ao === null || bo === null) return ao === bo ? a.order - b.order : (ao === null ? 1 : -1);
      return bo - ao || a.order - b.order;
    });
    var sig = A.view.difficulty + JSON.stringify(rows.map(function (r) { return [r.id, r.best, r.medal]; }));
    if (holder.dataset.sig === sig) return;
    holder.dataset.sig = sig;
    holder.textContent = "";
    var table = el("table", "medals-table");
    var head = el("tr");
    ["Room", "Best", "Par", "Over par", "Medal"].forEach(function (h) { var th = el("th", null, h); th.scope = "col"; head.appendChild(th); });
    var thead = el("thead");
    thead.appendChild(head);
    table.appendChild(thead);
    var body = el("tbody");
    rows.forEach(function (r) {
      var tr = el("tr");
      var th = el("th");
      th.scope = "row";
      var go = smallButton(r.name, "Go to " + r.name + " in " + r.chapter, "medals-go", function () {
        send({ action: "pick", room: r.id });
        $("medals-panel").hidden = true;
        $("medals-toggle-button").setAttribute("aria-expanded", "false");
        var anchor = $("room-panel");
        if (anchor.scrollIntoView) anchor.scrollIntoView({ block: "start" });
      });
      th.appendChild(go);
      tr.appendChild(th);
      tr.appendChild(el("td", null, r.best === null ? "-" : String(r.best)));
      tr.appendChild(el("td", null, String(r.par)));
      tr.appendChild(el("td", null, r.best === null ? "not cleared" : (r.best <= r.par ? "at par" : "+" + (r.best - r.par))));
      var m = el("td");
      if (r.medal) m.appendChild(medalNode(MEDAL_WORDS[r.medal])); else m.textContent = "none";
      tr.appendChild(m);
      body.appendChild(tr);
    });
    table.appendChild(body);
    holder.appendChild(table);
  }
  function renderGoalStrip() {
    var list = $("goals-list");
    var sig = A.view.goals.map(function (g) { return g.id + g.have; }).join(",");
    $("goals").hidden = false;
    if (list.dataset.sig === sig) return;
    list.dataset.sig = sig;
    list.textContent = "";
    if (!A.view.goals.length) { list.appendChild(el("li", null, "Every goal you can reach right now is done. The sandbox goal appears once the sandbox is open.")); return; }
    A.view.goals.forEach(function (g) {
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
  var knownEarned = null;
  function renderAchievements() {
    var list = $("achievements-list");
    var earnedNow = [];
    var sig = A.view.achievements.map(function (a) { return a.id + a.have; }).join(",");
    if (list.dataset.sig !== sig) {
      list.dataset.sig = sig;
      list.textContent = "";
      A.view.achievements.forEach(function (a) {
        var li = el("li", a.earned ? "earned" : "");
        li.setAttribute("data-achievement-id", a.id);
        li.appendChild(el("span", "tick", a.earned ? "Earned" : a.have + "/" + a.need));
        var name = el("strong", null, " " + a.label + " ");
        name.setAttribute("data-achievement-label", "");
        li.appendChild(name);
        li.appendChild(el("span", null, a.description));
        list.appendChild(li);
      });
    }
    A.view.achievements.forEach(function (a) { if (a.earned) earnedNow.push(a.id); });
    $("achievements-toggle-button").textContent = "Achievements (" + earnedNow.length + "/" + A.view.achievements.length + ")";
    if (knownEarned !== null) {
      earnedNow.filter(function (id) { return knownEarned.indexOf(id) === -1; }).forEach(function (id) {
        var a = A.view.achievements.filter(function (x) { return x.id === id; })[0];
        showToast("Achievement unlocked: " + a.label + ".");
        announce("Achievement unlocked: " + a.label + ".");
      });
    }
    knownEarned = earnedNow;
  }
  function renderWorkshop() {
    var s = A.view.scrap;
    var sig = s.svg + s.found;
    setText($("workshop-summary"), "Scrap has " + s.found + " of " + s.total + " parts back on, " + s.polished + " of them polished.");
    if ($("scrap-holder").dataset.sig !== sig) {
      $("scrap-holder").dataset.sig = sig;
      $("scrap-holder").innerHTML = s.svg;
      var zl = $("zone-list");
      zl.textContent = "";
      s.zones.forEach(function (z) {
        zl.appendChild(el("li", null, z.name + ": " + z.have + "/" + z.need + (z.finish ? " (" + z.finish + ")" : "")));
      });
      var pl = $("parts-list");
      pl.textContent = "";
      s.parts.forEach(function (p) {
        pl.appendChild(el("li", p.found ? "found" : "missing", p.found ? p.name + " (" + p.finish + "), from " + p.room_name : "Not found yet: from " + p.room_name));
      });
    }
  }
  function renderHints() {
    var h = A.view.hint;
    var btn = $("hint-button");
    btn.hidden = h.rung >= h.max;
    $("hint-limit").hidden = !(h.max < 3 && h.rung >= h.max);
    setText(btn, h.rung === 0 ? "Would you like a suggestion?" : (h.rung === 1 ? "Another hint" : "Another hint: the answer"));
    $("hint-nudge").hidden = !h.nudge;
    setText($("hint-nudge"), h.nudge ? "Nudge: " + h.nudge : "");
    $("hint-hint").hidden = !h.hint;
    setText($("hint-hint"), h.hint ? "Hint: " + h.hint : "");
    $("hint-answer").hidden = !h.answer;
    if (h.answer) setText($("hint-answer-lines"), h.answer.lines.join("\n"));
    document.dispatchEvent(new CustomEvent("robotScriptHints", { detail: h }));
  }

  // ---- render everything ----------------------------------------------------------------------------------
  function render() {
    renderAbout();
    var changed = A.view.room.id !== A.roomId;
    if (A.view.room.svg) {
      $("room-holder").innerHTML = A.view.room.svg;
      A.roomId = A.view.room.id;
      A.PALETTE_SIG = "";
      A.headDeg = A.view.room.start[2] * 90;
      invalidateRun();
    } else if (changed) {
      A.roomId = A.view.room.id;
    }
    renderStats();
    renderRoomHead();
    if (!A.play.trace) renderGoals("room-goals", A.view.room.goals);
    renderProgram();
    renderRooms();
    renderGoalStrip();
    renderAchievements();
    renderWorkshop();
    renderHints();
    syncPlayButtons();

    renderMedals();
  }

  // what the other parts use
  A.loadChangelog = loadChangelog;
  A.onRoomClick = onRoomClick;
  A.render = render;
  A.wirePanelToggle = wirePanelToggle;
})();
