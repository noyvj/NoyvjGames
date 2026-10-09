/* Heist Committee, Desktop boot only (loaded by pc.html). The guided tutorial for the Desktop layout: the Classic
   walkthrough points at the cash strip and toolbar buttons, which the Desktop layout turns into readout chips, icons
   and the Menu. index.html uses these steps when they exist (window.HEIST_COMMITTEE_PC_TUTORIAL_STEPS) and its
   own otherwise. */
window.HEIST_COMMITTEE_PC_TUTORIAL_STEPS = [
  {
    title: "Welcome to the committee",
    text: "You never control the heist itself. You control the plan: who does what, and when. Then you watch it play out, and whatever goes wrong goes wrong for a reason you can read. This walkthrough covers the Desktop layout. Skip it any time, and reopen it later from the Menu (or press Escape).",
  },
  {
    selector: "#pc-readouts",
    title: "Cash, reputation and where you are",
    text: "Cash pays the crew and buys gear. Reputation opens new jobs, new crew and new gear, and only goes up when a job goes better than you managed before. The last chip says which stage you are on.",
  },
  {
    selector: "#board-cards",
    title: "Pick a job",
    text: "Each job is a target with a prize. A bad night still pays a little, nobody is ever eliminated, and more jobs open as your reputation grows.",
  },
  {
    selector: "#pc-stage",
    title: "Everything happens here",
    text: "Scouting, hiring, planning, playback and the payout all take turns in this window. Scout to learn what might go wrong, hire five of eight crew (each has a visible trait and a quirk you discover by watching them or paying for a background check), then fill the timeline: rows are crew, columns are beats. Pick an action and tap cells, or drag it, or use the arrow keys and Enter.",
  },
  {
    title: "The checklist and Standby",
    text: "While planning, the list beside the timeline says which goals your plan covers, which actions are missing something they need and which crew will clash. Warnings never block you. A crew member on Standby for one kind of trouble absorbs it; standing around costs a turn.",
  },
  {
    title: "Watch it play",
    text: "Next beat reveals the job one beat at a time, and every line says why it happened. The payout shows the chain of events and which link started it. Retry the same night with a better plan any time.",
  },
  {
    selector: "#pc-menu-button",
    title: "Icons and the Menu",
    text: "The three icons open the Minutes of the Committee, your Achievements and Settings. The Menu, or Escape when nothing else is open, holds the rest: this tutorial, How it works and What's New. Each opens as a window over the game, and Escape closes the top one.",
  },
  {
    title: "You are ready",
    text: "Have fun, and keep the plan flexible.",
  },
];
