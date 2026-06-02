"""
Sync fixtures and results from football-data.org (free tier).
Register for a free API key at: https://www.football-data.org/client/register
Set the FOOTBALL_DATA_API_KEY environment variable on Heroku.

Competition code for FIFA World Cup 2026 is 'WC'.
"""

import os
import requests
from datetime import datetime, timezone

FOOTBALL_API = "https://api.football-data.org/v4"

STAGE_MAP = {
    "GROUP_STAGE":     "Group Stage",
    "ROUND_OF_32":     "Round of 32",
    "ROUND_OF_16":     "Round of 16",
    "QUARTER_FINALS":  "Quarter-final",
    "SEMI_FINALS":     "Semi-final",
    "THIRD_PLACE":     "Runner-up",
    "FINAL":           "Final",
}

# API team names that differ from our seed data names
TEAM_NAME_MAP = {
    "United States":                    "USA",
    "Korea Republic":                   "South Korea",
    "Republic of Korea":                "South Korea",
    "IR Iran":                          "Iran",
    "Côte d'Ivoire":                    "Ivory Coast",
    "Bosnia and Herzegovina":           "Bosnia",
    "Democratic Republic of Congo":     "DR Congo",
    "Hong Kong":                        "Hong Kong",
    "North Macedonia":                  "North Macedonia",
    "Cabo Verde":                       "Cape Verde",
    "Venezuela (Bolivarian Republic of)": "Venezuela",
}


def _normalise(name):
    return TEAM_NAME_MAP.get(name, name).strip().lower()


def sync_fixtures(app):
    """Fetch all WC 2026 matches from football-data.org and upsert into DB."""
    api_key = os.environ.get("FOOTBALL_DATA_API_KEY")
    if not api_key:
        return {"error": "FOOTBALL_DATA_API_KEY not configured", "created": 0, "updated": 0}

    headers = {"X-Auth-Token": api_key}
    try:
        resp = requests.get(
            f"{FOOTBALL_API}/competitions/WC/matches",
            headers=headers,
            timeout=15,
        )
        # Honour rate-limit headers to avoid being throttled (as per API docs)
        remaining = int(resp.headers.get("X-Requests-Available-Minute", 10))
        if remaining < 2:
            import time
            reset_in = int(resp.headers.get("X-RequestCounter-Reset", 60))
            print(f"Rate limit nearly reached, waiting {reset_in}s")
            time.sleep(reset_in)

        resp.raise_for_status()
    except requests.RequestException as exc:
        return {"error": str(exc), "created": 0, "updated": 0}

    api_matches = resp.json().get("matches", [])

    from models import db, Team, Match

    with app.app_context():
        # Build name lookup once
        teams_by_name = {t.name.lower(): t for t in Team.query.all()}

        created = updated = skipped = 0

        for am in api_matches:
            stage = STAGE_MAP.get(am.get("stage", ""), "Group Stage")

            home_name = am["homeTeam"].get("name")
            away_name = am["awayTeam"].get("name")
            if not home_name or not away_name:
                skipped += 1
                continue

            home_key = _normalise(home_name)
            away_key = _normalise(away_name)
            home_team = teams_by_name.get(home_key)
            away_team = teams_by_name.get(away_key)

            if not home_team or not away_team:
                skipped += 1
                continue

            match_date = None
            if am.get("utcDate"):
                try:
                    match_date = datetime.fromisoformat(
                        am["utcDate"].replace("Z", "+00:00")
                    ).replace(tzinfo=None)
                except ValueError:
                    pass

            full_time = am.get("score", {}).get("fullTime", {})
            home_score = full_time.get("home")
            away_score = full_time.get("away")

            existing = Match.query.filter_by(
                home_team_id=home_team.id,
                away_team_id=away_team.id,
                stage=stage,
            ).first()

            if existing:
                changed = False
                if home_score is not None and existing.home_score != home_score:
                    existing.home_score = home_score
                    existing.away_score = away_score
                    changed = True
                if match_date and existing.match_date != match_date:
                    existing.match_date = match_date
                    changed = True
                if am.get("venue") and existing.venue != am["venue"]:
                    existing.venue = am["venue"]
                    changed = True
                if changed:
                    updated += 1
            else:
                db.session.add(Match(
                    home_team_id=home_team.id,
                    away_team_id=away_team.id,
                    stage=stage,
                    match_date=match_date,
                    venue=am.get("venue"),
                    home_score=home_score,
                    away_score=away_score,
                ))
                created += 1

        db.session.commit()
        return {
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "total_api": len(api_matches),
            "synced_at": datetime.utcnow().isoformat(),
        }
