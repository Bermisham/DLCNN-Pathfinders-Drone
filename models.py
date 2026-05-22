from database import db
from datetime import datetime

class Trip(db.Model):
    __tablename__ = 'trips'

    id         = db.Column(db.Integer, primary_key=True)
    started_at = db.Column(db.DateTime, default=datetime.now())
    ended_at   = db.Column(db.DateTime, nullable=True)
    drone_id   = db.Column(db.String, nullable=True)
    notes      = db.Column(db.Text, nullable=True)

    hazards    = db.relationship('Hazard', backref='trip', lazy=True)


class Hazard(db.Model):
    __tablename__ = 'hazards'

    id          = db.Column(db.Integer, primary_key=True)
    trip_id     = db.Column(db.Integer, db.ForeignKey('trips.id'), nullable=False)
    image_path  = db.Column(db.String, nullable=True)
    lat         = db.Column(db.Float, nullable=False)
    lng         = db.Column(db.Float, nullable=False)
    detected_at = db.Column(db.DateTime, default=datetime.now())
    type        = db.Column(db.String, nullable=False)
    severity    = db.Column(db.String, nullable=True)