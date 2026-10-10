/* Evidence Hunt, Desktop boot only (loaded by pc.html). The guided tutorial for the Desktop layout: the Classic walkthrough names
   toolbar buttons, which the Desktop layout turns into icons, the Menu and windows, and the notebook and sheet sit in a side column.
   index.html uses these steps when they exist (window.EVIDENCE_HUNT_PC_TUTORIAL_STEPS) and its own otherwise. */
window.EVIDENCE_HUNT_PC_TUTORIAL_STEPS = [
  {
    title: "Welcome to the notebook",
    text: "You are the quiet investigator a client calls when a house feels wrong. Each case is a house drawn as a floor plan, and you work out which kind of spirit is in it. Nothing is timed, nobody is harmed, and a wrong name only costs a point. The spirits and rules are invented. This walkthrough covers the Desktop layout. Skip it any time, and reopen it from the Menu.",
  },
  {
    selector: "#house-plan",
    title: "The house",
    text: "Click a room to walk in. Walking is free. The moment you step in, the room tells you whether it is restless (a spirit is there) or still. Walk every room first.",
  },
  {
    selector: "#gear-row",
    title: "Your bag",
    text: "Pack a few pieces of equipment before your first reading. The bag holds only a few, so pick the ones that tell the suspects apart. After your first reading the bag is locked, and a different bag is a second trip that costs 1.",
  },
  {
    selector: "#pc-side",
    title: "The notebook and the book of visitors",
    text: "The side column holds the notebook (every reading, room by room) and the client's book of visitors: the kinds that might be in this house, with their evidence and habits. Kinds your notebook rules out are struck through.",
  },
  {
    selector: "#accuse-box",
    title: "Name the spirit",
    text: "When only one kind fits, pick it and name it. A wrong name costs 1 and nothing else: your notebook stays and you can try again. The case ends with a quiet note about who the spirit was.",
  },
  {
    selector: "#restore-button",
    title: "Restore",
    text: "You can restore a case to its start at any time, for free, and try a different plan. Your seals are kept.",
  },
  {
    selector: "#goals",
    title: "Your goals",
    text: "Three goals stay in view, in any order. Every room, reading and name counts toward something on the screen.",
  },
  {
    selector: "#pc-menu-button",
    title: "Icons and the Menu",
    text: "The icons open the Cases, the field guide, the Achievements, the Practice houses and Settings. The Menu, or Escape when nothing else is open, holds the rest: this tutorial, About and What's New. Each opens as a window over the game, and Escape closes the top one.",
  },
  {
    title: "You are ready",
    text: "Take your time. Your seals and guide pages are saved as you go.",
  },
];
