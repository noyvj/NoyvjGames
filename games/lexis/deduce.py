"""Lexis -- the deducibility checker (the fairness guarantee).

The commonest failure of this kind of game is a word the player cannot actually work out. This module
answers, for any set of scenes the player has seen: "which readings of the language are still consistent
with the evidence, and do they all behave the same way?" If they do, the player can rely on the language;
if some still disagree, the scenes shown so far do not settle it and the curriculum needs another scene.

Used by the tests (every prefix of every curriculum is checked) and by the game to decide what is proven.

A reading (Hypothesis) is a number rule plus a meaning for each word form. Meanings are the actions the
rung-1 world understands. Two readings are the same for the player's purposes when they predict the same
station for every sentence the language can form, so the question is behavioural, not about spelling.
"""

import itertools
from dataclasses import dataclass

from lang import NUMBER_RULES, decode_number
from pulse import MAX_NUMBER, PULSE, say_door, say_lamps
from world import Station

SEMS = ("LAMPS", "DOOR", "OPEN", "SHUT", "IGNORE")


@dataclass(frozen=True)
class Hypothesis:
    rule: str
    meanings: tuple   # ((form, sem), ...) in a fixed order, so it is hashable

    def sem_of(self, form):
        for f, sem in self.meanings:
            if f == form:
                return sem
        return "IGNORE"


def _forms(language):
    return tuple(word.form for word in language.words)


def all_hypotheses(language=PULSE):
    forms = _forms(language)
    for rule in NUMBER_RULES:
        for assignment in itertools.product(SEMS, repeat=len(forms)):
            yield Hypothesis(rule, tuple(zip(forms, assignment)))


def evaluate(hyp, marks, station, language=PULSE):
    """What station results if the signal `marks` is read under `hyp`. A reading never errors: a signal it
    cannot make sense of simply changes nothing."""
    n = language.token_len
    tokens = [marks[i:i + n] for i in range(0, len(marks) - len(marks) % n, n)]
    lamps, door = station.lamps, station.door
    i = 0
    while i < len(tokens):
        token = tokens[i]
        sem = "IGNORE" if language.is_number_token(token) else hyp.sem_of(token)
        nxt = tokens[i + 1] if i + 1 < len(tokens) else None
        if sem == "LAMPS" and nxt is not None and language.is_number_token(nxt):
            lamps = min(max(decode_number(nxt[1:], hyp.rule), 0), MAX_NUMBER)
            i += 2
        elif sem == "DOOR" and nxt is not None and not language.is_number_token(nxt) and hyp.sem_of(nxt) in ("OPEN", "SHUT"):
            door = "open" if hyp.sem_of(nxt) == "OPEN" else "shut"
            i += 2
        else:
            i += 1
    return Station(lamps, door)


def consistent_hypotheses(scenes, language=PULSE):
    return [
        hyp for hyp in all_hypotheses(language)
        if all(evaluate(hyp, s.marks, s.before, language) == s.after for s in scenes)
    ]


def _probe_messages():
    """Every sentence the Pulse language can form, tried from a few different starting stations."""
    messages = [say_lamps(n) for n in range(MAX_NUMBER + 1)] + [say_door("open"), say_door("shut")]
    starts = [Station(0, "shut"), Station(3, "open"), Station(7, "shut")]
    return [(m, st) for m in messages for st in starts]


def disagreements(scenes, language=PULSE):
    """The probe messages on which the readings still consistent with `scenes` disagree. Empty means the
    scenes settle how the language behaves."""
    hyps = consistent_hypotheses(scenes, language)
    if not hyps:
        return [("no reading fits these scenes", None)]
    out = []
    for message, start in _probe_messages():
        predictions = {evaluate(h, message, start, language) for h in hyps}
        if len(predictions) > 1:
            out.append((message, start))
    return out


def determinate(scenes, language=PULSE):
    return not disagreements(scenes, language)
