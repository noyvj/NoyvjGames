"""Lexis -- reading a signal.

`parse(marks, language)` turns a string of marks into a Sentence, or raises SignalError carrying a reason
code and an IN-WORLD line. A sentence that cannot be understood is never a crash and never "wrong answer":
the world just does not react the way you hoped, and says why in its own terms. That is the feedback the
player learns from.
"""

from dataclasses import dataclass


class SignalError(Exception):
    """The station could not make sense of the signal. `reason` is a stable code (tests and the notebook
    use it); `text` is what the world says."""

    def __init__(self, reason, text):
        super().__init__(text)
        self.reason = reason
        self.text = text


@dataclass(frozen=True)
class Sentence:
    """A parsed sentence. For lamps `value` is the number; for a door it is "open" or "shut"."""

    noun: str
    value: object


def tokenize(marks, language):
    if not marks:
        raise SignalError("silence", "Nothing was sent. The station hums and waits.")
    alphabet = set("01")
    if any(ch not in alphabet for ch in marks):
        raise SignalError("bad_mark", "That is not a mark this channel carries.")
    n = language.token_len
    if len(marks) % n:
        raise SignalError("cut_off", "The signal stops in the middle of a word. The station waits for the rest.")
    return [marks[i:i + n] for i in range(0, len(marks), n)]


def parse(marks, language):
    tokens = tokenize(marks, language)
    end_form = language.by_id("end").form
    if tokens[-1] != end_form:
        raise SignalError("no_end", "The message never closes. The station keeps listening.")
    body = tokens[:-1]
    if end_form in body:
        raise SignalError("early_end", "The message closes too early. The station stops listening halfway.")
    if len(body) != 2:
        raise SignalError("shape", "The station expects a thing and then what to do with it. This is not that shape.")
    first, second = body

    noun = language.by_form(first)
    if language.is_number_token(first) or noun is None or noun.kind != "noun":
        raise SignalError("no_thing", "The station does not recognise what you are talking about.")

    if noun.id == "lamp":
        if not language.is_number_token(second):
            raise SignalError("lamp_needs_number", "The lamps wait for a count. They get something else.")
        return Sentence("lamp", language.number_value(second))
    if noun.id == "door":
        state = language.by_form(second)
        if state is None or state.kind != "state":
            raise SignalError("door_needs_state", "The door waits for open or shut. It gets something else.")
        return Sentence("door", state.id)
    raise SignalError("no_thing", "The station does not recognise what you are talking about.")
