/* Lighthouse, Desktop boot only (loaded by pc.html). The guided tutorial for the Desktop layout: the Classic walkthrough
   points at the toolbar and panels the Desktop layout moves into icons, the Menu and windows. index.html uses these steps
   when they exist (window.LIGHTHOUSE_PC_TUTORIAL_STEPS) and its own otherwise. */
window.LIGHTHOUSE_PC_TUTORIAL_STEPS = [
  {
    title: "The keeper's life",
    text: "You keep one light on one rock. Each evening you plan the night, the night plays out, and each morning you read how the ships fared. Nothing you do can end the game, and everything can be paused. This walkthrough covers the Desktop layout. Skip it any time, and reopen it later from the Menu (or press Escape).",
  },
  {
    selector: "#pc-readouts",
    title: "The station at a glance",
    text: "Night, the clock, oil, your energy, the harbour's opinion of you (The Light) and salvage, which buys upgrades. They update live.",
  },
  {
    selector: "#goals-panel",
    title: "Three goals, no order",
    text: "Three goals are always on show: the next title the harbour could give you, the upgrade nearest your salvage, and something to try. Do them in any order; each is replaced when it is done.",
  },
  {
    selector: "#scene-panel",
    title: "The rock",
    text: "The beam sweeps the sea and ships pass by. A ship lit by your beam gets a ring and a mark. Fog, haze, squalls and storms shorten how far the beam reaches. The keeper's log sits just below.",
  },
  {
    selector: "#barometer-card",
    title: "The barometer",
    text: "Tonight's weather as a band of two steps. It is right about nine nights in ten, so it is a hint, not a promise.",
  },
  {
    selector: "#board-card",
    title: "The harbour board",
    text: "The ships expected tonight, roughly when, and how far the beam must reach for each to find you.",
  },
  {
    selector: "#plan-blocks",
    title: "The lamp plan",
    text: "Choose a lamp level for dusk, deep night and dawn. Brighter reaches further and burns more oil; the estimate under it says whether the oil will last.",
  },
  {
    selector: "#light-lamp-button",
    title: "Light the lamp",
    text: "When you are ready. In the night, Space pauses, [ and ] change speed, keys 1 to 4 change the lamp for the rest of this part of the night, W winds the clockwork and T sees to trouble.",
  },
  {
    selector: "#station-panel",
    title: "The station",
    text: "Storms wear the tower, the lantern glass, the rail, the dock and the cistern. In the day you mend them with supplies from the supply boat, whose twelve crates you order yourself.",
  },
  {
    selector: "#pc-menu-button",
    title: "Icons and the Menu",
    text: "The icons open the Letters, your Achievements and Settings. The Menu, or Escape when nothing else is open, holds the rest: this tutorial, the Eerie details switch (the odd things that happen in the night; off keeps the letters and kind moments), About the Light with its named sources, and What's New. Each opens as a window, and Escape closes the top one.",
  },
  {
    title: "You are ready",
    text: "Set the lamp, light it, and keep the sea company. Take your time.",
  },
];

/* Ship hover card (Desktop) --------------------------------------------------- */
(function () {
  "use strict";
  var card = null;
  var data = {};

  function init() {
    card = document.createElement("div");
    card.id = "ship-hover-card";
    card.innerHTML = "<h3 id='shc-name'></h3><p><span class='label'>Cargo:</span> <span id='shc-cargo'></span></p><p><span class='label'>Mood:</span> <span id='shc-mood'></span></p><p><span class='label'>Last letter:</span> <span id='shc-letter'></span></p>";
    document.body.appendChild(card);

    var scene = document.getElementById("scene-panel");
    if (!scene) return;

    scene.addEventListener("mouseover", onOver, true);
    scene.addEventListener("mouseout", onOut, true);
    scene.addEventListener("mousemove", onMove, true);
  }

  function onOver(e) {
    var el = e.target.closest("[data-ship-id]");
    if (!el) return;
    data.name = el.getAttribute("data-name") || "Unknown Ship";
    data.cargo = el.getAttribute("data-cargo") || "None";
    data.mood = el.getAttribute("data-mood") || "Neutral";
    data.letter = el.getAttribute("data-letter") || "No letters yet";
    card.querySelector("#shc-name").textContent = data.name;
    card.querySelector("#shc-cargo").textContent = data.cargo;
    card.querySelector("#shc-mood").textContent = data.mood;
    card.querySelector("#shc-letter").textContent = data.letter;
    card.classList.add("visible");
  }

  function onOut(e) {
    var el = e.target.closest("[data-ship-id]");
    if (!el || !card.contains(e.relatedTarget)) return;
    card.classList.remove("visible");
  }

  function onMove(e) {
    if (!card.classList.contains("visible")) return;
    var x = e.clientX + 12;
    var y = e.clientY + 12;
    var rect = card.getBoundingClientRect();
    if (x + rect.width > window.innerWidth) x = e.clientX - rect.width - 12;
    if (y + rect.height > window.innerHeight) y = e.clientY - rect.height - 12;
    card.style.left = x + "px";
    card.style.top = y + "px";
  }

  document.addEventListener("DOMContentLoaded", init);
})();

  /* Letters window: two-pane mail reader --------------------------------------------------- */
  (function () {
    "use strict";
    var panel = document.getElementById("letters-panel");
    var list = document.getElementById("letters-list");
    var wrapper = null;
    var reader = null;
    var activeIdx = -1;

    function init() {
      if (!panel || !list) return;
      
      wrapper = document.createElement("div");
      wrapper.id = "letters-pane-wrapper";
      list.parentNode.insertBefore(wrapper, list);
      wrapper.appendChild(list);
      
      reader = document.createElement("div");
      reader.id = "letters-reader";
      wrapper.appendChild(reader);

      list.addEventListener("click", onListClick);
      document.addEventListener("keydown", onKey);
    }

    function onListClick(e) {
      var item = e.target.closest("li");
      if (!item) return;
      var idx = Array.prototype.indexOf.call(list.children, item);
      showLetter(idx);
    }

    function showLetter(idx) {
      if (idx < 0 || idx >= list.children.length) return;
      activeIdx = idx;
      if (list.children[activeIdx]) list.children[activeIdx].classList.remove("active");
      list.children[activeIdx].classList.add("active");

      var letterEl = list.children[activeIdx].querySelector(".letter-content") || list.children[activeIdx];
      reader.innerHTML = "";
      reader.appendChild(letterEl.cloneNode(true));
    }

    function onKey(e) {
      if (panel.hidden) return;
      if (e.key === "j" || e.key === "J") {
        showLetter(activeIdx - 1);
      } else if (e.key === "k" || e.key === "K") {
        showLetter(activeIdx + 1);
      }
    }

    document.addEventListener("DOMContentLoaded", init);
  })();
