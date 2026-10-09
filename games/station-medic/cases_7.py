"""Chapter 7, Two at Once: some patients carry two conditions together, and show the signs of both. Work out the pair, then choose
cures that do not clash: two heavy treatments never go together."""

from casekit import P, S

SHIFTS = [
    S("7-1", "Two in One", "Maren shows the signs of two conditions at once. The sheet lists every pair that fits; a scan can tell the pairs apart.",
      "vent brass coil", {"cells": 1, "drip": 1, "loz": 1, "wrap": 1},
      [P("maren", "vent brass", "A cough and a fever together, and I thought one was the other's fault. The tomatoes agree with me.")],
      tests="lamp", maxc=2),
    S("7-2", "The Heavy Pair", "Two conditions, and the quickest cure for each is heavy. Heavy treatments never go together.",
      "dust drift", {"drip": 1, "tonic": 1, "vials": 1},
      [P("orla", "dust drift", "A cough and a tilting floor. I have given orders on worse. Please be quick; I do not like to be seen sitting.")],
      maxc=2, robots=1),
    S("7-3", "Two Looks", "A fever and a rash at once: four pairs fit, and two scans separate them.",
      "coil ember emberrash mothrash", {"liners": 1, "roll": 1, "salve": 1, "wrap": 1},
      [P("nell", "ember mothrash", "Hot and papery. I counted the patches. Then I counted the degrees. Then I sat on the floor.")],
      tests="dye pulse", maxc=2, robots=1),
    S("7-4", "A Note on a Pair", "Two conditions and a chart note: the cure that works for both may be the one the chart forbids.",
      "vent dust coldh frost", {"cells": 1, "drip": 1, "loz": 1, "roll": 1},
      [P("pell", "dust frost", "A cough, and cold that goes inwards. Nothing heavy, I have a note on my hand. It is right there.", traits="heavy")],
      tests="dye lamp", maxc=2, robots=1),
    S("7-5", "A Cold Pair", "A pair with spore flecks in it: the cold room first, then the sorting.",
      "spore soot hollow", {"gel": 1, "roll": 1, "tonic": 1, "wrap": 1},
      [P("yusra", "spore hollow", "A cough with flecks, and an ache like an empty room. I have been sitting in the booth, very still, for three days.")],
      tests="dye", maxc=2, beds=1, robots=1),
    S("7-6", "Shake and Pair", "A shake and something else, together. Steady first, then sort, then treat.",
      "saltt loose vent rasp", {"gel": 1, "roll": 1, "vials": 2, "wrap": 1},
      [P("imre", "saltt vent", "I shake and I cough and I am sure I am being dramatic. Tell me I am being dramatic.")],
      tests="breath dye", maxc=2, robots=1),
    S("7-7", "Everything Twice", "Three patients, each possibly carrying two things. The sheet has not changed; the work has.",
      "coil brass vent dust hum drift", {"cells": 3, "drip": 2, "gel": 1, "loz": 2, "roll": 1, "vials": 3, "wrap": 2},
      [P("halloran", "hum drift", "Dizzy, drowsy, and the floor keeps changing sides. I would like one cause, please. I do not mind which."),
       P("teo", "coil dust", "Hot, coughing, and still cooking. I have a habit of making soup out of bad ideas."),
       P("kit", "vent brass", "A cough and a fever. I told the drones to look after the screws. They are very good at that.")],
      tests="lamp dye breath", maxc=2, robots=1),
]
