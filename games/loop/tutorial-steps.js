// Loop's tutorial walkthrough steps (the Classic page; pc.js replaces them with window.LOOP_PC_TUTORIAL_STEPS on the
// Desktop page). boot.js hands them to GameTutorial.init once the engine has loaded.
const LOOP_TUTORIAL_STEPS = [
  {
    title: "Welcome to Loop",
    text: "You're running a small manufacturing chain that, by default, is a straight line: extract raw material, manufacture goods, use them, then throw them away. Your job is to redesign it into something closer to a closed loop. This walkthrough covers every real system in the game — skip it any time, and reopen it later from the Tutorial button up top.",
  },
  {
    selector: "#chain-flow-section",
    title: "The Chain",
    text: "This is your supply chain: Extract → Manufacture → Use → Discard. Right now it's a straight line, so 100% of every cycle's production needs freshly extracted raw material. As you invest in circularity below, a share of production starts looping back into Manufacture instead — watch this message and the flow arrows update to reflect it.",
  },
  {
    selector: "#vignette",
    title: "Follow One Item",
    text: "This tracks one representative product — a phone — through the exact same chain, in plain language. It's driven by the same circular share the chain view above shows, just made concrete: is this phone thrown away for good, or does part of it eventually come back?",
  },
  {
    selector: "#status",
    title: "Your Dashboard",
    text: "Funds pay for every investment below. New extraction costs money and, over the game's lifetime, builds up Environmental damage — the more cumulative extraction you've done, the more expensive every future unit of new extraction gets (up to 2.5x). Loop closure tracks two numbers: your circular share this cycle right now, and your lifetime average across every cycle you've run, including any earlier straight-line ones.",
  },
  {
    selector: "#circularity",
    title: "Circularity Investments",
    text: "Repair Networks, Reuse Systems, and Recycling Loops each permanently supply a fixed number of units toward next cycle's production target — sourced from repaired/reused/recycled material instead of new extraction. Recycling Loops supply the most per unit invested; Repair Networks the least. Buy enough combined supply to push new extraction to zero and you've closed the loop.",
  },
  {
    selector: "#trade-network",
    title: "Trade Network",
    text: "The Trade Link works two ways: investing in it imports reuse capacity from a neighboring system, counting toward your loop closure just like your own investments. Separately, whenever your own circularity investments produce more supply than the current cycle needs, that surplus is automatically sold outward for extra revenue instead of going to waste.",
  },
  {
    selector: "#advance-cycle-button",
    title: "Advance Cycle",
    text: "This locks in your current investment mix for the cycle: it extracts whatever raw material your circularity + trade supply didn't cover, charges you for it at the current damage-adjusted cost, sells your production and any exported surplus, then moves you to the next cycle. Your funds, damage, and loop-closure numbers all update the moment you click it.",
  },
  {
    title: "Redesign the Machine",
    text: "There's no fail-state here — score rewards funds plus a direct bonus for your lifetime circular share, so closing the loop is worth pursuing for its own sake, not just to dodge rising extraction costs. Keep investing in circularity until new extraction hits zero, and watch the trend line confirm you're closing the loop over time. Good luck redesigning the chain.",
  },
];
