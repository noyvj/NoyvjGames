// SOL's tutorial walkthrough steps (the Classic page; pc.js sets window.SOL_PC_TUTORIAL_STEPS, which boot.js
// prefers on the Desktop page). boot.js hands them to GameTutorial.init once the engine has loaded.
const SOL_TUTORIAL_STEPS = [
  {
    title: "Welcome to SOL",
    text: "You're starting a solar-system mining operation on Earth. This quick walkthrough covers the core loop and every system you'll unlock along the way — skip it any time, and reopen it later from the Tutorial button up top.",
  },
  {
    selector: "#click-button",
    title: "Mine Iron",
    text: "Click this to manually mine Iron. Manual clicking matters most early on — once automation kicks in here, it fades in relevance, but you'll click again on each new planet you reach.",
  },
  {
    selector: "#automation",
    title: "Auto-Miners",
    text: "Spend Iron to buy an Auto-Miner — it mines a steady amount per second on its own, no clicking required. This is how every resource loop scales past what manual clicking alone can do.",
  },
  {
    selector: "#ecology",
    title: "Ecological Health",
    text: "Extraction pollutes the planet over time. Below 10% health you lose 25% of your output; at 0% production stops entirely. Recyclers slow the decline — build one to keep this sustainable.",
  },
  {
    selector: "#terraform",
    title: "Terraforming",
    text: "This bar fills on its own from sustained economic and ecological balance — it isn't a separate resource you spend. Keep ecology healthy over time and this rises automatically.",
  },
  {
    selector: "#research",
    title: "Research",
    text: "Research is a tree: buy nodes with Iron, and most give a small bonus (more yield, cheaper miners, cheaper trade routes). Branches split and rejoin, and the last node of each level unlocks new destinations. Research isn't planet-by-planet: the Near Bodies level opens the Moon and Mars together.",
  },
  {
    selector: "#governor",
    title: "Governor — Priority & Budget",
    text: "Once you're managing multiple planets, you can't watch them all at once. The Governor keeps a planet running while you're away — Priority sets what it optimizes for, Budget sets how much of its resources it spends doing that.",
  },
  {
    selector: "#travel",
    title: "Travel",
    text: "Once you've funded enough research, travel buttons appear here for every newly-unlocked body. You don't need to fully develop your current planet first — just meet the research requirement.",
  },
  {
    title: "You're ready",
    text: "That's the whole loop: mine, automate, balance ecology, research, expand, and let the Governor mind what you leave behind. Reach 100% terraforming everywhere for the win state — the simulation keeps going afterward as a sandbox. Good luck out there.",
  },
];
