from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class Team(db.Model):
    __tablename__ = "teams"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    code = db.Column(db.String(3), nullable=False)
    group_name = db.Column(db.String(1), nullable=True)
    confederation = db.Column(db.String(20), nullable=True)
    eliminated = db.Column(db.Boolean, default=False)
    eliminated_stage = db.Column(db.String(50), nullable=True)

    assignments = db.relationship("Assignment", back_populates="team")
    home_matches = db.relationship("Match", foreign_keys="Match.home_team_id", back_populates="home_team")
    away_matches = db.relationship("Match", foreign_keys="Match.away_team_id", back_populates="away_team")

    @property
    def points(self):
        STAGE_POINTS = {
            "Group Stage": 0,
            "Round of 32": 2,
            "Round of 16": 4,
            "Quarter-final": 7,
            "Semi-final": 11,
            "Runner-up": 15,
            "Champion": 20,
        }
        total = 0
        for match in self.home_matches + self.away_matches:
            if match.home_score is None or match.away_score is None:
                continue
            if match.stage == "Group Stage":
                if match.home_team_id == self.id and match.home_score > match.away_score:
                    total += 1
                elif match.away_team_id == self.id and match.away_score > match.home_score:
                    total += 1
                elif match.home_score == match.away_score:
                    total += 0  # draws handled via penalty winner
                if match.penalty_winner_id == self.id:
                    total += 1
        if self.eliminated_stage:
            total += STAGE_POINTS.get(self.eliminated_stage, 0)
        elif not self.eliminated:
            # Still in — award points for furthest stage reached
            pass
        return total


class Participant(db.Model):
    __tablename__ = "participants"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    entry_fee_paid = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    assignments = db.relationship("Assignment", back_populates="participant")

    @property
    def total_points(self):
        return sum(a.team.points for a in self.assignments)

    @property
    def teams(self):
        return [a.team for a in self.assignments]


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


class Prize(db.Model):
    __tablename__ = "prizes"
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    paid_out = db.Column(db.Boolean, default=False)
    winner_id = db.Column(db.Integer, db.ForeignKey("participants.id"), nullable=True)

    winner = db.relationship("Participant")
