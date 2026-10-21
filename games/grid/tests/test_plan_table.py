from .pagefiles import page_text


def test_plan_table_markup_exists():
    text = page_text()
    assert 'id="plan-table"' in text
    assert 'id="plan-body"' in text
    for k in ("plant", "cost", "output", "emissions", "payback"):
        assert f'id="plan-sort-{k}"' in text
