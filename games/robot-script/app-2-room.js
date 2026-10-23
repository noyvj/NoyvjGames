/* Robot Script, part 2 of 5: the stats, the room drawing (applyFrame, markNode) and run playback (Run, Step, Skip,
   Rewind, breakpoints and the result card). Glue only; every rule is in the engine. */
(function () {
  "use strict";

  var A = window.RobotScriptApp;
  var $ = A.$, announce = A.announce, el = A.el, plural = A.plural, send = A.send, setText = A.setText,
      SPEED_MS = A.SPEED_MS, TILE = A.TILE;

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
    bumpStat("stat-rooms", A.view.totals.cleared + "/" + A.view.totals.rooms);
    bumpStat("stat-gold", A.view.totals.gold);
    bumpStat("stat-parts", A.view.scrap.found + "/" + A.view.scrap.total);
    bumpStat("stat-runs", A.view.tally.runs);
    bumpStat("stat-written", A.view.tally.written);
    bumpStat("stat-hints", A.view.tally.hints);
    bumpStat("stat-sbx-runs", A.view.tally.sbx_runs);
    bumpStat("stat-sbx-tiles", A.view.tally.sbx_tiles);
    bumpStat("stat-silver", A.view.totals.silver);
    bumpStat("stat-bronze", A.view.totals.bronze);
    bumpStat("stat-halts", A.view.tally.halts);
  }

  // ---- the room --------------------------------------------------------------------------------------
  function medalNode(name) {
    return el("span", "medal medal-" + name, name.charAt(0).toUpperCase() + name.slice(1));
  }
  function renderGoals(listId, goals) {
    var ul = $(listId);
    ul.textContent = "";
    goals.forEach(function (g) {
      var li = el("li", g.met ? "met" : "", g.label + (g.met ? " (done)" : ""));
      ul.appendChild(li);
    });
  }
  function renderRoomHead() {
    var r = A.view.room;
    setText($("room-chapter"), r.chapter + " · room " + r.number + " of " + r.of);
    setText($("room-heading"), r.name);
    setText($("room-intro"), r.intro);
    var words = $("words-lines");
    var sig = r.id;
    if (words.dataset.sig !== sig) {
      words.dataset.sig = sig;
      words.textContent = "";
      r.words.lines.forEach(function (l) { words.appendChild(el("li", null, l)); });
      $("words-rows").textContent = "";
      r.words.rows.forEach(function (l) { $("words-rows").appendChild(el("li", null, l)); });
    }
  }
  function svgEl() { return $("room-holder").querySelector("svg"); }
  function applyFrame(f, jump) {
    var svg = svgEl();
    if (!svg) return;
    var robot = svg.querySelector("#rs-robot");
    var mod = ((A.headDeg % 360) + 360) % 360;
    var delta = (((f[2] * 90 - mod) + 540) % 360) - 180;
    A.headDeg += delta;
    if (jump) robot.classList.add("jump");
    robot.style.transform = "translate(" + (f[0] * TILE + TILE / 2) + "px," + (f[1] * TILE + TILE / 2) + "px) rotate(" + A.headDeg + "deg)";
    if (jump) { void robot.getBoundingClientRect(); robot.classList.remove("jump"); }
    svg.querySelector("#rs-carry").classList.toggle("on", f[3] >= 0);
    Array.prototype.forEach.call(svg.querySelectorAll(".rs-part"), function (p) {
      var i = Number(p.id.replace("rs-part-", ""));
      p.classList.toggle("gone", !((f[4] >> i) & 1));
    });
    Array.prototype.forEach.call(svg.querySelectorAll(".rs-fill"), function (p) {
      var i = Number(p.id.replace("rs-fill-", ""));
      p.classList.toggle("on", Boolean((f[5] >> i) & 1));
    });
    Array.prototype.forEach.call(svg.querySelectorAll(".rs-switch"), function (p) {
      var i = Number(p.id.replace("rs-lamp-", ""));
      p.classList.toggle("lit", Boolean((f[6] >> i) & 1));
    });
    Array.prototype.forEach.call(svg.querySelectorAll(".rs-door"), function (p) {
      p.classList.toggle("open", Boolean((f[6] >> Number(p.dataset.sw)) & 1));
    });
  }
  function initialFrame() {
    var s = A.view.room.start;
    var n = svgEl().querySelectorAll(".rs-part").length;
    return [s[0], s[1], s[2], -1, (1 << n) - 1, 0, 0, ""];
  }
  function markNode(addr, stopped) {
    Array.prototype.forEach.call(document.querySelectorAll(".node.running, .node.stopped"), function (n) { n.classList.remove("running", "stopped"); });
    if (!addr) return;
    var node = document.querySelector('[data-a="' + addr + '"]');
    if (!node) return;
    node.classList.add(stopped ? "stopped" : "running");
    if (node.scrollIntoView) node.scrollIntoView({ block: "nearest" });
  }

  // ---- playback --------------------------------------------------------------------------------------
  function speedMs() {
    var reduced = document.documentElement.getAttribute("data-reduced-motion") === "true";
    if (reduced) return 0;
    var custom = window.robotScriptPlaybackDelay;
    if (custom !== undefined && typeof custom === "number") return custom;
    var name = document.documentElement.getAttribute("data-run-speed") || "normal";
    var base = SPEED_MS[name] === undefined ? SPEED_MS.normal : SPEED_MS[name];
    return Math.max(1, Math.floor(base / A.playbackSpeed));
  }
  function stopTimer() {
    if (A.play.timer) { clearInterval(A.play.timer); A.play.timer = null; }
    A.play.running = false;
  }
  function updatePlaybackSpeed(delay) {
    if (!A.play.running || !A.play.trace) return;
    stopTimer();
    A.play.timer = setInterval(advance, delay);
    syncPlayButtons();
  }
  function stepFrame(dir) {
    if (!A.play.trace || !A.play.frames) return;
    stopTimer();
    var nextI = A.play.i + dir;
    if (nextI < 0) nextI = 0;
    if (nextI >= A.play.frames.length) nextI = A.play.frames.length - 1;
    var last = A.play.frames.length - 1;
    if (nextI < last) hideResult();
    showFrameAt(nextI, true);
    if (nextI === last) finishRun();
    syncPlayButtons();
  }
  function hideResult() {
    $("result-card").hidden = true;
    setText($("run-line"), "");
  }
  function invalidateRun() {
    stopTimer();
    A.play.trace = null;
    A.play.frames = null;
    A.play.i = 0;
    A.play.bpAt = -1;
    markNode("", false);
    hideResult();
    if (A.view && svgEl()) {
      applyFrame(initialFrame(), true);
      renderGoals("room-goals", A.view.room.goals);
    }
    syncPlayButtons();
  }
  function syncPlayButtons() {
    var run = $("run-button");
    var live = A.play.trace && A.play.i < A.play.frames.length - 1;
    setText(run, A.play.running ? "Pause" : (live ? "Resume" : (A.play.trace ? "Run again" : "Run")));
    $("step-button").disabled = false;
    $("skip-button").disabled = !live;
    $("rewind-button").disabled = !A.play.trace || A.play.i === 0;
  }
  function showFrameAt(i, jump) {
    A.play.i = i;
    var f = A.play.frames[i];
    applyFrame(f, jump);
    if (i > 0) RobotHaptics.tick();
    var last = i === A.play.frames.length - 1;
    markNode(i === 0 ? "" : f[7], last && A.play.trace.status !== "cleared" && A.play.trace.status !== "short" && Boolean(A.play.trace.at));
    var done = Math.min(i, A.play.trace.actions);
    setText($("run-line"), done ? "Step " + done + " of " + A.play.trace.actions : "");
  }
  function breakpointSet() { return window.ROBOT_SCRIPT_breakpoints || new Set(); }
  function advance() {
    if (!A.play.frames) return;
    // R4-RSPC-3: a run that is playing pauses before a step the player marked in the gutter (pc.js keeps the set of
    // addresses); Resume or Step carries on past it, and stepping by hand never stops at one.
    if (A.play.running && A.play.i < A.play.frames.length - 1 && A.play.bpAt !== A.play.i + 1) {
      var next = A.play.frames[A.play.i + 1];
      if (next[7] && breakpointSet().has(next[7])) {
        A.play.bpAt = A.play.i + 1;
        stopTimer();
        markNode(next[7], false);
        setText($("run-line"), "Paused at a breakpoint. Resume or Step to go on.");
        announce("Paused at a breakpoint.");
        syncPlayButtons();
        return;
      }
    }
    if (A.play.i >= A.play.frames.length - 1) { finishRun(); return; }
    showFrameAt(A.play.i + 1, false);
    if (A.play.i >= A.play.frames.length - 1) finishRun();
  }
  function finishRun() {
    stopTimer();
    var t = A.play.trace;
    if (!t) return;
    var halted = t.status === "halt" || t.status === "loop";
    if (halted && t.at) markNode(t.at, true);
    if (t.sandbox) {
      var sc = $("result-card");
      sc.hidden = false;
      sc.className = "result-card " + (halted ? "stopped" : "cleared");
      setText($("result-title"), halted ? "The robot stopped" : "The run is over");
      $("result-medal").textContent = "";
      setText($("result-text"), t.message);
      $("result-goals").textContent = "";
      $("next-button").hidden = true;
      $("scrap-line").hidden = true;
      $("part-line").hidden = true;
      announce(t.message);
      syncPlayButtons();
      return;
    }
    renderGoals("room-goals", t.goals);
    var card = $("result-card");
    card.hidden = false;
    card.className = "result-card " + (t.cleared ? "cleared" : "stopped");
    var medal = $("result-medal");
    medal.textContent = "";
    if (t.cleared) {
      setText($("result-title"), "Room cleared");
      medal.appendChild(medalNode(t.medal_name));
      var ladder = t.difficulty === "easy" ? " on Easy" : t.difficulty === "hard" ? " on Hard" : "";
      medal.appendChild(document.createTextNode(" " + plural(t.size, "step", "steps") + " (par " + t.par + ")" + ladder));
      var more = t.medal === 3 ? "That is gold." : t.medal === 2 ? "Gold needs " + t.gold + " or fewer steps." : "Silver needs " + t.silver + " or fewer steps, gold needs " + t.gold + ".";
      if (t.difficulty !== "normal" && t.normal_medal_name !== "none" && t.normal_medal_name) more += " On Normal this room stands at " + t.normal_medal_name + ".";
      if (t.note) more = t.note + " " + more;
      setText($("result-text"), (t.new_best ? "A new best for this room" + ladder + ". " : "Your best here" + ladder + " is " + t.best + ". ") + more);
      RobotHaptics.buzz();
    } else if (halted) {
      setText($("result-title"), "The robot stopped");
      setText($("result-text"), t.message + " Nothing is lost: change the list and run it again.");
    } else {
      setText($("result-title"), "Not finished yet");
      setText($("result-text"), t.message);
    }
    renderGoals("result-goals", t.goals);
    var sl = $("scrap-line");
    sl.hidden = !(t.cleared && t.scrap_line);
    setText(sl, t.scrap_line ? "Scrap: " + t.scrap_line : "");
    var pl = $("part-line");
    pl.hidden = !(t.part);
    setText(pl, t.part ? (t.part.first ? "Part found for Scrap: " : "Scrap's part: ") + t.part.name + " (" + t.part.finish + ")." : "");
    var next = $("next-button");
    next.hidden = !(t.cleared && t.next);
    if (t.next) setText(next, "Next room: " + t.next_name);
    announce(t.cleared ? "Room cleared, " + t.medal_name + " medal." : t.message);
    syncPlayButtons();
  }
  function startPlay(trace, autoplay, i) {
    stopTimer();
    A.play.trace = trace;
    A.play.frames = trace.frames;
    A.play.i = i !== undefined ? i : 0;
    if (i === undefined) A.play.bpAt = -1;      // resuming keeps the breakpoint it just stopped at, so it is passed once
    hideResult();
    applyFrame(A.play.frames[A.play.i], true);
    syncPlayButtons();
    var ms = speedMs();
    if (!autoplay) return;
    if (ms === 0 && breakpointSet().size === 0) { showFrameAt(A.play.frames.length - 1, true); finishRun(); return; }
    A.play.running = true;
    A.play.timer = setInterval(advance, Math.max(1, ms));
    syncPlayButtons();
  }
  function onRun() {
    if (A.play.running) { stopTimer(); syncPlayButtons(); return; }
    if (A.play.trace && A.play.i < A.play.frames.length - 1) {
      startPlay(A.play.trace, true, A.play.i);
      return;
    }
    var result = send({ action: "run" });
    if (result && result.run) startPlay(result.run, true);
  }
  function onStep() {
    if (A.play.running) { stopTimer(); }
    if (!A.play.trace || A.play.i >= A.play.frames.length - 1) {
      var result = send({ action: "run" });
      if (!result || !result.run) return;
      startPlay(result.run, false);
    }
    advance();
    syncPlayButtons();
  }
  function onSkip() {
    if (!A.play.trace) return;
    stopTimer();
    showFrameAt(A.play.frames.length - 1, true);
    finishRun();
  }
  function onRewind() {
    if (!A.play.trace) return;
    stopTimer();
    hideResult();
    renderGoals("room-goals", A.view.room.goals);
    showFrameAt(0, true);
    syncPlayButtons();
  }

  // what the other parts use
  A.invalidateRun = invalidateRun;
  A.medalNode = medalNode;
  A.onRewind = onRewind;
  A.onRun = onRun;
  A.onSkip = onSkip;
  A.onStep = onStep;
  A.renderGoals = renderGoals;
  A.renderRoomHead = renderRoomHead;
  A.renderStats = renderStats;
  A.speedMs = speedMs;
  A.stepFrame = stepFrame;
  A.svgEl = svgEl;
  A.syncPlayButtons = syncPlayButtons;
  A.updatePlaybackSpeed = updatePlaybackSpeed;
})();
