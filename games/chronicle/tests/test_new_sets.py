import json
from pathlib import Path

import pytest

from setdata import read_set_files, validate, load_set
import core


IDS = ['history-of-computing', 'ancient-greece', 'history-of-food']
COUNTS = {'history-of-computing': 8, 'ancient-greece': 7, 'history-of-food': 3}
SETS_DIR = Path(__file__).resolve().parent.parent / 'sets'
BUILT = [i for i in IDS if (SETS_DIR / i / 'meta.json').exists()]


@pytest.mark.parametrize("id", BUILT)
def test_evidence(id):
    files = read_set_files(SETS_DIR / id)
    claims = files['claims']
    assert len(claims) == COUNTS[id]
    sources_registry = files['sources']
    for claim in claims:
        assert len(claim['sources']) >= 3
        institutions = set()
        for src_id in claim['sources']:
            src = sources_registry[src_id]
            institutions.add(src['institution'])
            assert 'title' in src
            assert 'url' in src and src['url'].startswith('https://')
            assert 'read' in src
        assert len(institutions) >= 2
    assert files['meta']['status'] == 'draft'


@pytest.mark.parametrize("id", BUILT)
def test_valid(id):
    files = read_set_files(SETS_DIR / id)
    if 'entities' not in files:
        pytest.skip("entities missing")
    assert validate(files) == []
    s = load_set(SETS_DIR / id)
    assert s.id == id


@pytest.mark.parametrize("id", BUILT)
def test_dates(id):
    files = read_set_files(SETS_DIR / id)
    if 'entities' not in files:
        pytest.skip("entities missing")
    events = {e['id']: e for e in files['entities']['events']}
    for claim in files['claims']:
        assert claim['value'] == events[claim['subject']]['date']


@pytest.mark.parametrize("id", BUILT)
def test_registered(id):
    index_path = SETS_DIR / 'index.json'
    if not index_path.exists():
        pytest.skip("sets/index.json missing")
    with open(index_path, 'r') as f:
        index = json.load(f)
    ids_in_index = [s['id'] for s in (index.get("sets", index))]
    if id not in ids_in_index:
        pytest.skip(f"{id} not in sets/index.json")
    assert id in core.SET_ORDER
