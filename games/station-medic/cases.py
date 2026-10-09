"""Station Medic -- the 60 authored shifts, grouped into chapters. The chapter files hold the data; this module compiles and
indexes them. A chapter is listed here once it is built."""

import cases_1
import cases_2

CHAPTER_DATA = (
    ("quiet-hours", "Quiet Hours", "Signs only. Read the sheet, match each patient, and share a thin shelf.", cases_1.SHIFTS),
    ("second-look", "The Second Look", "Look-alike conditions. A scan tells them apart, and every scan costs a supply.", cases_2.SHIFTS),
)

ALL = [d for _id, _name, _blurb, shifts in CHAPTER_DATA for d in shifts]
