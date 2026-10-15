"""Spectrum language: a planet that speaks in light lines."""

from dataclasses import dataclass
from typing import List, Optional


# Spectrum bands: each band has a name and a color (for display)
BANDS = {
    "r": ("red", "#ff4d4d"),
    "g": ("green", "#4dff4d"),
    "b": ("blue", "#4d4dff"),
    "i": ("infrared", "#8040ff"),
    "u": ("ultraviolet", "#ff4080"),
}

# The meaning of each band in the context of the Spectrum planet's science
BAND_MEANINGS = {
    "r": "heat",
    "g": "growth",
    "b": "depth",
    "i": "warmth",
    "u": "energy",
}

# Max number of bands in a single line
MAX_BANDS = 5


@dataclass(frozen=True)
class Reaction:
    """Result of sending a signal on the Spectrum planet."""
    understood: bool
    text: str
    reason: Optional[str] = None
    stock: Optional[List[str]] = None  # List of band names present in the line


def react(line: str, stock: List[str]) -> Reaction:
    """Process a signal on the Spectrum planet.

    Args:
        line: A string of band letters (e.g., "rgb")
        stock: The current stock of bands on the counter

    Returns:
        A Reaction object describing the result
    """
    if not line:
        return Reaction(False, "No signal sent.", "empty_line")

    # Validate the line
    for char in line:
        if char not in BANDS:
            return Reaction(False, f"Unknown band '{char}'.", "unknown_band")

    if len(line) > MAX_BANDS:
        return Reaction(False, f"Too many bands (max {MAX_BANDS}).", "too_many_bands")

    # Check if the line is valid in the context of the current stock
    # For simplicity, we'll just check if the bands are present in the stock
    # In a more complex version, this would involve more sophisticated rules
    for band in line:
        if band not in stock:
            return Reaction(False, f"Band '{band}' not available on the counter.", "band_not_available")

    # If all checks pass, the signal is understood
    new_stock = list(stock)
    for band in line:
        if band not in new_stock:
            new_stock.append(band)

    return Reaction(True, f"Signal received: {', '.join(BANDS[band][0] for band in line)}.", stock=new_stock)


def get_bands() -> List[str]:
    """Return the list of available band names."""
    return list(BANDS.keys())


def get_band_name(band: str) -> str:
    """Return the name of a band."""
    return BANDS.get(band, ("unknown", "#000000"))[0]


def get_band_color(band: str) -> str:
    """Return the color of a band."""
    return BANDS.get(band, ("unknown", "#000000"))[1]
