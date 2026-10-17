// The Herd walkthrough, shown by shared/tutorial.js (GameTutorial.init in boot.js). window.HERD_PC_TUTORIAL_STEPS (pc.js) replaces it on the Desktop page.
const HERD_TUTORIAL_STEPS = [
  {
    title: "Welcome to Herd",
    text: "You're running a farm. Growing your herd earns income — but it also raises methane emissions automatically, in direct proportion to herd size, from turn one. This walkthrough covers the whole loop, including how to break that coupling. Skip any time, and reopen it later from the Tutorial button up top.",
  },
  {
    selector: "#actions",
    title: "Grow Your Herd",
    text: "Spend funds to add one unit to your herd. A bigger herd earns more income each round — but every unit also emits methane per round, automatically, for as long as it's alive. That coupling is the default; nothing else has to happen for it to kick in.",
  },
  {
    selector: "#gauge-section",
    title: "The Coupling Gauge",
    text: "This dial tracks methane produced per herd unit, not your total emissions — CLEAN (green) means low emissions per unit, HIGH (red) means baseline, fully-coupled agriculture. It only falls when you invest in the decoupling measures below; it never falls just from having a bigger herd.",
  },
  {
    selector: "#status",
    title: "Funds, Herd, Methane & Pressure",
    text: "Your core numbers live here: Funds to spend, Herd size, and total accumulated Methane, which never resets and keeps climbing every round you have any herd at all. Built-up methane also triggers market/regulatory pressure that permanently eats into income (capped at 80% loss) — and Score is funds minus a penalty on total methane, so a big bank balance built on unchecked emissions can still score low.",
  },
  {
    selector: "#decoupling",
    title: "Decoupling Investments",
    text: "Feed Additives, Herd Caps, and Capture Systems all reduce your coupling ratio — same herd size, lower emissions per unit — and their effects stack. There's a floor, though: past a certain point, further investment stops helping. Worked example: a herd of 10 at the 1.00 baseline ratio emits 10 methane/round. Five Capture Systems investments (10% reduction each) cut the ratio to 0.50, so that same 10-herd farm now emits only 5 methane/round — half the emissions, same herd size, same income per unit.",
  },
  {
    selector: "#plant-pivot",
    title: "Alternative Protein Pivot",
    text: "A different kind of decoupling: shift part of your output to plant-based production instead of making animal production more efficient. It cuts methane per unit much further, but plant-based output earns slightly less income, and it can only replace up to 60% of production.",
  },
  {
    selector: "#advance-round-button",
    title: "Advance Round",
    text: "Nothing happens until you click this — growing your herd or investing doesn't generate income or emit methane by itself. Advancing the round is what applies your herd's income (minus pressure) and adds this round's methane to your running total.",
  },
  {
    title: "You're ready",
    text: "That's the loop: grow, watch methane rise automatically, invest to decouple growth from emissions, and advance the round to see it play out. A farm that grows larger and stays more profitable while cutting emissions per unit beats one that just grows unchecked — that's the whole point. Good luck out there.",
  },
];
