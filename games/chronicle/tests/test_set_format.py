"""The set format's validation: every rule the project promises about evidence must FAIL a bad set."""

import pytest

import setdata
from setdata import SetError, load_set_dict, validate


def codes(files):
    return {p.split(":", 1)[0] for p in validate(files)}


def test_the_sample_set_is_valid(raw):
    assert validate(raw) == []
    assert load_set_dict(raw).id == "presidents-sample"


def claim(raw, cid):
    return next(c for c in raw["claims"] if c["id"] == cid)


DATE_CLAIM = "c-e-washington-oath-date"


# ---- sources: at least three, each with title, institution, URL and read date -------------------------------

@pytest.mark.parametrize("keep", [0, 1, 2])
def test_a_claim_with_fewer_than_three_sources_fails(raw, keep):
    claim(raw, DATE_CLAIM)["sources"] = claim(raw, DATE_CLAIM)["sources"][:keep]
    assert "E_CLAIM_SOURCES" in codes(raw)


def test_a_missing_sources_list_fails(raw):
    del claim(raw, DATE_CLAIM)["sources"]
    assert "E_CLAIM_SOURCES" in codes(raw)


def test_a_source_with_a_missing_url_fails(raw):
    sid = claim(raw, DATE_CLAIM)["sources"][0]["source"]
    del raw["sources"][sid]["url"]
    found = codes(raw)
    assert "E_SOURCE_FIELD" in found and "E_CLAIM_SOURCE_INCOMPLETE" in found


@pytest.mark.parametrize("bad", ["", "not a url", "ftp://example.org/x", "https://", "javascript:alert(1)"])
def test_a_source_with_an_invalid_url_fails(raw, bad):
    sid = claim(raw, DATE_CLAIM)["sources"][0]["source"]
    raw["sources"][sid]["url"] = bad
    assert "E_SOURCE_FIELD" in codes(raw)


@pytest.mark.parametrize("bad", [None, "", "yesterday", "2026-13-01", "2026-02-30", "07/10/2026"])
def test_a_source_with_a_missing_or_invalid_read_date_fails(raw, bad):
    sid = claim(raw, DATE_CLAIM)["sources"][0]["source"]
    if bad is None:
        del raw["sources"][sid]["read"]
    else:
        raw["sources"][sid]["read"] = bad
    found = codes(raw)
    assert "E_SOURCE_FIELD" in found and "E_CLAIM_SOURCE_INCOMPLETE" in found


@pytest.mark.parametrize("field", ["title", "institution"])
def test_a_source_needs_a_title_and_an_institution_or_author(raw, field):
    sid = claim(raw, DATE_CLAIM)["sources"][0]["source"]
    del raw["sources"][sid][field]
    assert "E_SOURCE_FIELD" in codes(raw)


def test_an_author_can_stand_in_for_an_institution(raw):
    sid = claim(raw, DATE_CLAIM)["sources"][0]["source"]
    raw["sources"][sid]["author"] = raw["sources"][sid].pop("institution")
    assert validate(raw) == []


def test_the_same_source_cited_twice_does_not_count_twice(raw):
    c = claim(raw, DATE_CLAIM)
    c["sources"][2] = dict(c["sources"][0])
    found = codes(raw)
    assert "E_CLAIM_SOURCES" in found


def test_two_source_ids_with_one_url_do_not_count_twice(raw):
    c = claim(raw, DATE_CLAIM)
    a, b = c["sources"][0]["source"], c["sources"][1]["source"]
    raw["sources"][b]["url"] = raw["sources"][a]["url"]
    assert "E_CLAIM_SOURCES" in codes(raw)


def test_three_sources_from_one_institution_fail(raw):
    c = claim(raw, DATE_CLAIM)
    for ref in c["sources"]:
        raw["sources"][ref["source"]]["institution"] = "One Institution"
    assert "E_CLAIM_INSTITUTIONS" in codes(raw)


def test_an_unknown_source_id_fails(raw):
    claim(raw, DATE_CLAIM)["sources"][0]["source"] = "nope"
    assert "E_CLAIM_SOURCES" in codes(raw)


def test_a_source_must_say_what_it_confirms(raw):
    claim(raw, DATE_CLAIM)["sources"][0]["note"] = ""
    assert "E_CLAIM_SOURCES" in codes(raw)


def test_more_than_three_sources_is_fine(raw):
    c = claim(raw, DATE_CLAIM)
    spare = next(s for s in raw["sources"] if s not in {r["source"] for r in c["sources"]})
    c["sources"].append({"source": spare, "note": "extra"})
    assert validate(raw) == []


# ---- confidence --------------------------------------------------------------------------------------------

def test_confidence_must_be_one_of_the_three_levels(raw):
    claim(raw, DATE_CLAIM)["confidence"] = "certain"
    assert "E_CLAIM" in codes(raw)


@pytest.mark.parametrize("level", ["disputed", "traditional-but-doubtful"])
def test_a_disputed_or_doubtful_claim_must_list_alternatives(raw, level):
    c = claim(raw, DATE_CLAIM)
    c["confidence"] = level
    assert "E_CLAIM" in codes(raw)
    c["alternatives"] = ["Another reading of the evidence."]
    assert validate(raw) == []


# ---- contradictions ----------------------------------------------------------------------------------------

def test_two_claims_that_disagree_fail(raw):
    twin = dict(claim(raw, DATE_CLAIM), id="c-twin", value="1789-05-01", text="George Washington took the oath on May 1, 1789, at Federal Hall in New York City.")
    raw["claims"].append(twin)
    assert "E_CONTRADICTION" in codes(raw)


def test_a_repeated_claim_for_one_field_fails(raw):
    raw["claims"].append(dict(claim(raw, DATE_CLAIM), id="c-twin"))
    assert "E_CONTRADICTION" in codes(raw)


def test_different_fields_of_one_subject_may_coexist(raw):
    # the sample already has three claims about the Gettysburg Address (date, tradition, final revision)
    assert len([c for c in raw["claims"] if c["subject"] == "e-gettysburg"]) == 3
    assert validate(raw) == []


def test_a_mutual_cause_relation_fails(raw):
    raw["claims"].append({"id": "c-rel", "subject": "e-fort-sumter", "field": "relation", "value": "led_to",
                          "text": "A led to B.", "confidence": "documented", "sources": claim(raw, DATE_CLAIM)["sources"]})
    raw["relations"] = [
        {"id": "r1", "from": "e-fort-sumter", "to": "e-emancipation", "type": "led_to", "strength": "direct", "claim": "c-rel"},
        {"id": "r2", "from": "e-emancipation", "to": "e-fort-sumter", "type": "led_to", "strength": "direct", "claim": "c-rel"},
    ]
    found = codes(raw)
    assert "E_RELATION_CONTRADICTION" in found
    assert "E_RELATION_ORDER" in found      # r2 also has the effect before its cause


def test_a_relation_where_the_cause_comes_after_the_effect_fails(raw):
    raw["claims"].append({"id": "c-rel", "subject": "e-fort-sumter", "field": "relation", "value": "led_to",
                          "text": "A led to B.", "confidence": "documented", "sources": claim(raw, DATE_CLAIM)["sources"]})
    raw["relations"] = [{"id": "r1", "from": "e-emancipation", "to": "e-fort-sumter", "type": "led_to", "strength": "direct", "claim": "c-rel"}]
    assert "E_RELATION_ORDER" in codes(raw)


def test_a_valid_relation_with_a_sourced_claim_passes(raw):
    raw["claims"].append({"id": "c-rel", "subject": "e-fort-sumter", "field": "relation", "value": "led_to",
                          "text": "A led to B.", "confidence": "documented", "sources": claim(raw, DATE_CLAIM)["sources"]})
    raw["relations"] = [{"id": "r1", "from": "e-fort-sumter", "to": "e-emancipation", "type": "led_to", "strength": "contributing", "claim": "c-rel"}]
    assert validate(raw) == []


def test_a_relation_without_a_claim_fails(raw):
    raw["relations"] = [{"id": "r1", "from": "e-fort-sumter", "to": "e-emancipation", "type": "led_to", "strength": "direct", "claim": "missing"}]
    assert "E_RELATION" in codes(raw)


# ---- dates and order ---------------------------------------------------------------------------------------

def event(raw, eid):
    return next(e for e in raw["entities"]["events"] if e["id"] == eid)


def test_an_event_whose_date_has_no_claim_fails(raw):
    raw["claims"] = [c for c in raw["claims"] if c["id"] != DATE_CLAIM]
    assert "E_EVENT_NO_CLAIM" in codes(raw)


def test_an_event_date_that_disagrees_with_its_claim_fails(raw):
    event(raw, "e-washington-oath")["date"] = "1789-04-29"
    assert "E_EVENT_DATE_CLAIM" in codes(raw)


@pytest.mark.parametrize("bad", ["", "17", "1789-4-30", "1789-13-01", "1789-02-30", "0000", "abc", None])
def test_a_missing_or_malformed_event_date_fails(raw, bad):
    e = event(raw, "e-washington-oath")
    if bad is None:
        del e["date"]
    else:
        e["date"] = bad
    assert "E_EVENT_DATE" in codes(raw)


def test_events_whose_order_disagrees_with_their_dates_fail(raw):
    a, b = event(raw, "e-washington-oath"), event(raw, "e-farewell")
    a["seq"], b["seq"] = b["seq"], a["seq"]
    assert "E_ORDER" in codes(raw)


def test_two_events_sharing_a_seq_fail(raw):
    event(raw, "e-farewell")["seq"] = event(raw, "e-washington-oath")["seq"]
    assert "E_ORDER" in codes(raw)


def test_a_range_event_needs_start_before_end(raw):
    e = event(raw, "e-removal-act")
    del e["date"]
    e["start"], e["end"] = "1830-05-28", "1830-05-01"
    assert "E_EVENT_DATE" in codes(raw)


def test_a_range_event_is_ordered_by_its_start_and_its_claim_carries_both_ends(raw):
    e = event(raw, "e-removal-act")
    del e["date"]
    e["start"], e["end"] = "1830-05-28", "1830-06-02"
    claim(raw, "c-e-removal-act-date")["value"] = "1830-05-28/1830-06-02"
    assert validate(raw) == []


def test_bce_years_are_supported_and_sort_before_ce():
    assert setdata.sort_key("-0431") < setdata.sort_key("0001") < setdata.sort_key("1789-04-30")
    assert setdata.format_date("-0431") == "431 BCE"
    assert setdata.format_date("1789-04-30") == "30 April 1789"
    assert setdata.format_date("1914/1918") == "1914 to 1918"
    assert setdata.parse_date("0000") is None


def test_an_event_naming_a_place_its_claim_never_mentions_fails(raw):
    event(raw, "e-washington-oath")["place"] = "paris"
    assert "E_PLACE_UNSUPPORTED" in codes(raw)


def test_an_event_naming_a_person_its_claim_never_mentions_fails(raw):
    event(raw, "e-washington-oath")["people"] = ["washington", "jefferson"]
    assert "E_PERSON_UNSUPPORTED" in codes(raw)


# ---- sections, readings, playability ---------------------------------------------------------------------------

def test_a_section_with_too_few_events_for_its_puzzle_size_is_unplayable(raw):
    next(s for s in raw["sections"] if s["id"] == "s3")["size"] = 5
    assert "E_SECTION_UNPLAYABLE" in codes(raw)


def test_an_event_in_no_section_fails(raw):
    next(s for s in raw["sections"] if s["id"] == "s1")["events"].remove("e-farewell")
    assert "E_SECTION" in codes(raw)


def test_a_section_requiring_a_later_section_fails(raw):
    next(s for s in raw["sections"] if s["id"] == "s1")["requires"] = ["s2"]
    assert "E_SECTION" in codes(raw)


def test_an_elsewhere_event_nobody_can_reach_fails(raw):
    e = event(raw, "c-bastille")
    e["date"] = "1100-07-14"
    claim(raw, "c-c-bastille-date")["value"] = "1100-07-14"
    # moving it also breaks seq order; fix the order so only reachability is wrong
    e["seq"] = 0
    for other in raw["entities"]["events"]:
        if other is not e:
            other["seq"] += 1
    assert "E_SECTION_UNPLAYABLE" in codes(raw)


def test_a_reading_must_cite_existing_claims_and_stay_short(raw):
    r = raw["readings"][0]
    r["claims"] = ["nope"]
    assert "E_READING" in codes(raw)
    r["claims"] = ["c-e-washington-oath-date"]
    r["text"] = "x" * 701
    assert "E_READING" in codes(raw)


def test_a_set_missing_a_file_fails(raw):
    del raw["claims"]
    assert codes(raw) == {"E_FILES"}


def test_load_set_dict_raises_with_every_problem(raw):
    claim(raw, DATE_CLAIM)["sources"] = []
    event(raw, "e-farewell")["seq"] = 99
    with pytest.raises(SetError) as err:
        load_set_dict(raw)
    assert len(err.value.problems) >= 2


def test_validation_never_raises_on_garbage():
    for junk in (None, [], "x", {"meta": 1}, {n: None for n in setdata.FILES}, {n: [] for n in setdata.FILES}, {n: {} for n in setdata.FILES}):
        assert validate(junk)          # a non-empty list of problems, never an exception
