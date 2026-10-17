// Continuum's tutorial walkthrough steps (the Classic page; pc.js sets window.CONTINUUM_PC_TUTORIAL_STEPS, which boot.js
// prefers on the Desktop page). boot.js hands them to GameTutorial.init once the engine has loaded.
const CONTINUUM_TUTORIAL_STEPS = [
  {
    title: "Welcome to Continuum",
    text: "You're growing a single settlement across eight eras, from a tribal community to a region reaching off-world. This walkthrough covers the systems you have right now — skip it any time, and reopen it later from the Tutorial button up top.",
  },
  {
    selector: "#scenario-select",
    title: "Starting Scenario & Hard Mode",
    text: "Pick a starting scenario before you advance your first season — it's locked in once play begins. Hard Mode tightens the sustainability score's penalties and thresholds, and can be switched on or off at any time.",
  },
  {
    selector: "#status",
    title: "The Settlement",
    text: "Your season, population versus available shelter, and four resources: food, materials, tools, and knowledge. Food has a hard storage ceiling — anything gathered past it spoils at the end of the season, so storage matters as much as gathering.",
  },
  {
    selector: "#land-health-display",
    title: "Land Health",
    text: "The land can only sustainably yield so much food per season. Harvest past that line and land health drops, cutting every future harvest — stay under it and the land recovers instead. This is what lets a small, careful settlement out-score a big, careless one.",
  },
  {
    selector: "#work",
    title: "Assign Work",
    text: "Move people between roles with the +/- buttons. Foragers bring in food, Gatherers bring in materials, Crafters turn materials into tools, and Keepers produce knowledge — the one currency that funds research across all eight eras.",
  },
  {
    selector: "#buildings",
    title: "Build",
    text: "Spend materials to build. Shelter raises how many people you can house, the Storage Pit raises how much food you can bank before it spoils, the Fire Circle holds the settlement together, and the Knapping Site boosts what your Crafters produce.",
  },
  {
    selector: "#sustainability",
    title: "Sustainability Score",
    text: "This score is the whole point: livability, equity, resource balance, and resilience, averaged together. Every input is a ratio, never a raw count, so growing bigger doesn't raise it on its own — equity in particular is capped by whichever basic need is worst-met, not the average.",
  },
  {
    selector: "#research",
    title: "Research Tree",
    text: "One tree spans all eight eras, sixteen tiers deep across three branches — provision, community, and craft. Spend knowledge to study a node; a tier opens once enough of the tier below it is researched. Early choices echo later: leaning into a branch can open or close doors many tiers on.",
  },
  {
    selector: "#speed-controls",
    title: "Time",
    text: "Seasons pass on their own, and the game starts paused so you can read everything first. Press 1x, 2x or 4x to let time run, or Pause any time (or press P). Each season your workers produce, your people eat, the land responds to how hard you pushed it, and population grows if there's food and shelter to spare. Time only runs while this page is open.",
  },
  {
    selector: "#info-page-toggle-button",
    title: "The Real Story",
    text: "Open this any time to read the real anthropology and archaeology behind whatever era the settlement is currently in — it updates automatically as the settlement moves through the ages.",
  },
  {
    selector: "#log",
    title: "The Log",
    text: "A running record of what's happened — a discovery, a population milestone, a shift in how the settlement is doing. It reacts to good and bad news alike, in the settlement's own voice. Read it or don't; nothing here is blocking or required.",
  },
  {
    selector: "#era-progress",
    title: "Moving to a New Era",
    text: "This shows what it takes to move the settlement into its next era, and why it isn't ready yet if it isn't. Leaving an era is permanent — you can look back at how it went later, but you can't undo the move forward.",
  },
  {
    selector: "#revisit",
    title: "Looking Back",
    text: "Once you've completed at least one era, you can look back at it exactly as it stood when you left — the settlement, the tree, the 3D scene, all frozen at that moment. Nothing you do during a look-back affects your forward progress.",
  },
  {
    selector: "#achievements-toggle-button",
    title: "Achievements",
    text: "Reaching an era, mastering a research branch, and running a genuinely well-balanced settlement all earn achievements — check here any time to see what's left.",
  },
  {
    selector: "#summary-toggle-button",
    title: "Civilization Summary",
    text: "An on-demand recap of the whole playthrough so far — eras completed, total seasons, peak population and sustainability, and how each era you've finished actually went. Check it any time; there's no forced end screen.",
  },
  {
    title: "You're ready",
    text: "Assign work, build, research, and keep an eye on the sustainability score — then advance the season and see how it all played out. Carry this settlement as far as it will go, into the Relay Age and beyond, but grow something worth living in. Good luck.",
  },
];
