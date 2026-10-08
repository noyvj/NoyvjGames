/* Pocket Bazaar, Desktop boot only (loaded by pc.html). The guided tutorial for the Desktop layout: the Classic
   walkthrough names the toolbar buttons, which the Desktop layout turns into icons, the Menu and windows, and the
   crates and tools sit in a side column. index.html uses these steps when they exist
   (window.POCKET_BAZAAR_PC_TUTORIAL_STEPS) and its own otherwise. */
window.POCKET_BAZAAR_PC_TUTORIAL_STEPS = [
  {
    title: "Welcome to the stall",
    text: "Customers ask for goods; you make them by merging and hand them over. Nothing here runs on a clock: customers wait in beats, which are your own actions, so you can stop and think as long as you like. This walkthrough covers the Desktop layout. Skip it any time, and reopen it from the Menu.",
  },
  {
    selector: "#stats",
    title: "Your numbers",
    text: "Coins, the day, how many customers you have served, and your combo. Every action you take moves one of these, or the tally in the side column.",
  },
  {
    selector: "#queue",
    title: "The customers",
    text: "Up to three customers stand at the stall with their orders and a patience bar counted in beats. Pick up a good, then click a customer who wants it (they get a dashed outline), or drag the good onto them.",
  },
  {
    selector: "#board",
    title: "The counter",
    text: "Click a good to pick it up and click an identical one (marked with a +) to merge them into the next tier. Three together jump two tiers, and a merge that lines up with a neighbour keeps going as a chain. Drag works too.",
  },
  {
    selector: "#pc-side",
    title: "Crates, Sell and Broom",
    text: "Crates are free and never run out. Sell turns any good into coins and Broom sweeps it away, so the counter can never jam. Only crates, merges, sweeps and hand-overs are beats; moving and selling are free.",
  },
  {
    selector: "#start-day-button",
    title: "Open the stall",
    text: "Each market day has a festival that changes one rule, and it says plainly whether it makes the day easier or harder. Between days you can spend coins on permanent upgrades and decorations.",
  },
  {
    selector: "#pc-menu-button",
    title: "Icons and the Menu",
    text: "The icons open Achievements, the Regulars and Settings. The Menu, or Escape when nothing else is open, holds the rest: this tutorial, About Pocket Bazaar with the pledge, and What's New. Each opens as a window over the game, and Escape closes the top one.",
  },
  {
    title: "You are ready",
    text: "Take your time. Your stall is saved after every action, and nothing is lost by leaving.",
  },
];
