"""Chapter 5, The Big Houses: ten to fourteen rooms, a bag of four and everything together."""

from casekit import C

CASES = [
    C('5-1', 'The Old Mill', 'mill', 'ledger',
      pool=('draughtling', 'glimmer', 'hearthkeeper', 'hushling', 'ledger', 'pacer', 'tangle'),
      restless=(('hall', 'workshop', 'loft'),),
      kit=4, accounts=(('mover', None),),
      features={'hall': 'wiring', 'loft': 'desk', 'boiler': 'draught'},
      client='The Mill Trust',
      intro=('The Mill Trust opens in spring. The mill floor, the workshop and the loft all show signs. The hall wiring '
             'hums, the loft has a desk of old notes, and the boiler room is draughty.'),
      ending=('A shopkeeper turned mill clerk, tidy and quietly moving the stock one shelf over, had the whole building in '
              'his keeping. The Trust framed a ledger page in the workshop, and he moves nothing now but the light.')),
    # min bag 3, candidates before any reading [4]
    C('5-2', 'The Abbey House', 'abbey', 'glimmer',
      pool=('candlewick', 'draughtling', 'glimmer', 'hushling', 'mothlight', 'scrivener', 'tangle'),
      restless=(('chapel', 'tower', 'study'),),
      kit=4, accounts=(('curious', None),),
      features={'chapel': 'streetlamp', 'tower': 'paint', 'cellar': 'damp'},
      client='The Heritage Committee',
      intro=('A chapel with a street lamp in its window, a bell loft with paint that glows, a damp cellar, and a scriptorium '
             'that is wilfully quiet. Lights follow visitors in the three rooms that matter.'),
      ending=('A lamp-lighter who walked the whole abbey at dusk was following the committee because he never could leave '
              'anyone in the dark. They left a lantern in each of the three rooms, and he took the rounds off.')),
    # min bag 3, candidates before any reading [4]
    C('5-3', 'The Seaside Hotel', 'hotel', ('hearthkeeper', 'tangle'),
      pool=('candlewick', 'hearthkeeper', 'hushling', 'ledger', 'scrivener', 'spindle', 'tangle'),
      restless=(('ballroom',), ('bedroom',)),
      kit=4, accounts=(('tidy', 'ballroom'), ('curious', 'bedroom')),
      features={'ballroom': 'draught', 'bedroom': 'wiring'},
      client='The Hotel Marrow',
      intro=('The ballroom has a draught that comes from nowhere, the suite has wiring that hums, and two presences are in '
             'two rooms. One keeps its room tidy. One follows guests about. Name both.'),
      ending=("The ballroom's was the hotel's fire-minder, and the suite's a knitter who followed guests to hand them the end "
              'of her wool. The staff say good evening to both, and the guests say the hotel is lovely.')),
    # min bag 3, candidates before any reading [3, 3]
    C('5-4', 'The Little Theatre', 'theatre', 'lullwisp',
      pool=('candlewick', 'hearthkeeper', 'hushling', 'ledger', 'lullwisp', 'mothlight', 'scrivener', 'tangle'),
      restless=(('ballroom', 'loft', 'gallery'),),
      kit=4, accounts=(),
      features={'ballroom': 'streetlamp', 'gallery': 'draught'},
      keepsake=('loft', 'musicbox', 'tidy'),
      client='The Little Theatre Company',
      intro=('Footsteps in the ballroom, the loft and the gallery. Beds in the dress circle are made. A street lamp shines '
             'on the stage. A music box sits in the loft, and its room will fool every instrument.'),
      ending=('A nurse who walked the whole theatre to tuck up the cast had left the music box as a lullaby for the loft. The '
              'Company wound it on opening night, and the performances run a little quieter.')),
    # min bag 2, candidates before any reading [3]
    C('5-5', 'The Country Estate', 'estate', 'draughtling',
      pool=('candlewick', 'draughtling', 'hearthkeeper', 'hushling', 'ledger', 'lullwisp', 'mothlight', 'tangle'),
      restless=(('music', 'nursery', 'attic'),),
      kit=4, accounts=(),
      features={'music': 'wiring', 'nursery': 'damp', 'attic': 'draught'},
      keepsake=('attic', 'teacup', 'shy'),
      client='The Estate Trustees',
      intro=('The music room wiring hums, the nursery floor is damp, and the attic is draughty and holds a teacup that will '
             'not give a clean reading. Small things move and slip away.'),
      ending=('A shy presence that loved an open window had been keeping the teacup warm. The trustees leave the attic window '
              'ajar, and the music room is only a music room.')),
    # min bag 2, candidates before any reading [3]
    C('5-6', 'The Grand House', 'grand', ('spindle', 'hushling'),
      pool=('hushling', 'ledger', 'lullwisp', 'mothlight', 'pacer', 'scrivener', 'spindle', 'tangle'),
      restless=(('music',), ('chapel',)),
      kit=4, accounts=(('mover', 'music'), ('curious', 'chapel')),
      features={'music': 'desk', 'chapel': 'damp'},
      client='The Grand House Society',
      intro=('Two presences: one in the music room on the first floor, one in the chapel on the ground floor. The music room '
             'desk and the chapel floor throw off two of the readings. Name both.'),
      ending=('A seamstress who loved the light in the music room and a child who loved to be found in the chapel. The '
              'Society moved a chair to the first and counts to twenty for the second.')),
    # min bag 3, candidates before any reading [3, 3]
    C('5-7', 'The Estate, Four Rooms', 'estate', 'pacer',
      pool=('candlewick', 'draughtling', 'hearthkeeper', 'ledger', 'pacer', 'scrivener', 'spindle', 'tangle'),
      restless=(('library', 'kitchen', 'study', 'scullery'),),
      kit=4, accounts=(('mover', None),),
      features={'library': 'desk', 'kitchen': 'wiring', 'study': 'paint'},
      client='The Estate Trustees, a second visit',
      intro=('Footsteps in four rooms of the estate: the library, the kitchen, the study and the scullery. Wiring in the '
             'kitchen, a desk in the library and glow paint in the study make some readings useless.'),
      ending=('The night worker who paced the floors had finally got around the whole estate. The Trustees set a stool in '
              'each of the four rooms, and he sits on one of them.')),
    # min bag 3, candidates before any reading [4]
    C('5-8', 'The Last House', 'grand', 'scrivener',
      pool=('draughtling', 'glimmer', 'hearthkeeper', 'hushling', 'ledger', 'lullwisp', 'scrivener', 'tangle'),
      restless=(('gallery', 'library', 'attic'),),
      kit=4, accounts=(('curious', None),),
      features={'gallery': 'streetlamp', 'library': 'desk', 'attic': 'paint'},
      keepsake=('attic', 'handmirror', 'curious'),
      client='The Society, again, with everything',
      intro=('The Grand House is the biggest on the books. A street lamp in the gallery, a desk in the library, glow paint '
             'in the attic, a hand mirror in the attic that fools every reading, and a letter-writer following everyone '
             'about.'),
      ending=('A letter-writer who answered every note had been tidying the letters of a house with no one left to write '
              'them. The Society left a pad on the desk, and by morning there was a reply in clean handwriting: thank you, '
              'the house is in order.')),
    # min bag 3, candidates before any reading [4]
]
