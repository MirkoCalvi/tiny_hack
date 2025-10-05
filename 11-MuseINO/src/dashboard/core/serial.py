from __future__ import annotations
import re
import time
import threading
from typing import Optional

from .state import data_lock, latest_data_by_camera, event_log, get_current_timestamp

ZANT_RE = re.compile(r"label\s*=\s*([A-Za-z0-9_]+).*?prob\s*=\s*([0-9]*\.?[0-9]+)")

def _parse_zant_line(line: str) -> Optional[tuple[str, float]]:
    """
    Extract (label, prob) from a line such as:
    '[ZANT] PERSON top1: idx=1 label=not_person prob=0.926 time=1958.3 ms'
    """
    m = ZANT_RE.search(line)
    if not m:
        return None
    label = m.group(1).strip()
    try:
        prob = float(m.group(2))
    except Exception:
        return None
    return (label, prob)

def _push_event(ev_type: str, cam_id: str, payload: dict):
    """
    Append an event to the shared event log.
    """
    event_log.append({
        "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(get_current_timestamp())),
        "cam_id": cam_id,
        "event": ev_type,
        "value": str(payload)
    })

def serial_reader(port: str, baud: int, cam_id: str):
    """
    Read the Nicla FOMO serial port, update latest_data_by_camera[cam_id]
    with mode='fomo', fomo_label, fomo_prob and push a 'FOMO' event.
    """
    try:
        import serial  # pyserial
    except Exception as e:
        print(f"[SER {cam_id}] missing pyserial: pip install pyserial ({e})")
        return

    while True:
        try:
            print(f"[SER {cam_id}] Opening {port} @ {baud} ...")
            with serial.Serial(port, baud, timeout=1) as ser:
                # Clear serial buffers
                ser.reset_input_buffer()
                ser.reset_output_buffer()
                print(f"[SER {cam_id}] OK, listening.")
                # Iterate over lines
                for raw in ser:
                    try:
                        line = raw.decode("utf-8", errors="ignore").strip()
                    except Exception:
                        continue
                    if not line:
                        continue

                    # Try to parse a ZANT line
                    parsed = _parse_zant_line(line)
                    if not parsed:
                        continue
                    label, prob = parsed
                    ts = get_current_timestamp()
                    with data_lock:
                        latest_data_by_camera[cam_id] = {
                            "ts": ts,
                            "cam_id": cam_id,
                            "mode": "fomo",
                            "fomo_label": label,
                            "fomo_prob": prob
                        }
                        _push_event("FOMO", cam_id, {"label": label, "prob": prob})

        except Exception as e:
            print(f"[SER {cam_id}] serial error: {e}")
            time.sleep(2.0)  # retry
