from database import db
from datetime import datetime

class Trip(db.Model):
    __tablename__ = 'trips'

    id = db.Column(db.Integer, primary_key=True)
    started_at = db.Column(db.DateTime, default=datetime.now())
    ended_at = db.Column(db.DateTime, nullable=True)
    drone_id = db.Column(db.String, nullable=True)
    video_path = db.Column(db.String, nullable=True)

    hazards = db.relationship('Hazard', backref='trip', lazy=True)

    @property
    def duration_str(self):
        if self.ended_at is None:
            return '--:--'
        total = int((self.ended_at - self.started_at).total_seconds())
        h, rem = divmod(total, 3600)
        m, s = divmod(rem, 60)
        return f'{h:02d}:{m:02d}:{s:02d}'


class Hazard(db.Model):
    __tablename__ = 'hazards'

    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey('trips.id'), nullable=False)
    image_path = db.Column(db.String, nullable=True)
    x = db.Column(db.Float, nullable=False)
    y = db.Column(db.Float, nullable=False)
    detected_at = db.Column(db.DateTime, default=datetime.now())
    type = db.Column(db.String, nullable=False)
    confidence = db.Column(db.Float, nullable=False)