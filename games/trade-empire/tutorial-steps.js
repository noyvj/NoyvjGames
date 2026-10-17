// Trade Empire's tutorial walkthrough steps (the Classic page; pc.js sets window.TRADE_EMPIRE_PC_TUTORIAL_STEPS, which boot.js
// prefers on the Desktop page). boot.js hands them to GameTutorial.init once the engine has loaded.
const TRADE_EMPIRE_TUTORIAL_STEPS = [
  {
    title: "Welcome to Trade Empire",
    text: "You're running a private interstellar trading corporation: four ships, five colonies, two need-cycles, and nobody but you — until automation — deciding who ships what to whom. This walkthrough covers every system in the game. Skip it any time, and reopen it later from the Tutorial button up top.",
  },
  {
    selector: "#map-panel",
    title: "The trade network",
    text: "Colonies are nodes, routes are lines — this map shows who's connected to whom. Every colony ships to whichever other colony needs what it produces. Automated ships render as moving dots along these lines once they're underway.",
  },
  {
    selector: "#ship-1-panel",
    title: "Load cargo & depart",
    text: "Each ship can load whatever its docked colony currently produces, up to its cargo capacity, then depart for another colony. On arrival, its cargo auto-sells at the current market price and delivers to whichever colony needs that good, raising that colony's need satisfaction. All four ships work independently.",
  },
  {
    selector: "#market-panel",
    title: "Market prices",
    text: "Selling a good repeatedly crashes its price — every unit sold nudges it down, and it only recovers gradually if you leave it alone. A price that drops below 70% of baseline shows as crashed, in red. Spreading sales across goods keeps prices higher than dumping everything through one route.",
  },
  {
    selector: "#colonies-panel",
    title: "Colony needs & development",
    text: "A colony's output scales from 0.5x up to 1.5x with how well its need is being met — an under-supplied colony produces less to trade, and need satisfaction decays over time if you stop delivering. Keep a colony fed for long enough and it develops to Level 2, gaining a second need that reaches into the other supply cycle.",
  },
  {
    selector: "#research-panel",
    title: "Research",
    text: "Research points build up passively over time, completely separate from trading profit — a second currency spent only on permanent, fleet-wide upgrades: more automation slots, faster ships, bigger cargo holds, and eventually access to a whole new cluster of colonies.",
  },
  {
    selector: ".automate-button",
    title: "Automating a ship",
    text: "Pay a one-time credit cost to automate a ship and it starts loading and departing on its own along a fixed route — no more clicking required. Only a limited number of ships can be automated at once; research an Automation Expansion to raise the cap.",
  },
  {
    selector: "#ledger",
    title: "Profit & automation slots",
    text: "Total profit is the one wallet in this game — it pays for automation and gets spent nowhere else. This ledger also tracks how many of your automation slots are currently in use, and logs your most recent sale.",
  },
  {
    selector: "#fleet-priority-panel",
    title: "Fleet priority",
    text: "Only affects automated ships that are idle and empty. Switch this on and they'll abandon their fixed shuttle route to reposition toward whichever producer feeds the fleet's most under-served colony — real prioritization across your whole automated fleet, not just per-route toggles.",
  },
  {
    selector: "#expansion-colonies-panel",
    title: "The Kepler Cluster",
    text: "Unlock the Galaxy Expansion research node and a second, self-contained three-colony need-triangle opens up — three brand-new goods, reachable by any ship. A developed Kepler colony's second need reaches back into the home system, linking the two clusters together. Deeper research keeps going: Outer Reaches opens the Rift Colonies, and Deep Survey then Umbral Reach (the costliest node in the tree) opens a fourth cluster, the Umbral Deep.",
  },
  {
    selector: "#endgame-panel",
    title: "Reaching full scale",
    text: "Max out your automation slots, switch Fleet Priority on, and unlock Galaxy Expansion, and you'll reach the endgame state: a background galaxy of worlds that grows on its own and trickles in extra passive revenue. The economy keeps running afterward — there's no hard stop. When you're ready you can renew the charter: it resets the world for charter points that buy permanent perks, and opens the optional harder charter.",
  },
  {
    title: "You're ready to trade",
    text: "That's the full loop: load, depart, sell, keep colonies fed, research upgrades, automate what you can, and let Fleet Priority handle the rest once you've earned it. Good luck building your galaxy.",
  },
];
