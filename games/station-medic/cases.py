"""Station Medic -- the 60 authored shifts, grouped into chapters. The chapter files hold the data; this module compiles and
indexes them. A chapter is listed here once it is built."""

import cases_1
import cases_2
import cases_3
import cases_4
import cases_5

CHAPTER_DATA = (
    ("quiet-hours", "Quiet Hours", "Signs only. Read the sheet, match each patient, and share a thin shelf.", cases_1.SHIFTS),
    ("second-look", "The Second Look", "Look-alike conditions. A scan tells them apart, and every scan costs a supply.", cases_2.SHIFTS),
    ("chart-notes", "Chart Notes", "A chart note forbids a kind of treatment, so the usual cure may not be the right one.", cases_3.SHIFTS),
    ("shared-shelves", "Shared Shelves", "One supply serves two jobs, so every scan you cut is a treatment you cannot give.", cases_4.SHIFTS),
    ("cold-room", "The Cold Room", "Spore flecks might mean a condition that spreads. The cold room has one bed.", cases_5.SHIFTS),
)

ALL = [d for _id, _name, _blurb, shifts in CHAPTER_DATA for d in shifts]
