
from __future__ import annotations
import time
import threading
from collections import defaultdict, deque
from typing import Dict, Deque, Tuple

# Global lock used to protect shared data structures across threads
# Required to avoid race conditions for UDP data and events
data_lock = threading.Lock()

def get_current_timestamp() -> float:
    """
    Return the current Unix timestamp in seconds.
    Used to keep temporal data received over UDP aligned.
    """
    return time.time()

# Shared structures used to store application state
# Hold the latest packet received for each camera ID
latest_data_by_camera: Dict[str, dict] = {}
# Time series of data for each camera: list of tuples (timestamp, distance, fps, people count)
# Use a deque with maxlen to bound memory usage and retain only recent samples
time_series_by_camera: Dict[str, Deque[Tuple[float, float, float, float]]] = defaultdict(lambda: deque(maxlen=20000))
# Event log for alarms and other notifications, capped in size to limit memory usage
event_log: Deque[dict] = deque(maxlen=100000)

# Alarm state for each camera, tracking alert start time and last change
alert_state_by_camera: Dict[str, dict] = defaultdict(lambda: {"in_alert": False, "t_start": None, "last_change": None})
# Offset applied per camera to normalise relative timestamps into absolute ones
timestamp_offset_by_camera: Dict[str, float] = {}

def clear_all_data():
    """
    Clear every measurement and state structure.
    Called at startup to guarantee a clean slate.
    """
    global latest_data_by_camera, time_series_by_camera, event_log, alert_state_by_camera, timestamp_offset_by_camera
    latest_data_by_camera.clear()
    time_series_by_camera.clear()
    event_log.clear()
    alert_state_by_camera.clear()
    timestamp_offset_by_camera.clear()
