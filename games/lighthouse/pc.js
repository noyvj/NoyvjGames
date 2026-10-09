/* Lighthouse, Desktop boot only (loaded by pc.html). The guided tutorial for the Desktop layout: the Classic walkthrough
   points at the toolbar and panels the Desktop layout moves into icons, the Menu and windows. index.html uses these steps
   when they exist (window.LIGHTHOUSE_PC_TUTORIAL_STEPS) and its own otherwise. */
window.LIGHTHOUSE_PC_TUTORIAL_STEPS = [
  {
    title: "The keeper's life",
    text: "You keep one light on one rock. Each evening you plan the night, the night plays out, and each morning you read how the ships fared. Nothing you do can end the game, and everything can be paused. This walkthrough covers the Desktop layout. Skip it any time, and reopen it later from the Menu (or press Escape).",
  },
  {
    selector: "#pc-readouts",
    title: "The station at a glance",
    text: "Night, the clock, oil, your energy, the harbour's opinion of you (The Light) and salvage, which buys upgrades. They update live.",
  },
  {
    selector: "#goals-panel",
    title: "Three goals, no order",
    text: "Three goals are always on show: the next title the harbour could give you, the upgrade nearest your salvage, and something to try. Do them in any order; each is replaced when it is done.",
  },
  {
    selector: "#scene-panel",
    title: "The rock",
    text: "The beam sweeps the sea and ships pass by. A ship lit by your beam gets a ring and a mark. Fog, haze, squalls and storms shorten how far the beam reaches. The keeper's log sits just below.",
  },
  {
    selector: "#barometer-card",
    title: "The barometer",
    text: "Tonight's weather as a band of two steps. It is right about nine nights in ten, so it is a hint, not a promise.",
  },
  {
    selector: "#board-card",
    title: "The harbour board",
    text: "The ships expected tonight, roughly when, and how far the beam must reach for each to find you.",
  },
  {
    selector: "#plan-blocks",
    title: "The lamp plan",
    text: "Choose a lamp level for dusk, deep night and dawn. Brighter reaches further and burns more oil; the estimate under it says whether the oil will last.",
  },
  {
    selector: "#light-lamp-button",
    title: "Light the lamp",
    text: "When you are ready. In the night, Space pauses, [ and ] change speed, keys 1 to 4 change the lamp for the rest of this part of the night, W winds the clockwork and T sees to trouble.",
  },
  {
    selector: "#station-panel",
    title: "The station",
    text: "Storms wear the tower, the lantern glass, the rail, the dock and the cistern. In the day you mend them with supplies from the supply boat, whose twelve crates you order yourself.",
  },
  {
    selector: "#pc-menu-button",
    title: "Icons and the Menu",
    text: "The icons open the Letters, your Achievements and Settings. The Menu, or Escape when nothing else is open, holds the rest: this tutorial, the Eerie details switch (the odd things that happen in the night; off keeps the letters and kind moments), About the Light with its named sources, and What's New. Each opens as a window, and Escape closes the top one.",
  },
  {
    title: "You are ready",
    text: "Set the lamp, light it, and keep the sea company. Take your time.",
  },
];
