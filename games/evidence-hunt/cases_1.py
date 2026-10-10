"""Chapter 1, First Visits: houses that grow from three rooms to seven. Read the sheet, walk the rooms, pick a bag, name the spirit."""

from casekit import C

CASES = [
    C('1-1', 'The Quiet Cottage', 'cottage', 'hearthkeeper',
      pool=('candlewick', 'hearthkeeper', 'pacer'),
      restless=(('parlour',),),
      kit=3, accounts=(),
      client='Mrs Oake, who has lived here sixty years',
      intro=('Mrs Oake says the parlour feels looked after, which is odd, since she lives alone. Her tea goes cold quicker '
             'than it should. She would like to know who is keeping her company.'),
      ending=('It was the housekeeper who kept the fire in for the old owners, and she only wants to be sure the hearth is '
              'swept. Mrs Oake sweeps it twice a day now, and the parlour has never been so warm.')),
    # min bag 1, candidates before any reading [2]
    C('1-2', 'The Lodge by the Gate', 'lodge', 'scrivener',
      pool=('candlewick', 'mothlight', 'scrivener'),
      restless=(('den',),),
      kit=3, accounts=(),
      client='Mr Anand, the new gatekeeper',
      intro=('Mr Anand keeps finding his letters answered. Neatly, in handwriting that is not his, on the days the post '
             'comes.'),
      ending=("A letter-writer who kept the estate's post stayed on in the den, still being helpful. Mr Anand leaves a pad on "
              'the desk each evening, and the replies are polite, brief and very good.')),
    # min bag 1, candidates before any reading [2]
    C('1-3', 'The Bungalow on Marsh Road', 'bungalow', 'draughtling',
      pool=('candlewick', 'draughtling', 'hearthkeeper', 'tangle'),
      restless=(('bedroom',),),
      kit=3, accounts=(('mover', None),),
      client='Dee, who moved in last week',
      intro=("Dee's mugs keep ending up on the other shelf, and the back bedroom is always a little breezy. She would like "
             'the breeze to introduce itself.'),
      ending=('A small, shy presence that loved an open window had only moved what stood in the way of the breeze. Dee props '
              'the sash open an inch, and the mugs stay where she puts them.')),
    # min bag 1, candidates before any reading [2]
    C('1-4', 'The Flat Over the Chemist', 'flat', 'glimmer',
      pool=('draughtling', 'glimmer', 'hushling', 'mothlight'),
      restless=(('parlour', 'pantry'),),
      kit=3, accounts=(),
      client='Mr Voss, a night-shift baker',
      intro=('Mr Voss sees small lights in his photographs of the parlour and the pantry. They are in no other room, and '
             'they are very polite about it.'),
      ending=('A lamp-lighter who walked the building at dusk was still making his rounds. The lights follow Mr Voss because '
              'he never could leave anyone in the dark. Mr Voss leaves a lamp on in the hall, and the rounds are shorter.')),
    # min bag 2, candidates before any reading [4]
    C('1-5', 'The Terrace at Number Nine', 'terrace', 'candlewick',
      pool=('candlewick', 'draughtling', 'ledger', 'spindle'),
      restless=(('nursery',),),
      kit=3, accounts=(('shy', None),),
      client='The Ibsen family',
      intro=('Their daughter says the nursery has a reading lamp nobody lit. Candle wax on the sill, she adds, but no '
             'candle.'),
      ending=('A reader who spent forty winters in one chair by one candle was glad of the company. The Ibsens put a proper '
              'lamp by the chair, and their daughter reads aloud to it, a chapter a night.')),
    # min bag 1, candidates before any reading [2]
    C('1-6', 'The Old Schoolhouse', 'schoolhouse', 'pacer',
      pool=('candlewick', 'hushling', 'ledger', 'pacer', 'tangle'),
      restless=(('classroom', 'boiler'),),
      kit=3, accounts=(('mover', None),),
      client='Ms Okafor, for the village hall committee',
      intro=('The committee is turning the schoolhouse into a hall. The classroom has prints in the chalk dust on mornings '
             'after the heating was off, and the boiler room ticks at night.'),
      ending=("A night caretaker who paced the corridors to settle the building's creaks was pacing them still. The committee "
              'mended the loose board and left a stool in the corridor. The pacing stopped on a Tuesday, because there was '
              'finally somewhere to sit.')),
    # min bag 2, candidates before any reading [3]
    C('1-7', 'The Farm at Three Elms', 'farmhouse', 'tangle',
      pool=('glimmer', 'ledger', 'scrivener', 'spindle', 'tangle'),
      restless=(('dairy', 'attic'),),
      kit=3, accounts=(('curious', None),),
      client='The Marlow sisters',
      intro=("The sisters' wool turns up in the dairy and the attic wound into neat balls, one end always pointing at "
             'whoever is nearest.'),
      ending=('A knitter who handed everyone the end of the thread had gone years without anyone to hand it to. The sisters '
              'took it in turns, and the Marlows now have more scarves than they have necks.')),
    # min bag 2, candidates before any reading [3]
    C('1-8', 'The Vicarage on the Hill', 'vicarage', 'lullwisp',
      pool=('glimmer', 'ledger', 'lullwisp', 'scrivener', 'tangle'),
      restless=(('cellar', 'landing', 'bedroom'),),
      kit=3, accounts=(('tidy', None),),
      client='The Reverend Alder',
      intro=('From the cellar to the bedroom, someone is tucking in the beds, folding the blankets and leaving every window '
             'open a crack. The Reverend suspects a draught with excellent manners.'),
      ending=('A nurse who tucked in every bed in every room was still doing her rounds. The Reverend thanks her at the '
              'cellar door each night, and leaves one window open a crack, for air.')),
    # min bag 2, candidates before any reading [3]
]
