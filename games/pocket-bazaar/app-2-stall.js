/* Pocket Bazaar, part 2 of 5: the customer queue, About and What's New, achievements, regulars, goals, decorations,
   the closed stall with its summary and the upgrade shop, and the stall seed. Glue only; every rule is in the engine. */
(function () {
  "use strict";

  var A = window.PocketBazaarApp;
  var $ = A.$, announce = A.announce, askThen = A.askThen, el = A.el, itemNode = A.itemNode, send = A.send,
      setText = A.setText, showMessage = A.showMessage, showToast = A.showToast;

  var cardEls = [];

  // ---- the queue -----------------------------------------------------------------------------
  function customerLabel(c) {
    var order = c.items.map(function (i) { return i.label + (i.done ? " (handed over)" : ""); }).join("; ");
    return c.name + ", " + c.kind + ". Wants " + order + ". " + c.patience + " of " + c.max + " beats of patience left. Pays " + c.pay + " coins.";
  }
  function renderQueue() {
    var holder = $("queue");
    var wants = A.selected !== null ? (A.view.deliverable[String(A.selected)] || []) : [];
    var sig = A.view.customers.map(function (c) { return c.name + c.items.map(function (i) { return i.done ? 1 : 0; }).join(""); }).join("|") + A.view.customers.length;
    if (holder.dataset.signature !== sig) {
      holder.textContent = "";
      holder.dataset.signature = sig;
      cardEls = [];
      for (var n = 0; n < A.view.day.window; n++) {
        var btn = el("button", "customer");
        btn.type = "button";
        btn.dataset.drop = "customer:" + n;
        btn.dataset.testid = "pocket-bazaar-customer-" + n;
        btn.addEventListener("click", (function (k) { return function () { if (!A.suppressClick) onCustomer(k); }; })(n));
        cardEls.push(btn);
        holder.appendChild(btn);
      }
    }
    cardEls.forEach(function (btn, n) {
      var c = A.view.customers[n];
      if (!c) {
        btn.className = "customer empty";
        btn.textContent = "";
        btn.dataset.sig = "";
        btn.disabled = false;
        btn.setAttribute("aria-label", "Empty spot at the stall");
        btn.appendChild(el("span", "note", A.view.day.waiting ? "" : "-"));
        return;
      }
      var low = c.patience * 4 <= c.max;
      var sigc = c.name + "|" + c.patience + "|" + c.items.map(function (i) { return i.done ? 1 : 0; }).join("");
      btn.className = "customer " + c.archetype + (low ? " low" : "") + (wants.indexOf(n) !== -1 ? " wants" : "");
      if (btn.dataset.sig !== sigc) {
        btn.dataset.sig = sigc;
        btn.textContent = "";
        var head = el("span", "cust-head");
        head.appendChild(el("span", "cust-face", c.name.charAt(0)));
        var names = el("span", null);
        names.style.minWidth = "0";
        names.appendChild(el("span", "cust-name", c.name));
        head.appendChild(names);
        btn.appendChild(head);
        btn.appendChild(el("span", "cust-kind", c.kind));
        var order = el("span", "cust-order");
        c.items.forEach(function (i) { order.appendChild(itemNode(i)); });
        btn.appendChild(order);
        btn.appendChild(el("span", "cust-want", "Wants it!"));
        var pat = el("span", "cust-patience");
        var bar = el("span", "bar");
        var fill = el("span", "bar-fill");
        fill.style.width = Math.max(0, Math.min(100, Math.round(100 * c.patience / c.max))) + "%";
        bar.appendChild(fill);
        pat.appendChild(bar);
        pat.appendChild(el("span", "beats", String(c.patience)));
        btn.appendChild(pat);
        // R4-PBMO-7 (phones, CSS): the patience as five large dots under the card plus the number of beats. A day's customers
        // wait 10 to 40 beats, so each dot stands for a fifth of the patience this customer started with.
        var dots = el("div", "patience-dots");
        dots.setAttribute("aria-hidden", "true");
        var lit = c.patience > 0 ? Math.max(1, Math.round(5 * c.patience / c.max)) : 0;
        for (var d = 0; d < 5; d++) dots.appendChild(el("span", "patience-dot" + (d < lit ? " filled" : "")));
        dots.appendChild(el("span", "patience-num", String(c.patience)));
        btn.appendChild(dots);
      }
      btn.setAttribute("aria-label", customerLabel(c) + (wants.indexOf(n) !== -1 ? " Would take the good you picked up." : ""));
    });
    var d = A.view.day;
    var line = $("queue-line");
    var f = A.view.festival;
    var sigq = f.id + "|" + d.waiting + "|" + d.left + "|" + (A.view.upcoming ? A.view.upcoming.name : "");
    if (line.dataset.sig !== sigq) {
      line.dataset.sig = sigq;
      line.textContent = "";
      var chip = el("span", "chip " + f.tone, f.name);
      chip.title = f.blurb;
      line.appendChild(chip);
      line.appendChild(document.createTextNode(" " + (d.waiting ? d.waiting + " more in line" : "last of the line") + (d.left ? " \u00B7 " + d.left + " left" : "")));
      if (A.view.upcoming) {
        var up = A.view.upcoming;
        line.appendChild(document.createTextNode(". Next up: " + up.name + " wants " + up.items.map(function (i) { return i.label; }).join(", ")));
      }
    }
    holder.setAttribute("aria-label", "Customers at the stall" + (d.waiting ? ", " + d.waiting + " more waiting in line" : ""));
  }

  function onCustomer(n) {
    if (!A.view || A.view.phase !== "open") return;
    if (A.selected === null) {
      var c = A.view.customers[n];
      if (c) showMessage(customerLabel(c), true);
      return;
    }
    send({ action: "deliver", from: A.selected, to: n });
  }

  // ---- panels: about, what's new ---------------------------------------------------------------
  function setToggleState(buttonId, panelId) { $(buttonId).setAttribute("aria-expanded", String(!$(panelId).hidden)); }
  function wirePanelToggle(buttonId, panelId) {
    $(buttonId).addEventListener("click", function () { $(panelId).hidden = !$(panelId).hidden; setToggleState(buttonId, panelId); });
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
  // The page sets window.CHANGELOG_JSON (the raw text of changelog.json) for shared/whats-new-banner.js.
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

  // ---- achievements, regulars, decorations ---------------------------------------------------------
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
    document.querySelector("#achievements-toggle-button").textContent = "Achievements (" + earnedNow.length + "/" + A.view.achievements.length + ")";
    if (knownEarned !== null) {
      earnedNow.filter(function (id) { return knownEarned.indexOf(id) === -1; }).forEach(function (id) {
        var a = A.view.achievements.filter(function (x) { return x.id === id; })[0];
        showToast("Achievement unlocked: " + a.label + ".");
        announce("Achievement unlocked: " + a.label + ".");
      });
    }
    knownEarned = earnedNow;
  }
  function renderRegulars() {
    var list = $("regulars-list");
    var sig = A.view.regulars.map(function (r) { return r.id + r.visits; }).join(",");
    setText($("regulars-summary"), "Regulars met: " + A.view.regulars_met + " of " + A.view.regulars.length + ". Three step up each day in a fixed rotation, so each one is back every fourth day.");
    if (list.dataset.sig === sig) return;
    list.dataset.sig = sig;
    list.textContent = "";
    A.view.regulars.forEach(function (r) {
      var li = el("li", "regular" + (r.visits ? "" : " unmet"));
      var head = el("p", "regular-head");
      head.appendChild(el("strong", null, r.visits ? r.name : "A regular you have not met"));
      if (r.visits) head.appendChild(el("span", "regular-role note", " " + r.role));
      li.appendChild(head);
      var pips = "\u25CF".repeat(r.level) + "\u25CB".repeat(3 - r.level);
      li.appendChild(el("p", "regular-bond", "Bond " + pips + " level " + r.level + " of 3, " + r.visits + (r.visits === 1 ? " visit" : " visits") + (r.next_at ? ", next level at " + r.next_at : ", complete")));
      r.lines.forEach(function (line) { li.appendChild(el("p", "regular-line", line)); });
      list.appendChild(li);
    });
  }
  function renderGoals() {
    var list = $("goals-list");
    list.textContent = "";
    A.view.goals.forEach(function (g) { list.appendChild(el("li", null, g.label + ": " + g.description + " (" + g.have + "/" + g.need + ")")); });
    $("goals").hidden = !A.view.goals.length;
  }
  function renderDecor() {
    var holder = $("decor-list");
    var sig = A.view.decor.map(function (s) { return s.items.map(function (i) { return (i.owned ? "o" : i.affordable ? "a" : "n") + (i.put ? "p" : ""); }).join(""); }).join("|");
    var out = [];
    A.view.decor.forEach(function (slot) {
      var put = slot.items.filter(function (i) { return i.put; })[0];
      if (put) out.push(put.name);
    });
    var owned = 0, total = 0;
    A.view.decor.forEach(function (s) { s.items.forEach(function (i) { total++; if (i.owned) owned++; }); });
    setText($("front-line"), "Stall front: " + (out.length ? out.join(", ") : "bare") + ". Decorations " + owned + "/" + total + ".");
    if (holder.dataset.sig === sig + "|" + A.view.coins) return;
    holder.dataset.sig = sig + "|" + A.view.coins;
    var openSlots = Array.prototype.map.call(holder.querySelectorAll("details[open]"), function (d) { return d.dataset.slot; });
    holder.textContent = "";
    A.view.decor.forEach(function (slot) {
      var det = el("details", "decor-slot");
      det.dataset.slot = slot.slot;
      if (openSlots.indexOf(slot.slot) !== -1) det.open = true;
      var ownedHere = slot.items.filter(function (i) { return i.owned; }).length;
      det.appendChild(el("summary", null, slot.label + " (" + ownedHere + "/" + slot.items.length + ")"));
      slot.items.forEach(function (i) {
        var row = el("div", "decor-item" + (i.owned ? " owned" : ""));
        row.appendChild(el("span", "decor-name", i.name));
        if (i.owned) {
          if (i.put) row.appendChild(el("span", "decor-state", "Out \u2713"));
          else {
            var b1 = el("button", null, "Put out");
            b1.type = "button";
            b1.addEventListener("click", function () { send({ action: "put_decor", id: i.id }); });
            row.appendChild(b1);
          }
        } else {
          var b2 = el("button", null, "Buy " + i.cost);
          b2.type = "button";
          b2.dataset.testid = "pocket-bazaar-decor-" + i.id;
          b2.setAttribute("aria-label", "Buy " + i.name + " for " + i.cost + " coins" + (i.affordable ? "" : ", you need " + (i.cost - A.view.coins) + " more"));
          if (!i.affordable) b2.setAttribute("aria-disabled", "true");
          b2.addEventListener("click", function () { send({ action: "buy_decor", id: i.id }); });
          row.appendChild(b2);
        }
        det.appendChild(row);
      });
      holder.appendChild(det);
    });
  }

  // ---- the closed stall ----------------------------------------------------------------------
  function renderClosed() {
    var sum = A.view.summary;
    $("summary").hidden = !sum;
    var heading = $("closed-heading");
    if (sum) {
      setText(heading, "Day " + sum.number + " is done");
      setText($("summary-stars"), "\u2605".repeat(sum.stars) + "\u2606".repeat(3 - sum.stars));
      $("summary-stars").setAttribute("aria-label", sum.stars + " of 3 stars");
      var list = $("summary-list");
      list.textContent = "";
      [["Served", sum.served + " of " + sum.total], ["Left unserved", String(sum.left)],
       ["Coins today", String(sum.coins)], ["Beats played", String(sum.beats)], ["Longest chain", String(sum.best_chain)], ["Renown", String(A.view.renown)]].forEach(function (row) {
        list.appendChild(el("dt", null, row[0]));
        list.appendChild(el("dd", null, row[1]));
      });
      setText($("closed-text"), "Your coins are saved. Open the next day whenever you like: there is no rush and nothing to miss.");
      setText($("summary-festival"), A.view.summary_festival ? "Festival: " + A.view.summary_festival.name : "");
      var bests = [];
      if (sum.new_bests.indexOf("combo") !== -1) bests.push("longest combo: " + sum.streak + " orders in a row");
      if (sum.new_bests.indexOf("day_coins") !== -1) bests.push("most coins in a day: " + sum.coins);
      var bestLine = $("summary-bests");
      bestLine.classList.toggle("just-improved", bests.length > 0);
      setText(bestLine, bests.length ? "New personal best: " + bests.join("; ") + "." : "Personal bests: longest combo " + A.view.best.combo + ", most coins in a day " + A.view.best.day_coins + ".");
      var unlockLine = $("summary-unlocks");
      unlockLine.hidden = !sum.unlocks.length;
      setText(unlockLine, sum.unlocks.length ? "New: " + sum.unlocks.map(function (u) { return A.view.unlock_names[u]; }).join(", ") + "!" : "");
    } else {
      setText(heading, A.view.days_played ? "The stall is closed" : "Welcome to your stall");
      setText($("closed-text"), A.view.days_played ? "Open the next day whenever you like." : "Customers will ask for goods. Open crates, merge them into better ones and hand them over. Nothing here runs on a clock.");
    }
    setText($("start-day-button"), "Open day " + A.view.next_day);
    var nu = A.view.next_unlock;
    setText($("renown-line"), "Renown " + A.view.renown + (nu ? ": " + (nu.need - A.view.renown) + " more opens " + nu.name + "." : ": everything is open."));
    var c = A.view.campaign;
    setText($("campaign-line"), c.mode === "campaign" ? "Market Days: day " + c.day + " of " + c.of : "Free Stall: day " + c.day + " (the campaign is done; days keep coming, slowly harder)");
    var f = A.view.festival;
    setText($("festival-label"), sum ? "Tomorrow's festival" : "Today's festival");
    setText($("festival-name"), f.name);
    var tone = $("festival-tone");
    setText(tone, f.tone === "tricky" ? "harder day" : "easier day");
    tone.className = "chip " + f.tone;
    setText($("festival-blurb"), f.blurb);
    renderShop();
    renderGoals();
    renderDecor();
  }

  function renderShop() {
    var list = $("shop-list");
    var sig = A.view.upgrades.map(function (u) { return u.id + (u.owned ? "o" : u.affordable ? "a" : "n"); }).join(",") + "|" + A.view.coins;
    var toggle = $("shop-toggle-button");
    setText(toggle, "Upgrades (" + A.view.upgrades.filter(function (u) { return u.owned; }).length + "/" + A.view.upgrades.length + ")");
    if (list.dataset.sig === sig) return;
    list.dataset.sig = sig;
    list.textContent = "";
    A.view.upgrades.forEach(function (u) {
      var li = el("li", "shop-item" + (u.owned ? " owned" : ""));
      li.appendChild(el("span", "shop-name", u.name));
      li.appendChild(el("span", "shop-blurb", u.blurb));
      if (u.owned) {
        li.appendChild(el("span", "shop-owned", "Owned \u2713"));
      } else {
        var btn = el("button", "shop-buy", "Buy " + u.cost);
        btn.type = "button";
        btn.dataset.testid = "pocket-bazaar-buy-" + u.id;
        btn.setAttribute("aria-label", "Buy " + u.name + " for " + u.cost + " coins" + (u.affordable ? "" : ", you need " + (u.cost - A.view.coins) + " more"));
        if (!u.affordable) btn.setAttribute("aria-disabled", "true");
        btn.addEventListener("click", function () { send({ action: "buy", id: u.id }); });
        li.appendChild(btn);
      }
      list.appendChild(li);
    });
  }

  // Z-1c: the stall's seed. The standard stall (the default, and every older save) shows POCKETBAZAAR-STAND; any other
  // valid seed text starts a fresh stall whose customers are drawn from the number derived from that text.
  var STANDARD_SEED = "POCKETBAZAAR-STAND";
  var seedCopy = null;
  function seedNumber(text) { return window.NoyvjSeed.rng(text).below(4294967296); }
  function startFromSeed(text) {
    A.selected = null;
    if (text === STANDARD_SEED) send({ action: "reset" });
    else send({ action: "reset", seed: seedNumber(text), seed_text: text });
    showMessage("A fresh stall begins from seed " + text + ".");
  }
  function mountSeeds() {
    if (!window.NoyvjSeed) return;
    seedCopy = window.NoyvjSeed.mountCopy("#seed-copy-slot", { seed: "", label: "This stall's seed" });
    window.NoyvjSeed.mountStart("#seed-start-slot", {
      game: "pocket-bazaar", buttonLabel: "Start a stall from this seed",
      onStart: function (text) {
        askThen("pocket-bazaar-reset", "Start a new stall from seed " + text + "? Your coins, upgrades, renown and personal bests will be erased.", "Erase it and start", function () { startFromSeed(text); });
      },
    });
  }
  function renderSeed() {
    if (!window.NoyvjSeed || !A.view) return;
    window.NoyvjSeed.set(A.view.seed_text || "");
    if (seedCopy) seedCopy.update(A.view.seed_text || "");
  }

  // what the other parts use
  A.loadChangelog = loadChangelog;
  A.mountSeeds = mountSeeds;
  A.renderAbout = renderAbout;
  A.renderAchievements = renderAchievements;
  A.renderClosed = renderClosed;
  A.renderQueue = renderQueue;
  A.renderRegulars = renderRegulars;
  A.renderSeed = renderSeed;
  A.wirePanelToggle = wirePanelToggle;
})();
