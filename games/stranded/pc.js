/* Stranded, Desktop boot only (loaded by pc.html). The guided tutorial for the Desktop layout: the Classic walkthrough
   names toolbar buttons, which the Desktop layout turns into icons, the Menu and windows, and the goals sit in a side column.
   index.html uses these steps when they exist (window.STRANDED_PC_TUTORIAL_STEPS) and its own otherwise. */
window.STRANDED_PC_TUTORIAL_STEPS = [
  {
    title: "Welcome to the line",
    text: "You are Harbour, the plain voice on a thin text line to Ines, a stubborn field engineer stuck on a small moon. Every reply you send gets an answer. Nothing is timed, and you can go back to any choice for free. This walkthrough covers the Desktop layout. Skip it any time, and reopen it from the Menu.",
  },
  {
    selector: "#chat",
    title: "The conversation",
    text: "Ines speaks on the left, you on the right. Each of your messages has a Rewind to here button: it takes you back to just before that reply, and nothing you found or tried is lost.",
  },
  {
    selector: "#stats",
    title: "Trust, Supplies and Hope",
    text: "Your replies move these three numbers. They are always shown as a number, a word and a bar. They can open or shut some replies, and they help decide which of the ten endings you reach.",
  },
  {
    selector: "#comms-panel",
    title: "Your replies",
    text: "Pick one of two to four replies, or press its number. A reply marked Tried is one you have sent before. A shut reply says why it is shut. After two different tries in a scene, What if? shows where each reply leads.",
  },
  {
    selector: "#goals",
    title: "Your goals",
    text: "Three goals stay in view in the side column, in any order, with the progress numbers beneath. Every reply, rewind and find counts toward something on the screen.",
  },
  {
    selector: "#hint-box",
    title: "Need a nudge?",
    text: "Only when you ask: a nudge, a hint, then the answer, and a button that takes you there.",
  },
  {
    selector: "#pc-menu-button",
    title: "Icons and the Menu",
    text: "The icons open the Branch map, the Archive, the Achievements and Settings. The Menu, or Escape when nothing else is open, holds the rest: this tutorial, About and What's New. Each opens as a window over the game, and Escape closes the top one.",
  },
  {
    title: "You are ready",
    text: "Take your time. Your map and archive are saved as you go.",
  },
];
