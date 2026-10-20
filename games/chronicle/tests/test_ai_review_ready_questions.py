"""Tests for review.ready_questions()."""


import review as rv


SAMPLE = "presidents-sample"
LABELS = {"confidence": {k: k for k in ("documented", "disputed", "traditional-but-doubtful")}, "strength": {"direct": "direct", "contributing": "contributing"}}


def everything(sample):
    return {"learned": list(sample.events), "sorted": sample.myth_claim_ids(), "threads": sample.web_relation_ids(),
            "decided": {d["id"]: {"picked": d["chosen"]} for d in sample.decisions}}


def test_ready_questions_returns_due_items_in_schedule_order(sample):
    """Normal case: returns questions for items due on the given day, in schedule order."""
    prog = {k: (set(v) if isinstance(v, list) else v) for k, v in everything(sample).items()}
    srs = {k: rv.new_record() for k in rv.all_keys(sample, prog)}

    keys = rv.all_keys(sample, prog)
    # Make the first two items due on day 0, third due later
    srs[keys[0]]["due"] = 0
    srs[keys[1]]["due"] = 0
    srs[keys[2]]["due"] = 5

    questions = rv.ready_questions(sample, prog, srs, day=0, labels=LABELS)
    returned_keys = [q[0] for q in questions]

    assert keys[0] in returned_keys and keys[1] in returned_keys
    assert keys[2] not in returned_keys
    assert returned_keys.index(keys[0]) < returned_keys.index(keys[1])


def test_ready_questions_respects_limit(sample):
    """Normal case: stops collecting after `limit` valid questions are found."""
    prog = {k: (set(v) if isinstance(v, list) else v) for k, v in everything(sample).items()}
    srs = {k: rv.new_record() for k in rv.all_keys(sample, prog)}

    keys = rv.all_keys(sample, prog)
    for k in keys:
        srs[k]["due"] = 0

    questions = rv.ready_questions(sample, prog, srs, day=0, labels=LABELS, limit=3)
    assert len(questions) == 3


def test_ready_questions_handles_empty_srs_returns_new_items(sample):
    """Edge case: when srs is empty (all items are new), returns them immediately without crashing."""
    prog = {k: (set(v) if isinstance(v, list) else v) for k, v in everything(sample).items()}

    questions = rv.ready_questions(sample, prog, {}, day=0, labels=LABELS)

    assert len(questions) > 0
    all_keys = rv.all_keys(sample, prog)
    for key, _ in questions:
        assert key in all_keys
