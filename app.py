import os
import csv
import io
import random
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, Response
from markupsafe import Markup
from models import db, Team, Participant, Assignment, Match, Prize, FunCategory, FunWinner, AppSettings
from seed_data import TEAMS, PARTICIPANTS, FUN_CATEGORIES, FLAG_EMOJIS, TEAM_FACTS, TEAM_SONGS, FLAG_CC, flag_url

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-in-prod")

database_url = os.environ.get("DATABASE_URL", "sqlite:///sweepstakes.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

# Match times come from ESPN as UTC and are stored naive-UTC. Display them in
# UK local time so kickoffs read correctly (BST in summer, GMT in winter).
UK_TZ = ZoneInfo("Europe/London")


@app.template_filter("uk")
def uk_time(dt, fmt="%d %b %Y %H:%M"):
    """Format a datetime in UK local time. Naive values are assumed UTC."""
    if not dt:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(UK_TZ).strftime(fmt)


def flag_img(code, height="1em", extra=""):
    """Render a team's flag as an <img> (emoji flags don't render on Windows).
    Height defaults to 1em so it scales with whatever font-size it sits in."""
    url = flag_url(code, 160)
    if not url:
        return Markup("")
    return Markup(
        f'<img src="{url}" alt="" loading="lazy" class="flag-img" '
        f'style="height:{height};{extra}">'
    )


@app.context_processor
def inject_globals():
    return {
        "is_admin": is_admin(),
        "FLAG_EMOJIS": FLAG_EMOJIS,
        "TEAM_SONGS": TEAM_SONGS,
        "FLAG_CC": FLAG_CC,
        "flag_url": flag_url,
        "flag_img": flag_img,
    }


# ── Fun category auto-calculators ─────────────────────────────────────────────

def _calc_wooden_spoon():
    """Worst group team: fewest points → worst GD → fewest scored → most cards.
    Teams identical on all four split the prize."""
    records = []
    for team in Team.query.all():
        if not any(m.played for m in team.all_matches if m.stage == "Group Stage"):
            continue
        gd = team.group_goals_for - team.group_goals_against
        records.append((team.group_points, gd, team.group_goals_for,
                        team.total_card_points, team))
    if not records:
        return []
    records.sort(key=lambda x: (x[0], x[1], x[2], -x[3]))
    worst = records[0][:4]
    return [r[-1] for r in records if r[:4] == worst]


def _calc_biggest_loser():
    """Heaviest single defeat: biggest margin → most conceded. Different teams
    tied on both (e.g. two 4-0 hammerings) split the prize."""
    worst_by_team = {}  # team_id -> (margin, conceded, team) for its worst loss
    for m in Match.query.filter(Match.home_score.isnot(None)).all():
        h, a = m.home_score, m.away_score
        if h == a:
            continue
        if h > a:
            diff, loser, conceded = h - a, m.away_team, a
        else:
            diff, loser, conceded = a - h, m.home_team, h
        cur = worst_by_team.get(loser.id)
        if cur is None or (diff, conceded) > (cur[0], cur[1]):
            worst_by_team[loser.id] = (diff, conceded, loser)
    if not worst_by_team:
        return []
    ranked = sorted(worst_by_team.values(), key=lambda x: (-x[0], -x[1]))
    top_diff, top_conc = ranked[0][0], ranked[0][1]
    return [t for (d, c, t) in ranked if d == top_diff and c == top_conc]


def _calc_dirtiest():
    """Most card points → most reds → fewest matches (dirtier per game)."""
    data = []
    for t in Team.query.all():
        if t.total_card_points <= 0:
            continue
        mp = sum(1 for m in t.all_matches if m.played)
        data.append((t.total_card_points, t.total_reds, mp, t))
    if not data:
        return []
    data.sort(key=lambda x: (-x[0], -x[1], x[2]))
    top = data[0][:3]
    return [d[-1] for d in data if d[:3] == top]


def _calc_best_defense():
    """Fewest conceded → most matches played (clean over more games) →
    most goals scored."""
    data = []
    for t in Team.query.all():
        mp = sum(1 for m in t.all_matches if m.played)
        if mp == 0:
            continue
        data.append((t.total_goals_conceded, mp, t.total_goals_for, t))
    if not data:
        return []
    data.sort(key=lambda x: (x[0], -x[1], -x[2]))
    top = data[0][:3]
    return [d[-1] for d in data if d[:3] == top]


def _calc_golden_boot():
    """Most goals → fewest conceded → fewest matches (most clinical)."""
    data = []
    for t in Team.query.all():
        if t.total_goals_for <= 0:
            continue
        mp = sum(1 for m in t.all_matches if m.played)
        data.append((t.total_goals_for, t.total_goals_conceded, mp, t))
    if not data:
        return []
    data.sort(key=lambda x: (-x[0], x[1], x[2]))
    top = data[0][:3]
    return [d[-1] for d in data if d[:3] == top]


def _calc_penalty_kings():
    """Most shootout wins → furthest progress (total points)."""
    data = [(t.penalty_wins, t.total_points, t) for t in Team.query.all()
            if t.penalty_wins > 0]
    if not data:
        return []
    data.sort(key=lambda x: (-x[0], -x[1]))
    top = data[0][:2]
    return [d[-1] for d in data if d[:2] == top]


def _calc_plucky_underdog():
    """Best group-stage casualty: most points → GD → goals scored →
    fewest conceded."""
    data = []
    for t in Team.query.all():
        if t.eliminated_stage != "Group Stage":
            continue
        gd = t.group_goals_for - t.group_goals_against
        data.append((t.group_points, gd, t.group_goals_for,
                     t.group_goals_against, t))
    if not data:
        return []
    data.sort(key=lambda x: (-x[0], -x[1], -x[2], x[3]))
    top = data[0][:4]
    return [d[-1] for d in data if d[:4] == top]


def _calc_draw_specialists():
    """Most draws → fewest matches (higher draw rate) → more goals in those
    draws (more entertaining)."""
    data = []
    for t in Team.query.all():
        if t.draws <= 0:
            continue
        mp = goals_in_draws = 0
        for m in t.all_matches:
            if not m.played:
                continue
            mp += 1
            if m.home_score == m.away_score:
                goals_in_draws += m.home_score + m.away_score
        data.append((t.draws, mp, goals_in_draws, t))
    if not data:
        return []
    data.sort(key=lambda x: (-x[0], x[1], -x[2]))
    top = data[0][:3]
    return [d[-1] for d in data if d[:3] == top]


def _calc_sieve():
    """Most conceded → fewest scored → fewest matches (leakier per game)."""
    data = []
    for t in Team.query.all():
        mp = sum(1 for m in t.all_matches if m.played)
        if mp == 0 or t.total_goals_conceded <= 0:
            continue
        data.append((t.total_goals_conceded, t.total_goals_for, mp, t))
    if not data:
        return []
    data.sort(key=lambda x: (-x[0], x[1], x[2]))
    top = data[0][:3]
    return [d[-1] for d in data if d[:3] == top]


def _calc_comeback_kings():
    """Most wins from a losing HT position → biggest HT deficit overturned
    in a single game."""
    stats = {}  # team_id -> [count, max_deficit, team]
    for m in Match.query.filter(
        Match.home_ht_score.isnot(None),
        Match.home_score.isnot(None),
    ).all():
        # Home team comeback
        if m.home_ht_score < m.away_ht_score and m.home_score > m.away_score:
            s = stats.setdefault(m.home_team_id, [0, 0, m.home_team])
            s[0] += 1
            s[1] = max(s[1], m.away_ht_score - m.home_ht_score)
        # Away team comeback
        if m.away_ht_score < m.home_ht_score and m.away_score > m.home_score:
            s = stats.setdefault(m.away_team_id, [0, 0, m.away_team])
            s[0] += 1
            s[1] = max(s[1], m.home_ht_score - m.away_ht_score)
    if not stats:
        return []
    ranked = sorted(stats.values(), key=lambda v: (-v[0], -v[1]))
    top = (ranked[0][0], ranked[0][1])
    return [v[2] for v in ranked if (v[0], v[1]) == top]


def _calc_fairest():
    """Fewest card points → fewest reds → most matches played (stayed clean
    longest) → most goals scored."""
    data = []
    for t in Team.query.all():
        if not any(m.cards_synced for m in t.all_matches):
            continue
        mp = sum(1 for m in t.all_matches if m.played)
        data.append((t.total_card_points, t.total_reds, mp, t.total_goals_for, t))
    if not data:
        return []
    data.sort(key=lambda x: (x[0], x[1], -x[2], -x[3]))
    top = data[0][:4]
    return [d[-1] for d in data if d[:4] == top]


FUN_CALCS = {
    "wooden_spoon":  _calc_wooden_spoon,
    "biggest_loser": _calc_biggest_loser,
    "dirtiest":      _calc_dirtiest,
    "best_defense":  _calc_best_defense,
    "golden_boot":   _calc_golden_boot,
    "penalty_kings": _calc_penalty_kings,
    "plucky_underdog": _calc_plucky_underdog,
    "draw_specialists": _calc_draw_specialists,
    "sieve":         _calc_sieve,
    "comeback_kings":_calc_comeback_kings,
    "fairest":       _calc_fairest,
}


def get_fun_leaders(category):
    """Return (teams, is_auto) — teams currently leading this fun category."""
    if category.calc_key and category.calc_key in FUN_CALCS:
        return FUN_CALCS[category.calc_key](), True
    return [w.team for w in category.winners if w.team], False


def get_fun_prizes_by_participant():
    """Returns dict of participant_id → total fun prizes earned.

    Each owner of a winning team gets the full category prize. If a category
    ends in an unbroken tie (multiple teams share top spot after every
    tie-breaker), every tied winner still receives the full prize."""
    prizes = {}
    for cat in FunCategory.query.order_by(FunCategory.sort_order).all():
        teams, _ = get_fun_leaders(cat)
        for team in teams:
            for a in team.assignments:
                prizes[a.participant_id] = prizes.get(a.participant_id, 0) + cat.prize
    return prizes


def get_sweepstakes_summary():
    # Round to the nearest pound for display (contributions include odd pennies,
    # e.g. Will Hicks £19.42, Martin Durchov £10.39).
    total_pot = round(sum(p.entry_fee_paid for p in Participant.query.all()))
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
                "flag_url": flag_url(a.team.code, 160),
                "group": a.team.group_name or "?",
                "confederation": a.team.confederation or "",
                "fact": random.choice(team_facts),
                "participant": a.participant.name,
            })
        random.shuffle(assignments_data)

    total_entries = sum(p.entries for p in participants_list)
    team_count = Team.query.count()
    return render_template(
        "draw.html",
        participants=participants_list,
        assignments=assignments,
        assignments_data=assignments_data,
        draw_done=draw_done,
        draw_public=draw_pub,
        is_admin=admin,
        total_entries=total_entries,
        team_count=team_count,
        shared_count=max(0, total_entries - team_count),
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
    if not teams:
        flash("No teams to draw. Re-seed teams first.", "warning")
        return redirect(url_for("draw"))

    # Every entry must yield a DISTINCT team for that person, and teams are
    # shared as evenly as possible (total entries usually exceeds team count).
    # Capacity = how many people may share each team, spread evenly.
    total_entries = sum(p.entries for p in participants_list)
    base, extra = divmod(total_entries, len(teams))
    shuffled = teams[:]
    random.shuffle(shuffled)
    capacity = {t.id: base + (1 if i < extra else 0) for i, t in enumerate(shuffled)}

    # Deal to the people with most entries first — they're the hardest to satisfy
    # with distinct teams, so placing them early avoids dead-ends.
    for p in sorted(participants_list, key=lambda x: x.entries, reverse=True):
        taken = set()
        for _ in range(p.entries):
            options = [t for t in teams if t.id not in taken and capacity[t.id] > 0]
            if not options:  # capacity exhausted — relax evenness, keep distinctness
                options = [t for t in teams if t.id not in taken]
            if not options:  # more entries than teams (impossible here) — stop
                break
            # Prefer the most-available teams to keep sharing balanced.
            random.shuffle(options)
            options.sort(key=lambda t: capacity[t.id], reverse=True)
            team = options[0]
            taken.add(team.id)
            capacity[team.id] -= 1
            db.session.add(Assignment(participant_id=p.id, team_id=team.id))

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


# ── Participant management (admin) ─────────────────────────────────────────────

@app.route("/draw/participant/add", methods=["POST"])
def add_participant():
    if not is_admin():
        flash("Admin only.", "danger")
        return redirect(url_for("draw"))
    name = (request.form.get("name") or "").strip()
    try:
        entries = int(request.form.get("entries", 1))
    except (TypeError, ValueError):
        entries = 1
    entries = max(1, min(entries, 50))
    if not name:
        flash("Enter a name.", "warning")
        return redirect(url_for("draw"))
    existing = Participant.query.filter(db.func.lower(Participant.name) == name.lower()).first()
    if existing:
        # Top up an existing player's entries rather than erroring/duplicating.
        existing.entry_fee_paid = entries * 5.0
        db.session.commit()
        flash(f"Updated {existing.name} to {entries} entr{'y' if entries == 1 else 'ies'}.", "success")
        return redirect(url_for("draw"))
    # entries stored as fee (£5 = 1 entry) to match how Participant.entries works.
    db.session.add(Participant(name=name, entry_fee_paid=entries * 5.0))
    db.session.commit()
    flash(f"Added {name} with {entries} entr{'y' if entries == 1 else 'ies'}.", "success")
    return redirect(url_for("draw"))


@app.route("/draw/participant/<int:pid>/delete", methods=["POST"])
def delete_participant(pid):
    if not is_admin():
        flash("Admin only.", "danger")
        return redirect(url_for("draw"))
    p = Participant.query.get_or_404(pid)
    name = p.name
    db.session.delete(p)  # cascades to their assignments
    db.session.commit()
    flash(f"Removed {name}.", "info")
    return redirect(url_for("draw"))


# ── Draw backup: export / import ───────────────────────────────────────────────

@app.route("/draw/export")
def export_draw():
    """Download the full draw (who got which team) as a CSV backup.

    Re-importable via /draw/import to repopulate if the DB is ever reset."""
    if not is_admin():
        flash("Admin only.", "danger")
        return redirect(url_for("draw"))
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Participant", "Entries", "Team", "TeamCode", "Group", "Confederation"])
    rows = (Assignment.query
            .join(Participant).join(Team, Assignment.team_id == Team.id)
            .order_by(Participant.name, Team.group_name).all())
    for a in rows:
        writer.writerow([
            a.participant.name, a.participant.entries, a.team.name,
            a.team.code, a.team.group_name or "", a.team.confederation or "",
        ])
    stamp = datetime.utcnow().strftime("%Y%m%d-%H%M")
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=wc2026-draw-{stamp}.csv"},
    )


@app.route("/draw/import", methods=["POST"])
def import_draw():
    """Repopulate assignments from a previously exported CSV.

    Matches teams by code and participants by name (creating any missing
    participants from the Entries column). Replaces the current draw."""
    if not is_admin():
        flash("Admin only.", "danger")
        return redirect(url_for("draw"))
    file = request.files.get("file")
    if not file or not file.filename:
        flash("Choose a CSV file to import.", "warning")
        return redirect(url_for("draw"))
    try:
        text = file.read().decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        teams_by_code = {t.code: t for t in Team.query.all()}
        people_by_name = {p.name: p for p in Participant.query.all()}
        pairs, skipped = [], 0
        for row in reader:
            pname = (row.get("Participant") or "").strip()
            code = (row.get("TeamCode") or "").strip()
            if not pname or not code:
                continue
            team = teams_by_code.get(code)
            if team is None:
                skipped += 1
                continue
            person = people_by_name.get(pname)
            if person is None:
                try:
                    entries = int(row.get("Entries", 1))
                except (TypeError, ValueError):
                    entries = 1
                person = Participant(name=pname, entry_fee_paid=max(1, entries) * 5.0)
                db.session.add(person)
                db.session.flush()
                people_by_name[pname] = person
            pairs.append((person.id, team.id))
    except Exception as e:
        flash(f"Could not read that CSV: {e}", "danger")
        return redirect(url_for("draw"))

    if not pairs:
        flash("No valid rows found in that CSV — nothing imported.", "warning")
        return redirect(url_for("draw"))

    Assignment.query.delete()
    for participant_id, team_id in pairs:
        db.session.add(Assignment(participant_id=participant_id, team_id=team_id))
    db.session.commit()
    msg = f"Imported {len(pairs)} assignments from backup."
    if skipped:
        msg += f" ({skipped} row(s) skipped — unknown team code.)"
    flash(msg, "success")
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
    "sieve":         ("Goals conceded", "total_goals_conceded",  True),
    "draw_specialists": ("Draws",       "draws",                 True),
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


KO_PROGRESSION = ["Round of 32", "Round of 16", "Quarter-final", "Semi-final", "Final"]


def get_team_progression(team, fixtures):
    """A step-by-step path of the team's run to the Final, from ESPN fixtures."""
    code = team.code

    def side(f):
        if not f["home"]["placeholder"] and f["home"]["abbrev"] == code:
            return "home"
        if not f["away"]["placeholder"] and f["away"]["abbrev"] == code:
            return "away"
        return None

    by_stage = {}
    for f in fixtures:
        if side(f):
            by_stage.setdefault(f["stage"], []).append(f)

    steps = []
    # ── Group stage ──
    grp = by_stage.get("Group Stage", [])
    grp_played = [f for f in grp if f["state"] == "post"]
    reached_ko = any(s in by_stage for s in KO_PROGRESSION)
    if team.eliminated_stage == "Group Stage":
        gstatus = "eliminated"
    elif reached_ko or team.eliminated_stage in (["Champion"] + KO_PROGRESSION + ["Runner-up"]):
        gstatus = "advanced"
    elif grp and len(grp_played) < len(grp):
        gstatus = "current"
    elif grp_played:
        gstatus = "advanced"
    else:
        gstatus = "upcoming"
    steps.append({
        "stage": "Group Stage", "status": gstatus,
        "detail": (f"Group {team.group_name} · {team.group_points} pts"
                   if grp_played else f"Group {team.group_name}"),
        "opponent": None, "score": None, "date": None,
    })

    elim_idx = (KO_PROGRESSION.index(team.eliminated_stage)
                if team.eliminated_stage in KO_PROGRESSION else None)
    for i, st in enumerate(KO_PROGRESSION):
        fs = by_stage.get(st)
        if not fs:
            locked = gstatus == "eliminated" or (elim_idx is not None and elim_idx < i)
            steps.append({"stage": st, "status": "locked" if locked else "future",
                          "opponent": None, "score": None, "date": None, "detail": None})
            continue
        f = fs[0]
        s = side(f)
        opp = f["away"] if s == "home" else f["home"]
        my = f[s]
        score = date = None
        if f["state"] == "post":
            if my["shootout"] is not None and opp["shootout"] is not None:
                won = my["shootout"] > opp["shootout"]
            else:
                won = (my["score"] or 0) > (opp["score"] or 0)
            status = ("champion" if (st == "Final" and won) else
                      "advanced" if won else "eliminated")
            score = f"{my['score']}–{opp['score']}"
            if my["shootout"] is not None:
                score += f" (p{my['shootout']}–{opp['shootout']})"
        elif f["state"] == "in":
            status, score = "current", "LIVE"
        else:
            status = "next"
        if f["date"]:
            date = f["date"].strftime("%d %b")
        steps.append({"stage": st, "status": status, "opponent": opp,
                      "score": score, "date": date, "detail": None})
    return steps


@app.route("/team/<code>")
def team_profile(code):
    from espn import fetch_fixtures
    team = Team.query.filter_by(code=code).first_or_404()
    group_tables = get_group_tables()
    matches = sorted(team.all_matches,
                     key=lambda m: (m.match_date or datetime.max, m.id))
    fun_standings = get_team_fun_standings(team)
    owners = [a.participant for a in team.assignments]
    progression = get_team_progression(team, fetch_fixtures())
    return render_template(
        "country.html",
        team=team,
        group_table=group_tables.get(team.group_name, []),
        matches=matches,
        fun_standings=fun_standings,
        owners=owners,
        progression=progression,
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
    # Sync participants from seed_data (idempotent — lets new entrants be added
    # and contribution totals corrected on deploy without wiping existing data
    # or the draw). Admin-added players (not in PARTICIPANTS) are left untouched.
    existing_participants = {p.name: p for p in Participant.query.all()}
    for p in PARTICIPANTS:
        existing = existing_participants.get(p["name"])
        if existing is None:
            db.session.add(Participant(**p))
        elif existing.entry_fee_paid != p["entry_fee_paid"]:
            existing.entry_fee_paid = p["entry_fee_paid"]
    db.session.commit()
    existing_names = {c.name for c in FunCategory.query.all()}
    added = False
    for f in FUN_CATEGORIES:
        if f["name"] not in existing_names:
            db.session.add(FunCategory(**f))
            added = True
    if added:
        db.session.commit()
    # Remove categories we no longer run: subjective (no calc_key) or orphaned
    # ones whose calculator has been retired (e.g. First Blood).
    stale = [c for c in FunCategory.query.all()
             if not c.calc_key or c.calc_key not in FUN_CALCS]
    if stale:
        for cat in stale:
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
        _scheduler.add_job(lambda: _sync(app), "interval", minutes=10, id="sync_fixtures")
        _scheduler.start()
    except Exception as _e:
        print(f"Scheduler not started: {_e}")

if __name__ == "__main__":
    app.run(debug=True)
