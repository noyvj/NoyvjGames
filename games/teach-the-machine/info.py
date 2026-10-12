"""Teach the Machine -- the About page: what the game is, what it will never do, and the real method behind Pip.

Pip, the workshop and every crate, door and signal are invented, and so is all the data. The method is real: Pip is a small decision
tree, trained by information gain. The facts below were read from the named Wikipedia pages on the date given and are reworded here, never
copied. About also tries to read the summary of the Decision tree learning article live when it is opened (app.js asks Wikipedia's
summary service) and names the day it was read; if that fails, the notes below stand with their own read date. Nothing here depends on a
clock: the live read date is made by the page.
"""

DATE_READ = "2026-10-12"
LIVE_SOURCE = {"title": "Decision tree learning", "publisher": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Decision_tree_learning",
               "api": "https://en.wikipedia.org/api/rest_v1/page/summary/Decision_tree_learning"}

FRAMING = ("Teach the Machine is set in an invented station workshop with Pip, a small sorting machine. Every case in the game is made up. "
           "The method is real, though very small: Pip is a decision tree, one of the simplest ways a computer can learn to sort things. "
           "Larger systems use many other methods, and this game does not claim to show how they work.")

PLEDGE = (
    "Nothing is timed. There is no clock, no energy and no streak: a lesson takes as long as you like.",
    "Nothing is lost. A wrong answer ends nothing, a cleared lesson stays cleared, and you can train again as often as you like.",
    "No luck. Training is the same every time: the same switches on the same cases always grow the same tree. Every lesson was proved by a program to be clearable, and to need a sensible choice of features.",
    "No sound, no pictures from anywhere else (Pip is drawn by the page), no purchases, no leaderboards and no ads inside a lesson.",
)

HOW = (
    "Each lesson is a sorting job. You choose which features Pip may look at with the switches, then press Train. Pip studies a fixed table of training cases and grows a small tree of yes-or-no questions.",
    "Press Test and Pip sorts cases it has never seen. Each answer is marked Right or Wrong in words. Get enough right (the lesson says how many) and the lesson is cleared.",
    "Every wrong answer has a Why button. It shows the exact questions the case went through, the question that decided it, the training cases that looked alike, and which of five kinds of mistake it was. Each kind goes into your Failure Notebook the first time you find one.",
    "Nothing says which features to use. Switching a feature off can help as much as switching one on. Change the switches and Train again as often as you like.",
    "Five cleared lessons on a shelf open the next shelf. Inside a shelf, any order.",
)

FACTS = (
    {
        "id": "tree", "heading": "A tree of questions",
        "fact": "In a classification tree, the leaves hold the answers (the class labels) and the branches are conditions on the features that lead to them.",
        "tie_in": "Pip's tree is exactly this. After Train, the workshop shows it in words, one question per branch.",
        "source": {"title": "Decision tree learning", "publisher": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Decision_tree_learning"},
    },
    {
        "id": "gain", "heading": "Picking the question",
        "fact": "Well-known tree learners such as ID3, C4.5 and C5.0 choose each question by information gain, a measure built on entropy from information theory.",
        "tie_in": "Pip picks the question that sorts its training cases most cleanly. A tie goes to the feature that comes first in the list, so Pip never rolls dice.",
        "source": {"title": "Decision tree learning", "publisher": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Decision_tree_learning"},
    },
    {
        "id": "complex", "heading": "Too complicated to trust",
        "fact": "Tree learners can build trees that are too complex and so do badly on new data. The usual remedy is to prune the tree.",
        "tie_in": "Pip's tree can only go three questions deep, which keeps it small. The unseen cases in each test are how you find out whether it learned or just memorised.",
        "source": {"title": "Decision tree learning", "publisher": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Decision_tree_learning"},
    },
    {
        "id": "noise", "heading": "Mistaking noise for a pattern",
        "fact": "Overfitting is a model fitting one data set so closely that it mistakes random leftover variation (noise) for real structure. A model can keep improving on its training data while getting worse on data it has not seen.",
        "tie_in": "That is what the Distractions shelf is about: with a short training table, a useless feature can look useful, and switching it off is the fix.",
        "source": {"title": "Overfitting", "publisher": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Overfitting"},
    },
)


def view():
    return {"framing": FRAMING, "date_read": DATE_READ, "pledge_heading": "What this game will never do", "pledge": list(PLEDGE),
            "how_heading": "How it works", "how": list(HOW), "facts_heading": "The real method",
            "facts": [dict(f, source=dict(f["source"], date_read=DATE_READ)) for f in FACTS], "live": dict(LIVE_SOURCE)}
