"""Chapter 3, Two Presences: two spirits, each in its own room. Name both."""

from casekit import C

CASES = [
    C('3-1', 'The Vicarage, Twice', 'vicarage', ('hearthkeeper', 'draughtling'),
      pool=('draughtling', 'hearthkeeper', 'ledger', 'lullwisp', 'spindle'),
      restless=(('cellar',), ('bedroom',)),
      kit=3, accounts=(('tidy', 'cellar'), ('mover', 'bedroom')),
      client='The Reverend Alder, again',
      intro=('The Reverend is back, and this time there are two of them: one in the cellar keeps things in order, and one in '
             'the bedroom moves them. Two presences, one in each of two rooms. Name both.'),
      ending=('The one in the cellar tends the boiler out of habit, and the one upstairs only wants the window open. They '
              'have never met, which both of them seem to prefer.')),
    # min bag 2, candidates before any reading [2, 3]
    C('3-2', 'The Corner Shop, Again', 'shop', ('scrivener', 'candlewick'),
      pool=('candlewick', 'hushling', 'pacer', 'scrivener', 'tangle'),
      restless=(('store',), ('parlour',)),
      kit=3, accounts=(('curious', 'store'), ('shy', 'parlour')),
      client='Mr Haldane',
      intro=('Mr Haldane has two now: one in the store follows him about, and one in the flat above hides whenever he comes '
             'in. Two presences, one in each of two rooms. Name both.'),
      ending=('The one in the store was only helping with the invoices, and the one upstairs wanted a lit page to read by. Mr '
              'Haldane gave each of them a lamp, and the shop is the better for it.')),
    # min bag 2, candidates before any reading [3, 2]
    C('3-3', 'The Villa Library and Bedroom', 'villa', ('tangle', 'ledger'),
      pool=('candlewick', 'hushling', 'ledger', 'pacer', 'scrivener', 'tangle'),
      restless=(('library',), ('bedroom',)),
      kit=3, accounts=(('curious', 'library'), ('mover', 'bedroom')),
      features={'library': 'desk', 'bedroom': 'wiring'},
      client='Dr Lindqvist',
      intro=("Dr Lindqvist's library has a thread running through it and the bedroom has the linen counted twice. Two "
             'presences, one in each of two rooms. The old writing desk and the wiring do not help.'),
      ending=("The thread was a knitter's, passed hand to hand, and the linen was a shopkeeper's, counted twice for love. Dr "
              'Lindqvist took the thread and left the count.')),
    # min bag 2, candidates before any reading [3, 2]
    C('3-4', 'The Manor Pair', 'manor', ('hushling', 'spindle'),
      pool=('draughtling', 'hushling', 'ledger', 'mothlight', 'scrivener', 'spindle'),
      restless=(('nursery',), ('study',)),
      kit=3, accounts=(('curious', 'nursery'), ('mover', 'study')),
      features={'nursery': 'draught'},
      client='Lady Ferrers',
      intro=('The nursery has a game of hide and seek that nobody started, and the study has buttons moved to the window. '
             'Two presences, one in each of two rooms. The nursery window is very draughty.'),
      ending=('One was a child who wanted to be found, and one was a seamstress who wanted the good light. Lady Ferrers found '
              'the first and moved her chair to the second.')),
    # min bag 2, candidates before any reading [2, 3]
    C('3-5', "The Inn's Two Guests", 'inn', ('hearthkeeper', 'scrivener'),
      pool=('candlewick', 'hearthkeeper', 'hushling', 'ledger', 'lullwisp', 'scrivener'),
      restless=(('taproom',), ('room1',)),
      kit=3, accounts=(('tidy', 'taproom'), ('curious', 'room1')),
      features={'taproom': 'wiring', 'room1': 'streetlamp'},
      client='The Pell family',
      intro=('A taproom where the stools are squared to the bar every night, and Room one where letters are answered and '
             'something follows the maid. Two presences, one in each of two rooms. Wiring in the taproom, a street lamp in '
             'Room one.'),
      ending=("The taproom's was the old landlord's fire-minder, and Room one's was the inn's helpful clerk. The Pells set a "
              'log on the fire and a pen on the desk.')),
    # min bag 2, candidates before any reading [3, 2]
    C('3-6', 'The Farmhouse and the Attic', 'farmhouse', ('draughtling', 'tangle'),
      pool=('draughtling', 'hearthkeeper', 'lullwisp', 'scrivener', 'spindle', 'tangle'),
      restless=(('dairy',), ('attic',)),
      kit=3, accounts=(('mover', 'dairy'), ('curious', 'attic')),
      features={'dairy': 'damp'},
      client='The Marlow sisters',
      intro=('The dairy shifts small things and avoids everyone. The attic follows you up the stairs and hands you wool. Two '
             'presences, one in each of two rooms. The dairy floor is permanently wet.'),
      ending=('A shy one that moves things for the breeze, and a knitter handing out thread. The sisters leave the dairy '
              'window ajar, and take the end of the wool in the attic.')),
    # min bag 2, candidates before any reading [3, 2]
    C('3-7', 'Number Nine, Both Floors', 'terrace', ('candlewick', 'hushling'),
      pool=('candlewick', 'draughtling', 'glimmer', 'hushling', 'scrivener'),
      restless=(('kitchen',), ('nursery',)),
      kit=3, accounts=(('shy', 'kitchen'), ('curious', 'nursery')),
      features={'nursery': 'draught'},
      client='The Ibsen family',
      intro=('The kitchen has a shy someone who reads by one candle. The nursery has a child following everyone about. Two '
             'presences, one in each of two rooms. The nursery window leaks cold.'),
      ending=("A reader by one candle, and a child who wanted to be found. The Ibsens' daughter reads to one and plays with "
              'the other, in that order, every night.')),
    # min bag 2, candidates before any reading [3, 2]
    C('3-8', 'The Mill, Top and Bottom', 'mill', ('ledger', 'spindle'),
      pool=('draughtling', 'ledger', 'lullwisp', 'mothlight', 'pacer', 'spindle', 'tangle'),
      restless=(('workshop',), ('loft',)),
      kit=3, accounts=(('mover', 'workshop'), ('mover', 'loft')),
      features={'workshop': 'paint', 'loft': 'desk'},
      client='Mr Acheson',
      intro=('The workshop moves things and counts them. The loft moves things and sews them. Two presences, one in each of '
             'two rooms. The workshop wall glows with old paint and the loft desk is covered in notes.'),
      ending=('A mill clerk who kept the books and a seamstress who loved one window, both moving small things. Mr Acheson '
              'set a ledger on the workshop bench and a chair in the loft, and they stopped moving things at once.')),
    # min bag 3, candidates before any reading [4, 4]
]
