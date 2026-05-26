import random
from datetime import datetime, timedelta
from flask import Flask, render_template
from database import db
from models import Trip, Hazard
import drone

app = Flask(__name__)

# SQLite file will be created at the root
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///drone.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

drone_obj = None

# Create tables if they don't exist yet
with app.app_context():
    db.create_all()

# --- Routes ---

@app.route('/')
def index():
    return render_template('main.html')

@app.route('/drone/connection', methods=['GET'])
def connection():
    global drone_obj

    # Check for drone connection
    if drone_obj is None:
        drone_obj = drone.connect_drone()
        if drone_obj is None:
            print("Drone Connection Failed")
            return ('', 204)
    else:
        if not drone.check_drone_connection(drone_obj):
            print("Drone Disconnected")
            drone_obj = None
            return ('', 204)
        
    # Fetch drone stats    
    battery = int(drone.get_drone_battery(drone_obj))
    snr = drone.get_drone_SNR(drone_obj)
    temp = drone.get_drone_temp(drone_obj)

    return render_template('partials/drone_status.html', drone_battery=battery, drone_snr=snr, drone_temperature=temp)

# --- Trip Routes ---
def _trip_list_partial():
    trips = Trip.query.order_by(Trip.started_at.desc()).all()
    return render_template('partials/trip_list.html', trips=trips)


@app.route('/trips/list', methods=['GET'])
def trip_list():
    return _trip_list_partial()


@app.route('/recording', methods=['GET'])
def recording():
    return render_template('partials/new_trip.html')


@app.route('/trips/<int:trip_id>/select', methods=['GET'])
def select_trip(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    return render_template('partials/trip_detail.html', trip=trip)

@app.route('/trips', methods=['GET'])
def get_trips():
    trips = Trip.query.order_by(Trip.started_at.desc()).all()
    return {'trips': [{'id': t.id, 'started_at': str(t.started_at)} for t in trips]}

@app.route('/trips/<int:trip_id>/hazards', methods=['GET'])
def get_hazards(trip_id):
    hazards = Hazard.query.filter_by(trip_id=trip_id).all()
    return {'hazards': [{'id': h.id, 'type': h.type, 'lat': h.lat, 'lng': h.lng} for h in hazards]}

# --- Hazard Detail Route ---
@app.route('/hazards/<int:hazard_id>', methods=['GET'])
def hazard_detail(hazard_id):
    hazard = Hazard.query.get_or_404(hazard_id)
    return render_template('partials/hazard_detail.html', hazard=hazard)

# --- Settings Routes ---
@app.route('/settings/clear', methods=['POST'])
def settings_clear():
    db.drop_all()
    db.create_all()
    return render_template('partials/settings_clear.html')


_HAZARD_TYPES = ['pothole', 'crack', 'debris', 'flooding', 'obstruction', 'erosion']
_SEVERITIES   = ['low', 'medium', 'high']

@app.route('/settings/dummy-trip', methods=['POST'])
def settings_dummy_trip():
    drone_id   = f"Tello {random.randint(1000, 9999)}"
    started_at = datetime.now() - timedelta(hours=random.randint(1, 72))
    ended_at   = started_at + timedelta(minutes=random.randint(20, 60))

    trip = Trip(drone_id=drone_id, started_at=started_at, ended_at=ended_at)
    db.session.add(trip)
    db.session.flush()

    for _ in range(random.randint(2, 6)):
        db.session.add(Hazard(
            trip_id     = trip.id,
            lat         = random.uniform(-90, 90),
            lng         = random.uniform(-180, 180),
            detected_at = started_at + timedelta(seconds=random.randint(0, int((ended_at - started_at).total_seconds()))),
            type        = random.choice(_HAZARD_TYPES),
            severity    = random.choice(_SEVERITIES),
        ))

    db.session.commit()
    return _trip_list_partial()

# --- New Trip Route ---
@app.route('/trips/start', methods=['POST'])
def start_trip():
    drone_id = drone.get_drone_serial_number(drone_obj)
    started_at = datetime.now()

    drone.drone_start(drone_obj)

    return ""

if __name__ == '__main__':
    app.run(debug=True)