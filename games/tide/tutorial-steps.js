// Tide's tutorial walkthrough steps (the Classic page; pc.js sets window.TIDE_PC_TUTORIAL_STEPS, which boot.js
// prefers on the Desktop page). boot.js hands them to GameTutorial.init once the engine has loaded.
const TIDE_TUTORIAL_STEPS = [
  {
    title: "Welcome to Tide",
    text: "You're running a coastal settlement, balancing fishing/industry income against ocean health and a slowly rising sea. This walkthrough covers every system — skip it any time, and reopen it later from the Tutorial button up top.",
  },
  {
    selector: "#investments",
    title: "Invest Each Season",
    text: "Spend funds on three categories: Output (fishing/industry income), Acidity Reduction (cleanup spending), and Adaptation (seawalls and other flood infrastructure). Each investment is permanent capacity — it keeps working every season from then on.",
  },
  {
    selector: "#acidity-bar",
    title: "Ocean Acidity",
    text: "Acidity rises with your Output capacity and falls (more slowly) with Acidity Reduction spending. It never goes negative, and there's no bulk cleanup credit — you're always managing a live balance, not fixing things after the fact.",
  },
  {
    selector: "#fish-yield-bar",
    title: "The Delayed Fish-Stock Crash",
    text: "This is the core lesson: fishing yield doesn't respond to today's acidity — it reflects acidity from 3 seasons ago. Damage from a choice you make now won't show up for a few turns, and it won't recover the instant you fix the cause either. Watch the log above the meters for narration as it lands.",
  },
  {
    selector: "#sea-level-section",
    title: "Sea Level Keeps Rising",
    text: "Sea level climbs every season no matter what you do — nothing in this game stops or slows the rise itself. What Adaptation spending changes is how much economic damage that rise causes, not the rise itself.",
  },
  {
    selector: "#adaptation-tier-display",
    title: "Adaptation Tiers",
    text: "Adaptation investment is cumulative and never decays. Crossing fixed thresholds (3, 6, then 10 total units invested) unlocks a stronger tier — Sandbag Berms, then Seawalls, then Reinforced Seawalls — each dampening a larger share of sea-level damage.",
  },
  {
    selector: "#coastline-grid",
    title: "The Coastline",
    text: "This tile grid is a direct read of your sea level — rows flip from land to flooded as the water crosses each row's threshold, rising from the bottom up. Unlocked adaptation tiers also add a visible seawall line along the shore.",
  },
  {
    selector: "#coastline-comparison",
    title: "Then vs. Now",
    text: "This side-by-side compares your starting coastline to right now. Investing in adaptation early won't stop the sea, but it visibly flattens how much coastline and cumulative damage you take over time — proof that acting early matters even before it pays off.",
  },
  {
    selector: "#advance-season-button",
    title: "Advance Season",
    text: "This is the turn button — it applies your current investments, ticks acidity, fish yield, sea level, and damage forward by one season, and updates every meter and the delayed-effect log at once.",
  },
  {
    title: "You're ready",
    text: "That's the whole loop: invest, watch acidity build quietly, brace for the fish-stock lag to land, and keep adapting to blunt the sea's advance. There's no way to stop the water — only to weather it better than doing nothing. Good luck out there.",
  },
];
