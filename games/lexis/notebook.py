"""Lexis -- the player's notebook and what is saved.

Guesses are free and can be wrong: the notebook stores whatever the player writes and never marks it. The
only feedback is from the world (what happens when they speak) and from confirmation checks, which say how
MANY of the chosen entries are right, never which. That keeps the deduction the player's, not the game's.
"""

from dataclasses import dataclass, field

from pulse import PULSE


def _norm(text):
    return " ".join(str(text).lower().split())


@dataclass
class Notebook:
    entries: dict = field(default_factory=dict)   # form -> the player's gloss

    def write(self, form, gloss):
        gloss = _norm(gloss)
        if gloss:
            self.entries[form] = gloss
        else:
            self.entries.pop(form, None)

    def truth(self, form, language=PULSE):
        """The real gloss of a form, or None when it spells nothing. Numbers gloss as their digits."""
        if language.is_number_token(form):
            return str(language.number_value(form))
        word = language.by_form(form)
        return word.meaning if word else None

    def confirm(self, forms, language=PULSE, truth=None):
        """How many of the chosen entries are right. Entries that are empty or not chosen do not count and
        are not revealed. `truth` (form -> true gloss or None) lets another language reuse the notebook."""
        truth = truth or (lambda form: self.truth(form, language))
        right = 0
        for form in forms:
            guess = self.entries.get(form)
            if guess is not None and guess == _norm(truth(form) or ""):
                right += 1
        return right

    def to_dict(self):
        return {"entries": dict(self.entries)}

    @staticmethod
    def from_dict(data):
        nb = Notebook()
        for form, gloss in (data or {}).get("entries", {}).items():
            nb.write(str(form), gloss)
        return nb


@dataclass
class LexisState:
    """Everything the save widget stores. Deterministic: there is no random state to save."""

    notebook: Notebook = field(default_factory=Notebook)
    scenes_seen: int = 0
    spoken: list = field(default_factory=list)   # signals the player has sent, oldest first
    # Rung 2 (the Compound language): its own notebook (by component letter), scenes seen and spoken glyphs.
    compound_notebook: Notebook = field(default_factory=Notebook)
    compound_scenes_seen: int = 0
    compound_spoken: list = field(default_factory=list)
    # Which planets the player has made contact with (the goal for each is in game.py).
    contact: dict = field(default_factory=lambda: {"pulse": False, "compound": False})

    def see_next_scene(self, total):
        self.scenes_seen = min(self.scenes_seen + 1, total)

    def to_dict(self):
        return {"version": 2, "notebook": self.notebook.to_dict(), "scenes_seen": self.scenes_seen,
                "spoken": list(self.spoken)[-200:],
                "compound": {"notebook": self.compound_notebook.to_dict(), "scenes_seen": self.compound_scenes_seen,
                             "spoken": list(self.compound_spoken)[-200:]},
                "contact": dict(self.contact)}

    @staticmethod
    def from_dict(data):
        data = data or {}
        state = LexisState(Notebook.from_dict(data.get("notebook")), max(0, int(data.get("scenes_seen", 0))))
        state.spoken = [str(s) for s in data.get("spoken", []) if set(str(s)) <= set("01")][-200:]
        comp = data.get("compound") or {}
        state.compound_notebook = Notebook.from_dict(comp.get("notebook"))
        state.compound_scenes_seen = max(0, int(comp.get("scenes_seen", 0)))
        state.compound_spoken = [str(s) for s in comp.get("spoken", []) if str(s).isalpha()][-200:]
        contact = data.get("contact") or {}
        state.contact = {"pulse": bool(contact.get("pulse")), "compound": bool(contact.get("compound"))}
        return state
