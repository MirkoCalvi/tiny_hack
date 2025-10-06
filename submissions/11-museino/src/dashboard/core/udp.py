from __future__ import annotations
import socket
import json
import sys
import os
from typing import Tuple

# Add the project path so we can import local modules
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core.state import data_lock, latest_data_by_camera, time_series_by_camera
from core.normalization import normalize_timestamp
from core.alerts import process_alert

def _ensure_message(message: dict, address: Tuple[str, int]) -> dict:
    """
    Ensure the received UDP message contains the fields needed for processing.
    Add a timestamp when missing, derive the camera ID from the sender address,
    convert legacy fields and set defaults for optional values.
    """
    message = dict(message)
    if "ts" not in message:
        import time
        message["ts"] = time.time()  # Add the current timestamp if missing
    if "cam_id" not in message:
        message["cam_id"] = f"{address[0]}:{address[1]}"  # Generate an ID based on IP:port
    if "tof_mm" not in message and "reading" in message:
        message["tof_mm"] = int(message["reading"])  # Convert legacy 'reading' into 'tof_mm'
    message.setdefault("fps", None)  # Default value for FPS
    message.setdefault("people", None)  # Default value for the people count
    message.setdefault("mode", "tof")  # Default mode
    return message

def _process_telemetry_message(message: dict, camera_id: str, timestamp: float, safe_distance_mm: int, hysteresis_mm: int, min_dwell_seconds: float):
    """
    Process a telemetry message received via UDP.
    Extract the distance, FPS and people count, update shared state and run alarm logic.
    """
    # Extract the main values from the message
    distance_mm = float(message.get("tof_mm")) if message.get("tof_mm") is not None else None
    frames_by_second = float(message.get("fps")) if message.get("fps") is not None else float("nan")
    people_count = float(message.get("people")) if message.get("people") is not None else None

    # Support the new Arduino format: use "count" when available
    if people_count is None:
        count = message.get("count")
        if count is not None:
            people_count = float(count)
        elif distance_mm is not None:
            # Fallback: assume 1 person if closer than the safe distance, otherwise 0
            people_count = 1.0 if distance_mm < safe_distance_mm else 0.0

    with data_lock:
        # Update the message with processed and normalised data
        message["ts"] = timestamp
        message["people"] = people_count
        message["fps"] = frames_by_second if frames_by_second == frames_by_second else None  # Convert NaN into None
        latest_data_by_camera[camera_id] = message

        if distance_mm is not None:
            # Append a point to the time series used for the chart
            time_series_by_camera[camera_id].append((
                timestamp, distance_mm,
                frames_by_second if frames_by_second == frames_by_second else float("nan"),
                people_count if people_count is not None else float("nan")
            ))
            # Run the alarm logic based on the measured distance
            process_alert(camera_id, distance_mm, timestamp, safe_distance_mm, hysteresis_mm, min_dwell_seconds)

def udp_listener(udp_ip_address: str, udp_port_number: int, safe_distance_mm: int, hysteresis_mm: int, min_dwell_seconds: float):
    """
    Continuously listen for UDP packets sent by the MuseINO cameras.
    For each packet, decode the JSON, normalise the data and update global state.
    Handle both telemetry messages and alarm events.
    """
    # Create and configure the UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((udp_ip_address, udp_port_number))
    print(f"[UDP] Listening on {udp_ip_address}:{udp_port_number}")

    while True:
        try:
            # Receive data from the socket (blocking)
            data, address = sock.recvfrom(8192)
            line = data.decode("utf-8", errors="ignore").strip()
            if not line:
                continue  # Skip empty packets

            # Decode the received JSON message
            message = json.loads(line)
            message = _ensure_message(message, address)

            camera_id = message["cam_id"]
            timestamp = normalize_timestamp(camera_id, float(message["ts"]))

            if "event" in message:
                # Event message (e.g. manual alarm) - store it in the event log
                with data_lock:
                    from core.state import event_log
                    event_log.append(message)
                continue  # Do not treat it as regular telemetry

            # Handle it as regular telemetry
            _process_telemetry_message(message, camera_id, timestamp, safe_distance_mm, hysteresis_mm, min_dwell_seconds)

        except json.JSONDecodeError:
            print("[UDP] Invalid JSON received")
        except Exception as e:
            print("[UDP] Error while processing:", e)
