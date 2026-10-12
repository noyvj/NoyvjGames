/* Reaction Bench, Desktop boot only (loaded by pc.html). The guided tutorial for the Desktop layout: the Classic walkthrough points
   at the Orders, Periodic table and Settings buttons, which the Desktop layout turns into icons, the Menu and windows, and puts the
   ledger and the suggestion box in a side column. index.html uses these steps when they exist (window.REACTION_BENCH_PC_TUTORIAL_STEPS)
   and its own otherwise. */
window.REACTION_BENCH_PC_TUTORIAL_STEPS = [
  {
    title: "Welcome to the night shift",
    text: "Each order is a chemical equation. You turn a dial in front of every formula until the atoms on both sides are equal, then run it and the compound goes on the shelf. Nothing is timed and nothing can go wrong. This walkthrough covers the Desktop layout. Skip it any time and reopen it from the Menu.",
  },
  {
    selector: "#bench",
    title: "Dials in front of each formula",
    text: "A conical flask is something that goes in and a round flask is something that comes out. The number on a dial says how many of that substance take part. Use the plus and minus buttons, or the arrow keys and the digits.",
  },
  {
    selector: "#ledger-block",
    title: "The atom ledger and Run",
    text: "In the column on the right a table counts every element on the left and on the right. Each row shows a tick and the word Equal, or a cross and how many too many or too few. When every row reads equal, Run works. Reset dials is free.",
  },
  {
    selector: "#hint-box",
    title: "Stuck? Ask",
    text: "The suggestion button never opens by itself. A nudge says where to look, a hint says what to turn, and the last rung gives the answer after a question. Every order can be finished without guessing.",
  },
  {
    selector: "#difficulty-slot",
    title: "Difficulty",
    text: "Easy, Normal and Hard change only how the suggestions open. The orders, the proofs and your records are the same on all three.",
  },
  {
    selector: "#goals",
    title: "Your goals",
    text: "Three goals stay in view, in any order. Every dial you turn and every compound you shelve counts toward something on the screen.",
  },
  {
    selector: "#pc-menu-button",
    title: "Icons and the Menu",
    text: "The icons open the order board, the shelf, the periodic table (every lit tile has a card), Achievements and Settings. The Menu, or Escape when nothing else is open, holds this tutorial, About and What's New. Each opens as a window over the bench, and Escape closes the top one. Five shelved orders in a chapter open the next; from chapter 2 you choose what comes out first, and in the last chapter each route has two steps.",
  },
  {
    title: "You are ready",
    text: "Take your time. Your progress is saved as you go, and the same save works on the Classic layout. Press ? at any time for the keyboard help.",
  },
];
