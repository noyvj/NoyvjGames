"""The tracker's wide tables reflow into cards on phone-width screens."""

import pathlib
import re

CSS = (pathlib.Path(__file__).resolve().parent.parent / "style.css").read_text()


def _phone_block():
    start = CSS.index("@media (max-width: 640px)")
    return CSS[start:CSS.index("/* Light theme", start)]


def test_phone_block_turns_rows_into_cards_without_sideways_scrolling():
    block = _phone_block()
    assert "table.parts thead" in block and "display: none" in block
    assert "grid-template-columns" in block
    assert "overflow-x: visible" in block


def test_every_non_name_column_gets_a_repeated_label():
    block = _phone_block()
    parts = re.findall(r'table\.parts td:nth-child\(\d\)::before \{ content: "([^"]+)"', block)
    resources = re.findall(r'table\.resources td:nth-child\(\d\)::before \{ content: "([^"]+)"', block)
    assert parts == ["Need", "Have", "Still need", "Wiki", "Build"]
    assert resources == ["Needed", "Built / refined have", "Raw have", "Still need", "Wiki"]
