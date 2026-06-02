import os
import random
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort
from models import db, Team, Participant, Assignment, Match, Prize, FunCategory, FunWinner
from seed_data import TEAMS, PARTICIPANTS, FUN_CATEGORIES

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-in-prod")

database_url = os.environ.get("DATABASE_URL", "sqlite:///sweepstakes.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)


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


def _calc_penalty_kings():
    teams = [(t.penalty_wins, t) for t in Team.query.all() if t.penalty_wins > 0]
    if not teams:
        return []
    teams.sort(key=lambda x: -x[0])
    max_wins = teams[0][0]
    return [t for (w, t) in teams if w == max_wins]


FUN_CALCS = {
    "wooden_spoon":  _calc_wooden_spoon,
    "biggest_loser": _calc_biggest_loser,
    "dirtiest":      _calc_dirtiest,
    "best_defense":  _calc_best_defense,
    "penalty_kings": _calc_penalty_kings,
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

@app.route("/standings")
def standings():
    group_tables = get_group_tables()
    knockout_matches = Match.query.filter(
        Match.stage != "Group Stage"
    ).order_by(Match.stage, Match.match_date).all()
    stages_order = ["Round of 32", "Round of 16", "Quarter-final", "Semi-final", "Runner-up", "Final"]
    knockout_by_stage = {}
    for m in knockout_matches:
        knockout_by_stage.setdefault(m.stage, []).append(m)
    return render_template(
        "standings.html",
        group_tables=group_tables,
        knockout_by_stage=knockout_by_stage,
        stages_order=stages_order,
    )


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
    FunWinner.query.filter_by(category_id=cid).delete()
    db.session.commit()
    flash("Winner cleared.", "info")
    return redirect(url_for("fun"))


# ── Draw ─────────────────────────────────────────────────────────────────────

@app.route("/draw")
def draw():
    participants_list = Participant.query.order_by(Participant.name).all()
    assignments = Assignment.query.all()
    draw_done = Assignment.query.count() > 0

    assignments_data = []
    if draw_done:
        for a in assignments:
            assignments_data.append({
                "team": a.team.name,
                "code": a.team.code,
                "group": a.team.group_name or "?",
                "confederation": a.team.confederation or "",
                "participant": a.participant.name,
            })
        random.shuffle(assignments_data)

    return render_template(
        "draw.html",
        participants=participants_list,
        assignments=assignments,
        assignments_data=assignments_data,
        draw_done=draw_done,
    )


@app.route("/draw/run", methods=["POST"])
def run_draw():
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
    Assignment.query.delete()
    db.session.commit()
    flash("Draw reset.", "info")
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
    return render_template("results.html", matches=matches, stages=stages,
                           teams=teams, stage_filter=stage_filter)


@app.route("/results/add", methods=["POST"])
def add_match():
    home_id = request.form.get("home_team_id")
    away_id = request.form.get("away_team_id")
    if not home_id or not away_id or home_id == away_id:
        flash("Select two different teams.", "danger")
        return redirect(url_for("results"))
    match_date = None
    ds = request.form.get("match_date", "")
    if ds:
        try:
            match_date = datetime.strptime(ds, "%Y-%m-%dT%H:%M")
        except ValueError:
            pass
    db.session.add(Match(
        home_team_id=int(home_id), away_team_id=int(away_id),
        stage=request.form.get("stage", "Group Stage"),
        venue=request.form.get("venue", "").strip() or None,
        match_date=match_date,
    ))
    db.session.commit()
    flash("Match added.", "success")
    return redirect(url_for("results"))


@app.route("/results/<int:mid>/score", methods=["POST"])
def update_score(mid):
    m = Match.query.get_or_404(mid)
    m.home_score = int(request.form.get("home_score", 0))
    m.away_score = int(request.form.get("away_score", 0))
    hp = request.form.get("home_pens", "").strip()
    ap = request.form.get("away_pens", "").strip()
    if hp and ap:
        m.home_penalties = int(hp)
        m.away_penalties = int(ap)
        m.penalty_winner_id = m.home_team_id if int(hp) > int(ap) else m.away_team_id
    hy = request.form.get("home_yellows", "").strip()
    ay = request.form.get("away_yellows", "").strip()
    hr = request.form.get("home_reds", "").strip()
    ar = request.form.get("away_reds", "").strip()
    if hy: m.home_yellows = int(hy)
    if ay: m.away_yellows = int(ay)
    if hr: m.home_reds = int(hr)
    if ar: m.away_reds = int(ar)
    db.session.commit()
    flash("Score updated.", "success")
    return redirect(url_for("results"))


@app.route("/results/<int:mid>/eliminate", methods=["POST"])
def eliminate_team(mid):
    m = Match.query.get_or_404(mid)
    team = Team.query.get_or_404(int(request.form.get("team_id")))
    team.eliminated = True
    team.eliminated_stage = request.form.get("eliminated_stage", m.stage)
    db.session.commit()
    flash(f"{team.name} eliminated.", "info")
    return redirect(url_for("results"))


@app.route("/results/<int:mid>/delete", methods=["POST"])
def delete_match(mid):
    db.session.delete(Match.query.get_or_404(mid))
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
    fun_prizes_map = get_fun_prizes_by_participant()
    return render_template("prizes.html", prizes=prizes_list,
                           participants=participants_list,
                           summary=summary, fun_prizes_map=fun_prizes_map)


@app.route("/prizes/add", methods=["POST"])
def add_prize():
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
    prize = Prize.query.get_or_404(pid)
    wid = request.form.get("winner_id")
    prize.winner_id = int(wid) if wid else None
    prize.paid_out = True
    db.session.commit()
    flash(f"'{prize.label}' paid out.", "success")
    return redirect(url_for("prizes"))


@app.route("/prizes/<int:pid>/delete", methods=["POST"])
def delete_prize(pid):
    db.session.delete(Prize.query.get_or_404(pid))
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

def init_db():
    db.create_all()
    if Team.query.count() == 0:
        for t in TEAMS:
            db.session.add(Team(**t))
        db.session.commit()
    if Participant.query.count() == 0:
        for p in PARTICIPANTS:
            db.session.add(Participant(**p))
        db.session.commit()
    if FunCategory.query.count() == 0:
        for f in FUN_CATEGORIES:
            db.session.add(FunCategory(**f))
        db.session.commit()


with app.app_context():
    init_db()

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
