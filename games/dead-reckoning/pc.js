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

// Quick leg input (R4-DEPC-1). pc.js loads in the head, so everything that touches the page waits for DOMContentLoaded. ------------
// "090 6kn 2h" is heading, speed and hours (units optional). Enter adds the leg through the engine (app.js listens for the event);
// the engine forces the numbers onto the chart's legal grid, so the leg row shows what was really added. L focuses the box.
document.addEventListener("DOMContentLoaded", function () {
  var input = document.getElementById("quick-leg-input");
  if (!input) return;
  input.hidden = false;
  var note = document.createElement("p");
  note.id = "quick-leg-note";
  note.className = "note";
  note.setAttribute("role", "status");
  input.setAttribute("aria-describedby", "quick-leg-note");
  input.parentNode.insertBefore(note, input.nextSibling);
  note.textContent = "Type a leg as heading, speed, hours (for example 090 6kn 2h), then Enter. Press L to jump here.";

  var PATTERN = /^\s*(\d{1,3})\s+(\d+(?:\.\d+)?)\s*(?:kn|kt|kts|knots?)?\s+(\d+(?:\.\d+)?)\s*(?:h|hr|hrs|hours?)?\s*$/i;

  input.addEventListener("keydown", function (e) {
    if (e.key !== "Enter") return;
    e.preventDefault();
    var raw = input.value.trim();
    if (!raw) return;
    var m = PATTERN.exec(raw);
    var heading = m ? parseInt(m[1], 10) : NaN;
    var hours = m ? parseFloat(m[3]) : NaN;
    if (!m || heading > 360 || !(hours > 0)) {
      input.setAttribute("aria-invalid", "true");
      note.textContent = "That is not a leg. Write heading, speed and hours, like 090 6kn 2h.";
      return;
    }
    input.removeAttribute("aria-invalid");
    document.dispatchEvent(new CustomEvent("dead-reckoning-quick-leg", { detail: { heading: heading % 360, speed: parseFloat(m[2]), hours: hours } }));
    input.value = "";
    note.textContent = "Leg added. The plan shows the values the chart allows.";
  });

  document.addEventListener("keydown", function (e) {
    if (e.key !== "l" && e.key !== "L") return;
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    var t = e.target;
    if (t && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT|BUTTON)$/.test(t.tagName))) return;
    if (input.offsetParent === null) return;      // the plan column is not showing a plan
    e.preventDefault();
    input.focus();
  });
});

// Print layout (Ctrl+P) -------------------------------------------------------
(function () {
  document.addEventListener("keydown", function (e) {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "p") {
      e.preventDefault();
      window.print();
    }
  });
})();
