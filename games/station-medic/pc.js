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
