/* Mirror Lab, Desktop boot only (loaded by pc.html). The guided tutorial for the Desktop layout: the Classic walkthrough
   names toolbar buttons, which the Desktop layout turns into icons, the Menu and windows, and puts the tray in a side column.
   index.html uses these steps when they exist (window.MIRROR_LAB_PC_TUTORIAL_STEPS) and its own otherwise. */
window.MIRROR_LAB_PC_TUTORIAL_STEPS = [
  {
    title: "Welcome to Arden Relay",
    text: "The light guides here were smashed. On each bench a beam leaves the emitter and you place pieces so it reaches every sensor. Nothing is timed and nothing is lost: any piece can be picked up again. This walkthrough covers the Desktop layout. Skip it any time, and reopen it from the Menu.",
  },
  {
    selector: "#tray",
    title: "The tray",
    text: "These are the pieces you have for this bench, in the column on the right. Click one to choose it, or drag it onto the bench. The count says how many are left.",
  },
  {
    selector: "#bench-holder",
    title: "The bench",
    text: "Dashed squares are slots. Click a slot to place the chosen piece and the beam redraws at once. Click a placed mirror or prism to flip it, drag a piece to move it, or drag it off the bench to pick it up. A white beam is a thin solid line, an S beam is short dashes marked S and an L beam is long dashes marked L.",
  },
  {
    selector: "#sensor-list",
    title: "Sensors, in words",
    text: "Every sensor is listed here in words as well as on the picture. A lit sensor is filled with a tick. A sensor with a cross is a decoy and must stay dark. A sensor never stops a beam.",
  },
  {
    selector: "#hint-button",
    title: "Hints are free",
    text: "A nudge says which piece matters and roughly where, a hint draws one piece as a dotted ghost, and the answer draws them all. They only come when you press, and the bench still counts.",
  },
  {
    selector: "#goals",
    title: "Your goals",
    text: "Three goals stay in view, in any order. Pieces you place, benches you clear and hints you ask for all count toward something on the screen.",
  },
  {
    selector: "#difficulty-panel",
    title: "Easy, Normal or Hard",
    text: "Normal is the game as designed. Easy and Hard only change how much help the hint ladder gives. Nothing is locked by any choice.",
  },
  {
    selector: "#pc-menu-button",
    title: "Icons and the Menu",
    text: "The icons open the Benches map, the Bench Log, Achievements and Settings. Clear 5 benches of a chapter to open the next. The Menu, or Escape when nothing else is open, holds the rest: this tutorial, About and What's New. Each opens as a window over the game, and Escape closes the top one.",
  },
  {
    title: "You are ready",
    text: "Take your time. Your benches are saved as you go.",
  },
];
