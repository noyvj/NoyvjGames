"""Chapter 7, Two ships: you plan the courses of TWO vessels on the same chart. Each has its own start, flag, speed range and deadline;
both sail the same sea. Keep them at least fleet.SEPARATION nm apart while both are under way: a closer approach costs one star and
never ends the passage. `waypoints` and `par_wait` at the top of a chart belong to Ship A; Ship B's are inside `second_ship(...)`.
The par plans for both ships are generated into pars.py (PARS and PARS2) by tools/check_charts.py --write.

Every chart is built so that the two ships' straight, unhurried plans would meet: the puzzle is timing as much as steering."""

from chartkit import chart, land, reef, rock, second_ship, shoal, stream, wind

CHARTS = [
    chart("two-01", "Crossing Courses", "ships", start=[2.0, 10.0], dest=[18.0, 10.0], deadline=5.0,
          ship2=second_ship([10.0, 2.0], [10.0, 18.0], 7.0, par_wait=2.0),
          intro="Two ships, one patch of open water. Ship A goes east and Ship B goes north, and their straight lines cross exactly in the middle. "
                "Both are fast enough to be there at the same hour. One of you has to be somewhere else.",
          log={"arrived": "Two landfalls and a clear gap between them. The harbour master noticed neither of us was in the other's way.",
               "missed": "At least one flag was missed. Plot both again; the sea is the same for both of you.",
               "aground": "A ship touched something. Nothing else was lost and a retry is free.",
               "late": "Both there, one of you late. Waiting is allowed, but it costs hours."}),
    chart("two-02", "The Narrow Pass", "ships", start=[2.0, 4.0], dest=[18.0, 16.0], deadline=6.5, par_wait=1.5,
          hazards=[reef("north-reef", "North Reef", 10.0, 13.2, 1.1), rock("south-rock", "South Rock", 10.0, 6.8, 0.8)],
          ship2=second_ship([18.0, 4.0], [2.0, 16.0], 5.0),
          intro="A reef to the north, a rock to the south and a gap of open water between them: the only sensible way through. "
                "Two ships are heading for it from opposite corners, and they will reach the middle of it together unless one of them does something about that.",
          log={"arrived": "Through the pass one after the other, with room to spare. Reef and rock were no trouble to either of us.",
               "missed": "Through the pass and short of a flag. Count the hours for each ship again.",
               "aground": "The reef or the rock got one of us. Nobody was hurt and the tide lifted her; a retry is free.",
               "late": "Both through, one of you slow. The pass is narrow, not endless."}),
    chart("two-03", "Crossing Stream", "ships", start=[2.0, 6.0], dest=[18.0, 6.0], deadline=6.0, naive_fails=True,
          currents=[stream("mid-stream", "the mid stream", [6, 0, 14, 20], 0, [1.3, 1.7], 3, 1.5)],
          ship2=second_ship([10.0, 11.5], [10.0, 2.0], 6.0, naive_fails=True, par_wait=2.0),
          intro="A stream runs north up the middle of the chart. Ship A crosses it going east and Ship B runs down it going south, and the stream "
                "moves both of them as they go. Allow for it, and remember it moves the meeting place too.",
          log={"arrived": "Both allowed for the stream, and neither of us ended up where the other one was.",
               "missed": "The stream took at least one of you off the flag. The chart gives its range; plot with the middle of it.",
               "aground": "A ship touched something. Nothing was lost; try again.",
               "late": "Both landed, but one of you waited longer than the chart could spare."}),
    chart("two-04", "Harbour Mouth", "ships", start=[2.0, 3.0], dest=[14.0, 17.0], deadline=7.0, naive_fails=True, par_wait=1.5,
          wind=wind(270, [10, 14], 12),
          land=[land("mid-isle", "Mid Isle", [[9, 7], [11, 7], [11, 11], [9, 11]])],
          hazards=[reef("mouth-reef", "Mouth Reef", 10.0, 15.0, 0.9)],
          waypoints=[[2.0, 3.0], [8.5, 12.5], [11.5, 13.5], [14.0, 17.0]],
          ship2=second_ship([18.0, 3.0], [6.0, 17.0], 7.0, naive_fails=True,
                            waypoints=[[18.0, 3.0], [11.5, 12.5], [8.5, 13.5], [6.0, 17.0]]),
          intro="One harbour, two ships, flags on opposite sides of it. An island in the middle sends both of them round the same way, "
                "and the wind is pushing them sideways. They meet at the harbour mouth, going opposite ways.",
          log={"arrived": "Both ships in, passing each other at the mouth with a polite distance between them.",
               "missed": "The wind took one of you off the flag. Plot both again.",
               "aground": "Mid Isle or Mouth Reef. Nothing worse than a delay; a retry is free.",
               "late": "In, but not in good time. The mouth is only so wide."}),
    chart("two-05", "Fog Signal", "ships", start=[2.0, 4.0], dest=[18.0, 16.0], deadline=7.0, naive_fails=True, fog=True,
          hazards=[shoal("grey-shoal", "Grey Shoal", 10.0, 10.0, 1.2), rock("mute-rock", "Mute Rock", 6.5, 7.0, 0.7, charted=False),
                   rock("hush-rock", "Hush Rock", 13.5, 13.0, 0.7, charted=False)],
          waypoints=[[2.0, 4.0], [5.5, 8.5], [8.5, 11.8], [12.3, 14.4], [18.0, 16.0]],
          ship2=second_ship([3.0, 15.0], [18.0, 3.0], 7.0, naive_fails=True, par_wait=1.5, waypoints=[[3.0, 15.0], [8.5, 8.5], [18.0, 3.0]]),
          intro="Fog, and a chart that is not complete: two rocks are missing from it. Either ship may find one, and then it is charted for both "
                "ships for good. The ships cannot see each other either, so keep your own count of where the other one is.",
          log={"arrived": "Both ships through the fog, round rocks neither of us saw, and clear of each other.",
               "missed": "The fog hid a distance. Plot both again; the rocks you have found are on the chart now.",
               "aground": "An unmarked rock. It is on the chart now, for both ships.",
               "late": "Both there, one late. The fog slows everyone."}),
    chart("two-06", "Tide Race", "ships", start=[2.0, 10.0], dest=[18.0, 10.0], deadline=5.0,
          currents=[stream("race-tide", "the race", [6, 0, 14, 20], 90, [1.4, 2.0], 90, 1.7, tide={"period": 12.0, "phase": 2.0})],
          ship2=second_ship([10.0, 3.0], [10.0, 17.0], 9.0, naive_fails=True, fair_ok=False, par_wait=3.0),
          intro="A tidal race through the middle of the chart. Ship A runs along it, east, with the stream; Ship B has to cross it, north, "
                "and wants it slack. Read the timetable for both: one ship's best hour is not the other's.",
          log={"arrived": "Ship A rode the stream and Ship B crossed on the slack. Neither of us was where the other wanted to be.",
               "missed": "The race had its say with at least one of you. The timetable is on the chart.",
               "aground": "A ship touched something. Nothing was lost; a retry is free.",
               "late": "Both landed, one of you late. Waiting for the tide is allowed; it is not free."}),
    chart("two-07", "Both Together", "ships", start=[2.0, 3.0], dest=[18.0, 17.0], deadline=5.0, naive_fails=True,
          wind=wind(225, [12, 16], 14), compass={"range": [3.0, 6.0], "true": 4.5},
          land=[land("twin-isle", "Twin Isle", [[8, 4], [12, 4], [12, 8], [8, 8]])],
          hazards=[reef("north-reef", "North Reef", 13.0, 14.0, 1.0), rock("bell-rock", "Bell Rock", 6.0, 13.0, 0.7)],
          currents=[stream("cross-stream", "the cross stream", [0, 8, 20, 13], 90, [0.9, 1.5], 93, 1.2)],
          waypoints=[[2.0, 3.0], [7.0, 9.0], [14.5, 12.5], [18.0, 17.0]],
          ship2=second_ship([2.0, 17.0], [18.0, 3.0], 7.0, naive_fails=True, par_wait=1.5, waypoints=[[2.0, 17.0], [7.0, 14.0], [18.0, 3.0]]),
          intro="The last chart of the chapter: a wind, a compass that reads wrong, a stream across the middle, an island and two hazards, and "
                "two ships crossing each other's paths. Everything you have learned, twice over.",
          log={"arrived": "Two ships through everything the sea had, and never in each other's way. Chapter done, navigator.",
               "missed": "A good deal right. Plot both ships again; the sea is the same for both.",
               "aground": "Twin Isle, North Reef or Bell Rock. A retry is free.",
               "late": "Both in, one late. Chapter done, but there is a better plan."}),
]
