"""Heist Committee -- the committee's own story: a debrief of crew banter after every job, and "minutes" that
open as the career goes on. Plain, warm and silly; nobody in it is harmed and nobody is perfect. All of it is
derived from the career and the heist log, never stored, and hidden by the shared Story switch (the rules never
depend on it)."""

import engine

TRAIT_LINES = {
    "chatty": "I was only making conversation.",
    "nervous": "Everyone was looking at me. Everyone.",
    "allergic": "It was the flowers. Or the dust. Or both. Atchoo.",
    "cat_person": "Did anyone else see the cat? It looked at me.",
    "clumsy": "It was already crooked when I got there.",
    "sentimental": "I took one mug. One. It had a nice handle.",
    "superstitious": "I said it was an unlucky beat. Nobody listens to me.",
    "lucky": "I do not know how it worked. It worked.",
    "calm": "I had it. I really did.",
    "show_off": "Did you see that distraction? Did you see it?",
    "hoarder": "Anyone want a pen? I have forty pens.",
    "claustrophobic": "That room had no corners. Which is worse, somehow.",
    "motion_sick": "Please never mention the van again.",
    "stage_fright": "There were so many people. All of them looking.",
    "night_owl": "It was the best part of the day. Night.",
    "light_sleeper": "I heard it coming from three rooms away.",
    "penny_pincher": "Did anyone save the receipts?",
    "team_player": "We did that together. All of us. Together.",
    "overconfident": "I told you it would be easy. For me it was.",
    "perfectionist": "It could have been neater.",
}

CLASS_LINES = {
    "clean": ["Nobody saw a thing. I would like that on a plaque.", "That was almost too smooth. Suspicious, even."],
    "loud": ["We got it, and we also got a lot of attention.", "The alarm had a lovely tune, I will give it that."],
    "stranded": ["Who was meant to be driving?", "It is a lovely evening for a long walk."],
    "bust": ["Next time we bring a bigger plan.", "That went exactly the way the plan did not say it would."],
}

MINUTES = (
    (0, "Minutes of the first meeting",
     "The Committee met on a wet Thursday, as it has for forty years, to discuss what to borrow and how. The Chair, Dame "
     "Philippa Quorum, opened the meeting by reading the minutes of the last one, which were identical. The Secretary, Mr Agenda "
     "Fitch, was asked to find some new members. He found five. Nobody had read their references."),
    (1, "Minutes of the second meeting",
     "A successful first job was noted. The Chair said this was unexpected and asked for it to be put in writing in case it "
     "never happened again. Mr Fitch pointed out that biscuits were now in short supply and proposed a sub-committee."),
    (3, "Minutes of the fourth meeting",
     "A motion was put that the Committee has been, until now, a very polite book club. The motion was not carried, but it "
     "was agreed that the book club had better cover stories. The Chair reminded everyone that she has never once been seen near a van."),
    (5, "Minutes of the sixth meeting",
     "Mr Fitch revealed that the Committee's founding charter says it must 'borrow only what would otherwise be forgotten'. "
     "After a long silence, the Chair said the Gloop Idol had been forgotten for years, "
     "and the cheese had certainly been forgotten by the cheese."),
    (8, "Minutes of the ninth meeting",
     "It emerged that three crew members had each made a secret tea cosy for the Chair. The Chair accepted all three with great "
     "dignity. A rumour that the Committee's real purpose is to find friends for its members was strongly denied, and then confirmed."),
    (12, "Minutes of the thirteenth meeting",
     "The Committee's reputation has spread. A man in a hat sent a letter asking to join. Mr Fitch checked his references. They were "
     "all the Chair. The letter has been framed."),
    (16, "Minutes of the final meeting (for now)",
     "The Chair announced that after forty years the Committee had finally decided something. Mr Fitch asked what. The Chair said: "
     "'Same time next Thursday.' The meeting was adjourned for cake."),
)


def minutes(meta):
    """Unlocked minutes (by jobs done) and the next unlock, if any."""
    done = meta.get("jobs_done", 0)
    opened = [{"title": t, "text": x} for need, t, x in MINUTES if done >= need]
    nxt = next((need for need, _t, _x in MINUTES if done < need), None)
    return {"entries": opened, "next_at": nxt, "jobs_done": done}


def debrief(content, crew_ids, result, cls, seed):
    """Three or four lines of crew banter: a class line, then each trait that fired, then a voice line."""
    lines = []
    names = {c: content.crew[c]["short"] for c in crew_ids}
    pick = engine.roll
    pool = CLASS_LINES.get(cls, [])
    speaker = crew_ids[int(pick(seed, "db", "s1") * len(crew_ids)) % len(crew_ids)]
    if pool:
        lines.append({"who": names[speaker], "text": pool[int(pick(seed, "db", "c") * len(pool)) % len(pool)]})
    seen = []
    for ev in result["events"]:
        if ev["type"] == "trait" and ev["trait"] in TRAIT_LINES and ev["crew"] in names and (ev["crew"], ev["trait"]) not in seen:
            seen.append((ev["crew"], ev["trait"]))
    for crew_id, trait in seen[:2]:
        lines.append({"who": names[crew_id], "text": TRAIT_LINES[trait]})
    voice = crew_ids[int(pick(seed, "db", "v") * len(crew_ids)) % len(crew_ids)]
    lines.append({"who": names[voice], "text": content.crew[voice]["voice"]})
    return lines
