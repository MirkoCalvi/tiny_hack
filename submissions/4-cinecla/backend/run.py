"""
Entry point to run the Flask API server
"""
from app import app, socketio
import api.jobs
import api.nicla
import api.dashboard

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=3002, debug=True)

