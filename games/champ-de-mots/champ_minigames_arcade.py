"""The base class the four newer games share (panel, start and close, timer, difficulty, summary) plus the speech hooks.
Part of the split of the old single-file minigames.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

import random

from pyodide.ffi import create_proxy

import champ_minigames_runstate as runstate
from champ_minigames_core import (
    DIFFICULTY_LABELS, _element, _lock_reason, _range_fully_unlocked, _render_difficulty, _reset_credit,
    _setup_difficulty, _with_growth, difficulty_points, get_difficulty, waters_text,
)


# render() is defined in champ_minigames_registry, which comes later in the module list; that module puts it here when
# it loads (see the end of champ_minigames_registry.py). Calls below find it at run time.
render = None


def configure_speech(speak_fn=None, speech_ok_fn=None):
    """game.py hands in its speak_french / speech_available (they use the
    page's own voices; both are quiet no-ops without them)."""
    runstate._speak = speak_fn
    runstate._speech_ok = speech_ok_fn


def _can_hear():
    return bool(runstate._speech_ok()) if runstate._speech_ok is not None else False


def _say(text, slow=False):
    if runstate._speak is not None:
        runstate._speak(text, slow)


def _can_water(plot):
    return plot.last_watered != runstate._farm.current_day


def _prefer_unwatered(plots, minimum):
    """Plots that can still be fully watered today, unless there are too few
    of them to build a round (then everything, so a game is always playable)."""
    fresh = [p for p in plots if _can_water(p)]
    return fresh if len(fresh) >= minimum else plots


class _Arcade:
    """The frame every new game shares: panel, start / close, timer and lives
    display, difficulty, summary, growth line. A subclass supplies its pool,
    how a round is built and drawn, and what an answer does."""

    key = ""
    lo, hi = 1, 23
    open_label = ""
    close_label = ""
    start_label = "Start"
    again_label = "Play again"
    difficulty_table = {}
    base_points = 10

    def __init__(self):
        self.open = False
        self.active = False
        self.score = 0
        self.best = 0
        self.lives = 0
        self.combo = 0
        self.time_remaining = 0
        self.end_reason = None
        self.note = ""
        self.round = None
        self.rendered = None
        self.proxies = []
        self.rng = random.Random()
        self._pool = None

    # --- hooks --------------------------------------------------------
    def build_pool(self):
        raise NotImplementedError

    def new_round(self):
        raise NotImplementedError

    def draw_round(self):
        raise NotImplementedError

    def clear_round_ui(self):
        pass

    def waters_labels(self):
        return []

    def describe(self, level):
        p = self.difficulty_table[level]
        return f"{DIFFICULTY_LABELS[level]}: {p['seconds']} seconds and {p['lives']} lives."

    def summary_text(self):
        return f"Time's up! Score: {self.score} (best this session: {self.best})."

    def lives_text(self):
        return f"Out of lives for this round. Score: {self.score} (best this session: {self.best})."

    def cleared_text(self):
        return f"Round complete! Score: {self.score} (best this session: {self.best})."

    # --- shared -------------------------------------------------------
    def el(self, suffix):
        return _element(f"{self.key}-{suffix}")

    def params(self):
        return self.difficulty_table[get_difficulty(self.key)]

    def pool(self):
        if self._pool is None:
            self._pool = self.build_pool()
        return self._pool

    def available(self):
        return _range_fully_unlocked(self.lo, self.hi)

    def lock_reason(self):
        return None if self.available() else _lock_reason(self.hi)

    def multiplier(self, combo):
        return 1.0 + min(combo // 3, 4) * 0.5

    def award(self, base=None):
        """Score for one right answer (combo multiplier, then difficulty)."""
        base = self.base_points if base is None else base
        return difficulty_points(self.key, round(base * self.multiplier(self.combo)))

    def start(self, event=None):
        if not self.available() or not self.pool():
            return None
        self.open = True
        self.active = True
        self.score = 0
        self.combo = 0
        self.lives = self.params().get("lives", 0)
        self.time_remaining = self.params().get("seconds", 0)
        self.end_reason = None
        self.note = ""
        self.rendered = None
        _reset_credit(self.key)
        self.begin()
        self.new_round()
        render()
        return self.round

    def begin(self):
        """Per-game reset at the start of a run."""

    def end(self, reason):
        self.active = False
        self.end_reason = reason
        self.best = max(self.best, self.score)
        self.round = None

    def tick(self, event=None):
        if not self.active:
            return None
        self.time_remaining -= 1
        if self.time_remaining <= 0:
            self.time_remaining = 0
            self.on_time_up()
        else:
            self.on_tick()
        render()
        return self.time_remaining

    def on_time_up(self):
        self.end("time")

    def on_tick(self):
        pass

    def close(self, event=None):
        self.open = False
        self.active = False
        self.round = None
        self.end_reason = None
        self.note = ""
        self.rendered = None
        render()

    def toggle(self, event=None):
        if self.open:
            self.close()
        else:
            self.open = True
            render()

    def open_panel(self):
        self.open = True
        render()

    def destroy_proxies(self):
        for proxy in self.proxies:
            proxy.destroy()
        self.proxies.clear()

    # stats line; subclasses override when they do not use a clock/lives
    def stats(self):
        return {
            "time": f"{self.time_remaining}s",
            "lives": "❤" * max(self.lives, 0) or "0 lives",
            "score": f"Score: {self.score}",
            "combo": f"Combo x{self.multiplier(self.combo):.1f}" if self.combo >= 3 else "",
        }

    def render(self):
        toggle = self.el("toggle-button")
        panel = self.el("panel")
        available = self.available()
        toggle.disabled = not self.open and not available
        toggle.innerText = self.close_label if self.open else self.open_label
        if not self.open:
            panel.hidden = True
            self.destroy_proxies()
            self.clear_round_ui()
            self.rendered = None
            return
        panel.hidden = False
        reason = self.lock_reason()
        lock = self.el("lock-message")
        lock.hidden = reason is None
        lock.innerText = reason or ""
        _render_difficulty(self.key, self.active, self.describe)
        values = self.stats()
        self.el("time-display").innerText = values["time"]
        self.el("lives-display").innerText = values["lives"]
        self.el("score-display").innerText = values["score"]
        self.el("combo-display").innerText = values["combo"]
        start = self.el("start-button")
        summary = self.el("summary")
        if not self.active:
            self.destroy_proxies()
            self.clear_round_ui()
            self.rendered = None
            self.el("feedback").innerText = ""
            self.el("waters").innerText = ""
            start.hidden = reason is not None
            start.innerText = self.again_label if self.end_reason is not None else self.start_label
            summary.hidden = self.end_reason is None
            if self.end_reason == "time":
                text = self.summary_text()
            elif self.end_reason == "lives":
                text = self.lives_text()
            elif self.end_reason == "cleared":
                text = self.cleared_text()
            else:
                text = ""
            summary.innerText = _with_growth(text, self.key) if text else ""
            return
        start.hidden = True
        summary.hidden = True
        if self.round is not self.rendered:
            self.destroy_proxies()
            self.el("feedback").innerText = self.note
            self.el("waters").innerText = waters_text(self.waters_labels())
            self.draw_round()
            self.rendered = self.round
        else:
            self.refresh_round()

    def refresh_round(self):
        """Light repaint on a clock tick (the round itself did not change)."""

    def setup(self):
        _setup_difficulty(self.key)
        self.el("toggle-button").addEventListener("click", create_proxy(self.toggle))
        self.el("start-button").addEventListener("click", create_proxy(self.start))
        self.el("close-button").addEventListener("click", create_proxy(self.close))
        self.setup_extra()

    def setup_extra(self):
        pass
