/* Herd, Desktop boot only (loaded by pc.html). The guided tutorial for the Desktop layout: the
   Classic walkthrough points at the single "status" panel, which the Desktop boot turns into
   readout chips and a Menu window. index.html uses these steps when they exist
   (window.HERD_PC_TUTORIAL_STEPS) and its own otherwise. */
window.HERD_PC_TUTORIAL_STEPS = [
  {
    title: "Welcome to Herd",
    text: "You're running a farm. Growing your herd earns income, but it also raises methane emissions automatically, in direct proportion to herd size, from turn one. This walkthrough covers the Desktop layout and the whole loop, including how to break that coupling. Skip any time, and reopen it later from the Menu.",
  },
  {
    selector: "#pc-readouts",
    title: "Your Farm at a Glance",
    text: "The chips across the top are the round, your Funds, Herd size, total accumulated Methane, the Coupling ratio (methane per herd unit), market/regulatory Pressure and your Score. Methane never resets and keeps climbing every round you have any herd. Pressure permanently eats into income (capped at 80% loss), and Score is funds minus a penalty on total methane, so a big bank balance built on unchecked emissions can still score low. The Menu opens the full Status window.",
  },
  {
    selector: "#actions",
    title: "Grow Your Herd",
    text: "Spend funds to add one unit to your herd. A bigger herd earns more income each round, but every unit also emits methane per round, automatically, for as long as it's alive. The line underneath previews exactly what the next unit costs and does. That coupling is the default; nothing else has to happen for it to kick in.",
  },
  {
    selector: "#gauge-section",
    title: "The Coupling Gauge",
    text: "This dial tracks methane produced per herd unit, not your total emissions. CLEAN (green) means low emissions per unit, HIGH (red) means baseline, fully-coupled agriculture. It only falls when you invest in the decoupling measures in the column on the right; it never falls just from having a bigger herd. Below it you can compare yourself with the documented real-world reduction, and the methane graph shows the shape of your run.",
  },
  {
    selector: "#decoupling",
    title: "Decoupling Investments",
    text: "Feed Additives, Herd Caps, and Capture Systems all reduce your coupling ratio (same herd size, lower emissions per unit), and their effects stack. There's a floor, though: past a certain point, further investment stops helping. Worked example: a herd of 10 at the 1.00 baseline ratio emits 10 methane/round. Five Capture Systems investments (10% reduction each) cut the ratio to 0.50, so that same 10-herd farm now emits only 5 methane/round: half the emissions, same herd size, same income per unit.",
  },
  {
    selector: "#plant-pivot",
    title: "Alternative Protein Pivot",
    text: "A different kind of decoupling: shift part of your output to plant-based production instead of making animal production more efficient. It cuts methane per unit much further, but plant-based output earns slightly less income, and it can only replace up to 60% of production.",
  },
  {
    selector: "#advance-round-button",
    title: "Advance Round",
    text: "Nothing happens until you click this (it stays pinned at the top of the column). Growing your herd or investing doesn't generate income or emit methane by itself. Advancing the round applies your herd's income (minus pressure) and adds this round's methane to your running total.",
  },
  {
    selector: "#pc-menu-button",
    title: "Icons and the Menu",
    text: "The three icons are Achievements, the Report Card and Settings. The Menu (or Escape, when nothing else is open) holds the rest: the full Status and score, the pure-growth baseline farm comparison, the community leaderboard, About Herd, the tutorial, How to Play, the real-world story, What's New and feedback. Each opens as a window over the farm, and Escape closes the top one.",
  },
  {
    title: "You're ready",
    text: "That's the loop: grow, watch methane rise automatically, invest to decouple growth from emissions, and advance the round to see it play out. A farm that grows larger and stays more profitable while cutting emissions per unit beats one that just grows unchecked. That's the whole point. Good luck out there.",
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
