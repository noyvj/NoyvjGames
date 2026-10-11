"""Rule Finder -- the About page: what the game is and what it will never do. It states no real-world facts: it is fiction and a
puzzle. The logic puzzles and psychology work that inspired it are listed on its Sources page (read as text only)."""

PLEDGE = (
    "There is no timer, no energy and no waiting: a case takes as long as you like and never changes while you think.",
    "Testing is free and unlimited. A wrong name costs nothing: it shows you one item your rule gets wrong, and you try again.",
    "Progress is only ever added. A named case stays named, a Codex page stays filled, and nothing expires or can be missed.",
    "No randomness anywhere: every case has one hidden rule, the same gate gives the same answer every time, and every case was checked by machine to be solvable from its starting examples and your own tests.",
    "Hints are free, only appear when you ask, and open one rung at a time. The answer is one tap away whenever you want it, and using it is never hidden or shamed.",
    "No audio, no ads inside the game, no purchases, and no leaderboards.",
)

FRAMING = ("Rule Finder is a small invented place: an old relay in a quiet signal room, a gate that lets some things through and stops "
           "the rest, and an operator who logs what he notices. Every case hides one rule. Nothing in it comes from a real "
           "machine or a real person, and it states no real-world facts.")

HOW = (
    "Each case shows a few starting examples, some Through and some Stopped. Build your own test items and send them: the gate answers at once, and testing is free.",
    "When you think you know the rule, build it in the Rule Builder: pick a property for each clause, tick Not to turn one around, and join clauses with and or or. Then press Name it.",
    "A rule is right when it agrees with the hidden one on every possible item, not only when the words match. If it is wrong you see one item it gets wrong, free of charge, and the hidden rule is never shown.",
    "The tests counter earns a medal against par, but the medal is a bonus: naming every case is the whole game. Every drawer and every case is open from the start, in any order.",
    "Each named case fills a page of the Rule Codex with the rule in words, the kind of property it was, and the shortest path: the fewest tests that would have proved it.",
)


def view():
    return {"framing": FRAMING, "notice": "Fiction. No real-world facts are used, so there are no sources to date.",
            "pledge_heading": "What this game will never do", "pledge": list(PLEDGE), "how_heading": "How it works", "how": list(HOW)}
