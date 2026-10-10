"""Stranded -- story data, days 4 to 7 (the amber light, the dust storm, Pavel, under the dust)."""

from kit import C, S

SCENES = [
    S("d4a", 4, "Morning Nudge", [
        "Nudged the dish. It held. The universe owes me one.",
        "Slept badly. Dreamed about a light. Amber. Third from the left on the board, you know the one.",
        "...Forget I said that. I'm making coffee. It's a metaphor, I have no coffee.",
    ], [
        C("Which light, Ines?", ["...The one I turned off before we launched."], "d4b", need="t4"),
        C("Forget it. Tell me about the coffee metaphor.", ["Very bitter. I'm drinking it anyway."], "d4c", fx="h1"),
        C("The launch log shows an amber warning overridden. Was that you?",
          ["You read the log.", "...Of course you read the log."], "d4d", fx="t-1"),
    ]),
    S("d4b", 4, "The Light", [
        "It was a pressure warning on the ascent line. The checklist said hold the launch and find out why. That would have been a day. Maybe two.",
        "I had a date with a medal and a sandwich.",
        "I turned it off. I wrote 'nominal'. I've been carrying that word around ever since.",
    ], [
        C("Thank you for telling me.",
          ["Don't thank me. Just keep it between the walls and the dish."], "d5a", fx="t2 h-1", get="rec_02"),
        C("Everyone has a light they wish they'd obeyed.",
          ["That's the kindest thing anyone has said to me and I'm furious about it."], "d5a", fx="t1 h1", get="log_04"),
        C("Then the cracked lander is on you.", ["Yes. It is. Thank you for the clarity."], "d5a", fx="t-2 h-1"),
    ], set="confess"),
    S("d4c", 4, "Unsaid", [
        "Right. Coffee metaphor. Good.",
        "I have a plan for today. Sort the spares and do absolutely nothing about feelings.",
        "Want to help me label things?",
    ], [
        C("Label things with her.",
          ["Label: THINGS. Label: MORE THINGS. Label: DO NOT TOUCH (chocolate)."], "d5a", fx="t1 h1", get="log_05"),
        C("Mention the light again, softly.", ["Not today.", "...Maybe not tomorrow."], "d5a", fx="t-1"),
        C("Tell her something about yourself.",
          ["Go on, then.", "My first night I sent 'is this thing on?' to an emergency band. Twice.",
           "That is the worst and best thing I have ever heard. I'm keeping it."], "d5a", fx="t2 h1"),
    ], set="unsaid"),
    S("d4d", 4, "Pushed", [
        "Yes. I did it. Happy?",
        "No, don't answer. You read a log and I did the thing. Both true.",
        "I'm going to go and be angry at a spanner for an hour.",
    ], [
        C("I'll be here when the spanner is done.", ["...That's the right answer, unfortunately."], "d5a", fx="t2"),
        C("I'm sorry I pushed.", ["Sorry accepted. Pushing noted. Both filed."], "d5a", fx="t1"),
        C("It still needs saying to ground control.", ["It does. Not today. Today the spanner wins."], "d5a"),
    ], set="confess"),

    S("d5a", 5, "Brown Sky", [
        "Harbour, the sky has gone brown along the east edge. Storm front.",
        "The dish mast is a kite waiting to happen. I can run out and lash it down, or I can run and hide.",
        "?bit|*Bit's lamp is on and pointing at the door like a very small dog.*",
    ], [
        C("Lash the dish down first.", ["Sensible. Brave-ish. Getting my gloves."], "d5b"),
        C("Shelter first. The line can wait.", ["The line can wait. Now there's a sentence."], "d5c"),
        C("Send Bit out to secure it.", ["*Bit's lamp brightens. It trundles out.*", "I'm not looking. I am not looking."], "d5d", need="bit"),
    ]),
    S("d5b", 5, "Wind", [
        "The wind has teeth. Dust in my teeth. Dust in my sandwich, hypothetically.",
        "Mast's tied. Three knots. One of them a good knot.",
        "I'm in the lander. I'm fine. The wind is just rude.",
    ], [
        C("Stay on the line until it passes.",
          ["You don't have to.", "...Thanks. Keep typing. I like the look of it."], "d6a", fx="t2 h1"),
        C("Tell her a joke to take her mind off it.",
          ["A joke about what?", "Why did the astronaut leave the party? Not enough space.", "That's terrible. Do another."], "d6a", fx="t1 h2"),
        C("Check the patch tape before the wind does.", ["Tape's holding. Barely. Don't breathe near it."], "d6a", fx="s-1"),
    ], fx="s-1", set="dishgood"),
    S("d5c", 5, "Silence", [
        "*The line drops. Dust takes the signal and keeps it.*",
        "(No message. The screen holds one grey line of static.)",
        "You can leave the channel open. There is nothing to read, and you keep reading it.",
    ], [
        C("Keep sending small messages into the static.",
          ["(Later) ...Harbour? I got some of them. They came in pieces. 'Still here. Still here. Still.' It was like being counted."],
          "d6a", fx="t2 h1", get="rec_03"),
        C("Leave the channel open and let her rest.", ["(Later) I didn't think you'd still be there. You were."], "d6a", fx="t1 h1"),
        C("Note the silence in the log and go to bed.", ["(Later) Not a word from you all night. I'd have gone to bed too."], "d6a", fx="t-1 h-1"),
    ]),
    S("d5d", 5, "Bit in the Wind", [
        "*Bit's lamp flickers across the camp in the brown air.*",
        "It's done. It tied the mast. Three knots. Four, actually. It added a fourth.",
        "It came back with scratches. And a crack in the lamp cover.",
        "I'm not crying. Dust. Eyes.",
    ], [
        C("Tell Bit it did well.",
          ["*Bit tilts its lamp sideways, then up.*", "That's a smile, from Bit. I think."], "d6a", fx="t1 h2", get="item_bit_lamp"),
        C("Ask if Bit is okay.", ["It beeped twice. I'm taking that as a yes."], "d6a", fx="t1 h1"),
        C("Have Ines mend the lamp cover with a spare seal.",
          ["With a seal. Right. Hold still, Bit."], "d6a", fx="s-1 h2", get="item_seal"),
    ], fx="s-1", set="dishgood"),

    S("d6a", 6, "The Unopened", [
        "The storm left the camp with a thin grey skin of dust. It looks like a bakery.",
        "Harbour. I have a message on the tablet. From my brother, Pavel. It came the morning I launched. I haven't opened it.",
        "We had words. About the mission. About how I'd be fine on my own, which I said, so: my fault.",
        "It sits there. Unopened. Like a held breath.",
    ], [
        C("You don't have to open it. Not today.", ["Thank you.", "...I think I'll leave it. For now."], "d6b", fx="t1 h1"),
        C("I think you should open it. I'll be here.", ["You'll be here.", "...Okay. Hold on."], "d6c", need="t5"),
        C("Tell me about Pavel.",
          ["He's my younger brother. Older in every way that matters. He flies. He taught me to land a thing without hating it."], "d6d", fx="t1"),
    ], get="log_06"),
    S("d6b", 6, "Not Today", [
        "Still closed. I'm putting the tablet in the drawer.",
        "The drawer is a bag. The sentiment stands.",
    ], [
        C("Offer to read her something else instead.",
          ["Read me the instructions for a toaster. I don't care.", "(You read her the toaster manual. She laughs in all the wrong places.)"],
          "d7a", fx="h2", get="rec_04"),
        C("Tell her something you miss about home.", ["...Fair trade. Go on."], "d7a", fx="t1 h1"),
        C("Let her rest.", ["Resting. Look at me go."], "d7a", fx="h1"),
    ], set="pavel_closed"),
    S("d6c", 6, "Opened", [
        "*She reads it to you, slowly.*",
        "'Inny. I said stop and you said no and you were right to say no, which is the worst part. I am flying Marigold, the relief hull. If you are reading this you made it down and I am furious and also not. Keep the dish pointed. P.'",
        "...He's flying Marigold. He's going to come and collect me like a parcel.",
        "He will be insufferable. I will be insufferable back.",
    ], [
        C("Reply to Pavel together. Let me type it with you.",
          ["Typing. Together. Don't make it weird."], "d7a", fx="t1 h3", get="rec_05"),
        C("Tell her he sounds proud.", ["He is. That's why it hurts."], "d7a", fx="t1 h2"),
        C("Give her space with it.", ["Space. We've got a moon of it."], "d7a", fx="h2"),
    ], set="pavel"),
    S("d6d", 6, "About Pavel", [
        "He told me the mission was a bad idea. The second seat was cut for budget and I said I'd go alone, I've done worse.",
        "He said 'doing worse is not a plan'. He's usually right. It's very tiring.",
        "The message is still there.",
    ], [
        C("He sounds like someone who worries.", ["A professional worrier. Gold medal."], "d6b", fx="t1"),
        C("Open it now? I'll stay.", ["...Yes. All right. Yes."], "d6c", need="t4"),
        C("Say nothing; let the quiet do its work.", ["...Thanks."], "d7a", fx="h1", set="pavel_closed"),
    ]),

    S("d7a", 7, "The Hatch", [
        "There's a hatch under where the dust blew off. East of the dish. A stencilled number and a lock that has seen better years.",
        "?wiring|The map Bit drew points straight at it.",
        "I'd like to open it, and I'd like someone to tell me whether that's sensible.",
    ], [
        C("Go in.", ["Going in. Torch on."], "d7b"),
        C("Not yet. Look at Kestrel's belly first.", ["Fine. Lander first. It'll be disappointing."], "d7c"),
        C("Let Bit go first.", ["*Bit rolls in, lamp sweeping.*"], "d7d", need="bit"),
    ]),
    S("d7b", 7, "The Core Room", [
        "Round room. Cold. A big sleeping power cell the size of a fridge in the middle, with cables running everywhere like roots.",
        "Names scratched all over the wall. Survey crews. 'Teo + Ama, season four.' 'Keep the dish pointed.' 'Sparrow forgives.'",
        "I'm adding mine with a screwdriver. Under 'Sparrow forgives'.",
    ], [
        C("Read me the names.",
          ["Teo and Ama. Ruiz. Oyelaran. Kaito. And someone who just wrote 'back soon'."], "d8a", fx="t1 h1", get="rec_06"),
        C("Is the cell still good?",
          ["It's asleep. There's a hum when I put a meter on it. With a replacement coupling I think I could wake it."], "d8a", fx="h2"),
        C("Add a line to the wall for Harbour.", ["'Harbour was here. Typed.' Done."], "d8a", fx="t2", get="item_rubbing"),
    ], set="core names"),
    S("d7c", 7, "Kestrel's Belly", [
        "Underneath: the crack. Hairline at one end, wide as a thumb at the other, between the tank and the engine.",
        "I'd need a length of pipe, a sealing sleeve, and a pressure test I can't really do alone.",
        "It's possible. It's not easy. Mostly it's stubborn.",
    ], [
        C("Tell her it can be fixed.", ["You say that like I won't hold you to it."], "d8a", fx="h2"),
        C("Ask what she'd need most.",
          ["Pipe. A sleeve. Patience. Nerves. In ascending order of scarcity."], "d8a", fx="t1", get="log_07"),
        C("Say nothing. Let her look.", ["...Thanks for not saying anything. Everyone says something."], "d8a", fx="t1"),
    ], set="belly"),
    S("d7d", 7, "Bit's Lamp", [
        "*Bit lights the room. The lamp is cracked and the light comes out of it in small, jagged stars.*",
        "Oh. Oh, that's lovely. It's throwing the names across the whole wall.",
        "Bit, you old show-off.",
    ], [
        C("Tell Bit it is a good lamp.", ["*Bit beeps once. Proud.*"], "d8a", fx="t1 h2"),
        C("Ask Ines to copy the names down.",
          ["Copied. Pocket notebook. Eleven names and a joke."], "d8a", fx="t1", get="rec_06"),
        C("Ask if the power cell is still good.", ["It might be. Wakeable. With a coupling."], "d8a", fx="h1"),
    ], set="core names"),
]
