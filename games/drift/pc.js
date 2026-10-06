// Drift, Desktop boot only (loaded by pc.html). The guided tutorial for the Desktop layout: the Classic
// walkthrough points at sections the Desktop layout rearranges (the numbers become chips, the
// Long-Horizon Outcomes coda opens as a window). index.html uses these steps when they exist
// (window.DRIFT_PC_TUTORIAL_STEPS) and its own otherwise.
window.DRIFT_PC_TUTORIAL_STEPS = [
  {
    title: "Welcome to Drift",
    text: "You're managing a receiving region's response to rising climate-driven displacement. This isn't about stopping the pressure, which is mostly outside your control: it's about whether your region's institutions turn it into a crisis or a manageable transition. This walkthrough covers the Desktop layout. Skip it any time, and reopen it later from the Menu (or press Escape).",
  },
  {
    selector: "#pc-readouts",
    title: "Your numbers",
    text: "The chips along the top show the round, your funds, total capacity, strain, people still pending integration and the wellbeing score. Funds pay for capacity investments and rise from base regional income plus what integrated arrivals contribute back.",
  },
  {
    selector: "#pressure",
    title: "Displacement pressure & strain",
    text: "Arrivals rise each round with background climate severity, largely outside your control. Strain measures how far cumulative arrivals have outrun your cumulative capacity across the whole run; higher strain cuts your income each round and stays elevated even if you catch up later, so getting ahead of pressure matters more than reacting to it. The region skyline above dims as strain rises.",
  },
  {
    selector: "#integration",
    title: "Integration",
    text: "Only Integration Services capacity determines how many pending arrivals become integrated each round: housing and infrastructure don't speed this up. Integrated people then contribute funds back every round after that. Watch for the turning-point message here, the round integration flips from cost to net gain.",
  },
  {
    selector: "#wellbeing",
    title: "Regional wellbeing",
    text: "Wellbeing is the average of three separately tracked scores: service quality (how well strain has stayed low over the whole run), economic health (funds against a reference scale) and social cohesion (the share of arrivals actually integrated). The message below the gauges tells you which one is lagging, and the graph at the bottom draws strain and wellbeing over the rounds.",
  },
  {
    selector: "#capacity",
    title: "Capacity investments",
    text: "The right-hand column holds your decisions and scrolls on its own. Spend funds on Housing, Integration Services or Infrastructure. Each adds capacity against arrival pressure, but Integration Services is the only one that moves pending people to integrated. The policy toolkit below it adds three permanent institutional levers.",
  },
  {
    selector: "#advance-round-button",
    title: "Advance Round",
    text: "Locks in this round's investments and resolves everything: new arrivals, strain, integration progress and income. There's no wait-timer, so invest first, then advance. The button stays pinned at the top of the column.",
  },
  {
    selector: "#pc-menu-button",
    title: "Icons and the Menu",
    text: "The three icons are Achievements, How to Play and Settings. The Menu (or Escape, when nothing else is open) holds everything else: the Accelerated Severity and Crisis Start options, the tutorial, the real-world story, What's New, About Drift and feedback. Each opens as a window over the game, and Escape closes the top one. Once at least one person is integrated, a Long-Horizon Outcomes button appears above the investments; it opens a window projecting your trajectory a few generations forward.",
  },
  {
    title: "You're ready",
    text: "That's the loop: prepare capacity ahead of pressure, keep services throughput high enough to integrate arrivals, and watch wellbeing rise as strain falls and contribution grows. A well-prepared region can absorb real pressure without it becoming a crisis. Good luck.",
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

// shared/story-chapters.js inserts the Story panel right after the h1 once its file has loaded. Whether
// that happens before or after the shell moves the h1 into the top bar depends on timing, so the panel
// can end up at the bottom of the page instead of in the top bar. Whichever order it happens in, move it
// into the top bar (where pc.css styles it as a pill that opens as a floating card).
(function homeStoryPanel() {
  const move = () => {
    const panel = document.getElementById("story-chapters");
    const bar = document.getElementById("pc-topbar");
    if (!panel || !bar) return false;
    if (panel.parentNode !== bar) bar.appendChild(panel);
    return true;
  };
  const start = () => {
    move();
    const observer = new MutationObserver(() => { move(); });
    observer.observe(document.body, { childList: true, subtree: true });
    setTimeout(() => observer.disconnect(), 15000);
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", () => setTimeout(start, 0));
  else setTimeout(start, 0);
})();
