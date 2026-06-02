"""
2026 FIFA World Cup qualified teams.
Groups are provisional — update once the official draw groups are confirmed.
"""

TEAMS = [
    # Group A
    {"name": "USA", "code": "USA", "group_name": "A", "confederation": "CONCACAF"},
    {"name": "Panama", "code": "PAN", "group_name": "A", "confederation": "CONCACAF"},
    {"name": "Honduras", "code": "HON", "group_name": "A", "confederation": "CONCACAF"},
    {"name": "Morocco", "code": "MAR", "group_name": "A", "confederation": "CAF"},
    # Group B
    {"name": "Mexico", "code": "MEX", "group_name": "B", "confederation": "CONCACAF"},
    {"name": "Jamaica", "code": "JAM", "group_name": "B", "confederation": "CONCACAF"},
    {"name": "Argentina", "code": "ARG", "group_name": "B", "confederation": "CONMEBOL"},
    {"name": "Chile", "code": "CHI", "group_name": "B", "confederation": "CONMEBOL"},
    # Group C
    {"name": "Canada", "code": "CAN", "group_name": "C", "confederation": "CONCACAF"},
    {"name": "Costa Rica", "code": "CRC", "group_name": "C", "confederation": "CONCACAF"},
    {"name": "Brazil", "code": "BRA", "group_name": "C", "confederation": "CONMEBOL"},
    {"name": "Ecuador", "code": "ECU", "group_name": "C", "confederation": "CONMEBOL"},
    # Group D
    {"name": "Germany", "code": "GER", "group_name": "D", "confederation": "UEFA"},
    {"name": "England", "code": "ENG", "group_name": "D", "confederation": "UEFA"},
    {"name": "Colombia", "code": "COL", "group_name": "D", "confederation": "CONMEBOL"},
    {"name": "Uruguay", "code": "URU", "group_name": "D", "confederation": "CONMEBOL"},
    # Group E
    {"name": "France", "code": "FRA", "group_name": "E", "confederation": "UEFA"},
    {"name": "Spain", "code": "ESP", "group_name": "E", "confederation": "UEFA"},
    {"name": "Nigeria", "code": "NGA", "group_name": "E", "confederation": "CAF"},
    {"name": "Senegal", "code": "SEN", "group_name": "E", "confederation": "CAF"},
    # Group F
    {"name": "Portugal", "code": "POR", "group_name": "F", "confederation": "UEFA"},
    {"name": "Netherlands", "code": "NED", "group_name": "F", "confederation": "UEFA"},
    {"name": "Japan", "code": "JPN", "group_name": "F", "confederation": "AFC"},
    {"name": "South Korea", "code": "KOR", "group_name": "F", "confederation": "AFC"},
    # Group G
    {"name": "Belgium", "code": "BEL", "group_name": "G", "confederation": "UEFA"},
    {"name": "Italy", "code": "ITA", "group_name": "G", "confederation": "UEFA"},
    {"name": "Egypt", "code": "EGY", "group_name": "G", "confederation": "CAF"},
    {"name": "South Africa", "code": "RSA", "group_name": "G", "confederation": "CAF"},
    # Group H
    {"name": "Austria", "code": "AUT", "group_name": "H", "confederation": "UEFA"},
    {"name": "Switzerland", "code": "SUI", "group_name": "H", "confederation": "UEFA"},
    {"name": "Australia", "code": "AUS", "group_name": "H", "confederation": "AFC"},
    {"name": "Saudi Arabia", "code": "KSA", "group_name": "H", "confederation": "AFC"},
    # Group I
    {"name": "Croatia", "code": "CRO", "group_name": "I", "confederation": "UEFA"},
    {"name": "Denmark", "code": "DEN", "group_name": "I", "confederation": "UEFA"},
    {"name": "Iran", "code": "IRN", "group_name": "I", "confederation": "AFC"},
    {"name": "Venezuela", "code": "VEN", "group_name": "I", "confederation": "CONMEBOL"},
    # Group J
    {"name": "Scotland", "code": "SCO", "group_name": "J", "confederation": "UEFA"},
    {"name": "Turkey", "code": "TUR", "group_name": "J", "confederation": "UEFA"},
    {"name": "Paraguay", "code": "PAR", "group_name": "J", "confederation": "CONMEBOL"},
    {"name": "Algeria", "code": "ALG", "group_name": "J", "confederation": "CAF"},
    # Group K
    {"name": "Poland", "code": "POL", "group_name": "K", "confederation": "UEFA"},
    {"name": "Serbia", "code": "SRB", "group_name": "K", "confederation": "UEFA"},
    {"name": "Tunisia", "code": "TUN", "group_name": "K", "confederation": "CAF"},
    {"name": "Bolivia", "code": "BOL", "group_name": "K", "confederation": "CONMEBOL"},
    # Group L
    {"name": "Romania", "code": "ROU", "group_name": "L", "confederation": "UEFA"},
    {"name": "Slovakia", "code": "SVK", "group_name": "L", "confederation": "UEFA"},
    {"name": "Cameroon", "code": "CMR", "group_name": "L", "confederation": "CAF"},
    {"name": "New Zealand", "code": "NZL", "group_name": "L", "confederation": "OFC"},
]

# Quantexa sweepstake participants — processed from contributions CSV
# entry_fee_paid = rounded total; entries = fee / 5
PARTICIPANTS = [
    {"name": "Alex Wood",          "entry_fee_paid": 25.00},  # 5 entries
    {"name": "Molly Atkinson",     "entry_fee_paid": 20.00},  # 4 entries
    {"name": "Harry Reid",         "entry_fee_paid": 20.00},  # 4 entries
    {"name": "Tristan Rowick",     "entry_fee_paid": 20.00},  # 4 entries
    {"name": "Mahamed Ali",        "entry_fee_paid": 15.00},  # 3 entries
    {"name": "John Keightley",     "entry_fee_paid": 15.00},  # 3 entries
    {"name": "Gregory Jones",      "entry_fee_paid": 15.00},  # 3 entries
    {"name": "Alex Cowan",         "entry_fee_paid": 15.00},  # 3 entries
    {"name": "Martin Durchov",     "entry_fee_paid": 10.00},  # 2 entries (rounded from £10.39)
    {"name": "Paris Dean-Vigrass", "entry_fee_paid": 10.00},  # 2 entries
    {"name": "Shyam Bhatt",        "entry_fee_paid": 10.00},  # 2 entries
    {"name": "Ed Hodgskiss",       "entry_fee_paid": 10.00},  # 2 entries
    {"name": "Charlotte Taylor",   "entry_fee_paid": 10.00},  # 2 entries
    {"name": "Will Fox",           "entry_fee_paid": 10.00},  # 2 entries
    {"name": "Mike McDaid",        "entry_fee_paid": 10.00},  # 2 entries
    {"name": "Alex Johnson",       "entry_fee_paid": 10.00},  # 2 entries
    {"name": "Alex Arotsker",      "entry_fee_paid": 10.00},  # 2 entries
    {"name": "Martyn Laidler",     "entry_fee_paid": 10.00},  # 2 entries
    {"name": "Ian Clarke",         "entry_fee_paid": 10.00},  # 2 entries
    {"name": "Manny Lawal",        "entry_fee_paid": 10.00},  # 2 entries
    {"name": "Andrew Jensen",      "entry_fee_paid":  5.00},  # 1 entry
    {"name": "Mark Cossey",        "entry_fee_paid":  5.00},  # 1 entry
    {"name": "Sam Hall",           "entry_fee_paid":  5.00},  # 1 entry
    {"name": "Iain Cooper",        "entry_fee_paid":  5.00},  # 1 entry
    {"name": "Marlon Joseph",      "entry_fee_paid":  5.00},  # 1 entry
    {"name": "Harry Bruce",        "entry_fee_paid":  5.00},  # 1 entry
    {"name": "Alasdair Cross",     "entry_fee_paid":  5.00},  # 1 entry
    {"name": "Will Rice",          "entry_fee_paid":  5.00},  # 1 entry
    {"name": "David Walsh",        "entry_fee_paid":  5.00},  # 1 entry
    {"name": "Tom Sheehy",         "entry_fee_paid":  5.00},  # 1 entry
    {"name": "James Bruce",        "entry_fee_paid":  5.00},  # 1 entry
    {"name": "Ben Willis",         "entry_fee_paid":  5.00},  # 1 entry
]

FUN_CATEGORIES = [
    {
        "name": "Wooden Spoon",
        "emoji": "🥄",
        "description": "The group-stage team with the lowest points and worst goal difference. A prize for the bravest underdog.",
        "calc_key": "wooden_spoon",
        "sort_order": 1,
    },
    {
        "name": "Dirtiest Team",
        "emoji": "🟥",
        "description": "Most disciplinary points across the tournament (yellow=1pt, red=3pts). Tiebreaker: most reds, then most straight reds, then shared.",
        "calc_key": "dirtiest",
        "sort_order": 2,
    },
    {
        "name": "Biggest Losers",
        "emoji": "💔",
        "description": "The team that suffers the biggest single-match defeat by goal difference. Tiebreaker: most goals conceded in that game.",
        "calc_key": "biggest_loser",
        "sort_order": 3,
    },
    {
        "name": "Golden Boot",
        "emoji": "⚽",
        "description": "The team whose player wins the FIFA Golden Boot (tournament top scorer). Admin assigns this at the end.",
        "calc_key": None,
        "sort_order": 4,
    },
    {
        "name": "Best Defense",
        "emoji": "🧱",
        "description": "The team that concedes the fewest goals across the whole tournament before being eliminated (or wins it all).",
        "calc_key": "best_defense",
        "sort_order": 5,
    },
    {
        "name": "Penalty Kings",
        "emoji": "🎯",
        "description": "The team that wins the most penalty shootouts across the knockout stages. Sudden death glory.",
        "calc_key": "penalty_kings",
        "sort_order": 6,
    },
    {
        "name": "Cinderella Story",
        "emoji": "🪄",
        "description": "The team that defies all expectations — furthest run from the lowest pre-tournament ranking. Admin picks this one.",
        "calc_key": None,
        "sort_order": 7,
    },
    {
        "name": "Hat-trick Heroes",
        "emoji": "🎩",
        "description": "The team whose player is first to score a hat-trick in the tournament. Admin assigns when it happens.",
        "calc_key": None,
        "sort_order": 8,
    },
    {
        "name": "First Blood",
        "emoji": "⚡",
        "description": "The team that scores the very first goal of WC 2026. Pure luck — anyone's game. The clock starts at kick-off on 11 June.",
        "calc_key": "first_blood",
        "sort_order": 9,
    },
    {
        "name": "Comeback Kings",
        "emoji": "🔄",
        "description": "The team that wins the most matches after being behind at half-time. Classic underdog spirit — never say die.",
        "calc_key": "comeback_kings",
        "sort_order": 10,
    },
    {
        "name": "Fair Play",
        "emoji": "🕊️",
        "description": "The team with the fewest disciplinary points across the whole tournament (yellow=1, red=3). Rewards discipline over dirty play. Tiebreaker: fewest reds.",
        "calc_key": "fairest",
        "sort_order": 11,
    },
]
