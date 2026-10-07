/* Tide, Desktop boot only (loaded by pc.html). The guided tutorial for the Desktop layout: the
   Classic walkthrough points at the acidity and fish-yield meters, the sea-level section and the
   then-vs-now comparison, which the Desktop layout moves into chips and windows. index.html uses
   these steps when they exist (window.TIDE_PC_TUTORIAL_STEPS) and its own otherwise. */
window.TIDE_PC_TUTORIAL_STEPS = [
  {
    title: "Welcome to Tide",
    text: "You're running a coastal settlement, balancing fishing and industry income against ocean health and a slowly rising sea. This walkthrough covers the Desktop layout. Skip it any time, and reopen it later from the Menu (or press Escape).",
  },
  {
    selector: "#pc-stagebar",
    title: "Pick your sea-level scenario first",
    text: "This chooses how fast the sea rises: Conservative, Moderate or Severe. It locks the moment you play your first season, so decide now. If you ever need to find it again, it is the control above the coastline.",
  },
  {
    selector: "#pc-side",
    title: "Invest each season",
    text: "Spend funds on Output (fishing or industry income), Acidity Reduction (cleanup spending) and Adaptation (seawalls and other flood defences). Each investment is permanent capacity that keeps working every season. The Output mix dropdown trades acidity against exposure to the fish-stock crash. The investments and Advance Season stay in view while the programmes below them scroll.",
  },
  {
    selector: "#pc-readouts",
    title: "Your numbers",
    text: "The chips along the top are the season, your funds, ocean acidity, fishing yield, sea level and the cumulative damage so far. The core lesson is the delay: fishing yield reflects acidity from three seasons ago, not today's, so damage from a choice you make now lands a few turns later and does not recover the moment you fix the cause. Open the Menu for the full status with the acidity and fish-yield meters and the graphs of that lag.",
  },
  {
    selector: "#pc-stage",
    title: "The coastline",
    text: "This tile grid is a direct read of your sea level: rows flip from land to flooded as the water crosses each row's threshold, rising from the bottom. Unlocked adaptation tiers add a visible seawall line along the shore. Hover a tile to see when it floods. The ticker underneath narrates delayed effects as they land, and an early warning appears above the coast when a fish-stock crash is already locked in.",
  },
  {
    selector: "#advance-season-button",
    title: "Advance Season",
    text: "This is the turn button. It applies your investments and ticks acidity, fish yield, sea level and damage forward one season. Sea level climbs every season no matter what you do; adaptation only reduces how much economic damage it causes.",
  },
  {
    selector: "#pc-menu-button",
    title: "Icons and the Menu",
    text: "The three icons are Achievements, the Session Summary and Settings. The Menu (or Escape, when nothing else is open) holds everything else: Status, graphs and history with the meters, Sea level, damage and adaptation tiers, Coastline then versus now, the sister settlement and harder lag options, the tutorial, How to Play, the real-world story, What's New and feedback. Each opens as a window over the game, and Escape closes the top one.",
  },
  {
    title: "You're ready",
    text: "That's the loop: invest, watch acidity build quietly, brace for the fish-stock lag to land, and keep adapting to blunt the sea's advance. There's no way to stop the water, only to weather it better than doing nothing. Good luck out there.",
  },
];

// The "?" shortcuts list (shared/keyboard-shortcuts.js) is its own overlay, not a shell window, so
// without this an Escape that closes it would also open the Menu. Flagging the event first (the
// shell checks this flag in its own capture listener) lets Escape just close the list.
document.addEventListener("keydown", (e) => {
  if (e.key !== "Escape") return;
  const help = document.getElementById("kb-shortcuts-panel");
  if (help && !help.hidden) e.__pcMenuOpened = true;
  // Escape on a graph that is showing its crosshair just clears the crosshair.
  const graph = e.target && e.target.closest ? e.target.closest("svg[data-crosshair]") : null;
  if (graph && graph.__crosshairIndex != null) e.__pcMenuOpened = true;
}, true);
