/* Grid, Desktop boot only (loaded by pc.html). The guided tutorial for the Desktop layout: Classic's
   walkthrough points at the single "status" panel, which the Desktop boot splits into readout chips
   and a side column. index.html uses these steps when they exist (window.GRID_PC_TUTORIAL_STEPS) and
   its own otherwise. */
window.GRID_PC_TUTORIAL_STEPS = [
  {
    title: "Welcome to Grid",
    text: "You're managing a regional power grid across a series of rounds. Demand keeps rising: you choose which plant types to build, retire or maintain to keep up, while balancing cost, emissions and the risk of disruption. This walkthrough covers the Desktop layout. Skip it any time, and reopen it later from the Menu.",
  },
  {
    selector: "#pc-readouts",
    title: "Your Grid at a Glance",
    text: "The chips across the top are your grid right now: the round, Demand, your Funds, total Capacity built, Emissions so far and the fossil share of your capacity. Watch them after every action. Building costs Funds, and Capacity needs to keep pace with rising Demand.",
  },
  {
    selector: "#plants",
    title: "Build, Retire, Maintain",
    text: "One row per plant type: Coal, Gas, Nuclear, Solar, Wind, Hydro and Battery Storage. Build spends Funds for capacity; Retire removes a unit and refunds half its current cost; Maintain spends Funds to reduce a plant type's average age instead of resetting it to zero. Battery doesn't generate power. It only helps buffer renewable output when Weather Variability is turned on.",
  },
  {
    selector: "#solar-build-button",
    title: "Renewables Get Cheaper Over Time",
    text: "Solar, Wind and Hydro get cheaper every time you build another one of that type, a real-world learning curve, floored at 40% of their starting price. Coal, Gas and Nuclear costs never change. Investing in renewables early pays off in lower costs later.",
  },
  {
    selector: "#disruption-risk-display",
    title: "Emissions Drive Disruption Risk",
    text: "In the side column, this line spells out your current disruption risk in plain terms. Fossil-heavy generation (mostly Coal and Gas) adds emissions every round, and rising emissions raise the odds and severity of a disruption next round.",
  },
  {
    selector: "#coal-maintain-button",
    title: "Aging Infrastructure",
    text: "Every standing plant quietly gets older each round. Past 8 rounds old, your oldest fleet risks a costly breakdown that knocks a unit offline. Maintain spends Funds to lower that plant type's average age. It buys time, it doesn't make the plant new again.",
  },
  {
    selector: "#trend-graph-message",
    title: "Tracking Your Trend",
    text: "This graph plots your emissions (red) against average renewable cost (blue, dotted) and a hardcoded global-average benchmark (dashed grey) over time, so you can see whether your grid is beating a typical fossil-heavy grid rather than guess.",
  },
  {
    selector: "#score-display",
    title: "Sustained Clean-Grid Score",
    text: "Your score averages how clean your grid's mix has been across every round you've played, not just where it stands now. A late clean sprint can't fully erase a dirty start, and a dirty finish can't erase an early clean run either. Sustained balance is what's rewarded.",
  },
  {
    selector: "#advance-round-button",
    title: "Advance Round",
    text: "When you're done building for this round, click Advance Round (it stays pinned at the top of this column). Demand grows, revenue comes in based on capacity met, emissions accumulate, plants age, and a disruption may trigger based on your current risk. Then it's time to plan the next round.",
  },
  {
    selector: "#pc-menu-button",
    title: "Icons and the Menu",
    text: "The three icons are Achievements, the Run Summary and Settings. The Menu (or Escape, when nothing else is open) holds the rest: the difficulty toggles and starting scenario, Career, comparing your grid with a shadow grid or a real region, the tutorial, How to Play, the real-world story, What's New, the Weather Log, feedback, fullscreen and the Classic layout. Everything opens as a window over the board, and Escape closes the top one.",
  },
  {
    title: "You're Ready to Manage the Grid",
    text: "That's the full loop: build capacity to meet rising demand, lean into renewables early to unlock the learning-curve payoff, maintain aging plants, and keep emissions down to avoid disruption. There's no game over, just a grid that gets harder to manage the longer you delay the clean transition. Good luck out there.",
  },
];
