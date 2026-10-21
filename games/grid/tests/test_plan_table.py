from .pagefiles import page_text


def test_plan_table_markup_exists():
    """The plan table markup is present in index.html."""
    html = page_text()
    assert 'id="plan-table"' in html
    assert 'id="plan-body"' in html
    for k in ("plant", "cost", "output", "emissions", "payback"):
        assert f'id="plan-sort-{k}"' in html
