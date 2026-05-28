import random
from datetime import datetime, timedelta
from flask import Flask, render_template, Response, request, send_file
from database import db
from models import Trip, Hazard
import drone

app = Flask(__name__)

# SQLite file will be created at the root
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///drone.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

drone_obj = None
is_running = False

battery = None
snr = None
temp = None
status = "Not Connected"

# Create tables if they don't exist yet
with app.app_context():
    db.create_all()

# --- Routes ---

@app.route('/')
def index():
    return render_template('main.html')

@app.route('/drone/connection', methods=['GET'])
def connection():
    global battery, snr, temp, status, is_running, drone_obj

    if is_running:
        return render_template('partials/drone_status.html', drone_battery=battery, drone_snr=snr, drone_temperature=temp, drone_connection_status=status)

    # Check for drone connection
    if drone_obj is None:
        drone_obj = drone.connect_drone()
        if drone_obj is None:
            print("Drone Connection Failed")
            status = "Not Connected"
            return ('', 204)
    else:
        if not drone.check_drone_connection(drone_obj):
            print("Drone Disconnected")
            drone_obj = None
            status = "Not Connected"
            return ('', 204)
        
    # Fetch drone stats    
    battery = int(drone.get_drone_battery(drone_obj))
    snr = drone.get_drone_SNR(drone_obj)
    temp = drone.get_drone_temp(drone_obj)
    status = drone.get_drone_serial_number(drone_obj)

    return render_template('partials/drone_status.html', drone_battery=battery, drone_snr=snr, drone_temperature=temp, drone_connection_status=status)

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
    return {'hazards': [{'id': h.id, 'type': h.type, 'x': h.x, 'y': h.y} for h in hazards]}

# --- Hazard Detail Routes ---
@app.route('/hazards/<int:hazard_id>', methods=['GET'])
def hazard_detail(hazard_id):
    hazard = Hazard.query.get_or_404(hazard_id)
    return render_template('partials/hazard_detail.html', hazard=hazard)

@app.route('/hazards/<int:hazard_id>/image', methods=['GET'])
def hazard_image(hazard_id):
    hazard = Hazard.query.get_or_404(hazard_id)
    if not hazard.image_path:
        return ('', 404)
    return send_file(hazard.image_path, mimetype='image/jpeg')

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
            x           = round(random.uniform(0, 500), 1),
            y           = round(random.uniform(0, 500), 1),
            detected_at = started_at + timedelta(seconds=random.randint(0, int((ended_at - started_at).total_seconds()))),
            type        = random.choice(_HAZARD_TYPES),
            confidence  = round(random.uniform(0.5, 0.99), 2),
        ))

    db.session.commit()
    return _trip_list_partial()

# --- Trip Recording Routes ---
@app.route('/drone/feed')
def drone_feed():
    return Response(drone.generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/trips/start', methods=['POST'])
def start_trip():
    global drone_obj, is_running
    if is_running or drone_obj is None:
        return ('', 204)

    # Parse the waypoint list submitted by the new_trip form
    directions = request.form.getlist('direction')
    distances  = request.form.getlist('distance')
    if not directions:
        return ('', 204)

    path = [(d, int(dist)) for d, dist in zip(directions, distances) if dist]
    if not path:
        return ('', 204)

    drone_id = drone.get_drone_serial_number(drone_obj)
    trip = Trip(drone_id=drone_id, started_at=datetime.now())
    db.session.add(trip)
    db.session.flush()
    trip_id = trip.id
    db.session.commit()

    is_running = True

    def on_complete(detections: dict, video_path: str | None):
        """Called from the trip thread when the flight ends (natural or stopped)."""
        global is_running, drone_obj
        with app.app_context():
            t = db.session.get(Trip, trip_id)
            if t:
                t.ended_at   = datetime.now()
                t.video_path = video_path
                for det in detections.values():
                    db.session.add(Hazard(
                        trip_id     = trip_id,
                        type        = det['class'],
                        confidence  = det['confidence'],
                        x           = det['position']['x'],
                        y           = det['position']['y'],
                        detected_at = datetime.fromisoformat(det['time_detected']),
                        image_path  = det.get('image_path'),
                    ))
                db.session.commit()
        is_running = False
        drone_obj = None

    drone.start_stream(drone_obj, path, on_complete=on_complete)
    return ('', 204)


@app.route('/trips/stop', methods=['POST'])
def stop_trip():
    global drone_obj, is_running
    if is_running:
        drone.stop_stream(drone_obj)
    return _trip_list_partial()

if __name__ == '__main__':
    app.run(debug=True)