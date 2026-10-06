/* Continuum, Desktop boot only (loaded by pc.html). The guided tutorial for the Hamlet-based
   layout: the Classic walkthrough points at the Work / Build / Research / Era panels, which
   the Desktop layout replaces with buildings in the scene. index.html uses these steps when
   they exist (window.CONTINUUM_PC_TUTORIAL_STEPS) and its own otherwise. */
window.CONTINUUM_PC_TUTORIAL_STEPS = [
  {
    title: "Welcome to Continuum",
    text: "You're growing a single settlement across eight eras, from a tribal community to a region reaching off-world. This walkthrough covers the Desktop layout, where you play from inside the scene. Skip it any time, and reopen it later from the Tutorial button up top.",
  },
  {
    selector: "#visual-stage",
    title: "The settlement is the controls",
    text: "Every building in the scene is a button. Click a workplace to put an idle person to work there, and use the small minus button on it to take someone off. Click a structure to build it with materials. Hover or focus any building to see what it does and what it costs. You can also Tab through them, and Enter presses the focused one.",
  },
  {
    selector: "#pc-stagebar",
    title: "Camera",
    text: "Drag the scene to rotate it, or use these presets for an overview, a close-up, an aerial or the classic isometric angle. The 2D view and Save Snapshot buttons live here too.",
  },
  {
    selector: "#pc-hud",
    title: "Readouts and trends",
    text: "The chips along the top of the scene are your settlement: people against shelter, food against storage, materials, tools and knowledge. Click one to open a dropdown with what it is doing each season, for example how many people you gain, or how much food is gathered, eaten and spoiled. Food has a hard storage ceiling, so anything gathered past it spoils at the end of the season. Before the first season a Scenario button also appears here.",
  },
  {
    selector: "#pc-hud .pc-dropdown-wrap:nth-child(6)",
    title: "Sustainability Score",
    text: "This score is the whole point: livability, equity, resource balance, and resilience, averaged together. Every input is a ratio, never a raw count, so growing bigger doesn't raise it on its own. Click it to see the four parts.",
  },
  {
    selector: "#speed-controls",
    title: "Time",
    text: "Seasons pass on their own, and the game starts paused so you can read everything first. Press 1x, 2x or 4x to let time run, or Pause any time (or press P).",
  },
  {
    title: "The Town Centre",
    text: "The Town Centre building in the scene opens research, civic challenges and moving to the next era. Spend knowledge to study a node in the research tree; leaving an era is permanent, so the Town Centre also tells you what is still missing.",
  },
  {
    selector: "#pc-menu-button",
    title: "Icons and the Menu",
    text: "The three icons are Achievements, City Views and Settings. The Menu (or Escape, when nothing else is open) holds the rest: the starting scenario, the tutorial, How to Play, the real-world note, What's New, the Civilization Summary, the Log and looking back, the Founder's Log, Council Minutes, Community, fullscreen and the Classic layout. New log entries also pop up over the scene for a few seconds. Everything opens as a window over the scene, and Escape closes the top one.",
  },
  {
    title: "You're ready",
    text: "Put people to work, build, research, and keep an eye on the sustainability score. Carry this settlement as far as it will go, into the Relay Age and beyond, but grow something worth living in. Good luck.",
  },
];
