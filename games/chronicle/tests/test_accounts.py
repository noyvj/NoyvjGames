"""Milestone 6, whose account?: passages tied to real sources, graded from fixed options built from source metadata."""

import copy
import json
import re
from pathlib import Path
from urllib.parse import urlparse

import pytest

import account as ac
import achievements
from setdata import ACCOUNT_KINDS, PURPOSES, VANTAGES, load_set_dict, validate

from .conftest import strip_extras

FIXTURES = Path(__file__).resolve().parent / "fixtures"
SAMPLE = "presidents-sample"
LOADED = {"great", "worst", "best", "terrible", "heroic", "villain", "tyrant", "failed", "disgrace", "brilliant", "evil", "corrupt",
          "shameful", "glorious", "noble", "cruel", "wicked", "clever", "genius", "foolish"}


def codes(files):
    return {p.split(":", 1)[0] for p in validate(files)}


def learn_all(p, sample):
    p.m.load_state({"sets": {SAMPLE: {"learned": list(sample.events)}}})


def solve(p, sample, account="a-gettysburg", rnd=0, wrong_first=False):
    p.call("account_start", account=account, round=rnd)
    puz = ac.make_account_puzzle(sample, account, rnd)
    for q in puz.questions:
        choice = q["answer"]
        if wrong_first and q["id"] == "kind":
            choice = [o for o in q["options"] if o != q["answer"]][0]
        p.call("account_answer", question=q["id"], choice=choice)
    r = p.call("account_check")
    if wrong_first:
        for q in puz.questions:
            if q["id"] == "kind":
                p.call("account_answer", question="kind", choice=q["answer"])
        r = p.call("account_check")
    return puz, r


# ---- the sample's accounts: every passage has a source, an author, a date and a kind ----------------------------------

def test_the_sample_has_two_accounts_with_two_or_three_passages_each(sample):
    assert [a["id"] for a in sample.accounts] == ["a-gettysburg", "a-emancipation"]
    for a in sample.accounts:
        assert 2 <= len(a["passages"]) <= 3 and a["event"] in sample.events
    assert len(sample.passage_keys()) == 6


def test_every_passage_has_a_real_source_an_author_a_date_and_a_kind(sample):
    for a in sample.accounts:
        for p in a["passages"]:
            src = sample.sources[p["source"]]
            assert urlparse(src["url"]).scheme == "https" and src["read"] in ("2026-10-07", "2026-10-08") and src["title"]
            assert p["author"].strip() and re.fullmatch(r"[a-z0-9-]+", p["author_id"])
            assert p["kind"] in ACCOUNT_KINDS
            if p["kind"] == "primary":
                assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", p["written"]) and p["written"] <= src["read"]
            else:
                assert p["written"] is None or re.fullmatch(r"\d{4}-\d{2}-\d{2}", p["written"])
            assert p["vantage"] in dict(VANTAGES) and p["purpose"] in dict(PURPOSES) and p["purpose_note"].strip()


def test_each_account_sets_a_primary_source_against_a_secondary_one_from_different_authors(sample):
    for a in sample.accounts:
        assert {p["kind"] for p in a["passages"]} == {"primary", "secondary"}
        assert len({p["author_id"] for p in a["passages"]}) == len(a["passages"])
    assert len(sample.authors()) >= 4


def test_a_primary_source_took_part_or_watched_and_a_secondary_one_wrote_afterwards(sample):
    for a in sample.accounts:
        for p in a["passages"]:
            assert (p["vantage"] == "later") == (p["kind"] == "secondary")


def test_the_two_planned_examples_are_there(sample):
    gett = sample.account("a-gettysburg")
    assert {p["source"] for p in gett["passages"]} == {"miller-gettysburg-address", "mhs-everett-letter", "nps-gett-wills-house"}
    emancipation = sample.account("a-emancipation")
    assert {p["source"] for p in emancipation["passages"]} == {"miller-emancipation-proclamation", "nps-emancipation", "loc-emancipation"}
    assert {p["author_id"] for p in emancipation["passages"]} == {"lincoln", "nps", "loc"}


def test_every_point_is_a_documented_claim_about_the_event_with_three_sources(sample):
    for a in sample.accounts:
        for pt in a["points"]:
            c = sample.claims[pt["claim"]]
            assert c["subject"] == a["event"] and c["confidence"] == "documented" and len(c["sources"]) >= 3
            assert len({r["institution"] for r in sample.resolved_sources(c)}) >= 2


def test_every_passage_source_is_one_of_the_sources_the_set_cites_for_the_event(sample):
    for a in sample.accounts:
        cited = {ref["source"] for pt in a["points"] for ref in sample.claims[pt["claim"]]["sources"]}
        cited |= {ref["source"] for c in sample.claims_for(a["event"]) for ref in c["sources"]}
        for p in a["passages"]:
            assert p["source"] in cited, (a["id"], p["source"])


def test_each_passage_leaves_something_out_or_the_account_has_a_passage_that_does(sample):
    for a in sample.accounts:
        omitted = [ac.omitted_points(a, p) for p in a["passages"]]
        assert any(omitted)
        for p, om in zip(a["passages"], omitted):
            if om:
                assert len(p["mentions"]) >= 2          # so the 'left out' question has at least three options


def test_passages_are_original_short_plain_summaries(sample):
    for a in sample.accounts:
        for p in a["passages"]:
            t = p["text"]
            assert 80 <= len(t) <= 520
            assert '"' not in t and "“" not in t and "”" not in t       # no quoted sentences
            assert "—" not in t and "–" not in t and "!" not in t
            assert not (set(re.findall(r"[a-z]+", t.lower())) & LOADED), (a["id"], p["id"])
            assert not re.search(r"\b(clearly|obviously|undoubtedly|of course)\b", t.lower())
            # a passage never gives its own author or kind away in so many words
            assert p["author"].lower() not in t.lower() and "primary source" not in t.lower() and "secondary source" not in t.lower()


def test_a_passage_is_not_a_copy_of_any_claim_text_or_source_note(sample):
    """A passage may reuse a short phrase of the set's own wording, never a whole sentence of it (and the passages are checked
    by hand against the sources, which this test cannot reach)."""
    def runs(text, n=14):
        words = re.findall(r"[a-z0-9']+", text.lower())
        return {" ".join(words[i:i + n]) for i in range(len(words) - n + 1)}
    pool = set()
    for c in sample.claims.values():
        pool |= runs(c["text"])
        for ref in c["sources"]:
            pool |= runs(ref["note"])
    for a in sample.accounts:
        for p in a["passages"]:
            assert not (runs(p["text"]) & pool), (a["id"], p["id"])


def test_point_labels_and_notes_are_plain(sample):
    for a in sample.accounts:
        for pt in a["points"]:
            assert len(pt["label"]) <= 90 and "—" not in pt["label"] and not (set(re.findall(r"[a-z]+", pt["label"].lower())) & LOADED)
        for p in a["passages"]:
            assert "—" not in p["purpose_note"] and "!" not in p["purpose_note"]


# ---- validation: every rule fails a bad set ---------------------------------------------------------------------------

def passage(raw, aid="a-gettysburg", pid="p1"):
    a = next(x for x in raw["accounts"]["accounts"] if x["id"] == aid)
    return next(p for p in a["passages"] if p["id"] == pid)


def test_the_sample_set_with_its_accounts_is_valid(raw):
    assert validate(raw) == []


@pytest.mark.parametrize("mutate,code", [
    (lambda p: p.update(source="nope"), "E_ACCOUNT_SOURCE"),
    (lambda p: p.update(author=""), "E_ACCOUNT_AUTHOR"),
    (lambda p: p.pop("author_id"), "E_ACCOUNT_AUTHOR"),
    (lambda p: p.update(kind="tertiary"), "E_ACCOUNT_KIND"),
    (lambda p: p.update(vantage="later"), "E_ACCOUNT_KIND"),            # a primary source that 'wrote afterwards'
    (lambda p: p.update(vantage="nope"), "E_ACCOUNT_KIND"),
    (lambda p: p.update(purpose="nope"), "E_ACCOUNT_KIND"),
    (lambda p: p.update(written=None), "E_ACCOUNT_DATE"),               # primary needs the date it was written
    (lambda p: p.update(written="1863-13-45"), "E_ACCOUNT_DATE"),
    (lambda p: p.update(written="2030-01-01"), "E_ACCOUNT_DATE"),      # written after the source was read
    (lambda p: p.update(text="He said \"four score\" and the rest of a long enough sentence to pass the length check easily here."), "E_ACCOUNT_TEXT"),
    (lambda p: p.update(text="Too short."), "E_ACCOUNT_TEXT"),
    (lambda p: p.update(purpose_note=""), "E_ACCOUNT_TEXT"),
    (lambda p: p.update(mentions=["no-such-point"]), "E_ACCOUNT_MENTIONS"),
    (lambda p: p.update(mentions=[]), "E_ACCOUNT_MENTIONS"),
    (lambda p: p.update(mentions=["ceremony"]), "E_ACCOUNT_MENTIONS"),  # one point only: fewer than three 'left out' options
])
def test_bad_passages_fail(raw, mutate, code):
    mutate(passage(raw))
    assert code in codes(raw)


def test_a_source_without_a_read_date_or_url_fails_the_account(raw):
    raw["sources"]["miller-gettysburg-address"].pop("read")
    assert "E_ACCOUNT_SOURCE" in codes(raw) or "E_SOURCE_FIELD" in codes(raw)
    assert "E_SOURCE_FIELD" in codes(raw)


def test_an_account_needs_two_passages_one_of_each_kind_and_different_authors(raw):
    acc = raw["accounts"]["accounts"][1]
    acc["passages"] = acc["passages"][:1]
    assert "E_ACCOUNT" in codes(raw)
    raw2 = copy.deepcopy(raw)
    for p in raw2["accounts"]["accounts"][0]["passages"]:
        p["kind"], p["vantage"] = "primary", "took-part"
    assert "E_ACCOUNT_KIND" in codes(raw2)
    raw3 = copy.deepcopy(raw)
    raw3["accounts"]["accounts"][0]["passages"][1]["author_id"] = raw3["accounts"]["accounts"][0]["passages"][0]["author_id"]
    raw3["accounts"]["accounts"][0]["passages"][1]["author"] = raw3["accounts"]["accounts"][0]["passages"][0]["author"]
    assert "E_ACCOUNT_AUTHOR" in codes(raw3)


def test_an_account_where_nothing_is_left_out_fails(raw):
    acc = raw["accounts"]["accounts"][0]
    every = [pt["id"] for pt in acc["points"]]
    for p in acc["passages"]:
        p["mentions"] = list(every)
    assert "E_ACCOUNT_MENTIONS" in codes(raw)


def test_the_set_needs_four_different_authors_for_four_options(raw):
    for a in raw["accounts"]["accounts"]:
        for p in a["passages"]:
            if p["author_id"] == "everett":
                p["author_id"], p["author"] = "lincoln", "Abraham Lincoln"
    assert "E_ACCOUNT_OPTIONS" in codes(raw) or "E_ACCOUNT_AUTHOR" in codes(raw)


def test_an_author_written_two_ways_fails(raw):
    passage(raw, "a-emancipation", "p1")["author"] = "A. Lincoln"
    assert "E_ACCOUNT_AUTHOR" in codes(raw)


@pytest.mark.parametrize("mutate", [
    lambda raw: raw["accounts"]["accounts"][0]["points"][1].update(claim="no-such-claim"),
    lambda raw: raw["accounts"]["accounts"][0]["points"][1].update(claim="c-e-washington-oath-date"),       # a claim about another event
    lambda raw: raw["accounts"]["accounts"][0]["points"][0].update(claim="c-e-gettysburg-tradition"),       # not documented
])
def test_a_point_must_be_a_documented_claim_about_the_accounts_event(raw, mutate):
    mutate(raw)
    assert "E_ACCOUNT_POINT" in codes(raw)


def test_a_point_claim_still_needs_three_sources(raw):
    claim = next(c for c in raw["claims"] if c["id"] == "c-a-gettysburg-speakers")
    claim["sources"] = claim["sources"][:2]
    assert "E_CLAIM_SOURCES" in codes(raw)


def test_a_stray_account_claim_fails(raw):
    raw["accounts"]["accounts"][0]["points"] = [pt for pt in raw["accounts"]["accounts"][0]["points"] if pt["id"] != "copies"]
    for p in raw["accounts"]["accounts"][0]["passages"]:
        p["mentions"] = [m for m in p["mentions"] if m != "copies"]
    assert "E_ACCOUNT_POINT" in codes(raw)          # c-a-gettysburg-copies is now used by no point
    raw2 = copy.deepcopy(raw)
    raw2.pop("accounts")
    assert "E_ACCOUNT_POINT" in codes(raw2)


def test_malformed_accounts_file_is_reported_not_raised(raw):
    for junk in ([], {"accounts": "x"}, {"accounts": [5]}, {"accounts": [{"id": "x"}]}, {"other": 1}):
        raw["accounts"] = junk
        assert codes(raw)                              # some problem is reported, nothing raises


def test_a_set_without_accounts_is_still_valid_and_has_no_account_mode(raw):
    strip_extras(raw)
    assert validate(raw) == []
    cset = load_set_dict(raw)
    assert cset.accounts == [] and cset.passage_keys() == [] and cset.authors() == {}


# ---- deterministic puzzles -----------------------------------------------------------------------------------------

def test_account_puzzles_are_pinned_by_a_fixture(sample):
    fixture = json.loads((FIXTURES / "account_puzzles_v1.json").read_text(encoding="utf-8"))
    assert fixture["seed_version"] == ac.SEED_VERSION and len(fixture["puzzles"]) == 12
    for code, want in fixture["puzzles"].items():
        _s, account, rnd = code.split("/")
        got = ac.make_account_puzzle(sample, account, int(rnd))
        assert got.order == want["order"] and got.focus == want["focus"], code
        assert [{"id": q["id"], "options": q["options"], "answer": q["answer"]} for q in got.questions] == want["questions"], code


def test_the_same_inputs_give_the_same_puzzle_and_rounds_differ(sample):
    assert ac.make_account_puzzle(sample, "a-emancipation", 4).to_dict() == ac.make_account_puzzle(sample, "a-emancipation", 4).to_dict()
    assert len({json.dumps(ac.make_account_puzzle(sample, "a-gettysburg", r).to_dict()["questions"]) for r in range(9)}) > 3


def test_the_first_rounds_visit_every_passage_so_judging_everything_is_reachable(sample):
    for a in sample.accounts:
        focused = [ac.make_account_puzzle(sample, a["id"], r).focus for r in range(ac.main_rounds(sample, a["id"]))]
        assert sorted(focused) == sorted(p["id"] for p in a["passages"])


def test_the_display_order_is_one_seeded_shuffle_per_account(sample):
    for a in sample.accounts:
        order = ac.display_order(sample, a["id"])
        assert sorted(order) == sorted(p["id"] for p in a["passages"])
        assert all(ac.make_account_puzzle(sample, a["id"], r).order == order for r in range(6))


def test_every_question_is_a_fixed_list_built_from_the_passages_own_metadata(sample):
    for a in sample.accounts:
        by_id = {p["id"]: p for p in a["passages"]}
        for r in range(12):
            puz = ac.make_account_puzzle(sample, a["id"], r)
            focus = by_id[puz.focus]
            q = {x["id"]: x for x in puz.questions}
            assert q["who"]["answer"] == focus["author_id"] and len(q["who"]["options"]) == 4 and len(set(q["who"]["options"])) == 4
            assert set(q["who"]["options"]) <= set(sample.authors())
            assert q["kind"]["options"] == list(ACCOUNT_KINDS) and q["kind"]["answer"] == focus["kind"]
            assert q["vantage"]["options"] == [v[0] for v in VANTAGES] and q["vantage"]["answer"] == focus["vantage"]
            assert q["purpose"]["options"] == [v[0] for v in PURPOSES] and q["purpose"]["answer"] == focus["purpose"]
            for qq in puz.questions:
                assert qq["answer"] in qq["options"]
            if "left_out" in q:
                lo = q["left_out"]
                assert lo["answer"] not in focus["mentions"] and 3 <= len(lo["options"]) <= 4
                assert [o for o in lo["options"] if o not in focus["mentions"]] == [lo["answer"]]   # exactly one right option
                assert set(lo["options"]) - {lo["answer"]} <= set(focus["mentions"])
            else:
                assert not ac.omitted_points(a, focus)


def test_left_out_questions_rotate_through_everything_a_passage_omits(sample):
    a = sample.account("a-gettysburg")
    puz = {r: ac.make_account_puzzle(sample, "a-gettysburg", r) for r in range(12)}
    for pid in (p["id"] for p in a["passages"]):
        seen = {q["answer"] for pz in puz.values() if pz.focus == pid for q in pz.questions if q["id"] == "left_out"}
        omitted = set(ac.omitted_points(a, next(p for p in a["passages"] if p["id"] == pid)))
        assert seen <= omitted
    assert any(len({q["answer"] for pz in puz.values() if pz.focus == pid for q in pz.questions if q["id"] == "left_out"}) > 1
               for pid in (p["id"] for p in a["passages"]))


def test_bad_inputs_raise_value_error(sample):
    for account, rnd in (("zz", 0), ("a-gettysburg", -1), ("a-gettysburg", False), ("a-gettysburg", None), ("a-gettysburg", 1.5)):
        with pytest.raises(ValueError):
            ac.make_account_puzzle(sample, account, rnd)


def test_grading(sample):
    puz = ac.make_account_puzzle(sample, "a-gettysburg", 0)
    right = puz.answer()
    assert ac.grade(puz, right)["all_right"] is True
    wrong = dict(right)
    wrong["kind"] = [o for o in ACCOUNT_KINDS if o != right["kind"]][0]
    g = ac.grade(puz, wrong)
    assert g["right"] == puz.size - 1 and [r["status"] for r in g["questions"]].count("wrong") == 1
    assert ac.grade(puz, {})["placed"] == 0 and {r["status"] for r in ac.grade(puz, {})["questions"]} == {"empty"}


def test_option_labels_come_from_the_sets_own_data(sample):
    assert ac.option_label(sample, "a-gettysburg", "who", "lincoln") == "Abraham Lincoln"
    assert ac.option_label(sample, "a-gettysburg", "kind", "primary").startswith("Primary source")
    assert ac.option_label(sample, "a-gettysburg", "left_out", "copies") == "How many handwritten copies of the speech survive"
    assert ac.option_label(sample, "a-gettysburg", "vantage", "later") == dict(VANTAGES)["later"]


# ---- the engine -------------------------------------------------------------------------------------------------------

def test_the_mode_is_listed_and_locked_until_the_event_is_learned(p, sample):
    v = p.call("mode", mode="account")["view"]
    assert [m["id"] for m in v["modes"]] == ["timeline", "web", "myth", "account", "decision", "review"] and v["modes"][3]["available"]
    assert v["mode"] == "account" and v["account"]["locked"] is True and [a["unlocked"] for a in v["accounts"]] == [False, False]
    assert p.call("account_start", account="a-gettysburg")["ok"] is False
    p.m.load_state({"sets": {SAMPLE: {"learned": ["e-gettysburg"]}}})
    v = p.call("boot")["view"]
    assert [a["unlocked"] for a in v["accounts"]] == [True, False] and v["account"]["id"] == "presidents-sample/a-gettysburg/0"
    assert p.call("account_start", account="a-emancipation")["ok"] is False


def test_the_board_hides_every_answer_the_source_and_the_author_until_it_is_finished(p, sample):
    learn_all(p, sample)
    p.call("mode", mode="account")
    v = p.call("boot")["view"]["account"]
    text = json.dumps(v)
    assert v["result"] is None and len(v["passages"]) == 3 and sum(1 for x in v["passages"] if x["focus"]) == 1
    assert '"answer"' not in text
    for secret in ("author", "miller-gettysburg-address", "millercenter", "masshist", "nps.gov", "mentions", "leaves_out",
                   "purpose_note", "claim", "written_label", "kind_label", '"source"', '"read"'):
        assert secret not in text, secret
    for q in v["questions"]:
        assert set(o for o in q) >= {"id", "prompt", "options", "choice", "locked", "status"} and q["choice"] is None
    # the passage letters and the prompts name the focus passage, nothing else
    assert v["focus_letter"] in text and "Passage %s" % v["focus_letter"] in v["questions"][0]["prompt"]


def test_right_answers_lock_wrong_ones_do_not_say_which_is_right_and_all_right_judges_the_source(p, sample):
    learn_all(p, sample)
    puz, r = solve(p, sample, wrong_first=True)
    v = r["view"]["account"]
    assert v["status"] == "solved" and v["checks"] == 2 and "2 checks" in v["message"]
    assert "%s/%s" % ("a-gettysburg", puz.focus) in p.m.S["sets"][SAMPLE]["judged"]
    assert p.m.S["sets"][SAMPLE]["asolved"]["a-gettysburg:0"] == {"checks": 2}
    assert r["new"] and "first_source" in p.m.get_state()["achievements_earned"]
    assert v["result"]["solved"] and v["result"]["new_count"] == 1 and len(v["result"]["passages"]) == 3


def test_a_wrong_check_locks_only_the_right_answers_and_never_names_the_right_one(p, sample):
    learn_all(p, sample)
    p.call("account_start", account="a-gettysburg", round=0)
    puz = ac.make_account_puzzle(sample, "a-gettysburg", 0)
    for q in puz.questions:
        wrong = [o for o in q["options"] if o != q["answer"]][0] if q["id"] in ("kind", "who") else q["answer"]
        p.call("account_answer", question=q["id"], choice=wrong)
    r = p.call("account_check")
    v = r["view"]["account"]
    by = {q["id"]: q for q in v["questions"]}
    assert by["kind"]["status"] == "wrong" and by["who"]["status"] == "wrong" and by["purpose"]["locked"] is True
    assert v["status"] == "playing" and v["result"] is None and "answer" not in json.dumps(v["questions"])
    assert "of %d answers are right and locked" % puz.size in v["message"] and "%d of %d" % (puz.size - 2, puz.size) in v["message"]
    assert p.call("account_answer", question="purpose", choice="persuade")["ok"] is False        # a locked answer cannot change
    assert p.m.S["sets"][SAMPLE]["judged"] == set()


def test_check_needs_every_question_answered_and_options_are_validated(p, sample):
    learn_all(p, sample)
    p.call("account_start", account="a-gettysburg", round=0)
    assert p.call("account_check")["ok"] is False
    assert p.call("account_answer", question="nope", choice="x")["ok"] is False
    assert p.call("account_answer", question="kind", choice="tertiary")["ok"] is False
    assert p.call("account_answer", question="kind", choice="primary")["ok"] is True
    assert p.call("account_answer", question="kind", choice="primary")["dirty"] is False
    assert p.call("account_answer", question="kind", choice=None)["ok"] is True
    assert p.call("account_start", account="a-gettysburg", round=-1)["ok"] is False
    assert p.call("account_start", account="zz")["ok"] is False


def test_show_the_answers_reveals_but_learns_nothing(p, sample):
    learn_all(p, sample)
    p.call("account_start", account="a-gettysburg", round=0)
    r = p.call("account_show")
    v = r["view"]["account"]
    assert v["status"] == "revealed" and v["result"]["solved"] is False and "Nothing was added" in v["message"]
    assert p.m.S["sets"][SAMPLE]["judged"] == set() and p.m.S["sets"][SAMPLE]["asolved"] == {}
    assert p.call("account_check")["ok"] is False and p.call("account_answer", question="kind", choice="primary")["ok"] is False
    assert p.call("account_next")["ok"] is True


def test_the_reveal_names_every_passage_source_with_its_link_and_read_date(p, sample):
    learn_all(p, sample)
    solve(p, sample)
    res = p.call("boot")["view"]["account"]["result"]
    kinds = set()
    for ps in res["passages"]:
        assert ps["author"] and ps["kind_label"] and ps["vantage_label"] and ps["purpose_label"] and ps["purpose_note"]
        assert ps["source"]["url"].startswith("https://") and ps["source"]["read"] in ("2026-10-07", "2026-10-08") and ps["source"]["institution"]
        assert ps["mentions"] and "written_label" in ps
        kinds.add(ps["kind"])
    assert kinds == {"primary", "secondary"}
    undated = [ps for ps in res["passages"] if "undated" in ps["written_label"]]
    assert undated and all(ps["kind"] == "secondary" for ps in undated)
    for pt in res["points"]:
        assert len(pt["claim"]["sources"]) >= 3 and pt["claim"]["confidence_label"]


def test_next_moves_on_and_every_passage_can_be_judged_to_clear_the_account(p, sample):
    learn_all(p, sample)
    for rnd in range(3):
        solve(p, sample, rnd=rnd)
    v = p.call("boot")["view"]
    assert v["accounts"][0]["cleared"] is True and v["accounts"][0]["progress"] == "Judged 3 of 3 sources"
    assert v["account"]["result"]["account_cleared"] is True
    r = p.call("account_next")
    assert r["view"]["account"]["round"] == 3 and "Practice puzzle" in r["view"]["account"]["round_label"]
    solve(p, sample, "a-emancipation", 0)
    p.call("account_start", account="a-emancipation", round=1)
    assert p.call("account_next")["view"]["account"]["round"] == 2


def test_the_archive_meter_counts_passages_and_lists_them(p, sample):
    learn_all(p, sample)
    before = p.call("boot")["view"]["set"]["found"]
    solve(p, sample)
    assert p.call("boot")["view"]["set"]["found"] == before + 1
    a = p.call("archive")["archive"]
    group = next(g for g in a["groups"] if g["id"] == "sources")
    assert len(group["entries"]) == 6 and sum(1 for e in group["entries"] if e["found"]) == 1
    hidden = [e for e in group["entries"] if not e["found"]]
    assert all(e["title"] is None and e["hint"] == "Whose account?" for e in hidden)
    found = next(e for e in group["entries"] if e["found"])
    entry = p.call("entry", id=found["id"])["entry"]
    assert entry["kind"] == "account" and entry["passage"]["source"]["url"] and entry["points"]
    assert p.call("entry", id=hidden[0]["id"])["ok"] is False


def test_account_claims_can_be_opened_only_after_the_account_is_judged_or_shown(p, sample):
    learn_all(p, sample)
    assert p.call("view_claim", claim="c-a-gettysburg-speakers")["ok"] is False
    p.call("account_start", account="a-gettysburg", round=0)
    p.call("account_show")
    assert p.call("view_claim", claim="c-a-gettysburg-speakers")["ok"] is True
    assert p.call("view_claim", claim="c-a-emancipation-covered")["ok"] is False


def test_account_claims_never_appear_in_the_plain_event_reveal(p, sample):
    learn_all(p, sample)
    entry = p.call("entry", id="e-gettysburg")["entry"]
    assert {c["id"] for c in [entry["claim"]] + entry["other_claims"]} == {"c-e-gettysburg-date", "c-e-gettysburg-tradition", "c-e-gettysburg-final-revision"}
    info = p.call("info")["info"]
    shown = {c["id"] for f in info["found_claims"] for c in f["claims"]}
    assert not {cid for cid in shown if cid.startswith("c-a-") or cid.startswith("c-d-")}


def test_the_info_page_lists_judged_accounts_with_their_facts_and_counts(p, sample):
    learn_all(p, sample)
    info = p.call("info")["info"]
    assert info["counts"]["accounts"] == 2 and info["counts"]["passages"] == 6 and info["counts"]["decisions"] == 3
    assert info["found_accounts"] == [] and [k["id"] for k in info["account_kinds"]] == ["primary", "secondary"]
    solve(p, sample)
    info = p.call("info")["info"]
    assert [a["judged"] for a in info["found_accounts"]] == [1] and len(info["found_accounts"][0]["points"]) == 5
    assert info["coverage"]["shown"] == len({c["id"] for f in info["found_claims"] for c in f["claims"]} | {pt["claim"]["id"] for pt in info["found_accounts"][0]["points"]})


def test_reporting_an_account_claim_builds_the_same_payload(p, sample):
    r = p.call("report", claim="c-a-gettysburg-speakers", reason="wrong_fact", note="check")
    assert r["ok"] and r["report"]["claim_id"] == "c-a-gettysburg-speakers" and r["sent"] is False and len(r["report"]["source_urls"]) >= 3


# ---- achievements ---------------------------------------------------------------------------------------------------

def test_account_achievements_are_computed_from_state(p, sample):
    learn_all(p, sample)
    solve(p, sample, rnd=0)
    earned = set(p.m.get_state()["achievements_earned"])
    assert {"first_source", "careful_reader"} <= earned and "both_kinds" not in earned and "every_account" not in earned
    primary = [r for r in range(3) if sample.passage("a-gettysburg", ac.make_account_puzzle(sample, "a-gettysburg", r).focus)["kind"] == "primary"]
    secondary = [r for r in range(3) if r not in primary]
    for r in (primary[0], secondary[0]):
        solve(p, sample, rnd=r)
    assert "both_kinds" in p.m.get_state()["achievements_earned"]
    for r in range(3):
        solve(p, sample, rnd=r)
    for r in range(3):
        solve(p, sample, "a-emancipation", r)
    assert "every_account" in p.m.get_state()["achievements_earned"]


def test_careful_reader_needs_a_single_check(p, sample):
    learn_all(p, sample)
    solve(p, sample, wrong_first=True)
    earned = set(p.m.get_state()["achievements_earned"])
    assert "first_source" in earned and "careful_reader" not in earned


# ---- save and load -------------------------------------------------------------------------------------------------

def test_account_progress_round_trips_and_an_older_save_still_loads(p, sample):
    learn_all(p, sample)
    solve(p, sample)
    state = copy.deepcopy(p.m.get_state())
    assert state["schema"] == 3 and state["sets"][SAMPLE]["judged"] and state["sets"][SAMPLE]["account_solved"]
    p.m.reset_engine()
    assert p.m.load_state(state) is True
    assert p.m.get_state()["sets"] == state["sets"] and p.m.get_state()["achievements_earned"] == state["achievements_earned"]
    old = {"schema": 2, "sets": {SAMPLE: {"learned": ["e-gettysburg"], "solved": {}, "revealed": [], "threads": [], "sorted": [],
                                           "web_solved": {}, "myth_solved": {}}}, "viewed": [], "settings": {}, "flags": {}}
    p.m.reset_engine()
    assert p.m.load_state(old) is True
    prog = p.m.S["sets"][SAMPLE]
    assert prog["learned"] == {"e-gettysburg"} and prog["judged"] == set() and prog["decided"] == {} and prog["srs"] == {} and p.m.S["day"] == 0


def test_a_session_in_progress_resumes(p, sample):
    learn_all(p, sample)
    p.call("account_start", account="a-gettysburg", round=1)
    puz = ac.make_account_puzzle(sample, "a-gettysburg", 1)
    p.call("account_answer", question="kind", choice=puz.questions[1]["answer"])
    state = copy.deepcopy(p.m.get_state())
    p.m.reset_engine()
    p.m.load_state(state)
    v = p.call("mode", mode="account")["view"]["account"]
    assert v["round"] == 1 and {q["id"]: q["choice"] for q in v["questions"]}["kind"] == puz.questions[1]["answer"]


def test_a_hostile_account_session_is_dropped(p, sample):
    learn_all(p, sample)
    p.call("account_start", account="a-gettysburg", round=0)
    good = copy.deepcopy(p.m.get_state()["account_session"])
    puz = ac.make_account_puzzle(sample, "a-gettysburg", 0)
    bad = []
    x = copy.deepcopy(good); x["answers"] = ["nope"] * puz.size; bad.append(x)
    x = copy.deepcopy(good); x["locked"] = [True] * puz.size; bad.append(x)                 # locked but unanswered
    x = copy.deepcopy(good); x["answers"] = [q["options"][0] for q in puz.questions]; x["locked"] = [True] * puz.size; bad.append(x)   # locked on a wrong answer
    x = copy.deepcopy(good); x["status"] = "solved"; bad.append(x)
    x = copy.deepcopy(good); x["round"] = -2; bad.append(x)
    x = copy.deepcopy(good); x["round"] = 10 ** 9; bad.append(x)
    x = copy.deepcopy(good); x["account"] = "zz"; bad.append(x)
    x = copy.deepcopy(good); x["marks"] = ["boom"] * puz.size; bad.append(x)
    x = copy.deepcopy(good); x["checks"] = -1; bad.append(x)
    x = copy.deepcopy(good); x["answers"] = x["answers"][:2]; bad.append(x)
    for s in bad:
        assert p.m._clean_asession(s) is None, s
    p.m.S["sets"][SAMPLE]["learned"].clear()
    assert p.m._clean_asession(good) is None            # the account is locked again


def test_garbage_in_the_new_fields_never_raises_and_good_fields_survive(p, sample):
    learn_all(p, sample)
    solve(p, sample)
    before = copy.deepcopy(p.m.get_state()["sets"])
    junk = {"sets": {SAMPLE: {"judged": "no", "account_solved": {"zz:1": {"checks": 1}, "a-gettysburg:x": {"checks": 1}, "a-gettysburg:1": {"checks": True}},
                               "decided": [1], "srs": 5}}, "account_session": 7, "decision_session": [], "day": "x"}
    p.m.load_state(junk)
    assert p.m.get_state()["sets"] == before
    p.m.load_state({"sets": {SAMPLE: {"judged": ["a-gettysburg/p1", "a-gettysburg/zz", 7, None, "x"],
                                       "account_solved": {"a-emancipation:2": {"checks": 4}}}}})
    prog = p.m.S["sets"][SAMPLE]
    assert "a-gettysburg/zz" not in prog["judged"] and prog["asolved"]["a-emancipation:2"] == {"checks": 4}


def test_solved_account_puzzles_keep_the_fewer_checks(p):
    p.m.load_state({"sets": {SAMPLE: {"account_solved": {"a-gettysburg:0": {"checks": 5}}}}})
    p.m.load_state({"sets": {SAMPLE: {"account_solved": {"a-gettysburg:0": {"checks": 2}}}}})
    p.m.load_state({"sets": {SAMPLE: {"account_solved": {"a-gettysburg:0": {"checks": 9}}}}})
    assert p.m.S["sets"][SAMPLE]["asolved"]["a-gettysburg:0"] == {"checks": 2}


def test_progress_for_a_set_this_build_lacks_keeps_the_new_fields(p):
    p.m.load_state({"sets": {"future-set": {"learned": ["a"], "judged": ["x/y"], "decided": {"d1": {"picked": "o"}}}}})
    out = p.m.get_state()["sets"]["future-set"]
    assert out["judged"] == ["x/y"] and out["decided"] == {"d1": {"picked": "o"}}


def test_a_set_without_accounts_has_no_account_mode(p, g, raw):
    strip_extras(raw)
    raw["meta"]["id"] = "plain"
    g.register_set(load_set_dict(raw))
    g.S["settings"]["set"] = "plain"
    g.S["session"] = None
    v = p.call("boot")["view"]
    assert v["modes"][3]["available"] is False and v["accounts"] == [] and v["decisions"] == []
    assert p.call("mode", mode="account")["ok"] is False and p.call("mode", mode="decision")["ok"] is False
    assert p.call("account_start", account="a-gettysburg")["ok"] is False
    assert p.call("mode", mode="review")["ok"] is True


def test_the_manifest_lists_the_new_achievements_and_all_are_reachable():
    for aid in ("first_source", "both_kinds", "careful_reader", "every_account", "first_decision", "every_crossroads", "first_recall", "long_memory"):
        assert aid in achievements.IDS
    data = json.loads((Path(__file__).resolve().parent.parent / "achievements.json").read_text(encoding="utf-8"))["achievements"]
    assert [a["id"] for a in data] == achievements.IDS
