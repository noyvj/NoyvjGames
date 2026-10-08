"""Lighthouse -- the calendar: nights, seasons, years and the clock on the wall."""

from data import FESTIVAL_NIGHT, NIGHT_LEN, NIGHT_START_MIN, NIGHTS_PER_SEASON, NIGHTS_PER_YEAR, SEASONS, TICK_MINUTES


def year_night(night):
    """1..40: which night of its year this night is."""
    return (night - 1) % NIGHTS_PER_YEAR + 1


def year_of(night):
    return (night - 1) // NIGHTS_PER_YEAR + 1


def season_of(night):
    """0..3 (spring, summer, autumn, winter)."""
    return (year_night(night) - 1) // NIGHTS_PER_SEASON


def season_name(night):
    return SEASONS[season_of(night)]


def night_in_season(night):
    return (year_night(night) - 1) % NIGHTS_PER_SEASON + 1


def night_len(night):
    return NIGHT_LEN[season_of(night)]


def is_festival(night):
    return year_night(night) == FESTIVAL_NIGHT


def block_of(night, tick):
    """0..2: dusk, deep night or dawn."""
    return min(2, tick * 3 // night_len(night))


def block_end(night, block):
    """The first tick that no longer belongs to this block."""
    length = night_len(night)
    return (length * (block + 1) + 2) // 3 if block < 2 else length


def clock_minutes(night, tick):
    return (NIGHT_START_MIN[season_of(night)] + tick * TICK_MINUTES) % 1440


def clock_label(night, tick):
    minutes = clock_minutes(night, tick)
    return "%02d:%02d" % (minutes // 60, minutes % 60)


def darkness(night, tick):
    """0.0 (dusk or dawn) .. 1.0 (the deepest dark): how dark the sky is, for drawing it."""
    length = night_len(night)
    x = (tick + 0.5) / length
    return max(0.0, min(1.0, 1.0 - abs(x - 0.5) * 2.0)) ** 0.6
