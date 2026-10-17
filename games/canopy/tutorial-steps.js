// Canopy's tutorial walkthrough steps (the Classic page; pc.js sets window.CANOPY_PC_TUTORIAL_STEPS, which boot.js
// prefers on the Desktop page). boot.js hands them to GameTutorial.init once the engine has loaded.
const CANOPY_TUTORIAL_STEPS = [
  {
    title: "Welcome to Canopy",
    text: "You're managing a forest region, plot by plot. Every plot is a choice: clear it now for quick income, or leave it standing and let its value compound. There's no fail state and no wrong answer — this quick walkthrough covers every system. Skip it any time, and reopen it later from the Tutorial button up top.",
  },
  {
    selector: "#plot-grid",
    title: "The Forest Grid",
    text: "36 plots, each tracked individually. Click a plot to select it — every plot starts Preserved, and what happens to it from here is entirely up to you.",
  },
  {
    selector: "#action-panel",
    title: "Clear or Replant",
    text: "With a plot selected, this panel shows its state and lets you act on it. Clear banks its current standing value as income right now, but permanently degrades that plot's future growth a little each time. Replant is only available on a Bare plot — it starts a slower recovery timer back toward full health.",
  },
  {
    selector: ".legend",
    title: "Reading Plot State",
    text: "Preserved and Recovered plots deepen in color as they mature — their value compounds the longer they're left alone, so an older plot earns faster than a new one. Bare plots are flat brown soil. Replanting plots gradually shift color as their recovery timer counts down. A long-undisturbed plot also quietly builds biodiversity — cross a threshold and a small wildlife icon appears on the tile.",
  },
  {
    selector: "#stats",
    title: "Income vs Standing Value",
    text: "Two numbers matter most: harvested income (banked from clearing) and standing forest value (what's still growing, uncleared). The message here compares them plainly — patience compounds, quick clearing doesn't, and you can watch the balance shift as you play.",
  },
  {
    selector: "#stakeholder-panel",
    title: "Stakeholder Requests",
    text: "Periodically the community asks you to clear your most established standing plot for a stated real need — housing, farming, or resources. Granting clears the plot and raises community relations by 10; declining keeps it standing but costs 5 relations. Neither choice is free, and neither is catastrophic. Every so often the community instead offers something positive for keeping a plot standing — accepting one of those raises relations and pays a small bonus, and there's no cost at all to declining.",
  },
  {
    selector: "#info-page-toggle-button",
    title: "The Real Story",
    text: "Open this any time to read how Canopy's clear-or-preserve tension maps onto real deforestation and carbon-sink science, with links to the sources behind it.",
  },
  {
    selector: "#session-summary-toggle-button",
    title: "Session Summary",
    text: "Open this any time for a recap: a trend chart of income vs. standing value, a comparison against what your forest would be worth if every plot had been left standing since the start, and a short shareable summary you can copy. You can also save the current stats as Run A or Run B to compare two different playstyles side by side — those two saved runs stick around even after a Reset Session.",
  },
  {
    selector: "#highland-lock-banner",
    title: "A Second Region",
    text: "Grow your main forest's standing value high enough and you'll unlock Highland Grove — a smaller second grove with the same clear/preserve/replant choices, its own income and standing value, on a fresh grid.",
  },
  {
    title: "You're ready",
    text: "That's the whole loop: select a plot, decide its fate, and watch how harvested income and standing forest value shift against each other over a session. Weigh community requests as they come. There's no way to lose — just different balances of quick income against a forest left to compound. You can also reset the session (or switch to a larger grid) any time from the toolbar. Good luck out there.",
  },
];
