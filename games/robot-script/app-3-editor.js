/* Robot Script, part 3 of 5: the list editor (palette, the program list and its blocks) and the keyboard. Glue only;
   every rule is in the engine. */
(function () {
  "use strict";

  var A = window.RobotScriptApp;
  var $ = A.$, el = A.el, GLYPHS = A.GLYPHS, onRun = A.onRun, plural = A.plural, send = A.send, setText = A.setText;

  // ---- the list editor ----------------------------------------------------------------------------------

  function condSelect(addr, value) {
    var sel = el("select");
    sel.setAttribute("aria-label", "Condition");
    A.view.program.conds.forEach(function (c) {
      var o = el("option", null, c.label);
      o.value = c.value;
      sel.appendChild(o);
    });
    sel.value = value;
    sel.addEventListener("change", function () { send({ action: "cond", at: addr, cond: sel.value }, true); });
    return sel;
  }
  function smallButton(text, label, cls, handler) {
    var b = el("button", cls, text);
    b.type = "button";
    b.setAttribute("aria-label", label);
    b.addEventListener("click", handler);
    return b;
  }
  function tools(node, idx, len, name) {
    var frag = document.createDocumentFragment();
    frag.appendChild(el("span", "spacer"));
    frag.appendChild(smallButton("↑", "Move " + name + " up", "node-mv", function () { send({ action: "move", at: node.a, delta: -1 }, true); }));
    frag.appendChild(smallButton("↓", "Move " + name + " down", "node-mv", function () { send({ action: "move", at: node.a, delta: 1 }, true); }));
    frag.appendChild(smallButton("×", "Remove " + name, "node-x", function () { send({ action: "remove", at: node.a }, true); }));
    Array.prototype.forEach.call(frag.querySelectorAll(".node-mv"), function (b, k) {
      if ((k === 0 && idx === 0) || (k === 1 && idx === len - 1)) { b.disabled = true; }
    });
    return frag;
  }
  function buildList(body) {
    var ol = el("ol", "plist");
    ol.dataset.list = body.list;
    var cur = A.view.program.cursor;
    function gap(i) {
      var li = el("li");
      var b = el("button", "gap" + (cur.list === body.list && cur.index === i ? " current" : ""));
      b.type = "button";
      b.setAttribute("data-touch-exempt", "");
      b.setAttribute("aria-label", (cur.list === body.list && cur.index === i ? "Next step goes here, position " : "Put the next step here, position ") + (i + 1));
      b.dataset.gap = body.list + ":" + i;
      b.addEventListener("click", function () { send({ action: "cursor", list: body.list, index: i }, true); });
      li.appendChild(b);
      return li;
    }
    ol.appendChild(gap(0));
    body.items.forEach(function (node, i) {
      var li = el("li");
      li.appendChild(buildNode(node, i, body.items.length));
      ol.appendChild(li);
      ol.appendChild(gap(i + 1));
    });
    return ol;
  }
  function buildNode(node, idx, len) {
    var name = "step " + (idx + 1);
    if (node.k.length === 1 || node.k === "call") {
      var div = el("div", "node");
      div.dataset.a = node.a;
      var label = node.k === "call" ? "Call " + node.name : node.label;
      var grip = el("span", "node-glyph", node.k === "call" ? node.name : GLYPHS[node.k]);
      grip.title = "Hold, then drag up or down to move this step";   // R4-RSMO-1: the long-press handle (the arrow buttons stay)
      div.appendChild(grip);
      div.appendChild(el("span", "node-label", label));
      div.appendChild(tools(node, idx, len, label));
      return div;
    }
    var block = el("div", "block");
    block.dataset.a = node.a;
    var head = el("div", "block-head node");
    head.dataset.a = node.a;
    if (node.k === "rep") {
      head.appendChild(el("span", null, "Repeat"));
      var count = el("span", "count");
      var minus = smallButton("−", "Fewer repeats", "", function () { send({ action: "count", at: node.a, n: node.n - 1 }, true); });
      var plus = smallButton("+", "More repeats", "", function () { send({ action: "count", at: node.a, n: node.n + 1 }, true); });
      var out = el("output", null, String(node.n));
      out.setAttribute("aria-label", node.n + " times");
      count.appendChild(minus); count.appendChild(out); count.appendChild(plus);
      head.appendChild(count);
      head.appendChild(el("span", null, "times"));
      block.appendChild(head);
      head.appendChild(tools(node, idx, len, "the repeat"));
      block.appendChild(buildList(node.body));
    } else if (node.k === "until") {
      head.appendChild(el("span", null, "Repeat until"));
      head.appendChild(condSelect(node.a, node.c));
      head.appendChild(tools(node, idx, len, "the until block"));
      block.appendChild(head);
      block.appendChild(buildList(node.body));
    } else {
      head.appendChild(el("span", null, "If"));
      head.appendChild(condSelect(node.a, node.c));
      head.appendChild(tools(node, idx, len, "the if block"));
      block.appendChild(head);
      block.appendChild(el("p", "block-sub", "then"));
      block.appendChild(buildList(node["then"]));
      block.appendChild(el("p", "block-sub", "otherwise"));
      block.appendChild(buildList(node["else"]));
    }
    void name;
    return block;
  }
  function renderPalette() {
    var p = A.view.program;
    var sig = p.palette.map(function (x) { return x.k + (x.ok ? 1 : 0); }).join(",");
    if (A.PALETTE_SIG === sig + A.roomId) return;
    A.PALETTE_SIG = sig + A.roomId;
    var holder = $("palette");
    holder.textContent = "";
    p.palette.forEach(function (item) {
      var b = el("button", null);
      b.type = "button";
      b.dataset.testid = "robot-script-add-" + item.k;
      b.appendChild(el("span", "glyph", GLYPHS[item.k] || "?"));
      b.appendChild(document.createTextNode(item.label));
      b.title = item.detail;
      b.setAttribute("aria-label", item.label + ". " + item.detail + (item.ok ? "" : ". Not possible here: " + item.why));
      if (!item.ok) b.setAttribute("aria-disabled", "true");
      b.addEventListener("click", function () { send({ action: "insert", kind: item.k }, true); });
      holder.appendChild(b);
    });
  }
  function renderProgram() {
    var p = A.view.program;
    var r = A.view.room;
    var tier = A.view.difficulty === "easy" ? " (Easy)" : A.view.difficulty === "hard" ? " (Hard)" : "";
    var line = r.sandbox ? plural(p.size, "step", "steps") + " in your list (up to " + p.max + ")." : plural(p.size, "step", "steps") + " in your list. Gold at " + r.gold + " or fewer, silver at " + r.silver + tier + "." + (r.best !== null ? " Your best" + tier + ": " + r.best + "." : "");
    setText($("size-line"), line);
    var tabs = $("routine-tabs");
    tabs.textContent = "";
    tabs.hidden = p.routines.length < 2;
    p.routines.forEach(function (rt) {
      var b = el("button", null, rt.label + " (" + rt.size + ")");
      b.type = "button";
      b.setAttribute("aria-pressed", String(rt.name === p.active));
      b.addEventListener("click", function () { send({ action: "routine", name: rt.name }, true); });
      tabs.appendChild(b);
    });
    var holder = $("program");
    var active = p.routines.filter(function (x) { return x.name === p.active; })[0] || p.routines[0];
    var scroll = holder.scrollTop;
    holder.textContent = "";
    holder.setAttribute("role", "group");
    holder.setAttribute("aria-label", active.label + ", " + plural(active.size, "step", "steps"));
    holder.appendChild(buildList(active));
    holder.scrollTop = scroll;
    renderPalette();
    $("undo-button").disabled = !p.can_undo;
    $("clear-button").disabled = p.size === 0;
    $("best-button").hidden = !r.has_best;
    if (A.refocus) {
      A.refocus = false;
      var g = holder.querySelector(".gap.current");
      if (g && document.activeElement && document.activeElement.closest && document.activeElement.closest("#program")) g.focus();
    }
  }

  // ---- keyboard ------------------------------------------------------------------------------------------
  function onKey(e) {
    if (!A.view || e.ctrlKey || e.metaKey || e.altKey) return;
    var tag = e.target && e.target.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
    if (document.querySelector("dialog[open], .confirm-dialog, [role='dialog']:not([hidden])")) return;
    var key = e.key;
    var map = { f: "F", l: "L", r: "R", g: "G", p: "P", s: "S" };
    if (map[key.toLowerCase()] && key.length === 1) {
      var item = A.view.program.palette.filter(function (x) { return x.k === map[key.toLowerCase()]; })[0];
      if (!item) return;
      e.preventDefault();
      A.refocus = true;
      send({ action: "insert", kind: item.k }, true);
      return;
    }
    if (key === "Backspace" || key === "Delete") {
      var cur = A.view.program.cursor;
      if (cur.index > 0) {
        e.preventDefault();
        A.refocus = true;
        send({ action: "remove", at: cur.list + "/" + (cur.index - 1) }, true);
      }
      return;
    }
    if (key === "z" || key === "Z") { e.preventDefault(); A.refocus = true; send({ action: "undo" }, true); return; }
    if (key === "Enter" && !(tag === "BUTTON" || tag === "A" || tag === "SUMMARY")) { e.preventDefault(); onRun(); }
  }

  // what the other parts use
  A.onKey = onKey;
  A.renderProgram = renderProgram;
  A.smallButton = smallButton;
  A.tools = tools;
})();
