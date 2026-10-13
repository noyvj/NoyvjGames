/* Lexis, Desktop boot only (loaded by pc.html). The guided tutorial for the Desktop layout: the Classic
   walkthrough points at the Crew log and About buttons, which the Desktop layout moves into icons, the Menu
   and windows. index.html uses these steps when they exist (window.LEXIS_PC_TUTORIAL_STEPS) and its own
   otherwise. */
window.LEXIS_PC_TUTORIAL_STEPS = [
  {
    title: "Welcome, officer",
    text: "You are the communications officer on a survey ship. Each planet speaks a language nobody has translated: your job is to work out what its signals mean, then answer. This walkthrough covers the Desktop layout. Skip it any time, and reopen it later from the Menu (or press Escape).",
  },
  {
    selector: "#pc-readouts",
    title: "Contact at a glance",
    text: "This chip counts the planets you have made contact with. Contact is how the story moves on: each one brings the next planet into range and adds a crew log entry.",
  },
  {
    selector: "#goal-line",
    title: "The crew's request",
    text: "The crew tells you what they need from each planet. When you manage it, contact is made. The planet tabs just above choose which world you are looking at; the next one stays out of range until the last one answers.",
  },
  {
    selector: "#transmissions-panel",
    title: "Watch what happens",
    text: "Each transmission is a signal and what the station did when it arrived. Press Receive next transmission, then compare them: what stays the same, and what changes? Everything you need is shown here before you are asked to rely on it.",
  },
  {
    selector: "#notebook-panel",
    title: "Write your guesses",
    text: "On the right is your notebook. Write what you think each group of marks means. Nothing here is marked right or wrong. Ticking entries and pressing Check tells you how many are right, never which.",
  },
  {
    selector: "#transmit-panel",
    title: "Answer",
    text: "Build a signal and send it. On Planet 1 you can type S for a short tick and L for a long bar, Backspace to take the last mark off and Delete to clear it. The station answers in its own terms, and when it cannot understand you, it says why.",
  },
  {
    selector: "#tab-compound",
    title: "Planet 2",
    text: "When planet 1 answers, a second world comes into range. Its signs are built from parts, so learning the parts lets you read signs nobody showed you.",
  },
  {
    selector: "#tab-bridge",
    title: "Planet 3",
    text: "The third world builds on the first two: things you learned on planet 2, numbers from planet 1, and a few new marks that change what a message does. Contact here needs a particular result on its counter, and the crew tells you which.",
  },
  {
    selector: "#pc-menu-button",
    title: "Icons and the Menu",
    text: "The three icons open the Crew log, your Achievements and Settings (text size, reduce motion, effects, high contrast and the theme). The Menu, or Escape when nothing else is open, holds the rest: this tutorial, About Lexis with its named sources, What's New, and the Contact report once you reach planet 3. Each opens as a window over the game, and Escape closes the top one.",
  },
  {
    title: "You are ready",
    text: "Every word can be worked out from what you are shown. Take your time.",
  },
];

/* Drag-and-drop notebook items into transmit bars (PC only) */
document.addEventListener("DOMContentLoaded", function () {
  var dragItem = null;

  document.addEventListener("dragstart", function (e) {
    if (e.target.closest(".notebook-list li")) {
      dragItem = e.target.closest(".notebook-list li");
      e.dataTransfer.setData("text/plain", dragItem.textContent.trim());
      e.dataTransfer.effectAllowed = "copy";
      setTimeout(function () { dragItem.classList.add("dragging"); }, 0);
    }
  });

  document.addEventListener("dragend", function (e) {
    if (dragItem) {
      dragItem.classList.remove("dragging");
      dragItem = null;
    }
  });

  document.addEventListener("dragover", function (e) {
    var target = e.target.closest("[data-builder] .signal");
    if (!target) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";

    if (dragItem && dragItem.parentNode === target) {
      var siblings = Array.from(target.children);
      var closestChild = null;
      var closestOffset = Number.NEGATIVE_INFINITY;
      for (var i = 0; i < siblings.length; i++) {
        var child = siblings[i];
        if (child === dragItem) continue;
        var box = child.getBoundingClientRect();
        var offset = e.clientY - box.top - box.height / 2;
        if (offset < 0 && offset > closestOffset) {
          closestOffset = offset;
          closestChild = child;
        }
      }
      target.insertBefore(dragItem, closestChild);
    }
  });

  document.addEventListener("drop", function (e) {
    var target = e.target.closest("[data-builder] .signal");
    if (target && e.dataTransfer.types.includes("text/plain")) {
      e.preventDefault();
      var text = e.dataTransfer.getData("text/plain");
      var span = document.createElement("span");
      span.className = "dropped-sign";
      span.textContent = text;
      target.appendChild(span);
    }
  });
});

/* Hover line on crew-log entries showing planet and scene (PC only) */
document.addEventListener("DOMContentLoaded", function () {
  var observer = new MutationObserver(function () {
    var entries = document.querySelectorAll("#crew-log-entries > *");
    for (var i = 0; i < entries.length; i++) {
      var el = entries[i];
      if (!el.dataset.source) {
        var text = el.textContent || "";
        var planet = "1";
        var m = text.match(/Planet (\d+)/);
        if (m) planet = m[1];
        el.dataset.source = "Planet " + planet + " • Scene " + (i + 1);
      }
    }
  });
  observer.observe(document.getElementById("crew-log-entries"), { childList: true, subtree: true });
});

document.addEventListener("DOMContentLoaded", function () {
  /* Notebook search (PC only) */
  var searchInput = null;
  var matches = [];
  var matchIndex = -1;
  var reducedMotion = false;

  function initSearch() {
    searchInput = document.createElement("input");
    searchInput.id = "pc-notebook-search";
    searchInput.type = "text";
    searchInput.placeholder = "Search notebook (/)";
    searchInput.className = "pc-notebook-search-input";
    document.body.appendChild(searchInput);

    searchInput.addEventListener("input", function () { filterNotebook(); });
    searchInput.addEventListener("keydown", function (e) {
      if (e.key === "ArrowDown") { e.preventDefault(); moveMatch(1); }
      else if (e.key === "ArrowUp") { e.preventDefault(); moveMatch(-1); }
      else if (e.key === "Escape") { closeSearch(); }
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "/" && !searchInput.matches(":focus") && !isTypingInInput()) {
        e.preventDefault();
        openSearch();
      }
    });
  }

  function isTypingInInput() {
    var tag = document.activeElement.tagName.toLowerCase();
    return tag === "input" || tag === "textarea" || document.activeElement.isContentEditable;
  }

  function openSearch() {
    searchInput.value = "";
    searchInput.hidden = false;
    searchInput.focus();
    filterNotebook();
  }

  function closeSearch() {
    searchInput.hidden = true;
    searchInput.blur();
    document.querySelectorAll(".notebook-list li").forEach(function(li) {
      li.style.display = "";
      li.classList.remove("search-match");
    });
  }

  function filterNotebook() {
    var query = searchInput.value.toLowerCase().trim();
    var allItems = Array.from(document.querySelectorAll(".notebook-list li"));
    matches = [];
    matchIndex = -1;

    allItems.forEach(function(li) {
      if (!query || li.textContent.toLowerCase().includes(query)) {
        li.style.display = "";
        matches.push(li);
      } else {
        li.style.display = "none";
      }
    });

    if (matches.length > 0 && matchIndex === -1) {
      moveMatch(1);
    } else if (matchIndex >= matches.length) {
      matchIndex = matches.length - 1;
    }
    highlightMatch();
  }

  function moveMatch(dir) {
    if (matches.length === 0) return;
    matchIndex += dir;
    if (matchIndex < 0) matchIndex = matches.length - 1;
    if (matchIndex >= matches.length) matchIndex = 0;
    highlightMatch();
  }

  function highlightMatch() {
    matches.forEach(function(li, i) {
      li.classList.toggle("search-match", i === matchIndex);
      if (i === matchIndex && !reducedMotion) {
        li.scrollIntoView({ behavior: "smooth", block: "nearest" });
      } else if (i === matchIndex) {
        li.scrollIntoView({ block: "nearest" });
      }
    });
  }

  function checkReducedMotion() {
    try {
      var val = window.localStorage.getItem("lexis-reduced-motion");
      reducedMotion = val === "true";
    } catch(e) { reducedMotion = false; }
    if (!reducedMotion && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      reducedMotion = true;
    }
  }

  initSearch();
  checkReducedMotion();
});

document.addEventListener("DOMContentLoaded", function () {
  /* Right-click context menu for signs (PC only) */
  var menu = null;
  var currentTarget = null;

  function createMenu() {
    if (menu) return menu;
    menu = document.createElement("div");
    menu.id = "lexis-context-menu";
    menu.className = "lexis-context-menu";
    menu.setAttribute("role", "menu");
    menu.hidden = true;
    ["Add note", "Show scenes", "Copy to transmit"].forEach(function(label) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "lexis-context-menu-item";
      btn.textContent = label;
      btn.setAttribute("role", "menuitem");
      btn.addEventListener("click", function (e) {
        e.stopPropagation();
        handleAction(label, currentTarget);
        closeMenu();
      });
      menu.appendChild(btn);
    });
    document.body.appendChild(menu);
    return menu;
  }

  function openMenu(e, target) {
    e.preventDefault();
    var m = createMenu();
    currentTarget = target;
    m.hidden = false;
    m.style.left = e.clientX + "px";
    m.style.top = e.clientY + "px";
  }

  function closeMenu() {
    if (menu) menu.hidden = true;
    currentTarget = null;
  }

  function handleAction(action, target) {
    console.log("Context action:", action, "on", target);
  }

  document.addEventListener("contextmenu", function (e) {
    var target = e.target.closest(".notebook-list li, .token-buttons button, [data-builder] .signal");
    if (target) openMenu(e, target);
  });

  document.addEventListener("click", function () { closeMenu(); });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") closeMenu(); });
});

document.addEventListener("DOMContentLoaded", function () {
  /* Pin a scene to a floating player (PC only) */
  var pinnedPanel = null;
  var currentPinnedScene = null;

  function createPinnedPanel() {
    if (pinnedPanel) return pinnedPanel;
    pinnedPanel = document.createElement("div");
    pinnedPanel.className = "lexis-pinned-scene";
    pinnedPanel.setAttribute("role", "dialog");
    pinnedPanel.setAttribute("aria-label", "Pinned scene");
    pinnedPanel.innerHTML = `
      <div class="lexis-pinned-scene-header">
        <span>Pinned scene</span>
        <button type="button" class="lexis-pinned-scene-close" aria-label="Close pinned scene">&times;</button>
      </div>
      <div class="lexis-pinned-scene-content"></div>
    `;
    document.body.appendChild(pinnedPanel);
    pinnedPanel.querySelector(".lexis-pinned-scene-close").addEventListener("click", function () {
      closePinnedScene();
    });
    return pinnedPanel;
  }

  function openPinnedScene(sceneEl) {
    var panel = createPinnedPanel();
    if (currentPinnedScene === sceneEl) {
      closePinnedScene();
      return;
    }
    currentPinnedScene = sceneEl;
    panel.querySelector(".lexis-pinned-scene-content").innerHTML = sceneEl.innerHTML;
    panel.setAttribute("open", "");
    
    document.querySelectorAll(".scene-list li .pin-btn").forEach(function(btn) {
      btn.classList.remove("active");
    });
    var pinBtn = sceneEl.querySelector(".pin-btn");
    if (pinBtn) pinBtn.classList.add("active");
  }

  function closePinnedScene() {
    if (pinnedPanel) pinnedPanel.removeAttribute("open");
    currentPinnedScene = null;
    document.querySelectorAll(".scene-list li .pin-btn").forEach(function(btn) {
      btn.classList.remove("active");
    });
  }

  document.addEventListener("click", function (e) {
    var pinBtn = e.target.closest(".pin-btn");
    if (!pinBtn) return;
    var sceneEl = pinBtn.closest(".scene-list li");
    if (sceneEl) openPinnedScene(sceneEl);
  });

  function ensurePinButtons() {
    document.querySelectorAll(".scene-list li").forEach(function(li) {
      if (!li.querySelector(".pin-btn")) {
        var btn = document.createElement("button");
        btn.type = "button";
        btn.className = "pin-btn";
        btn.textContent = "📌";
        btn.setAttribute("aria-label", "Pin this scene");
        li.appendChild(btn);
      }
    });
  }

  ensurePinButtons();
  var observer = new MutationObserver(function () { ensurePinButtons(); });
  document.querySelectorAll(".scene-list").forEach(function(list) {
    observer.observe(list, { childList: true });
  });
});

document.addEventListener("DOMContentLoaded", function () {
  /* Ctrl+Z / Ctrl+Y undo/redo for transmit lines (PC only) */
  const history = {};

  document.querySelectorAll("[data-builder] .signal").forEach(signal => {
    const builder = signal.closest("[data-builder]").getAttribute("data-builder");
    const key = `lexis-${builder}`;
    if (!history[key]) history[key] = { undo: [], redo: [] };

    let timer = null;
    const observer = new MutationObserver(() => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        history[key].undo.push(signal.innerHTML);
        if (history[key].undo.length > 50) history[key].undo.shift();
        history[key].redo = [];
      }, 120);
    });
    observer.observe(signal, { childList: true, subtree: true, characterData: true, attributes: true });
  });

  document.addEventListener("keydown", (e) => {
    const signal = document.activeElement?.closest("[data-builder] .signal");
    if (!signal) return;
    const builder = signal.closest("[data-builder]").getAttribute("data-builder");
    const key = `lexis-${builder}`;

    if ((e.ctrlKey || e.metaKey) && e.key === "z") {
      e.preventDefault();
      if (history[key].undo.length > 0) {
        history[key].redo.push(signal.innerHTML);
        signal.innerHTML = history[key].undo.pop();
      }
    } else if ((e.ctrlKey || e.metaKey) && e.key === "y") {
      e.preventDefault();
      if (history[key].redo.length > 0) {
        history[key].undo.push(signal.innerHTML);
        signal.innerHTML = history[key].redo.pop();
      }
    }
  });
});

document.addEventListener("DOMContentLoaded", function () {
  /* Double-click a scene to jump to its notebook entry (PC only) */
  var reducedMotion = false;
  function checkReducedMotion() {
    try {
      var val = window.localStorage.getItem("lexis-reduced-motion");
      reducedMotion = val === "true";
    } catch(e) { reducedMotion = false; }
    if (!reducedMotion && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      reducedMotion = true;
    }
  }
  checkReducedMotion();

  document.addEventListener("dblclick", function (e) {
    var sceneLi = e.target.closest(".scene-list li");
    if (!sceneLi) return;
    
    var sceneList = sceneLi.parentElement;
    var scenes = Array.from(sceneList.children);
    var sceneIndex = scenes.indexOf(sceneLi);
    if (sceneIndex === -1) return;

    var notebookList = document.querySelector(".notebook-list");
    if (!notebookList) return;
    var notebookItems = Array.from(notebookList.children);
    var targetNotebook = notebookItems[sceneIndex];
    if (!targetNotebook) return;

    var behavior = reducedMotion ? "auto" : "smooth";
    targetNotebook.scrollIntoView({ behavior: behavior, block: "nearest" });
    
    targetNotebook.classList.add("notebook-jumped");
    setTimeout(function() { targetNotebook.classList.remove("notebook-jumped"); }, 1500);

    var focusTarget = targetNotebook.querySelector("input, textarea, [contenteditable]");
    if (focusTarget) focusTarget.focus();
  });
});

document.addEventListener("DOMContentLoaded", function () {
  /* Print glossary (PC only) */
  var printGlossary = document.createElement("div");
  printGlossary.id = "print-glossary";
  printGlossary.hidden = true;
  document.body.appendChild(printGlossary);

  function buildGlossary() {
    var html = "<h2>Lexis Glossary</h2>";
    var planets = [
      ["notebook-list", "Planet 1: Pulse"],
      ["c-notebook-list", "Planet 2: Compound"],
      ["b-notebook-list", "Planet 3: Bridge"]
    ];
    planets.forEach(function(p) {
      var ul = document.getElementById(p[0]);
      if (!ul) return;
      html += "<h3>" + p[1] + "</h3><ol>";
      Array.from(ul.children).forEach(function(li) {
        var text = li.textContent.trim();
        if (text) html += "<li>" + text + "</li>";
      });
      html += "</ol>";
    });
    printGlossary.innerHTML = html;
  }

  window.addEventListener("beforeprint", buildGlossary);
  window.addEventListener("afterprint", function () {
    printGlossary.innerHTML = "";
    printGlossary.hidden = true;
  });
});
