"""Stranded -- story data, days 1 to 3 (first contact, the count, Bit)."""

from kit import C, S

SCENES = [
    S("d1a", 1, "Wrong Channel", [
        "...hello? Is that Harbour? The relay board says you're the night voice. Please tell me you're not a recording.",
        "Ines Varga, Sparrow Relay, Orrin. Alive. Mostly annoyed.",
        "My lander has a crack in it and I would like it noted that I did not put it there.",
    ], [
        C("Hello, Ines. I'm here, and I'm staying on the line.",
          ["Staying. Right. That's what the last voice said before the budget meeting.", "...Sorry. That was rude. It's good to read a person. Hello, Harbour."],
          "d1b", fx="t1 h1"),
        C("Status report, please. Start with the lander.",
          ["Wow. Straight to the damage. Do you also ask people their shoe size before hello?", "Fine. Lander first."],
          "d1c"),
        C("Night shift. Cold biscuits, warm opinions. Yours?",
          ["Ha. Cold biscuits. I would trade you a moon for one.", "Opinions I have. Biscuits I do not."],
          "d1b", fx="h2"),
    ]),
    S("d1b", 1, "Her Side of It", [
        "Landed yesterday on the dust side of Orrin, which is every side.",
        "Sparrow was meant to be a day's work: swap a power cell, relight the relay, go home with a medal and a sandwich.",
        "Then a storm rolled through and rattled Kestrel like a dice cup.",
        "Now the relay is dark, the lander is cracked, and my radio is a dish on a stick.",
    ], [
        C("A dish on a stick still reached me. That's something.",
          ["It is something. It is also held together with tape I was saving.", "...Don't tell anyone about the tape."], "d1d", fx="t1"),
        C("What do you need first?", ["A sandwich. A medal. Failing both, a plan."], "d1d", fx="h1"),
        C("Tell me about the storm.", ["The storm wasn't the worst of it. Never mind. Next question."], "d1d"),
    ]),
    S("d1c", 1, "The Report", [
        "Kestrel: the ascent stage has a crack in a line somewhere between the tank and the engine. Where exactly, I would rather not say yet.",
        "Dish: fragile. I nudge it every morning.",
        "Rations: plenty.",
        "Oxygen: plenty.",
        "That's the report. You may now compliment my brevity.",
    ], [
        C("'Plenty' twice, very quickly. Good brevity. I'm writing down 'plenty, approximately'.",
          ["Approximately is a fair word. Put it in the margin."], "d1d", fx="t1"),
        C("Thank you. That helps.", ["See? Brevity."], "d1d", fx="h1"),
        C("Where is 'somewhere'?",
          ["Somewhere is a place I will tell you about when I'm ready. Like every other place."], "d1d", fx="t-1"),
    ]),
    S("d1d", 1, "The Dish", [
        "One more thing, and then I will let you go back to your biscuits.",
        "The dish only holds the line if it's pointed right. There's a stiff joint on the mast and I give it a nudge every morning.",
        "If it slips you'll hear nothing from me until I fix it. Don't panic. I'll just be ignoring you.",
    ], [
        C("Let me talk you through the mast joint now.",
          ["You can't see the mast.", "...But you can tell me when I'm doing it wrong. Hold on, I'll get the wrench."],
          "d2a", fx="t1 h1", set="dishgood", get="log_01"),
        C("Rest first. Nudge it tomorrow.", ["Rest. Revolutionary. I'll write it on my hand."], "d2a", fx="h2"),
        C("Describe the whole camp for me.",
          ["The camp is a lander, a hut and a dish. I'll draw it. Don't laugh."], "d2a", fx="t1", get="item_sketch"),
    ]),

    S("d2a", 2, "The Count", [
        "Inventory. Since you're the nosy sort.",
        "Meal packs: eleven. Water: fine, the relay house has a still. Oxygen: fine. Spare tape: less than I'd like. Chocolate: one bar, classified.",
        "Eleven packs is not eleven days, by the way. If I eat like a bird it's about nine. I eat like a seagull.",
    ], [
        C("Let's ration it together, with a plan on paper.",
          ["Paper. We have no paper. We have a tablet with a cracked corner.", "Fine. A plan. I hate that you're right."],
          "d2b", fx="s2 t1", set="ration"),
        C("You know your stores. How are you, though?", ["Fine.", "That's the short answer. The long answer is also fine."], "d2c", fx="t1 h1"),
        C("Tell me about the classified chocolate.",
          ["No.", "...It's the dark one with orange. I'm saving it for something that needs it."], "d2d", fx="h1", get="item_bar"),
        C("Eleven packs, you'll manage. It'll be fine, Ines. It always is.",
          ["Don't. 'It'll be fine' is what people say before they have read the number.",
           "...I know you mean it. I'll say the number myself. Eleven. Nine, if I eat like a bird. Now you know."],
          "d2d", fx="t-1 h1", set="quick"),
    ]),
    S("d2b", 2, "The Plan", [
        "Three packs a day for three days, then we see.",
        "I wrote it on my arm. Don't tell the medical office I used a pen on my arm.",
        "...I gave myself the small portion. Don't look at me like that. I can't see you looking.",
    ], [
        C("Take the bigger portion. That's an order from the night shift.",
          ["You don't give orders. You give suggestions with commas.", "...Fine. Bigger portion. Hush."], "d2d", fx="t1 s-1 h1"),
        C("Small is fine, as long as you eat something.", ["I'm eating. I'm reporting. Same thing."], "d2d", fx="s1"),
        C("You're hiding something about the numbers.", ["I'm hiding nothing. I'm curating."], "d2d", fx="t-1"),
    ]),
    S("d2c", 2, "Fine", [
        "I don't sleep well in the lander. It creaks like it's thinking.",
        "In the hut it's quiet. Too quiet. I talk to the walls.",
        "They don't answer, which is honestly a relief.",
    ], [
        C("I'll answer. Talk to me instead.", ["You're on the other end of a dish. You're a wall that types."], "d2d", fx="t1 h2"),
        C("Leave the walls a goodnight message.", ["That's stupid. Hold on. Recording."], "d2d", fx="h1", get="rec_01"),
        C("Sleep in the hut tonight. It's quieter.", ["Bossy, but fine. Hut it is."], "d2d", fx="t1"),
    ]),
    S("d2d", 2, "Evening", [
        "Done with numbers. The sun is low on the grey and the gas giant is up over the ridge, enormous, the colour of a bruise. Best thing about this moon.",
        "Ask me something, Harbour. Anything. Not the lander.",
    ], [
        C("What's really wrong with Kestrel?",
          ["...The fuel line. Between the tank and the engine. A split you could slide a coin into.",
           "I can't fly with it and I can't fix it without a part I'm not sure we have. That's the real thing."],
          "d3a", fx="t1", set="knowfuel", get="log_02", need="t4"),
        C("What do you see out there?", ["The ring. Light from nowhere. A hut with one dark window and a lander with a bad back."], "d3a", fx="h2"),
        C("Goodnight, Ines.", ["Goodnight, Harbour. Don't touch my chocolate."], "d3a", fx="t1"),
    ]),

    S("d3a", 3, "The Relay House", [
        "I went into the relay house. It's the grey box with the shut door I've been ignoring.",
        "Cold in there. Smells like old coins. A rack of dark boards, a still, a bench and, in the corner, a bin.",
        "The bin has a lamp on it. The lamp is off. It's a maintenance robot, sitting there like something told to wait that nobody came back for.",
    ], [
        C("Wake it up.", ["It might not like being woken. I wouldn't.", "Fine. Spending a little charge from my pack."], "d3b", fx="s-1", set="bit"),
        C("Leave it. Don't touch what you don't understand.",
          ["I touch things I don't understand. It's my whole profession.", "...But fine. It isn't going anywhere."], "d3c", fx="h-1"),
        C("Its battery could power the dish properly.",
          ["That's the practical thing. I hate the practical thing."], "d3d", fx="s1", set="battery"),
    ]),
    S("d3b", 3, "Bit", [
        "*The lamp flickers twice. Then a small, sulky amber glow.*",
        "It's looking at me. One eye and no opinions.",
        "It beeped. Once. Short. Like a question.",
        "I'm calling it Bit. Because it's the bit I could fix.",
    ], [
        C("Tell Bit hello from Harbour.",
          ["*Bit swivels toward the dish. The lamp goes soft.*", "It knows the dish is the way to you. Clever, annoying robot."], "d4a", fx="t1 h2"),
        C("Ask Bit to scan the wall for wiring.",
          ["*Bit's lamp sweeps. A line of tiny amber dots draws the cables across the wall.*",
           "It's showing me a map. The power runs to a hatch under the dust, east of the dish."], "d4a", fx="t1", set="wiring", get="log_03"),
        C("Ask Ines how she feels about having company.",
          ["Company. It beeps. Who asked for company.", "...I did, a bit. Don't write that down."], "d4a", fx="t1 h2"),
    ]),
    S("d3c", 3, "Left Alone", [
        "I left it. It's in the corner doing the thing where a thing looks at you without looking.",
        "I did tidy the bench. Not for the robot. For me.",
        "Don't you dare say 'for the robot'.",
    ], [
        C("Say nothing about the robot.", ["Good."], "d4a"),
        C("You can wake it tomorrow if you want.", ["...Maybe tomorrow."], "d4a", fx="t1 h1"),
        C("Read me what's on the bench.",
          ["Tools. A plaque. A hand-lettered sign that says KEEP THE DISH POINTED. The only useful advice on this moon."], "d4a", get="item_plaque"),
    ]),
    S("d3d", 3, "Borrowed Power", [
        "Done. Took the cell out.",
        "The dish is stronger. I can hear you without squinting.",
        "Bit's lamp went out when I took it. It didn't beep. I'm choosing to believe it didn't mind.",
    ], [
        C("Thank Bit.", ["Thanking a bin. A new low.", "...Thank you, Bit. Sorry about the cell."], "d4a", fx="t1"),
        C("It's a good trade. The line matters.", ["It matters. Doesn't make it clean."], "d4a", fx="s1"),
        C("Put the cell back if it bothers you.", ["No. Not now. I'll put it back when I can."], "d4a", fx="t1 h-1"),
    ], set="dishgood"),
]
