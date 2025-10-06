from flask import Flask, request, jsonify, send_from_directory
from baremetal import feed, process_feed
from db import db, OrbitData
import threading 
import base64
import math
import json
import os

app = Flask(__name__)

db.connect()
db.create_tables([OrbitData])

### Example of a satellite object ###
EXAMPLE_SATELLITE = {
    "line1": "1    11U 59001A   22053.83197560  .00000847  00000-0  45179-3 0  9996",
    "line2": "2    11  32.8647 264.6509 1466352 126.0358 248.5175 11.85932318689790",
    "name": "Otto"
}


def receive_serial_data():
    """ Read serial data from the Nicla Vision, create an entry with the timestamp and the result (if present) """
    while True:
        process_feed(feed)

REACT_BUILD_DIR = 'dist' 

@app.route('/')
def serve_root():
    return send_from_directory(REACT_BUILD_DIR, 'index.html')

@app.route("/get_data", methods=["GET"])
def get_data():
    """ Backend route to get data from the database """
    if request.method == "GET":
        data = OrbitData.select().order_by(OrbitData.timestamp.desc()).limit(10)
        return jsonify([{ 
            "timestamp": math.floor(o.timestamp.timestamp() * 1000),
            "classification": json.loads(o.classification),
            "image": "data:image/png;base64," + base64.b64encode(o.image).decode('utf-8')
        } for o in data])
    
@app.route("/get_satellite", methods=["GET"])
def get_satellite():
    """ Backend route to get the description of the satellite objects """
    if request.method == "GET":
        return jsonify([EXAMPLE_SATELLITE])

@app.route('/<path:path>')
def serve_static_or_react_router(path):
    if os.path.exists(os.path.join(REACT_BUILD_DIR, path)):
        return send_from_directory(REACT_BUILD_DIR, path)
    else:
        return send_from_directory(REACT_BUILD_DIR, 'index.html')

if __name__ == "__main__":
    serial_thread = threading.Thread(target=receive_serial_data, daemon=True)
    serial_thread.start()
    app.run(debug=True, threaded=True)
