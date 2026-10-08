"""Chapter 4, Fog and unmarked dangers: no landmark can be seen, and some hazards are not on the chart. They are drawn only after
the ship has found one (a close pass or a grounding), and the chart remembers what you found for the next attempt."""

from chartkit import chart, land, reef, rock, shoal, stream, wind

WATCH = {"modes": ["watch", "plan"], "default_mode": "watch", "fog": True}

CHARTS = [
    chart("fog-01", "Thin Fog", "fog", start=[2.0, 10.0], dest=[18.0, 10.0], deadline=6.0, naive_fails=True, **WATCH,
          hazards=[rock("gong-rock", "Gong Rock", 10.0, 10.0, 0.8, charted=False), reef("far-reef", "Far Reef", 6.0, 12.5, 1.0, charted=False)],
          waypoints=[[2.0, 10.0], [10.0, 7.5], [18.0, 10.0]],
          intro="The fog came down at dawn. The chart shows the sea as it was surveyed, and surveys miss things. Something sits on the direct line; you will find out what, once, and then it is on your chart for good.",
          log={"arrived": "We found the Gong Rock the slow way and went round it the second time.",
               "missed": "Round the danger, short of the flag. The fog hides distances too.",
               "aground": "Something hard and unmarked. It is on the chart now.",
               "late": "Round in the end; the fog slowed us."}),
    chart("fog-02", "Grey Water", "fog", start=[2.0, 4.0], dest=[18.0, 16.0], deadline=7.0, naive_fails=True, **WATCH,
          hazards=[shoal("grey-shoal", "Grey Shoal", 9.0, 6.0, 1.2), rock("hush-rock", "Hush Rock", 12.0, 11.0, 0.7, charted=False),
                   rock("whisper-rock", "Whisper Rock", 7.0, 14.5, 0.7, charted=False)],
          currents=[stream("grey-stream", "the grey stream", [5, 0, 15, 20], 0, [0.8, 1.2], 4, 1.0)],
          waypoints=[[2.0, 4.0], [11.0, 3.5], [15.5, 12.0], [18.0, 16.0]],
          intro="A stream and a shoal you can read on the chart, and two rocks that are not on it. Fog makes the chart the only thing you have, and the chart is not complete.",
          log={"arrived": "Past the shoal, past two rocks we never saw, and onto the flag.",
               "missed": "Past the rocks and not quite on the flag.",
               "aground": "Another rock the survey missed. It is on the chart now.",
               "late": "Slow in the fog, as one is."}),
    chart("fog-03", "Hissing Rocks", "fog", start=[2.0, 18.0], dest=[18.0, 2.0], deadline=7.0, naive_fails=True, **WATCH,
          hazards=[rock("first-hiss", "First Hiss", 6.0, 14.0, 0.6, charted=False), rock("second-hiss", "Second Hiss", 10.0, 10.0, 0.6, charted=False),
                   rock("third-hiss", "Third Hiss", 14.0, 6.0, 0.6, charted=False)],
          waypoints=[[2.0, 18.0], [8.0, 15.5], [15.0, 11.0], [18.0, 2.0]],
          intro="Three rocks in a row on the diagonal, none of them charted. After the first one you will know to look for the others.",
          log={"arrived": "Round all three. They hissed as we passed, which is manners, for a rock.",
               "missed": "Past the hissing, short of the flag.",
               "aground": "One of the three. The other two are probably nearby.",
               "late": "Round the hissing, slowly."}),
    chart("fog-04", "Thick Fog", "fog", start=[3.0, 3.0], dest=[17.0, 17.0], deadline=7.0, naive_fails=True, **WATCH,
          wind=wind(90, [12, 16], 14),
          land=[land("fog-head", "Fog Head", [[8, 8], [12, 8], [12, 11], [8, 11]])],
          hazards=[reef("grey-reef", "Grey Reef", 5.0, 9.0, 1.0), rock("ghost-rock", "Ghost Rock", 14.0, 12.0, 0.7, charted=False),
                   rock("pale-rock", "Pale Rock", 6.0, 13.5, 0.7, charted=False)],
          currents=[stream("thick-stream", "the thick stream", [0, 0, 20, 20], 315, [0.6, 1.0], 319, 0.8)],
          waypoints=[[3.0, 3.0], [11.5, 5.5], [17.5, 9.5], [17.0, 17.0]],
          intro="Wind, a stream, a headland on the chart and two rocks that are not. Chapter four's last chart: all of it at once, in the fog.",
          log={"arrived": "Through the fog with everything allowed for. Chapter done, navigator.",
               "missed": "A good deal right, and not enough.",
               "aground": "The fog keeps its secrets, one at a time.",
               "late": "Right, but slowly."}),
]
