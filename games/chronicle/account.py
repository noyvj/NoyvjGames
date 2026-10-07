"""Chronicle -- whose account?: read short passages about one event from different sources, then judge one of them.

A puzzle is a PURE FUNCTION of (set id, set version, account id, round), like the other mechanics: nothing random,
no clock, no saved progress (the generator is the shared splitmix64 in puzzle.py). An account (`accounts.json`) is
one event with 2 to 4 passages, each a short ORIGINAL summary of a real source. The page shows every passage in a
seeded display order (Passage A, B, C...); round r puts one of them in focus (display[r % n], so the first n rounds
visit every passage once) and asks up to five questions about its source:

  who        Who wrote the source behind this passage?          options: its author + 3 others from the set (seeded)
  kind       Primary or secondary?                              fixed two options
  vantage    What could the writer see of the event?            fixed options (took part / watched / wrote afterwards)
  purpose    What was the writer trying to do?                  fixed options
  left_out   Which of these does the passage leave out?         1 point it omits + up to 3 it mentions (seeded); only
                                                                asked when the passage omits something

Every answer is a choice from a fixed list built from the passage's own metadata; there is no free text. "Leaves
out" is judged against the passage as printed (a short summary), never against the whole source: the page says so.
`tests/fixtures/account_puzzles_v1.json` pins the sample set's puzzles; a deliberate change to the generator must
bump SEED_VERSION and regenerate the fixture (tests/make_fixture.py).
"""

from puzzle import Rng
from setdata import ACCOUNT_KINDS, PURPOSES, VANTAGES

SEED_VERSION = "v1"
QUESTIONS = ("who", "kind", "vantage", "purpose", "left_out")
PROMPTS = {
    "who": "Who wrote the source behind this passage?",
    "kind": "Is that source primary or secondary?",
    "vantage": "What could the writer see of the event?",
    "purpose": "What was the writer trying to do?",
    "left_out": "Which of these does this passage leave out?",
}
WHO_OPTIONS = 4


class AccountPuzzle:
    def __init__(self, set_id, account, round_no, order, focus, questions):
        self.set_id = set_id
        self.account = account
        self.round = round_no
        self.order = order              # passage ids in the order the page shows them (Passage A, B, C...)
        self.focus = focus              # the passage the questions are about
        self.questions = questions      # [{"id", "options": [option ids in shown order], "answer": option id}]

    @property
    def code(self):
        return "%s/%s/%d" % (self.set_id, self.account, self.round)

    @property
    def size(self):
        return len(self.questions)

    def question_ids(self):
        return [q["id"] for q in self.questions]

    def answer(self):
        return {q["id"]: q["answer"] for q in self.questions}

    def to_dict(self):
        return {"id": self.code, "set": self.set_id, "account": self.account, "round": self.round, "order": list(self.order),
                "focus": self.focus, "questions": [{"id": q["id"], "options": list(q["options"]), "answer": q["answer"]} for q in self.questions]}


def display_order(cset, account_id):
    """The passages in the order the page shows them: one seeded shuffle per account, the same in every round."""
    a = cset.account(account_id)
    rng = Rng("chronicle-account-order|%s|%s|%s|%s" % (SEED_VERSION, cset.id, cset.version, account_id))
    return rng.shuffle([p["id"] for p in a["passages"]])


def main_rounds(cset, account_id):
    a = cset.account(account_id)
    return len(a["passages"]) if a else 0


def omitted_points(account, passage):
    return [pt["id"] for pt in account["points"] if pt["id"] not in passage["mentions"]]


def make_account_puzzle(cset, account_id, round_no):
    a = cset.account(account_id)
    if a is None:
        raise ValueError("unknown account %r" % (account_id,))
    if not isinstance(round_no, int) or isinstance(round_no, bool) or round_no < 0:
        raise ValueError("round must be a non-negative integer")
    order = display_order(cset, account_id)
    n = len(order)
    focus_id = order[round_no % n]
    focus = next(p for p in a["passages"] if p["id"] == focus_id)
    rng = Rng("chronicle-account|%s|%s|%s|%s|%d" % (SEED_VERSION, cset.id, cset.version, account_id, round_no))
    questions = []

    others = [aid for aid in cset.authors() if aid != focus["author_id"]]
    if len(others) < WHO_OPTIONS - 1:
        raise ValueError("account %s: not enough authors for a 'who wrote it' question" % account_id)
    questions.append({"id": "who", "options": rng.shuffle([focus["author_id"]] + rng.sample(others, WHO_OPTIONS - 1)),
                      "answer": focus["author_id"]})
    questions.append({"id": "kind", "options": list(ACCOUNT_KINDS), "answer": focus["kind"]})
    questions.append({"id": "vantage", "options": [v[0] for v in VANTAGES], "answer": focus["vantage"]})
    questions.append({"id": "purpose", "options": [v[0] for v in PURPOSES], "answer": focus["purpose"]})
    omitted = omitted_points(a, focus)
    if omitted:
        right = omitted[(round_no // n) % len(omitted)]
        shown = rng.sample(list(focus["mentions"]), min(3, len(focus["mentions"])))
        questions.append({"id": "left_out", "options": rng.shuffle([right] + shown), "answer": right})
    return AccountPuzzle(cset.id, account_id, round_no, order, focus_id, questions)


def grade(puzzle, answers):
    """Per-question verdicts for a full or partial set of answers ({question id: option id or None})."""
    out = []
    right = 0
    for q in puzzle.questions:
        chosen = answers.get(q["id"])
        if chosen is None:
            out.append({"question": q["id"], "choice": None, "status": "empty"})
        elif chosen == q["answer"]:
            right += 1
            out.append({"question": q["id"], "choice": chosen, "status": "right"})
        else:
            out.append({"question": q["id"], "choice": chosen, "status": "wrong"})
    placed = sum(1 for o in out if o["choice"] is not None)
    return {"questions": out, "right": right, "placed": placed, "all_right": right == puzzle.size}


def option_label(cset, account_id, question_id, option_id):
    """The words shown for one option (the engine builds them so app.js never needs the set's rules)."""
    a = cset.account(account_id)
    if question_id == "who":
        return cset.authors().get(option_id, option_id)
    if question_id == "kind":
        from setdata import KIND_LABELS
        return KIND_LABELS[option_id]
    if question_id == "vantage":
        return dict(VANTAGES)[option_id]
    if question_id == "purpose":
        return dict(PURPOSES)[option_id]
    return next(pt["label"] for pt in a["points"] if pt["id"] == option_id)
