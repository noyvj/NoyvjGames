// Le Champ de Mots, Desktop boot only (loaded by pc.html). The guided tutorial for the Desktop layout:
// the Classic walkthrough points at the stats tile, the legend and the Review section, which the Desktop
// layout moves into chips, the stage footer and the side column, and talks about row unlocking that no
// longer exists. index.html uses these steps when they exist (window.CHAMP_DE_MOTS_PC_TUTORIAL_STEPS)
// and its own otherwise. Selectors must start with an #id that exists on pc.html (the farm's rows and
// their per-row buttons are built by game.py, so the farm step covers them in words).
window.CHAMP_DE_MOTS_PC_TUTORIAL_STEPS = [
  {
    title: "Welcome to Le Champ de Mots",
    text: "This farm is your FREN151/152 syllabus, laid out as one continuous field: every plot is a vocabulary word, phrase or grammar rule, planted in the order your course teaches it. This walkthrough covers the Desktop layout. Skip it any time, and reopen it later from the Menu (or press Escape).",
  },
  {
    selector: "#farm",
    title: "The Farm",
    text: "Each block is one taught week, running straight from FREN151 into FREN152, and every week is open from the start. The farm scrolls on its own if it is taller than the window. Click any plot to water that one. Each week's header also has a Proficiency test (a longer, purely informational quiz over that week) and a Bonus sentence button (order the word tiles, translate each tile, then the whole sentence).",
  },
  {
    selector: "#pc-readouts",
    title: "Your numbers",
    text: "The chips along the top show the day, how many plots are ready for water, how much of the farm is growing and automated, and your practice score. The practice score counts correct answers from the minigames, drills and tests, so everything you play adds to something you can see. It never changes a plot's schedule.",
  },
  {
    selector: "#water-next-button",
    title: "Watering a Plot",
    text: "Click this to water whichever plot is due next: a quick recall prompt (translate, fill in the blank, or multiple choice, depending on the plot). The question opens as a window over the farm; Enter checks a typed answer, and Escape closes it. Quick water is the one-question version for a short break, and Water options beside it lists the other ways to choose what to water (a week, a topic, the wilting plots, quick multiple choice, typing, listening or a minigame), each with how many plots it can water right now. The first correct answer for a plot each day waters it; later ones that day only nudge it.",
  },
  {
    selector: "#legend",
    title: "Growth Stages",
    text: "A plot climbs from Seed to Sprout to Budding to Blooming to Automated as it is recalled correctly over spaced-out visits. Automated plots need only rare maintenance checks. A plot that has gone overdue just droops a little; that is a gentle nudge, not a penalty, and one correct answer clears it. The tally and bar above the farm show how many plots sit at each stage.",
  },
  {
    selector: "#accent-toggle-checkbox",
    title: "Accent Sensitivity",
    text: "This decides whether your typed answers need exact accents (é, è, ç) to count, or whether accents are ignored. It only affects typed answers; multiple-choice questions are unaffected either way.",
  },
  {
    selector: "#next-day-button",
    title: "Advancing the Day",
    text: "Time here only moves when you click this: there is no real clock running in the background. Advancing the day is what makes spaced-out reviews come due, so move the farm forward at whatever pace suits you.",
  },
  {
    selector: "#review-section",
    title: "Review Tab",
    text: "Opt-in cross-section practice. Random Word Review, Grammar Review, the Weak-spot drill and the Mixed Review Marathon pull questions from any week, filtered the way you choose. The first correct answer for a plot each day waters it fully, and further correct answers that day only nudge it. A wrong answer changes nothing.",
  },
  {
    selector: "#blitz-toggle-button",
    title: "Study tools and practice games",
    text: "The column holds the practice games below the Review tab: Liaison practice and nine arcade minigames (Greetings and Basics Blitz, Verb Racer, Boutique Dash, Café Rush, the Passé Composé Sprint, Word Match, Grammar Gaps, Listening Pick and Word Order Race). Each opens as a window over the farm, has a Slower, Normal and Faster setting, names the plot a right answer waters, and counts toward your practice score. The sentence builder, conversation, listening and placement test buttons sit with the watering button above.",
  },
  {
    selector: "#pc-menu-button",
    title: "Icons and the Menu",
    text: "The four icons are the Progress dashboard, My phrasebook, Achievements and Settings (where the visual style lives). The Menu (or Escape, when nothing else is open) holds the rest: this tutorial, How to Play, the study calendar, What's New, My Reports, how reviews are scheduled and the story. Everything opens as a window over the farm, and Escape closes the top one.",
  },
  {
    title: "You're ready",
    text: "That is the whole field: water what is due, let accurate recall grow each plant and stretch out its interval, and advance the day at your own pace. Nothing here is punishing: a plot can droop, but it never dies, and there is no score being kept against you. Good luck out there.",
  },
];

// The "?" shortcuts list (shared/keyboard-shortcuts.js) and the first-run visual-style picker are their
// own overlays, not shell windows, so without this an Escape that closes one of them would also open the
// Menu. Flagging the event first (the shell checks this flag in its own capture listener) lets Escape
// just close the overlay.
document.addEventListener("keydown", (e) => {
  if (e.key !== "Escape") return;
  const help = document.getElementById("kb-shortcuts-panel");
  const picker = document.getElementById("visual-style-picker");
  if ((help && !help.hidden) || (picker && !picker.hidden)) e.__pcMenuOpened = true;
  // shared/keyboard-shortcuts.js answers Escape by clicking the Review toggle when the review panel is
  // open, which folds the Review controls instead of ending the session (also true in Classic). Closing
  // the session first, with its own Close button, leaves the controls as they were.
  const review = document.getElementById("review-panel");
  const typing = /^(INPUT|TEXTAREA|SELECT)$/.test((e.target && e.target.tagName) || "");
  if (review && !review.hidden && !typing) {
    const close = document.getElementById("review-close-button");
    if (close) close.click();
  }
}, true);

(function () {
  "use strict";
  const ready = (fn) => {
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", () => setTimeout(fn, 0));
    else setTimeout(fn, 0);
  };

  // shared/story-chapters.js inserts its Story panel right after the h1 once its file loads, which would
  // put it in the top bar. Once it exists, file it in the "About" window instead.
  ready(() => {
    const homeStory = () => {
      const story = document.getElementById("story-chapters");
      const about = document.getElementById("pc-about-panel");
      if (!story || !about) return false;
      if (story.parentNode !== about) about.appendChild(story);
      return true;
    };
    if (homeStory()) return;
    const observer = new MutationObserver(() => { if (homeStory()) observer.disconnect(); });
    observer.observe(document.documentElement, { childList: true, subtree: true });
    setTimeout(() => observer.disconnect(), 20000);
  });

  // The scheduler explainer is a collapsed <details> in Classic; in its own window it starts open.
  ready(() => {
    const explainer = document.getElementById("srs-explainer");
    if (explainer) explainer.open = true;
  });

  // Question and arcade windows: the shell focuses a window's close button when it opens, which is the
  // wrong first stop for a quiz. Move focus to the answer box or the first answer choice (or the Start
  // button of an arcade game), and again whenever a re-render removes the focused control (answering
  // rebuilds the choice buttons), so a whole session can be played from the keyboard.
  const QUESTION_PANELS = [
    "practice-panel", "review-panel", "proficiency-panel", "bonus-panel", "placement-panel", "conversation-panel",
    "builder-panel", "listening-panel", "liaison-panel", "blitz-panel", "racer-panel", "boutique-panel",
    "cafe-panel", "sprint-panel", "pairs-panel", "gaps-panel", "listenpick-panel", "wordorder-panel",
    "water-options-panel",
  ];
  const FOCUS_ORDER = [
    "input:not([hidden])", "[id$='-choices'] button", "[id$='-options'] button", "#builder-pool button",
    "#bonus-tile-pool button", "[id$='start-button']:not([hidden])", "#placement-start-button:not([hidden])",
    "[id$='next-button']:not([hidden])", "#practice-confidence button",
  ];
  const visible = (el) => el && !el.hidden && !el.disabled && el.getClientRects().length > 0;
  function focusQuestion(panel) {
    const frame = panel.closest(".pc-window-frame");
    if (!frame || frame.hidden) return;
    for (const selector of FOCUS_ORDER) {
      const target = [...panel.querySelectorAll(selector)].find(visible);
      if (target) { target.focus({ preventScroll: true }); return; }
    }
  }
  ready(() => {
    QUESTION_PANELS.forEach((id) => {
      const panel = document.getElementById(id);
      if (!panel) return;
      let wasHidden = panel.hidden;
      new MutationObserver((records) => {
        const nowHidden = panel.hidden;
        const opened = wasHidden && !nowHidden;
        wasHidden = nowHidden;
        if (nowHidden) return;
        if (opened) { setTimeout(() => focusQuestion(panel), 0); return; }
        const structural = records.some((r) => r.type === "childList");
        const lost = !document.activeElement || document.activeElement === document.body;
        if (structural && lost) setTimeout(() => { if (!document.activeElement || document.activeElement === document.body) focusQuestion(panel); }, 0);
      }).observe(panel, { attributes: true, attributeFilter: ["hidden"], childList: true, subtree: true });
    });
  });
})();
