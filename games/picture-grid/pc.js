/* Picture Grid, Desktop boot only (loaded by pc.html). The guided tutorial for the Desktop layout: the Classic walkthrough
   points at the Gallery and Settings buttons, which the Desktop layout turns into icons, the Menu and windows. index.html uses
   these steps when they exist (window.PICTURE_GRID_PC_TUTORIAL_STEPS) and its own otherwise. */
window.PICTURE_GRID_PC_TUTORIAL_STEPS = [
  {
    title: "Welcome to the gallery",
    text: "Each frame hides a small picture. You work out which cells belong to it from the numbers on its rows and columns. Nothing is timed, nothing can go wrong, and you can skip this walkthrough at any time. It covers the Desktop layout; reopen it from the Menu.",
  },
  {
    selector: "#board",
    title: "The frame",
    text: "A number is the length of a run of filled cells in that row or column. 3 1 means a run of three, at least one empty cell, then a single filled cell. When a line's cells make exactly its numbers it turns grey with a tick. Drag along a line to mark several cells at once.",
  },
  {
    selector: "#mode-fill-button",
    title: "Fill and Dot",
    text: "Fill marks a cell that is part of the picture; Dot marks one you know is empty. F and X choose the tool, the arrow keys move the ring and Space marks. Undo and Redo are right beside them, and Clear row, Clear column and Clear frame ask nothing you cannot take back.",
  },
  {
    selector: "#hint-box",
    title: "Stuck? Ask",
    text: "The suggestion button never opens by itself. A nudge says which line has a certain move, a hint says what kind of reasoning works there, and the last rung fills that line after a question. Every picture can be finished without guessing.",
  },
  {
    selector: "#difficulty-slot",
    title: "Difficulty",
    text: "Easy, Normal and Hard change only how the suggestions open. The pictures, the numbers and your records are the same on all three.",
  },
  {
    selector: "#goals",
    title: "Your goals",
    text: "Three goals stay in view, in any order. Every cell you fill and every picture you hang counts toward something on the screen.",
  },
  {
    selector: "#pc-menu-button",
    title: "Icons and the Menu",
    text: "The icons open the Gallery wall (with the Slideshow of everything you have hung), Achievements and Settings. The Menu, or Escape when nothing else is open, holds this tutorial, About and What's New. Each opens as a window over the game, and Escape closes the top one. Six hung pictures in a gallery open the next.",
  },
  {
    title: "You are ready",
    text: "Take your time. Your progress is saved as you go, and the same save works on the Classic layout.",
  },
];
