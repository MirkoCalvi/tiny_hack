"""

"""


from flask import Flask, request, jsonify, send_from_directory
from datetime import datetime, timedelta
import os, sqlite3
import base64
from pathlib import Path
import uuid
from apscheduler.schedulers.background import BackgroundScheduler


app = Flask(__name__)
DB_FILENAME: str = "board_data.db"


#   --- database helper functions ----

def get_db():
    conn = sqlite3.connect(DB_FILENAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS boards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                board_id TEXT UNIQUE,
                serial TEXT,
                registered_at TEXT,
                last_seen TEXT,
                uptime TEXT
            );
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                board_id TEXT,
                timestamp TEXT,
                image TEXT,
                pizza_type TEXT,
                pizza_status TEXT
            );
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                board_id TEXT UNIQUE,
                enable INTEGER  
            );
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                board_id TEXT UNIQUE,
                status INTEGER  
            );
        """)
        db.commit()


init_db()


#   ---- utility functions ----

def now():
    return datetime.now().isoformat()


#   ---- Arduino API ----

@app.route("/api/board/register", methods=["POST"])
def register_board():
    """Boards register during setup, receiving a unique ID"""
    board_data = request.get_json()
    board_serial = board_data.get("serial")
    new_board_id = f"board_{uuid.uuid4().hex}"
    with get_db() as db:
        db.execute(
            "INSERT OR IGNORE INTO boards (board_id, serial, registered_at, last_seen, uptime) VALUES (?, ?, ?, ?, ?)",
            (new_board_id, board_serial, now(), now(), 0)
        )
        db.execute(
            "INSERT OR IGNORE INTO config (board_id, enable) VALUES (?, ?)",
            (new_board_id, 1)
        )
        db.execute(
            "INSERT OR IGNORE INTO status (board_id, status) VALUES (?, ?)",
            (new_board_id, 1)
        )
        db.commit()
    
    return jsonify({
        "board_id": new_board_id,
        "config": {"enable": True}
    })


@app.route("/api/board/config", methods=["GET"])
def get_board_config():
    """Boards call this during loop, to retrieve settings"""
    board_data = request.get_json()
    board_id = board_data.get("board_id")
    with get_db() as db:
        permission = db.execute("SELECT enable FROM config WHERE board_id=?", (board_id,)).fetchone()
        if not permission:
            return jsonify({"enable": False})
        db.execute(f"UPDATE boards SET last_seen=? WHERE board_id=?", (now(), board_id))
        db.commit()
    return jsonify({"enable": bool(permission[0])})


@app.route("/api/board/telemetry", methods=["POST"])
def send_telemetry():
    """Boards call this sending pictures and board data"""
    board_data = request.get_json()
    board_id = board_data.get("board_id")
    if not board_id:
        return jsonify({"status": 0})
    uptime = board_data.get("uptime")
    image = board_data.get("image")
    pizza_type = board_data.get("pizza_type")
    pizza_status = board_data.get("pizza_status")
    with get_db() as db:
        db.execute("""
            INSERT INTO telemetry (board_id, image, timestamp, pizza_type, pizza_status)
                VALUES (?, ?, ?, ?, ?)
        """, (board_id, image, now(), pizza_type, pizza_status))
        db.execute(f"UPDATE status SET status=? WHERE board_id=?", (now(), board_id))
        db.execute(f"UPDATE boards SET uptime=? WHERE board_id=?", (uptime, board_id))
        db.commit()
    return jsonify({"status": 1})


#   ---- Web app API ----

@app.route("/api/app/dashboard", methods=["GET"])
def get_dashboard():
    """App calls this to get general info about all devices"""
    out_list = []
    with get_db() as db:
        boards = db.execute("SELECT * FROM boards").fetchall()
        for b in boards:
            enable = db.execute(f"SELECT enable FROM config WHERE board_id=?", (b["board_id"], )).fetchone()
            if not enable:
                continue
            status = db.execute(f"SELECT status FROM status WHERE board_id=?", (b["board_id"], )).fetchone()
            if not status:
                continue
            out_list.append({
                "serial": b["serial"], "board_id": b["board_id"],
                "registered_at": b["registered_at"], "last_seen": b["last_seen"],
                "uptime": b["uptime"], "status": status[0], "enable": enable[0]
            })
    return jsonify({"boards": out_list})

@app.route("/api/app/config", methods=["POST"])
def set_board_config():
    """App calls this to set configuration of a specific board"""
    app_data = request.get_json()
    board_id = app_data.get("board_id")
    enable = app_data.get("enable")
    if board_id is None or enable is None:
        return jsonify({"status": False})
    with get_db() as db:
        db.execute("UPDATE config SET enable=? WHERE board_id=?", (enable, board_id))
        db.commit()
    return jsonify({"status": True})


@app.route("/api/app/latest", methods=["GET"])
def get_latest_updates():
    """App calls this to get the latest pizza images and the corresponding devices"""
    out_data = []
    with get_db() as db:
        last_rows = db.execute("SELECT * FROM telemetry ORDER BY id DESC LIMIT 5").fetchall()
        last_rows.reverse()
        for row in last_rows:
            out_data.append({
                "board_id": row[1],
                "timestamp": row[2],
                "image": row[3],
                "pizza_type": row[4],
                "pizza_status": row[5]
            })
    return jsonify({"pizzas": out_data})

#   ---- client timeout function ----

def check_timeout():
    cutoff = datetime.fromisoformat(now()) - timedelta(minutes=5)
    with get_db() as db:
        boards = db.execute("SELECT * FROM boards").fetchall()
        for b in boards:
            last_seen = datetime.fromisoformat(b["last_seen"])
            enable = db.execute(f"SELECT enable FROM config WHERE board_id=?", (b["board_id"], )).fetchone()
            if not enable:
                continue
            if last_seen < cutoff and enable[0] == 1:
                db.execute(f"UPDATE status SET status=0 WHERE board_id=?", (b["board_id"], ))
        db.commit()


scheduler = BackgroundScheduler()
job = scheduler.add_job(check_timeout, "interval", minutes=1)
scheduler.start()


if __name__ == "__main__":
    app.run(port=5000)
