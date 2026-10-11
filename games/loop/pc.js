// Loop, Desktop boot only (loaded by pc.html). The guided tutorial for the Desktop layout: the Classic
// walkthrough points at sections the Desktop layout rearranges (the numbers become chips, the trade
// buttons move into the decisions column, long text moves into windows). index.html uses these steps
// when they exist (window.LOOP_PC_TUTORIAL_STEPS) and its own otherwise.
window.LOOP_PC_TUTORIAL_STEPS = [
  {
    title: "Welcome to Loop",
    text: "You're running a small manufacturing chain that, by default, is a straight line: extract raw material, manufacture goods, use them, then throw them away. Your job is to redesign it into something closer to a closed loop. This walkthrough covers the Desktop layout. Skip it any time, and reopen it later from the Menu (or press Escape).",
  },
  {
    selector: "#pc-readouts",
    title: "Your numbers",
    text: "The chips along the top are the cycle, your funds, environmental damage (and what it does to the cost of new extraction), how circular this cycle is, your lifetime circular share and your score. Funds pay for every investment. Damage never resets, so the more you extract over the whole game, the more each future unit costs, up to 2.5x.",
  },
  {
    selector: "#chain-flow-section",
    title: "The Chain",
    text: "This is your supply chain: Extract, Manufacture, Use, Discard. Right now it's a straight line, so 100% of every cycle's production needs freshly extracted raw material. As you invest in circularity, a share of production starts looping back into Manufacture instead; watch this message and the flow arrows change. Below it, one phone is followed through the same chain in plain language.",
  },
  {
    selector: "#status",
    title: "Damage and Loop closure",
    text: "The two meters are the heart of the game. Environmental damage rises with every unit of new extraction and never falls. Loop closure shows your circular share this cycle and your lifetime average, including any earlier straight-line cycles. Under them is your score (funds plus a bonus for lifetime circular share) and, in the fold-out, your streak, trend and comparisons with real-world benchmarks.",
  },
  {
    selector: "#pc-side",
    title: "Your decisions",
    text: "The right-hand column holds everything you decide each cycle and scrolls on its own, with Advance Cycle pinned at the top. At the very start you also pick what the chain produces and, if you like, an optional challenge mode; those choices lock after the first cycle.",
  },
  {
    selector: "#repair-invest-button",
    title: "Circularity Investments",
    text: "Repair Networks, Reuse Systems and Recycling Loops each permanently supply a fixed number of units toward next cycle's production target, sourced from repaired, reused or recycled material instead of new extraction. Recycling supplies the most per unit, Repair the least. Focus and Redesign sharpen a measure, the Culture campaign trims how much material you need, and the Material passport follows one unit's journey. Buy enough combined supply to push new extraction to zero and you've closed the loop. Streak insurance protects a run of perfect cycles once per chain, and the Career panel below keeps your name plates and records. Space advances the cycle, 1 2 3 buy the three measures and T buys a Trade Link.",
  },
  {
    selector: "#trade-network",
    title: "Trade network and supply map",
    text: "The Trade Link, Regional Partner and Overseas Consortium buttons sit in the decisions column under your investments. Each imports reuse capacity from a neighbouring system that counts toward your loop, and any supply beyond what this cycle needs is sold outward for revenue. This panel shows it all as a route and a supply map; the visual views draw the same numbers as an interactive diagram.",
  },
  {
    selector: "#advance-cycle-button",
    title: "Advance Cycle",
    text: "This locks in your investment mix: it extracts whatever raw material your circularity and trade supply didn't cover, charges you for it at the current damage-adjusted cost, sells your production and any exported surplus, then moves you to the next cycle.",
  },
  {
    selector: "#pc-menu-button",
    title: "Icons and the Menu",
    text: "The three icons are Achievements, How to Play and Settings. The Menu (or Escape, when nothing else is open) holds the rest: the tutorial, the real story, What's New, relabelling your goods, About Loop, feedback, fullscreen and the Classic layout. Everything opens as a window over the game, and Escape closes the top one.",
  },
  {
    title: "Redesign the Machine",
    text: "There's no fail-state here: the score rewards funds plus a direct bonus for your lifetime circular share, so closing the loop is worth pursuing for its own sake. Keep investing in circularity until new extraction hits zero, and watch the trend line confirm you're closing the loop over time. Good luck redesigning the chain.",
  },
];

// The Supply map fold-out holds the text map and the visual-view toggle that make up the trade panel's
// lower half; on a wide window there is room, so it starts open.
document.addEventListener("DOMContentLoaded", () => {
  // Only a default: a fold-out the player has opened or shut before keeps their choice (settings.js).
  const remembered = (id) => {
    try { return window.localStorage.getItem("loop-panel-open:" + id) !== null; } catch (e) { return false; }
  };
  const map = document.getElementById("network-map-panel");
  if (map && !remembered("network-map-panel")) map.open = true;
  const relabel = document.getElementById("relabel-goods-panel");
  if (relabel && !remembered("relabel-goods-panel")) relabel.open = true; // its own window here, so no need to unfold it first
});
