/* Constellations, Desktop boot only (loaded by pc.html). The guided tutorial for the Desktop layout: the Classic walkthrough points at the
   Charts, Sky Atlas and Settings buttons, which the Desktop layout turns into icons, the Menu and windows. index.html uses these steps when
   they exist (window.CONSTELLATIONS_PC_TUTORIAL_STEPS) and its own otherwise. */
window.CONSTELLATIONS_PC_TUTORIAL_STEPS = [
  {
    title: "Welcome to the observatory",
    text: "Each chart is a patch of real sky. You join the stars with lines until the shape that appears is a constellation, and it is kept in your Sky Atlas. Nothing is timed, nothing can go wrong, and you can skip this walkthrough at any time. It covers the Desktop layout; reopen it from the Menu.",
  },
  {
    selector: "#board",
    title: "Reading the numbers",
    text: "A number on a star says how many lines must touch it. A star with no number can have any number of lines, or none. Lines may not cross, and all the lines together must make one connected shape. A number that holds gets a double ring and a tick.",
  },
  {
    selector: "#board",
    title: "Drawing a line",
    text: "Drag from one star to another, or tap one star and then the next. Press the same two stars again to take the line away. With the keyboard, arrow keys move the ring, a letter jumps to that star and Space picks it up. A thick double line is already drawn for you; a pair with a cross through it can never be joined.",
  },
  {
    selector: "#undo-button",
    title: "Undo and Done",
    text: "Undo, Redo and Erase my lines are always at hand in the right-hand column. When every number holds and the lines make one piece, Done adds the constellation to your atlas.",
  },
  {
    selector: "#hint-box",
    title: "Stuck? Ask",
    text: "The suggestion button never opens by itself. A nudge says which star has a certain line, a hint shows the line and why it is certain, and the last rung shows the whole shape. Every chart can be finished without guessing.",
  },
  {
    selector: "#difficulty-slot",
    title: "Difficulty",
    text: "Easy, Normal and Hard change only how the suggestions open. The charts, the numbers and your records are the same on all three.",
  },
  {
    selector: "#goals",
    title: "Your goals",
    text: "Three goals stay in view, in any order. Every line you draw and every constellation you find counts toward something on the screen.",
  },
  {
    selector: "#pc-menu-button",
    title: "Icons and the Menu",
    text: "The icons open the Charts (five seasons of eight; five found in a season open the next page), the Sky Atlas with a card for every constellation you find, Achievements and Settings. The Menu, or Escape when nothing else is open, holds this tutorial, About and What's New. Each opens as a window over the game, and Escape closes the top one.",
  },
  {
    title: "You are ready",
    text: "Take your time. Your progress is saved as you go, and the same save works on the Classic layout.",
  },
];
