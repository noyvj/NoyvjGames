"""Stranded -- story data, day 12: the nine endings. Every one is warm or bittersweet; nobody is lost."""

from kit import S

SCENES = [
    S("e_lantern", 12, "Lantern", [
        "Sparrow is lit. For a few minutes it is the brightest thing in half a sky.",
        "Marigold turned toward it, slow as a cat, and came to find the light.",
        "?bit|Bit rode out in the crate on my lap, lamp low, cracked stars all over the lid.",
        "?!bit|I looked back at the relay house from the ramp. One window, one green light. Not dark any more.",
        "Harbour, I didn't think a dark thing could be talked back to. You talked.",
        "(Harbour's log: the relay is still lit. The next lonely crew will find a plaque, a paper boat, and a very good name on the wall.)",
    ], end="lantern"),
    S("e_keeper", 12, "Quiet Keeper", [
        "Marigold's here, and so is a plan. A season, Harbour. One season. I keep the light and the dish and the names.",
        "They'll bring me a better chair. I said no to the chair. Then I asked for the chair.",
        "?bit|Bit stays too. Somebody has to hold the lamp steady while I'm bad at being alone.",
        "I'll write. I'll be rude about the food. Leave the line open.",
        "(Harbour's log: she is happy. The line is open. We talk about nothing, and it is wonderful.)",
    ], end="keeper"),
    S("e_pavel", 12, "Pavel at the Door", [
        "There's a knock on the airlock. A real one. Knuckles.",
        "It's Pavel. Of course it's Pavel. He's standing there with a helmet under one arm looking like a man who has rehearsed a speech and is about to ignore it.",
        "He said 'You are an enormous idiot.' I said 'I know.' Then we didn't say anything for a long time.",
        "?pavel|I'd opened his message, so I already knew. It still hit like a door.",
        "Harbour, thank you for the line. I'm going home with my brother. He's insufferable and he's right.",
        "(Harbour's log: two people on a ship, arguing quietly about who gets the window seat.)",
    ], end="pavel"),
    S("e_straight", 12, "Straight Up", [
        "Kestrel lifted off the dust like it had never had a bad day.",
        "Orrin fell away, grey and small, with the ring laid across the dark like a lid.",
        "I met Marigold in orbit. They opened their hatch and I came in with a bag, a half-eaten chocolate bar and a grin I couldn't put away.",
        "?confess|I told them the truth about the amber light before they could ask. It was easier than I thought.",
        "Straight up. First try. Harbour, I'm never going to shut up about it.",
        "(Harbour's log: she is home, and unbearable, and fine.)",
    ], end="straight"),
    S("e_half", 12, "Half a Lander", [
        "She flew. Not far, not neatly, and Kestrel hissed a good part of the way.",
        "Low orbit. A thin voice from Marigold, flying slow and kind to meet me. I climbed across with my teeth together.",
        "Kestrel stays behind, patched and sulking. I patted her on the way out.",
        "?bit|Bit stayed in the hut and watched me go with its lamp down low.",
        "That was not good enough, Harbour. It was merely enough.",
        "(Harbour's log: she is safe. She says she will go back for Kestrel. I think she will.)",
    ], end="half"),
    S("e_bit", 12, "Bit Comes Home", [
        "Bit came with me. Strapped in with the good tape, lamp low, trying very hard to look like luggage.",
        "On the ship it rolled to the window and tipped its lamp toward the grey moon, once, like a bow.",
        "They have a spare shelf for it on Marigold. A badge, even. 'CREW (SMALL)'.",
        "Harbour, I didn't think a robot could look at a moon and mean it.",
        "(Harbour's log: a small amber light, travelling home, pointed at nothing in particular and happy about it.)",
    ], end="bit"),
    S("e_marigold", 12, "Marigold Arrives", [
        "Marigold's here. A proper hatch, a proper welcome, a proper blanket that smells of other people's laundry.",
        "Orderly. Just like I was told. It was boring for about one day and wonderful for the rest.",
        "I'm going home. I will be tired for a month. I will tell everyone the dish was a very good dish.",
        "?pavel_closed|There's a message on my tablet I haven't opened. I'll open it on the way home. With company.",
        "(Harbour's log: she waved at the camera. Not at me. At everyone. It still counts.)",
    ], end="marigold"),
    S("e_quiet", 12, "Quiet Line", [
        "...Marigold's here. I'm going aboard.",
        "I don't think I can say much. I'm sorry, Harbour. It isn't you. It's just a lot of quiet to put down.",
        "(The line stays open. There is nothing new on it. You keep it open anyway.)",
        "(Some weeks later, one line comes in, without a greeting.)",
        "'The dish was a good dish. Thank you for staying on it.'",
        "(Harbour's log: it is the best message I have ever received. I read it twice and I did not reply, because she did not ask me to.)",
    ], end="quiet"),
    S("e_honest", 12, "A Straight Line", [
        "I told them. All of it. The amber light, the 'nominal', the day I wanted so badly to save.",
        "The board was quiet, then odd, then kind. They're changing the rule so a pilot can say 'I'm not sure' and have the launch held without anyone calling it a failure.",
        "?pavel|Pavel read the report before I did. He said it was the best thing I'd ever written. He's still insufferable.",
        "?!pavel|I'll write to my brother. I think I might actually open that message now.",
        "I was a stubborn idiot. I'm a slightly less stubborn idiot. Thank you for the straight line, Harbour.",
        "(Harbour's log: a small rule was changed because one person told the truth to another.)",
    ], end="honest"),
]
