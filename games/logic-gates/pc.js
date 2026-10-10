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
