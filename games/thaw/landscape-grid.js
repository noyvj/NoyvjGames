// R4-THMO-5: the landscape comparison board. With a phone turned sideways (style.css shows #landscape-board only on a
// short landscape screen), the four regions' mini graphs and temperatures sit in a 2 by 2 grid. The cells are copies
// of the game's own graphs (Region A's #graph and the B, C and D cards), refreshed whenever the game redraws them, so
// nothing here has a state of its own. Settings > "Hide the four-region board" turns it off.
(function () {
  "use strict";
  var board = document.getElementById("landscape-board");
  if (!board) return;
  var cells = Array.prototype.slice.call(board.querySelectorAll(".landscape-cell"));
  var scheduled = false;

  function copyGraph(source, box) {
    box.textContent = "";
    var svg = source ? source.querySelector("svg") : null;
    if (!svg) return;
    var copy = svg.cloneNode(true);
    // The copy is a picture only: no id twins, no crosshair hooks, no tab stop.
    copy.removeAttribute("id");
    copy.removeAttribute("tabindex");
    copy.removeAttribute("data-pts");
    copy.removeAttribute("data-sel");
    Array.prototype.forEach.call(copy.querySelectorAll("[id]"), function (node) { node.removeAttribute("id"); });
    box.appendChild(copy);
  }

  function refresh() {
    scheduled = false;
    cells.forEach(function (cell) {
      var graph = document.getElementById(cell.getAttribute("data-graph"));
      var stat = document.getElementById(cell.getAttribute("data-stat"));
      var gate = document.getElementById(cell.getAttribute("data-needs") || "");
      var box = cell.querySelector(".landscape-cell-graph");
      var text = stat ? stat.textContent.replace(/^[^:]*:\s*/, "").trim() : "";
      if (gate && gate.hidden) {
        // Region D stays a reveal-it-yourself region (its own button on the page), so the board does not give it away.
        box.textContent = "Not revealed yet";
        text = "";
      } else {
        copyGraph(graph, box);
      }
      cell.querySelector(".landscape-cell-stat").textContent = text;
    });
  }

  function schedule() {
    if (scheduled) return;
    scheduled = true;
    window.requestAnimationFrame(refresh);
  }

  var watcher = new MutationObserver(schedule);
  cells.forEach(function (cell) {
    ["data-graph", "data-stat"].forEach(function (name) {
      var source = document.getElementById(cell.getAttribute(name));
      if (source) watcher.observe(source, { childList: true, characterData: true, subtree: true });
    });
    var gate = document.getElementById(cell.getAttribute("data-needs") || "");
    if (gate) watcher.observe(gate, { attributes: true, attributeFilter: ["hidden"] });
  });
  refresh();
})();
