// Drift's tutorial walkthrough steps (the Classic page; pc.js sets window.DRIFT_PC_TUTORIAL_STEPS, which boot.js
// prefers on the Desktop page). boot.js hands them to GameTutorial.init once the engine has loaded.
const DRIFT_TUTORIAL_STEPS = [
  {
    title: "Welcome to Drift",
    text: "You're managing a receiving region's response to rising climate-driven displacement. This isn't about stopping the pressure — that's mostly outside your control — it's about whether your region's institutions turn it into a crisis or a manageable transition. Skip this any time, and reopen it later from the Tutorial button up top.",
  },
  {
    selector: "#status",
    title: "Region status",
    text: "Round, Funds, and Total capacity are your basic snapshot every round. Funds pay for capacity investments and rise from base regional income plus what integrated arrivals contribute back; Total capacity is your combined housing, services, and infrastructure capacity.",
  },
  {
    selector: "#pressure",
    title: "Displacement pressure & strain",
    text: "Arrivals rise each round with background climate severity — largely outside your control. Strain measures how far cumulative arrivals have outrun your cumulative capacity across the whole run; higher strain directly cuts into your income each round and stays elevated even if you catch up later, so getting ahead of pressure matters more than reacting to it.",
  },
  {
    selector: "#capacity",
    title: "Capacity investments",
    text: "Spend funds on Housing, Integration Services, or Infrastructure. Each adds capacity that counts against arrival pressure — but Integration Services does something the other two don't: it's the only one that moves arrived people from pending to integrated.",
  },
  {
    selector: "#integration",
    title: "Integration",
    text: "Only Integration Services capacity determines how many pending arrivals become integrated each round — housing and infrastructure don't speed this up. Integrated people then contribute funds back every round after that. Watch for the turning-point message here: it marks the round your integrated arrivals' contributions have paid back the services investment that enabled them — the moment integration flips from cost to net gain.",
  },
  {
    selector: "#wellbeing",
    title: "Regional wellbeing",
    text: "Wellbeing is the average of three separately-tracked scores, not one blended number: service quality (how well strain has stayed low over the whole run), economic health (funds against a reference scale), and social cohesion (the share of arrivals actually integrated). The message below tells you which one is lagging.",
  },
  {
    selector: "#advance-round-button",
    title: "Advance Round",
    text: "Locks in this round's investments and resolves everything: new arrivals, strain, integration progress, and income. There's no wait-timer here — every round is an active decision, so invest first, then advance.",
  },
  {
    selector: "#round-tools",
    title: "Round tools",
    text: "Reset this round refunds everything you decided since the round began. The Rewind Token undoes the last Advance Round once per region. Play 5 rounds advances with your current allocation and stops early when strain rises a level or a forecast event arrives. Under them, a recap line says what the last round did; the Round Ledger and Collection buttons up top keep the full record.",
  },
  {
    selector: "#coda-button",
    title: "Long-Horizon Outcomes",
    text: "Once at least one person has been integrated, this reveals a projection of your current trajectory a few generations forward — a rough extrapolation, not a guarantee, showing what durable integration compounds into over the long run.",
  },
  {
    title: "You're ready",
    text: "That's the loop: prepare capacity ahead of pressure, keep services throughput high enough to integrate arrivals, and watch wellbeing rise as strain falls and contribution grows. A well-prepared region can absorb real pressure without it becoming a crisis — that's the whole point. Good luck.",
  },
];
