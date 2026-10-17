"""Word Match, Grammar Gaps, Listening Pick and Word Order Race, each a small subclass of the shared base class.
Part of the split of the old single-file minigames.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

from js import document
from pyodide.ffi import create_proxy

import champ_minigames_runstate as runstate
from champ_minigames_core import (
    DIFFICULTY_LABELS, _build_answer_area, _check, _credit, _record, _strip_parens, answer_note, context_line,
    difficulty_points, plot_label, waters_text,
)
from champ_minigames_blitz import (
    VARIANT_BLANK_ENDING, VARIANT_BLANK_WORD, VARIANT_CONJUGATION_SWAP, VARIANT_EXAMPLE_EN_FR,
    VARIANT_EXAMPLE_FR_EN, VARIANT_FR_EN_CHOICE, VARIANT_SYMBOL_NAME_CHOICE,
)
from champ_minigames_racer import RACER_HI, RACER_LO
from champ_minigames_cafe import CAFE_PASSE_COMPOSE_TOPIC_IDS
from champ_minigames_sprint import SPRINT_VARIANTS
from champ_minigames_arcade import _Arcade, _can_hear, _prefer_unwatered, _say


# render() is defined in champ_minigames_registry, which comes later in the module list; that module puts it here when
# it loads (see the end of champ_minigames_registry.py). Calls below find it at run time.
render = None


# ---------------------------------------------------------------------------
# Word Match: pairs of French and English cards (vocabulary and phrases, 12-23)
# ---------------------------------------------------------------------------
PAIRS_LO, PAIRS_HI = 12, 23
PAIRS_PER_BOARD = 4
PAIRS_BOARDS = 3
PAIRS_MAX_FR = 22
PAIRS_MAX_EN = 30
PAIRS_BAD_CHARS = set("[]+/…{}<>")
PAIRS_DIFFICULTY = {
    "slower": {"seconds": 150, "lives": 6},
    "normal": {"seconds": 90, "lives": 3},
    "faster": {"seconds": 60, "lives": 2},
}


class _PairsGame(_Arcade):
    boards_done = 0
    selected = None
    key = "pairs"
    lo, hi = PAIRS_LO, PAIRS_HI
    open_label = "🔗 Word Match"
    close_label = "Close Word Match"
    start_label = "Start matching"
    again_label = "Match again"
    difficulty_table = PAIRS_DIFFICULTY

    def build_pool(self):
        plots = []
        for sequence in range(self.lo, self.hi + 1):
            if not runstate._farm.is_row_unlocked(sequence):
                continue
            for plot in runstate._farm.row_plots(sequence):
                if plot.topic_type not in ("vocab", "phrase") or len(plot.items) != 1:
                    continue
                fr = _strip_parens(plot.items[0]["fr"])
                en = _strip_parens(plot.items[0]["en"])
                if not fr or not en or len(fr) > PAIRS_MAX_FR or len(en) > PAIRS_MAX_EN:
                    continue
                if PAIRS_BAD_CHARS & set(plot.items[0]["fr"] + plot.items[0]["en"]):
                    continue
                plots.append(plot)
        return plots

    def begin(self):
        self.boards_done = 0
        self.selected = None

    def pick_plots(self):
        pool = _prefer_unwatered(self.pool(), PAIRS_PER_BOARD * 2)
        for _ in range(60):
            chosen = self.rng.sample(pool, PAIRS_PER_BOARD)
            frs = {_strip_parens(p.items[0]["fr"]).lower() for p in chosen}
            ens = {_strip_parens(p.items[0]["en"]).lower() for p in chosen}
            if len(frs) == PAIRS_PER_BOARD and len(ens) == PAIRS_PER_BOARD:
                return chosen
        return self.rng.sample(pool, PAIRS_PER_BOARD)

    def new_round(self):
        plots = self.pick_plots()
        cards = []
        for plot in plots:
            item = plot.items[0]
            cards.append({"side": "fr", "plot_id": plot.plot_id, "text": _strip_parens(item["fr"])})
            cards.append({"side": "en", "plot_id": plot.plot_id, "text": _strip_parens(item["en"])})
        self.rng.shuffle(cards)
        for index, card in enumerate(cards):
            card["id"] = index
            card["matched"] = False
        self.selected = None
        self.round = {"cards": cards, "plots": [p.plot_id for p in plots]}

    def waters_labels(self):
        return [plot_label(pid) for pid in self.round["plots"]] if self.round else []

    def select(self, card_id):
        """Tap a card. First tap selects, the second (on the other language)
        tries the pair. Returns True / False for a tried pair, None otherwise."""
        if not self.active or self.round is None:
            return None
        cards = self.round["cards"]
        if not 0 <= card_id < len(cards) or cards[card_id]["matched"]:
            return None
        card = cards[card_id]
        if self.selected is None or cards[self.selected]["side"] == card["side"]:
            self.selected = None if self.selected == card_id else card_id
            render()
            return None
        first = cards[self.selected]
        self.selected = None
        correct = first["plot_id"] == card["plot_id"]
        _record(self.key, correct)
        label = plot_label(card["plot_id"])
        if correct:
            first["matched"] = card["matched"] = True
            kind = runstate._credit_plot_id(card["plot_id"], self.key) if runstate._credit_plot_id is not None else None
            self.note = answer_note(label, True, [kind])
            self.combo += 1
            self.score += self.award()
            if all(c["matched"] for c in cards):
                self.boards_done += 1
                if self.boards_done >= PAIRS_BOARDS:
                    self.score += difficulty_points(self.key, max(0, self.time_remaining))
                    self.end("cleared")
                    render()
                    return True
                self.new_round()
        else:
            self.note = "Not a pair: nothing changes for either plot."
            self.combo = 0
            self.lives -= 1
            if self.lives <= 0:
                self.end("lives")
        render()
        return correct

    def clear_round_ui(self):
        self.el("board").innerHTML = ""

    def cleared_text(self):
        return (
            f"Board cleared! All {PAIRS_BOARDS} boards matched with {self.time_remaining}s to spare. "
            f"Score: {self.score} (best this session: {self.best})."
        )

    def draw_round(self):
        board = self.el("board")
        board.innerHTML = ""
        self.el("progress").innerText = f"Board {self.boards_done + 1} of {PAIRS_BOARDS}"
        for card in self.round["cards"]:
            button = document.createElement("button")
            button.id = f"pairs-card-{card['id']}"
            button.className = "choice pairs-card pairs-card--" + card["side"]
            button.innerText = card["text"]
            proxy = create_proxy(self.make_handler(card["id"]))
            button.addEventListener("click", proxy)
            self.proxies.append(proxy)
            board.appendChild(button)
        self.paint_cards()

    def make_handler(self, card_id):
        def handler(event=None):
            self.select(card_id)
        return handler

    def paint_cards(self):
        board = self.el("board")
        by_id = {c["id"]: c for c in self.round["cards"]}
        for button in board.children:
            try:
                card_id = int(button.id.rsplit("-", 1)[1])
            except (ValueError, IndexError):
                continue
            card = by_id[card_id]
            classes = "choice pairs-card pairs-card--" + card["side"]
            if card["matched"]:
                classes += " choice--answer"
                button.disabled = True
            elif self.selected == card_id:
                classes += " pairs-card--selected"
            button.className = classes
            button.setAttribute("aria-pressed", "true" if self.selected == card_id else "false")

    def refresh_round(self):
        self.el("feedback").innerText = self.note
        self.paint_cards()


# ---------------------------------------------------------------------------
# Grammar Gaps: timed fill-the-gap over the grammar the other games skip
# ---------------------------------------------------------------------------
GAPS_LO, GAPS_HI = 1, 23
GAPS_VARIANTS = {VARIANT_BLANK_WORD, VARIANT_BLANK_ENDING, VARIANT_CONJUGATION_SWAP}
# A rule that is only a list of forms ("je mets / tu mets / il met") has no gap
# to fill; it is asked as "which English matches this example?" instead, so that
# every grammar plot has an arcade game.
GAPS_FALLBACK_VARIANTS = {VARIANT_EXAMPLE_FR_EN, VARIANT_EXAMPLE_EN_FR}
GAPS_DIFFICULTY = {
    "slower": {"seconds": 90, "lives": 5},
    "normal": {"seconds": 60, "lives": 3},
    "faster": {"seconds": 45, "lives": 2},
}


class _GapsGame(_Arcade):
    key = "gaps"
    lo, hi = GAPS_LO, GAPS_HI
    open_label = "🧩 Grammar Gaps"
    close_label = "Close Grammar Gaps"
    start_label = "Start"
    difficulty_table = GAPS_DIFFICULTY

    def build_pool(self):
        plots = []
        for sequence in range(self.lo, self.hi + 1):
            if not runstate._farm.is_row_unlocked(sequence) or RACER_LO <= sequence <= RACER_HI:
                continue
            for plot in runstate._farm.row_plots(sequence):
                if plot.topic_type != "grammar":
                    continue
                # The passé composé has its own Sprint, unless a rule there has no gap for
                # the Sprint to ask (the être verbs are a list): then it is asked here.
                if plot.topic_id in CAFE_PASSE_COMPOSE_TOPIC_IDS and any(
                    v in SPRINT_VARIANTS for v in runstate._variants_for(plot)
                ):
                    continue
                if self.variants_of(plot):
                    plots.append(plot)
        return plots

    def variants_of(self, plot):
        offered = runstate._variants_for(plot)
        return [v for v in offered if v in GAPS_VARIANTS] or [v for v in offered if v in GAPS_FALLBACK_VARIANTS]

    def new_round(self):
        pool = _prefer_unwatered(self.pool(), 8)
        plot = self.rng.choice(pool)
        self.round = runstate._generate_question(plot, self.rng, variant=self.rng.choice(self.variants_of(plot)))

    def waters_labels(self):
        return [plot_label(self.round["plot_id"])] if self.round else []

    def submit(self, given):
        if not self.active or self.round is None:
            return None
        question = self.round
        correct = _check(question, given)
        _record(self.key, correct)
        label = plot_label(question["plot_id"])
        if correct:
            kind = _credit(question, self.key)
            self.note = answer_note(label, True, [kind])
            self.combo += 1
            self.score += self.award()
        else:
            self.note = answer_note(label, False, [])
            self.combo = 0
            self.lives -= 1
        if self.lives <= 0:
            self.end("lives")
        else:
            self.new_round()
        render()
        return correct

    def clear_round_ui(self):
        self.el("choices").innerHTML = ""
        self.el("context").innerText = ""
        self.el("prompt").innerText = ""

    def draw_round(self):
        self.el("context").innerText = context_line(self.round)
        self.el("prompt").innerText = self.round["prompt"]
        _build_answer_area(self.key, self.round, self.el("choices"), self.proxies, self.submit)

    def refresh_round(self):
        pass


# ---------------------------------------------------------------------------
# Listening Pick: hear the French, pick what it means
# ---------------------------------------------------------------------------
LISTEN_LO, LISTEN_HI = 1, 23
LISTEN_QUESTIONS = 10
LISTEN_VARIANTS = (VARIANT_FR_EN_CHOICE, VARIANT_SYMBOL_NAME_CHOICE)
LISTEN_DIFFICULTY = {
    "slower": {"seconds": 25, "lives": 6},
    "normal": {"seconds": 15, "lives": 3},
    "faster": {"seconds": 9, "lives": 2},
}
LISTEN_HIDDEN_PROMPT = "🔊 Listen, then pick what it means."


class _ListenGame(_Arcade):
    asked = 0
    revealed = False
    key = "listenpick"
    lo, hi = LISTEN_LO, LISTEN_HI
    open_label = "🎧 Listening Pick"
    close_label = "Close Listening Pick"
    start_label = "Start listening"
    again_label = "Listen again"
    difficulty_table = LISTEN_DIFFICULTY

    def describe(self, level):
        p = self.difficulty_table[level]
        return f"{DIFFICULTY_LABELS[level]}: {p['seconds']} seconds to answer each of {LISTEN_QUESTIONS} questions, {p['lives']} lives."

    def build_pool(self):
        plots = []
        for sequence in range(self.lo, self.hi + 1):
            if not runstate._farm.is_row_unlocked(sequence):
                continue
            for plot in runstate._farm.row_plots(sequence):
                if plot.topic_type != "grammar" and any(v in LISTEN_VARIANTS for v in runstate._variants_for(plot)):
                    plots.append(plot)
        return plots

    def begin(self):
        self.asked = 0
        self.revealed = False
        self.question_seconds = self.params()["seconds"]
        self.time_remaining = self.question_seconds

    def new_round(self):
        pool = _prefer_unwatered(self.pool(), 10)
        plot = self.rng.choice(pool)
        variant = self.rng.choice([v for v in runstate._variants_for(plot) if v in LISTEN_VARIANTS])
        self.round = runstate._generate_question(plot, self.rng, variant=variant)
        self.asked += 1
        self.revealed = False
        self.time_remaining = self.question_seconds
        _say(self.round["prompt"])

    def waters_labels(self):
        if not self.round:
            return []
        # The French text is the answer's giveaway, so while it is hidden the line only
        # says that a plot is being watered; the note after the answer names it.
        if self.hidden():
            return ["the word you are hearing"]
        return [plot_label(self.round["plot_id"])]

    def hidden(self):
        return _can_hear() and not self.revealed

    def stats(self):
        values = super().stats()
        values["combo"] = f"Question {min(self.asked, LISTEN_QUESTIONS)} of {LISTEN_QUESTIONS}"
        return values

    def on_time_up(self):
        # The clock for one question ran out: a miss, and on to the next.
        if self.round is not None:
            self.settle(False, timed_out=True)

    def settle(self, correct, timed_out=False):
        question = self.round
        label = plot_label(question["plot_id"])
        _record(self.key, correct)
        if correct:
            kind = _credit(question, self.key)
            self.note = answer_note(label, True, [kind])
            self.combo += 1
            self.score += self.award()
        else:
            reason = "Time ran out. " if timed_out else ""
            self.note = reason + answer_note(label, False, []) + f" It was: {question['prompt']} = {question['answer']}."
            self.combo = 0
            self.lives -= 1
        if self.lives <= 0:
            self.end("lives")
        elif self.asked >= LISTEN_QUESTIONS:
            self.end("cleared")
        else:
            self.new_round()

    def submit(self, given):
        if not self.active or self.round is None:
            return None
        correct = _check(self.round, given)
        self.settle(correct)
        render()
        return correct

    def cleared_text(self):
        return f"All {LISTEN_QUESTIONS} heard! Score: {self.score} (best this session: {self.best})."

    def clear_round_ui(self):
        self.el("choices").innerHTML = ""
        self.el("context").innerText = ""
        self.el("prompt").innerText = ""
        self.el("play-button").hidden = True
        self.el("slow-button").hidden = True
        self.el("show-button").hidden = True

    def draw_round(self):
        self.el("context").innerText = context_line(self.round)
        self.el("prompt").innerText = LISTEN_HIDDEN_PROMPT if self.hidden() else self.round["prompt"]
        can_hear = _can_hear()
        self.el("play-button").hidden = not can_hear
        self.el("slow-button").hidden = not can_hear
        self.el("show-button").hidden = not self.hidden()
        _build_answer_area(self.key, self.round, self.el("choices"), self.proxies, self.submit)

    def reveal(self, event=None):
        if self.round is None:
            return
        self.revealed = True
        self.el("prompt").innerText = self.round["prompt"]
        self.el("waters").innerText = waters_text(self.waters_labels())
        self.el("show-button").hidden = True

    def replay(self, event=None):
        if self.round is not None:
            _say(self.round["prompt"])

    def replay_slow(self, event=None):
        if self.round is not None:
            _say(self.round["prompt"], True)

    def setup_extra(self):
        self.el("play-button").addEventListener("click", create_proxy(self.replay))
        self.el("slow-button").addEventListener("click", create_proxy(self.replay_slow))
        self.el("show-button").addEventListener("click", create_proxy(self.reveal))


# ---------------------------------------------------------------------------
# Word Order Race: put an example sentence's words in order
# ---------------------------------------------------------------------------
ORDER_LO, ORDER_HI = 1, 23
ORDER_SENTENCES = 6
ORDER_MIN_WORDS, ORDER_MAX_WORDS = 3, 8
ORDER_BAD_CHARS = set("[]+/…{}()<>→")
ORDER_DIFFICULTY = {
    "slower": {"seconds": 60, "lives": 0},
    "normal": {"seconds": 40, "lives": 0},
    "faster": {"seconds": 25, "lives": 0},
}


class _OrderGame(_Arcade):
    done = 0
    painted = None
    key = "wordorder"
    lo, hi = ORDER_LO, ORDER_HI
    open_label = "🧱 Word Order Race"
    close_label = "Close Word Order Race"
    start_label = "Start the race"
    again_label = "Race again"
    difficulty_table = ORDER_DIFFICULTY
    base_points = 10

    def describe(self, level):
        p = self.difficulty_table[level]
        return f"{DIFFICULTY_LABELS[level]}: {p['seconds']} seconds for each of {ORDER_SENTENCES} sentences. A miss costs nothing but the points."

    def eligible_items(self, plot):
        items = []
        for item in plot.items:
            fr = item["fr"].strip()
            words = fr.split()
            if not ORDER_MIN_WORDS <= len(words) <= ORDER_MAX_WORDS:
                continue
            if ORDER_BAD_CHARS & set(fr) or not item.get("en"):
                continue
            if len(set(words)) < 2:
                continue
            items.append(item)
        return items

    def build_pool(self):
        plots = []
        for sequence in range(self.lo, self.hi + 1):
            if not runstate._farm.is_row_unlocked(sequence):
                continue
            for plot in runstate._farm.row_plots(sequence):
                if plot.topic_type == "grammar" and self.eligible_items(plot):
                    plots.append(plot)
        return plots

    def begin(self):
        self.done = 0
        self.placed = []
        self.painted = None
        self.used_plots = set()
        self.question_seconds = self.params()["seconds"]
        self.time_remaining = self.question_seconds

    def stats(self):
        values = super().stats()
        values["lives"] = ""
        values["combo"] = f"Sentence {min(self.done + 1, ORDER_SENTENCES)} of {ORDER_SENTENCES}"
        return values

    def new_round(self):
        pool = [p for p in self.pool() if p.plot_id not in self.used_plots] or self.pool()
        pool = _prefer_unwatered(pool, 4)
        plot = self.rng.choice(pool)
        self.used_plots.add(plot.plot_id)
        item = self.rng.choice(self.eligible_items(plot))
        words = item["fr"].strip().split()
        order = list(range(len(words)))
        for _ in range(12):
            self.rng.shuffle(order)
            if [words[i] for i in order] != words:
                break
        self.placed = []
        self.time_remaining = self.question_seconds
        self.round = {
            "plot_id": plot.plot_id,
            "answer": " ".join(words),
            "words": words,
            "order": order,
            "en": item["en"].strip(),
        }

    def waters_labels(self):
        return [plot_label(self.round["plot_id"])] if self.round else []

    def on_time_up(self):
        if self.round is not None:
            self.settle(False, timed_out=True)

    def settle(self, correct, timed_out=False):
        question = self.round
        label = plot_label(question["plot_id"])
        _record(self.key, correct)
        if correct:
            kind = runstate._credit_plot_id(question["plot_id"], self.key) if runstate._credit_plot_id is not None else None
            self.note = answer_note(label, True, [kind])
            self.combo += 1
            self.score += self.award(self.base_points + max(0, self.time_remaining) // 4)
        else:
            reason = "Time ran out. " if timed_out else ""
            self.note = reason + answer_note(label, False, []) + f" The sentence was: {question['answer']}"
            self.combo = 0
        self.done += 1
        if self.done >= ORDER_SENTENCES:
            self.end("cleared")
        else:
            self.new_round()

    def place(self, tile_index):
        """Tap a tile in the pool (an index into the shuffled order). When the
        last tile is placed the sentence is checked."""
        if not self.active or self.round is None or tile_index in self.placed:
            return None
        if not 0 <= tile_index < len(self.round["order"]):
            return None
        self.placed.append(tile_index)
        if len(self.placed) < len(self.round["order"]):
            render()
            return None
        built = [self.round["words"][self.round["order"][i]] for i in self.placed]
        correct = built == self.round["words"]
        self.settle(correct)
        render()
        return correct

    def undo(self, event=None):
        if self.active and self.placed:
            self.placed.pop()
            render()

    def cleared_text(self):
        return f"All {ORDER_SENTENCES} sentences done! Score: {self.score} (best this session: {self.best})."

    def clear_round_ui(self):
        self.el("pool").innerHTML = ""
        self.el("placed").innerHTML = ""
        self.el("prompt").innerText = ""
        self.el("undo-button").hidden = True

    def draw_round(self):
        self.el("prompt").innerText = self.round["en"]
        self.paint_tiles()

    def paint_tiles(self):
        self.destroy_proxies()
        self.painted = tuple(self.placed)
        pool, placed_box = self.el("pool"), self.el("placed")
        pool.innerHTML = ""
        placed_box.innerHTML = ""
        words, order = self.round["words"], self.round["order"]
        for tile_index in self.placed:
            chip = document.createElement("span")
            chip.className = "bonus-tile bonus-tile--placed"
            chip.innerText = words[order[tile_index]]
            placed_box.appendChild(chip)
        for tile_index, word_index in enumerate(order):
            if tile_index in self.placed:
                continue
            button = document.createElement("button")
            button.id = f"wordorder-tile-{tile_index}"
            button.className = "choice bonus-tile"
            button.innerText = words[word_index]
            proxy = create_proxy(self.make_handler(tile_index))
            button.addEventListener("click", proxy)
            self.proxies.append(proxy)
            pool.appendChild(button)
        self.el("undo-button").hidden = not self.placed

    def make_handler(self, tile_index):
        def handler(event=None):
            self.place(tile_index)
        return handler

    def refresh_round(self):
        # Repaint the tiles only when one was placed or taken back: a clock tick
        # must not rebuild buttons under a finger.
        if tuple(self.placed) != self.painted:
            self.paint_tiles()

    def setup_extra(self):
        self.el("undo-button").addEventListener("click", create_proxy(self.undo))
