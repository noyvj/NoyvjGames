from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent


def test_plan_table_markup():
    html = (GAME_DIR / "index.html").read_text()
    assert 'id="plan-table"' in html
    assert 'id="plan-body"' in html
    for k in ("plant", "cost", "output", "emissions", "payback"):
        assert f'id="plan-sort-{k}"' in html
