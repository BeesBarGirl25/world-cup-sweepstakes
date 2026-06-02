from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

STAGE_POINTS = {
    "Group Stage": 0,
    "Round of 32": 2,
    "Round of 16": 4,
    "Quarter-final": 7,
    "Semi-final": 11,
    "Runner-up": 15,
    "Champion": 20,
}


class Team(db.Model):
    __tablename__ = "teams"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    code = db.Column(db.String(3), nullable=False)
    group_name = db.Column(db.String(1), nullable=True)
    confederation = db.Column(db.String(20), nullable=True)
    eliminated = db.Column(db.Boolean, default=False)
    eliminated_stage = db.Column(db.String(50), nullable=True)
    flag_emoji = db.Column(db.String(10), nullable=True)

    assignments = db.relationship("Assignment", back_populates="team")
    home_matches = db.relationship("Match", foreign_keys="Match.home_team_id", back_populates="home_team")
    away_matches = db.relationship("Match", foreign_keys="Match.away_team_id", back_populates="away_team")
    fun_wins = db.relationship("FunWinner", back_populates="team")

    @property
    def all_matches(self):
        return list(self.home_matches) + list(self.away_matches)

    @property
    def points(self):
        total = 0
        for m in self.all_matches:
            if not m.played:
                continue
            if m.stage == "Group Stage":
                is_home = m.home_team_id == self.id
                gf = m.home_score if is_home else m.away_score
                ga = m.away_score if is_home else m.home_score
                if gf > ga:
                    total += 1
                if m.penalty_winner_id == self.id:
                    total += 1
        if self.eliminated_stage:
            total += STAGE_POINTS.get(self.eliminated_stage, 0)
        return total

    @property
    def group_goals_for(self):
        total = 0
        for m in self.all_matches:
            if m.stage == "Group Stage" and m.played:
                total += m.home_score if m.home_team_id == self.id else m.away_score
        return total

    @property
    def group_goals_against(self):
        total = 0
        for m in self.all_matches:
            if m.stage == "Group Stage" and m.played:
                total += m.away_score if m.home_team_id == self.id else m.home_score
        return total

    @property
    def group_points(self):
        pts = 0
        for m in self.all_matches:
            if m.stage == "Group Stage" and m.played:
                is_home = m.home_team_id == self.id
                gf = m.home_score if is_home else m.away_score
                ga = m.away_score if is_home else m.home_score
                if gf > ga: pts += 3
                elif gf == ga: pts += 1
        return pts

    @property
    def total_goals_conceded(self):
        total = 0
        for m in self.all_matches:
            if m.played:
                total += m.away_score if m.home_team_id == self.id else m.home_score
        return total

    @property
    def total_card_points(self):
        total = 0
        for m in self.all_matches:
            if m.home_team_id == self.id:
                total += (m.home_yellows or 0) + (m.home_reds or 0) * 3
            else:
                total += (m.away_yellows or 0) + (m.away_reds or 0) * 3
        return total

    @property
    def total_reds(self):
        total = 0
        for m in self.all_matches:
            if m.home_team_id == self.id:
                total += m.home_reds or 0
            else:
                total += m.away_reds or 0
        return total

    @property
    def penalty_wins(self):
        return sum(1 for m in self.all_matches if m.penalty_winner_id == self.id)


class Participant(db.Model):
    __tablename__ = "participants"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    entry_fee_paid = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    assignments = db.relationship("Assignment", back_populates="participant", cascade="all, delete-orphan")

    @property
    def total_points(self):
        return sum(a.team.points for a in self.assignments)

    @property
    def teams(self):
        return [a.team for a in self.assignments]

    @property
    def entries(self):
        return max(1, round(self.entry_fee_paid / 5))

    @property
    def alive_teams(self):
        return [t for t in self.teams if not t.eliminated]


class Assignment(db.Model):
    __tablename__ = "assignments"
    id = db.Column(db.Integer, primary_key=True)
    participant_id = db.Column(db.Integer, db.ForeignKey("participants.id"), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    drawn_at = db.Column(db.DateTime, default=datetime.utcnow)

    participant = db.relationship("Participant", back_populates="assignments")
    team = db.relationship("Team", back_populates="assignments")


class Match(db.Model):
    __tablename__ = "matches"
    id = db.Column(db.Integer, primary_key=True)
    stage = db.Column(db.String(50), nullable=False, default="Group Stage")
    match_date = db.Column(db.DateTime, nullable=True)
    venue = db.Column(db.String(100), nullable=True)
    home_team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    away_team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    home_score = db.Column(db.Integer, nullable=True)
    away_score = db.Column(db.Integer, nullable=True)
    home_penalties = db.Column(db.Integer, nullable=True)
    away_penalties = db.Column(db.Integer, nullable=True)
    penalty_winner_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=True)
    home_yellows = db.Column(db.Integer, nullable=True)
    away_yellows = db.Column(db.Integer, nullable=True)
    home_reds = db.Column(db.Integer, nullable=True)
    away_reds = db.Column(db.Integer, nullable=True)
    home_ht_score = db.Column(db.Integer, nullable=True)
    away_ht_score = db.Column(db.Integer, nullable=True)
    first_goal_team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=True)
    api_fixture_id = db.Column(db.Integer, nullable=True, unique=True)
    cards_synced = db.Column(db.Boolean, default=False)

    home_team = db.relationship("Team", foreign_keys=[home_team_id], back_populates="home_matches")
    away_team = db.relationship("Team", foreign_keys=[away_team_id], back_populates="away_matches")

    @property
    def played(self):
        return self.home_score is not None and self.away_score is not None

    @property
    def result_string(self):
        if not self.played:
            return "vs"
        s = f"{self.home_score} - {self.away_score}"
        if self.home_penalties is not None:
            s += f" (pens {self.home_penalties}-{self.away_penalties})"
        return s


class FunCategory(db.Model):
    __tablename__ = "fun_categories"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    emoji = db.Column(db.String(10), default="🏆")
    prize = db.Column(db.Float, default=10.0)
    calc_key = db.Column(db.String(50), nullable=True)  # None = manual
    sort_order = db.Column(db.Integer, default=0)

    winners = db.relationship("FunWinner", back_populates="category", cascade="all, delete-orphan")


class FunWinner(db.Model):
    __tablename__ = "fun_winners"
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey("fun_categories.id"), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=True)
    notes = db.Column(db.String(200), nullable=True)
    finalized = db.Column(db.Boolean, default=False)

    category = db.relationship("FunCategory", back_populates="winners")
    team = db.relationship("Team", back_populates="fun_wins")


class AppSettings(db.Model):
    __tablename__ = "app_settings"
    key = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.String(200), default="")


class Prize(db.Model):
    __tablename__ = "prizes"
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    paid_out = db.Column(db.Boolean, default=False)
    winner_id = db.Column(db.Integer, db.ForeignKey("participants.id"), nullable=True)

    winner = db.relationship("Participant")
