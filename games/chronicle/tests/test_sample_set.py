"""The sample set's content rules: sourced, balanced, marked as a draft, written in original words."""

import re
from urllib.parse import urlparse

import setdata

READ_DATES = {"2026-10-07", "2026-10-08"}      # the first draft was read on the 7th, the cause-web and myth sources on the 8th


def test_the_sample_is_marked_a_draft_everywhere_it_is_described(sample):
    assert sample.status == "sample-draft"
    assert "draft" in sample.status_label.lower() and "sample" in sample.status_label.lower()
    assert "not been reviewed" in sample.meta["description"] or "none of it has been reviewed" in sample.meta["description"]


def test_counts(sample):
    assert len(sample.event_ids("event")) == 14
    assert len(sample.event_ids("context")) == 7
    assert len(sample.people) == 10 and len(sample.places) == 14


def test_every_claim_has_three_distinct_https_sources_from_two_institutions(sample):
    for c in sample.claims.values():
        refs = sample.resolved_sources(c)
        assert len(refs) >= 3, c["id"]
        assert len({r["url"] for r in refs}) == len(refs)
        assert len({r["institution"] for r in refs}) >= 2, c["id"]
        for r in refs:
            assert urlparse(r["url"]).scheme == "https" and r["title"] and r["institution"], r
            assert r["read"] in READ_DATES and r["note"], r


def test_every_event_has_exactly_one_date_claim_and_it_matches(sample):
    for eid, e in sample.events.items():
        claims = [c for c in sample.claims_for(eid) if c["field"] == "date"]
        assert len(claims) == 1 and claims[0]["value"] == e["date"], eid


def test_both_non_documented_confidence_levels_are_exercised(sample):
    levels = {c["confidence"] for c in sample.claims.values()}
    assert levels == {"documented", "disputed", "traditional-but-doubtful"}
    for c in sample.claims.values():
        if c["confidence"] != "documented":
            assert c["alternatives"]


def test_sources_were_read_on_the_stated_day_and_urls_are_unique_per_id(sample):
    urls = [s["url"] for s in sample.sources.values()]
    assert len(set(urls)) == len(urls)
    assert all(s["read"] in READ_DATES for s in sample.sources.values())


def test_every_source_is_used_by_some_claim(sample):
    used = {ref["source"] for c in sample.claims.values() for ref in c["sources"]}
    assert used == set(sample.sources)


def test_text_is_plain_and_in_the_project_style(sample):
    texts = []
    for c in sample.claims.values():
        texts += [c["text"], c["value"]] + list(c.get("alternatives", []))
        texts += [ref["note"] for ref in c["sources"]]
    texts += [e["title"] for e in sample.events.values()]
    texts += [r["text"] for r in sample.readings] + [r["title"] for r in sample.readings]
    texts += [s["blurb"] for s in sample.sections] + [sample.meta["description"]]
    for t in texts:
        assert "—" not in t and "–" not in t, t           # no em or en dashes
        assert "!" not in t, t
        assert t == t.strip()
        assert not re.search(r"\bhistorians (agree|say) that\b", t)    # weasel framing without a source


def test_claims_are_dated_facts_not_praise_or_blame(sample):
    loaded = {"great", "worst", "best", "terrible", "heroic", "villain", "tyrant", "failed", "disgrace", "brilliant", "evil", "corrupt"}
    for c in sample.claims.values():
        words = set(re.findall(r"[a-z]+", c["text"].lower()))
        assert not (words & loaded), (c["id"], words & loaded)
    for r in sample.readings:
        assert not (set(re.findall(r"[a-z]+", r["text"].lower())) & loaded), r["id"]


def test_the_balanced_sections_cover_both_the_early_and_the_modern_presidency(sample):
    years = sorted(int(sample.events[e]["date"][:4]) for e in sample.event_ids("event"))
    assert years[0] < 1800 and years[-1] > 1970
    assert len(sample.people) >= 8


def test_sections_unlock_in_the_documented_order(sample):
    assert [s["id"] for s in sample.sections] == ["s1", "s2", "s3", "s4"]
    assert sample.section("s1")["requires"] == []
    assert sample.section("s4")["requires"] == ["s2", "s3"]
    assert [sample.section(s)["difficulty"] for s in sample.section_ids] == [1, 2, 2, 3]


def test_every_reading_only_cites_claims_of_its_own_section(sample):
    for r in sample.readings:
        pool = set(sample.section_pool(r["section"])) if r["section"] != "s4" else set(sample.events)
        for cid in r["claims"]:
            assert sample.claims[cid]["subject"] in pool, (r["id"], cid)


def test_the_gettysburg_story_is_labelled_as_doubtful_and_its_dating_as_disputed(sample):
    assert sample.claims["c-e-gettysburg-tradition"]["confidence"] == "traditional-but-doubtful"
    assert sample.claims["c-e-gettysburg-final-revision"]["confidence"] == "disputed"
    assert sample.claims["c-e-gettysburg-date"]["confidence"] == "documented"


def test_the_review_page_files_exist_and_check_the_same_rule():
    from pathlib import Path
    html = (Path(__file__).resolve().parent.parent / "review.html").read_text(encoding="utf-8")
    assert 'name="robots" content="noindex' in html
    assert "Fewer than three distinct URLs" in html and "no read date" in html
    for f in setdata.FILES:
        assert '"%s"' % f in html
