"""Hull Repair -- authored boards (frozen from tools/gen.py; every one is proven unique by tests)."""

DOCK = [
    {
        "id": 'airlock-two', "name": 'Airlock Two',
        "rows": ['...A.', '.e.b.', '..c..', 'B..Ca', 'DdEFf'],
        "sol": 'A3040414243;B0302010010202131;C333222;D0414;E2423131211;F3444',
    },
    {
        "id": 'cargo-hold', "name": 'Cargo Hold',
        "rows": ['...d.', '.b.c.', '..aA.', '.BCD.', '...eE'],
        "sol": 'A3222;B131211;C232414040302010010202131;D334342414030;E4434',
    },
    {
        "id": 'tool-locker', "name": 'Tool Locker',
        "rows": ['.AB..', 'a.d..', '....c', '.b.C.', '....D'],
        "sol": 'A100001;B203040413132222313;C334342;D44342414040302121121',
    },
    {
        "id": 'suit-room', "name": 'Suit Room',
        "rows": ['.....', '..A..', 'B...C', '..bc.', '..a..'],
        "sol": 'A2111121303041424;B020100102030404131322223;C4243443433',
    },
    {
        "id": 'dock-control', "name": 'Dock Control',
        "rows": ['A.....', '.BCc..', '..dDbf', 'E...F.', '....ae', 'gG....'],
        "sol": 'A000102121323333444;B111020304050514142;C2131;D3222;E030414242535455554;F435352;G1505',
    },
    {
        "id": 'cargo-lift', "name": 'Cargo Lift',
        "rows": ['...Ac.', '..deBC', '.DE...', '....a.', 'F.fgG.', 'b.....'],
        "sol": 'A3020100001020313233343;B4142525354554535251505;C515040;D121121;E223231;F041424;G4434',
    },
    {
        "id": 'waiting-lounge', "name": 'Waiting Lounge',
        "rows": ['...Ad.', '.Bac..', '..ef..', '..C..D', '.E.F..', '.b....'],
        "sol": 'A302021;B111000010203040515;C232425354555544443424131;D5352515040;E14131222;F343332',
    },
    {
        "id": 'mail-room', "name": 'Mail Room',
        "rows": ['...a..', '.AB...', 'C..De.', 'Ec.b..', '......', '..d...'],
        "sol": 'A110100102030;B21222333;C021213;D32314140505152535455453525;E03040515142434444342',
    },
]
