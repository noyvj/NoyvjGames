(function () {
  "use strict";
  var CHART = document.getElementById("chart-holder");
  if (!CHART) return;

  // Respect system reduced-motion preference
  if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  var MARKER = null;
  var TIMER = null;
  var START_X = 0, START_Y = 0;
  var THRESHOLD = 15;

  function dropMark(x, y) {
    if (MARKER) removeMark();
    MARKER = document.createElementNS("http://www.w3.org/2000/svg", "g");
    MARKER.setAttribute("class", "dr-fix-mark");
    MARKER.innerHTML = '<circle cx="0" cy="0" r="6" fill="none" stroke="var(--accent)" stroke-width="2"/><line x1="-8" y1="0" x2="8" y2="0" stroke="var(--accent)" stroke-width="2"/><line x1="0" y1="-8" x2="0" y2="8" stroke="var(--accent)" stroke-width="2"/>';
    MARKER.setAttribute("transform", "translate(" + x + "," + y + ")");
    CHART.querySelector(".dr-chart").appendChild(MARKER);
  }

  function removeMark() {
    if (MARKER) { MARKER.remove(); MARKER = null; }
  }

  CHART.addEventListener("touchstart", function (e) {
    START_X = e.touches[0].clientX;
    START_Y = e.touches[0].clientY;
    TIMER = setTimeout(function () {
      var rect = CHART.getBoundingClientRect();
      var x = e.touches[0].clientX - rect.left;
      var y = e.touches[0].clientY - rect.top;
      dropMark(x, y);
    }, 500);
  }, { passive: true });

  CHART.addEventListener("touchmove", function (e) {
    var dx = e.touches[0].clientX - START_X;
    var dy = e.touches[0].clientY - START_Y;
    if (dx * dx + dy * dy > THRESHOLD * THRESHOLD) {
      clearTimeout(TIMER);
      TIMER = null;
    }
  }, { passive: true });

  CHART.addEventListener("touchend", function () {
    clearTimeout(TIMER);
    TIMER = null;
  });

  CHART.addEventListener("touchcancel", function () {
    clearTimeout(TIMER);
    TIMER = null;
  });
})();
