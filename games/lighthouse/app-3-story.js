/* Lighthouse, part 3 of 6: letters, sailors, gifts, the keeper's room, the notebook and the off-chart lights. */
(function () {
  "use strict";

  var A = window.LighthouseApp;
  var $ = A.$, announce = A.announce, el = A.el, fillOnce = A.fillOnce, plural = A.plural, setText = A.setText,
      showToast = A.showToast, svgEl = A.svgEl;
  A.knownUnread = null;

  // ---- letters, sailors, gifts, the room ------------------------------------------------------------------
  function roomPart(tag, attrs, cls) { var n = svgEl(tag, attrs); if (cls) n.setAttribute("class", cls); return n; }
  var GIFT_DRAW = {
    brass_key: function (x, y) { var g = svgEl("g"); g.appendChild(roomPart("circle", { cx: x, cy: y - 10, r: 5 }, "room-accent")); g.appendChild(roomPart("path", { d: "M" + x + " " + (y - 5) + " V" + y + " M" + x + " " + (y - 2) + " h4" }, "room-ink")); return g; },
    odd_cork: function (x, y) { var g = svgEl("g"); g.appendChild(roomPart("rect", { x: x - 5, y: y - 11, width: 10, height: 11, rx: 2 }, "room-accent")); return g; },
    pressed_flower: function (x, y) { var g = svgEl("g"); g.appendChild(roomPart("path", { d: "M" + x + " " + y + " V" + (y - 11) }, "room-ink")); g.appendChild(roomPart("circle", { cx: x, cy: y - 13, r: 4 }, "room-accent")); return g; },
    lens_cloth: function (x, y) { var g = svgEl("g"); g.appendChild(roomPart("path", { d: "M" + (x - 8) + " " + y + " q4 -12 8 -4 q4 -8 8 4 z" }, "room-fill")); return g; },
    tin_fish: function (x, y) { var g = svgEl("g"); g.appendChild(roomPart("rect", { x: x - 9, y: y - 9, width: 18, height: 9, rx: 2 }, "room-fill")); g.appendChild(roomPart("path", { d: "M" + (x - 4) + " " + (y - 5) + " q4 -4 8 0 q-4 4 -8 0" }, "room-ink")); return g; },
    walnuts: function (x, y) { var g = svgEl("g"); g.appendChild(roomPart("rect", { x: x - 6, y: y - 16, width: 12, height: 16, rx: 3 }, "room-fill")); g.appendChild(roomPart("rect", { x: x - 7, y: y - 19, width: 14, height: 4, rx: 1 }, "room-accent")); return g; },
    biscuits: function (x, y) { var g = svgEl("g"); g.appendChild(roomPart("rect", { x: x - 12, y: y - 12, width: 24, height: 12, rx: 2 }, "room-accent")); g.appendChild(roomPart("path", { d: "M" + (x - 12) + " " + (y - 8) + " h24" }, "room-ink")); return g; },
    chart: function (x, y) { var g = svgEl("g"); g.appendChild(roomPart("rect", { x: x - 18, y: y, width: 36, height: 26 }, "room-fill")); g.appendChild(roomPart("path", { d: "M" + (x - 12) + " " + (y + 18) + " q6 -14 12 -4 t12 -6" }, "room-ink")); g.appendChild(roomPart("circle", { cx: x + 6, cy: y + 8, r: 2 }, "room-accent")); return g; },
    pip_drawing: function (x, y) { var g = svgEl("g"); g.appendChild(roomPart("rect", { x: x - 14, y: y, width: 28, height: 28 }, "room-fill")); g.appendChild(roomPart("path", { d: "M" + (x - 4) + " " + (y + 24) + " L" + (x - 2) + " " + (y + 6) + " h4 L" + (x + 4) + " " + (y + 24) + " z M" + (x - 1) + " " + (y + 10) + " h2 M" + (x - 1) + " " + (y + 14) + " h2 M" + (x - 1) + " " + (y + 18) + " h2" }, "room-ink")); return g; },
    postcard: function (x, y) { var g = svgEl("g"); g.appendChild(roomPart("rect", { x: x - 12, y: y, width: 24, height: 17 }, "room-fill")); g.appendChild(roomPart("path", { d: "M" + (x - 7) + " " + (y + 8) + " h8 M" + (x - 7) + " " + (y + 12) + " h12" }, "room-ink")); return g; },
    stair_shell: function (x, y) { var g = svgEl("g"); g.appendChild(roomPart("path", { d: "M" + x + " " + y + " v14" }, "room-ink")); g.appendChild(roomPart("path", { d: "M" + (x - 6) + " " + (y + 26) + " q0 -12 6 -12 q6 0 6 12 q-6 4 -12 0 z M" + (x - 3) + " " + (y + 22) + " h6" }, "room-accent")); return g; },
  };
  var SLOT_POS = { shelf: function (i) { return [100 + i * 30, 88]; }, table: function (i) { return [168 + i * 34, 150]; }, wall: function (i) { return [70 + i * 52, 22]; }, window: function () { return [276, 36]; }, floor: function (i) { return [60 + i * 30, 185]; } };

  function drawRoom(v) {
    var svg = $("room-svg");
    svg.textContent = "";
    svg.appendChild(roomPart("rect", { x: 0, y: 0, width: 360, height: 140 }, "room-wall"));
    svg.appendChild(roomPart("rect", { x: 0, y: 140, width: 360, height: 60 }, "room-floor"));
    var win = roomPart("g");
    win.appendChild(roomPart("rect", { x: 240, y: 16, width: 72, height: 70 }, "room-fill"));
    win.appendChild(roomPart("path", { d: "M276 16 V86 M240 51 H312" }, "room-ink"));
    svg.appendChild(win);
    svg.appendChild(roomPart("path", { d: "M80 92 H210" }, "room-ink"));                               // the shelf
    svg.appendChild(roomPart("path", { d: "M150 150 H300 M158 150 V196 M292 150 V196" }, "room-ink"));   // the table
    svg.appendChild(roomPart("path", { d: "M20 150 H64 M20 150 V196 M64 150 V196 M20 128 H64 V150" }, "room-ink"));   // the bed
    var chair = roomPart("g", { id: "room-chair", class: "room-chair" });
    chair.appendChild(roomPart("path", { d: "M318 190 V160 H338 V190 M318 160 V140 H328" }, "room-ink"));
    svg.appendChild(chair);
    var ro = v.story.room_odd || { chair: 0, cup: false };
    var chairG = $("room-chair");
    if (ro.chair) chairG.setAttribute("transform", "rotate(" + ro.chair + " 328 175)");
    if (ro.cup) {
      var cup = roomPart("g", { class: "odd-detail" });
      cup.appendChild(roomPart("path", { d: "M222 150 v-12 h14 v12 z M236 142 q6 0 0 6" }, "room-fill"));
      svg.appendChild(cup);
    }
    var used = {};
    v.story.room.forEach(function (gid) {
      var g = v.story.gifts.filter(function (x) { return x.id === gid; })[0];
      if (!g || !GIFT_DRAW[gid]) return;
      var i = used[g.slot] = (used[g.slot] || 0) + 1;
      var pos = SLOT_POS[g.slot](i - 1);
      var node = GIFT_DRAW[gid](pos[0], pos[1]);
      var t = svgEl("title"); t.textContent = g.name; node.insertBefore(t, node.firstChild);
      svg.appendChild(node);
    });
    $("room-svg").setAttribute("aria-label", "The keeper's room" + (v.story.room.length ? ", with " + v.story.room.length + " keepsake" + (v.story.room.length === 1 ? "" : "s") : ", still bare"));
  }

  function letterItem(l) {
    var li = el("li"); li.dataset.read = String(l.read); li.dataset.letterId = l.id;
    var head = el("div", null, "letter-head");
    head.appendChild(el("strong", l.from_name + ": " + l.subject));
    head.appendChild(el("span", "night " + l.night, "note"));
    if (!l.read) head.appendChild(el("span", "New", "letter-new"));
    li.appendChild(head);
    if (!l.read) {
      var open = el("button", "Open the letter"); open.type = "button";
      open.addEventListener("click", function () { var r = A.send({ action: "read_letter", id: l.id }, false); if (r && r.message) { showToast(r.message); announce(r.message); } });
      li.appendChild(open);
      return li;
    }
    li.appendChild(el("p", l.text, "letter-text"));
    if (l.gift) li.appendChild(el("p", "In the envelope: " + l.gift.name + ".", "letter-gift"));
    if (l.reply) {
      li.appendChild(el("p", "You answered: " + l.reply, "letter-reply"));
      li.appendChild(el("p", l.answer ? l.from_name + " writes back: " + l.answer : "Your reply goes out with the next boat.", l.answer ? "letter-answer" : "note"));
    } else if (l.replies.length) {
      var row = el("div", null, "reply-buttons"); row.setAttribute("role", "group"); row.setAttribute("aria-label", "Reply to " + l.from_name);
      l.replies.forEach(function (r) {
        var b = el("button", r.label); b.type = "button";
        b.addEventListener("click", function () { var res = A.send({ action: "reply", id: l.id, reply: r.id }, false); if (res && res.message) announce(res.message); });
        row.appendChild(b);
      });
      li.appendChild(row);
    }
    return li;
  }

  var KIND_WORD = { odd: "Odd", moment: "The moment", kind: "Kind", resolve: "Explained" };
  function renderNotebook(s) {
    var nb = s.notebook;
    setText($("notebook-counts"), "Mysteries solved " + nb.mysteries.filter(function (m) { return m.solved; }).length + " of " + nb.mysteries_total + ". Small oddities explained " + nb.trifles.filter(function (t) { return t.explained; }).length + " of " + nb.trifles_total + ".");
    fillOnce($("notebook-list"), JSON.stringify(nb.mysteries), function (h) {
      nb.mysteries.forEach(function (m) {
        var li = el("li"); li.dataset.begun = String(m.begun); li.dataset.solved = String(m.solved);
        var head = el("div"); head.appendChild(el("strong", m.title));
        head.appendChild(el("span", m.solved ? "Solved" : m.begun ? "Still a mystery" : "", "nb-status"));
        li.appendChild(head);
        if (m.summary) li.appendChild(el("p", m.summary, "note"));
        if (m.entries.length) {
          var ol = el("ol");
          m.entries.forEach(function (e) {
            var item = el("li"); item.appendChild(el("span", KIND_WORD[e.kind] + ", night " + e.night + ": ", "nb-technique")); item.appendChild(document.createTextNode(e.text));
            ol.appendChild(item);
          });
          li.appendChild(ol);
        }
        h.appendChild(li);
      });
    });
    fillOnce($("oddities-list"), JSON.stringify(nb.trifles), function (h) {
      nb.trifles.forEach(function (t) {
        var li = el("li"); li.dataset.begun = "true"; li.dataset.solved = String(t.explained);
        li.appendChild(el("div", t.odd + " (night " + t.night + ")"));
        li.appendChild(el("div", t.explained ? "Explained: " + t.resolve : "Not explained yet.", "note"));
        h.appendChild(li);
      });
    });
  }
  function renderOdd(s) {
    var layer = $("off-chart");
    var want = {};
    (s.odd || []).forEach(function (o) { if (o.light || o.phantom) want[o.mystery] = o; });
    Array.prototype.slice.call(layer.children).forEach(function (n) { if (!want[n.dataset.mystery]) layer.removeChild(n); });
    Object.keys(want).forEach(function (m) {
      var o = want[m], node = layer.querySelector('[data-mystery="' + m + '"]');
      if (!node) {
        node = svgEl("g", { "data-mystery": m, class: "odd-light odd-detail" });
        if (o.phantom) {
          var hull = svgEl("g", { opacity: 0.55 });
          hull.appendChild(svgEl("path", { d: "M-70 0 L70 0 L60 14 L-60 14 Z", style: "fill: var(--ship-fill, #10181f); stroke: var(--ship-line, #9db4c6)", "stroke-width": 2 }));
          hull.appendChild(svgEl("rect", { x: -48, y: -16, width: 96, height: 16, style: "fill: var(--ship-fill, #10181f); stroke: var(--ship-line, #9db4c6)", "stroke-width": 2 }));
          for (var w = 0; w < 12; w++) hull.appendChild(svgEl("rect", { x: -44 + w * 8, y: -11, width: 4, height: 6, style: "fill: var(--on, #ffd866)" }));
          node.appendChild(hull);
        } else {
          node.appendChild(svgEl("circle", { r: 11, fill: "url(#glow-grad)", opacity: 0.7 }));
          node.appendChild(svgEl("circle", { r: 3.4, style: "fill: var(--on, #ffd866)" }));
        }
        layer.appendChild(node);
      }
      if (o.phantom) node.setAttribute("transform", "translate(" + o.phantom[0] + "," + o.phantom[1] + ") scale(" + o.phantom[2] + ")");
      else node.setAttribute("transform", "translate(" + o.light[0] + "," + o.light[1] + ")");
      node.classList.toggle("blinking", Boolean(o.blink));
    });
  }

  function renderStory(v) {
    var s = v.story;
    $("letters-toggle-button").hidden = !s.on;
    if (!s.on) { $("letters-panel").hidden = true; A.setToggleState("letters-toggle-button", "letters-panel"); return; }
    $("letters-toggle-button").textContent = s.unread ? "Letters (" + s.unread + " new)" : "Letters";
    if (A.knownUnread !== null && s.unread > A.knownUnread) showToast("A letter has come.");
    A.knownUnread = s.unread;
    setText($("letters-counts"), "Sailors met " + s.counts.met + " of " + s.counts.sailors + ". Letters read " + s.counts.letters + " of " + s.counts.letters_total + ". Gifts found " + s.counts.gifts + " of " + s.counts.gifts_total + ".");
    $("letters-empty").hidden = s.inbox.length > 0;
    fillOnce($("letters-list"), JSON.stringify(s.inbox), function (h) { s.inbox.forEach(function (l) { h.appendChild(letterItem(l)); }); });
    fillOnce($("sailors-list"), JSON.stringify(s.sailors), function (h) {
      s.sailors.forEach(function (x) {
        var li = el("li"); li.dataset.met = String(x.met);
        li.appendChild(el("span", x.name, "sailor-name"));
        if (x.met) {
          li.appendChild(el("div", x.role, "note"));
          li.appendChild(el("div", x.blurb));
          li.appendChild(el("div", (x.ashore ? "Writes from ashore. " : "Boat got safely by " + plural(x.passes, "time") + ". ") + "Letters: " + x.letters_got + " of " + x.letters, "note"));
        } else li.appendChild(el("div", "Not met yet.", "note"));
        h.appendChild(li);
      });
    });
    fillOnce($("gifts-list"), JSON.stringify(s.gifts), function (h) {
      s.gifts.forEach(function (g) {
        var li = el("li"); li.dataset.have = String(g.have);
        li.appendChild(el("strong", g.have || g.ever ? g.name : "Not found yet"));
        if (g.have) li.appendChild(el("div", g.text, "note"));
        h.appendChild(li);
      });
    });
    renderNotebook(s);
    renderOdd(s);
    fillOnce($("room-svg"), JSON.stringify([s.room, s.room_odd]), function () { drawRoom(v); });
    setText($("room-text"), s.room.length ? "Everything on the shelf, the table and the walls came in an envelope." : "Nothing on the shelf yet. Letters sometimes bring something small.");
  }

  // what the other parts use (see the File map in CLAUDE.md)
  A.renderStory = renderStory;
})();
