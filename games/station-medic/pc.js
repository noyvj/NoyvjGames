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

(function () {
  "use strict";
  var contextMenu = null;

  function showContextMenu(e) {
    if (!contextMenu) {
      contextMenu = document.createElement("div");
      contextMenu.id = "patient-context-menu";
      contextMenu.setAttribute("role", "menu");
      ["Scan", "Treat", "Isolate", "Comfort"].forEach(function(action) {
        var btn = document.createElement("button");
        btn.textContent = action;
        btn.setAttribute("role", "menuitem");
        btn.addEventListener("click", function() {
          contextMenu.hidden = true;
          // Placeholder for future ward job logic
        });
        contextMenu.appendChild(btn);
      });
      document.body.appendChild(contextMenu);
    }
    contextMenu.hidden = false;
    var x = e.clientX;
    var y = e.clientY;
    var rect = contextMenu.getBoundingClientRect();
    if (x + rect.width > window.innerWidth) x = window.innerWidth - rect.width - 10;
    if (y + rect.height > window.innerHeight) y = window.innerHeight - rect.height - 10;
    contextMenu.style.left = x + "px";
    contextMenu.style.top = y + "px";
  }

  function onKeyDown(e) {
    if (document.documentElement.getAttribute("data-layout") !== "pc") return;
    var key = e.key.toLowerCase();
    if (key >= '1' && key <= '4') {
      var idx = parseInt(key, 10) - 1;
      var patients = document.querySelectorAll("#patients .scene");
      if (patients[idx]) {
        patients[idx].click();
        e.preventDefault();
      }
    } else if (key === 's') {
      var scanRow = document.getElementById("scan-row");
      if (scanRow) { scanRow.focus(); e.preventDefault(); }
    } else if (key === 't') {
      var treatRow = document.getElementById("treat-row");
      if (treatRow) { treatRow.focus(); e.preventDefault(); }
    } else if (key === 'z') {
      var bedside = document.getElementById("bedside");
      if (bedside && !bedside.hidden) {
        bedside.hidden = true;
        var patients = document.querySelectorAll("#patients .scene");
        for (var i = 0; i < patients.length; i++) patients[i].classList.remove("selected");
        e.preventDefault();
      }
    }
  }

  function init() {
    document.addEventListener("mouseover", onHover);
    document.addEventListener("mouseout", onLeave);
    document.addEventListener("click", function(e) {
      var li = e.target.closest("#sheet-list li");
      if (li) {
        li.classList.toggle("struck-out");
      }
    });
    // Right-click menu on patients (Desktop only)
    document.addEventListener("contextmenu", function(e) {
      if (document.documentElement.getAttribute("data-layout") !== "pc") return;
      var patientCard = e.target.closest(".scene");
      if (patientCard && document.getElementById("patients").contains(patientCard)) {
        e.preventDefault();
        showContextMenu(e);
      }
    });
    document.addEventListener("click", function(e) {
      if (contextMenu && !contextMenu.hidden && !e.target.closest("#patient-context-menu")) {
        contextMenu.hidden = true;
      }
    });
    document.addEventListener("keydown", onKeyDown);
  }
  function onHover(e) {
    var el = e.target.closest(".bedside-signs li, .bedside-readings li");
    if (!el) return;
    var val = el.textContent.trim();
    if (!val) return;
    var conditions = document.querySelectorAll("#sheet-list li");
    for (var i = 0; i < conditions.length; i++) {
      var c = conditions[i];
      var signs = c.getAttribute("data-signs") || "";
      var scans = c.getAttribute("data-scans") || "";
      if (signs.split(",").indexOf(val) !== -1 || scans.split(",").indexOf(val) !== -1) {
        c.classList.add("highlighted");
      }
    }
  }
  function onLeave(e) {
    var conditions = document.querySelectorAll("#sheet-list li");
    for (var i = 0; i < conditions.length; i++) {
      conditions[i].classList.remove("highlighted");
    }
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
