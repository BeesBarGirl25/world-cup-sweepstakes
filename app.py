import os
import random
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from models import db, Team, Participant, Assignment, Match, Prize, FunCategory, FunWinner, AppSettings
from seed_data import TEAMS, PARTICIPANTS, FUN_CATEGORIES, FLAG_EMOJIS, TEAM_FACTS

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-in-prod")

database_url = os.environ.get("DATABASE_URL", "sqlite:///sweepstakes.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)


@app.context_processor
def inject_globals():
    return {
        "is_admin": is_admin(),
        "FLAG_EMOJIS": FLAG_EMOJIS,
    }


# ── Fun category auto-calculators ─────────────────────────────────────────────

def _calc_wooden_spoon():
    teams = Team.query.all()
    records = []
    for team in teams:
        played = any(m.played for m in team.all_matches if m.stage == "Group Stage")
        if not played:
            continue
        records.append((team.group_points, team.group_goals_for - team.group_goals_against, team))
    if not records:
        return []
    records.sort(key=lambda x: (x[0], x[1]))
    worst_pts, worst_gd, _ = records[0]
    return [t for (p, g, t) in records if p == worst_pts and g == worst_gd]


def _calc_biggest_loser():
    worst = None
    for m in Match.query.filter(Match.home_score.isnot(None)).all():
        h, a = m.home_score, m.away_score
        if h == a:
            continue
        if h > a:
            diff, loser, conceded = h - a, m.away_team, a
        else:
            diff, loser, conceded = a - h, m.home_team, h
        if worst is None or diff > worst[1] or (diff == worst[1] and conceded > worst[2]):
            worst = (loser, diff, conceded)
    return [worst[0]] if worst else []


def _calc_dirtiest():
    teams = Team.query.all()
    if not teams:
        return []
    card_data = [(t.total_card_points, t.total_reds, t) for t in teams
                 if t.total_card_points > 0]
    if not card_data:
        return []
    card_data.sort(key=lambda x: (-x[0], -x[1]))
    top_pts, top_reds, _ = card_data[0]
    return [t for (pts, reds, t) in card_data if pts == top_pts and reds == top_reds]


def _calc_best_defense():
    teams = Team.query.all()
    played = [(t.total_goals_conceded, t) for t in teams
              if any(m.played for m in t.all_matches)]
    if not played:
        return []
    played.sort(key=lambda x: x[0])
    min_conceded = played[0][0]
    return [t for (c, t) in played if c == min_conceded]


def _calc_golden_boot():
    """Team that has scored the most goals across the tournament.
    Tiebreak: fewest conceded."""
    teams = [t for t in Team.query.all() if t.total_goals_for > 0]
    if not teams:
        return []
    teams.sort(key=lambda t: (-t.total_goals_for, t.total_goals_conceded))
    top_gf = teams[0].total_goals_for
    top_ga = teams[0].total_goals_conceded
    return [t for t in teams
            if t.total_goals_for == top_gf and t.total_goals_conceded == top_ga]


def _calc_penalty_kings():
    teams = [(t.penalty_wins, t) for t in Team.query.all() if t.penalty_wins > 0]
    if not teams:
        return []
    teams.sort(key=lambda x: -x[0])
    max_wins = teams[0][0]
    return [t for (w, t) in teams if w == max_wins]


def _calc_first_blood():
    """Team that scores the very first goal of the entire tournament."""
    first = (
        Match.query
        .filter(Match.first_goal_team_id.isnot(None))
        .order_by(Match.match_date)
        .first()
    )
    if not first:
        return []
    team = Team.query.get(first.first_goal_team_id)
    return [team] if team else []


def _calc_comeback_kings():
    """Most wins from a losing HT position across the tournament."""
    counts = {}
    for m in Match.query.filter(
        Match.home_ht_score.isnot(None),
        Match.home_score.isnot(None),
    ).all():
        # Home team comeback
        if m.home_ht_score < m.away_ht_score and m.home_score > m.away_score:
            counts[m.home_team_id] = counts.get(m.home_team_id, 0) + 1
        # Away team comeback
        if m.away_ht_score < m.home_ht_score and m.away_score > m.home_score:
            counts[m.away_team_id] = counts.get(m.away_team_id, 0) + 1
    if not counts:
        return []
    best = max(counts.values())
    return Team.query.filter(Team.id.in_(
        [tid for tid, c in counts.items() if c == best]
    )).all()


def _calc_fairest():
    """Team with the fewest card points (opposite of Dirtiest). Tiebreak: fewer yellows."""
    teams = [t for t in Team.query.all() if any(m.cards_synced for m in t.all_matches)]
    if not teams:
        return []
    ranked = sorted(teams, key=lambda t: (t.total_card_points, t.total_reds))
    if not ranked:
        return []
    best_pts = ranked[0].total_card_points
    best_reds = ranked[0].total_reds
    return [t for t in ranked if t.total_card_points == best_pts and t.total_reds == best_reds]


FUN_CALCS = {
    "wooden_spoon":  _calc_wooden_spoon,
    "biggest_loser": _calc_biggest_loser,
    "dirtiest":      _calc_dirtiest,
    "best_defense":  _calc_best_defense,
    "golden_boot":   _calc_golden_boot,
    "penalty_kings": _calc_penalty_kings,
    "first_blood":   _calc_first_blood,
    "comeback_kings":_calc_comeback_kings,
    "fairest":       _calc_fairest,
}


def get_fun_leaders(category):
    """Return (teams, is_auto) — teams currently leading this fun category."""
    if category.calc_key and category.calc_key in FUN_CALCS:
        return FUN_CALCS[category.calc_key](), True
    return [w.team for w in category.winners if w.team], False


def get_fun_prizes_by_participant():
    """Returns dict of participant_id → total fun prizes earned."""
    prizes = {}
    for cat in FunCategory.query.order_by(FunCategory.sort_order).all():
        teams, _ = get_fun_leaders(cat)
        for team in teams:
            for a in team.assignments:
                prizes[a.participant_id] = prizes.get(a.participant_id, 0) + cat.prize
    return prizes


def get_sweepstakes_summary():
    total_pot = sum(p.entry_fee_paid for p in Participant.query.all())
    fun_prizes = sum(get_fun_prizes_by_participant().values())
    main_prizes = sum(p.amount for p in Prize.query.all())
    return {
        "pot": total_pot,
        "fun_prizes": fun_prizes,
        "main_prizes": main_prizes,
        "remaining": max(0, total_pot - fun_prizes),
    }


def get_group_tables():
    """Returns {group_name: [row_dict sorted by standings rules]}."""
    teams = Team.query.order_by(Team.group_name).all()
    groups = {}
    for team in teams:
        g = team.group_name or "?"
        w = d = l = gf = ga = 0
        for m in team.all_matches:
            if m.stage != "Group Stage" or not m.played:
                continue
            is_home = m.home_team_id == team.id
            tf = m.home_score if is_home else m.away_score
            ta = m.away_score if is_home else m.home_score
            gf += tf; ga += ta
            if tf > ta: w += 1
            elif tf == ta: d += 1
            else: l += 1
        row = dict(team=team, P=w+d+l, W=w, D=d, L=l, GF=gf, GA=ga, GD=gf-ga,
                   Pts=w*3+d)
        groups.setdefault(g, []).append(row)

    for g in groups:
        groups[g].sort(key=lambda r: (-r["Pts"], -r["GD"], -r["GF"]))
    return groups


# ── Dashboard / landing ───────────────────────────────────────────────────────

@app.route("/")
def index():
    participants_list = Participant.query.all()
    standings = sorted(participants_list, key=lambda p: p.total_points, reverse=True)
    fun_prizes_map = get_fun_prizes_by_participant()
    summary = get_sweepstakes_summary()
    categories = FunCategory.query.order_by(FunCategory.sort_order).all()
    cat_leaders = [(cat, get_fun_leaders(cat)) for cat in categories]
    recent_matches = (
        Match.query.filter(Match.home_score.isnot(None))
        .order_by(Match.id.desc()).limit(5).all()
    )
    draw_done = Assignment.query.count() > 0
    return render_template(
        "index.html",
        standings=standings,
        fun_prizes_map=fun_prizes_map,
        summary=summary,
        cat_leaders=cat_leaders,
        recent_matches=recent_matches,
        draw_done=draw_done,
    )


# ── Player profile ────────────────────────────────────────────────────────────

@app.route("/player/<int:pid>")
def player_profile(pid):
    participant = Participant.query.get_or_404(pid)
    all_participants = Participant.query.all()
    standings = sorted(all_participants, key=lambda p: p.total_points, reverse=True)
    rank = next((i+1 for i, p in enumerate(standings) if p.id == pid), None)

    fun_prizes_map = get_fun_prizes_by_participant()
    fun_prize = fun_prizes_map.get(pid, 0)

    total_alive = Team.query.filter_by(eliminated=False).count()
    player_alive = len(participant.alive_teams)
    likelihood = round(player_alive / max(total_alive, 1) * 100, 1) if total_alive > 0 else 0

    summary = get_sweepstakes_summary()
    categories = FunCategory.query.order_by(FunCategory.sort_order).all()
    cat_leaders = [(cat, get_fun_leaders(cat)) for cat in categories]

    # Which fun categories might this participant win?
    my_team_ids = {t.id for t in participant.teams}
    fun_potential = []
    for cat, (leaders, is_auto) in cat_leaders:
        for t in leaders:
            if t.id in my_team_ids:
                fun_potential.append((cat, t))
                break

    group_tables = get_group_tables()

    return render_template(
        "player.html",
        participant=participant,
        rank=rank,
        total=len(standings),
        fun_prize=fun_prize,
        likelihood=likelihood,
        summary=summary,
        fun_potential=fun_potential,
        group_tables=group_tables,
        cat_leaders=cat_leaders,
    )


# ── Participants (read-only) ──────────────────────────────────────────────────

@app.route("/participants")
def participants():
    people = Participant.query.order_by(Participant.name).all()
    summary = get_sweepstakes_summary()
    return render_template("participants.html", participants=people, summary=summary)


# ── Tournament standings ──────────────────────────────────────────────────────

@app.route("/tournament")
def tournament():
    from espn import fetch_fixtures, fixtures_by_date, bracket_tree
    group_tables = get_group_tables()

    all_fixtures = fetch_fixtures()
    fx_days = fixtures_by_date(all_fixtures)
    bracket_cols, third_place = bracket_tree(all_fixtures)
    seen, fx_stages = set(), []
    for f in all_fixtures:
        if f["stage"] not in seen:
            seen.add(f["stage"]); fx_stages.append(f["stage"])

    results_matches = (
        Match.query.filter(Match.home_score.isnot(None))
        .order_by(Match.match_date, Match.id).all()
    )
    played_stages = {m.stage for m in results_matches}
    stage_order = ["Group Stage", "Round of 32", "Round of 16", "Quarter-final",
                   "Semi-final", "Third-place Play-off", "Final"]
    res_stages = [s for s in stage_order if s in played_stages]

    active = request.args.get("tab", "standings")
    if active not in ("standings", "bracket", "fixtures", "results"):
        active = "standings"
    return render_template(
        "tournament.html",
        group_tables=group_tables,
        fx_days=fx_days,
        fx_stages=fx_stages,
        bracket_cols=bracket_cols,
        third_place=third_place,
        results_matches=results_matches,
        res_stages=res_stages,
        active_tab=active,
        is_admin=is_admin(),
    )


@app.route("/standings")
def standings():
    return redirect(url_for("tournament", tab="standings"))


# ── Fun categories ────────────────────────────────────────────────────────────

@app.route("/fun")
def fun():
    categories = FunCategory.query.order_by(FunCategory.sort_order).all()
    cat_data = []
    for cat in categories:
        leaders, is_auto = get_fun_leaders(cat)
        cat_data.append({"cat": cat, "leaders": leaders, "is_auto": is_auto})
    fun_prizes_map = get_fun_prizes_by_participant()
    summary = get_sweepstakes_summary()
    teams = Team.query.order_by(Team.name).all()
    participants_list = Participant.query.order_by(Participant.name).all()
    return render_template(
        "fun.html",
        cat_data=cat_data,
        fun_prizes_map=fun_prizes_map,
        summary=summary,
        teams=teams,
        participants=participants_list,
    )


@app.route("/fun/<int:cid>/winner", methods=["POST"])
def set_fun_winner(cid):
    if not is_admin():
        flash("Admin only.", "danger")
        return redirect(url_for("fun"))
    cat = FunCategory.query.get_or_404(cid)
    team_id = request.form.get("team_id")
    notes = request.form.get("notes", "").strip()
    if not team_id:
        flash("Select a team.", "danger")
        return redirect(url_for("fun"))
    FunWinner.query.filter_by(category_id=cid).delete()
    db.session.add(FunWinner(
        category_id=cid,
        team_id=int(team_id),
        notes=notes or None,
        finalized=True,
    ))
    db.session.commit()
    flash(f"Winner set for '{cat.name}'.", "success")
    return redirect(url_for("fun"))


@app.route("/fun/<int:cid>/clear", methods=["POST"])
def clear_fun_winner(cid):
    if not is_admin():
        flash("Admin only.", "danger")
        return redirect(url_for("fun"))
    FunWinner.query.filter_by(category_id=cid).delete()
    db.session.commit()
    flash("Winner cleared.", "info")
    return redirect(url_for("fun"))


# ── Draw ─────────────────────────────────────────────────────────────────────

@app.route("/draw")
def draw():
    if not is_admin():
        flash("The draw is admin-only.", "warning")
        return redirect(url_for("admin_login", next=url_for("draw")))
    participants_list = Participant.query.order_by(Participant.name).all()
    draw_done = Assignment.query.count() > 0
    draw_pub = is_draw_public()
    admin = is_admin()

    assignments = Assignment.query.all() if (draw_pub or admin) else []
    assignments_data = []
    if draw_done and (draw_pub or admin):
        facts = TEAM_FACTS
        for a in assignments:
            team_facts = facts.get(a.team.code, ["A World Cup team!"])
            assignments_data.append({
                "team": a.team.name,
                "code": a.team.code,
                "flag": a.team.flag_emoji or FLAG_EMOJIS.get(a.team.code, "🏳️"),
                "group": a.team.group_name or "?",
                "confederation": a.team.confederation or "",
                "fact": random.choice(team_facts),
                "participant": a.participant.name,
            })
        random.shuffle(assignments_data)

    return render_template(
        "draw.html",
        participants=participants_list,
        assignments=assignments,
        assignments_data=assignments_data,
        draw_done=draw_done,
        draw_public=draw_pub,
        is_admin=admin,
    )


@app.route("/draw/run", methods=["POST"])
def run_draw():
    if not is_admin():
        flash("Admin only.", "danger")
        return redirect(url_for("draw"))
    if Assignment.query.count() > 0:
        flash("Draw has already been run. Reset it first.", "warning")
        return redirect(url_for("draw"))

    participants_list = Participant.query.all()
    teams = Team.query.all()

    pool = []
    for p in participants_list:
        pool.extend([p] * p.entries)
    random.shuffle(pool)
    random.shuffle(teams)

    assigned_pairs = set()
    for i, participant in enumerate(pool):
        team = teams[i % len(teams)]
        pair = (participant.id, team.id)
        if pair not in assigned_pairs:
            assigned_pairs.add(pair)
            db.session.add(Assignment(participant_id=participant.id, team_id=team.id))

    db.session.commit()
    flash("Draw complete!", "success")
    return redirect(url_for("draw"))


@app.route("/draw/reset", methods=["POST"])
def reset_draw():
    if not is_admin():
        flash("Admin only.", "danger")
        return redirect(url_for("draw"))
    Assignment.query.delete()
    db.session.commit()
    flash("Draw reset.", "info")
    return redirect(url_for("draw"))


# ── Results ──────────────────────────────────────────────────────────────────

@app.route("/results")
def results():
    return redirect(url_for("tournament", tab="results"))


@app.route("/results/<int:mid>/delete", methods=["POST"])
def delete_match(mid):
    if not is_admin():
        flash("Admin only.", "danger")
        return redirect(url_for("results"))
    db.session.delete(Match.query.get_or_404(mid))
    db.session.commit()
    flash("Match deleted.", "info")
    return redirect(url_for("results"))


# ── Fixtures (live from ESPN) ─────────────────────────────────────────────────

@app.route("/fixtures")
def fixtures():
    return redirect(url_for("tournament", tab="fixtures"))


@app.route("/bracket")
def bracket():
    return redirect(url_for("tournament", tab="bracket"))


# ── Country profile ───────────────────────────────────────────────────────────

# Fun categories that rank cleanly on a single numeric metric.
# key → (label, attribute, higher_is_better)
RANKED_METRICS = {
    "golden_boot":   ("Goals scored",   "total_goals_for",       True),
    "best_defense":  ("Goals conceded", "total_goals_conceded",  False),
    "dirtiest":      ("Card points",    "total_card_points",     True),
    "fairest":       ("Card points",    "total_card_points",     False),
    "penalty_kings": ("Shootout wins",  "penalty_wins",          True),
}


def get_team_fun_standings(team):
    """For each fun category, where this team ranks (or whether it leads)."""
    out = []
    played_teams = [t for t in Team.query.all() if any(m.played for m in t.all_matches)]
    for cat in FunCategory.query.order_by(FunCategory.sort_order).all():
        leaders, _ = get_fun_leaders(cat)
        is_leader = any(t.id == team.id for t in leaders)
        rank = total = value = None
        if cat.calc_key in RANKED_METRICS:
            label, attr, higher = RANKED_METRICS[cat.calc_key]
            team_val = getattr(team, attr)
            value = f"{team_val} {label.lower()}"
            # For "more is better" stats, a 0 isn't a meaningful ranking.
            if not (higher and not team_val):
                ranked = [t for t in played_teams if getattr(t, attr) is not None]
                ranked.sort(key=lambda t: getattr(t, attr), reverse=higher)
                total = len(ranked)
                for i, t in enumerate(ranked, 1):
                    if t.id == team.id:
                        rank = i
                        break
        out.append({"cat": cat, "is_leader": is_leader,
                    "rank": rank, "total": total, "value": value,
                    "leaders": leaders})
    return out


@app.route("/team/<code>")
def team_profile(code):
    team = Team.query.filter_by(code=code).first_or_404()
    group_tables = get_group_tables()
    matches = sorted(team.all_matches,
                     key=lambda m: (m.match_date or datetime.max, m.id))
    fun_standings = get_team_fun_standings(team)
    owners = [a.participant for a in team.assignments]
    return render_template(
        "country.html",
        team=team,
        group_table=group_tables.get(team.group_name, []),
        matches=matches,
        fun_standings=fun_standings,
        owners=owners,
    )


# ── Leaderboard ──────────────────────────────────────────────────────────────

@app.route("/leaderboard")
def leaderboard():
    participants_list = Participant.query.all()
    standings = sorted(participants_list, key=lambda p: p.total_points, reverse=True)
    draw_done = Assignment.query.count() > 0
    return render_template("leaderboard.html", standings=standings, draw_done=draw_done)


# ── Prizes ───────────────────────────────────────────────────────────────────

@app.route("/prizes")
def prizes():
    prizes_list = Prize.query.all()
    participants_list = Participant.query.order_by(Participant.name).all()
    summary = get_sweepstakes_summary()
    fun_prizes_map = get_fun_prizes_by_participant()
    return render_template("prizes.html", prizes=prizes_list,
                           participants=participants_list,
                           summary=summary, fun_prizes_map=fun_prizes_map)


@app.route("/prizes/add", methods=["POST"])
def add_prize():
    if not is_admin():
        flash("Admin only.", "danger")
        return redirect(url_for("prizes"))
    label = request.form.get("label", "").strip()
    if not label:
        flash("Prize label required.", "danger")
        return redirect(url_for("prizes"))
    db.session.add(Prize(label=label, amount=float(request.form.get("amount", 0))))
    db.session.commit()
    flash("Prize added.", "success")
    return redirect(url_for("prizes"))


@app.route("/prizes/<int:pid>/payout", methods=["POST"])
def payout_prize(pid):
    if not is_admin():
        flash("Admin only.", "danger")
        return redirect(url_for("prizes"))
    prize = Prize.query.get_or_404(pid)
    wid = request.form.get("winner_id")
    prize.winner_id = int(wid) if wid else None
    prize.paid_out = True
    db.session.commit()
    flash(f"'{prize.label}' paid out.", "success")
    return redirect(url_for("prizes"))


@app.route("/prizes/<int:pid>/delete", methods=["POST"])
def delete_prize(pid):
    if not is_admin():
        flash("Admin only.", "danger")
        return redirect(url_for("prizes"))
    db.session.delete(Prize.query.get_or_404(pid))
    db.session.commit()
    flash("Prize removed.", "info")
    return redirect(url_for("prizes"))


# ── Sync ─────────────────────────────────────────────────────────────────────

@app.route("/admin/sync", methods=["POST"])
def admin_sync():
    from espn import sync_fixtures
    result = sync_fixtures(app)
    if result.get("error"):
        flash(f"Sync failed: {result['error']}", "danger")
    else:
        flash(f"Sync — {result['created']} new, {result['updated']} updated, "
              f"{result['skipped']} unmatched.", "success")
    return redirect(request.referrer or url_for("results"))


# ── API ───────────────────────────────────────────────────────────────────────

@app.route("/api/leaderboard")
def api_leaderboard():
    participants_list = Participant.query.all()
    standings = sorted(participants_list, key=lambda p: p.total_points, reverse=True)
    return jsonify([
        {"rank": i+1, "name": p.name, "points": p.total_points,
         "teams": [t.name for t in p.teams]}
        for i, p in enumerate(standings)
    ])


# ── Easter egg ────────────────────────────────────────────────────────────────

@app.route("/lucky")
def lucky():
    participants_list = Participant.query.all()
    lucky_one = random.choice(participants_list) if participants_list else None
    return render_template("lucky.html", lucky=lucky_one)


# ── Init ──────────────────────────────────────────────────────────────────────

def is_admin():
    return session.get("is_admin", False)


def is_draw_public():
    s = AppSettings.query.get("draw_public")
    return s and s.value == "true"


def migrate_db():
    """Add columns that exist in the models but not yet in the live DB.
    db.create_all() creates missing TABLES but never adds columns to
    pre-existing ones — so columns added in later releases need this."""
    from sqlalchemy import inspect, text
    inspector = inspect(db.engine)
    expected = {
        "teams": {
            "flag_emoji": "VARCHAR(10)",
        },
        "matches": {
            "home_yellows": "INTEGER",
            "away_yellows": "INTEGER",
            "home_reds": "INTEGER",
            "away_reds": "INTEGER",
            "home_ht_score": "INTEGER",
            "away_ht_score": "INTEGER",
            "first_goal_team_id": "INTEGER",
            "api_fixture_id": "INTEGER",
            "cards_synced": "BOOLEAN",
        },
    }
    for table, cols in expected.items():
        if not inspector.has_table(table):
            continue
        existing = {c["name"] for c in inspector.get_columns(table)}
        for col, coltype in cols.items():
            if col not in existing:
                try:
                    db.session.execute(text(
                        f"ALTER TABLE {table} ADD COLUMN {col} {coltype}"
                    ))
                    db.session.commit()
                    print(f"Migrated: added {table}.{col}")
                except Exception as exc:
                    db.session.rollback()
                    print(f"Migration skip {table}.{col}: {exc}")


def init_db():
    db.create_all()
    migrate_db()
    if Team.query.count() == 0:
        for t in TEAMS:
            db.session.add(Team(**t))
        db.session.commit()
    # Backfill flag emojis for existing teams
    for team in Team.query.all():
        if not team.flag_emoji:
            team.flag_emoji = FLAG_EMOJIS.get(team.code, "🏳️")
    db.session.commit()
    # Add any participants from seed_data not already present (idempotent — lets
    # new entrants be added on deploy without wiping existing data or the draw).
    existing_participants = {p.name for p in Participant.query.all()}
    for p in PARTICIPANTS:
        if p["name"] not in existing_participants:
            db.session.add(Participant(**p))
    db.session.commit()
    existing_names = {c.name for c in FunCategory.query.all()}
    added = False
    for f in FUN_CATEGORIES:
        if f["name"] not in existing_names:
            db.session.add(FunCategory(**f))
            added = True
    if added:
        db.session.commit()
    # Remove subjective categories — we only run objective, auto-calculated ones
    subjective = FunCategory.query.filter(FunCategory.calc_key.is_(None)).all()
    if subjective:
        for cat in subjective:
            FunWinner.query.filter_by(category_id=cat.id).delete()
            db.session.delete(cat)
        db.session.commit()


# ── Admin auth ────────────────────────────────────────────────────────────────

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        pw = request.form.get("password", "")
        if pw == os.environ.get("ADMIN_PASSWORD", "wc2026"):
            session["is_admin"] = True
            flash("Admin mode activated. 🔑", "success")
            return redirect(request.form.get("next") or url_for("index"))
        flash("Wrong password.", "danger")
    return render_template("admin_login.html",
                           next=request.args.get("next", ""))


@app.route("/admin/logout")
def admin_logout():
    session.pop("is_admin", None)
    flash("Logged out of admin.", "info")
    return redirect(url_for("index"))


@app.route("/admin/reseed", methods=["POST"])
def reseed_teams():
    """Wipe teams/matches/assignments and re-seed from seed_data.TEAMS.

    Use when the provisional team list/groups need replacing with the real
    draw. This clears the draw — re-run it afterwards on the Draw page.
    """
    if not is_admin():
        flash("Admin only.", "danger")
        return redirect(url_for("index"))
    FunWinner.query.delete()
    Assignment.query.delete()
    Match.query.delete()
    Team.query.delete()
    db.session.commit()
    for t in TEAMS:
        db.session.add(Team(**t, flag_emoji=FLAG_EMOJIS.get(t["code"], "🏳️")))
    db.session.commit()
    flash(f"Re-seeded {len(TEAMS)} teams. Matches and the draw were cleared — "
          "re-run the draw on the Draw page.", "success")
    return redirect(url_for("draw"))


@app.route("/admin/publish-draw", methods=["POST"])
def publish_draw():
    if not is_admin():
        flash("Admin only.", "danger")
        return redirect(url_for("draw"))
    s = AppSettings.query.get("draw_public") or AppSettings(key="draw_public")
    s.value = "true"
    db.session.merge(s)
    db.session.commit()
    flash("Draw published! Everyone can now see the assignments.", "success")
    return redirect(url_for("draw"))


@app.route("/admin/unpublish-draw", methods=["POST"])
def unpublish_draw():
    if not is_admin():
        flash("Admin only.", "danger")
        return redirect(url_for("draw"))
    s = AppSettings.query.get("draw_public") or AppSettings(key="draw_public")
    s.value = "false"
    db.session.merge(s)
    db.session.commit()
    flash("Draw hidden from public.", "info")
    return redirect(url_for("draw"))


with app.app_context():
    init_db()

import os as _os
if not app.debug or _os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from espn import sync_fixtures as _sync
        _scheduler = BackgroundScheduler(daemon=True)
        _scheduler.add_job(lambda: _sync(app), "interval", hours=3, id="sync_fixtures")
        _scheduler.start()
    except Exception as _e:
        print(f"Scheduler not started: {_e}")

if __name__ == "__main__":
    app.run(debug=True)
