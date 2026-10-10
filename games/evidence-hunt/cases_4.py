"""Chapter 4, Keepsakes: a keepsake swamps every reading in its room, and looking at it gives one more line of testimony."""

from casekit import C

CASES = [
    C('4-1', 'The Hand Mirror', 'villa', 'glimmer',
      pool=('candlewick', 'draughtling', 'glimmer', 'hushling', 'tangle'),
      restless=(('conservatory', 'bedroom'),),
      kit=3, accounts=(),
      keepsake=('bedroom', 'handmirror', 'curious'),
      client='Ms Thorne, an estate agent',
      intro=('Ms Thorne cannot sell the villa. Pale lights drift through the conservatory and bedroom, and a silver hand '
             'mirror sits on the dresser that nobody admits to owning. Its room will throw off any reading.'),
      ending=('The lights were a lamp-lighter making his rounds, and the mirror was how he checked each room was bright. Ms '
              'Thorne returned it to the dresser. The villa sold to a family who love lamps.')),
    # min bag 2, candidates before any reading [3]
    C('4-2', 'The Music Box', 'manor', 'tangle',
      pool=('draughtling', 'hearthkeeper', 'pacer', 'scrivener', 'tangle'),
      restless=(('nursery', 'parlour'),),
      kit=3, accounts=(),
      keepsake=('nursery', 'musicbox', 'mover'),
      client='Mr Brandt',
      intro=('A small brass music box turns up in a different place every morning, and a thread of wool follows it. The '
             'nursery room it keeps returning to will fool any reading.'),
      ending=('A knitter who kept her music box for company was following the family about with the end of her thread. Mr '
              'Brandt winds the box on Sundays, and the wool has stopped wandering.')),
    # min bag 2, candidates before any reading [3]
    C('4-3', 'The Thimble in Room One', 'inn', 'lullwisp',
      pool=('candlewick', 'ledger', 'lullwisp', 'mothlight', 'scrivener', 'spindle'),
      restless=(('room1', 'room2', 'attic'),),
      kit=3, accounts=(),
      keepsake=('room1', 'thimble', 'tidy'),
      client="Nell Fairweather, the inn's new landlady",
      intro=('Beds made at every hour, windows left open a crack, and a dented silver thimble in Room one that will not stay '
             "in a drawer. The thimble's room swamps every instrument."),
      ending=('A nurse who tucked in every bed still carried her thimble for the buttons. Nell sewed one onto a pillow, and '
              'the beds have been left alone since.')),
    # min bag 2, candidates before any reading [3]
    C('4-4', 'The Brass Key', 'mill', 'pacer',
      pool=('candlewick', 'draughtling', 'pacer', 'scrivener', 'spindle', 'tangle'),
      restless=(('workshop', 'store'),),
      kit=3, accounts=(),
      keepsake=('workshop', 'brasskey', 'mover'),
      client='The Castellano brothers',
      intro=('Footsteps in the workshop and the store, and a worn brass key that migrates from nail to nail. The workshop '
             'where it hangs will not give a clean reading.'),
      ending=('A night worker who walked the floors to settle the building carried the key as proof that every door was '
              'locked. The brothers hung it by the main door, and the footsteps stopped there.')),
    # min bag 2, candidates before any reading [3]
    C('4-5', 'The Paperweight', 'vicarage', 'scrivener',
      pool=('hearthkeeper', 'hushling', 'ledger', 'lullwisp', 'pacer', 'scrivener'),
      restless=(('study', 'bedroom'),),
      kit=3, accounts=(),
      features={'bedroom': 'desk'},
      keepsake=('study', 'paperweight', 'tidy'),
      client='Mrs Duval',
      intro=('The study is tidy past all reason, a glass paperweight is squared to the edge of the desk, and the bedroom has '
             "a desk full of someone else's notes. The study will not give a clean reading."),
      ending=('A letter-writer who answered every note was keeping the pile in order with her paperweight. Mrs Duval set it '
              'on her own letters, and the replies are now both neat and kind.')),
    # min bag 2, candidates before any reading [3]
    C('4-6', 'The Teacup', 'shop', 'mothlight',
      pool=('draughtling', 'hushling', 'ledger', 'lullwisp', 'mothlight', 'scrivener'),
      restless=(('shop', 'parlour'),),
      kit=3, accounts=(),
      features={'shop': 'streetlamp'},
      keepsake=('parlour', 'teacup', 'shy'),
      client='Mr Osei',
      intro=('A chipped blue teacup sits in the flat above the shop, tucked well back, and the street lamp makes the shop '
             'floor useless for readings. Something slips away whenever Mr Osei walks in.'),
      ending=('A lodger drawn to every lit window liked the teacup because it caught the lamplight. Mr Osei moves it to the '
              'front window each evening, and the lodger no longer hides.')),
    # min bag 2, candidates before any reading [3]
    C('4-7', 'The Button Tin', 'farmhouse', 'draughtling',
      pool=('draughtling', 'hushling', 'ledger', 'lullwisp', 'mothlight', 'pacer'),
      restless=(('kitchen', 'dairy'),),
      kit=3, accounts=(('shy', None),),
      features={'kitchen': 'draught'},
      keepsake=('dairy', 'buttontin', 'shy'),
      client='The Whitlock cousins',
      intro=('An old biscuit tin of buttons has been pushed to the back of the dairy shelf, as if it prefers not to be seen. '
             'The kitchen draught is dreadful. The dairy tin will fool every instrument.'),
      ending=('A shy presence that loved an open window kept its buttons in the tin, out of the way. The cousins put it by '
              'the open window, and it keeps itself company.')),
    # min bag 2, candidates before any reading [3]
    C('4-8', 'The Wool Basket', 'hotel', 'hushling',
      pool=('draughtling', 'glimmer', 'hushling', 'ledger', 'pacer', 'scrivener', 'tangle'),
      restless=(('bedroom', 'gallery'),),
      kit=3, accounts=(),
      features={'gallery': 'paint'},
      keepsake=('bedroom', 'woolbasket', 'curious'),
      client='The new manager of the Hotel Marrow',
      intro=('A basket of grey wool follows guests down the corridor of the first floor, always facing the door. The gallery '
             'wall paint glows without being asked. The suite where the basket stays will confuse every reading.'),
      ending=('A child who loved hide and seek used the wool basket to follow people and hide behind. The manager plays one '
              'game a week, and the basket stays in the suite.')),
    # min bag 3, candidates before any reading [4]
]
