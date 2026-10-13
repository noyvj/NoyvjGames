/* Dead Reckoning, Desktop boot only (loaded by pc.html). The guided tutorial for the Desktop layout: the Classic walkthrough points at
   buttons the Desktop layout moves into icons, the Menu and windows. index.html uses these steps when they exist
   (window.DEAD_RECKONING_PC_TUTORIAL_STEPS) and its own otherwise. */
window.DEAD_RECKONING_PC_TUTORIAL_STEPS = [
  {
    title: "Welcome, navigator",
    text: "You know your speed, your heading and the time, and nothing else about where the ship is. Plot a course, sail it, then see how far the sea moved you from your estimate. This walkthrough covers the Desktop layout. Skip it any time, and reopen it later from the Menu (or press Escape).",
  },
  {
    selector: "#chart-goal",
    title: "The goal",
    text: "Reach the flag, inside its ring, before the deadline. The deadline is in hours of sailing, never real time: nothing here is timed. On a two-ship chart each ship has its own flag and deadline, and the two must stay at least a mile apart: the Ship A and Ship B buttons (keys 1 and 2) choose which one you are planning.",
  },
  {
    selector: "#chart-holder",
    title: "The chart",
    text: "Hazards are hatched or dotted shapes with names. A stream is a dashed zone with an arrow and a range in knots; the truth lies somewhere in the range. Click the chart to mark a point for the ruler.",
  },
  {
    selector: "#planner-panel",
    title: "Your plan",
    text: "A plan is a list of legs: a heading in degrees, a speed in knots and a time in hours. The dashed line on the chart is your plot of where you think each leg takes you. A, Enter, S and Z are the quick keys.",
  },
  {
    selector: "#allow-checkbox",
    title: "Allow for the chart",
    text: "With this on, your plot adds the middle of every range the chart prints (streams, wind, compass error). Off, it is plain dead reckoning: heading, speed and time only.",
  },
  {
    selector: "#sail-button",
    title: "Sail",
    text: "Sail shows the real track as a solid line, with the gap to your plot marked each hour, and tells you exactly how the stars were earned. You may retry with the same plan and tune it.",
  },
  {
    selector: "#pc-menu-button",
    title: "Icons and the Menu",
    text: "The icons open the Charts (seven chapters, the last with two ships to plan at once, and a practice mode), your Achievements and Settings. The Menu, or Escape when nothing else is open, holds the rest: this tutorial, About Dead Reckoning with its named sources, the Captain's log and What's New. Each opens as a window over the game, and Escape closes the top one.",
  },
  {
    selector: "#quick-leg-input",
    title: "Quick leg input",
    text: "Type a leg here as heading speed hours (e.g., 090 6kn 2h) and press Enter to add it instantly. Works with or without units.",
  },
  {
    title: "You are ready",
    text: "Fair weather. Take your time.",
  },
];

// Quick leg input (PC only) --------------------------------------------------
(function () {
  var input = document.getElementById("quick-leg-input");
  if (!input) return;
  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter") {
      e.preventDefault();
      var val = input.value.trim();
      if (!val) return;
      var parts = val.split(/\s+/);
      var h = parseInt(parts[0], 10);
      var s = parseFloat(parts[1]);
      var t = parseFloat(parts[2]);
      if (isNaN(h) || isNaN(s) || isNaN(t)) {
        input.setCustomValidity("Format: heading speed hours (e.g., 090 6kn 2h)");
        return;
      }
      input.setCustomValidity("");
      window.dispatchEvent(new CustomEvent("dead-reckoning-quick-leg", { detail: { heading: h, speed: s, hours: t } }));
      input.value = "";
    }
  });
})();

// Chart zoom & pan (PC only) -------------------------------------------------
(function () {
  var holder = document.getElementById("chart-holder");
  if (!holder) return;
  var svg = holder.querySelector("svg.dr-chart");
  if (!svg) return;

  var scale = 1, tx = 0, ty = 0;
  var MIN_SCALE = 0.5, MAX_SCALE = 4;
  var dragging = false, startX, startY, startTx, startTy;
  var reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function applyTransform() {
    svg.style.transform = "translate(" + tx + "px, " + ty + "px) scale(" + scale + ")";
    svg.style.transformOrigin = "center center";
  }

  holder.addEventListener("wheel", function (e) {
    if (reducedMotion) return;
    e.preventDefault();
    var rect = holder.getBoundingClientRect();
    var cx = e.clientX - rect.left;
    var cy = e.clientY - rect.top;
    var factor = e.deltaY < 0 ? 1.1 : 1 / 1.1;
    var newScale = Math.min(MAX_SCALE, Math.max(MIN_SCALE, scale * factor));
    if (newScale === scale) return;

    tx = cx - (cx - tx) * (newScale / scale);
    ty = cy - (cy - ty) * (newScale / scale);
    scale = newScale;
    applyTransform();
  }, { passive: false });

  holder.addEventListener("mousedown", function (e) {
    if (e.button !== 0) return;
    dragging = true;
    startX = e.clientX;
    startY = e.clientY;
    startTx = tx;
    startTy = ty;
    holder.classList.add("grabbing");
  });

  window.addEventListener("mousemove", function (e) {
    if (!dragging) return;
    tx = startTx + (e.clientX - startX);
    ty = startTy + (e.clientY - startY);
    applyTransform();
  });

  window.addEventListener("mouseup", function () {
    if (dragging) {
      dragging = false;
      holder.classList.remove("grabbing");
    }
  });

  document.addEventListener("keydown", function (e) {
    if ((e.key === "r" || e.key === "R") && !e.ctrlKey && !e.metaKey && !e.altKey) {
      if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;
      scale = 1; tx = 0; ty = 0;
      applyTransform();
    }
  });

  window.matchMedia("(prefers-reduced-motion: reduce)").addEventListener("change", function (e) {
    reducedMotion = e.matches;
  });
})();
