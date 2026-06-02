import os
import random
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from models import db, Team, Participant, Assignment, Match, Prize
from seed_data import TEAMS, PARTICIPANTS

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-in-prod")

# Database configuration — PostgreSQL on Heroku, SQLite locally
database_url = os.environ.get("DATABASE_URL", "sqlite:///sweepstakes.db")
if database_url.startswith("postgres://"):  # Heroku uses deprecated prefix
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)


def get_sweepstakes_summary():
    total_pot = sum(p.entry_fee_paid for p in Participant.query.all())
    prizes = Prize.query.all()
    prizes_allocated = sum(p.amount for p in prizes)
    return {"pot": total_pot, "allocated": prizes_allocated}


# ── Routes ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    teams = Team.query.order_by(Team.group_name, Team.name).all()
    groups = {}
    for t in teams:
        groups.setdefault(t.group_name or "?", []).append(t)
    recent_matches = (
        Match.query.filter(Match.home_score.isnot(None))
        .order_by(Match.id.desc())
        .limit(5)
        .all()
    )
    upcoming = (
        Match.query.filter(Match.home_score.is_(None))
        .order_by(Match.match_date)
        .limit(5)
        .all()
    )
    summary = get_sweepstakes_summary()
    return render_template(
        "index.html",
        groups=groups,
        recent_matches=recent_matches,
        upcoming=upcoming,
        summary=summary,
    )


# ── Participants ─────────────────────────────────────────────────────────────

@app.route("/participants")
def participants():
    people = Participant.query.order_by(Participant.name).all()
    summary = get_sweepstakes_summary()
    return render_template("participants.html", participants=people, summary=summary)


@app.route("/participants/add", methods=["POST"])
def add_participant():
    name = request.form.get("name", "").strip()
    fee = request.form.get("fee", 0)
    if not name:
        flash("Name is required.", "danger")
        return redirect(url_for("participants"))
    if Participant.query.filter_by(name=name).first():
        flash(f"'{name}' already exists.", "warning")
        return redirect(url_for("participants"))
    p = Participant(name=name, entry_fee_paid=float(fee))
    db.session.add(p)
    db.session.commit()
    flash(f"Added {name}.", "success")
    return redirect(url_for("participants"))


@app.route("/participants/<int:pid>/delete", methods=["POST"])
def delete_participant(pid):
    p = Participant.query.get_or_404(pid)
    db.session.delete(p)
    db.session.commit()
    flash(f"Removed {p.name}.", "info")
    return redirect(url_for("participants"))


@app.route("/participants/<int:pid>/fee", methods=["POST"])
def update_fee(pid):
    p = Participant.query.get_or_404(pid)
    p.entry_fee_paid = float(request.form.get("fee", 0))
    db.session.commit()
    flash(f"Updated fee for {p.name}.", "success")
    return redirect(url_for("participants"))


# ── Draw ─────────────────────────────────────────────────────────────────────

@app.route("/draw")
def draw():
    participants = Participant.query.order_by(Participant.name).all()
    unassigned_teams = Team.query.filter(~Team.id.in_(
        db.session.query(Assignment.team_id)
    )).order_by(Team.name).all()
    assignments = Assignment.query.order_by(Assignment.drawn_at).all()
    draw_done = Assignment.query.count() > 0
    return render_template(
        "draw.html",
        participants=participants,
        unassigned_teams=unassigned_teams,
        assignments=assignments,
        draw_done=draw_done,
    )


@app.route("/draw/run", methods=["POST"])
def run_draw():
    if Assignment.query.count() > 0:
        flash("Draw has already been run. Reset it first.", "warning")
        return redirect(url_for("draw"))

    participants = Participant.query.all()
    teams = Team.query.all()

    if not participants:
        flash("Add participants before running the draw.", "danger")
        return redirect(url_for("draw"))

    # Build a weighted pool: each participant appears once per £5 entry
    pool = []
    for p in participants:
        entries = max(1, round(p.entry_fee_paid / 5))
        pool.extend([p] * entries)
    random.shuffle(pool)
    random.shuffle(teams)
    # Assign every pool slot a team (cycling through teams so all entries get one)
    # Teams get multiple owners when entries > teams — that's intentional
    assigned_pairs = set()
    for i, participant in enumerate(pool):
        team = teams[i % len(teams)]
        pair = (participant.id, team.id)
        if pair not in assigned_pairs:
            assigned_pairs.add(pair)
            db.session.add(Assignment(participant_id=participant.id, team_id=team.id))

    db.session.commit()
    flash("Draw complete! Teams have been assigned.", "success")
    return redirect(url_for("draw"))


@app.route("/draw/reset", methods=["POST"])
def reset_draw():
    Assignment.query.delete()
    db.session.commit()
    flash("Draw reset. All assignments cleared.", "info")
    return redirect(url_for("draw"))


# ── Results ──────────────────────────────────────────────────────────────────

@app.route("/results")
def results():
    stage_filter = request.args.get("stage", "")
    query = Match.query
    if stage_filter:
        query = query.filter_by(stage=stage_filter)
    matches = query.order_by(Match.stage, Match.match_date).all()
    stages = [r[0] for r in db.session.query(Match.stage).distinct().all()]
    teams = Team.query.order_by(Team.name).all()
    return render_template("results.html", matches=matches, stages=stages, teams=teams, stage_filter=stage_filter)


@app.route("/results/add", methods=["POST"])
def add_match():
    home_id = request.form.get("home_team_id")
    away_id = request.form.get("away_team_id")
    stage = request.form.get("stage", "Group Stage")
    venue = request.form.get("venue", "").strip()
    match_date_str = request.form.get("match_date", "")

    if not home_id or not away_id or home_id == away_id:
        flash("Select two different teams.", "danger")
        return redirect(url_for("results"))

    from datetime import datetime
    match_date = None
    if match_date_str:
        try:
            match_date = datetime.strptime(match_date_str, "%Y-%m-%dT%H:%M")
        except ValueError:
            pass

    m = Match(
        home_team_id=int(home_id),
        away_team_id=int(away_id),
        stage=stage,
        venue=venue or None,
        match_date=match_date,
    )
    db.session.add(m)
    db.session.commit()
    flash("Match added.", "success")
    return redirect(url_for("results"))


@app.route("/results/<int:mid>/score", methods=["POST"])
def update_score(mid):
    m = Match.query.get_or_404(mid)
    m.home_score = int(request.form.get("home_score", 0))
    m.away_score = int(request.form.get("away_score", 0))

    home_pens = request.form.get("home_pens", "").strip()
    away_pens = request.form.get("away_pens", "").strip()
    if home_pens and away_pens:
        m.home_penalties = int(home_pens)
        m.away_penalties = int(away_pens)
        m.penalty_winner_id = m.home_team_id if int(home_pens) > int(away_pens) else m.away_team_id

    db.session.commit()
    flash("Score updated.", "success")
    return redirect(url_for("results"))


@app.route("/results/<int:mid>/eliminate", methods=["POST"])
def eliminate_team(mid):
    m = Match.query.get_or_404(mid)
    team_id = int(request.form.get("team_id"))
    stage = request.form.get("eliminated_stage", m.stage)
    team = Team.query.get_or_404(team_id)
    team.eliminated = True
    team.eliminated_stage = stage
    db.session.commit()
    flash(f"{team.name} marked as eliminated at {stage}.", "info")
    return redirect(url_for("results"))


@app.route("/results/<int:mid>/delete", methods=["POST"])
def delete_match(mid):
    m = Match.query.get_or_404(mid)
    db.session.delete(m)
    db.session.commit()
    flash("Match deleted.", "info")
    return redirect(url_for("results"))


# ── Leaderboard ──────────────────────────────────────────────────────────────

@app.route("/leaderboard")
def leaderboard():
    participants = Participant.query.all()
    standings = sorted(participants, key=lambda p: p.total_points, reverse=True)
    draw_done = Assignment.query.count() > 0
    return render_template("leaderboard.html", standings=standings, draw_done=draw_done)


# ── Prizes ───────────────────────────────────────────────────────────────────

@app.route("/prizes")
def prizes():
    prizes = Prize.query.all()
    participants = Participant.query.order_by(Participant.name).all()
    summary = get_sweepstakes_summary()
    return render_template("prizes.html", prizes=prizes, participants=participants, summary=summary)


@app.route("/prizes/add", methods=["POST"])
def add_prize():
    label = request.form.get("label", "").strip()
    amount = request.form.get("amount", 0)
    if not label:
        flash("Prize label is required.", "danger")
        return redirect(url_for("prizes"))
    db.session.add(Prize(label=label, amount=float(amount)))
    db.session.commit()
    flash("Prize added.", "success")
    return redirect(url_for("prizes"))


@app.route("/prizes/<int:pid>/payout", methods=["POST"])
def payout_prize(pid):
    prize = Prize.query.get_or_404(pid)
    winner_id = request.form.get("winner_id")
    prize.winner_id = int(winner_id) if winner_id else None
    prize.paid_out = True
    db.session.commit()
    flash(f"Prize '{prize.label}' marked as paid out.", "success")
    return redirect(url_for("prizes"))


@app.route("/prizes/<int:pid>/delete", methods=["POST"])
def delete_prize(pid):
    prize = Prize.query.get_or_404(pid)
    db.session.delete(prize)
    db.session.commit()
    flash("Prize removed.", "info")
    return redirect(url_for("prizes"))


# ── API ───────────────────────────────────────────────────────────────────────

@app.route("/api/leaderboard")
def api_leaderboard():
    participants = Participant.query.all()
    standings = sorted(participants, key=lambda p: p.total_points, reverse=True)
    return jsonify([
        {
            "rank": i + 1,
            "name": p.name,
            "points": p.total_points,
            "teams": [t.name for t in p.teams],
        }
        for i, p in enumerate(standings)
    ])


# ── Init ──────────────────────────────────────────────────────────────────────

def init_db():
    db.create_all()
    if Team.query.count() == 0:
        for t in TEAMS:
            db.session.add(Team(**t))
        db.session.commit()
        print(f"Seeded {len(TEAMS)} teams.")
    if Participant.query.count() == 0:
        for p in PARTICIPANTS:
            db.session.add(Participant(**p))
        db.session.commit()
        print(f"Seeded {len(PARTICIPANTS)} participants.")


with app.app_context():
    init_db()

if __name__ == "__main__":
    app.run(debug=True)
