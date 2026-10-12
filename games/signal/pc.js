/* Signal, Desktop boot only (loaded by pc.html). The guided tutorial for the Desktop layout: the Classic
   walkthrough points at sections the Desktop layout rearranges (the status line becomes readout chips, the
   tool toggle and answer buttons move to a side column). index.html uses these steps when they exist
   (window.SIGNAL_PC_TUTORIAL_STEPS) and its own otherwise. */
window.SIGNAL_PC_TUTORIAL_STEPS = [
  {
    title: "Welcome to Signal",
    text: "Hidden transmitters are broadcasting somewhere on this grid. You can only listen at a few tiles, and each listen returns one number: the summed signal of every transmitter at that tile. This walkthrough covers the Desktop layout. Skip it any time, and reopen it later from the Menu (or press Escape).",
  },
  {
    selector: "#pc-readouts",
    title: "Your puzzle at a glance",
    text: "The chips show which puzzle you are on, how many pings you have left, par (how many pings a solver needed) and how many markers you have placed against how many transmitters there are. The mode tabs above the grid switch between the Easy and Hard dailies, the archive of past days and endless practice.",
  },
  {
    selector: "#board",
    title: "Ping a tile",
    text: "Click a tile to ping it, or move with the arrow keys and press Enter (or type a column letter and a row number, like D4, to jump). Each ping spends one from your budget. Nothing broadcasts from the outer ring. A single transmitter reads its radius minus the distance, and nothing beyond that, so a 5 could be one close transmitter or several far ones.",
  },
  {
    selector: "#waterfall-section",
    title: "Read the number",
    text: "Every reading appears here in the order you pinged. The number, the bar glyph and the fill height all say the same thing, so you never need colour to read them. Compare readings to work out where the transmitters must be: tiles your readings have ruled out are hatched in Easy.",
  },
  {
    selector: "#tool-toggle-button",
    title: "Mark your suspects",
    text: "Switch the tool to Mark (or press Space on a tile, or right-click it) to drop a diamond where you think a transmitter is. You need exactly one marker per transmitter.",
  },
  {
    selector: "#commit-button",
    title: "Commit",
    text: "When your markers match the transmitter count, commit. Every transmitter must be exactly right to win. Fewer pings than par is the boast. Then copy a spoiler-free result to share.",
  },
  {
    selector: "#pc-menu-button",
    title: "Icons and the Menu",
    text: "The four icons are the Archive of past days, Stats, Achievements and Settings. The Menu (or Escape, when nothing else is open) holds the rest: this tutorial, How to Play, About Signal, What's New, the community leaderboard and feedback. Each opens as a window over the game, and Escape closes the top one.",
  },
  {
    title: "You're ready",
    text: "That's the loop: ping, read, narrow it down, mark, commit. A new daily puzzle goes on the air every UTC midnight, and endless practice has bigger boards if you want more. Good luck.",
  },
];

// The Desktop layout is for wide windows, so the shared mobile dock (which would lift the answer buttons
// out of the side column into a fixed bar below 640px, and drop them back in the wrong place on widening)
// is switched off here. shared/mobile-dock.js assigns window.MobileDock after this file runs; the setter
// below keeps this inert stand-in in its place.
Object.defineProperty(window, "MobileDock", { configurable: true, get() { return { init() {} }; }, set() {} });
