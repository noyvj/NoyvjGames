"""Checks for the sets built from data/<id>.json (history-of-computing, ancient-greece, history-of-food).

The BUILT tests only run for sets whose folder exists, so while none is built they are collected but skipped; the
`sample` tests below run the very same helpers on the presidents sample so that the helpers themselves are proved
to read the real file shapes (a claim's sources are {"source": id, "note": ...}, sets/index.json lists "folder").
"""
import json
from pathlib import Path

import pytest

import core
from setdata import load_set, read_set_files, validate

IDS = ['history-of-computing', 'ancient-greece', 'history-of-food']
COUNTS = {'history-of-computing': 8, 'ancient-greece': 7, 'history-of-food': 3}
SETS_DIR = Path(__file__).resolve().parent.parent / 'sets'
BUILT = [i for i in IDS if (SETS_DIR / i / 'meta.json').exists()]


def evidence_problems(files):
    """Every claim needs three sources from at least two institutions; every source needs the fields the About page shows."""
    problems = []
    for claim in files['claims']:
        ids = [item['source'] for item in claim['sources']]
        if len(ids) < 3:
            problems.append('%s has %d sources' % (claim['id'], len(ids)))
        institutions = {files['sources'][i]['institution'] for i in ids}
        if len(institutions) < 2:
            problems.append('%s has one institution' % claim['id'])
        for i in ids:
            src = files['sources'][i]
            if not (src.get('title') and src.get('read') and str(src.get('url', '')).startswith('https://')):
                problems.append('source %s lacks title, read date or https url' % i)
    return problems


def date_problems(files):
    """A date claim's value must equal the date of the event it names."""
    events = {e['id']: e for e in files['entities']['events']}
    return [c['id'] for c in files['claims'] if c['field'] == 'date' and c['value'] != events[c['subject']]['date']]


def indexed_folders():
    index = json.loads((SETS_DIR / 'index.json').read_text(encoding='utf-8'))
    return [entry['folder'] for entry in index['sets']]


@pytest.mark.parametrize("set_id", BUILT)
def test_evidence(set_id):
    files = read_set_files(SETS_DIR / set_id)
    assert len(files['claims']) == COUNTS[set_id]
    assert evidence_problems(files) == []
    assert files['meta']['status'] == 'draft'


@pytest.mark.parametrize("set_id", BUILT)
def test_valid(set_id):
    files = read_set_files(SETS_DIR / set_id)
    if 'entities' not in files:
        pytest.skip("entities missing")
    assert validate(files) == []
    assert load_set(SETS_DIR / set_id).id == set_id


@pytest.mark.parametrize("set_id", BUILT)
def test_dates(set_id):
    files = read_set_files(SETS_DIR / set_id)
    if 'entities' not in files:
        pytest.skip("entities missing")
    assert date_problems(files) == []


@pytest.mark.parametrize("set_id", BUILT)
def test_registered(set_id):
    if set_id not in indexed_folders():
        pytest.skip("%s is not in sets/index.json yet" % set_id)
    assert set_id in core.SET_ORDER


def test_helpers_read_the_real_shapes_on_the_sample():
    files = read_set_files(SETS_DIR / 'presidents-sample')
    assert evidence_problems(files) == []
    assert date_problems(files) == []
    assert indexed_folders()[0] == 'presidents-sample'
    assert 'presidents-sample' in core.SET_ORDER
