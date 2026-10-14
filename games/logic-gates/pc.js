/* Logic Gates, Desktop boot only (loaded by pc.html). The guided tutorial for the Desktop layout: the Classic walkthrough points at
   buttons the Desktop layout moves into icons, the Menu and windows. index.html uses these steps when they exist
   (window.LOGIC_GATES_PC_TUTORIAL_STEPS) and its own otherwise. */
window.LOGIC_GATES_PC_TUTORIAL_STEPS = [
  {
    title: "Welcome to Meridian Relay",
    text: "Each board has switches on the left, lamps on the right, and a table the lamps must match. You wire chips between them. Nothing is timed. This walkthrough covers the Desktop layout. Skip it any time, and reopen it later from the Menu.",
  },
  {
    selector: "#level-goal",
    title: "The goal",
    text: "This sentence says what the lamps must do. The result table on the right checks every case at once and names the first one that is wrong.",
  },
  {
    selector: "#board-panel",
    title: "The board",
    text: "Solid thick wires carry 1, thin dashed wires carry 0. Click a round pin on a source, then a round pin on an input, to connect them. Flip the switches to see what your circuit does.",
  },
  {
    selector: "#board-panel",
    title: "Tie 1 and tie 0",
    text: "The two small boxes marked tie 1 and tie 0 are fixed inputs: a wire tied to 1 or to 0 for good. Use one when a chip needs a constant, for example tie one input of a NAND chip to 1 and it becomes an inverter. Hover a tie box for the same note.",
  },
  {
    selector: "#parts-panel",
    title: "Parts",
    text: "Add chips here. Every connection can also be chosen from a list on each chip. Undo, Clear and Restore mean nothing is ever lost. U undoes, N goes to the next level.",
  },
  {
    selector: "#check-panel",
    title: "Does it match?",
    text: "Every row must say Right. When they all do, the level is solved and the circuit becomes a chip you keep.",
  },
  {
    selector: "#hints-panel",
    title: "Stuck?",
    text: "A nudge, then a hint, then the answer in words with a button that puts it on the board. Asking takes nothing away.",
  },
  {
    selector: "#pc-menu-button",
    title: "Icons and the Menu",
    text: "The icons open the Levels (forty boards in five chapters), your Chips, Achievements and Settings. The Menu, or Escape when nothing else is open, holds the Sandbox, this tutorial, About Logic Gates with its named sources, the Station log and What's New. Each opens as a window over the game.",
  },
  {
    title: "You are ready",
    text: "Take your time. The station has waited eleven years.",
  },
];

/* Wire hover card (R4-LGPC-3): point at a wire to read its live value and the truth-table rows where it is 1.
   render.py writes data-value, data-src and (for small tables) data-rows on every .lg-wire; the board is rebuilt on every
   action, so everything is looked up from the pointer, never from a remembered element. Mouse-only extra: the same facts are
   in the board description and the truth table. */
(function () {
  "use strict";
  var card = null;

  function build() {
    card = document.createElement("div");
    card.className = "lg-wire-hover-card";
    card.setAttribute("aria-hidden", "true");
    card.hidden = true;
    card.innerHTML = '<span class="lg-wire-value"></span> <span class="lg-wire-rows"></span>';
    document.body.appendChild(card);
  }

  function hide() { if (card) card.hidden = true; }

  function onMove(e) {
    var wire = e.target && e.target.closest ? e.target.closest(".lg-wire") : null;
    if (!wire) { hide(); return; }
    if (!card) build();
    var src = wire.getAttribute("data-src") || "";
    var name = src.indexOf("in:") === 0 ? "Switch " + src.slice(3) : (src.indexOf("const:") === 0 ? "Tie " + src.slice(6) : "Chip output " + src);
    var rows = wire.getAttribute("data-rows");
    card.querySelector(".lg-wire-value").textContent = name + " is " + (wire.getAttribute("data-value") === "1" ? "1 (high)" : "0 (low)") + ".";
    card.querySelector(".lg-wire-rows").textContent = rows === null ? "" : (rows ? "High on rows: " + rows.split(" ").join(", ") : "High on no row.");
    card.hidden = false;
    var x = e.clientX + 14, y = e.clientY + 14;
    var w = card.offsetWidth, h = card.offsetHeight;
    if (x + w > window.innerWidth - 4) x = Math.max(4, e.clientX - w - 14);
    if (y + h > window.innerHeight - 4) y = Math.max(4, e.clientY - h - 14);
    card.style.left = x + "px";
    card.style.top = y + "px";
  }

  function init() {
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseleave", hide);
    window.addEventListener("blur", hide);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
