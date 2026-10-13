/* Robot Script, Desktop boot only (loaded by pc.html). The guided tutorial for the Desktop layout: the Classic
   walkthrough names toolbar buttons, which the Desktop layout turns into icons, the Menu and windows, and the list
   editor sits in a side column. index.html uses these steps when they exist (window.ROBOT_SCRIPT_PC_TUTORIAL_STEPS)
   and its own otherwise. */
window.ROBOT_SCRIPT_PC_TUTORIAL_STEPS = [
  {
    title: "Welcome to the deck",
    text: "A maintenance robot does exactly what your list says. Write the list, press Run, and watch. Nothing is timed, and a run that goes wrong costs nothing. This walkthrough covers the Desktop layout. Skip it any time, and reopen it from the Menu.",
  },
  {
    selector: "#room-panel",
    title: "The room",
    text: "The robot starts on its tile facing the way its nose points. The checklist above the room says what the room needs. Parts are diamonds, sockets are dashed frames, switches are numbered plates and doors are barred and lettered.",
  },
  {
    selector: "#pc-side",
    title: "Your list",
    text: "The side column holds your list. Tap an instruction to add it where the marked gap is, tap another gap to add somewhere else, and use the arrows and the x to rearrange or remove steps. Every instruction is one step.",
  },
  {
    selector: "#run-button",
    title: "Run, Step and Skip",
    text: "Run plays your list. Step does one action at a time and Skip jumps to the end. If the robot cannot do a step it stops there and says why. Your list stays, so fix it and run again.",
  },
  {
    selector: "#size-line",
    title: "Steps and medals",
    text: "Fewer steps earn better medals: gold at the reference length, silver a little over, bronze for any clear. Hints are free and never touch a medal.",
  },
  {
    selector: "#goals",
    title: "Your goals",
    text: "Three goals stay in view, in any order. Every run, every step you write and every hint you ask for counts toward something on the screen.",
  },
  {
    selector: "#pc-menu-button",
    title: "Icons and the Menu",
    text: "The icons open the Rooms, Scrap's Workshop, Achievements and Settings. The Menu, or Escape when nothing else is open, holds the rest: this tutorial, About and What's New. Each opens as a window over the game, and Escape closes the top one.",
  },
  {
    title: "You are ready",
    text: "Take your time. Your lists and medals are saved as you go.",
  },
];

// Breakpoints gutter for Desktop view
(function () {
  "use strict";
  window.ROBOT_SCRIPT_breakpoints = new Set();

  function toggleBreakpoint(index) {
    if (window.ROBOT_SCRIPT_breakpoints.has(index)) {
      window.ROBOT_SCRIPT_breakpoints.delete(index);
    } else {
      window.ROBOT_SCRIPT_breakpoints.add(index);
    }
    _updateGutters();
  }
  window.ROBOT_SCRIPT_toggleBreakpoint = toggleBreakpoint;

  function _updateGutters() {
    var lines = document.querySelectorAll("#program ol > li");
    for (var i = 0; i < lines.length; i++) {
      var gutter = lines[i].querySelector(".gutter");
      if (!gutter) continue;
      if (window.ROBOT_SCRIPT_breakpoints.has(i)) {
        gutter.classList.add("breakpoint");
      } else {
        gutter.classList.remove("breakpoint");
      }
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    var program = document.getElementById("program");
    if (!program) return;

    // Inject gutters into existing lines
    var lines = program.querySelectorAll("#program ol > li");
    for (var i = 0; i < lines.length; i++) {
      var gutter = document.createElement("div");
      gutter.className = "gutter";
      gutter.setAttribute("data-index", i);
      gutter.setAttribute("role", "button");
      gutter.setAttribute("aria-label", "Toggle breakpoint at line " + (i + 1));
      gutter.addEventListener("click", function (e) {
        e.stopPropagation();
        toggleBreakpoint(parseInt(e.currentTarget.getAttribute("data-index"), 10));
      });
      lines[i].appendChild(gutter);
    }

    // Hook into future lines if app.js adds them dynamically
    var observer = new MutationObserver(function (mutations) {
      for (var m = 0; m < mutations.length; m++) {
        mutations[m].addedNodes.forEach(function (node) {
          if (node.nodeType === 1 && node.tagName === "LI") {
            var idx = Array.prototype.indexOf.call(node.parentNode.children, node);
            var gutter = document.createElement("div");
            gutter.className = "gutter";
            gutter.setAttribute("data-index", idx);
            gutter.setAttribute("role", "button");
            gutter.setAttribute("aria-label", "Toggle breakpoint at line " + (idx + 1));
            gutter.addEventListener("click", function (e) {
              e.stopPropagation();
              toggleBreakpoint(parseInt(e.currentTarget.getAttribute("data-index"), 10));
            });
            node.appendChild(gutter);
          }
        });
      }
    });
    observer.observe(program, { childList: true });
  });
})();

// Compare mode (R4-RSPC-9)
(function () {
  "use strict";
  var KEY = "robot-script-compare-mode";
  function loadCompare() {
    try { return localStorage.getItem(KEY) === "true"; } catch (e) { return false; }
  }
  function saveCompare(on) { localStorage.setItem(KEY, String(on)); }

  document.addEventListener("DOMContentLoaded", function () {
    var toggleBtn = document.getElementById("compare-toggle-button");
    if (!toggleBtn) return;

    var stage = document.getElementById("pc-stage");
    if (!stage) return;
    var panel = document.createElement("div");
    panel.id = "compare-panel";
    panel.hidden = !loadCompare();
    panel.innerHTML = `
      <div class="compare-header">
        <span>Compare programs</span>
        <button id="compare-close" type="button" aria-label="Close compare">×</button>
      </div>
      <div class="compare-areas">
        <textarea id="compare-a" spellcheck="false" placeholder="Current program"></textarea>
        <textarea id="compare-b" spellcheck="false" placeholder="Paste or type second program"></textarea>
      </div>
      <button id="compare-diff-btn" type="button">Show diff</button>
      <pre id="compare-diff" class="compare-diff" hidden></pre>
    `;
    stage.appendChild(panel);

    function updateA() {
      var lines = document.querySelectorAll("#program ol > li");
      var text = Array.from(lines).map(function(li) { return li.textContent.trim(); }).join("\n");
      document.getElementById("compare-a").value = text;
    }

    toggleBtn.addEventListener("click", function () {
      var isOn = !panel.hidden;
      panel.hidden = isOn;
      saveCompare(!isOn);
      if (!isOn) updateA();
    });

    document.getElementById("compare-close").addEventListener("click", function () {
      panel.hidden = true;
      saveCompare(false);
    });

    document.getElementById("compare-diff-btn").addEventListener("click", function () {
      var a = document.getElementById("compare-a").value.split("\n");
      var b = document.getElementById("compare-b").value.split("\n");
      var maxLen = Math.max(a.length, b.length);
      var html = "<table>";
      for (var i = 0; i < maxLen; i++) {
        var lineA = a[i] || "";
        var lineB = b[i] || "";
        if (lineA === lineB) {
          html += "<tr><td class='diff-unchanged'>" + (i+1) + "</td><td>" + escapeHtml(lineA) + "</td></tr>";
        } else {
          html += "<tr class='diff-changed'><td class='diff-line-a'>" + (i+1) + "</td><td class='diff-line-a'>- " + escapeHtml(lineA) + "</td></tr>";
          if (lineB) {
            html += "<tr class='diff-changed'><td class='diff-line-b'>" + (i+1) + "</td><td class='diff-line-b'>+ " + escapeHtml(lineB) + "</td></tr>";
          }
        }
      }
      html += "</table>";
      var diffEl = document.getElementById("compare-diff");
      diffEl.innerHTML = html;
      diffEl.hidden = false;
    });

    function escapeHtml(str) {
      return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }

    var observer = new MutationObserver(function () { updateA(); });
    observer.observe(document.getElementById("program"), { childList: true, subtree: true });
  });
})();

// Snippets drawer (Desktop boot)
(function () {
  "use strict";
  var KEY = "robot-script-snippets";
  function load() {
    try { return JSON.parse(localStorage.getItem(KEY)) || []; } catch (e) { return []; }
  }
  function save(snips) { localStorage.setItem(KEY, JSON.stringify(snips)); }

  function render() {
    var body = document.getElementById("pc-snippets-body");
    if (!body) return;
    body.innerHTML = "";
    var snips = load();
    snips.forEach(function (s, i) {
      var item = document.createElement("div");
      item.className = "pc-snippet-item";
      item.draggable = true;
      item.setAttribute("aria-label", "Drag to insert: " + s.name);
      item.innerHTML = '<span class="pc-snippet-name">' + s.name + '</span><button class="pc-snippet-del" aria-label="Delete snippet">✕</button>';
      item.addEventListener("dragstart", function (e) {
        e.dataTransfer.setData("text/plain", JSON.stringify(s));
        e.dataTransfer.effectAllowed = "copy";
      });
      var delBtn = item.querySelector(".pc-snippet-del");
      delBtn.addEventListener("click", function () {
        snips.splice(i, 1);
        save(snips);
        render();
      });
      body.appendChild(item);
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    var addBtn = document.getElementById("snippets-add-button");
    if (addBtn) {
      addBtn.addEventListener("click", function () {
        var name = prompt("Name for this snippet:");
        if (!name) return;
        var lines = document.querySelectorAll("#program ol > li");
        var text = Array.from(lines).map(function(li) { return li.textContent.trim(); }).join("\n");
        if (!text) { alert("The list is empty."); return; }
        var snips = load();
        snips.push({ id: Date.now().toString(), name: name, text: text });
        save(snips);
        render();
      });
    }

    var program = document.getElementById("program");
    if (program) {
      program.addEventListener("dragover", function (e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = "copy";
        program.classList.add("drag-over");
      });
      program.addEventListener("dragleave", function () {
        program.classList.remove("drag-over");
      });
      program.addEventListener("drop", function (e) {
        e.preventDefault();
        program.classList.remove("drag-over");
        var data = e.dataTransfer.getData("text/plain");
        if (!data) return;
        try {
          var s = JSON.parse(data);
          var ol = program.querySelector("ol");
          if (ol) {
            var lines = s.text.split("\n");
            for (var i = 0; i < lines.length; i++) {
              var newLi = document.createElement("li");
              newLi.textContent = lines[i];
              ol.appendChild(newLi);
            }
          }
        } catch (err) {}
      });
    }

    render();
  });
})();

// Playback slider and keyboard controls (Desktop boot)
(function () {
  "use strict";
  var KEY = "robot-script-playback-speed";
  function loadSpeed() {
    try { return parseInt(localStorage.getItem(KEY), 10) || 50; } catch (e) { return 50; }
  }
  function saveSpeed(val) { localStorage.setItem(KEY, String(val)); }

  document.addEventListener("DOMContentLoaded", function () {
    var playback = document.getElementById("playback");
    if (!playback) return;

    var slider = document.createElement("input");
    slider.type = "range";
    slider.min = "0";
    slider.max = "100";
    slider.value = loadSpeed();
    slider.id = "playback-slider";
    slider.setAttribute("aria-label", "Playback speed");
    slider.addEventListener("input", function () {
      var val = parseInt(slider.value, 10);
      // Map 0-100 to 600ms-50ms (slow to fast)
      var delay = Math.max(50, 600 - (val * 5.5));
      playback.dataset.playbackDelay = delay;
      window.robotScriptPlaybackDelay = delay;
      saveSpeed(val);
      document.dispatchEvent(new CustomEvent("robotScriptPlaybackSpeedChange", { detail: val }));
    });
    playback.appendChild(slider);

    // Keyboard shortcuts
    document.addEventListener("keydown", function (e) {
      if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;
      var slider = document.getElementById("playback-slider");
      if (!slider) return;
      var val = parseInt(slider.value, 10);
      if (e.key === "[") {
        slider.value = Math.max(0, val - 5);
        playback.dataset.playbackDelay = slider.value;
        window.robotScriptPlaybackDelay = slider.value;
        saveSpeed(slider.value);
        document.dispatchEvent(new CustomEvent("robotScriptPlaybackSpeedChange", { detail: slider.value }));
        e.preventDefault();
      } else if (e.key === "]") {
        slider.value = Math.min(100, val + 5);
        playback.dataset.playbackDelay = slider.value;
        window.robotScriptPlaybackDelay = slider.value;
        saveSpeed(slider.value);
        document.dispatchEvent(new CustomEvent("robotScriptPlaybackSpeedChange", { detail: slider.value }));
        e.preventDefault();
      } else if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
        document.dispatchEvent(new CustomEvent("robotScriptFrameStep", { detail: e.key === "ArrowLeft" ? -1 : 1 }));
        e.preventDefault();
      }
    });
  });
})();
