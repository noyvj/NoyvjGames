(function () {
  "use strict";
  var selectedShelf = null;
  var TAP_MS = 200;
  var DRAG_PX = 10;

  function init() {
    document.addEventListener("pointerdown", onPointerDown, true);
    document.addEventListener("pointerup", onPointerUp, true);
    document.addEventListener("dragstart", onDragStart, false);
    document.addEventListener("drop", onDrop, false);
  }

  function onPointerDown(e) {
    var shelf = e.target.closest(".shelf");
    if (!shelf || shelf.classList.contains("empty")) return;
    shelf._px = e.clientX;
    shelf._py = e.clientY;
    shelf._pt = Date.now();
  }

  function onPointerUp(e) {
    var shelf = e.target.closest(".shelf");
    if (!shelf || shelf.classList.contains("empty")) return;
    var dx = Math.abs(e.clientX - shelf._px);
    var dy = Math.abs(e.clientY - shelf._py);
    var dt = Date.now() - shelf._pt;

    if (dx > DRAG_PX || dy > DRAG_PX) return;
    if (dt < TAP_MS) toggleSelection(shelf);
  }

  function toggleSelection(shelf) {
    var was = shelf.classList.contains("selected");
    document.querySelectorAll(".shelf.selected").forEach(function (s) { s.classList.remove("selected"); });
    if (!was) {
      shelf.classList.add("selected");
      selectedShelf = shelf;
    } else {
      selectedShelf = null;
    }
  }

  function onDragStart(e) {
    var shelf = e.target.closest(".shelf");
    if (!shelf || shelf.classList.contains("empty")) return;
    e.dataTransfer.setData("text/plain", shelf.dataset.supply);
    e.dataTransfer.effectAllowed = "copy";
    selectedShelf = shelf;
    document.querySelectorAll(".shelf.selected").forEach(function (s) { s.classList.remove("selected"); });
    shelf.classList.add("selected");
  }

  function onDrop(e) {
    var patient = e.target.closest(".patient");
    if (!patient || !selectedShelf) return;
    e.preventDefault();
    applySupply(selectedShelf, patient);
    clearSelection();
  }

  document.addEventListener("click", function (e) {
    var patient = e.target.closest(".patient");
    if (!patient || !selectedShelf) return;
    if (e.target.tagName === "BUTTON" || e.target.closest("button")) return;
    applySupply(selectedShelf, patient);
    clearSelection();
  });

  function applySupply(shelf, patient) {
    var supply = shelf.dataset.supply;
    var pid = patient.id || patient.dataset.patientId;
    document.dispatchEvent(new CustomEvent("station-medic-apply-supply", {
      detail: { supply: supply, patientId: pid }
    }));
  }

  function clearSelection() {
    document.querySelectorAll(".shelf.selected").forEach(function (s) { s.classList.remove("selected"); });
    selectedShelf = null;
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
