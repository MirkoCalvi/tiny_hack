
from __future__ import annotations
import os
import sys

# Add the project path so we can import local modules
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core.state import get_current_timestamp, timestamp_offset_by_camera

def normalize_timestamp(camera_id: str, raw_timestamp: float) -> float:
    """
    Normalise different timestamp formats into Unix seconds.
    - If it is in milliseconds (>=1e12) -> divide by 1000
    - If it is 'relative' (<1e9) -> anchor it to now using a per-camera offset
    This lets us handle timestamps produced by different sources (e.g. Arduino, embedded systems).
    """
    timestamp = float(raw_timestamp)
    # Check whether the timestamp is expressed in milliseconds (very large values)
    if timestamp >= 1_000_000_000_000:
        timestamp = timestamp / 1000.0
    # For relative (small) timestamps, compute the offset to make it absolute
    if timestamp < 1_000_000_000:
        offset = timestamp_offset_by_camera.get(camera_id)
        if offset is None:
            # Compute the offset as the difference between now and the relative timestamp
            offset = get_current_timestamp() - timestamp
            timestamp_offset_by_camera[camera_id] = offset
        timestamp = timestamp + offset
    return timestamp
