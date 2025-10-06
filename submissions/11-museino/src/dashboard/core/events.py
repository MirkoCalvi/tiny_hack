
from __future__ import annotations
import os.path as op
import os
import sys
from datetime import datetime
import pandas as pd

# Add the project path so we can import local modules
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core.state import get_current_timestamp, event_log, data_lock

def push_event(event_type: str, camera_id: str, payload: dict):
    """
    Append an event to the shared event log.
    Used to record events such as alarm entries and exits.
    The payload stores extra data like distance or dwell time.
    """
    with data_lock:
        event_log.append({
            "time": datetime.fromtimestamp(get_current_timestamp()).isoformat(timespec="seconds"),
            "cam_id": camera_id,
            "event": event_type,
            "value": pd.io.json.dumps(payload, ensure_ascii=False),
        })



def to_events_dataframe(event_list: list[dict] | None = None) -> "pd.DataFrame":
    """
    Convert the event list into a pandas DataFrame for display.
    If event_list is None, read from the current event log.
    """
    import pandas as pd
    if event_list is None:
        with data_lock:
            event_list = list(event_log)
    if not event_list:
        return pd.DataFrame(columns=["time", "cam_id", "event", "value"])
    return pd.DataFrame(event_list).copy()


