"""
Fixtures, results, cards and bracket data from ESPN's public soccer API.

ESPN serves the full 2026 World Cup (league `fifa.world`) for free with no key,
including the real teams/groups and live scores — unlike API-Football's free
tier, which blocks the 2026 season.

Three consumers:
  * fetch_fixtures(app)  → normalised fixture list (cached) for the Fixtures
                           page and the Bracket page (shows placeholders too).
  * sync_fixtures(app)   → upserts Match rows + recomputes eliminations so the
                           leaderboard/standings advance. Drop-in replacement
                           for the old sync.sync_fixtures.
"""

import re
import time
import requests
from datetime import datetime

ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world"

# Tournament window, fetched in chunks so ESPN never truncates a long range.
DATE_CHUNKS = [
    "20260611-20260620",
    "20260621-20260630",
    "20260701-20260710",
    "20260711-20260720",
]

# ESPN season.slug → our stage label (must match models.STAGE_POINTS keys
# for the knockout stages, plus the standings stage ordering).
STAGE_SLUG_MAP = {
    "group-stage":     "Group Stage",
    "round-of-32":     "Round of 32",
    "round-of-16":     "Round of 16",
    "quarterfinals":   "Quarter-final",
    "semifinals":      "Semi-final",
    "3rd-place-match": "Third-place Play-off",
    "final":           "Final",
}

KNOCKOUT_ORDER = [
    "Round of 32", "Round of 16", "Quarter-final",
    "Semi-final", "Third-place Play-off", "Final",
]

# Short cache so page views / the 3-hour sync don't hammer ESPN.
_CACHE = {"ts": 0.0, "data": None}
_CACHE_TTL = 600  # seconds


def _parse_minute(detail):
    """Leading minute from a play clock like "45'+2'" or "90'" → int (or None)."""
    disp = (detail.get("clock") or {}).get("displayValue") or ""
    m = re.match(r"\s*(\d+)", disp)
    return int(m.group(1)) if m else None


def _is_placeholder(competitor):
    """True for unresolved knockout slots ("Group A 2nd Place", abbrev "2A")."""
    team = competitor.get("team") or {}
    abbr = team.get("abbreviation") or ""
    name = team.get("displayName") or ""
    if re.search(r"\d", abbr):           # real country codes have no digits
        return True
    return any(w in name for w in ("Place", "Winner", "Group", "Third", "TBD", "/"))


def _slot_label(abbr, name, placeholder):
    """Short chip for an unresolved knockout slot.

    Group slots keep their compact code ("1A", "2B", "3RD"); winner-of feeders
    ("Round of 32 1 Winner") become "W1" so the chip stays tiny.
    """
    if not placeholder:
        return abbr
    if re.fullmatch(r"[123][A-L]|3RD", abbr or ""):
        return abbr
    m = re.search(r"(\d+)\s*Winner", name or "")
    if m:
        return "W" + m.group(1)
    return abbr or "—"


def _normalise_competitor(c):
    team = c.get("team") or {}
    score = c.get("score")
    try:
        score = int(score) if score is not None and score != "" else None
    except (TypeError, ValueError):
        score = None
    shootout = c.get("shootoutScore")
    try:
        shootout = int(shootout) if shootout is not None and shootout != "" else None
    except (TypeError, ValueError):
        shootout = None
    placeholder = _is_placeholder(c)
    abbrev = team.get("abbreviation") or ""
    name = team.get("displayName") or "TBD"
    return {
        "espn_id":     team.get("id"),
        "name":        name,
        "abbrev":      abbrev,
        "slot":        _slot_label(abbrev, name, placeholder),
        "logo":        team.get("logo"),
        "score":       score,
        "shootout":    shootout,
        "home_away":   c.get("homeAway"),
        "placeholder": placeholder,
    }


def _fetch_raw(chunk):
    resp = requests.get(
        f"{ESPN_BASE}/scoreboard",
        params={"dates": chunk},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("events", [])


def fetch_fixtures(force=False):
    """All WC fixtures as normalised dicts, newest cache within _CACHE_TTL.

    Returns [] only if every chunk fails AND nothing is cached.
    """
    now = time.time()
    if not force and _CACHE["data"] is not None and (now - _CACHE["ts"]) < _CACHE_TTL:
        return _CACHE["data"]

    fixtures = {}
    errors = 0
    for chunk in DATE_CHUNKS:
        try:
            for e in _fetch_raw(chunk):
                comp = (e.get("competitions") or [{}])[0]
                competitors = comp.get("competitors") or []
                home = next((c for c in competitors if c.get("homeAway") == "home"), None)
                away = next((c for c in competitors if c.get("homeAway") == "away"), None)
                if not home or not away:
                    continue

                slug = (e.get("season") or {}).get("slug", "")
                status = (comp.get("status") or {}).get("type") or {}

                match_date = None
                if e.get("date"):
                    try:
                        match_date = datetime.fromisoformat(
                            e["date"].replace("Z", "+00:00")
                        )
                    except ValueError:
                        pass

                fixtures[e["id"]] = {
                    "espn_id":       int(e["id"]),
                    "date":          match_date,
                    "stage":         STAGE_SLUG_MAP.get(slug, "Group Stage"),
                    "stage_slug":    slug,
                    "venue":         (comp.get("venue") or {}).get("fullName"),
                    "state":         status.get("state"),        # pre / in / post
                    "completed":     bool(status.get("completed")),
                    "status_detail": status.get("shortDetail") or status.get("detail") or "",
                    "home":          _normalise_competitor(home),
                    "away":          _normalise_competitor(away),
                    "details":       comp.get("details") or [],
                }
        except requests.RequestException:
            errors += 1

    if not fixtures and errors:
        # total failure — keep whatever we had rather than blanking the pages
        return _CACHE["data"] or []

    data = sorted(
        fixtures.values(),
        key=lambda f: (f["date"] or datetime.max, f["espn_id"]),
    )
    _CACHE["data"] = data
    _CACHE["ts"] = now
    return data


def fixtures_by_date(fixtures):
    """Group fixtures into ordered [(date_label, [fixture, ...]), ...]."""
    buckets = {}
    for f in fixtures:
        key = f["date"].date() if f["date"] else None
        buckets.setdefault(key, []).append(f)
    ordered = sorted(buckets.items(), key=lambda kv: (kv[0] or datetime.max.date()))
    out = []
    for day, items in ordered:
        label = day.strftime("%A %d %B") if day else "Date TBC"
        out.append((label, items))
    return out


# ── Connected bracket tree ────────────────────────────────────────────────────
#
# The 2026 knockout structure is fixed. ESPN numbers matches within each round
# by event-id order (id-sort == FIFA match number), and every slot label says
# which feeder match it comes from. We bake the feeder graph below so the bracket
# stays correct even once the placeholder labels are replaced by real teams.
#
# FEED[round][match_number] = [(feeder_round, feeder_number), ...]
BRACKET_ROUNDS = ["Round of 32", "Round of 16", "Quarter-final", "Semi-final", "Final"]
FEED = {
    "Final": {1: [("Semi-final", 1), ("Semi-final", 2)]},
    "Semi-final": {
        1: [("Quarter-final", 1), ("Quarter-final", 2)],
        2: [("Quarter-final", 3), ("Quarter-final", 4)],
    },
    "Quarter-final": {
        1: [("Round of 16", 1), ("Round of 16", 2)],
        2: [("Round of 16", 5), ("Round of 16", 6)],
        3: [("Round of 16", 3), ("Round of 16", 4)],
        4: [("Round of 16", 7), ("Round of 16", 8)],
    },
    "Round of 16": {
        1: [("Round of 32", 1), ("Round of 32", 3)],
        2: [("Round of 32", 2), ("Round of 32", 5)],
        3: [("Round of 32", 4), ("Round of 32", 6)],
        4: [("Round of 32", 7), ("Round of 32", 8)],
        5: [("Round of 32", 11), ("Round of 32", 12)],
        6: [("Round of 32", 9), ("Round of 32", 10)],
        7: [("Round of 32", 13), ("Round of 32", 15)],
        8: [("Round of 32", 14), ("Round of 32", 16)],
    },
}


def bracket_tree(fixtures):
    """Ordered bracket columns + the third-place match.

    Returns (columns, third_place) where columns is
    [(round, [fixture | None, ...]), ...] laid out left→right so that the match
    at index k in a round is fed by indices 2k and 2k+1 of the previous round
    (lets the connector lines join feeders to their next-round match).
    """
    # Number each round's matches by event-id order.
    by_round = {}
    for f in fixtures:
        if f["stage"] in BRACKET_ROUNDS:
            by_round.setdefault(f["stage"], []).append(f)
    numbered = {}
    for rnd, items in by_round.items():
        for i, f in enumerate(sorted(items, key=lambda x: x["espn_id"]), start=1):
            numbered[(rnd, i)] = f

    order = {r: [] for r in BRACKET_ROUNDS}

    def visit(rnd, num):
        for fr, fn in FEED.get(rnd, {}).get(num, []):
            visit(fr, fn)
        order[rnd].append(num)

    visit("Final", 1)

    # Fall back to plain date order for any round we couldn't place (e.g. ESPN
    # hasn't published a round yet).
    columns = []
    for rnd in BRACKET_ROUNDS:
        seq = order[rnd]
        if not seq:
            continue
        col = [numbered.get((rnd, n)) for n in seq]
        if any(col):
            columns.append((rnd, col))

    third = [f for f in fixtures if f["stage"] == "Third-place Play-off"]
    return columns, third


# ── DB sync ───────────────────────────────────────────────────────────────────

def _extract_events(fixture, home_team, away_team):
    """Cards, half-time score and first goal from ESPN play details."""
    home_y = home_r = away_y = away_r = 0
    home_ht = away_ht = 0
    first_goal_team_id = None
    first_goal_min = 10 ** 9

    home_eid = str(fixture["home"]["espn_id"])
    away_eid = str(fixture["away"]["espn_id"])

    for d in fixture["details"]:
        tid = str((d.get("team") or {}).get("id") or "")
        is_home = tid == home_eid
        is_away = tid == away_eid
        if not (is_home or is_away):
            continue
        text = (d.get("type") or {}).get("text", "") or ""

        if "Card" in text:
            if "Red" in text:
                if is_home: home_r += 1
                else:       away_r += 1
            elif "Yellow" in text:
                if is_home: home_y += 1
                else:       away_y += 1
            continue

        if d.get("scoringPlay"):
            minute = _parse_minute(d)
            # Own goals credit the opposing side.
            scorer = away_team if ("Own Goal" in text and is_home) else \
                     home_team if ("Own Goal" in text and is_away) else \
                     (home_team if is_home else away_team)
            if minute is not None:
                if minute <= 45:
                    if scorer.id == home_team.id: home_ht += 1
                    else:                          away_ht += 1
                if minute < first_goal_min:
                    first_goal_min = minute
                    first_goal_team_id = scorer.id

    return {
        "home_yellows": home_y, "away_yellows": away_y,
        "home_reds": home_r, "away_reds": away_r,
        "home_ht": home_ht, "away_ht": away_ht,
        "first_goal_team_id": first_goal_team_id,
        "has_cards": (home_y or away_y or home_r or away_r) > 0,
    }


def _winner_loser(m):
    """(winner_team, loser_team) for a completed knockout match, else None."""
    if m.home_penalties is not None and m.away_penalties is not None \
            and m.home_penalties != m.away_penalties:
        home_wins = m.home_penalties > m.away_penalties
    elif m.home_score is not None and m.home_score != m.away_score:
        home_wins = m.home_score > m.away_score
    else:
        return None
    return (m.home_team, m.away_team) if home_wins else (m.away_team, m.home_team)


def _recompute_eliminations(db, Team, Match):
    """Derive elimination state from completed matches (knockouts + groups)."""
    for t in Team.query.all():
        t.eliminated = False
        t.eliminated_stage = None

    for m in Match.query.filter(Match.stage.in_(KNOCKOUT_ORDER)).all():
        if not m.played:
            continue
        wl = _winner_loser(m)
        if not wl:
            continue
        winner, loser = wl
        if m.stage == "Final":
            loser.eliminated = True
            loser.eliminated_stage = "Runner-up"
            winner.eliminated = False
            winner.eliminated_stage = "Champion"
        elif m.stage == "Third-place Play-off":
            continue  # both already eliminated at the Semi-final
        else:
            loser.eliminated = True
            loser.eliminated_stage = m.stage

    # Group non-qualifiers — only once the full Round of 32 is known.
    r32 = Match.query.filter_by(stage="Round of 32").all()
    r32_ids = set()
    for m in r32:
        r32_ids.add(m.home_team_id)
        r32_ids.add(m.away_team_id)
    if len(r32) == 16 and len(r32_ids) == 32:
        for t in Team.query.all():
            played = any(mt.played for mt in t.all_matches if mt.stage == "Group Stage")
            if t.id not in r32_ids and played and not t.eliminated_stage:
                t.eliminated = True
                t.eliminated_stage = "Group Stage"


def sync_fixtures(app):
    """Upsert Match rows from ESPN and recompute eliminations."""
    from models import db, Team, Match

    fixtures = fetch_fixtures(force=True)
    if not fixtures:
        return {"error": "Could not reach ESPN", "created": 0, "updated": 0, "skipped": 0}

    with app.app_context():
        teams_by_code = {t.code: t for t in Team.query.all()}
        created = updated = skipped = 0

        for f in fixtures:
            home_team = teams_by_code.get(f["home"]["abbrev"])
            away_team = teams_by_code.get(f["away"]["abbrev"])
            if not home_team or not away_team:
                skipped += 1   # unresolved knockout slot, or unknown team
                continue

            fix_id = f["espn_id"]
            scored = f["state"] in ("in", "post") and \
                f["home"]["score"] is not None and f["away"]["score"] is not None
            home_score = f["home"]["score"] if scored else None
            away_score = f["away"]["score"] if scored else None
            home_pens = f["home"]["shootout"]
            away_pens = f["away"]["shootout"]

            ev = _extract_events(f, home_team, away_team) if scored else None

            existing = Match.query.filter_by(api_fixture_id=fix_id).first()
            if not existing:
                existing = Match.query.filter_by(
                    home_team_id=home_team.id,
                    away_team_id=away_team.id,
                    stage=f["stage"],
                ).first()

            if existing:
                changed = False
                if existing.api_fixture_id != fix_id:
                    existing.api_fixture_id = fix_id; changed = True
                if existing.stage != f["stage"]:
                    existing.stage = f["stage"]; changed = True
                if f["date"] and existing.match_date != f["date"].replace(tzinfo=None):
                    existing.match_date = f["date"].replace(tzinfo=None); changed = True
                if f["venue"] and existing.venue != f["venue"]:
                    existing.venue = f["venue"]; changed = True
                if scored and (existing.home_score != home_score
                               or existing.away_score != away_score):
                    existing.home_score = home_score
                    existing.away_score = away_score
                    changed = True
                if home_pens is not None and (existing.home_penalties != home_pens
                                              or existing.away_penalties != away_pens):
                    existing.home_penalties = home_pens
                    existing.away_penalties = away_pens
                    existing.penalty_winner_id = (
                        home_team.id if (home_pens or 0) > (away_pens or 0) else away_team.id
                    )
                    changed = True
                if ev:
                    existing.home_ht_score = ev["home_ht"]
                    existing.away_ht_score = ev["away_ht"]
                    existing.home_yellows = ev["home_yellows"]
                    existing.away_yellows = ev["away_yellows"]
                    existing.home_reds = ev["home_reds"]
                    existing.away_reds = ev["away_reds"]
                    if ev["first_goal_team_id"]:
                        existing.first_goal_team_id = ev["first_goal_team_id"]
                    existing.cards_synced = True
                    changed = True
                if changed:
                    updated += 1
            else:
                m = Match(
                    home_team_id=home_team.id,
                    away_team_id=away_team.id,
                    stage=f["stage"],
                    match_date=f["date"].replace(tzinfo=None) if f["date"] else None,
                    venue=f["venue"],
                    home_score=home_score,
                    away_score=away_score,
                    home_penalties=home_pens,
                    away_penalties=away_pens,
                    api_fixture_id=fix_id,
                )
                if home_pens is not None and away_pens is not None:
                    m.penalty_winner_id = (
                        home_team.id if home_pens > away_pens else away_team.id
                    )
                if ev:
                    m.home_ht_score = ev["home_ht"]
                    m.away_ht_score = ev["away_ht"]
                    m.home_yellows = ev["home_yellows"]
                    m.away_yellows = ev["away_yellows"]
                    m.home_reds = ev["home_reds"]
                    m.away_reds = ev["away_reds"]
                    m.first_goal_team_id = ev["first_goal_team_id"]
                    m.cards_synced = True
                db.session.add(m)
                created += 1

        db.session.commit()
        _recompute_eliminations(db, Team, Match)
        db.session.commit()

        return {
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "synced_at": datetime.utcnow().isoformat(),
        }
