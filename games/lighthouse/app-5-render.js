/* Lighthouse, part 5 of 6: year end, the station, the log, About the Light, achievements, changelog, phases, render() and sound. */
(function () {
  "use strict";

  var A = window.LighthouseApp;
  var $ = A.$, GAME_ID = A.GAME_ID, HUM_KEY = A.HUM_KEY, announce = A.announce, clockLabel = A.clockLabel,
      el = A.el, fact = A.fact, fillOnce = A.fillOnce, lsGet = A.lsGet, renderDay = A.renderDay,
      renderEvening = A.renderEvening, renderGoals = A.renderGoals, renderHud = A.renderHud,
      renderMorning = A.renderMorning, renderNight = A.renderNight, renderScene = A.renderScene,
      renderStory = A.renderStory, setText = A.setText, showToast = A.showToast;

  function renderYearEnd(v) {
    setText($("yearend-text"), "Forty nights are kept. The light is lit, the log is full and the harbour knows your name. You may close the book here or keep the light as long as you like.");
    var facts = $("yearend-facts");
    fillOnce(facts, JSON.stringify(v.meta) + v.reputation, function (holder) {
      holder.appendChild(fact("Nights kept", v.meta.nights_kept));
      holder.appendChild(fact("Ships passed safely", v.meta.ships_passed));
      holder.appendChild(fact("Ships turned back", v.meta.ships_delayed));
      holder.appendChild(fact("Ships helped off the shoals", v.meta.rescues));
      holder.appendChild(fact("Lamp-hours", v.meta.lamp_hours));
      holder.appendChild(fact("The Light", v.reputation + " (" + v.rep_title + ")"));
    });
  }
  function renderStation(v) {
    var list = $("structure-list");
    fillOnce(list, "structure", function (holder) {
      v.structure.forEach(function (p) {
        var li = el("li"); li.dataset.part = p.id;
        var ic = el("span", p.icon, "ico"); ic.setAttribute("aria-hidden", "true"); li.appendChild(ic);
        li.appendChild(el("span", p.label));
        var m = el("span", null, "meter"); m.appendChild(el("span", null, "meter-fill")); li.appendChild(m);
        li.appendChild(el("span", "", "part-num"));
        li.appendChild(el("span", "", "part-state"));
        holder.appendChild(li);
      });
    });
    v.structure.forEach(function (p, i) {
      var li = list.children[i];
      var m = li.querySelector(".meter");
      m.setAttribute("data-state", p.state);
      m.firstElementChild.style.setProperty("--pct", p.value + "%");
      setText(li.querySelector(".part-num"), p.value + "/100");
      setText(li.querySelector(".part-state"), { sound: "Sound", worn: "Worn", poor: "Poor", failing: "Failing" }[p.state]);
    });
    var sup = $("supplies-list");
    fillOnce(sup, JSON.stringify(v.supplies), function (holder) {
      v.supplies.forEach(function (s) {
        var li = el("li"); li.dataset.count = String(s.count);
        li.appendChild(el("span", s.label)); li.appendChild(el("strong", String(s.count)));
        holder.appendChild(li);
      });
    });
    setText($("station-extra"), "Comfort " + v.comfort + " of " + v.comfort_max + ". Upgrades fitted: " + (v.upgrades.filter(function (u) { return u.owned; }).map(function (u) { return u.name; }).join(", ") || "none yet") + ".");
  }

  var KIND_ICON = { ship: "\u2693", weather: "\u2601", incident: "\u26A0", damage: "\u2716", lamp: "\u2738", clock: "\u23F2", keeper: "\u270B", note: "\u2022", story: "\u270E", odd: "\u2754", hand: "\u270D" };
  function clauses(text) { return text.match(/[^,;.:]+[,;.:]?\s*/g) || [text]; }
  function renderLog(v) {
    var list = $("log-list");
    var sig = v.log.length + "|" + (v.log.length ? v.log[v.log.length - 1].text : "");
    $("log-empty").hidden = v.log.length > 0;
    var total = v.log.length;
    fillOnce(list, sig, function (holder) {
      v.log.slice().reverse().forEach(function (e, i) {
        var li = el("li");
        if (e.kind === "odd") li.className = "odd-detail"; else if (e.kind === "hand") li.className = "odd-detail hand"; else if (e.kind === "story") li.className = "story-line";
        li.appendChild(el("span", clockLabel(v.start_min, v.tick_minutes, e.t), "log-time"));
        var k = el("span", KIND_ICON[e.kind] || "\u2022", "log-kind"); k.setAttribute("aria-hidden", "true"); li.appendChild(k);
        var body = el("span", null, "log-text");
        var fresh = (e.kind === "odd" || e.kind === "hand" || e.kind === "story") && i === 0 && v.phase === "night" && total > A.lastLogCount && A.lastLogCount > 0;
        if (fresh) {
          li.classList.add("reveal");
          clauses(e.text).forEach(function (clause, n) { var s = el("span", clause, "clause"); s.style.setProperty("--i", String(n)); body.appendChild(s); });
        } else body.textContent = e.text;
        li.appendChild(body);
        holder.appendChild(li);
      });
    });
    // read out what is new (ships, trouble, weather, damage), never the lamp-lighting line
    if (v.phase === "night" && v.log.length > A.lastLogCount) {
      var fresh = v.log.slice(A.lastLogCount).filter(function (e) { return e.kind !== "keeper" || e.text.indexOf("patch") === -1; }).map(function (e) { return e.text; });
      if (fresh.length) announce(fresh.slice(-3).join(" "));
    }
    A.lastLogCount = v.phase === "night" ? v.log.length : 0;
  }

  var infoShown = false;
  function renderInfo(v) {
    if (infoShown) return;
    infoShown = true;
    $("info-page-framing").textContent = v.info.framing;
    var how = $("info-page-how");
    v.info.how.forEach(function (t) { how.appendChild(el("li", t)); });
    var list = $("info-page-sources");
    v.info.facts.forEach(function (fact) {
      var item = el("li", null, "info-page-source");
      item.appendChild(el("strong", fact.heading));
      item.appendChild(el("p", fact.fact, "info-page-framing"));
      item.appendChild(el("p", fact.tie_in, "info-page-tie-in"));
      var link = el("a", fact.source.title);
      link.href = fact.source.url; link.target = "_blank"; link.rel = "noopener noreferrer";
      var src = el("p", null, "info-page-source-note");
      src.appendChild(document.createTextNode("Source: "));
      src.appendChild(link);
      src.appendChild(document.createTextNode(", " + fact.source.publisher + ". Read on " + fact.source.date_read + "."));
      item.appendChild(src);
      list.appendChild(item);
    });
    $("info-page-note").textContent = v.story.note;
  }

  // ---- achievements, changelog, panels ----------------------------------------------------------------
  function renderAchievements(v) {
    var list = $("achievements-list");
    list.textContent = "";
    var earnedNow = [];
    (v.achievements || []).forEach(function (a) {
      var li = el("li", null, a.earned ? "earned" : "");
      li.setAttribute("data-achievement-id", a.id);
      li.appendChild(el("span", a.earned ? "Earned" : "Not yet", "tick"));
      var name = el("strong", " " + a.label + " "); name.setAttribute("data-achievement-label", "");
      li.appendChild(name);
      li.appendChild(el("span", a.description));
      list.appendChild(li);
      if (a.earned) earnedNow.push(a.id);
    });
    $("achievements-toggle-button").textContent = "Achievements (" + earnedNow.length + "/" + (v.achievements || []).length + ")";
    var keepingAll = (v.achievements || []).filter(function (x) { return !x.story; }), storyAll = (v.achievements || []).filter(function (x) { return x.story; });
    setText($("ach-summary"), "Keeping the light: " + keepingAll.filter(function (x) { return x.earned; }).length + " of " + keepingAll.length + ". The story layer: " + storyAll.filter(function (x) { return x.earned; }).length + " of " + storyAll.length + ". A Quiet year can reach every one of the first group.");
    if (A.knownEarned !== null) {
      earnedNow.filter(function (id) { return A.knownEarned.indexOf(id) === -1; }).forEach(function (id) {
        var a = v.achievements.filter(function (x) { return x.id === id; })[0];
        showToast("Achievement unlocked: " + a.label + ".");
      });
    }
    A.knownEarned = earnedNow;
  }
  function renderChangelog(entries) {
    var holder = $("changelog-entries");
    holder.textContent = "";
    entries.forEach(function (entry) {
      var row = el("article", null, "changelog-entry");
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
  function setToggleState(buttonId, panelId) { $(buttonId).setAttribute("aria-expanded", String(!$(panelId).hidden)); }
  function wirePanelToggle(buttonId, panelId) {
    $(buttonId).addEventListener("click", function () {
      $(panelId).hidden = !$(panelId).hidden;
      setToggleState(buttonId, panelId);
    });
  }

  // ---- phases -----------------------------------------------------------------------------------------
  var PHASE_PANELS = { evening: "evening-panel", night: "night-panel", morning: "morning-panel", day: "day-panel", yearend: "yearend-panel" };
  function renderPhase(v, userMoved) {
    Object.keys(PHASE_PANELS).forEach(function (p) { $(PHASE_PANELS[p]).hidden = v.phase !== p; });
    $("night-controls").hidden = v.phase !== "night";
    if (v.phase === "evening") renderEvening(v);
    if (v.phase === "night") renderNight(v);
    if (v.phase === "morning") renderMorning(v);
    if (v.phase === "day") renderDay(v);
    if (v.phase === "yearend") { renderYearEnd(v); A.recordDaily(v); }
    if (A.lastPhase !== null && A.lastPhase !== v.phase) {
      var panel = $(PHASE_PANELS[v.phase]);
      var heading = panel.querySelector("h2");
      heading.setAttribute("tabindex", "-1");
      if (userMoved) heading.focus({ preventScroll: false });
      announce({ evening: "Evening. Plan the night.", night: "The lamp is lit.", morning: "Dawn. The morning report is ready.", day: "Day. Choose your tasks.", yearend: "The year is complete." }[v.phase]);
    }
    A.lastPhase = v.phase;
  }

  function syncTime(v) {
    var ctl = window.NoyvjTime && window.NoyvjTime.get(GAME_ID);
    if (!ctl) return;
    if (v.phase === "night") ctl.release("planning"); else ctl.hold("planning");
  }

  function render(v, userMoved) {
    A.view = v;
    renderHud(v);
    renderGoals(v);
    renderInfo(v);
    renderStory(v);
    renderScene(v);
    renderPhase(v, userMoved);
    renderStation(v);
    renderLog(v);
    renderAchievements(v);
    syncTime(v);
    soundFor(v);
    A.renderSeed(v);
    // the phone touches (mobile-*.js) listen for this on document; the view is a plain object they must only read
    document.dispatchEvent(new CustomEvent("lighthouse-view", { detail: v }));
  }

  // A small door for the phone-only scripts (mobile-*.js): they may read the latest view and send ordinary engine
  // actions, the same ones the buttons send. They never touch the engine directly.
  window.lighthouseApi = {
    view: function () { return A.view; },
    send: function (request) { return A.send(request, false); },
    announce: announce,
    toast: showToast
  };

  // ---- sound (shared/sfx.js: generated in code, off unless the player turns it on, never the only signal) ----
  // A soft bell when a ship comes safely past, and (if the hum is not switched off) a faint bed under the night.
  var shipStates = {};
  function humPref() { return lsGet(HUM_KEY) !== "off"; }
  function soundFor(v) {
    if (!window.NoyvjSfx) return;
    var night = v.phase === "night";
    window.NoyvjSfx.play(night && humPref() ? "hum_start" : "hum_stop");
    if (!night) { shipStates = {}; return; }
    var rang = false;
    v.ships.forEach(function (s) {
      if (shipStates[s.id] && shipStates[s.id] !== "passed" && s.state === "passed") rang = true;
      shipStates[s.id] = s.state;
    });
    if (rang) window.NoyvjSfx.play("bell");
  }

  // what the other parts use (see the File map in CLAUDE.md)
  A.humPref = humPref; A.loadChangelog = loadChangelog; A.render = render; A.setToggleState = setToggleState;
  A.soundFor = soundFor; A.syncTime = syncTime; A.wirePanelToggle = wirePanelToggle;
})();
