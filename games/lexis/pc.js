/* Lexis, Desktop boot only (loaded by pc.html). The guided tutorial for the Desktop layout: the Classic
   walkthrough points at the Crew log and About buttons, which the Desktop layout moves into icons, the Menu
   and windows. index.html uses these steps when they exist (window.LEXIS_PC_TUTORIAL_STEPS) and its own
   otherwise. */
window.LEXIS_PC_TUTORIAL_STEPS = [
  {
    title: "Welcome, officer",
    text: "You are the communications officer on a survey ship. Each planet speaks a language nobody has translated: your job is to work out what its signals mean, then answer. This walkthrough covers the Desktop layout. Skip it any time, and reopen it later from the Menu (or press Escape).",
  },
  {
    selector: "#pc-readouts",
    title: "Contact at a glance",
    text: "This chip counts the planets you have made contact with. Contact is how the story moves on: each one brings the next planet into range and adds a crew log entry.",
  },
  {
    selector: "#goal-line",
    title: "The crew's request",
    text: "The crew tells you what they need from each planet. When you manage it, contact is made. The planet tabs just above choose which world you are looking at; the next one stays out of range until the last one answers.",
  },
  {
    selector: "#transmissions-panel",
    title: "Watch what happens",
    text: "Each transmission is a signal and what the station did when it arrived. Press Receive next transmission, then compare them: what stays the same, and what changes? Everything you need is shown here before you are asked to rely on it.",
  },
  {
    selector: "#notebook-panel",
    title: "Write your guesses",
    text: "On the right is your notebook. Write what you think each group of marks means. Nothing here is marked right or wrong. Ticking entries and pressing Check tells you how many are right, never which.",
  },
  {
    selector: "#transmit-panel",
    title: "Answer",
    text: "Build a signal and send it. On Planet 1 you can type S for a short tick and L for a long bar, Backspace to take the last mark off and Delete to clear it. The station answers in its own terms, and when it cannot understand you, it says why.",
  },
  {
    selector: "#tab-compound",
    title: "Planet 2",
    text: "When planet 1 answers, a second world comes into range. Its signs are built from parts, so learning the parts lets you read signs nobody showed you.",
  },
  {
    selector: "#tab-bridge",
    title: "Planet 3",
    text: "The third world builds on the first two: things you learned on planet 2, numbers from planet 1, and a few new marks that change what a message does. Contact here needs a particular result on its counter, and the crew tells you which.",
  },
  {
    selector: "#pc-menu-button",
    title: "Icons and the Menu",
    text: "The three icons open the Crew log, your Achievements and Settings (text size, reduce motion, effects, high contrast and the theme). The Menu, or Escape when nothing else is open, holds the rest: this tutorial, About Lexis with its named sources, What's New, and the Contact report once you reach planet 3. Each opens as a window over the game, and Escape closes the top one.",
  },
  {
    title: "You are ready",
    text: "Every word can be worked out from what you are shown. Take your time.",
  },
];
