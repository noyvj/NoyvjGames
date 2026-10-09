/* Robot Script, Desktop boot only (loaded by pc.html). The guided tutorial for the Desktop layout: the Classic
   walkthrough names toolbar buttons, which the Desktop layout turns into icons, the Menu and windows, and the list
   editor sits in a side column. index.html uses these steps when they exist (window.ROBOT_SCRIPT_PC_TUTORIAL_STEPS)
   and its own otherwise. */
window.ROBOT_SCRIPT_PC_TUTORIAL_STEPS = [
  {
    title: "Welcome to the deck",
    text: "A maintenance robot does exactly what your list says. Write the list, press Run, and watch. Nothing is timed, and a run that goes wrong costs nothing. This walkthrough covers the Desktop layout. Skip it any time, and reopen it from the Menu.",
  },
  {
    selector: "#room-panel",
    title: "The room",
    text: "The robot starts on its tile facing the way its nose points. The checklist above the room says what the room needs. Parts are diamonds, sockets are dashed frames, switches are numbered plates and doors are barred and lettered.",
  },
  {
    selector: "#pc-side",
    title: "Your list",
    text: "The side column holds your list. Tap an instruction to add it where the marked gap is, tap another gap to add somewhere else, and use the arrows and the x to rearrange or remove steps. Every instruction is one step.",
  },
  {
    selector: "#run-button",
    title: "Run, Step and Skip",
    text: "Run plays your list. Step does one action at a time and Skip jumps to the end. If the robot cannot do a step it stops there and says why. Your list stays, so fix it and run again.",
  },
  {
    selector: "#size-line",
    title: "Steps and medals",
    text: "Fewer steps earn better medals: gold at the reference length, silver a little over, bronze for any clear. Hints are free and never touch a medal.",
  },
  {
    selector: "#goals",
    title: "Your goals",
    text: "Three goals stay in view, in any order. Every run, every step you write and every hint you ask for counts toward something on the screen.",
  },
  {
    selector: "#pc-menu-button",
    title: "Icons and the Menu",
    text: "The icons open the Rooms, Scrap's Workshop, Achievements and Settings. The Menu, or Escape when nothing else is open, holds the rest: this tutorial, About and What's New. Each opens as a window over the game, and Escape closes the top one.",
  },
  {
    title: "You are ready",
    text: "Take your time. Your lists and medals are saved as you go.",
  },
];
