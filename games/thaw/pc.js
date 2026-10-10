// Thaw, Desktop boot only (loaded by pc.html). The guided tutorial for the Desktop layout: the Classic
// walkthrough points at sections the Desktop layout rearranges (the numbers become chips, the second
// and third regions share a panel). index.html uses these steps when they exist
// (window.THAW_PC_TUTORIAL_STEPS) and its own otherwise.
window.THAW_PC_TUTORIAL_STEPS = [
  {
    title: "Welcome to Thaw",
    text: "You're managing a northern region as global temperature rises on a fixed background schedule you don't control. This walkthrough covers the Desktop layout. Skip it any time, and reopen it later from the Menu (or press Escape).",
  },
  {
    selector: "#pc-readouts",
    title: "Your numbers",
    text: "The chips along the top show the round, your funds, the global temperature and, side by side, where Region B and Region C stand. The temperature keeps climbing each round whatever you do: that's the background trajectory. You are someone responding to it, not the main driver of the meter.",
  },
  {
    selector: "#melt-status-display",
    title: "The Melt Threshold",
    text: "Once temperature crosses +10.0°, permafrost starts melting and releases methane that adds to next round's warming on top of the fixed background rise: warming causes melt causes more warming. Below the threshold, permafrost is dormant. The status block around this line is Region A, your home region.",
  },
  {
    selector: "#pc-side",
    title: "Invest each round",
    text: "The right-hand column holds your decisions and scrolls on its own, with Advance Round pinned at the top. Output generates funds and has no effect on temperature. Permafrost Preservation and Monitoring & Response never earn funds, but they are the only investments that dampen the feedback loop. Below them: the carbon bank, the optional forecast mini-game and the starting policy stance.",
  },
  {
    selector: "#dampening-display",
    title: "Feedback Dampening",
    text: "Every Preservation or Monitoring investment raises this percentage, which reduces the methane feedback bonus once melt starts. It never touches the fixed background rise. The line just below it confirms the dampening is already in effect, even before melt begins.",
  },
  {
    selector: "#acceleration-display",
    title: "Visible Acceleration",
    text: "This shows warming's current speed as a multiple of the steady background rate. 1x means no feedback yet; it climbs the longer melt continues unchecked, and that climbing multiple is what a runaway feedback loop looks like. The graph beneath it draws the same trajectory.",
  },
  {
    selector: "#trajectory-display",
    title: "The Hope Angle",
    text: "This compares your real temperature to a hidden shadow region that faces the same background trajectory but never receives any Preservation or Monitoring. The gap between the two is how many degrees your interventions have actually saved: intervention changes the slope, and the slope matters.",
  },
  {
    selector: "#region-comparison",
    title: "Region B & Region C",
    text: "Two more regions run alongside your own, each free to follow a different strategy against the same background trajectory, with one-click presets for each. Watching an unmanaged region's steep curve next to a managed one's flatter curve is the clearest proof that intervention works. Region D, the pure-neglect baseline, is in the Menu.",
  },
  {
    selector: "#advance-round-button",
    title: "Advance Round",
    text: "When you're done investing, click here to advance all regions by one round: funds are collected, temperature rises, and melt and feedback are recalculated for each.",
  },
  {
    selector: "#pc-menu-button",
    title: "Icons and the Menu",
    text: "The three icons are Achievements, the Climate Scientist (real NOAA methane data) and Settings. The Menu (or Escape, when nothing else is open) holds everything else: the climate archive and scientist's log, Four regions one story, Region D, long-game and framing options, community comparison, How to Play, the real-world story, What's New and feedback. Each opens as a window over the game, and Escape closes the top one. Key moments in your regions also pop up as notifications over the stage.",
  },
  {
    title: "Key terms",
    text: "Melt threshold: the temperature (+10°) past which permafrost starts to melt and methane begins adding to the warming rate. Feedback dampening: how much of the methane feedback your Preservation and Monitoring units remove; it never touches the fixed background rise. Acceleration factor: how many times faster than the steady background rise warming is going right now; 1x means no feedback yet. Monitoring & Response: units that each remove a little of the feedback (4%) and add to the shared research station; they never earn funds. The Key terms window in the Menu has the rest, and the underlined terms in Region A's block pop up a one-line definition.",
  },
  {
    title: "You're ready",
    text: "That's the whole loop: watch the background trajectory rise, invest in Preservation and Monitoring to dampen the feedback loop before it tips, and advance rounds to see the gap between intervention and inaction grow. Good luck out there.",
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

// The Classic page keeps the tool sections (board room, planner, ...) as collapsed <details>; in a
// Desktop window the window title already names them, so open them once the shell has built the windows.
window.addEventListener("load", () => {
  document.querySelectorAll(".pc-composite details.tool-section").forEach((d) => { d.open = true; });
});
