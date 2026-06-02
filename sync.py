"""
Sync fixtures, results and card data from API-Football (api-sports.io).
Free tier: 100 requests/day — plenty for 3-hour polling.
WC 2026: league_id=1, season=2026
Register at: https://dashboard.api-football.com
Set env var: API_FOOTBALL_KEY
"""

import os
import time
import requests
from datetime import datetime

API_BASE = "https://v3.football.api-sports.io"
LEAGUE_ID = 1
SEASON = 2026

STAGE_MAP = {
    "Group Stage":    "Group Stage",
    "Round of 32":    "Round of 32",
    "Round of 16":    "Round of 16",
    "Quarter-finals": "Quarter-final",
    "Semi-finals":    "Semi-final",
    "3rd Place Final":"Runner-up",
    "Final":          "Final",
}

TEAM_NAME_MAP = {
    "United States":                      "USA",
    "Korea Republic":                     "South Korea",
    "Republic of Korea":                  "South Korea",
    "IR Iran":                            "Iran",
    "Iran (Islamic Republic of)":         "Iran",
    "Côte d'Ivoire":                      "Ivory Coast",
    "Venezuela (Bolivarian Republic of)": "Venezuela",
    "Bosnia and Herzegovina":             "Bosnia",
    "Cape Verde":                         "Cape Verde",
    "Cabo Verde":                         "Cape Verde",
}


def _normalise(name):
    if not name:
        return None
    return TEAM_NAME_MAP.get(name, name).strip().lower()


def _get_stage(round_str):
    if not round_str:
        return "Group Stage"
    for key, val in STAGE_MAP.items():
        if key.lower() in round_str.lower():
            return val
    if "group" in round_str.lower():
        return "Group Stage"
    return round_str


def _check_rate(resp):
    remaining = resp.headers.get("x-ratelimit-requests-remaining")
    if remaining and int(remaining) < 5:
        reset = int(resp.headers.get("x-ratelimit-reset", 60))
        print(f"API-Football rate limit low ({remaining} left) — sleeping {reset}s")
        time.sleep(reset)


def sync_fixtures(app):
    api_key = os.environ.get("API_FOOTBALL_KEY")
    if not api_key:
        return {"error": "API_FOOTBALL_KEY not configured", "created": 0, "updated": 0}

    headers = {"x-apisports-key": api_key}

    # ── 1. Fetch all WC 2026 fixtures (1 API call) ────────────────────────────
    try:
        resp = requests.get(
            f"{API_BASE}/fixtures",
            params={"league": LEAGUE_ID, "season": SEASON},
            headers=headers,
            timeout=15,
        )
        _check_rate(resp)
        resp.raise_for_status()
    except requests.RequestException as exc:
        return {"error": str(exc), "created": 0, "updated": 0}

    data = resp.json()
    if data.get("errors") and data["errors"] != []:
        return {"error": str(data["errors"]), "created": 0, "updated": 0}

    api_fixtures = data.get("response", [])

    from models import db, Team, Match

    with app.app_context():
        teams_by_name = {t.name.lower(): t for t in Team.query.all()}
        created = updated = skipped = 0
        needs_cards = []  # api_fixture_ids that need card stats fetched

        for f in api_fixtures:
            home_name = f["teams"]["home"].get("name")
            away_name = f["teams"]["away"].get("name")
            if not home_name or not away_name:
                skipped += 1
                continue

            home_team = teams_by_name.get(_normalise(home_name))
            away_team = teams_by_name.get(_normalise(away_name))
            if not home_team or not away_team:
                skipped += 1
                continue

            fix_id    = f["fixture"]["id"]
            stage     = _get_stage(f["league"].get("round", ""))
            status    = f["fixture"]["status"]["short"]
            is_done   = status in ("FT", "AET", "PEN", "AWD", "WO")

            match_date = None
            raw_date = f["fixture"].get("date")
            if raw_date:
                try:
                    match_date = datetime.fromisoformat(
                        raw_date.replace("Z", "+00:00")
                    ).replace(tzinfo=None)
                except ValueError:
                    pass

            goals     = f.get("goals", {})
            home_score = goals.get("home")
            away_score = goals.get("away")

            pen = f.get("score", {}).get("penalty", {})
            home_pens = pen.get("home")
            away_pens = pen.get("away")

            venue = (f["fixture"].get("venue") or {}).get("name")

            # Find existing match by fixture ID first, then by teams+stage
            existing = Match.query.filter_by(api_fixture_id=fix_id).first()
            if not existing:
                existing = Match.query.filter_by(
                    home_team_id=home_team.id,
                    away_team_id=away_team.id,
                    stage=stage,
                ).first()

            if existing:
                changed = False
                if existing.api_fixture_id != fix_id:
                    existing.api_fixture_id = fix_id
                    changed = True
                if home_score is not None and existing.home_score != home_score:
                    existing.home_score = home_score
                    existing.away_score = away_score
                    changed = True
                if home_pens is not None and existing.home_penalties != home_pens:
                    existing.home_penalties = home_pens
                    existing.away_penalties = away_pens
                    existing.penalty_winner_id = (
                        home_team.id if (home_pens or 0) > (away_pens or 0) else away_team.id
                    )
                    changed = True
                if match_date and existing.match_date != match_date:
                    existing.match_date = match_date
                    changed = True
                if venue and existing.venue != venue:
                    existing.venue = venue
                    changed = True
                if changed:
                    updated += 1
                if is_done and not existing.cards_synced:
                    needs_cards.append(fix_id)
            else:
                m = Match(
                    home_team_id=home_team.id,
                    away_team_id=away_team.id,
                    stage=stage,
                    match_date=match_date,
                    venue=venue,
                    home_score=home_score,
                    away_score=away_score,
                    home_penalties=home_pens if home_pens is not None else None,
                    away_penalties=away_pens if away_pens is not None else None,
                    api_fixture_id=fix_id,
                )
                if home_pens is not None and away_pens is not None:
                    m.penalty_winner_id = (
                        home_team.id if home_pens > away_pens else away_team.id
                    )
                db.session.add(m)
                created += 1
                if is_done:
                    needs_cards.append(fix_id)

        db.session.commit()

        # ── 2. Fetch card stats for newly completed matches ───────────────────
        # Cap at 15 per sync to stay comfortably within 100 req/day
        card_updates = 0
        for fix_id in needs_cards[:15]:
            try:
                sr = requests.get(
                    f"{API_BASE}/fixtures/statistics",
                    params={"fixture": fix_id},
                    headers=headers,
                    timeout=10,
                )
                _check_rate(sr)
                sr.raise_for_status()

                match = Match.query.filter_by(api_fixture_id=fix_id).first()
                if not match:
                    continue

                for team_stats in sr.json().get("response", []):
                    tname = team_stats["team"].get("name", "")
                    team = teams_by_name.get(_normalise(tname))
                    if not team:
                        continue
                    yellows = reds = 0
                    for stat in team_stats.get("statistics", []):
                        t = stat.get("type", "")
                        v = int(stat.get("value") or 0)
                        if t == "Yellow Cards":
                            yellows = v
                        elif t == "Red Cards":
                            reds = v
                    if team.id == match.home_team_id:
                        match.home_yellows = yellows
                        match.home_reds = reds
                    elif team.id == match.away_team_id:
                        match.away_yellows = yellows
                        match.away_reds = reds

                match.cards_synced = True
                card_updates += 1
                time.sleep(0.3)

            except Exception as exc:
                print(f"Card stats error for fixture {fix_id}: {exc}")

        db.session.commit()

        return {
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "card_updates": card_updates,
            "total_api": len(api_fixtures),
            "synced_at": datetime.utcnow().isoformat(),
        }
