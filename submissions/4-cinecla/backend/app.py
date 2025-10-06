"""
Flask application initialization and configuration
"""
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Initialize Flask app
app = Flask(__name__)
CORS(app, origins=['http://localhost:5173'])

# Initialize SocketIO for WebSocket
socketio = SocketIO(app, cors_allowed_origins='http://localhost:5173')


# All impressions
# in memory Python list :)
# we are storing device_id, emotion, timestamp and frame_data from the nicla.py endpoint
impressions = []

# Current session data
current_session = {
    'video_url': None,
    'start_time': None
}

# Nicla device identifiers
devices = ['1', '2']

# Utility functions

def get_timestamp_ms():
    """Get current timestamp in milliseconds"""
    return int(datetime.now().timestamp() * 1000)

