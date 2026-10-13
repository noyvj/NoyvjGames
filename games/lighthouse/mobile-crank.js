(function () {
  "use strict";
  var THRESHOLD = 360;
  var container = null;
  var svg = null;
  var handle = null;
  var startAngle = 0;
  var currentRotation = 0;
  var totalRotation = 0;
  var isDragging = false;

  function init() {
    if (document.getElementById("crank-container")) return;
    if (document.documentElement.getAttribute("data-reduced-motion") === "true") return;
    container = document.createElement("div");
    container.id = "crank-container";
    container.className = "crank-wrap";
    container.innerHTML = '<svg class="crank-svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="40" fill="none" stroke="var(--edge)" stroke-width="2"/><line class="crank-handle" x1="50" y1="50" x2="50" y2="10" stroke="var(--accent)" stroke-width="4" stroke-linecap="round"/></svg><span class="crank-label">Wind</span>';
    document.body.appendChild(container);
    svg = container.querySelector(".crank-svg");
    handle = container.querySelector(".crank-handle");
    bindEvents();
  }

  function getAngle(e) {
    var rect = svg.getBoundingClientRect();
    var cx = rect.left + rect.width / 2;
    var cy = rect.top + rect.height / 2;
    var clientX = e.touches ? e.touches[0].clientX : e.clientX;
    var clientY = e.touches ? e.touches[0].clientY : e.clientY;
    return Math.atan2(clientY - cy, clientX - cx) * (180 / Math.PI);
  }

  function bindEvents() {
    svg.addEventListener("mousedown", onDown);
    svg.addEventListener("touchstart", onDown, { passive: false });
    window.addEventListener("mousemove", onMove);
    window.addEventListener("touchmove", onMove, { passive: false });
    window.addEventListener("mouseup", onUp);
    window.addEventListener("touchend", onUp);
  }

  function onDown(e) {
    isDragging = true;
    startAngle = getAngle(e) - currentRotation;
    e.preventDefault();
  }

  function onMove(e) {
    if (!isDragging) return;
    var angle = getAngle(e);
    var delta = angle - (startAngle + currentRotation);
    if (delta > 180) delta -= 360;
    if (delta < -180) delta += 360;
    currentRotation += delta;
    totalRotation += delta;
    handle.style.transform = "rotate(" + currentRotation + "deg)";
    e.preventDefault();
  }

  function onUp() {
    if (!isDragging) return;
    isDragging = false;
    if (Math.abs(totalRotation) >= THRESHOLD) {
      triggerWind();
      totalRotation = 0;
      currentRotation = 0;
      handle.style.transform = "rotate(0deg)";
    }
  }

  function triggerWind() {
    var amount = Math.floor(Math.abs(totalRotation) / THRESHOLD);
    document.dispatchEvent(new CustomEvent("lighthouse-crank-wound", { detail: amount }));
  }

  window.lighthouseInitCrank = init;
})();
