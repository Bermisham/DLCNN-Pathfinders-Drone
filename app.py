from flask import Flask, render_template, make_response
from database import db
from models import Trip, Hazard

app = Flask(__name__)

# SQLite file will be created at the root
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///drone.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Create tables if they don't exist yet
with app.app_context():
    db.create_all()

# --- Routes ---

@app.route('/')
def index():
    return render_template('main.html')



def _trip_list_partial():
    trips = Trip.query.order_by(Trip.started_at.desc()).all()
    return render_template('partials/trip_list.html', trips=trips)

@app.route('/trips/list', methods=['GET'])
def trip_list():
    return _trip_list_partial()

@app.route('/trips/new', methods=['POST'])
def new_trip():
    trip = Trip()
    db.session.add(trip)
    db.session.commit()
    return _trip_list_partial()

@app.route('/trips/<int:trip_id>/select', methods=['GET'])
def select_trip(trip_id):
    return make_response(f'Trip #{trip_id}')

@app.route('/trips', methods=['GET'])
def get_trips():
    trips = Trip.query.order_by(Trip.started_at.desc()).all()
    return {'trips': [{'id': t.id, 'started_at': str(t.started_at)} for t in trips]}

@app.route('/trips/<int:trip_id>/hazards', methods=['GET'])
def get_hazards(trip_id):
    hazards = Hazard.query.filter_by(trip_id=trip_id).all()
    return {'hazards': [{'id': h.id, 'type': h.type, 'lat': h.lat, 'lng': h.lng} for h in hazards]}

if __name__ == '__main__':
    app.run(debug=True)