// The Le Champ de Mots walkthrough, shown by shared/tutorial.js (GameTutorial.init in boot.js). window.CHAMP_DE_MOTS_PC_TUTORIAL_STEPS (pc.js) replaces it on the Desktop page.
const CHAMP_DE_MOTS_TUTORIAL_STEPS = [
  {
    title: "Welcome to Le Champ de Mots",
    text: "This farm is your FREN151/152 syllabus, laid out one continuous field — every plot is a vocabulary word, phrase, or grammar rule, planted in the order your course teaches it. This quick walkthrough covers how it works — skip it any time, and reopen it later from the Tutorial button up top.",
  },
  {
    selector: "#farm",
    title: "The Farm",
    text: "Each row is one taught week, running straight from FREN151 into FREN152. A new row only unlocks once every plot in the previous row has grown to at least Sprout, so the farm's pace stays roughly matched to real syllabus progress instead of letting you plant everything at once.",
  },
  {
    selector: "#water-next-button",
    title: "Watering a Plot",
    text: "Click this to water whichever plot is due next — a quick recall prompt (translate, fill-in-the-blank, or multiple choice, depending on the plot). You can also click any individual plot in the grid directly to water that one instead. Water options beside it lists other ways to choose: a week, a topic, the wilting plots, quick multiple choice, typing, listening or a minigame. The first correct answer for a plot each day waters it; later ones that day only nudge it.",
  },
  {
    selector: ".accent-toggle",
    title: "Accent Sensitivity",
    text: "This toggle decides whether your typed answers need exact accents (é, è, ç) to count, or whether accents are ignored. It only affects typed answers — multiple-choice questions are unaffected either way.",
  },
  {
    selector: "#legend",
    title: "Growth Stages",
    text: "A plot climbs from Seed to Sprout to Budding to Blooming to Automated as it's recalled correctly over spaced-out visits — Automated plots need only rare maintenance checks. A plot that's gone overdue for review just droops a little; that's a gentle nudge, not a penalty, and one correct answer clears it. The ? Colours and icons button beside the farm lists every other mark you can see.",
  },
  {
    selector: "#next-day-button",
    title: "Advancing the Day",
    text: "Time here only moves when you click this — there's no real clock running in the background. Advancing the day is what makes spaced-out reviews come due, so move the farm forward at whatever pace suits you.",
  },
  {
    selector: ".row-proficiency-button",
    title: "Weekly Proficiency Tests",
    text: "Every unlocked week has its own proficiency test button on its row header — a longer, one-off quiz covering everything taught that week. It's purely informational: taking it never changes any plot's growth or schedule.",
  },
  {
    selector: ".row-bonus-button",
    title: "Bonus Sentence Sections",
    text: "Each week also offers a bonus sentence-building section: order the word tiles, translate each tile, then translate the whole sentence. It's optional extra practice, built only from that week's own vocabulary and grammar.",
  },
  {
    selector: "#review-section",
    title: "Review Tab",
    text: "Opt-in cross-section practice — Random Word Review and Grammar Review pull questions from any unlocked week, filtered to a minimum growth stage you choose. The first correct answer for a plot each day waters it fully, and further correct answers that day only nudge it. A wrong answer changes nothing.",
  },
  {
    title: "You're ready",
    text: "That's the whole field: water what's due, let accurate recall grow each plant and stretch out its interval, and advance the day at your own pace. Nothing here is punishing — a plot can droop, but it never dies, and there's no score being kept against you. Good luck out there.",
  },
];
