/* Rule Finder, Desktop boot only (loaded by pc.html). The guided tutorial for the Desktop layout: the Classic walkthrough
   names toolbar buttons, which the Desktop layout turns into icons, the Menu and windows. index.html uses these steps when
   they exist (window.RULE_FINDER_PC_TUTORIAL_STEPS) and its own otherwise. */
window.RULE_FINDER_PC_TUTORIAL_STEPS = [
  {
    title: "Welcome to the signal room",
    text: "An old relay lets some items through its gate and stops the rest. Every case hides one rule. Your job is to find it and name it. Nothing is timed, testing is free, and a wrong name only shows you one item to think about. This walkthrough covers the Desktop layout. Skip it any time, and reopen it from the Menu.",
  },
  {
    selector: "#gate-holder",
    title: "The gate",
    text: "Items come in from the left. If the rule lets one in, the doors open and it goes Through; if not, the bars come down and it is Stopped. The lamps, the words and the ticks and crosses all say the same thing.",
  },
  {
    selector: "#bins",
    title: "Your log",
    text: "The starting examples are already here, Through on the left and Stopped on the right. Everything you send is added.",
  },
  {
    selector: "#builder",
    title: "Build an item",
    text: "Build your own test item and press Send it, or press Enter. Numbers, strings of shapes and little patterns each have their own builder, with number keys for the shapes and squares. Every test is free.",
  },
  {
    selector: "#rule-rows",
    title: "The Rule Builder",
    text: "When you think you know the rule, pick the property the gate looks at. Tick Not to turn it around, and in later drawers add a clause to join two or three with and or or.",
  },
  {
    selector: "#name-button",
    title: "Name it",
    text: "Your rule is right when it agrees with the hidden one on every possible item. If it is not, you see one item it gets wrong, free, and you try again.",
  },
  {
    selector: "#hint-button",
    title: "Hints are free",
    text: "A nudge says what kind of property to look at, a hint suggests a good item to send, and the answer writes the rule out. They open one at a time, only when you press.",
  },
  {
    selector: "#goals",
    title: "Your goals",
    text: "Three goals stay in view, in any order. Every test you send, hint you ask for and case you name counts toward something on the screen.",
  },
  {
    selector: "#pc-menu-button",
    title: "Icons and the Menu",
    text: "The icons open the Drawers wall, the Rule Codex, Achievements and Settings. The Menu, or Escape when nothing else is open, holds the rest: this tutorial, About and What's New. Each opens as a window over the game, and Escape closes the top one.",
  },
  {
    title: "You are ready",
    text: "Take your time. Your progress is saved as you go.",
  },
];
