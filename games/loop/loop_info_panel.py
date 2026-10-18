"""The 'Real Story' info page content and its toggle."""

import info_page

import loop_runstate as runstate


# Info Page — optional, player-triggered supplement (never forced
# mid-session). Framing is written fresh, not copied from any source;
# sources are the curated real-world backing for the game's mechanics.
INFO_PAGE = {
    "framing": (
        "Most of the modern economy still runs in a straight line — "
        "extract, make, use, discard — even though a genuinely circular "
        "alternative (eliminate waste, circulate materials, regenerate "
        "nature) is well-documented and already improving outcomes where "
        "it's tried. Loop's chain-visualization mechanic is a direct "
        "simplification of that real framework."
    ),
    "mechanic_tie_in": (
        "Loop's three circularity investments (repair, reuse, recycling) "
        "map onto the three real circular-economy design principles this "
        "whole field is built around."
    ),
    "sources": [
        {
            "label": "Ellen MacArthur Foundation — The Circular Economy: Definition & Model Explained",
            "url": "https://www.ellenmacarthurfoundation.org/topics/circular-economy-introduction/overview",
            "note": "The standard-setting definition of circular economy — Loop's core mechanic is a direct translation of this framework.",
        },
        {
            "label": "Ellen MacArthur Foundation — Circular Economy Principles",
            "url": "https://www.ellenmacarthurfoundation.org/circular-economy-principles",
            "note": "Breaks circularity into three concrete design principles, structuring Loop's three types of circularity investment.",
        },
        {
            "label": "Mongabay — The circular economy: Sustainable solutions to solve planetary overshoot?",
            "url": "https://news.mongabay.com/2023/07/the-circular-economy-sustainable-solutions-to-solve-planetary-overshoot/",
            "note": "Accessible journalism with a concrete example (recycled steel's emissions/water savings) for the framing paragraph.",
        },
        {
            "label": "PMC/NCBI — Waste metrics in the framework of circular economy",
            "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC10693739/",
            "note": "A more academic treatment connecting overconsumption directly to circular economy metrics.",
        },
    ],
}


# Rendering/toggle logic lives in shared/info_page.py now (see that
# module's docstring) -- this used to be a ~25+4 line implementation
# byte-identical across all 8 climate games. info_page_open stays local
# here since it's part of this game's save contract.
def render_info_page():
    info_page.render(INFO_PAGE, runstate.info_page_open)


def on_toggle_info_page(event=None):
    runstate.info_page_open = info_page.toggle(runstate.info_page_open)
    render_info_page()
