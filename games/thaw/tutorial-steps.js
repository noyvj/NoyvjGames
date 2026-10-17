// Thaw's tutorial walkthrough steps (the Classic page; pc.js sets window.THAW_PC_TUTORIAL_STEPS, which boot.js
// prefers on the Desktop page). boot.js hands them to GameTutorial.init once the engine has loaded.
const THAW_TUTORIAL_STEPS = [
  {
    title: "Welcome to Thaw",
    text: "You're managing a northern region as global temperature rises on a fixed background schedule you don't control. This walkthrough covers every system — skip it any time, and reopen it later from the Tutorial button up top.",
  },
  {
    selector: "#status",
    title: "The Background Trajectory",
    text: "Global temperature rises by a fixed amount every round no matter what you do — that's the background trajectory. Funds and warming rate are tracked here; unlike other games in this hub, you aren't the primary driver of the central meter, just someone responding to it.",
  },
  {
    selector: "#melt-status-display",
    title: "The Melt Threshold",
    text: "Once temperature crosses +10.0°, permafrost starts melting and releases methane that adds to next round's warming, on top of the fixed background rise — warming causes melt causes more warming. Below the threshold, permafrost is dormant.",
  },
  {
    selector: "#investments",
    title: "Output, Preservation & Monitoring",
    text: "Each round you can invest in Output (generates funds, no effect on temperature), Permafrost Preservation, or Monitoring & Response. Preservation and Monitoring never generate funds — they're the only investments that dampen the feedback loop.",
  },
  {
    selector: "#dampening-display",
    title: "Feedback Dampening",
    text: "Every Preservation or Monitoring investment raises this percentage, which reduces the methane feedback bonus once melt starts — it never touches the fixed background rise, which always climbs regardless. The line just below confirms the dampening is already in effect, even before melt begins.",
  },
  {
    selector: "#acceleration-display",
    title: "Visible Acceleration",
    text: "This shows warming's current speed as a multiple of the steady background rate. 1x means no feedback yet; it climbs higher the longer melt continues unchecked — that climbing multiple is what a runaway feedback loop looks like.",
  },
  {
    selector: "#trajectory-display",
    title: "The Hope Angle",
    text: "This compares your real temperature to a hidden shadow region that faces the same background trajectory but never receives any Preservation/Monitoring investment. The gap between the two is how many degrees your interventions have actually saved — intervention changes the slope, and the slope matters.",
  },
  {
    selector: "#region-comparison",
    title: "Region B & Region C",
    text: "Two more regions run alongside your own, each free to follow a different strategy against the same background trajectory. Watching an unmanaged region's steep curve next to a managed one's flatter curve, side by side, is the clearest proof that intervention works.",
  },
  {
    selector: "#advance-round-button",
    title: "Advance Round",
    text: "When you're done investing, click here to advance all three regions by one round — funds are collected, temperature rises, and melt/feedback is recalculated for each.",
  },
  {
    title: "Key terms",
    text: "Melt threshold: the temperature (+10°) past which permafrost starts to melt and methane begins adding to the warming rate. Feedback dampening: how much of the methane feedback your Preservation and Monitoring units remove; it never touches the fixed background rise. Acceleration factor: how many times faster than the steady background rise warming is going right now; 1x means no feedback yet. Monitoring & Response: units that each remove a little of the feedback (4%) and add to the shared research station; they never earn funds. The Key terms list in the game has the rest, and the underlined terms near the top of Region A pop up a one-line definition.",
  },
  {
    title: "You're ready",
    text: "That's the whole loop: watch the background trajectory rise, invest in Preservation and Monitoring to dampen the feedback loop before it tips, and advance rounds to see the gap between intervention and inaction grow. Good luck out there.",
  },
];
