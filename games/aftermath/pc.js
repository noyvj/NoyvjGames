/* Aftermath, Desktop boot only (loaded by pc.html). The guided tutorial for the Desktop layout: the
   Classic walkthrough points at the single "status" card's resource lines and the skill tree in the
   one-column page, while the Desktop layout shows the numbers as chips and the decisions in a right
   column. index.html uses these steps when they exist (window.AFTERMATH_PC_TUTORIAL_STEPS) and its
   own otherwise. */
window.AFTERMATH_PC_TUTORIAL_STEPS = [
  {
    title: "Welcome to Aftermath",
    text: "This settlement faces a fixed sequence of extreme-weather and other resilience shocks every run. Between events you choose whether to spend resources on resilience (survive the next hit better) or growth (earn more to spend). Runs are short and repeat. A permanent skill tree carries lessons forward, so every run leaves the next one a little more capable, even a bad one. This walkthrough covers the Desktop layout. Skip it any time, and reopen it later from the Menu.",
  },
  {
    selector: "#pc-readouts",
    title: "Your Numbers",
    text: "The chips across the top are the event you are on (of 7), your Resources, your Resilience and Growth capacity this run, and the Resilience knowledge you have banked for the skill tree. Resources are what every decision spends and every event damages.",
  },
  {
    selector: "#status",
    title: "Facing a Run",
    text: "The settlement card shows the next scheduled event, its expected damage and the last event's result. Each run works through a fixed sequence of 7 events: floods, heatwaves and storms, non-weather shocks like supply-chain disruption and infrastructure failure, and a social shock (civil unrest). Severity is not random: it is a fixed pattern tied to the run number, so replaying the same run always poses the same challenge, and it is shown as an exact multiplier before you commit. Your very first run is always typical difficulty.",
  },
  {
    selector: "#resilience-invest-button",
    title: "Invest in Resilience",
    text: "Spend resources to raise this run's resilience capacity. Each point adds a flat 5% mitigation, cutting the damage the next event deals, capped at 85% so some damage always gets through. This investment resets to zero at the start of every new run. These controls stay pinned at the top of the right-hand column while the skill tree scrolls beneath them.",
  },
  {
    selector: "#growth-invest-button",
    title: "Invest in Growth",
    text: "Spend resources to raise this run's growth capacity instead. Each point adds a flat 8 resources of passive income every time you face an event. It does nothing to reduce damage, so it is a bet that the extra income outweighs skipping a point of mitigation.",
  },
  {
    selector: "#mitigation-bar",
    title: "Mitigation",
    text: "This meter shows the share of event damage you are currently avoiding, built from your Resilience investment (plus a flat +10% once you unlock Early Warning Systems in the skill tree). It is capped at 85%: no matter how invested you are, an event can always do at least some damage.",
  },
  {
    selector: "#resolve-event-button",
    title: "Face Next Event",
    text: "Resolves the next scheduled event: growth income is added first, then the event's damage, reduced by your current mitigation, is subtracted from your resources. There is no way to skip or delay an event once you have committed to a run.",
  },
  {
    selector: "#knowledge-points-display",
    title: "Resilience Knowledge and the Skill Tree",
    text: "Knowledge points are earned at the end of every run (your leftover resources divided by 20, rounded, but never zero, even after a terrible run). Spend them here on permanent skills that pre-equip every future run with a head start. Unlike Resilience and Growth investment, these carry forward forever.",
  },
  {
    selector: "#progress-comparison-display",
    title: "How Far You've Come",
    text: "Once you have completed at least two runs, this line compares your very first run's score to your most recent. It is the same fixed event sequence, so a higher score really does mean you handled it better. Under the card, the settlement also remembers in its own words which kinds of events it has weathered before.",
  },
  {
    selector: "#new-run-button",
    title: "Starting a New Run",
    text: "Once all 7 scheduled events are resolved, this button appears (the Scenario picker and the Extended Run option sit just under it). Starting a new run resets your resources, resilience and growth back to a fresh baseline, but reads your current skill tree, so any skills you have unlocked since the last run apply automatically from the very first event.",
  },
  {
    selector: "#pc-menu-button",
    title: "Icons and the Menu",
    text: "The three icons are Achievements, Past Runs and Settings. The Menu (or Escape, when nothing else is open) holds the rest: the tutorial, How to Play, the real-world story, What's New, the community resilience index and leaderboard, backing up your progress, feedback, fullscreen and the Classic layout. Everything opens as a window over the game, and Escape closes the top one.",
  },
  {
    title: "You're Ready",
    text: "That's the loop: allocate resources between resilience and growth, face each scheduled event, and let a permanent skill tree carry what you learn into the next run. No single run has to go perfectly. Resilience is cumulative, and nothing is ever wasted. Good luck out there.",
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
