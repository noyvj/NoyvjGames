"""Chapter 2, Misleading Readings: a room's own feature can make a reading look positive. Trust the room the house does not fool."""

from casekit import C

CASES = [
    C('2-1', 'The Draught on Ash Street', 'terrace', 'mothlight',
      pool=('draughtling', 'glimmer', 'hearthkeeper', 'hushling', 'mothlight'),
      restless=(('bedroom', 'kitchen'),),
      kit=3, accounts=(('shy', None),),
      features={'bedroom': 'draught', 'nursery': 'wiring'},
      client='Mrs Kamara',
      intro=('A bedroom that is cold in August, and a kitchen where pale lights hang in the photographs. Mrs Kamara has '
             'already blamed the window. The window is, in fairness, quite draughty.'),
      ending=('The bedroom was cold because of the window, as Mrs Kamara said, and the lights were a shy lodger drawn to '
              'every lit window in the house. She apologises to the window and leaves the kitchen light on.')),
    # min bag 2, candidates before any reading [3]
    C('2-2', 'The Corner Shop', 'shop', 'ledger',
      pool=('draughtling', 'ledger', 'lullwisp', 'scrivener', 'spindle'),
      restless=(('store',),),
      kit=3, accounts=(('mover', None),),
      features={'store': 'wiring', 'shop': 'damp'},
      client='Mr Haldane',
      intro=('The shelves are put in order overnight, and the stock is always one shelf out. The storeroom wiring hums and '
             'the shop floor is damp, so Mr Haldane has stopped trusting his instruments.'),
      ending=('A shopkeeper who kept the books in perfect order and the stock always one shelf out had never stopped working. '
              'Mr Haldane lets him move one tin a night. Takings are up.')),
    # min bag 2, candidates before any reading [3]
    C('2-3', 'The Cloakroom Hooks', 'schoolhouse', 'hushling',
      pool=('hushling', 'mothlight', 'pacer', 'scrivener', 'tangle'),
      restless=(('classroom', 'cloaks'),),
      kit=3, accounts=(('curious', None),),
      features={'classroom': 'draught', 'cloaks': 'damp'},
      client='Ms Rivera, head teacher',
      intro=('Names are traced in the dust, and something follows the caretaker down the corridor and then hides behind the '
             'coats. The old window leaks cold air and the floor is damp enough to spoil any footprint.'),
      ending=('The child who loved hide and seek wanted to be found. Ms Rivera counts to twenty at the cloakroom door every '
              'Friday, loudly, and finds a very pleased coat.')),
    # min bag 2, candidates before any reading [3]
    C('2-4', 'The Back Parlour', 'farmhouse', 'spindle',
      pool=('candlewick', 'glimmer', 'pacer', 'spindle', 'tangle'),
      restless=(('parlour',),),
      kit=3, accounts=(),
      features={'parlour': 'desk', 'dairy': 'draught'},
      client='Mr and Mrs Teague',
      intro=('There is one lovely window, one writing desk and, each morning, a pile of thread and buttons moved to the '
             "window. The desk is full of someone else's old notes, which is not helping."),
      ending=('A seamstress who loved one room for its light moved her thread to the good window. The Teagues put a sewing '
              'chair there, and the buttons are sorted by colour by morning.')),
    # min bag 2, candidates before any reading [3]
    C('2-5', "The Villa's Spare Room", 'villa', 'draughtling',
      pool=('draughtling', 'hearthkeeper', 'ledger', 'mothlight', 'pacer', 'scrivener'),
      restless=(('bedroom', 'bathroom'),),
      kit=3, accounts=(('mover', None),),
      features={'bedroom': 'wiring', 'bathroom': 'damp'},
      client='Dr Lindqvist',
      intro=('The bedroom wiring hums and the bathroom floor is always damp, so Dr Lindqvist cannot tell which odd readings '
             'are the house and which are the guest.'),
      ending=('A shy little presence moved small things to make room for the breeze. Dr Lindqvist now opens the bathroom '
              'window, and finds the soap where it should be.')),
    # min bag 2, candidates before any reading [3]
    C('2-6', 'The Manor Nursery', 'manor', 'glimmer',
      pool=('glimmer', 'hushling', 'ledger', 'pacer', 'spindle', 'tangle'),
      restless=(('nursery', 'landing'),),
      kit=3, accounts=(('curious', None),),
      features={'nursery': 'paint', 'landing': 'streetlamp'},
      client='Lady Ferrers',
      intro=('Glow paint on the nursery walls, a street lamp that looks straight in at the landing, and pale lights in every '
             'photograph. Lady Ferrers says a spirit that wanted to be noticed would at least be unambiguous.'),
      ending=('A lamp-lighter who walked the whole house each evening only wanted the rooms bright. Lady Ferrers had the '
              'landing light turned up a notch, and the photographs went plain again.')),
    # min bag 2, candidates before any reading [3]
    C('2-7', 'The Coaching Inn', 'inn', 'scrivener',
      pool=('draughtling', 'hushling', 'lullwisp', 'pacer', 'scrivener', 'tangle'),
      restless=(('room2',),),
      kit=3, accounts=(('curious', None),),
      features={'room2': 'desk', 'cellar': 'damp'},
      client='The Pell family',
      intro=("Room two has a writing desk covered in the last guest's notes, and the beer cellar is as damp as a well. "
             'Letters are being answered in the hall, and the Pells would like to know by whom.'),
      ending=("The inn's old clerk had answered every letter ever left on the mat and could not stop tidying the post. The "
              'Pells leave him one letter a night, and he is delighted.')),
    # min bag 2, candidates before any reading [3]
    C('2-8', 'The Vicarage Study', 'vicarage', 'tangle',
      pool=('hushling', 'lullwisp', 'mothlight', 'pacer', 'scrivener', 'tangle'),
      restless=(('study', 'dining'),),
      kit=3, accounts=(('curious', None),),
      features={'study': 'wiring', 'dining': 'streetlamp', 'cellar': 'paint'},
      client='The Reverend Moore',
      intro=('Wiring in the study, a street lamp at the dining room window and glow paint in the cellar, which turns out to '
             'be just paint. Things move. Something follows the Reverend about. He suspects a very long thread.'),
      ending=('A knitter was handing out the end of her thread to everyone she met. The Reverend takes it, politely, and '
              'wears the result.')),
    # min bag 2, candidates before any reading [3]
]
