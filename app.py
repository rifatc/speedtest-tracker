from flask import Flask, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import speedtest
import json
import os

app = Flask(__name__)

# Ensure the data directory exists
os.makedirs('data', exist_ok=True)

# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////app/data/speedtest.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class SpeedTest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    download = db.Column(db.Float, nullable=False)
    upload = db.Column(db.Float, nullable=False)
    ping = db.Column(db.Float, nullable=False)
    share_link = db.Column(db.String(255), nullable=True)

# Create database tables
with app.app_context():
    db.create_all()

def run_speed_test():
    st = speedtest.Speedtest(secure=True)
    st.get_best_server()
    
    download_speed = st.download() / 1_000_000  # Convert to Mbps
    upload_speed = st.upload() / 1_000_000      # Convert to Mbps
    ping = st.results.ping
    
    # Try to get share link, set to None if it fails
    try:
        share_link = st.results.share()
    except (TypeError, AttributeError):
        share_link = None
    
    # Save to database
    speed_test = SpeedTest(download=download_speed, upload=upload_speed, ping=ping, share_link=share_link)
    db.session.add(speed_test)
    db.session.commit()
    
    return {
        'download': download_speed,
        'upload': upload_speed,
        'ping': ping,
        'share_link': share_link
    }

def create_graph(data_type):
    results = SpeedTest.query.order_by(SpeedTest.timestamp.desc()).limit(50).all()
    results = results[::-1]  # Reverse to show oldest to newest
    
    timestamps = [result.timestamp.strftime('%Y-%m-%d %H:%M:%S') for result in results]
    values = [getattr(result, data_type) for result in results]
    
    return {
        'labels': timestamps,
        'values': values,
        'title': f'{data_type.capitalize()} Speed Over Time',
        'yAxisLabel': 'Speed (Mbps)' if data_type != 'ping' else 'Ping (ms)'
    }

@app.route('/')
def dashboard():
    last_test = SpeedTest.query.order_by(SpeedTest.timestamp.desc()).first()
    
    graphs = {
        'download': create_graph('download'),
        'upload': create_graph('upload'),
        'ping': create_graph('ping')
    }
    
    return render_template('dashboard.html', last_test=last_test, graphs=graphs)

@app.route('/history')
def history():
    tests = SpeedTest.query.order_by(SpeedTest.timestamp.desc()).all()
    return render_template('history.html', tests=tests)

@app.route('/run-test', methods=['POST'])
def test():
    try:
        results = run_speed_test()
        return jsonify({'success': True, 'data': results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)