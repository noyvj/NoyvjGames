// C-24: a "Print or save as PDF" button inside the Run Summary panel (the panel is rebuilt each time it opens, so it is
// put back whenever it goes missing). Printing shows only the summary (shared/print-summary.css hides the rest).
(function () {
  var panel = document.getElementById("summary-panel");
  if (!panel) return;
  function ensure() {
    if (panel.querySelector(":scope > .summary-print-button") || !panel.firstChild) return;
    var button = document.createElement("button");
    button.type = "button";
    button.className = "secondary summary-print-button";
    button.textContent = "Print or save as PDF";
    button.addEventListener("click", function () { window.print(); });
    panel.appendChild(button);
  }
  ensure();
  new MutationObserver(ensure).observe(panel, { childList: true });
})();
// C-11: "Save schematic image" turns the schematic SVG (plain attributes, so it stands alone) into a PNG for download; if the
// browser cannot draw it to a canvas the SVG file is offered instead. Nothing leaves the page.
(function () {
  var button = document.getElementById("schematic-save-button");
  var status = document.getElementById("schematic-save-status");
  if (!button) return;
  function save(blob, name) {
    var url = URL.createObjectURL(blob);
    var link = document.createElement("a");
    link.href = url; link.download = name;
    document.body.appendChild(link); link.click(); link.remove();
    setTimeout(function () { URL.revokeObjectURL(url); }, 2000);
  }
  button.addEventListener("click", function () {
    var svg = document.querySelector("#schematic-graphic svg");
    if (!svg) { status.textContent = "Nothing to save yet."; return; }
    var text = new XMLSerializer().serializeToString(svg);
    var svgBlob = new Blob([text], { type: "image/svg+xml;charset=utf-8" });
    var img = new Image();
    img.onload = function () {
      try {
        var canvas = document.createElement("canvas");
        canvas.width = img.width || 600; canvas.height = img.height || 300;
        canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height);
        canvas.toBlob(function (png) {
          if (png) { save(png, "grid-schematic.png"); status.textContent = "Saved grid-schematic.png."; }
          else { save(svgBlob, "grid-schematic.svg"); status.textContent = "Saved grid-schematic.svg."; }
        }, "image/png");
      } catch (e) { save(svgBlob, "grid-schematic.svg"); status.textContent = "Saved grid-schematic.svg."; }
    };
    img.onerror = function () { save(svgBlob, "grid-schematic.svg"); status.textContent = "Saved grid-schematic.svg."; };
    img.src = URL.createObjectURL(svgBlob);
  });
})();
