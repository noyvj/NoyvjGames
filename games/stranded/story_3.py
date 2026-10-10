"""Stranded -- story data, day 8 (three roads) and the three arcs of days 9 to 11: relay (r), lander (l), wait (w)."""

from kit import C, S

SCENES = [
    S("d8a", 8, "Three Roads", [
        "Right. Options. I've counted them on my fingers and run out of fingers on one hand, so there are three.",
        "One: relight Sparrow. Wake the core, kick the relay on, and Marigold hears us from half a sky away.",
        "Two: fix Kestrel and fly up to meet Marigold myself.",
        "Three: sit tight. Eat slowly. Be rescued in an orderly manner.",
        "Your call, Harbour. And if you say 'what do you want, Ines' I will throw a spanner at the moon.",
    ], [
        C("Relight the relay.", ["A light on a dark thing. It's the kind of stupid I like."], "r9a", fx="h1", need="core&h4"),
        C("Fix Kestrel and fly.", ["Right. Kestrel. Her bad back and my bad nerves."], "l9a", need="s3"),
        C("Sit tight and be rescued in an orderly manner.", ["Orderly. I can do orderly. For about a day."], "w9a", fx="s1"),
        C("What do you want, Ines?",
          ["...You said the forbidden thing.", "Fine. The spanner stays on the bench. Give me a moment to think about what I actually want."],
          ["core&h6>r9a", "s5>l9a", "w9a"], fx="t1", need="t6"),
    ]),

    # ---- the relay arc ---------------------------------------------------------------------------------------------------
    S("r9a", 9, "Cold Cell", [
        "The core cell wants a coupling and a spark. I have neither. I have a hammer and good intentions.",
        "Three places I could get a spark: Kestrel's reserve cell, a survey cell the earlier crews left in the wall, or...",
        "?bit|*Bit rolls a little closer. Nobody has asked it anything.*",
    ], [
        C("Use Kestrel's reserve cell.",
          ["That's the lander's own heart. Taking it means Kestrel will never fly.", "...All right. Moon first, lander second."], "r9b", fx="s-1", set="nolander"),
        C("Ask Bit.", ["*Bit's lamp goes very still.*"], "r9c", need="bit"),
        C("Open the survey cell in the wall.",
          ["Eleven names and a cell. Labelled 'for whoever's next'. That's us."], "r10a", fx="t1 h2", need="names", set="gift", get="item_cell"),
    ]),
    S("r9b", 9, "Stripped", [
        "Pulled the cell. Kestrel looks like a lamb with its wool off, and I'm trying not to look at it.",
        "The relay house has power. I have a lander that will never leave the ground.",
    ], [
        C("You did what the moon needed.", ["Don't be generous. I'll start enjoying it."], "r10a", fx="t1"),
        C("We'll find another way up.", ["The only other way up is through a relay. So we light it."], "r10a", fx="h2"),
        C("That was brave.", ["It was a lander. Don't write 'brave' about hardware."], "r10a", fx="h1"),
    ]),
    S("r9c", 9, "Bit Offers", [
        "*Bit rolls up to the cell. It opens its own back panel. A small, full battery sits inside.*",
        "It's offering. I didn't ask twice. It just offered.",
        "I can't take that. I can't.",
    ], [
        C("Let Bit give it. It chose.",
          ["...Okay. Okay. I'll put it back after. I promise, Bit."], "r10a", fx="t1 h-1", set="bitgave"),
        C("Ask Ines to try the wall cell instead.",
          ["There's a cell in the wall. Labelled for whoever's next. Bit, close your panel. Good robot."], "r10a", fx="t1 h2", need="names", set="gift", get="item_cell"),
    ]),
    S("r10a", 10, "Wiring", [
        "A day of wiring. This is the part of a heroic story that gets cut from the film: eight hours of swearing quietly at a connector.",
        "It's coming together. The coupling fits. Mostly.",
    ], [
        C("Slow and careful: test every join.",
          ["Test every join. Dull. Correct. Cutting my own corners in half."], "r10b", fx="s-1 t1", set="careful"),
        C("Try it live and see if it wakes.",
          ["Risky and fun. My two favourite things that are not sandwiches."], "r10c", fx="h2", set="live"),
    ], get="log_10"),
    S("r10b", 10, "A Hum", [
        "It hums. Harbour. The core is humming. A low slow note, like a cat deciding to like me.",
        "Every join passed. The board has a light. One light. Green.",
    ], [
        C("Say it out loud: 'Sparrow is awake'.", ["Sparrow is awake. I'm going to cry on the back of my glove."], "r11a", fx="t1 h3"),
        C("Ask her to rest before the switch.", ["Rest. Fine. Tomorrow I'll be unbearably tidy."], "r11a", fx="t1 h1"),
        C("Ask her to take a picture for the wall.", ["Picture taken. The wall will get a very out-of-focus Sparrow."], "r11a", fx="h1", get="item_photo"),
    ]),
    S("r10c", 10, "Fizz", [
        "Fizz. Pop. A smell like burnt toast. The coupling smoked and the whole board went dark for a moment.",
        "...But it's back. Dim, but back. One light, amber, which I'm choosing not to read into.",
    ], [
        C("Laugh with her about it.", ["It did look like a sneeze."], "r11a", fx="t1 h2"),
        C("Ask her to check every join now.", ["Now you're sensible."], "r11a", fx="t1 s-1", set="careful"),
        C("Ask if she's okay.", ["Singed eyebrow. Fine otherwise. Still pretty."], "r11a", fx="h1"),
    ]),
    S("r11a", 11, "The Switch", [
        "It's all wired. One switch. If it works, Sparrow sends a signal to every ship in half a sky and I'm a lighthouse for a little while.",
        "If it doesn't, I swear at it some more. Either way we know.",
    ], [
        C("Light it, and tell Marigold.", ["Telling. Lighting. Here we go."], ["pavel>e_pavel", "e_lantern"], fx="h2"),
        C("Ask what she wants once it's on.",
          ["...I want to stay. A little. Keep it lit for whoever's next.", "Not forever. A season. Marigold can take me when there's a keeper."],
          "e_keeper", need="names&h6"),
        C("Let her throw the switch in her own time, quietly.",
          ["Quietly. Good. A lantern doesn't say anything. It just is."], "e_lantern", fx="t1"),
        C("Ask what Bit needs before the switch is thrown.",
          ["...Bit gave nearly everything it had to the core. What's left is a trickle.",
           "It won't have enough to ride out with me. I'd have to leave it to rest in the window."],
          "e_asleep", fx="t1", need="bitgave"),
    ]),

    # ---- the lander arc -------------------------------------------------------------------------------------------------
    S("l9a", 9, "Parts", [
        "Kestrel. Parts. A pipe the width of my thumb, a sleeve to clamp it and the right kind of patience.",
        "Pipe: I can cut a length from the relay house water line, or take the dish mast tube, which is the line to you.",
        "?bit|*Bit points its lamp at a locker in the corner. It has been into the locker.*",
    ], [
        C("Cut a length from the relay house water line.", ["The water line. We have the still. Fine."], "l9b", fx="s-1"),
        C("Use the dish mast tube.", ["That's your line. It'll go quiet. All right."], "l9c"),
        C("Ask Bit to look for scraps.",
          ["*Bit rolls to the locker and comes back with a pipe the right width and a neat coil of tape.*"], "l10a", fx="t1 h2", need="bit", set="scrap"),
    ]),
    S("l9b", 9, "Water Line", [
        "Cut. A clean cut. We lose a little pressure in the still, which the moon can spare.",
        "I can trim it longer or shorter. I'd like an opinion.",
    ], [
        C("Measure twice.", ["Twice. Right. I've got a ruler and no excuses."], "l10a", fx="t1"),
        C("Cut it long and trim later.", ["Long. Trim later. That's how I do everything."], "l10a", fx="s-1 h1"),
        C("Ask for a rest first.", ["A rest. Fine. Nobody has asked me for a rest in years."], "l10a", fx="h2"),
    ]),
    S("l9c", 9, "The Quiet Day", [
        "*The dish mast is down. The channel drops to a trickle: one line, now and then.*",
        "(She sends once, and then not again for a long while. The screen waits, and you wait with it.)",
        "Pipe's out. It fits. I think. Mind the mast.",
    ], [
        C("Trust her. Leave a short message for when the line returns.",
          ["(Later) Message got me. Thanks for not panicking."], "l10a", fx="t2"),
        C("Keep messaging so she hears you.", ["(Later) It's like having a pigeon on the roof."], "l10a", fx="t1 h1"),
        C("Ask her to rebuild the mast as soon as she can.", ["Mast first. Pipe second. Priorities."], "l10a", fx="s-1"),
    ]),
    S("l10a", 10, "The Weld", [
        "Pipe in. Sleeve on. It's ugly. It's mine.",
        "Now the test, which I can't properly do without a pressure rig, so: I improvise.",
    ], [
        C("Test it twice, slowly.", ["Twice. Slowly. You've met me."], "l10b", fx="s-1 t1"),
        C("Good enough. Fly.", ["Good enough. The two most dangerous words in the language."], "l10c", fx="h2"),
    ], get="log_11"),
    S("l10b", 10, "The Test", [
        "The seal holds. Held for a whole hour. Held for another. Nothing hissed.",
        "It's not pretty. It's sound.",
    ], [
        C("Tell her she is good at this.", ["...Don't. I'll start believing it."], "l11a", fx="t2 h2"),
        C("Ask her to log the repair honestly.", ["I'll write the real log. All of it."], "l11a", fx="t2", need="confess"),
        C("Ask what Kestrel's name means.",
          ["A small bird that can hover in one place against the wind. Mine can't. But it is trying."], "l11a", fx="h2"),
    ], set="tested"),
    S("l10c", 10, "Hasty", [
        "*A thin hiss. Very thin.*",
        "There. That's the sound of 'good enough'.",
        "It might hold. It might hold all the way. I'd fly it. I'd also write myself a strongly worded letter.",
    ], [
        C("Ask her to test it properly before flying.", ["...Fine. Fine. Tomorrow."], "l10b", fx="t1"),
        C("Trust her instincts.", ["Instincts. The thing I keep being told to distrust."], "l11a", fx="h1"),
        C("Tell her to take a breath first.", ["Breathing. In. Out. Still hissing."], "l11a"),
    ]),
    S("l11a", 11, "Ignition", [
        "Kestrel's warm. Her bad back is mended, or at least held. I could fly this afternoon.",
        "Marigold meets me in orbit. Someone good is flying her.",
        "?bit|*Bit is parked by the ramp, lamp low, pretending to be furniture.*",
    ], [
        C("Take Bit with you.", ["Bit comes. Bit comes! Strapped in with the good tape."], ["tested>e_bit", "e_half"], fx="h2", need="bit"),
        C("Ask her to record the full truth about the amber light for the debrief.",
          ["Recording. All of it. Like pulling teeth with a spoon."], ["tested>e_honest", "e_half"], fx="t1", need="confess&t5"),
        C("Fly.", ["Flying. Say a nice word to the bad back."], ["tested>e_straight", "e_half"], fx="h1"),
    ]),

    # ---- the wait arc -------------------------------------------------------------------------------------------------------
    S("w9a", 9, "Quiet Camp", [
        "So. We sit. Eat slowly. The relief ship is coming and will arrive when it arrives.",
        "I'm told this is what 'orderly' feels like.",
        "Want to do something with the spare days? Not time. The spare days. Whatever.",
    ], [
        C("Tidy the camp.", ["Tidying. A heroic act. Watch me sweep."], "w9b", fx="h1"),
        C("Teach her a word game by text.", ["A word game. Fine. Prepare to lose."], "w9c", fx="h1"),
        C("Let her sleep; just keep the line open.", ["Sleep. Yes. I'll keep you in my... other ear."], "w10a", fx="h2 t1"),
        C("It's out of your hands now. Try not to fuss.", ["Out of my hands. That's the part I hate."], "w10a", fx="h-2"),
    ]),
    S("w9b", 9, "Tidy", [
        "Swept the hut. Polished the plaque. Arranged the tools by size, then by mood.",
        "Found a tin under the bench with a note: 'For whoever's lonely.' Inside: a pack of sugar and a tiny paper boat.",
        "Sugar. Paper boat. I'm putting the boat on the dish. Sparrow gets a mascot.",
    ], [
        C("A paper boat for the dish. Perfect.", ["Perfect. Mounted. It's a very serious boat."], "w10a", fx="t1 h2", get="item_boat"),
        C("Save the sugar for emergency chocolate.", ["Emergency chocolate. A good reserve."], "w10a", fx="s1 h1"),
        C("Read the note aloud.", ["'For whoever's lonely. It does get better. Nudge the dish.' Someone was kind here."], "w10a", fx="t1", get="log_08"),
    ]),
    S("w9c", 9, "Word Game", [
        "Your word: LANTERN. Mine: HARBOUR. You win by two letters on purpose, don't think I didn't notice.",
        "Another round. I have a feeling about 'sparrow'.",
    ], [
        C("Let her win.", ["Don't let me win. I'll know. I always know."], "w10a", fx="h2"),
        C("Play to win.", ["There he is. Rematch tomorrow."], "w10a", fx="t1 h1", get="rec_07"),
        C("Choose words about home.", ["Kettle. Doorstep. Rain. ...Those are good words."], "w10a", fx="t1 h2"),
    ]),
    S("w10a", 10, "The Long Middle", [
        "Harbour, I am bored of being safe. I want to do something stubborn.",
        "?pavel|I'd like to write Pavel back, but I want to do something with my hands first.",
    ], [
        C("Let her walk to the ridge and see the ring.", ["The ridge. The ring. I'll bring a snack."], "w10b", fx="s-1 h3"),
        C("Ask her to write the debrief honestly.", ["The honest debrief. Like pulling teeth with a spoon."], "w10c", fx="t2", need="confess"),
        C("Ask her to record a message for whoever comes next.",
          ["For whoever's lonely. Right. Recording."], "w11a", fx="t1 h2", get="rec_08"),
        C("Say it is only a few more days, and keep it brief.", ["A few days. Said like it's a few minutes."], "w11a", fx="h-1"),
    ]),
    S("w10b", 10, "The Ridge", [
        "The ring is the thing. All of it, stretched across the dark like glass. I forgot I was angry.",
        "I'm sitting on the ridge with my knees up. I wish you could see it.",
    ], [
        C("Ask her to describe it for you.",
          ["Pale. Sharp. Slow. Like the edge of a very large plate."], "w11a", fx="t2 h2"),
        C("Ask her to take a picture for later.", ["Visor fogging. Taking it anyway."], "w11a", fx="h2", get="item_ridge"),
        C("Tell her to come home soon.", ["Soon. Soon-ish. I'll take the long way down."], "w11a", fx="t1 h1"),
    ]),
    S("w10c", 10, "Debrief", [
        "Dear Review Board. On the morning of launch I turned off an amber pressure warning and wrote 'nominal'. I did it to save a day. It cost a lander and nine days of a good man's worry.",
        "I can't send it from here. But it's written.",
    ], [
        C("It was brave to write it.", ["Brave. Everyone uses that word. Fine. Brave."], "w11a", fx="t2 h2", get="log_09"),
        C("You don't have to send it.", ["Oh, I'm sending it."], "w11a", fx="t1"),
        C("Offer to carry the message to the board.", ["You'll carry it. Good. I'll carry the rest."], "w11a", fx="t2"),
    ]),
    S("w11a", 11, "Marigold's Light", [
        "There's a light in the sky that wasn't there. It's moving. It's coming.",
        "That's the relief ship. That's actually it. Harbour.",
    ], [
        C("Tell Marigold you've got her.", ["Telling. Here they come."], ["pavel>e_pavel", "e_marigold"], fx="h2"),
        C("Ask her to tell them about Bit.", ["Telling. Bit is not furniture. Bit is crew."], "e_bit", fx="t1", need="bit"),
        C("Ask her to say what's true when they land.", ["I will. All of it. In the right order."], "e_honest", fx="t1", need="confess"),
        C("Be quiet; let her be quiet.", ["...Thank you for not saying anything."], ["h<5>e_quiet", "e_marigold"], need=""),
    ]),
]
