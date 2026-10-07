/* Canopy, Desktop boot only (loaded by pc.html). The guided tutorial for the Desktop layout: the
   Classic walkthrough points at the stats, legend, session summary and region banners, which the
   Desktop layout moves into chips, windows and the Menu. index.html uses these steps when they
   exist (window.CANOPY_PC_TUTORIAL_STEPS) and its own otherwise. */
window.CANOPY_PC_TUTORIAL_STEPS = [
  {
    title: "Welcome to Canopy",
    text: "You're managing a forest region, plot by plot. Every plot is a choice: clear it now for quick income, or leave it standing and let its value compound. There's no fail state and no wrong answer. This walkthrough covers the Desktop layout; skip it any time and reopen it later from the Menu.",
  },
  {
    selector: "#plot-grid",
    title: "The Forest Grid",
    text: "Each plot is tracked individually. Click a plot to select it, or move between plots with the arrow keys. Every plot starts Preserved, and what happens to it from here is up to you.",
  },
  {
    selector: "#action-panel",
    title: "Clear or Replant",
    text: "With a plot selected, this panel shows its state and lets you act on it. Clear banks its current standing value as income right now, but permanently degrades that plot's future growth a little each time. Replant is only available on a Bare plot and starts a slower recovery. Tend gives one plot a short growth boost (hotkey T), and Adopt marks a plot as a long-term project.",
  },
  {
    selector: "#legend-panel",
    title: "Reading Plot State",
    text: "Preserved and Recovered plots deepen in colour as they mature, so an older plot earns faster than a new one. Bare plots are flat brown soil, and Replanting plots shift colour as their timer counts down. A long-undisturbed plot also builds biodiversity: cross a threshold and a small wildlife icon appears on the tile.",
  },
  {
    selector: "#pc-readouts",
    title: "Income vs Standing Value",
    text: "Two numbers matter most: harvested income (banked from clearing) and standing forest value (what is still growing). Biodiversity and community relations sit beside them. The Forest summary window (Menu) compares income and value in plain words.",
  },
  {
    selector: "#pc-side",
    title: "Stakeholder Requests",
    text: "Periodically the community asks you to clear your most established standing plot for a real need. A request appears in this column with Grant and Decline buttons (press N to jump to the plot it names). Granting clears the plot and raises community relations by 10; declining keeps it standing but costs 5. Sometimes the community instead offers something good for keeping a plot standing, and then declining is free.",
  },
  {
    selector: "#pc-menu-button",
    title: "Icons and the Menu",
    text: "The icons are Achievements, the Forest Almanac, Ranger contracts, the Seed Vault (perks and idle ranger crews bought with seed points), the Session Summary (income vs standing value, a report card and a shareable recap) and Settings. The Menu (or Escape, when nothing else is open) holds the rest: Levels (a level select where every fifth level is a game mode, such as Poacher Patrol and Storm Front), Reset Session, Name your forest, the Forest summary, grid size and difficulty, the Highland Grove and Wetland Forest regions you unlock as your forest grows, How to Play, the real-world note and story, the example playthrough, What's New and feedback. Everything opens as a window over the forest, and Escape closes the top one.",
  },
  {
    title: "You're ready",
    text: "That's the whole loop: select a plot, decide its fate, and watch how harvested income and standing forest value shift against each other. Weigh community requests as they come. There's no way to lose, only different balances of quick income against a forest left to compound. Good luck out there.",
  },
];

/* shared/story-chapters.js adds its Story list after the page heading, which in this layout is the
   top bar. Once it exists, file it in the "About this forest" window instead. */
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

/* "Name your forest" is a window in this layout: it opens already unfolded (the <details> is only
   a fold on the Classic page). */
(function () {
  function unfold() {
    const names = document.querySelector(".names-details");
    if (names) names.open = true;
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", () => setTimeout(unfold, 0));
  else setTimeout(unfold, 0);
})();
