/* SOL, Desktop boot only (loaded by pc.html). Three jobs:
   1. The guided tutorial for the Desktop layout. The Classic walkthrough points at the Research and
      Governor sections, which the Desktop layout moves into windows opened from the Menu.
      index.html uses these steps when they exist (window.SOL_PC_TUTORIAL_STEPS) and its own otherwise.
   2. Each world's view keeps its hero (planet picture, resource name, count, mine button) together in one
      block so the layout can put it beside the world's panels. Nodes are moved, never copied, so ids and
      listeners survive.
   3. The resource chips under the top bar show only the worlds you have unlocked, and the shared "?"
      list closing with Escape does not also open the Menu. */
window.SOL_PC_TUTORIAL_STEPS = [
  {
    title: "Welcome to SOL",
    text: "You're starting a solar-system mining operation on Earth. This walkthrough covers the Desktop layout and every system you'll unlock along the way. Skip it any time, and reopen it later from the Menu.",
  },
  {
    selector: "#click-button",
    title: "Mine Iron",
    text: "Click this to mine Iron by hand (or hold it to repeat slowly). Manual clicking matters most early on; once automation kicks in it fades, but you'll click again on each new world you reach.",
  },
  {
    selector: "#pc-readouts",
    title: "Your resources",
    text: "One chip per world you have unlocked, each with its own resource: Iron, then Water Ice, Regolith, Sulfur, Platinum, Tholins, Helium-3 and Methane. They keep counting for every world, including the ones you are not standing on.",
  },
  {
    selector: "#automation",
    title: "Auto-Miners",
    text: "Spend Iron to buy an Auto-Miner. It mines a steady amount per second on its own, no clicking required. This is how every resource loop scales past what manual clicking alone can do.",
  },
  {
    selector: "#ecology",
    title: "Ecological Health",
    text: "Extraction pollutes the planet over time. Below 10% health you lose 25% of your output; at 0% production stops entirely. Recyclers slow the decline, so build one to keep this sustainable.",
  },
  {
    selector: "#terraform",
    title: "Terraforming",
    text: "This bar fills on its own from sustained economic and ecological balance. It isn't a resource you spend, so keep ecology healthy over time and it rises by itself. The colour of the planet shifts as it fills.",
  },
  {
    selector: "#travel",
    title: "Travel",
    text: "Once you've funded enough research, a travel button appears here for every newly unlocked world. You don't need to fully develop your current planet first. Each world has its own panels and its own resource; the Return button brings you home.",
  },
  {
    selector: "#pc-menu-button",
    title: "Research, Governor and the Menu",
    text: "The four icons are Overview (every world on one screen, with travel, Governor and Focus controls), Achievements, Stats and Share, and Settings. The Menu (or Escape, when nothing else is open) holds the rest. Open Research tree there to buy nodes with Iron: branches split and rejoin, and the last node of each level unlocks new destinations. Open Governor to set the priority and budget that keep a world running while you are elsewhere. Both work from any world. Each opens as a window over the game, and Escape closes the top one.",
  },
  {
    title: "You're ready",
    text: "That's the whole loop: mine, automate, balance ecology, research, expand, and let the Governor mind what you leave behind. Reach 100% terraforming everywhere for the win state; the simulation keeps going afterward as a sandbox. Good luck out there.",
  },
];

(function () {
  // 2. Hero blocks.
  const HERO = ".planet-visual, .resource-label, .prestige-bonus-tag, .resource-count, .click-button, #away-planet-name, #away-arrival-text";
  function groupHeroes() {
    document.querySelectorAll('#game > [id$="-view"]').forEach((view) => {
      if (view.querySelector(":scope > .pc-hero")) return;
      const parts = [...view.children].filter((node) => node.matches(HERO));
      if (!parts.length) return;
      const hero = document.createElement("div");
      hero.className = "pc-hero";
      view.insertBefore(hero, parts[0]);
      parts.forEach((node) => hero.appendChild(node));
    });
  }

  // 3a. Chips for worlds you have not unlocked yet stay out of the way. A world is unlocked once its
  // travel button is shown (Earth always is).
  const CHIP_TRAVEL = {
    "Water Ice": "travel-mars-button",
    "Regolith": "travel-moon-button",
    "Sulfur": "travel-venus-button",
    "Platinum": "travel-asteroid-belt-button",
    "Tholins": "travel-pluto-button",
    "Helium-3": "travel-jupiter-moons-button",
    "Methane": "travel-saturn-moons-button",
  };
  function syncChips() {
    document.querySelectorAll("#pc-readouts .pc-readout").forEach((chip) => {
      const label = chip.querySelector(".pc-readout-label");
      const button = label && document.getElementById(CHIP_TRAVEL[label.textContent]);
      if (button) chip.hidden = button.hidden;
    });
  }
  function watchChips() {
    const buttons = Object.values(CHIP_TRAVEL).map((id) => document.getElementById(id)).filter(Boolean);
    const observer = new MutationObserver(syncChips);
    buttons.forEach((b) => observer.observe(b, { attributes: true, attributeFilter: ["hidden"] }));
    syncChips();
  }

  // 3b. The "?" shortcuts list (shared/keyboard-shortcuts.js) is its own overlay, not a shell window, so
  // without this an Escape that closes it would also open the Menu.
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    const help = document.getElementById("kb-shortcuts-panel");
    if (help && !help.hidden) e.__pcMenuOpened = true;
  }, true);

  // 3c. game.py only redraws the research node buttons (and whether each one is affordable) when something
  // calls update_research_display(), which never happens as Iron accumulates, so a node can stay greyed out
  // after you can afford it (also true on the Classic page). In this layout the buttons of nodes that are
  // not locked follow the Iron count (the one on Earth's hero, which the game updates every tick). Only the
  // buttons' disabled flag changes, nothing is redrawn, and buying a node is still checked by the game itself.
  function keepResearchFresh() {
    const iron = document.getElementById("resource-count");
    const list = document.getElementById("research-node-list");
    if (!iron || !list) return;
    const sync = () => {
      const have = parseInt(iron.textContent, 10);
      if (Number.isNaN(have)) return;
      list.querySelectorAll(".research-node--available button").forEach((button) => {
        const cost = parseInt((button.textContent.match(/\((\d+) Iron\)/) || [])[1], 10);
        if (!Number.isNaN(cost)) button.disabled = have < cost;
      });
    };
    new MutationObserver(sync).observe(iron, { childList: true, characterData: true, subtree: true });
    new MutationObserver(sync).observe(list, { childList: true });
    sync();
  }

  document.addEventListener("DOMContentLoaded", () => {
    groupHeroes();
    const log = document.getElementById("captains-log");
    if (log) log.open = true; // its window is titled "Captain's log" already, so the list starts open
    setTimeout(keepResearchFresh, 0);
    // The chips are built by the shell's own DOMContentLoaded handler, which runs after this one.
    setTimeout(watchChips, 0);
  });
})();
