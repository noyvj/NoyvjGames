"""Teach the Machine -- the lessons: shelves, gating and scoring.

The lesson tables themselves are GENERATED (tools/build_lessons.py -> lessons_s1.py, lessons_s2.py, lessons_s3.py ...) from the hand-written
specs in tools/lesson_specs.py and are never edited by hand: each lesson holds its fixed training table, its fixed unseen table, the target
(a whole percent), the starting switches, the proved best set of features and a golden snapshot of the tree that best set grows.

A shelf n+1 opens when OPEN_AT (5) lessons of shelf n are cleared (any five); inside a shelf every lesson is open in any order.
"""

import lessonkit
import lessons_s1
import lessons_s2
import lessons_s3

OPEN_AT = 5
SHELF_INFO = (
    {"id": "basics", "name": "Sorting Basics", "blurb": "One thing decides the answer. Find which."},
    {"id": "two", "name": "Two Features", "blurb": "The answer needs two things at once."},
    {"id": "distractions", "name": "Distractions", "blurb": "More to look at is not always better."},
)
_RAW = (lessons_s1.LESSONS, lessons_s2.LESSONS, lessons_s3.LESSONS)


SHELVES = []
ALL = []
for _s, (_info, _lessons) in enumerate(zip(SHELF_INFO, _RAW)):
    _shelf = dict(_info, index=_s, lessons=[])
    for _n, _raw in enumerate(_lessons):
        _lesson = lessonkit.prepare(_raw, _s, _n + 1)
        _shelf["lessons"].append(_lesson)
        ALL.append(_lesson)
    SHELVES.append(_shelf)
BY_ID = {l["id"]: l for l in ALL}
ORDER = [l["id"] for l in ALL]
TOTAL = len(ALL)
order_set, fit, score, train_score, need_for = lessonkit.order_set, lessonkit.fit, lessonkit.score, lessonkit.train_score, lessonkit.need_for


def shelf_done(cleared, s):
    return sum(1 for l in SHELVES[s]["lessons"] if l["id"] in cleared)


def shelf_need(s):
    return 0 if s == 0 else min(OPEN_AT, len(SHELVES[s - 1]["lessons"]))


def shelf_open(cleared, s):
    return s == 0 or shelf_done(cleared, s - 1) >= shelf_need(s)


def lesson_open(cleared, lid):
    return lid in BY_ID and shelf_open(cleared, BY_ID[lid]["shelf"])


def shelves_finished(cleared):
    return sum(1 for s in range(len(SHELVES)) if shelf_done(cleared, s) == len(SHELVES[s]["lessons"]))
