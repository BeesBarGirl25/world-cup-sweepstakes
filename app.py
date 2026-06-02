import os
import random
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from models import db, Team, Participant, Assignment, Match, Prize
from seed_data import TEAMS, PARTICIPANTS

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-in-prod")

database_url = os.environ.get("DATABASE_URL", "sqlite:///sweepstakes.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)


def get_sweepstakes_summary():
    total_pot = sum(p.entry_fee_paid for p in Participant.query.all())
    prizes = Prize.query.all()
    prizes_allocated = sum(p.amount for p in prizes)
    return {"pot": total_pot, "allocated": prizes_allocated}


# ── Dashboard ────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    teams = Team.query.order_by(Team.group_name, Team.name).all()
    groups = {}
    for t in teams:
        groups.setdefault(t.group_name or "?", []).append(t)
    recent_matches = (
        Match.query.filter(Match.home_score.isnot(None))
        .order_by(Match.id.desc())
        .limit(6)
        .all()
    )
    upcoming = (
        Match.query.filter(Match.home_score.is_(None))
        .order_by(Match.match_date)
        .limit(5)
        .all()
    )
    summary = get_sweepstakes_summary()
    last_sync = _last_sync_time()
    return render_template(
        "index.html",
        groups=groups,
        recent_matches=recent_matches,
        upcoming=upcoming,
        summary=summary,
        last_sync=last_sync,
    )


# ── Participants (read-only) ──────────────────────────────────────────────────

@app.route("/participants")
def participants():
    people = Participant.query.order_by(Participant.name).all()
    summary = get_sweepstakes_summary()
    return render_template("participants.html", participants=people, summary=summary)


# ── Draw ─────────────────────────────────────────────────────────────────────

@app.route("/draw")
def draw():
    participants_list = Participant.query.order_by(Participant.name).all()
    assignments = Assignment.query.all()
    draw_done = Assignment.query.count() > 0
    return render_template(
        "draw.html",
        participants=participants_list,
        assignments=assignments,
        draw_done=draw_done,
    )


@app.route("/draw/run", methods=["POST"])
def run_draw():
    if Assignment.query.count() > 0:
        flash("Draw has already been run. Reset it first.", "warning")
        return redirect(url_for("draw"))

    participants_list = Participant.query.all()
    teams = Team.query.all()

    if not participants_list:
        flash("No participants to draw for.", "danger")
        return redirect(url_for("draw"))

    pool = []
    for p in participants_list:
        entries = max(1, round(p.entry_fee_paid / 5))
        pool.extend([p] * entries)
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
    last_sync = _last_sync_time()
    return render_template(
        "results.html",
        matches=matches,
        stages=stages,
        teams=teams,
        stage_filter=stage_filter,
        last_sync=last_sync,
    )


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
        m.penalty_winner_id = (
            m.home_team_id if int(home_pens) > int(away_pens) else m.away_team_id
        )

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
    flash(f"{team.name} eliminated at {stage}.", "info")
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
    return render_template(
        "prizes.html", prizes=prizes_list, participants=participants_list, summary=summary
    )


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
    flash(f"'{prize.label}' marked as paid out.", "success")
    return redirect(url_for("prizes"))


@app.route("/prizes/<int:pid>/delete", methods=["POST"])
def delete_prize(pid):
    prize = Prize.query.get_or_404(pid)
    db.session.delete(prize)
    db.session.commit()
    flash("Prize removed.", "info")
    return redirect(url_for("prizes"))


# ── Sync ─────────────────────────────────────────────────────────────────────

@app.route("/admin/sync", methods=["POST"])
def admin_sync():
    from sync import sync_fixtures
    result = sync_fixtures(app)
    if result.get("error"):
        flash(f"Sync failed: {result['error']}", "danger")
    else:
        flash(
            f"Sync complete — {result['created']} new, {result['updated']} updated "
            f"({result['skipped']} unmatched teams).",
            "success",
        )
    return redirect(request.referrer or url_for("results"))


# ── API ───────────────────────────────────────────────────────────────────────

@app.route("/api/leaderboard")
def api_leaderboard():
    participants_list = Participant.query.all()
    standings = sorted(participants_list, key=lambda p: p.total_points, reverse=True)
    return jsonify([
        {
            "rank": i + 1,
            "name": p.name,
            "points": p.total_points,
            "teams": [t.name for t in p.teams],
        }
        for i, p in enumerate(standings)
    ])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _last_sync_time():
    latest = Match.query.filter(Match.home_score.isnot(None)).order_by(Match.id.desc()).first()
    return None


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

# Background scheduler — polls football-data.org every 3 hours
# Only start outside Flask reloader child process to avoid duplicate jobs
import os as _os
if not app.debug or _os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from sync import sync_fixtures as _sync

        _scheduler = BackgroundScheduler(daemon=True)
        _scheduler.add_job(lambda: _sync(app), "interval", hours=3, id="sync_fixtures")
        _scheduler.start()
    except Exception as _e:
        print(f"Scheduler not started: {_e}")

if __name__ == "__main__":
    app.run(debug=True)
