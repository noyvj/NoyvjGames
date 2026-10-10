"""F-29: plain-language glossary popovers. The behaviour is plain JS (settings.js); these tests pin
the word list, that every definition is short and plain, and the CSS hooks. The live behaviour
(dotted underlines, popover on hover/focus, the glossary in How to Play) is checked in a browser."""

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
JS = (HERE / "settings.js").read_text(encoding="utf-8")
CSS = (HERE / "style.css").read_text(encoding="utf-8")


def _entries():
    return re.findall(r'\{ key: "(\w+)", name: "([^"]+)", pattern: /(.+?)/i,\s*text: "([^"]+)" \}', JS)


def test_the_glossary_covers_the_hard_words_the_todo_names():
    keys = {k for k, _n, _p, _t in _entries()}
    assert {"coupling", "baseline", "welfare", "capture", "decoupling", "pressure", "certification"} <= keys


def test_every_definition_is_one_or_two_plain_sentences():
    for _key, name, _pattern, text in _entries():
        assert 40 <= len(text) <= 190, name
        assert len(re.findall(r"\.(?:\s|$)", text)) <= 2, name
        assert text[0].isupper() and text.endswith(".")


def test_the_words_are_only_marked_in_static_explainer_text():
    assert 'GLOSSARY_SCOPE = ".info-toggle p, .context-blurb, #howto-panel .howto-step p"' in JS


def test_popover_and_glossary_block_have_styles_and_the_escape_key_closes_it():
    for hook in (".glossary-term", "#glossary-popover", ".howto-glossary", 'html[data-high-contrast="true"] #glossary-popover'):
        assert hook in CSS
    assert 'event.key === "Escape" && glossaryPopover && !glossaryPopover.hidden' in JS


def test_the_terms_appear_in_the_pages_static_text():
    html = (HERE / "index.html").read_text(encoding="utf-8").lower()
    for word in ("coupling ratio", "welfare", "pressure", "decoupl"):
        assert word in html
