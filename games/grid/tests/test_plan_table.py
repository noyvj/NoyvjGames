from .pagefiles import page_text


def test_plan_table_markup_exists():
    html = page_text()
    assert 'id="plan-table"' in html
    assert 'id="plan-body"' in html
    for k in ("plant", "cost", "output", "emissions", "payback"):
        assert f'id="plan-sort-{k}"' in html
