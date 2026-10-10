"""FS (FREN152 slides): the catalogue additions keep the farm's old plots, ids and order intact.

Topics added from the 2026 slides carry "-fs" in their id and are appended to the end of their week,
so every original plot id keeps its place (a save written before the additions loads unchanged). The
original 23 weeks / 138 topics / 1047 items / 790 plots are pinned by `tests/fs_baseline.json`.
"""

import json
from pathlib import Path

from .conftest import BASE_COUNTS, catalog_counts

BASELINE = json.loads((Path(__file__).resolve().parent / "fs_baseline.json").read_text(encoding="utf-8"))


def _plot_ids(weeks):
    ids = []
    for week in weeks:
        for topic in week["topics"]:
            if topic["topic_type"] == "grammar":
                ids.append(topic["id"])
            else:
                ids += [f"{topic['id']}-i{i:02d}" for i in range(len(topic["items"]))]
    return ids


def _fs_topics(catalog):
    return [(w["sequence"], t) for w in catalog["weeks"] for t in w["topics"] if "-fs" in t["id"]]


def test_the_original_plots_keep_their_ids_and_order(game_env):
    weeks = game_env.module.CATALOG["weeks"]
    original = _plot_ids([{"topics": [t for t in w["topics"] if "-fs" not in t["id"]]} for w in weeks])
    assert original == BASELINE["plot_ids"]
    assert len(BASELINE["plot_ids"]) == BASE_COUNTS["plots"]


def test_added_topics_sit_after_their_weeks_original_topics(game_env):
    for week in game_env.module.CATALOG["weeks"]:
        flags = ["-fs" in t["id"] for t in week["topics"]]
        assert flags == sorted(flags), week["sequence"]  # False... then True...


def test_original_topics_are_untouched(game_env):
    by_id = {
        t["id"]: (w["sequence"], t["topic_type"], len(t["items"]))
        for w in game_env.module.CATALOG["weeks"]
        for t in w["topics"]
    }
    for seq, tid, kind, count in BASELINE["topics"]:
        assert by_id[tid] == (seq, kind, count), tid


def test_every_added_topic_is_in_the_row_that_matches_its_id(game_env):
    for seq, topic in _fs_topics(game_env.module.CATALOG):
        week_number = int(topic["id"].split("-")[1][1:])
        assert seq == week_number + 10, topic["id"]  # FREN152 week N is farm row N + 10
        assert seq >= 12


def test_added_topics_are_complete_and_ids_are_unique(game_env):
    seen = set()
    for _seq, topic in _fs_topics(game_env.module.CATALOG):
        assert topic["id"] not in seen
        seen.add(topic["id"])
        assert topic["topic_type"] in {"vocab", "phrase", "grammar"}
        assert topic["title"].strip() and topic["items"]
        if topic["topic_type"] == "grammar":
            assert topic.get("rule") and len(topic["items"]) >= 3, topic["id"]
        for item in topic["items"]:
            assert item["fr"].strip() and item["en"].strip(), topic["id"]


def test_farm_headline_counts_add_up(game_env):
    counts = catalog_counts()
    added_topics = _fs_topics(game_env.module.CATALOG)
    assert counts["topics"] == BASE_COUNTS["topics"] + len(added_topics)
    assert counts["items"] == BASE_COUNTS["items"] + sum(len(t["items"]) for _s, t in added_topics)
    plots = sum(1 if t["topic_type"] == "grammar" else len(t["items"]) for _s, t in added_topics)
    assert counts["plots"] == BASE_COUNTS["plots"] + plots
    assert len(game_env.state.plots) == counts["plots"]
