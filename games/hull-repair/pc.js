/* Hull Repair, Desktop boot only (loaded by pc.html). The guided tutorial for the Desktop layout: the Classic walkthrough
   names toolbar buttons, which the Desktop layout turns into icons, the Menu and windows. index.html uses these steps when
   they exist (window.HULL_REPAIR_PC_TUTORIAL_STEPS) and its own otherwise. */
window.HULL_REPAIR_PC_TUTORIAL_STEPS = [
  {
    title: "Welcome to the station",
    text: "Tern is dark and needs its power and pipes laid again, one room at a time. Join each pair of matching ports with a line. Nothing is timed, and a wrong line only costs you a tap to take it back. This walkthrough covers the Desktop layout. Skip it any time, and reopen it from the Menu.",
  },
  {
    selector: "#board-holder",
    title: "The board",
    text: "Solid shapes are sources and ringed shapes are sinks; a source and sink with the same shape and letter belong together. Drag from a port to lay a line and drop it on its partner. Lines never cross or share a cell. Holes are hull that is gone.",
  },
  {
    selector: "#line-chips",
    title: "Your lines",
    text: "Each line shows whether it is joined. Click one to clear just that line. Dragging back along a line shortens it, dragging across another line cuts it, and clicking the end of a line takes one cell back. The arrow keys, Enter and Backspace draw without the mouse.",
  },
  {
    selector: "#board-line",
    title: "Patched and restored",
    text: "Joining every line patches the room and lights it dimly. Covering every cell as well restores it fully. The dots mark cells nothing covers yet; every board has exactly one way to cover them all.",
  },
  {
    selector: "#hint-button",
    title: "Hints are free",
    text: "A nudge says where to start, a hint draws the opening of one line as a dotted ghost, and the answer draws the whole layout. Using them never costs anything, and the room still counts.",
  },
  {
    selector: "#goals",
    title: "Your goals",
    text: "Three goals stay in view, in any order. Every line you lay, erase or hint you ask for counts toward something on the screen.",
  },
  {
    selector: "#pc-menu-button",
    title: "Icons and the Menu",
    text: "The icons open the Station map, the Repair log, Achievements and Settings. The Menu, or Escape when nothing else is open, holds the rest: this tutorial, About and What's New. Each opens as a window over the game, and Escape closes the top one.",
  },
  {
    title: "You are ready",
    text: "Take your time. Your repairs are saved as you go.",
  },
];
