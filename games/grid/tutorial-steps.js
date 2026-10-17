// The Grid walkthrough, shown by shared/tutorial.js (GameTutorial.init in boot.js). window.GRID_PC_TUTORIAL_STEPS (pc.js) replaces it on the Desktop page.
const GRID_TUTORIAL_STEPS = [
  {
    title: "Welcome to Grid",
    text: "You're managing a regional power grid across a series of rounds. Demand keeps rising — you choose which plant types to build, retire, or maintain to keep up, while balancing cost, emissions, and the risk of disruption. This quick walkthrough covers every system — skip it any time, and reopen it later from the Tutorial button up top.",
  },
  {
    selector: "#status",
    title: "Your Grid at a Glance",
    text: "This panel tracks your grid's state each round: current Demand, your Funds to spend, total Capacity built, and Emissions accumulated so far. Watch these after every action — building costs Funds, and Capacity needs to keep pace with rising Demand.",
  },
  {
    selector: "#plants",
    title: "Build, Retire, Maintain",
    text: "Seven plant types are available: Coal, Gas, Nuclear, Solar, Wind, Hydro, and Battery Storage. Build spends Funds for capacity; Retire removes a unit and refunds half its current cost; Maintain spends Funds to reduce a plant type's average age instead of resetting it to zero. Battery doesn't generate power -- it only helps buffer renewable output when Weather Variability is turned on.",
  },
  {
    selector: "[data-plant=\"solar\"]",
    title: "Renewables Get Cheaper Over Time",
    text: "Solar, Wind, and Hydro get cheaper every time you build another one of that type — a real-world 'learning curve' effect — floored at 40% of their starting price. Coal, Gas, and Nuclear costs never change. Investing in renewables early pays off in lower costs later.",
  },
  {
    selector: "#disruption-risk-display",
    title: "Emissions Drive Disruption Risk",
    text: "Fossil-heavy generation (mostly Coal and Gas) accumulates emissions every round. Rising emissions directly raise the odds and severity of a disruption event next round — this line spells out exactly what your current risk is, in plain terms.",
  },
  {
    selector: "#coal-maintain-button",
    title: "Aging Infrastructure",
    text: "Every standing plant quietly gets older each round. Past 8 rounds old, your oldest fleet risks a costly breakdown that knocks a unit offline. Maintain spends Funds to lower that plant type's average age — it buys time, it doesn't make the plant new again.",
  },
  {
    selector: "#trend-graph",
    title: "Tracking Your Trend",
    text: "This graph plots your emissions (red) against average renewable cost (green) and a hardcoded global-average benchmark (dashed grey) over time — so you can see whether your grid is beating a typical fossil-heavy grid, not just guess.",
  },
  {
    selector: "#score-display",
    title: "Sustained Clean-Grid Score",
    text: "Your score averages how clean your grid's mix has been across every round you've played, not just where it stands right now. A late clean sprint can't fully erase a dirty start, and a dirty finish can't erase an early clean run either — sustained balance is what's rewarded.",
  },
  {
    selector: "#advance-round-button",
    title: "Advance Round",
    text: "When you're done building for this round, click Advance Round. Demand grows, revenue comes in based on capacity met, emissions accumulate, plants age, and a disruption event may trigger based on your current risk. Then it's time to plan the next round.",
  },
  {
    title: "You're Ready to Manage the Grid",
    text: "That's the full loop: build capacity to meet rising demand, lean into renewables early to unlock the learning-curve payoff, maintain aging plants, and keep emissions down to avoid disruption. There's no game over — just a grid that gets harder to manage the longer you delay the clean transition. Good luck out there.",
  },
];
