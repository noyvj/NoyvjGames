/* Station Medic, Desktop boot only (loaded by pc.html). The guided tutorial for the Desktop layout: the Classic walkthrough
   names toolbar buttons, which the Desktop layout turns into icons, the Menu and windows, and the cabinet and sheet sit in a
   side column. index.html uses these steps when they exist (window.STATION_MEDIC_PC_TUTORIAL_STEPS) and its own otherwise. */
window.STATION_MEDIC_PC_TUTORIAL_STEPS = [
  {
    title: "Welcome to the infirmary",
    text: "You are the only medic on Lowlight Station. Crew come in with signs, and you choose the scans and the treatments. Nothing is timed, and a bad call only costs a seal. This is a fiction game with invented conditions, not medical advice. This walkthrough covers the Desktop layout. Skip it any time, and reopen it from the Menu.",
  },
  {
    selector: "#patients",
    title: "The ward",
    text: "Each person waiting is a card. Click one to look at them. Their signs are on the card below: a patient shows all the signs of what they have.",
  },
  {
    selector: "#pc-side",
    title: "The cabinet and the sheet",
    text: "The side column holds the supply cabinet (each shelf has a letter and a count), today's sheet of conditions (their signs, scans and cures) and the shift log. Conditions that cannot fit the patient you are looking at are dimmed.",
  },
  {
    selector: "#bedside-actions",
    title: "Scan and treat",
    text: "A scan answers yes or no and uses a supply. A treatment uses a supply too. Treat only when one condition fits, or when one treatment cures every one that does. Chart notes forbid some treatments.",
  },
  {
    selector: "#restore-button",
    title: "Restore",
    text: "A bad call costs a seal, never a person. You can restore the shift to its start at any time, for free, and try a different plan.",
  },
  {
    selector: "#goals",
    title: "Your goals",
    text: "Three goals stay in view, in any order. Every scan, treatment and hint counts toward something on the screen.",
  },
  {
    selector: "#pc-menu-button",
    title: "Icons and the Menu",
    text: "The icons open the Shifts, the Record, the Achievements and Settings. The Menu, or Escape when nothing else is open, holds the rest: this tutorial, About and What's New. Each opens as a window over the game, and Escape closes the top one.",
  },
  {
    title: "You are ready",
    text: "Take your time. Your seals and records are saved as you go.",
  },
];

/* Desktop-only extras (Round 4). They read the view that app.js already drew (window.stationMedicView) and redraw after every
   "station-medic-rendered" event, because app.js rebuilds the lists they decorate. Nothing here talks to the engine. */
(function () {
  "use strict";
  var pc = window.StationMedicPc = {
    ready: function (fn) { if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", fn); else fn(); },
    view: function () { return typeof window.stationMedicView === "function" ? window.stationMedicView() : null; },
    onRendered: function (fn) { document.addEventListener("station-medic-rendered", fn); },
  };

  // R4-SMPC-2: hover (or keyboard focus) a sign or a scan result to light the conditions on the sheet that carry it.
  function conditionsFor(item) {
    var v = pc.view();
    if (!v) return [];
    var chip = item.querySelector(".sign-chip");
    var sign = chip ? chip.textContent : null;
    var scan = item.dataset.scan || null;
    return v.sheet.filter(function (c) {
      return (sign !== null && c.signs.indexOf(sign) !== -1) || (scan !== null && c.scans.indexOf(scan) !== -1);
    }).map(function (c) { return String(c.id); });
  }
  function light(ids) {
    document.querySelectorAll("#sheet-list li").forEach(function (li) { li.classList.toggle("highlighted", ids.indexOf(li.dataset.cond) !== -1); });
  }
  function enter(e) {
    var item = e.target.closest && e.target.closest("#bedside-signs li, #bedside-readings li");
    if (item) light(conditionsFor(item));
  }
  function leave(e) {
    if (e.target.closest && e.target.closest("#bedside-signs li, #bedside-readings li")) light([]);
  }
  pc.ready(function () {
    document.addEventListener("mouseover", enter);
    document.addEventListener("mouseout", leave);
    document.addEventListener("focusin", enter);
    document.addEventListener("focusout", leave);
  });
})();

(function () {
  "use strict";
  var pc = window.StationMedicPc;

  // R4-SMPC-3: a notepad on the Condition Sheet. A click on a condition (or its Rule out button, which is the keyboard way)
  // strikes it out; a second click puts it back. This is the player's own note, separate from the engine's "rule out for me"
  // dimming, and it is kept for the page's life only (it is not part of a save).
  var struck = {};
  function shiftKey() { var h = document.getElementById("scene-holder"); return h ? h.dataset.sig || "" : ""; }
  function keyOf(li) { return shiftKey() + ":" + li.dataset.cond; }
  function decorate() {
    document.querySelectorAll("#sheet-list li").forEach(function (li) {
      var on = Boolean(struck[keyOf(li)]);
      var nameNode = li.querySelector(".cname");
      var name = nameNode && nameNode.firstChild ? nameNode.firstChild.textContent : "this condition";
      li.classList.toggle("struck-out", on);
      var b = li.querySelector(".strike-btn");
      if (!b) {
        b = document.createElement("button");
        b.type = "button";
        b.className = "strike-btn";
        li.appendChild(b);
      }
      b.textContent = on ? "Put back" : "Rule out";
      b.setAttribute("aria-pressed", String(on));
      b.setAttribute("aria-label", (on ? "Put back " : "Rule out ") + name + " in my notes");
    });
  }
  pc.ready(function () {
    pc.onRendered(decorate);
    document.addEventListener("click", function (e) {
      var li = e.target.closest && e.target.closest("#sheet-list li");
      if (!li || e.target.closest("a")) return;
      var key = keyOf(li);
      struck[key] = !struck[key];
      decorate();
    });
    decorate();
  });
})();

(function () {
  "use strict";
  var pc = window.StationMedicPc;

  // R4-SMPC-4: right-click a patient for Scan, Treat, Isolate and Comfort at the cursor (Shift+F10 or the menu key on a focused
  // patient does the same). It picks the patient, then uses the bedside's own buttons: Scan and Treat move to the first scan or
  // treatment button, Isolate presses Move to the cold room (or Back to the ward), Comfort opens its usual confirm.
  var menu = null, openerIndex = -1;
  var ITEMS = [
    ["Scan", function () { return focusFirst("scan-row"); }],
    ["Treat", function () { return focusFirst("treat-row"); }],
    ["Isolate", function () { return press("station-medic-isolate") || press("station-medic-release"); }],
    ["Comfort", function () { return press("station-medic-comfort"); }],
  ];
  function bedsideButton(testid) { return document.querySelector('#bedside-actions [data-testid="' + testid + '"]'); }
  function press(testid) { var b = bedsideButton(testid); if (b) b.click(); return Boolean(b); }
  function focusFirst(rowId) { var b = document.querySelector("#" + rowId + " button"); if (b) b.focus(); return Boolean(b); }
  function canDo(label) {
    var bedside = document.getElementById("bedside-actions");
    if (!bedside || bedside.hidden) return false;
    if (label === "Scan") return Boolean(document.querySelector("#scan-row button"));
    if (label === "Treat") return Boolean(document.querySelector("#treat-row button"));
    if (label === "Isolate") return Boolean(bedsideButton("station-medic-isolate") || bedsideButton("station-medic-release"));
    return Boolean(bedsideButton("station-medic-comfort"));
  }
  function build() {
    menu = document.createElement("div");
    menu.id = "patient-context-menu";
    menu.setAttribute("role", "menu");
    menu.setAttribute("aria-label", "Ward jobs");
    menu.hidden = true;
    ITEMS.forEach(function (item) {
      var b = document.createElement("button");
      b.type = "button";
      b.setAttribute("role", "menuitem");
      b.textContent = item[0];
      b.addEventListener("click", function () {
        if (b.getAttribute("aria-disabled") === "true") return;
        close(false);
        item[1]();
      });
      menu.appendChild(b);
    });
    menu.addEventListener("keydown", function (e) {
      var buttons = Array.prototype.slice.call(menu.querySelectorAll("button"));
      var i = buttons.indexOf(document.activeElement);
      if (e.key === "ArrowDown") { buttons[(i + 1) % buttons.length].focus(); e.preventDefault(); }
      else if (e.key === "ArrowUp") { buttons[(i + buttons.length - 1) % buttons.length].focus(); e.preventDefault(); }
      else if (e.key === "Escape") { e.stopPropagation(); close(true); }
      else if (e.key === "Tab") close(false);
    });
    document.body.appendChild(menu);
  }
  function close(refocus) {
    if (!menu || menu.hidden) return;
    menu.hidden = true;
    var back = document.querySelector('#patients .patient[data-patient-id="' + openerIndex + '"]');
    if (refocus && back) back.focus();
  }
  function open(patientButton, x, y) {
    if (!menu) build();
    openerIndex = Number(patientButton.dataset.patientId);
    window.stationMedicSelect(openerIndex);                  // look at them first, so the bedside shows their buttons
    menu.querySelectorAll("button").forEach(function (b, i) {
      var ok = canDo(ITEMS[i][0]);
      b.setAttribute("aria-disabled", String(!ok));
      b.title = ok ? "" : "Not available for this patient on this shift";
    });
    menu.hidden = false;
    var w = menu.offsetWidth, h = menu.offsetHeight;
    menu.style.left = Math.max(4, Math.min(x, window.innerWidth - w - 4)) + "px";
    menu.style.top = Math.max(4, Math.min(y, window.innerHeight - h - 4)) + "px";
    var first = menu.querySelector('button[aria-disabled="false"]') || menu.querySelector("button");
    first.focus();
  }
  pc.ready(function () {
    document.addEventListener("contextmenu", function (e) {
      var b = e.target.closest && e.target.closest("#patients .patient");
      if (!b) { close(false); return; }
      e.preventDefault();
      var r = b.getBoundingClientRect();
      var fromKeyboard = e.clientX === 0 && e.clientY === 0;
      open(b, fromKeyboard ? r.left + r.width / 2 : e.clientX, fromKeyboard ? r.top + r.height / 2 : e.clientY);
    });
    document.addEventListener("click", function (e) { if (menu && !menu.hidden && !e.target.closest("#patient-context-menu")) close(false); });
    window.addEventListener("blur", function () { close(false); });
    window.addEventListener("resize", function () { close(false); });
  });
})();

(function () {
  "use strict";
  var pc = window.StationMedicPc;

  // R4-SMPC-8: a supply tray along the bottom of the stage: every shelf with its letter and count, always in view. Pointing at
  // (or focusing) a shelf lights the patients who could have a scan or treatment from it right now and says who in words;
  // pressing it picks the shelf up, the same as pressing it in the cabinet, and then a patient uses it.
  var tray = null, note = null;
  function ensure() {
    if (tray && document.body.contains(tray)) return true;
    var stage = document.getElementById("pc-stage");
    if (!stage) return false;
    tray = document.createElement("div");
    tray.id = "supply-tray";
    tray.setAttribute("role", "group");
    tray.setAttribute("aria-label", "Supply tray");
    note = document.createElement("span");
    note.className = "tray-note";
    note.setAttribute("aria-live", "polite");
    stage.appendChild(tray);
    return true;
  }
  function usable(glyph) {
    return Array.prototype.filter.call(document.querySelectorAll("#patients .patient"), function (p) { return (p.dataset.usable || "").indexOf(glyph) !== -1; });
  }
  function show(glyph, name) {
    var who = usable(glyph);
    document.querySelectorAll("#patients .patient").forEach(function (p) { p.classList.toggle("tray-highlight", who.indexOf(p) !== -1); });
    note.textContent = who.length ? name + ": " + who.map(function (p) { return p.querySelector(".pname").textContent; }).join(", ") + " could have it now." : name + ": nobody could use it right now.";
  }
  function clear() {
    document.querySelectorAll("#patients .tray-highlight").forEach(function (p) { p.classList.remove("tray-highlight"); });
    note.textContent = "";
  }
  function draw() {
    var v = pc.view();
    if (!v || !ensure()) return;
    tray.textContent = "";
    v.cabinet.items.forEach(function (i) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = "tray-item" + (i.count === 0 ? " empty" : "");
      b.setAttribute("aria-label", i.name + ": " + i.count + " left. Point at it to see who could use it; press to pick it up.");
      var letter = document.createElement("span");
      letter.className = "tray-letter";
      letter.textContent = i.glyph;
      var count = document.createElement("span");
      count.className = "tray-count";
      count.textContent = String(i.count);
      b.appendChild(letter);
      b.appendChild(count);
      b.addEventListener("mouseenter", function () { show(i.glyph, i.name); });
      b.addEventListener("focus", function () { show(i.glyph, i.name); });
      b.addEventListener("mouseleave", clear);
      b.addEventListener("blur", clear);
      b.addEventListener("click", function () {
        var shelf = document.querySelector('#cabinet-list li[data-item="' + i.i + '"] .shelf-pick');
        if (shelf) shelf.click();
      });
      tray.appendChild(b);
    });
    tray.appendChild(note);
  }
  pc.ready(function () { pc.onRendered(draw); window.addEventListener("load", draw); draw(); });
})();
