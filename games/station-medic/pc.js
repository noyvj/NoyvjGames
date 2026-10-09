/* Station Medic, Desktop boot only (loaded by pc.html). The guided tutorial for the Desktop layout: the Classic walkthrough
   names toolbar buttons, which the Desktop layout turns into icons, the Menu and windows, and the cabinet and sheet sit in a
   side column. index.html uses these steps when they exist (window.STATION_MEDIC_PC_TUTORIAL_STEPS) and its own otherwise. */
window.STATION_MEDIC_PC_TUTORIAL_STEPS = [
  {
    title: "Welcome to the infirmary",
    text: "You are the only medic on Lowlight Station. Crew come in with signs, and you choose the scans and the treatments. Nothing is timed, and a bad call only costs a seal. This is a fiction game with invented conditions, not medical advice. This walkthrough covers the Desktop layout. Skip it any time, and reopen it from the Menu.",
  },
  {
    selector: "#patients",
    title: "The ward",
    text: "Each person waiting is a card. Click one to look at them. Their signs are on the card below: a patient shows all the signs of what they have.",
  },
  {
    selector: "#pc-side",
    title: "The cabinet and the sheet",
    text: "The side column holds the supply cabinet (each shelf has a letter and a count), today's sheet of conditions (their signs, scans and cures) and the shift log. Conditions that cannot fit the patient you are looking at are dimmed.",
  },
  {
    selector: "#bedside-actions",
    title: "Scan and treat",
    text: "A scan answers yes or no and uses a supply. A treatment uses a supply too. Treat only when one condition fits, or when one treatment cures every one that does. Chart notes forbid some treatments.",
  },
  {
    selector: "#restore-button",
    title: "Restore",
    text: "A bad call costs a seal, never a person. You can restore the shift to its start at any time, for free, and try a different plan.",
  },
  {
    selector: "#goals",
    title: "Your goals",
    text: "Three goals stay in view, in any order. Every scan, treatment and hint counts toward something on the screen.",
  },
  {
    selector: "#pc-menu-button",
    title: "Icons and the Menu",
    text: "The icons open the Shifts, the Record, the Achievements and Settings. The Menu, or Escape when nothing else is open, holds the rest: this tutorial, About and What's New. Each opens as a window over the game, and Escape closes the top one.",
  },
  {
    title: "You are ready",
    text: "Take your time. Your seals and records are saved as you go.",
  },
];
