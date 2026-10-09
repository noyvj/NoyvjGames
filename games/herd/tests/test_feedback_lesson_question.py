"""FY-4: the end-of-game feedback has a second question about Herd's own lesson (decoupling)."""
from pathlib import Path

GAME = Path(__file__).resolve().parent.parent
IDS = ("feedback-decoupling-strategy-button", "feedback-decoupling-tax-button")


def test_both_pages_have_the_lesson_question():
    for page in ("index.html", "pc.html"):
        html = (GAME / page).read_text(encoding="utf-8")
        for element_id in IDS:
            assert f'id="{element_id}"' in html, (page, element_id)
        assert "real strategy, or a tax on growth" in html


def test_submit_needs_both_answers_and_folds_them_into_the_response():
    html = (GAME / "index.html").read_text(encoding="utf-8")
    assert "if (!answer || !decouplingAnswer) return;" in html
    assert "understanding=${answer}; decoupling=${decouplingAnswer}" in html
    assert "Answer both questions first" in html
