/* Trade Empire, Desktop boot only (loaded by pc.html). The guided tutorial for the Desktop layout: the
   Classic walkthrough points at the colonies, market, research and ledger sections, which the Desktop
   layout moves into windows opened from the Menu, plus the ship panels and map in new places.
   index.html uses these steps when they exist (window.TRADE_EMPIRE_PC_TUTORIAL_STEPS) and its own
   otherwise. */
window.TRADE_EMPIRE_PC_TUTORIAL_STEPS = [
  {
    title: "Welcome to Trade Empire",
    text: "You're running a private interstellar trading corporation: four ships, five colonies, two need-cycles, and nobody but you (until automation) deciding who ships what to whom. This walkthrough covers the Desktop layout and the whole loop. Skip it any time, and reopen it later from the Menu.",
  },
  {
    selector: "#map-panel",
    title: "The trade network",
    text: "Colonies are nodes, routes are lines. Every colony ships to whichever other colony needs what it produces. Ships appear as moving dots along the lines while they travel: a circle for a ship you fly by hand, a diamond for an automated one. This map grows as you research new clusters.",
  },
  {
    selector: "#mobile-needs-strip",
    title: "Needs at a glance",
    text: "One chip per colony, naming the good it needs most and how well that need is being met. Check it before you pick a destination for a loaded ship. The full colony list, with development, investment and demands, is in the Menu under Colonies.",
  },
  {
    selector: "#pc-side",
    title: "Your fleet",
    text: "Each ship has its own panel in this column. Load cargo fills the hold with whatever the docked colony produces; then pick a destination with a Depart button. On arrival the cargo sells at the current market price and is delivered to the colony that needs it. Rename a ship if you like, and scroll for the rest of the fleet (ships 5 and 6 are bought).",
  },
  {
    selector: "#ship-1-automate-button",
    title: "Automating a ship",
    text: "Pay a one-time credit cost to automate a ship and it loads and departs on its own along a fixed route, no more clicking. Only a limited number of ships can be automated at once; research an Automation Expansion to raise the cap. The Automation chip at the top shows your slots.",
  },
  {
    selector: "#pc-readouts",
    title: "Profit, automation and research",
    text: "Total profit is the one wallet in this game: it pays for automation, ships and investments. Research points are a second currency that builds up on its own over time and is spent only on permanent, fleet-wide upgrades in the Research window. Selling a good over and over crashes its price, so spread your sales across goods (the Market window shows every price).",
  },
  {
    selector: "#fleet-priority-panel",
    title: "Fleet priority",
    text: "Only affects automated ships that are idle and empty. Switch this on and they abandon their fixed shuttle route to reposition toward whichever producer feeds the fleet's most under-served colony: real prioritisation across the whole automated fleet, not just per-route toggles.",
  },
  {
    selector: "#guild-panel",
    title: "The Trade Guild",
    text: "Now and then the guild offers a bulk contract: deliver a number of units of a good to a colony before a deadline for a bonus on top of the normal sale. Accept it here, or ignore it. Declining or missing one costs nothing.",
  },
  {
    selector: "#pc-menu-button",
    title: "Icons and the Menu",
    text: "The four icons are Achievements, the Summary, the Charter (permanent perks bought with charter points) and Settings. The Menu (or Escape, when nothing else is open) holds the rest: Colonies (development, investment, demands), the Market with stockpiles and trade posts, Research (including the clusters beyond home: Kepler, the Rift and the Umbral Deep), How to Play, About and story, What's New. Each opens as a window over the map, and Escape closes the top one. Reach the full-scale endgame and a Galaxy panel appears under your fleet, where you can renew the charter.",
  },
  {
    title: "You're ready to trade",
    text: "That's the full loop: load, depart, sell, keep colonies fed, research upgrades, automate what you can, and let Fleet Priority handle the rest once you've earned it. Good luck building your galaxy.",
  },
];

// The "?" shortcuts list (shared/keyboard-shortcuts.js) is its own overlay, not a shell window, so
// without this an Escape that closes it would also open the Menu. Flagging the event first (the
// shell checks this flag in its own capture listener) lets Escape just close the list.
document.addEventListener("keydown", (e) => {
  if (e.key !== "Escape") return;
  const help = document.getElementById("kb-shortcuts-panel");
  if (help && !help.hidden) e.__pcMenuOpened = true;
}, true);

/* shared/story-chapters.js adds its Story list after the page heading, which in this layout is the
   top bar. Once it exists, file it in the "About Trade Empire" window instead. */
(function () {
  function homeStory() {
    const story = document.getElementById("story-chapters");
    const about = document.getElementById("pc-about-panel");
    if (!story || !about) return false;
    if (story.parentNode !== about) about.appendChild(story);
    return true;
  }
  function start() {
    if (homeStory()) return;
    const observer = new MutationObserver(() => { if (homeStory()) observer.disconnect(); });
    observer.observe(document.documentElement, { childList: true, subtree: true });
    setTimeout(() => observer.disconnect(), 20000);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", () => setTimeout(start, 0));
  else setTimeout(start, 0);
})();

/* The Research window exists to list the nodes, so its (Classic: collapsed) node list starts open. */
(function () {
  function openNodes() {
    const nodes = document.querySelector(".research-nodes-toggle");
    if (nodes) nodes.open = true;
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", openNodes);
  else openNodes();
})();
