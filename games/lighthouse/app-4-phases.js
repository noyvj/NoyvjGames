/* Lighthouse, part 4 of 6: the evening plan, the night controls, the morning report, the day tasks and the supply order. */
(function () {
  "use strict";

  var A = window.LighthouseApp;
  var $ = A.$, GAME_ID = A.GAME_ID, clockLabel = A.clockLabel, el = A.el, fillOnce = A.fillOnce, isOff = A.isOff,
      meter = A.meter, plural = A.plural, setEnabled = A.setEnabled, setText = A.setText;

  // ---- the evening -----------------------------------------------------------------------------------
  var LEVEL_IDS = ["dim", "standard", "bright", "storm"];
  function buildPlan(v) {
    fillOnce($("plan-blocks"), "plan", function (holder) {
      v.blocks.forEach(function (name, b) {
        var row = el("div", null, "block-row");
        row.appendChild(el("span", name, "block-name"));
        row.id = "plan-block-" + b;
        var seg = el("div", null, "seg");
        seg.setAttribute("role", "group");
        seg.setAttribute("aria-label", "Lamp level for " + name.toLowerCase());
        v.level_options.forEach(function (opt) {
          var btn = el("button", opt.label);
          btn.type = "button";
          btn.dataset.level = opt.id;
          btn.dataset.block = String(b);
          btn.appendChild(el("small", "reach " + opt.reach + ", oil " + opt.burn.toFixed(1) + "/tick"));
          btn.addEventListener("click", function () {
            var levels = A.view.plan.levels.slice();
            levels[b] = opt.id;
            A.send({ action: "plan", levels: levels });
          });
          seg.appendChild(btn);
        });
        row.appendChild(seg);
        holder.appendChild(row);
      });
    });
    v.plan.levels.forEach(function (lvl, b) {
      $("plan-block-" + b).querySelectorAll("button").forEach(function (btn) {
        btn.setAttribute("aria-pressed", String(btn.dataset.level === lvl));
      });
    });
  }

  function blockSizes(length) {
    var ends = [0, 1, 2].map(function (b) { return b < 2 ? Math.floor((length * (b + 1) + 2) / 3) : length; });
    return [ends[0], ends[1] - ends[0], ends[2] - ends[1]];
  }
  function estimate(v) {
    var sizes = blockSizes(v.length), total = 0, dryAt = null, left = v.oil, tick = 0;
    for (var b = 0; b < 3; b++) {
      var burn = v.level_options[LEVEL_IDS.indexOf(v.plan.levels[b])].burn;
      for (var i = 0; i < sizes[b]; i++) {
        var rate = v.plan.ration && total >= v.plan.ration ? v.level_options[0].burn : burn;
        left -= rate; total += rate; tick++;
        if (left <= 0 && dryAt === null) dryAt = tick;
      }
    }
    return { total: Math.round(total), dryAt: dryAt };
  }

  function renderEvening(v) {
    setText($("evening-night"), String(v.night));
    setText($("evening-note"), (v.festival ? "Tonight is the Lamplighters' Supper: every boat stays in harbour. " : "") + v.season + ", night " + v.night_in_season + " of 10. The night is " + (v.length * v.tick_minutes / 60).toFixed(1).replace(".0", "") + " hours long.");
    // barometer
    var f = v.forecast, labels = ["Calm", "Unsettled", "Rough", "Dangerous"];
    var scale = $("barometer-scale");
    fillOnce(scale, "scale", function (holder) {
      labels.forEach(function (name) {
        var cell = el("div", null, "scale-cell");
        cell.appendChild(el("span", "", "scale-mark"));
        cell.appendChild(document.createTextNode(name));
        holder.appendChild(cell);
      });
    });
    Array.prototype.forEach.call(scale.children, function (cell, i) {
      var inside = i >= f.lo && i <= f.hi;
      cell.dataset.in = String(inside);
      cell.firstElementChild.textContent = inside ? "●" : "○";
    });
    scale.setAttribute("aria-label", "Barometer: " + (f.narrow ? f.lo_label : f.lo_label + " to " + f.hi_label));
    setText($("barometer-text"), (f.narrow ? "The glass points to " + f.lo_label.toLowerCase() + " weather." : "The glass says " + f.lo_label.toLowerCase() + " to " + f.hi_label.toLowerCase() + ".") +
      (f.vane ? " With the wind vane it is right about 19 nights in 20." : " It is right about 9 nights in 10, so treat it as a hint."));
    // harbour board
    var list = $("board-list");
    fillOnce(list, JSON.stringify(v.notice) + v.plan.levels.join(), function (holder) {
      v.notice.forEach(function (n) {
        var li = el("li");
        li.appendChild(el("span", n.icon, "ico"));
        li.lastChild.setAttribute("aria-hidden", "true");
        li.appendChild(el("strong", n.label + " " + n.name));
        if (n.who_name) li.appendChild(el("span", n.who_name, "sailor-note"));
        if (n.chalked) li.className = "odd-detail";
        li.appendChild(el("span", "about " + n.at + " (" + n.block_label.toLowerCase() + "), needs reach " + n.need + " or more" + (n.chalked ? " (chalked on the board)" : ""), "board-detail"));
        holder.appendChild(li);
      });
      if (!v.notice.length) holder.appendChild(el("li", "No ships are expected tonight."));
    });
    setText($("board-note"), "The weather takes reach away: haze 1, fog 2, squall 2, storm 3. A cracked lantern glass takes 1 or 2 more.");
    buildPlan(v);
    var est = estimate(v);
    var msg = "About " + est.total + " measures of oil if the plan holds (you have " + Math.round(v.oil) + ").";
    if (est.dryAt !== null) msg += " That is not enough: the lamp would go out about " + clockLabel(v.start_min, v.tick_minutes, est.dryAt) + ".";
    setText($("plan-estimate"), msg);
    $("ration-select").value = String(v.plan.ration);
    if ($("ration-select").value !== String(v.plan.ration)) {
      var opt = el("option", v.plan.ration + " measures"); opt.value = String(v.plan.ration); $("ration-select").appendChild(opt); $("ration-select").value = String(v.plan.ration);
    }
    ["wind", "watch", "repair"].forEach(function (t) { $("task-" + t).checked = Boolean(v.plan.tasks[t]); });
    var focus = $("focus-select");
    fillOnce(focus, "focus", function (holder) {
      var worst = el("option", "the worst part first"); worst.value = "worst"; holder.appendChild(worst);
      v.structure.forEach(function (p) { var o = el("option", "the " + p.label.toLowerCase()); o.value = p.id; holder.appendChild(o); });
    });
    focus.value = v.plan.focus;
    var notes = [];
    if (v.boat.tonight) notes.push(v.structure[3].value < 30 ? "The mail boat is due tonight but the dock is too damaged for her to tie up." : "The mail boat is due tonight with your order.");
    if (v.supplies[0].count === 0) notes.push("The larder is empty: you will go hungry tomorrow.");
    if (v.structure[1].value < 50) notes.push("The lantern glass is cracked, so the beam is shorter than the table says.");
    if (v.structure[0].value < 40) notes.push("The tower is shaken: the clockwork will run down faster.");
    if (v.tired) notes.push("You are tired. Rest in the day if you can.");
    setText($("evening-reminders"), notes.join(" "));
  }

  // ---- the night -------------------------------------------------------------------------------------
  function renderNight(v) {
    fillOnce($("lamp-controls"), "lamp", function (holder) {
      v.level_options.forEach(function (opt, i) {
        var btn = el("button", (i + 1) + " " + opt.label);
        btn.type = "button";
        btn.dataset.level = opt.id;
        btn.title = "Reach " + opt.reach + ", oil " + opt.burn.toFixed(1) + " per tick (key " + (i + 1) + ")";
        btn.addEventListener("click", function () { if (!isOff(btn)) A.send({ action: "level", level: opt.id }); });
        holder.appendChild(btn);
      });
    });
    Array.prototype.forEach.call($("lamp-controls").children, function (btn) {
      btn.setAttribute("aria-pressed", String(v.beam.level === btn.dataset.level));
      setEnabled(btn, v.oil > 0);
    });
    var pct = v.clockwork.left / v.clockwork.max * 100;
    meter("clock-meter", pct, v.beam.stopped ? "empty" : pct < 25 ? "low" : "ok");
    setText($("clock-state"), v.beam.stopped ? "Stopped: the beam holds a fixed cone" : Math.round(v.clockwork.left) + " of " + v.clockwork.max + " ticks left");
    setEnabled("wind-button", v.clockwork.left < v.clockwork.max - 1);
    $("incident-row").hidden = !v.incident;
    if (v.incident) setText($("incident-text"), v.incident.text + " (" + plural(v.incident.left, "tick") + " before it costs you)");
    var patch = $("patch-select");
    var damaged = v.structure.filter(function (p) { return p.value < 100; });
    fillOnce(patch, damaged.map(function (p) { return p.id; }).join(), function (holder) {
      damaged.forEach(function (p) { var o = el("option", p.label); o.value = p.id; holder.appendChild(o); });
      if (!damaged.length) { var none = el("option", "Nothing needs patching"); none.value = ""; holder.appendChild(none); }
    });
    setEnabled("patch-button", damaged.length > 0);
    // ships
    var ships = $("ship-list");
    fillOnce(ships, JSON.stringify(v.ships.map(function (s) { return [s.id, s.state, s.arrived, s.lit, s.present]; })), function (holder) {
      v.ships.forEach(function (s) {
        var li = el("li");
        li.dataset.lit = String(s.lit);
        var icon = el("span", s.icon, "ico"); icon.setAttribute("aria-hidden", "true");
        li.appendChild(icon);
        li.appendChild(el("strong", s.label + " " + s.name));
        if (s.who_name) li.appendChild(el("span", s.who_name, "sailor-note"));
        var status = s.state !== "pending" ? { passed: "Passed safely", delayed: "Turned back", damaged: "On the shoals, safe" }[s.state] :
          s.present ? (s.lit ? "Near the rock, in the beam" : "Near the rock, looking for the light") : "Expected about " + s.at;
        var st = el("span", status, "ship-state");
        st.dataset.state = s.state === "pending" && s.present ? "pending" : s.state;
        li.appendChild(st);
        holder.appendChild(li);
      });
      if (!v.ships.length) holder.appendChild(el("li", "No ships tonight."));
    });
    setText($("night-note"), v.beam.lit ? "" : "The lamp is out. Ships cannot see you until morning.");
  }

  // ---- the morning -----------------------------------------------------------------------------------
  function fact(label, value) {
    var d = el("div"); d.appendChild(el("dt", label)); d.appendChild(el("dd", String(value))); return d;
  }
  function renderMorning(v) {
    var r = v.report;
    if (!r) return;
    setText($("morning-night"), String(r.night));
    setText($("report-summary"), r.summary);
    var ships = $("report-ships");
    fillOnce(ships, JSON.stringify(r.ships), function (holder) {
      r.ships.forEach(function (s) {
        var li = el("li");
        li.appendChild(el("strong", s.name));
        var st = el("span", { passed: "Passed safely", delayed: "Turned back to wait", damaged: "Ran on the shoals; everyone is safe", unrecorded: "Never came" }[s.outcome], "ship-state");
        st.dataset.state = s.outcome;
        li.appendChild(st);
        holder.appendChild(li);
      });
      if (!r.ships.length) holder.appendChild(el("li", "No ships came by."));
    });
    var facts = $("report-facts");
    fillOnce(facts, JSON.stringify([r.lamp_hours, r.oil_used, r.damage, r.rep, r.salvage, r.incidents]), function (holder) {
      holder.appendChild(fact("Lamp-hours", r.lamp_hours));
      holder.appendChild(fact("Oil burnt", r.oil_used));
      holder.appendChild(fact("Damage taken", r.damage));
      holder.appendChild(fact("Reputation", (r.rep >= 0 ? "+" : "") + r.rep));
      holder.appendChild(fact("Salvage", "+" + r.salvage));
      holder.appendChild(fact("Troubles", r.incidents));
    });
    var lines = $("report-lines");
    fillOnce(lines, JSON.stringify(r.lines), function (holder) { r.lines.forEach(function (t) { holder.appendChild(el("li", t)); }); });
    var beats = $("report-beats");
    fillOnce(beats, JSON.stringify(r.beats || []) + String(v.story.on), function (h) {
      (r.beats || []).forEach(function (b) {
        var odd = b.kind === "odd" || b.kind === "moment" || b.kind === "trifle";
        h.appendChild(el("li", b.text, odd ? "odd-detail" : "story-line"));
      });
    });
    beats.hidden = !v.story.on || !(r.beats || []).length;
    var post = $("report-letters");
    var postText = (r.letters || []).map(function (l) { return "A letter from " + l.from_name + " has come: " + l.subject + "."; }).concat((r.met || []).map(function (n) { return "You have met " + n + "."; })).join(" ");
    setText(post, postText); post.hidden = !postText || !v.story.on;
    setText($("report-delivery"), v.delivery ? v.delivery.text : (v.boat.due ? "The mail boat could not land and will come again." : ""));
  }

  // ---- the day ---------------------------------------------------------------------------------------
  function costText(cost) { return Object.keys(cost).map(function (k) { return cost[k] + " " + k; }).join(" + "); }
  function canAfford(v, cost) { return Object.keys(cost).every(function (k) { return v.supplies.filter(function (s) { return s.id === k; })[0].count >= cost[k]; }); }
  function renderDay(v) {
    setText($("day-night"), String(v.night));
    setText($("day-slots"), "Daylight left: " + v.day.slots + " of " + v.day.max_slots + " tasks");
    var list = $("repair-list");
    fillOnce(list, "repair", function (holder) {
      v.structure.forEach(function (p) {
        var li = el("li"); li.dataset.part = p.id;
        var name = el("span"); name.appendChild(el("strong", p.icon + " " + p.label)); name.appendChild(el("span", "", "cost"));
        li.appendChild(name);
        var m = el("span", null, "meter"); m.appendChild(el("span", null, "meter-fill")); li.appendChild(m);
        var btn = el("button", "Mend"); btn.type = "button";
        btn.addEventListener("click", function () { if (!isOff(btn)) A.daySend({ action: "day", task: "repair", part: p.id }); });
        li.appendChild(btn);
        holder.appendChild(li);
      });
    });
    v.structure.forEach(function (p, i) {
      var li = list.children[i];
      var cost = v.day.repair_cost[p.id];
      meter(li.querySelector(".meter").id || (li.querySelector(".meter").id = "repair-meter-" + p.id), p.value, p.state === "failing" ? "empty" : p.state === "poor" ? "low" : "ok");
      setText(li.querySelector(".cost"), " " + p.value + "/100 (" + costText(cost) + ")" + (v.day.repaired.indexOf(p.id) !== -1 ? " mended today" : ""));
      var btn = li.querySelector("button");
      setEnabled(btn, v.day.slots > 0 && p.value < 100 && canAfford(v, cost));
    });
    var tasks = $("task-buttons");
    fillOnce(tasks, "tasks", function (holder) {
      [["rest", "Sleep in the day"], ["tidy", "Tidy the room"], ["beachcomb", "Walk the tideline"], ["garden", "Tend the greenhouse box"]].forEach(function (t) {
        var btn = el("button", t[1]); btn.type = "button"; btn.id = "task-" + t[0] + "-button";
        btn.addEventListener("click", function () { if (!isOff(btn)) A.daySend({ action: "day", task: t[0] }); });
        holder.appendChild(btn);
      });
    });
    setEnabled("task-rest-button", v.day.slots > 0 && v.energy < 100);
    setEnabled("task-tidy-button", v.day.slots > 0 && v.comfort < v.comfort_max);
    setEnabled("task-beachcomb-button", v.day.slots > 0);
    $("task-garden-button").hidden = !v.day.greenhouse;
    setEnabled("task-garden-button", v.day.slots > 0);
    $("task-rest-button").title = "Restores about " + v.day.rest_gain + " energy";
    $("task-tidy-button").title = "Comfort " + v.comfort + " of " + v.comfort_max + ": a cosier room restores more when you sleep";
    $("task-beachcomb-button").title = "Once a day: +1 salvage and a useful find";
    var rescue = $("rescue-list");
    fillOnce(rescue, JSON.stringify(v.waiting) + String(canAfford(v, v.day.rescue_cost)) + v.day.slots, function (holder) {
      v.waiting.forEach(function (w) {
        var li = el("li");
        li.appendChild(el("span", w.name + " is waiting on the shoals, all hands safe (" + costText(v.day.rescue_cost) + ")"));
        li.appendChild(el("span"));
        var btn = el("button", "Help her off"); btn.type = "button";
        setEnabled(btn, v.day.slots > 0 && canAfford(v, v.day.rescue_cost));
        btn.addEventListener("click", function () { if (!isOff(btn)) A.daySend({ action: "day", task: "rescue", id: w.id }); });
        li.appendChild(btn);
        holder.appendChild(li);
      });
    });
    setText($("workshop-salvage"), String(v.salvage));
    var ups = $("upgrade-list");
    fillOnce(ups, JSON.stringify(v.upgrades.map(function (u) { return [u.id, u.owned, u.affordable]; })), function (holder) {
      v.upgrades.forEach(function (u) {
        var li = el("li"); li.dataset.owned = String(u.owned);
        var info = el("span"); info.appendChild(el("span", u.name, "up-name")); info.appendChild(document.createTextNode(" " + (u.owned ? "(fitted) " : "(" + u.cost + " salvage) ") + u.text));
        li.appendChild(info);
        var btn = el("button", u.owned ? "Fitted" : "Buy"); btn.type = "button";
        setEnabled(btn, !u.owned && u.affordable);
        btn.addEventListener("click", function () {
          if (isOff(btn)) return;
          var go = function () { A.daySend({ action: "upgrade", id: u.id }); };
          if (u.rare && window.ConfirmDialog) window.ConfirmDialog.ask({ id: GAME_ID + "-upgrade-" + u.id, message: "Spend " + u.cost + " salvage on " + u.name + "?", confirmLabel: "Fit it", onConfirm: go });
          else go();
        });
        li.appendChild(btn);
        holder.appendChild(li);
      });
    });
    renderOrder(v);
    var f = v.forecast;
    setText($("day-forecast"), (f.narrow ? f.lo_label : f.lo_label + " to " + f.hi_label) + " expected tonight (night " + v.forecast.night + "). " + (v.notice.length ? plural(v.notice.length, "ship") + " listed on the harbour board." : "No ships listed."));
    setText($("boat-text"), v.boat.due ? "The mail boat is still due: she waits offshore and comes again tomorrow night." :
      "The mail boat is next expected on night " + v.boat.next_night + ". She brings " + v.boat.crates + " crates, split the way you order them.");
  }

  var ORDER_LABELS = { oil: "Oil", food: "Food", timber: "Timber", tar: "Tar", glass: "Glass" };
  function renderOrder(v) {
    var order = A.orderDraft || v.boat.order;
    var holder = $("order-grid");
    fillOnce(holder, "order", function (h) {
      Object.keys(ORDER_LABELS).forEach(function (k) {
        var cell = el("div", null, "order-cell"); cell.dataset.kind = k;
        cell.appendChild(el("strong", ORDER_LABELS[k]));
        var step = el("span", null, "stepper");
        var minus = el("button", "−"); minus.type = "button"; minus.setAttribute("aria-label", "One crate less " + ORDER_LABELS[k].toLowerCase());
        var out = el("output", "0"); out.setAttribute("aria-live", "polite");
        var plus = el("button", "+"); plus.type = "button"; plus.setAttribute("aria-label", "One crate more " + ORDER_LABELS[k].toLowerCase());
        minus.addEventListener("click", function () { if (!isOff(minus)) changeOrder(k, -1); });
        plus.addEventListener("click", function () { if (!isOff(plus)) changeOrder(k, 1); });
        step.appendChild(minus); step.appendChild(out); step.appendChild(plus);
        cell.appendChild(step);
        cell.appendChild(el("span", "", "note"));
        h.appendChild(cell);
      });
    });
    var total = 0;
    Object.keys(ORDER_LABELS).forEach(function (k) { total += order[k]; });
    Array.prototype.forEach.call(holder.children, function (cell) {
      var k = cell.dataset.kind;
      setText(cell.querySelector("output"), String(order[k]));
      setText(cell.querySelector(".note"), "= " + order[k] * v.boat.units[k] + (k === "oil" ? " oil" : " " + k));
      var btns = cell.querySelectorAll("button");
      setEnabled(btns[0], order[k] > 0);
      setEnabled(btns[1], total < v.boat.crates);
    });
    setText($("order-total"), total === v.boat.crates ? "Crates ordered: " + total + " of " + v.boat.crates + "." : "Crates ordered: " + total + " of " + v.boat.crates + ". Place " + plural(v.boat.crates - total, "more crate") + " to send the order.");
  }
  function changeOrder(kind, delta) {
    var order = Object.assign({}, A.orderDraft || A.view.boat.order);
    order[kind] += delta;
    var total = 0;
    Object.keys(order).forEach(function (k) { total += order[k]; });
    if (order[kind] < 0 || total > A.view.boat.crates) return;
    if (total === A.view.boat.crates) { A.orderDraft = null; A.send({ action: "order", order: order }); }
    else { A.orderDraft = order; renderOrder(A.view); }
  }

  // what the other parts use (see the File map in CLAUDE.md)
  A.LEVEL_IDS = LEVEL_IDS; A.fact = fact; A.renderDay = renderDay; A.renderEvening = renderEvening;
  A.renderMorning = renderMorning; A.renderNight = renderNight;
})();
