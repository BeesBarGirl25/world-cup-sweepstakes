"""
2026 FIFA World Cup qualified teams.
Groups are provisional — update once the official draw groups are confirmed.
"""

# Keyed by ESPN team abbreviation (matches the codes we seed below).
FLAG_EMOJIS = {
    "MEX": "🇲🇽", "CZE": "🇨🇿", "KOR": "🇰🇷", "RSA": "🇿🇦",
    "CAN": "🇨🇦", "BIH": "🇧🇦", "SUI": "🇨🇭", "QAT": "🇶🇦",
    "BRA": "🇧🇷", "SCO": "🏴󠁧󠁢󠁳󠁣󠁴󠁿", "HAI": "🇭🇹", "MAR": "🇲🇦",
    "PAR": "🇵🇾", "TUR": "🇹🇷", "AUS": "🇦🇺", "USA": "🇺🇸",
    "ECU": "🇪🇨", "GER": "🇩🇪", "CIV": "🇨🇮", "CUW": "🇨🇼",
    "NED": "🇳🇱", "SWE": "🇸🇪", "JPN": "🇯🇵", "TUN": "🇹🇳",
    "BEL": "🇧🇪", "IRN": "🇮🇷", "EGY": "🇪🇬", "NZL": "🇳🇿",
    "ESP": "🇪🇸", "URU": "🇺🇾", "KSA": "🇸🇦", "CPV": "🇨🇻",
    "NOR": "🇳🇴", "FRA": "🇫🇷", "SEN": "🇸🇳", "IRQ": "🇮🇶",
    "ARG": "🇦🇷", "AUT": "🇦🇹", "ALG": "🇩🇿", "JOR": "🇯🇴",
    "COL": "🇨🇴", "POR": "🇵🇹", "UZB": "🇺🇿", "COD": "🇨🇩",
    "ENG": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "CRO": "🇭🇷", "PAN": "🇵🇦", "GHA": "🇬🇭",
}

# 🥚 Easter egg: each flag on a country profile links to that nation's
# football song / chant. YouTube search links so they never rot.
def _yt(q):
    from urllib.parse import quote_plus
    return "https://www.youtube.com/results?search_query=" + quote_plus(q)

TEAM_SONGS = {
    "ENG": ("🦁 Three Lions — It's Coming Home", _yt("three lions football's coming home")),
    "SCO": ("🎉 No Scotland, No Party!", _yt("no scotland no party yes sir i can boogie")),
    "ARG": ("🇦🇷 Muchachos", _yt("muchachos ahora nos volvimos a ilusionar")),
    "BRA": ("🥁 Brazil Samba", _yt("brazil world cup samba torcida")),
    "NED": ("🟧 Wij Houden van Oranje", _yt("wij houden van oranje andre hazes")),
    "USA": ("🦅 Born in the U.S.A.", _yt("born in the usa bruce springsteen")),
    "GER": ("🇩🇪 54, 74, 90, 2010", _yt("54 74 90 2010 sportfreunde stiller")),
    "FRA": ("🇫🇷 La Marseillaise", _yt("la marseillaise hymne national")),
    "MEX": ("🎺 Cielito Lindo", _yt("cielito lindo mexico")),
    "ESP": ("💃 Y Viva España", _yt("y viva espana")),
    "JPN": ("⚽ Samurai Blue", _yt("japan samurai blue supporters chant")),
    "KOR": ("🇰🇷 Be the Reds!", _yt("be the reds korea world cup")),
}

TEAM_FACTS = {
    "USA": [
        "Hosting WC 2026 on home soil — their biggest football moment since the 1994 tournament they also hosted.",
        "Beat England 1–0 in 1950 in one of football's greatest ever upsets. England were joint favourites.",
        "Christian Pulisic — nicknamed 'Captain America' — became the first American to score in a WC knockout game at Qatar 2022.",
    ],
    "PAN": [
        "Their first ever World Cup was 2018 Russia — they lost all 3 group games but the whole nation celebrated just being there.",
        "Román Torres scored a last-minute qualifier vs USA in 2017 that sent Panama to their first WC. Panama declared a national holiday.",
        "Their WC campaign in 2018 included a famous 6–1 loss to England, but goalkeeper Jaime Penedo saved a penalty from Harry Kane.",
    ],
    "HON": [
        "Only national team linked to an actual war — the 1969 'Football War' with El Salvador was triggered by a World Cup qualifier.",
        "Have never won a World Cup match across three appearances (1982, 2010, 2014) — but their fans are among the most passionate in CONCACAF.",
        "Wilson Palacios — their most famous modern player — played for Tottenham and was renowned for his never-say-die attitude.",
    ],
    "MAR": [
        "First African AND Arab nation ever to reach a World Cup semi-final — at Qatar 2022, beating Spain and Portugal along the way.",
        "Goalkeeper Yassine Bounou ('Bono') saved TWO penalties in the shootout vs Spain in the Round of 16. Ice cold.",
        "Half their squad were born or raised in Europe but chose Morocco — their unity became the story of the 2022 tournament.",
    ],
    "MEX": [
        "El Tri are co-hosts of WC 2026 — their THIRD time hosting the World Cup (1970 and 1986 also).",
        "Knocked out at the Round of 16 for SEVEN consecutive tournaments before 2022 — the infamous 'Quinto Partido' (fifth match) curse.",
        "Scored after just 36 minutes vs Germany at WC 2018 — Germany didn't qualify from the group. Mexico celebrated like they'd won it.",
    ],
    "JAM": [
        "Their only World Cup was 1998 France — they beat Japan 2–1 but it was their first and only WC win.",
        "First Caribbean nation ever to qualify for a World Cup — a landmark moment for the region.",
        "Robbie Earle — their cult hero — famously had his complimentary tickets seized after giving them to 50 Robbie Earle lookalikes.",
    ],
    "ARG": [
        "Reigning World Champions! Lionel Messi finally lifted the trophy at Qatar 2022 after three previous heartbreaks.",
        "Diego Maradona's 'Hand of God' goal vs England in 1986 is the most controversial moment in World Cup history.",
        "Argentina have won 3 World Cups (1978, 1986, 2022) — and lost three finals (1930, 1990, 2014).",
    ],
    "CHI": [
        "Hosted the 1962 World Cup and finished 3rd — still their best ever achievement at the tournament.",
        "Won back-to-back Copa Américas in 2015 and 2016 — beating Argentina in both finals on penalties.",
        "Beat then-defending champions Spain 2–0 at WC 2014, ending their title defence in the group stage.",
    ],
    "CAN": [
        "Co-hosts of WC 2026 and only their second ever WC appearance — their first in 1986 ended without scoring a single goal.",
        "Alphonso Davies went from a Ghanaian refugee camp to Bayern Munich via Canada — one of football's most remarkable stories.",
        "Topped the CONCACAF qualifying table in 2022 for the first time ever, conceding just 7 goals in 14 games.",
    ],
    "CRC": [
        "Reached the quarter-finals at WC 2014 in Brazil — beating Uruguay, Italy and Greece before losing to Holland on penalties.",
        "Goalkeeper Keylor Navas won THREE Champions Leagues with Real Madrid after his heroics at WC 2014 made him world-famous.",
        "Known as 'Los Ticos' — they punch massively above their weight for a nation of just 5 million people.",
    ],
    "BRA": [
        "Most World Cup wins ever: 5 titles (1958, 1962, 1970, 1994, 2002) — the only team to have won it on four different continents.",
        "Only nation to have played in EVERY single World Cup — all 23 editions.",
        "Pelé won the WC at just 17 years old in 1958 — scoring twice in the final — and is still Brazil's all-time top scorer.",
    ],
    "ECU": [
        "Knocked out hosts Qatar in the very first match of WC 2022 — winning 2–0 with Enner Valencia scoring both goals.",
        "Only their 4th World Cup appearance — they've qualified in 2002, 2006, 2014 and now 2026 (2022 too!).",
        "Enner Valencia scored 3 of their 4 goals at WC 2014 in Brazil — became a national legend overnight.",
    ],
    "GER": [
        "4 World Cup wins (1954, 1974, 1990, 2014) — the most by a European nation.",
        "Demolished Brazil 7–1 in the 2014 semi-final in Belo Horizonte — a result so shocking it traumatised an entire nation.",
        "Were knocked out in the group stage at both WC 2018 AND 2022 — their worst consecutive run since before WW2.",
    ],
    "ENG": [
        "Won one World Cup — in 1966 at Wembley. 'It's Coming Home' has been their anthem for every tournament since.",
        "Famously missed penalty after penalty in shootouts for decades... until finally winning one vs Colombia at WC 2018.",
        "Bobby Moore, their 1966 captain, is still the only Englishman ever to lift the World Cup. He died aged just 51.",
    ],
    "COL": [
        "James Rodríguez's volley vs Uruguay at WC 2014 won FIFA Goal of the Tournament — arguably the best WC goal of the decade.",
        "Their 1994 squad were threatened before the tournament and Andrés Escobar was murdered after scoring an own goal. Football's darkest moment.",
        "Carlos Valderrama — with the most iconic afro in football history — captained them to back-to-back Round of 16 appearances.",
    ],
    "URU": [
        "Won the FIRST ever World Cup in 1930, on home soil — and also won in 1950, knocking out Brazil in the final game.",
        "Most World Cup wins relative to population of any nation — 3.4 million people, 2 world titles.",
        "Luis Suárez bit Italian Giorgio Chiellini at WC 2014 — earning a 4-month global ban. Uruguay went out in the next round.",
    ],
    "FRA": [
        "2-time World Cup winners (1998 on home soil, 2018 in Russia) — with one of the most gifted squads in football history.",
        "Lost the 2022 final to Argentina on penalties in the most dramatic WC final ever — Mbappé scored a hat-trick and still lost.",
        "Zinedine Zidane headbutted Marco Materazzi in the 2006 final — then walked off to a standing ovation. France still lost.",
    ],
    "ESP": [
        "Won WC 2010 with a 1–0 final win over Netherlands — Andrés Iniesta's 116th-minute winner was football perfection.",
        "Dominated world football 2008–2012 with 'tiki-taka' — Euro 2008, WC 2010, Euro 2012 back-to-back-to-back.",
        "Were shockingly knocked out by Japan in the WC 2022 group stage despite finishing level on points with Germany.",
    ],
    "NGA": [
        "The 'Super Eagles' — Africa's most-watched team with over 200 million passionate fans behind every match.",
        "Reached the Round of 16 in their first three WC appearances (1994, 1998, 2014) — a remarkable record on debut.",
        "Jay-Jay Okocha was 'so good they named him twice' — one of the most skilful players ever to grace the World Cup.",
    ],
    "SEN": [
        "Beat reigning champions France in the opening match of WC 2002 — one of the greatest WC upsets ever.",
        "Reached the quarter-finals at WC 2002 — Africa's joint-best performance at the time.",
        "Sadio Mané led them to their first ever Africa Cup of Nations title in 2022 — a defining moment for a generation.",
    ],
    "POR": [
        "Eusébio — the 'Black Panther' — scored 9 goals at the 1966 WC and was voted tournament best player.",
        "Cristiano Ronaldo has played at 5 World Cups but never progressed beyond the quarter-finals. His great regret.",
        "Their best finish remains 3rd place in 1966 — nearly 60 years ago and the monkey still isn't off their back.",
    ],
    "NED": [
        "Three WC finals, zero wins — 1974 (Germany), 1978 (Argentina), 2010 (Spain). The greatest team never to win it.",
        "Johan Cruyff and 'Total Football' in 1974 revolutionised how the entire world plays the beautiful game.",
        "'Clockwork Orange' — their nickname from that 1974 campaign — is the most iconic WC team identity ever.",
    ],
    "JPN": [
        "Beat both Germany AND Spain at WC 2022 — the two biggest upsets of the tournament.",
        "Legendary for their 'Blue Samurai' spirit and for having fans clean the stadium after every single match.",
        "Lost to Croatia only on penalties in the last 16 at WC 2022 — arguably should have gone much further.",
    ],
    "KOR": [
        "Co-hosts in 2002 who reached the SEMI-FINALS — one of the greatest WC fairy tales ever told.",
        "Beat Spain in a penalty shootout at WC 2022 — Korea's reputation as giant-killers lives on.",
        "Son Heung-min — Tottenham's greatest ever player — leads them as captain and is their all-time top scorer.",
    ],
    "BEL": [
        "Held the FIFA #1 ranking for over 3 years — the so-called 'Golden Generation' that never won a single major trophy.",
        "3rd place at WC 2018 in Russia — best ever finish — beating Brazil in the quarter-finals.",
        "De Bruyne, Lukaku, Hazard — all at their peak at the same time. And still nothing. Football can be cruel.",
    ],
    "ITA": [
        "4 World Cup wins (1934, 1938, 1982, 2006) — second only to Brazil for most titles.",
        "Shockingly failed to qualify for both WC 2018 AND WC 2022 — their worst period since the 1930s.",
        "Marco Tardelli's screaming celebration after scoring in the 1982 final is one of football's most iconic moments ever.",
    ],
    "EGY": [
        "Record 7-time Africa Cup of Nations winners — more than any other nation on the continent.",
        "Mohamed Salah — one of the world's best players — finally gets a proper World Cup stage to perform on.",
        "Their last WC appearance was 2018 — they lost all 3 games. But this squad is vastly different.",
    ],
    "RSA": [
        "Hosted WC 2010 — the first African nation ever to do so.",
        "Siphiwe Tshabalala's thunderbolt opener vs Mexico was voted one of the top 10 WC goals of all time.",
        "'Bafana Bafana' (The Boys The Boys) — agonisingly knocked out of their own home World Cup in the group stage.",
    ],
    "AUT": [
        "Finished 3rd at the 1954 World Cup — a Golden Era they've been chasing ever since.",
        "David Alaba — one of Europe's finest defenders — captains Austria and plays for Real Madrid.",
        "Their famous 'Wunderteam' of the 1930s were one of the first truly great international sides in football history.",
    ],
    "SUI": [
        "Reached the quarter-finals at WC 2022 — their best run in decades, beating Serbia along the way.",
        "Xherdan Shaqiri scored a spectacular bicycle kick vs Serbia at WC 2018 then did a controversial double-eagle celebration.",
        "Swiss law means their players can represent Switzerland AND their parents' home nation — giving them incredible squad depth.",
    ],
    "AUS": [
        "The Socceroos reached the Round of 16 at WC 2022 — beating Denmark in a tense group decider.",
        "Tim Cahill's volley vs Netherlands at WC 2014 is regularly voted the greatest WC goal of the 21st century.",
        "Lost to eventual champions Argentina in the last 16 at WC 2022 — but made them work hard for every inch.",
    ],
    "KSA": [
        "Beat eventual WC 2022 champions Argentina 2–1 — one of the biggest shocks in WC history. The whole Arab world stopped.",
        "Saudi fans stayed in the stadium for hours after beating Argentina — waving flags and refusing to leave.",
        "Sami Al-Jaber played at 4 World Cups for Saudi Arabia — a true legend of Asian and world football.",
    ],
    "CRO": [
        "Runners-up at WC 2018 — the smallest nation by population (just 4 million) to reach a final since 1950.",
        "Luka Modrić won the Golden Ball (Best Player) at WC 2018 — breaking the Messi/Ronaldo stranglehold on football awards.",
        "Beat Brazil on penalties at WC 2022 before losing to Argentina in the semis. Never go quietly.",
    ],
    "DEN": [
        "Won Euro 1992 without even qualifying — Yugoslavia were banned and Denmark came in as last-minute replacements. Then won it.",
        "Peter Schmeichel — arguably the greatest goalkeeper in Premier League history — captained Denmark at WC 1998.",
        "Christian Eriksen suffered a cardiac arrest at Euro 2020, was resuscitated on the pitch, and returned to play international football.",
    ],
    "IRN": [
        "Beat USA 2–1 at WC 1998 in one of football's most politically charged matches — the whole Middle East celebrated.",
        "Carlos Queiroz — ex-Real Madrid and Portugal coach — has managed Iran multiple times and turned them into Asian powerhouses.",
        "Ali Daei held the men's international scoring record at 109 goals for 16 years — until Cristiano Ronaldo finally overtook it.",
    ],
    "VEN": [
        "Making their FIRST EVER World Cup appearance in 2026 — a historic moment for Venezuelan football.",
        "Nicknamed 'La Vinotinto' (The Red Wine) after their distinctive dark maroon kit — one of football's most striking colours.",
        "Qualified despite playing in the world's toughest regional qualification — CONMEBOL, home to Brazil, Argentina and Uruguay.",
    ],
    "SCO": [
        "Have qualified for 8 World Cups but never made it past the group stage — often eliminated by tiny margins and gut-wrenching results.",
        "Archie Gemmill's solo goal vs Netherlands at WC 1978 is the most celebrated moment in Scottish football history.",
        "Denis Law, Kenny Dalglish and Graeme Souness — Scotland produced some of football's greatest ever players but never the WC glory.",
    ],
    "TUR": [
        "Finished 3rd at WC 2002 — their best ever finish — beating co-host South Korea in the 3rd place play-off.",
        "Hakan Şükür scored after just 11 seconds vs South Korea in 2002 — still the fastest goal in WC history.",
        "Returning to the WC after a 24-year absence — their passionate fans will make noise wherever they play.",
    ],
    "PAR": [
        "Reached the quarter-finals at WC 2010 — still their best ever achievement at a World Cup.",
        "Goalkeeper José Luis Chilavert scored 8 international goals — from free kicks and penalties. A genuine celebrity.",
        "Famous for drawing all three group games at WC 2010 and still qualifying — the masters of the hard-earned point.",
    ],
    "ALG": [
        "Beat West Germany at WC 1982 — considered one of the greatest upsets in WC history at the time.",
        "Reached the Round of 16 at WC 2014, losing to Germany in extra time after a hard-fought, goalless 90 minutes.",
        "Riyad Mahrez won the AFCON with Algeria in 2019 and the Premier League with Manchester City in 2021 and 2022.",
    ],
    "POL": [
        "Finished 3rd at WC 1974 AND 1982 — their golden generation with the legendary Zbigniew Boniek.",
        "Robert Lewandowski finally scored at a World Cup in 2022, ending years of tournament goal drought and heartbreak.",
        "Were knocked out by eventual champions France in the Round of 16 at WC 2022 — beaten by the best team in the world.",
    ],
    "SRB": [
        "As Yugoslavia, they were one of the founding nations of the World Cup in 1930, finishing 4th in that inaugural tournament.",
        "Dušan Vlahović and Aleksandar Mitrović — two of Europe's deadliest strikers — lead a generation with genuine ambition.",
        "Beat Cameroon 3–2 at WC 2022 in one of the tournament's most entertaining group games.",
    ],
    "TUN": [
        "First African nation to win a World Cup match — beat Mexico 3–1 in 1978. A landmark moment for African football.",
        "Had a goal against France ruled out in literally the last second of stoppage time at WC 2022 — sporting heartbreak.",
        "Wahbi Khazri was their talisman at WC 2018 — scored against Belgium but couldn't stop them going out in the group stage.",
    ],
    "BOL": [
        "Play home games in La Paz at 3,600 metres altitude — visiting teams genuinely struggle to breathe and often can't run.",
        "Won the Copa América in 1963 on home soil — still their only major trophy in over 60 years of trying.",
        "Beat Argentina 6–1 in 2009 World Cup qualifying — one of the most shocking results in South American football history.",
    ],
    "ROU": [
        "Gheorghe Hagi — 'The Maradona of the Carpathians' — led Romania to the quarter-finals of WC 1994 in USA.",
        "Beat Argentina AND Colombia at WC 1994 in one of the tournament's greatest group stage performances.",
        "Ianis Hagi (Gheorghe's son!) now leads a new generation of Romanian talent with genuine WC ambitions.",
    ],
    "SVK": [
        "Made their debut as an independent nation at WC 2010 — immediately beating holders Italy 3–2. What an entrance.",
        "Martin Škrtel — their most famous recent player — was one of the Premier League's most fearsome defenders at Liverpool.",
        "Marek Hamšík captained them across multiple tournaments — a midfield maestro who played most of his career in Italy.",
    ],
    "CMR": [
        "The 'Indomitable Lions' — reached the quarter-finals at WC 1990, the first African team ever to do so.",
        "Roger Milla came out of retirement at age 38, scored 4 goals at WC 1990, and danced around every corner flag he could find.",
        "Cameroon also appeared at WC 1994, 1998, 2002, 2010, 2014 and 2022 — one of Africa's most consistent qualifiers.",
    ],
    "NZL": [
        "The 'All Whites' — please don't confuse them with the All Blacks. Very different sport, equally passionate fans.",
        "At WC 2010, drew all three of their group matches without losing — the only unbeaten team in the entire group stage.",
        "One of only a handful of nations from Oceania ever to qualify for a World Cup — beating Australia in the OFC playoff.",
    ],
    "CZE": [
        "As Czechoslovakia they reached two World Cup finals (1934, 1962) — losing both, but to legendary Italy and Brazil sides.",
        "Pavel Nedvěd, their Ballon d'Or winner, is one of the greatest midfielders of the modern era.",
        "Beat the Netherlands 3–2 at Euro 2004 in one of the greatest comeback group games ever — coming back from 2–0 down.",
    ],
    "BIH": [
        "Their only previous World Cup was 2014 — Edin Džeko and a young squad announced themselves on the world stage.",
        "Built almost entirely from a generation born during the Bosnian War — football became a symbol of national unity.",
        "Miralem Pjanić and Edin Džeko gave them one of the most talented spines any small nation has ever fielded.",
    ],
    "QAT": [
        "Hosted the 2022 World Cup — the first ever held in the Middle East and the first in November/December.",
        "Won the 2019 AND 2023 AFC Asian Cups back-to-back — establishing themselves as a genuine Asian powerhouse.",
        "Almoez Ali scored a record 9 goals at the 2019 Asian Cup — including an outrageous overhead kick in the final.",
    ],
    "HAI": [
        "Their only previous World Cup was 1974 — where Emmanuel Sanon famously ended Dino Zoff's 1,142-minute clean-sheet run vs Italy.",
        "One of the most passionate footballing nations in the Caribbean despite enormous off-field hardship.",
        "Qualifying for 2026 sparked celebrations across the entire Haitian diaspora — a rare moment of national joy.",
    ],
    "CIV": [
        "The 'Elephants' — won the Africa Cup of Nations on home soil in 2024 after a remarkable run from near-elimination.",
        "Didier Drogba once helped broker a ceasefire in Ivory Coast's civil war by appealing to both sides on TV.",
        "Their golden generation of Drogba, the Touré brothers and Gervinho never got past the WC group stage — a source of national heartbreak.",
    ],
    "CUW": [
        "With ~150,000 people, Curaçao are one of the smallest nations EVER to reach a World Cup — a genuine fairy tale.",
        "A tiny Dutch Caribbean island, they draw on players with Netherlands eredivisie pedigree through heritage.",
        "Former Dutch international Patrick Kluivert has been part of the project to lift this island onto the world stage.",
    ],
    "SWE": [
        "Finished runners-up at the 1958 World Cup on home soil — losing the final to a 17-year-old Pelé and Brazil.",
        "Reached the semi-finals at USA '94, with Tomas Brolin and Kennet Andersson lighting up the tournament.",
        "Zlatan Ibrahimović — their greatest ever player — sadly never shone at a World Cup, but this is a new generation.",
    ],
    "NOR": [
        "Boast Erling Haaland and Martin Ødegaard — arguably the most exciting attacking duo any nation will bring to 2026.",
        "Famously never lost to Brazil — beating them at France '98 and holding them in 1997. A perfect record vs the five-time champions.",
        "Their last World Cup was 1998 — ending a long wait, they arrive as one of the tournament's dark horses.",
    ],
    "CPV": [
        "The 'Blue Sharks' — a tiny Atlantic island nation of ~500,000 reaching their first ever World Cup. Pure history.",
        "One of the smallest countries by population ever to qualify — a staggering achievement for African football.",
        "Beat Cameroon, Angola and others in qualifying — proof that the Cape Verde footballing project has truly arrived.",
    ],
    "IRQ": [
        "Stunned the world by winning the 2007 Asian Cup — months after war ravaged the country. The whole nation wept with joy.",
        "Younis Mahmoud's winning header in that 2007 final is one of Asian football's most iconic moments.",
        "Returning to the World Cup for the first time since 1986 — football remains a unifying force across Iraq.",
    ],
    "JOR": [
        "Reached their first ever Asian Cup final in 2024 — knocking out South Korea along the way in a famous run.",
        "Making their World Cup debut in 2026 — a historic first for the Jordanian game.",
        "Musa Al-Taamari, their flying winger, is the star man Jordanians hope can shock the world.",
    ],
    "UZB": [
        "Making their World Cup debut in 2026 after decades of agonisingly narrow qualification near-misses.",
        "One of Central Asia's footballing giants — they've reached multiple Asian Cup quarter-finals and beyond.",
        "Qualification sparked national celebrations — a landmark moment for Uzbek sport.",
    ],
    "COD": [
        "As Zaire, they were the first Black African nation to reach a World Cup, in 1974.",
        "The 'Leopards' won the Africa Cup of Nations in 1968 and 1974 — a proud continental pedigree.",
        "Home to a vast pool of talent, DR Congo's return to the World Cup stage has been decades in the making.",
    ],
    "GHA": [
        "The 'Black Stars' — agonisingly missed a last-minute penalty vs Uruguay in the 2010 quarter-final, denied a historic semi-final.",
        "Asamoah Gyan, their talisman, remains Africa's all-time leading World Cup goalscorer.",
        "Four-time Africa Cup of Nations winners and one of the continent's most storied footballing nations.",
    ],
}

# Official 2026 FIFA World Cup draw — groups, codes and names from ESPN.
TEAMS = [
    # Group A
    {"name": "Mexico", "code": "MEX", "group_name": "A", "confederation": "CONCACAF"},
    {"name": "Czechia", "code": "CZE", "group_name": "A", "confederation": "UEFA"},
    {"name": "South Korea", "code": "KOR", "group_name": "A", "confederation": "AFC"},
    {"name": "South Africa", "code": "RSA", "group_name": "A", "confederation": "CAF"},
    # Group B
    {"name": "Canada", "code": "CAN", "group_name": "B", "confederation": "CONCACAF"},
    {"name": "Bosnia & Herzegovina", "code": "BIH", "group_name": "B", "confederation": "UEFA"},
    {"name": "Switzerland", "code": "SUI", "group_name": "B", "confederation": "UEFA"},
    {"name": "Qatar", "code": "QAT", "group_name": "B", "confederation": "AFC"},
    # Group C
    {"name": "Brazil", "code": "BRA", "group_name": "C", "confederation": "CONMEBOL"},
    {"name": "Scotland", "code": "SCO", "group_name": "C", "confederation": "UEFA"},
    {"name": "Haiti", "code": "HAI", "group_name": "C", "confederation": "CONCACAF"},
    {"name": "Morocco", "code": "MAR", "group_name": "C", "confederation": "CAF"},
    # Group D
    {"name": "Paraguay", "code": "PAR", "group_name": "D", "confederation": "CONMEBOL"},
    {"name": "Türkiye", "code": "TUR", "group_name": "D", "confederation": "UEFA"},
    {"name": "Australia", "code": "AUS", "group_name": "D", "confederation": "AFC"},
    {"name": "USA", "code": "USA", "group_name": "D", "confederation": "CONCACAF"},
    # Group E
    {"name": "Ecuador", "code": "ECU", "group_name": "E", "confederation": "CONMEBOL"},
    {"name": "Germany", "code": "GER", "group_name": "E", "confederation": "UEFA"},
    {"name": "Ivory Coast", "code": "CIV", "group_name": "E", "confederation": "CAF"},
    {"name": "Curaçao", "code": "CUW", "group_name": "E", "confederation": "CONCACAF"},
    # Group F
    {"name": "Netherlands", "code": "NED", "group_name": "F", "confederation": "UEFA"},
    {"name": "Sweden", "code": "SWE", "group_name": "F", "confederation": "UEFA"},
    {"name": "Japan", "code": "JPN", "group_name": "F", "confederation": "AFC"},
    {"name": "Tunisia", "code": "TUN", "group_name": "F", "confederation": "CAF"},
    # Group G
    {"name": "Belgium", "code": "BEL", "group_name": "G", "confederation": "UEFA"},
    {"name": "Iran", "code": "IRN", "group_name": "G", "confederation": "AFC"},
    {"name": "Egypt", "code": "EGY", "group_name": "G", "confederation": "CAF"},
    {"name": "New Zealand", "code": "NZL", "group_name": "G", "confederation": "OFC"},
    # Group H
    {"name": "Spain", "code": "ESP", "group_name": "H", "confederation": "UEFA"},
    {"name": "Uruguay", "code": "URU", "group_name": "H", "confederation": "CONMEBOL"},
    {"name": "Saudi Arabia", "code": "KSA", "group_name": "H", "confederation": "AFC"},
    {"name": "Cape Verde", "code": "CPV", "group_name": "H", "confederation": "CAF"},
    # Group I
    {"name": "Norway", "code": "NOR", "group_name": "I", "confederation": "UEFA"},
    {"name": "France", "code": "FRA", "group_name": "I", "confederation": "UEFA"},
    {"name": "Senegal", "code": "SEN", "group_name": "I", "confederation": "CAF"},
    {"name": "Iraq", "code": "IRQ", "group_name": "I", "confederation": "AFC"},
    # Group J
    {"name": "Argentina", "code": "ARG", "group_name": "J", "confederation": "CONMEBOL"},
    {"name": "Austria", "code": "AUT", "group_name": "J", "confederation": "UEFA"},
    {"name": "Algeria", "code": "ALG", "group_name": "J", "confederation": "CAF"},
    {"name": "Jordan", "code": "JOR", "group_name": "J", "confederation": "AFC"},
    # Group K
    {"name": "Colombia", "code": "COL", "group_name": "K", "confederation": "CONMEBOL"},
    {"name": "Portugal", "code": "POR", "group_name": "K", "confederation": "UEFA"},
    {"name": "Uzbekistan", "code": "UZB", "group_name": "K", "confederation": "AFC"},
    {"name": "Congo DR", "code": "COD", "group_name": "K", "confederation": "CAF"},
    # Group L
    {"name": "England", "code": "ENG", "group_name": "L", "confederation": "UEFA"},
    {"name": "Croatia", "code": "CRO", "group_name": "L", "confederation": "UEFA"},
    {"name": "Panama", "code": "PAN", "group_name": "L", "confederation": "CONCACAF"},
    {"name": "Ghana", "code": "GHA", "group_name": "L", "confederation": "CAF"},
]

# Quantexa sweepstake participants — processed from the contributions CSV.
# entry_fee_paid = summed total across all of a person's contributions.
# entries = max(1, round(fee / 5)) — see Participant.entries in models.py.
# Duplicate contributors are summed (e.g. Molly Atkinson £15+£5=£20,
# Martin Durchov £0.78+£9.61=£10.39). Admin-added players store fee = entries*5.
PARTICIPANTS = [
    {"name": "Alex Wood",          "entry_fee_paid": 25.00},  # 5 entries
    {"name": "Molly Atkinson",     "entry_fee_paid": 20.00},  # 4 entries
    {"name": "Harry Reid",         "entry_fee_paid": 20.00},  # 4 entries
    {"name": "Tristan Rowick",     "entry_fee_paid": 20.00},  # 4 entries
    {"name": "Wasiq Rehman",       "entry_fee_paid": 20.00},  # 4 entries
    {"name": "Stavros Katsoris",   "entry_fee_paid": 20.00},  # 4 entries
    {"name": "Will Hicks",         "entry_fee_paid": 19.42},  # 4 entries
    {"name": "Mahamed Ali",        "entry_fee_paid": 15.00},  # 3 entries
    {"name": "John Keightley",     "entry_fee_paid": 15.00},  # 3 entries
    {"name": "Gregory Jones",      "entry_fee_paid": 15.00},  # 3 entries
    {"name": "Alex Cowan",         "entry_fee_paid": 15.00},  # 3 entries
    {"name": "Liam Bowmer",        "entry_fee_paid": 15.00},  # 3 entries
    {"name": "Dan Pryer",          "entry_fee_paid": 15.00},  # 3 entries
    {"name": "Martin Durchov",     "entry_fee_paid": 10.39},  # 2 entries (£0.78 + £9.61)
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
    {"name": "Stephen Ward",       "entry_fee_paid": 10.00},  # 2 entries
    {"name": "Ben Musgrave",       "entry_fee_paid": 10.00},  # 2 entries
    {"name": "Will Reade",         "entry_fee_paid": 10.00},  # 2 entries
    {"name": "Renos Ballas",       "entry_fee_paid": 10.00},  # 2 entries
    {"name": "Danny Gold",         "entry_fee_paid": 10.00},  # 2 entries
    {"name": "Sam Nejad",          "entry_fee_paid": 10.00},  # 2 entries
    {"name": "Jak Maloret",        "entry_fee_paid": 10.00},  # 2 entries
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
    {"name": "William Carter",     "entry_fee_paid":  5.00},  # 1 entry
    {"name": "Nic Harrison",       "entry_fee_paid":  5.00},  # 1 entry
    {"name": "Nathan Grand",       "entry_fee_paid":  5.00},  # 1 entry
    {"name": "Daniela Casilli",    "entry_fee_paid":  5.00},  # 1 entry
    {"name": "Joe Watts",          "entry_fee_paid":  5.00},  # 1 entry
    {"name": "Sian Ayres",         "entry_fee_paid":  5.00},  # 1 entry
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
        "name": "Best Defense",
        "emoji": "🧱",
        "description": "The team that concedes the fewest goals across the whole tournament before being eliminated (or wins it all).",
        "calc_key": "best_defense",
        "sort_order": 5,
    },
    {
        "name": "Golden Boot",
        "emoji": "👟",
        "description": "The team that scores the most goals across the whole tournament. Tiebreaker: fewest goals conceded.",
        "calc_key": "golden_boot",
        "sort_order": 4,
    },
    {
        "name": "Penalty Kings",
        "emoji": "🎯",
        "description": "The team that wins the most penalty shootouts across the knockout stages. Sudden death glory.",
        "calc_key": "penalty_kings",
        "sort_order": 6,
    },
    {
        "name": "Plucky Underdog",
        "emoji": "🐣",
        "description": "The best team to be knocked out in the group stage — most group points (tiebreak goal difference) among those who go home early. For the minnow that overachieved.",
        "calc_key": "plucky_underdog",
        "sort_order": 7,
    },
    {
        "name": "Draw Specialists",
        "emoji": "🤝",
        "description": "The team with the most drawn matches across the tournament. Masters of the hard-earned point — never beaten, never quite winning.",
        "calc_key": "draw_specialists",
        "sort_order": 8,
    },
    {
        "name": "The Sieve",
        "emoji": "🧺",
        "description": "The team that concedes the most goals across the whole tournament (tiebreak: fewest scored). The leakiest defence of them all.",
        "calc_key": "sieve",
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
