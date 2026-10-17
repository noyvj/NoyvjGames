// Aftermath's tutorial walkthrough steps (the Classic page; pc.js sets window.AFTERMATH_PC_TUTORIAL_STEPS, which boot.js
// prefers on the Desktop page). boot.js hands them to GameTutorial.init once the engine has loaded.
const AFTERMATH_TUTORIAL_STEPS = [
  {
    title: "Welcome to Aftermath",
    text: "This settlement faces a fixed sequence of extreme-weather and other resilience shocks every run. Between events you choose whether to spend resources on resilience (survive the next hit better) or growth (earn more to spend). Runs are short and repeat — a permanent skill tree carries lessons forward, so every run leaves the next one a little more capable, even a bad one.",
  },
  {
    selector: "#status",
    title: "Facing a Run",
    text: "Each run works through a fixed sequence of 7 events — floods, heatwaves, and storms, non-weather shocks like supply-chain disruption and infrastructure failure, and a social shock (civil unrest). The Heat season scenario, chosen before a run starts, adds a fourth kind of shock: a heat-health emergency, where the heat itself endangers people. Severity (mild/typical/severe, and now shown as an exact multiplier before you commit) isn't random: it's a fixed pattern tied to the run number, so replaying the same run always poses the same challenge. Your very first run is always typical difficulty.",
  },
  {
    selector: "#resilience-invest-button",
    title: "Invest in Resilience",
    text: "Spend resources to raise this run's resilience capacity. Each point adds a flat 5% mitigation, cutting the damage the next event deals — capped at 85% total, so some damage always gets through. This investment resets to zero at the start of every new run.",
  },
  {
    selector: "#growth-invest-button",
    title: "Invest in Growth",
    text: "Spend resources to raise this run's growth capacity instead. Each point adds a flat 8 resources of passive income every time you face an event — it does nothing to reduce damage, so it's a bet that the extra income outweighs skipping a point of mitigation.",
  },
  {
    selector: "#mitigation-bar",
    title: "Mitigation",
    text: "This meter shows the share of event damage you're currently avoiding, built from your Resilience investment (plus a flat +10% once you unlock Early Warning Systems in the skill tree). It's capped at 85% — no matter how invested you are, an event can always do at least some damage.",
  },
  {
    selector: "#resolve-event-button",
    title: "Face Next Event",
    text: "Resolves the next scheduled event: growth income is added first, then the event's damage — reduced by your current mitigation — is subtracted from your resources. There's no way to skip or delay an event once you've committed to a run.",
  },
  {
    selector: "#skill-tree",
    title: "Resilience Knowledge & Skill Tree",
    text: "Knowledge points are earned at the end of every run (your leftover resources divided by 20, rounded — but never zero, even after a terrible run). Spend them here on permanent skills that pre-equip every future run with a head start. Unlike Resilience/Growth investment, these carry forward forever.",
  },
  {
    selector: "#progress-comparison-display",
    title: "How Far You've Come",
    text: "Once you've completed at least two runs, this line compares your very first run's score to your most recent — same fixed event sequence, so a higher score really does mean you handled it better. This settlement also remembers, in its own words up top, which kinds of events it has weathered before.",
  },
  {
    selector: "#new-run-button",
    title: "Starting a New Run",
    text: "Once all 7 scheduled events are resolved, this button appears. Starting a new run resets your resources, resilience, and growth back to a fresh baseline — but reads your current skill tree, so any skills you've unlocked since the last run apply automatically from the very first event.",
  },
  {
    title: "You're ready",
    text: "That's the loop: allocate resources between resilience and growth, face each scheduled event, and let a permanent skill tree carry what you learn into the next run. No single run has to go perfectly — resilience is cumulative, and nothing is ever wasted. Good luck out there.",
  },
];
