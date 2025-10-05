
from __future__ import annotations
import os
import sys

# Aggiunge il percorso del progetto per importare moduli locali
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core.state import get_current_timestamp, timestamp_offset_by_camera

def normalize_timestamp(camera_id: str, raw_timestamp: float) -> float:
    """
    Normalizza vari formati di timestamp in secondi dall'epoca Unix.
    - Se è in millisecondi (>=1e12) -> divide per 1000
    - Se è 'relativo' (<1e9) -> ancora al tempo corrente usando un offset per telecamera
    Questo permette di gestire timestamp provenienti da diverse fonti (es. Arduino, sistemi embedded).
    """
    timestamp = float(raw_timestamp)
    # Controlla se il timestamp è in millisecondi (valori molto grandi)
    if timestamp >= 1_000_000_000_000:
        timestamp = timestamp / 1000.0
    # Se è relativo (piccolo), calcola l'offset per renderlo assoluto
    if timestamp < 1_000_000_000:
        offset = timestamp_offset_by_camera.get(camera_id)
        if offset is None:
            # Calcola l'offset come differenza tra ora corrente e timestamp relativo
            offset = get_current_timestamp() - timestamp
            timestamp_offset_by_camera[camera_id] = offset
        timestamp = timestamp + offset
    return timestamp
