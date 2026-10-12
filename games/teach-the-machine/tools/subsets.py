"""Teach the Machine -- the subset search (dev tool and test helper; the game itself never runs it).

For a lesson it tries every set of switched-on features (at most 8 features, so at most 256 sets, the empty set included as a plain
"answer the majority" machine) and records what Pip scores on the unseen table. The best set is the highest score, then the fewest
features, then the one that comes first when sets are compared by their features' positions: a fixed rule, so the stored best set is a fact.
"""

import itertools
import sys
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
if str(GAME_DIR) not in sys.path:
    sys.path.insert(0, str(GAME_DIR))

import lessonkit  # noqa: E402


def all_sets(fids):
    for size in range(len(fids) + 1):
        for combo in itertools.combinations(range(len(fids)), size):
            yield combo


def all_scores(lesson):
    """{tuple of feature ids (in lesson order): right answers on the unseen table} for every set of switches."""
    fids = lesson["fids"]
    out = {}
    for combo in all_sets(fids):
        on = tuple(fids[i] for i in combo)
        out[on] = lessonkit.score(lesson, set(on))[0]
    return out


def best_set(lesson, scores=None):
    """(the best tuple of feature ids, its score)."""
    scores = scores if scores is not None else all_scores(lesson)
    fids = lesson["fids"]
    key = lambda on: (-scores[on], len(on), tuple(fids.index(f) for f in on))
    on = min(scores, key=key)
    return on, scores[on]
