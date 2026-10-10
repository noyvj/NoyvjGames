"""Stranded -- the About page: what the game is, what it will never do, the fiction notice and two modest real facts with a
named source and the date they were read (read live on 2026-10-10). Nothing else here is real."""

DATE_READ = "2026-10-10"

NOTICE = ("Stranded is fiction. Orrin, Sparrow Relay, the ships Kestrel and Marigold, Ines, Bit, Pavel and Harbour are all invented, "
          "and nothing in it describes a real mission or a real person.")

FRAMING = ("Stranded is a branching story told as a text conversation. You are Harbour, the plain voice on a thin line to Ines, "
           "who is stuck on a small moon. Every choice gets an answer, you can rewind to any choice for free, and the branch map "
           "shows the paths you have not tried yet.")

PLEDGE = (
    "There is no timer and no waiting: replies arrive one at a time when you tap (or all at once if you choose that in Settings). Nothing happens while you are away.",
    "Nobody dies on screen. A poor choice costs trust, supplies or hope, and you can always rewind and choose again.",
    "Progress is only ever added. Rewinding never takes away an ending, a collectable or a path you have tried.",
    "No randomness anywhere: the same choices always lead to the same place.",
    "Hints are free, only appear when you ask, and the answer is one tap away.",
    "No audio, no purchases, no leaderboards.",
)

HOW = (
    "Read what Ines says, then choose what to send. She always answers, and the answer can change Trust, Supplies and Hope.",
    "A reply marked Needs is shut for now. It opens when the stat or the earlier event it names has happened, so a different earlier choice can open it.",
    "Rewind to here (on any of your messages) goes back to that choice. The branch map lists every day, which choices you have tried and the places you have not found yet.",
    "What if opens on a scene once you have tried two different replies there, and shows where each reply would lead.",
    "Ten endings: nine warm or bittersweet and one quietly sad. Harbour is not perfect either: now and then the quick kind thing is the wrong thing, and a few replies show it. The Archive holds Ines's log entries, the things she finds, and her recordings.",
)

FACTS = (
    {"id": "delay", "heading": "A line to the Moon",
     "fact": "The Moon is about 1.3 light-seconds from Earth, so a radio message to it takes about that long one way.",
     "tie_in": "In the game: Orrin is much farther than that, which is why the line is thin and text-only, but nothing in the story waits on a delay.",
     "source": {"title": "Lunar distance", "url": "https://en.wikipedia.org/wiki/Lunar_distance", "publisher": "Wikipedia", "date_read": DATE_READ}},
    {"id": "relay", "heading": "Why a relay",
     "fact": "The Moon blocks direct radio contact between Earth and its far side, so for the Chang'e 4 landing the Queqiao satellite, launched on 20 May 2018, relayed messages from a halo orbit around the Earth-Moon L2 point.",
     "tie_in": "In the game: Sparrow is a dark relay, and lighting it is one of three ways home.",
     "source": {"title": "Queqiao relay satellite", "url": "https://en.wikipedia.org/wiki/Queqiao_relay_satellite", "publisher": "Wikipedia", "date_read": DATE_READ}},
)


def view():
    return {"framing": FRAMING, "notice": NOTICE, "pledge_heading": "What this game will never do", "pledge": list(PLEDGE),
            "how_heading": "How it works", "how": list(HOW), "facts_heading": "Two real facts behind the idea",
            "facts": [dict(f) for f in FACTS]}
