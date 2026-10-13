(function () {
  "use strict";
  var STEP = 0.5;
  var MIN_SPEED = 0.5, MAX_SPEED = 12;
  var MIN_HOURS = 0.5, MAX_HOURS = 12;
  var currentSpeed = 0;
  var currentHours = 0;
  var isDragging = false;
  var startY = 0;
  var startOffset = 0;

  function init() {
    var container = document.getElementById("wheel-pickers");
    if (!container) return;
    container.hidden = false;

    ["speed", "hours"].forEach(function (key) {
      var picker = container.querySelector(".wheel-picker[data-key='" + key + "']");
      var track = picker.querySelector(".wheel-track");
      var content = picker.querySelector(".wheel-content");
      var valueEl = picker.querySelector(".wheel-value");

      var min = key === "speed" ? MIN_SPEED : MIN_HOURS;
      var max = key === "speed" ? MAX_SPEED : MAX_HOURS;
      var html = "";
      for (var v = min; v <= max + 0.001; v += STEP) {
        html += "<div class='wheel-option' data-val='" + v + "'>" + v.toFixed(1) + "</div>";
      }
      content.innerHTML = html;

      updatePosition(picker, content, valueEl, key === "speed" ? currentSpeed : currentHours);

      var onDown = function (e) { isDragging = true; startY = e.clientY || e.touches[0].clientY; startOffset = parseFloat(content.style.top) || 0; track.style.transition = "none"; };
      var onMove = function (e) { if (!isDragging) return; var y = e.clientY || e.touches[0].clientY; move(picker, content, valueEl, key, startOffset + (y - startY)); };
      var onUp = function () { if (!isDragging) return; isDragging = false; snap(picker, content, valueEl, key); track.style.transition = ""; };

      track.addEventListener("mousedown", onDown);
      track.addEventListener("touchstart", onDown, { passive: true });
      document.addEventListener("mousemove", onMove);
      document.addEventListener("touchmove", onMove, { passive: true });
      document.addEventListener("mouseup", onUp);
      document.addEventListener("touchend", onUp);
    });
  }

  function updatePosition(picker, content, valueEl, val) {
    var min = picker.dataset.key === "speed" ? MIN_SPEED : MIN_HOURS;
    var idx = Math.round((val - min) / STEP);
    var offset = -idx * 2.5;
    content.style.top = offset + "rem";
    valueEl.textContent = val.toFixed(1);
  }

  function move(picker, content, valueEl, key, rawOffset) {
    var min = picker.dataset.key === "speed" ? MIN_SPEED : MIN_HOURS;
    var max = picker.dataset.key === "speed" ? MAX_SPEED : MAX_HOURS;
    var totalOptions = Math.round((max - min) / STEP) + 1;
    var maxOffset = 0;
    var minOffset = -(totalOptions - 1) * 2.5;
    var clamped = Math.max(minOffset, Math.min(maxOffset, rawOffset));
    content.style.top = clamped + "rem";
    
    var val = min + (-clamped / 2.5) * STEP;
    val = Math.round(val / STEP) * STEP;
    if (key === "speed") currentSpeed = val; else currentHours = val;
    valueEl.textContent = val.toFixed(1);
  }

  function snap(picker, content, valueEl, key) {
    var top = parseFloat(content.style.top) || 0;
    var idx = Math.round(-top / 2.5);
    var min = picker.dataset.key === "speed" ? MIN_SPEED : MIN_HOURS;
    var val = min + idx * STEP;
    if (key === "speed") currentSpeed = val; else currentHours = val;
    updatePosition(picker, content, valueEl, val);
    
    window.dispatchEvent(new CustomEvent("dr-wheel-change", { detail: { key: key, value: val } }));
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
