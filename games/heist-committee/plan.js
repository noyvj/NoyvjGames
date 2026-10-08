/* Heist Committee -- the plan screen: timeline grid, action tray, inspector, live checks.
   Two ways to place an action, both always supported: tap an action then tap a cell (or tap a cell then an action),
   or drag with a mouse/pen/finger from the tray. Arrow keys move over the grid, Enter places, Delete clears.
   No game logic here: every placement is sent to the engine, which validates it. */
(function () {
  "use strict";
  var HC = window.HC, $ = HC.$, el = HC.el;

  var armed = null;            // an action id the next tapped cell receives ("standby" uses standbyKind)
  var standbyKind = null;
  var selected = null;         // {lane, beat}
  var cursor = { lane: 0, beat: 0 };
  var justDragged = false;

  function planOf(view) { return view.plan; }
  function cellOf(view, lane, beat) { return planOf(view).lanes[lane][beat]; }
  function ownerBeat(view, lane, beat) {
    var c = cellOf(view, lane, beat);
    return c.role === "cont" ? c.of : beat;
  }
  function trayItem(view, id) { return view.tray.filter(function (t) { return t.id === id; })[0]; }

  // ---- timeline --------------------------------------------------------------------------------
  // mode "plan": interactive cells. mode "playback": read-only cells coloured by result (play.js passes `results`).
  HC.buildTimeline = function (container, view, mode, extra) {
    extra = extra || {};
    var plan = planOf(view), n = view.beats.length;
    container.textContent = "";
    container.style.setProperty("--beats", n);
    var pairBadge = {};
    plan.pairs.forEach(function (p) { pairBadge[p.lane + ":" + p.beat] = p; });
    var head = el("div", { role: "row" });
    head.appendChild(el("div", { "class": "beat-head", role: "columnheader" }, [el("b", { text: "Crew" })]));
    view.beats.forEach(function (b, i) {
      var cls = "beat-head";
      if (extra.now === i) cls += " now";
      else if (extra.now !== undefined && extra.now < i) cls += " future";
      var h = el("div", { "class": cls, role: "columnheader", title: b.note || null }, [el("b", { text: (i + 1) + ". " + b.name })]);
      b.tags.forEach(function (t) { h.appendChild(el("span", { "class": "beat-tag", text: t.icon + " " + t.label })); });
      head.appendChild(h);
    });
    container.appendChild(head);
    view.crew.forEach(function (c, lane) {
      var row = el("div", { role: "row" });
      var move = el("span", { "class": "lane-move" });
      if (mode === "plan") {
        move.appendChild(el("button", { type: "button", "aria-label": "Move " + c.short + " up a lane", disabled: lane === 0 ? true : null, "data-testid": "heist-lane-up-" + lane, text: "▲",
          onclick: function () { selected = null; HC.send({ action: "move_lane", lane: lane, dir: -1 }); } }));
        move.appendChild(el("button", { type: "button", "aria-label": "Move " + c.short + " down a lane", disabled: lane === view.crew.length - 1 ? true : null, "data-testid": "heist-lane-down-" + lane, text: "▼",
          onclick: function () { selected = null; HC.send({ action: "move_lane", lane: lane, dir: 1 }); } }));
      }
      row.appendChild(el("div", { "class": "lane-head", role: "rowheader" }, [
        HC.glyph(c),
        el("span", { "class": "lane-name" }, [el("b", { text: c.short }), el("span", { text: c.role_label }), el("span", { text: c.trait.name })]),
        mode === "plan" ? move : null]));
      for (var b = 0; b < n; b++) row.appendChild(buildCell(view, lane, b, mode, extra, pairBadge));
      container.appendChild(row);
    });
  };

  function cellLabel(view, lane, beat, c) {
    var crew = view.crew[lane], beatName = view.beats[beat].name;
    var base = crew.short + ", beat " + (beat + 1) + " " + beatName + ": ";
    if (c.role === "empty") return base + "empty";
    if (c.role === "cont") return base + "continues " + cellOf(view, lane, c.of).name;
    var s = c.name + (c.arg_label ? " for " + c.arg_label : "") + (c.span > 1 ? ", " + c.span + " beats" : "");
    if (c.odds) s += ", " + c.odds.label;
    return base + s;
  }

  function buildCell(view, lane, beat, mode, extra, pairBadge) {
    var c = cellOf(view, lane, beat);
    var cls = "cell " + (c.role === "empty" ? "empty" : c.role === "cont" ? "cont" : "filled");
    var inner = [];
    if (c.role === "start") {
      inner.push(el("span", { "class": "cell-icon", "aria-hidden": "true", text: c.icon }));
      inner.push(el("span", { "class": "cell-name", text: c.name }));
      if (c.arg) inner.push(el("span", { "class": "cell-sub", text: c.arg_icon + " " + c.arg_label }));
      else if (c.span > 1) inner.push(el("span", { "class": "cell-sub", text: c.span + " beats" }));
      if (c.odds && mode === "plan") inner.push(HC.oddsChip(c.odds));
    } else if (c.role === "cont") {
      inner.push(el("span", { "class": "cell-sub", text: "↳ " + cellOf(view, lane, c.of).name }));
    } else if (mode === "plan") {
      inner.push(el("span", { "class": "plus", "aria-hidden": "true", text: "+" }));
    }
    var res = extra.results && extra.results[lane + ":" + (c.role === "cont" ? c.of : beat)];
    if (res && c.role !== "empty") {
      cls += " res-" + res.outcome;
      if (c.role === "start" || res.show) {
        inner.push(el("span", { "class": "res", text: res.icon + " " + res.label }));
        if (res.shake) cls += " shake";
      }
    }
    var pair = pairBadge[lane + ":" + beat];
    var node = el(mode === "plan" ? "button" : "div", {
      type: mode === "plan" ? "button" : null, "class": cls, role: "gridcell", "data-lane": lane, "data-beat": beat,
      "data-testid": "heist-cell-" + lane + "-" + beat,
      "aria-label": cellLabel(view, lane, beat, c), tabindex: mode === "plan" ? ((cursor.lane === lane && cursor.beat === beat) ? "0" : "-1") : null
    }, inner);
    if (pair) {
      var bad = pair.value < 0;
      node.appendChild(el("span", { "class": "badge " + (bad ? "clash" : "help"), title: pair.text }, [bad ? "⚡ clash" : (pair.kind === "mentor" ? "🎓 coach" : "♥ friends")]));
    }
    if (mode === "plan") {
      if (selected && selected.lane === lane && selected.beat === ownerBeat(view, lane, beat)) node.classList.add("selected");
      if (armed) node.classList.add("armed-target");
      node.addEventListener("click", function () { onCell(lane, beat); });
      node.addEventListener("focus", function () { cursor = { lane: lane, beat: beat }; });
      if (c.role !== "empty") node.addEventListener("pointerdown", function (e) { startDrag(e, { cell: { lane: lane, beat: ownerBeat(view, lane, beat) } }); });
    }
    return node;
  }

  // ---- placing ---------------------------------------------------------------------------------
  function armedCell() { return armed === "standby" ? "standby:" + standbyKind : armed; }
  function place(lane, beat, cell) {
    var before = HC.view.plan.lanes[lane][beat].cell;
    var reply = HC.send({ action: "place", lane: lane, beat: beat, cell: cell });
    if (reply && reply.view && !reply.view.note) {
      var c = reply.view.plan.lanes[lane][beat];
      HC.announce("Placed " + (c.name || "action") + " for " + reply.view.crew[lane].short + " in beat " + (beat + 1));
    }
    return before;
  }

  function onCell(lane, beat) {
    if (justDragged) { justDragged = false; return; }
    var view = HC.view;
    beat = ownerBeat(view, lane, beat);
    cursor = { lane: lane, beat: beat };
    if (armed) { selected = null; place(lane, beat, armedCell()); return; }
    if (selected && selected.lane === lane && selected.beat === beat) selected = null;
    else selected = { lane: lane, beat: beat };
    renderPlan(view);
    var cellNode = document.querySelector('.cell[data-lane="' + lane + '"][data-beat="' + beat + '"]');
    if (cellNode) cellNode.focus();
  }

  function onTray(id) {
    var view = HC.view, item = trayItem(view, id);
    if (!item) return;
    if (selected) {
      var s = selected;
      if (id === "standby" && !standbyKind) standbyKind = defaultKind(view);
      selected = null;
      armed = null;
      place(s.lane, s.beat, id === "standby" ? "standby:" + standbyKind : id);
      return;
    }
    armed = armed === id ? null : id;
    if (armed === "standby" && !standbyKind) standbyKind = defaultKind(view);
    renderPlan(view);
  }

  function defaultKind(view) {
    var scouted = view.plan.cover.filter(function (k) { return k.scouted; });
    return (scouted[0] || view.plan.cover[0]).id;
  }

  function disarm() { armed = null; selected = null; renderPlan(HC.view); }

  // ---- drag (pointer events) -----------------------------------------------------------------------
  var drag = null;
  function startDrag(e, source) {
    if (e.button !== undefined && e.button !== 0) return;
    drag = { source: source, x: e.clientX, y: e.clientY, active: false, ghost: null, over: null, id: e.pointerId };
  }
  function cellUnder(x, y) {
    var node = document.elementFromPoint(x, y);
    return node && node.closest ? node.closest(".cell[data-lane]") : null;
  }
  document.addEventListener("pointermove", function (e) {
    if (!drag || e.pointerId !== drag.id) return;
    if (!drag.active) {
      if (Math.abs(e.clientX - drag.x) + Math.abs(e.clientY - drag.y) < 9) return;
      drag.active = true;
      var label = drag.source.tray ? trayItem(HC.view, drag.source.tray).name : cellOf(HC.view, drag.source.cell.lane, drag.source.cell.beat).name;
      drag.ghost = el("div", { "class": "drag-ghost", text: label });
      document.body.appendChild(drag.ghost);
    }
    e.preventDefault();
    drag.ghost.style.left = (e.clientX + 12) + "px";
    drag.ghost.style.top = (e.clientY + 12) + "px";
    var over = cellUnder(e.clientX, e.clientY);
    if (drag.over && drag.over !== over) drag.over.classList.remove("drop-over");
    if (over) over.classList.add("drop-over");
    drag.over = over;
  }, { passive: false });
  function endDrag(e, cancelled) {
    if (!drag || (e && e.pointerId !== drag.id)) return;
    var d = drag;
    drag = null;
    if (!d.active) return;
    justDragged = true;
    setTimeout(function () { justDragged = false; }, 60);
    if (d.ghost) d.ghost.remove();
    if (d.over) d.over.classList.remove("drop-over");
    if (cancelled || !d.over) return;
    var lane = +d.over.dataset.lane, beat = ownerBeat(HC.view, lane, +d.over.dataset.beat);
    if (d.source.tray) {
      var id = d.source.tray;
      if (id === "standby" && !standbyKind) standbyKind = defaultKind(HC.view);
      place(lane, beat, id === "standby" ? "standby:" + standbyKind : id);
    } else {
      var from = d.source.cell;
      if (from.lane !== lane || from.beat !== beat) HC.send({ action: "move_cell", lane: from.lane, beat: from.beat, to_lane: lane, to_beat: beat });
    }
    selected = null;
  }
  document.addEventListener("pointerup", function (e) { endDrag(e, false); });
  document.addEventListener("pointercancel", function (e) { endDrag(e, true); });

  // ---- tray / inspector / checks ---------------------------------------------------------------
  function renderTray(view) {
    var sig = JSON.stringify([view.tray.map(function (t) { return t.id; }), armed, standbyKind, view.plan.cover]);
    HC.fillOnce($("tray"), sig, function (box) {
      view.tray.forEach(function (t, i) {
        var sub = t.kind === "standby" ? "hold one trouble" : t.kind === "improvise" ? "wing it" :
          t.skill + (t.difficulty ? " vs " + t.difficulty : "") + " · " + t.duration + (t.duration > 1 ? " beats" : " beat");
        var btn = el("button", { type: "button", "class": "tray-item", "aria-pressed": armed === t.id ? "true" : "false", title: t.blurb, "data-testid": "heist-tray-" + t.id,
          "aria-keyshortcuts": i < 9 ? String(i + 1) : null,
          onclick: function () { if (justDragged) { justDragged = false; return; } onTray(t.id); } }, [
          el("span", { "class": "t-name", text: t.icon + " " + t.name }),
          el("span", { "class": "t-sub", text: sub })]);
        btn.style.touchAction = "none";
        btn.addEventListener("pointerdown", function (e) { startDrag(e, { tray: t.id }); });
        box.appendChild(btn);
      });
    });
    var row = $("cover-row");
    row.hidden = armed !== "standby";
    HC.fillOnce(row, JSON.stringify([view.plan.cover, standbyKind]), function (box) {
      box.appendChild(el("span", { "class": "note", text: "Stand by for:" }));
      view.plan.cover.forEach(function (k) {
        box.appendChild(el("button", { type: "button", "aria-pressed": standbyKind === k.id ? "true" : "false", "data-testid": "heist-cover-" + k.id,
          text: k.icon + " " + k.label + (k.scouted ? " (scouted)" : ""),
          onclick: function () { standbyKind = k.id; renderPlan(HC.view); } }));
      });
    });
    var hint = "";
    if (armed) {
      var item = trayItem(view, armed);
      hint = "Placing " + item.name + (armed === "standby" ? " (" + view.plan.cover.filter(function (k) { return k.id === standbyKind; })[0].label + ")" : "") +
        (item.duration > 1 ? " (" + item.duration + " beats)" : "") + ": tap or press Enter on cells, or drag it. Press Escape to put it down.";
    } else if (selected) {
      hint = "Cell selected: pick an action to put there, or Remove it below.";
    } else {
      hint = "Pick an action, then tap cells. Or tap a cell first, then pick the action. You can drag too.";
    }
    HC.setText($("armed-hint"), hint);
  }

  function renderInspector(view) {
    var box = $("inspector-body");
    var parts = [];
    if (!selected) {
      parts.push(el("p", { "class": "note", text: "Tap a cell to see who is there, what they are good at and why the odds are what they are." }));
    } else {
      var lane = selected.lane, beat = selected.beat, crew = view.crew[lane], c = cellOf(view, lane, beat);
      var head = el("div", { "class": "row" }, [HC.glyph(crew), el("div", {}, [
        el("h4", { text: crew.name + ", beat " + (beat + 1) + ": " + view.beats[beat].name }),
        el("span", { "class": "tier", text: crew.role_icon + " " + crew.role_label })])]);
      parts.push(head);
      parts.push(el("div", {}, crew.skills.map(HC.skillLine)));
      var chips = el("div", {}, [HC.traitChip(crew.trait, "Trait")]);
      chips.appendChild(crew.quirk ? HC.traitChip(crew.quirk, "Quirk") : el("span", { "class": "chip quirk-hidden", text: "? Quirk: unknown" }));
      parts.push(chips);
      if (c.role === "start") {
        parts.push(el("h4", { text: c.icon + " " + c.name + (c.arg_label ? " (" + c.arg_label + ")" : "") }));
        if (c.odds) {
          parts.push(el("p", {}, ["Odds: ", HC.oddsChip(c.odds), " (score " + (c.odds.margin > 0 ? "+" : "") + c.odds.margin + ")"]));
          var ul = el("ul", {});
          c.odds.parts.forEach(function (p) { ul.appendChild(el("li", { text: p[0] + ": " + (p[1] > 0 ? "+" : "") + p[1] })); });
          parts.push(ul);
          parts.push(el("p", { "class": "note", text: "The score is the sum. Solid is 1 or more, Risky is 0, Long shot is below 0. Trouble in the heist itself can still push it down." }));
        } else if (c.kind === "standby") {
          parts.push(el("p", { "class": "note", text: "Absorbs the first " + c.arg_label.toLowerCase() + " trouble this beat, and does nothing else." }));
        } else if (c.kind === "improvise") {
          parts.push(el("p", { "class": "note", text: "Tries to handle any trouble that lands this beat, using their best skill. A gamble." }));
        }
        parts.push(el("button", { type: "button", "data-testid": "heist-remove", text: "Remove this action",
          onclick: function () { selected = null; HC.send({ action: "clear", lane: lane, beat: beat }); } }));
      } else {
        parts.push(el("p", { "class": "note", text: "Empty. Pick an action to put here." }));
      }
    }
    var sig = JSON.stringify([selected, parts.length, view.plan.lanes]) + JSON.stringify(view.crew.map(function (c) { return c.quirk_known; }));
    HC.fillOnce(box, sig, function (b) { parts.forEach(function (p) { b.appendChild(p); }); });
  }

  function renderChecks(view) {
    var marks = { ok: "✓", warn: "⚠", info: "ℹ" };
    var words = { ok: "Covered", warn: "Warning", info: "Note" };
    HC.fillOnce($("check-list"), JSON.stringify(view.plan.messages), function (ul) {
      view.plan.messages.forEach(function (m) {
        ul.appendChild(el("li", { "class": m.level }, [el("span", { "class": "mark", "aria-hidden": "true", text: marks[m.level] }),
          el("span", {}, [el("span", { "class": "sr-only", text: words[m.level] + ": " }), m.text])]));
      });
    });
  }

  function renderPlan(view, focusTo) {
    if (!view || view.phase !== "plan") return;
    if (armed && !trayItem(view, armed)) armed = null;
    var focused = focusTo || (document.activeElement && document.activeElement.dataset && document.activeElement.dataset.lane !== undefined ?
      { lane: +document.activeElement.dataset.lane, beat: +document.activeElement.dataset.beat } : null);
    $("plan-intro").textContent = view.target.intro + " Fill the timeline, check the list on the right, then start the heist. You can undo as much as you like until you do.";
    HC.buildTimeline($("timeline"), view, "plan");
    renderTray(view);
    renderInspector(view);
    renderChecks(view);
    HC.fillOnce($("sidebar-scout"), JSON.stringify([view.scout, view.cash]), function (box) { box.appendChild(HC.scoutPanel(view, true)); });
    $("undo-button").disabled = !view.plan.can_undo;
    $("redo-button").disabled = !view.plan.can_redo;
    if (focused) {
      var node = document.querySelector('.cell[data-lane="' + focused.lane + '"][data-beat="' + focused.beat + '"]');
      if (node) node.focus();
    }
  }
  HC.renderers.plan = renderPlan;
  HC.planState = function () { return { armed: armed, selected: selected, cursor: cursor }; };

  // ---- keyboard --------------------------------------------------------------------------------
  function moveCursor(dLane, dBeat) {
    var view = HC.view, n = view.beats.length;
    cursor = { lane: Math.max(0, Math.min(4, cursor.lane + dLane)), beat: Math.max(0, Math.min(n - 1, cursor.beat + dBeat)) };
    renderPlan(view, { lane: cursor.lane, beat: cursor.beat });
  }
  document.addEventListener("keydown", function (e) {
    var view = HC.view;
    if (!view || view.phase !== "plan" || e.altKey) return;
    var tag = e.target && e.target.tagName;
    if (/^(INPUT|TEXTAREA|SELECT)$/.test(tag || "")) return;
    var inGrid = e.target && e.target.closest && e.target.closest("#timeline");
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z") {
      e.preventDefault();
      HC.send({ action: e.shiftKey ? "redo" : "undo" });
      return;
    }
    if (e.ctrlKey || e.metaKey) return;
    if (e.key === "Escape") { if (armed || selected) { e.preventDefault(); disarm(); } return; }
    if (inGrid) {
      var step = { ArrowLeft: [0, -1], ArrowRight: [0, 1], ArrowUp: [-1, 0], ArrowDown: [1, 0] }[e.key];
      if (step) { e.preventDefault(); moveCursor(step[0], step[1]); return; }
      if (e.key === "Delete" || e.key === "Backspace") {
        e.preventDefault();
        selected = null;
        HC.send({ action: "clear", lane: cursor.lane, beat: ownerBeat(view, cursor.lane, cursor.beat) });
        return;
      }
      if (e.key.toLowerCase() === "s" && !e.shiftKey) {
        e.preventDefault();
        if (!standbyKind) standbyKind = defaultKind(view);
        place(cursor.lane, ownerBeat(view, cursor.lane, cursor.beat), "standby:" + standbyKind);
        return;
      }
    }
    if (/^[1-9]$/.test(e.key) && view.tray[+e.key - 1]) {
      e.preventDefault();
      onTray(view.tray[+e.key - 1].id);
    }
  });

  // ---- buttons -----------------------------------------------------------------------------------
  $("undo-button").addEventListener("click", function () { HC.send({ action: "undo" }); });
  $("redo-button").addEventListener("click", function () { HC.send({ action: "redo" }); });
  $("clear-plan-button").addEventListener("click", function () {
    HC.ask("heist-clear-plan", "Clear the whole plan? You can undo it.", "Clear it", function () { selected = null; HC.send({ action: "clear_plan" }); });
  });
  $("abandon-button").addEventListener("click", function () {
    HC.ask("heist-abandon", "Abandon this job? The crew keep their fees and you get nothing.", "Abandon", function () { armed = null; selected = null; HC.send({ action: "abandon" }); });
  });
  $("start-heist-button").addEventListener("click", function () {
    HC.ask("heist-start", "Start the heist? The plan is fixed once it begins.", "Start Heist", function () { armed = null; selected = null; HC.send({ action: "start_heist" }); });
  });
})();
