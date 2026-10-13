(function () {
  "use strict";
  var SHEET_ID = "result-sheet";
  var HANDLE_ID = "result-sheet-handle";
  var CONTENT_ID = "result-sheet-content";

  function getReducedMotion() {
    try { return window.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch (e) { return false; }
  }

  function init() {
    var sheet = document.getElementById(SHEET_ID);
    if (!sheet) return;
    var handle = document.getElementById(HANDLE_ID);
    if (handle) {
      handle.addEventListener("click", function () {
        sheet.classList.toggle("open");
      });
    }
  }

  function render(tableData) {
    var sheet = document.getElementById(SHEET_ID);
    if (!sheet || !tableData) return;
    
    var content = document.getElementById(CONTENT_ID);
    if (!content) return;
    
    while (content.firstChild) content.removeChild(content.firstChild);

    var table = document.createElement("table");
    table.className = "truth";
    var thead = document.createElement("thead");
    var headerRow = document.createElement("tr");
    (tableData.ins || []).forEach(function (inp) {
      var th = document.createElement("th");
      th.textContent = inp;
      headerRow.appendChild(th);
    });
    (tableData.outs || []).forEach(function (out) {
      var th = document.createElement("th");
      th.textContent = out;
      headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    var tbody = document.createElement("tbody");
    (tableData.rows || []).forEach(function (row) {
      var tr = document.createElement("tr");
      if (!row.ok) tr.classList.add("failing");
      (row.inputs || []).forEach(function (val) {
        var td = document.createElement("td");
        td.textContent = val;
        tr.appendChild(td);
      });
      (row.outputs || []).forEach(function (val) {
        var td = document.createElement("td");
        td.textContent = val;
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    content.appendChild(table);

    // Auto-show when results appear, but respect reduced motion for scrolling
    if (!sheet.classList.contains("open") && tableData.rows.length) {
      sheet.classList.add("open");
    }

    var failingRow = content.querySelector("tr.failing");
    if (failingRow && !getReducedMotion()) {
      setTimeout(function () { failingRow.scrollIntoView({ block: "center", behavior: "smooth" }); }, 100);
    } else if (failingRow) {
      failingRow.scrollIntoView({ block: "center" });
    }
  }

  window.NoyvjResultSheet = { init: init, render: render };
})();
