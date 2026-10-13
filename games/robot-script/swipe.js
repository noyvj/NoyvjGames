/**
 * swipe.js - Mobile swipe-to-delete for the instruction list.
 */
(function () {
  "use strict";
  var THRESHOLD = 40;
  var undoBar = null;
  var swipedNode = null;
  var startX = 0;
  var currentX = 0;

  function init() {
    if (document.documentElement.getAttribute("data-reduced-motion") === "true") return;
    var editor = document.getElementById("editor-panel");
    if (!editor) return;
    editor.addEventListener("touchstart", onTouchStart, { passive: false });
    editor.addEventListener("touchmove", onTouchMove, { passive: false });
    editor.addEventListener("touchend", onTouchEnd);
  }

  function onTouchStart(e) {
    var node = e.target.closest(".node");
    if (!node || node.querySelector("button") || node.querySelector("select")) return;
    startX = e.touches[0].clientX;
    currentX = startX;
    swipedNode = node;
  }

  function onTouchMove(e) {
    if (!swipedNode) return;
    currentX = e.touches[0].clientX;
    var diff = currentX - startX;
    if (diff < -THRESHOLD / 2) {
      swipedNode.style.transform = "translateX(" + Math.max(diff, -50) + "px)";
    } else {
      swipedNode.style.removeProperty("transform");
    }
  }

  function onTouchEnd(e) {
    if (!swipedNode) return;
    var diff = currentX - startX;
    if (diff < -THRESHOLD) {
      swipedNode.classList.add("swiped");
      showUndoBar(swipedNode);
    } else {
      swipedNode.style.removeProperty("transform");
    }
    swipedNode = null;
  }

  function showUndoBar(node) {
    if (!undoBar) {
      undoBar = document.createElement("div");
      undoBar.className = "undo-bar";
      var btnUndo = document.createElement("button");
      btnUndo.textContent = "Undo";
      btnUndo.addEventListener("click", function () {
        hideUndoBar();
        restoreNode(swipedNode);
      });
      var btnDelete = document.createElement("button");
      btnDelete.textContent = "Delete";
      btnDelete.addEventListener("click", function () {
        dispatchDelete(swipedNode);
      });
      undoBar.appendChild(btnUndo);
      undoBar.appendChild(btnDelete);
      document.body.appendChild(undoBar);
    }
    node.style.position = "absolute";
    node.style.left = "-200%";
    undoBar.classList.add("visible");
  }

  function dispatchDelete(node) {
    document.dispatchEvent(new CustomEvent("robotScriptSwipeDelete", { detail: node.dataset.a }));
    hideUndoBar();
    restoreNode(node);
  }

  function hideUndoBar() {
    if (undoBar) undoBar.classList.remove("visible");
  }

  function restoreNode(node) {
    node.style.position = "";
    node.style.left = "";
    node.classList.remove("swiped");
    hideUndoBar();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
