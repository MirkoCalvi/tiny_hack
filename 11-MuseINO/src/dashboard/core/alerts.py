                                    
from __future__ import annotations
import os
import sys

# Aggiunge il percorso per importare moduli locali
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core.state import alert_state_by_camera
from core.events import push_event

def process_alert(camera_id: str, distance_mm: float, timestamp: float, safe_distance_mm: int, hysteresis_mm: int, min_dwell_seconds: float):
    """
    Elabora la logica di allarme per una camera basata sulla distanza misurata.
    Utilizza isteresi per evitare oscillazioni rapide tra stati di allarme.
    Registra eventi di ingresso/uscita dall'allarme nel log.
    """
    alert_state = alert_state_by_camera[camera_id]
    previous_alert_state = alert_state["in_alert"]
    # Calcola le soglie con isteresi per stabilità
    lower_threshold, upper_threshold = safe_distance_mm - hysteresis_mm, safe_distance_mm + hysteresis_mm

    # Logica di isteresi: cambia stato solo se oltre le soglie
    if distance_mm < lower_threshold:
        new_alert_state = True
    elif distance_mm > upper_threshold:
        new_alert_state = False
    else:
        new_alert_state = previous_alert_state

    last_change = alert_state.get("last_change") or timestamp
    # Debounce: aspetta min_dwell_seconds prima di cambiare stato
    if new_alert_state != previous_alert_state:
        if (timestamp - last_change) >= min_dwell_seconds:
            alert_state["last_change"] = timestamp
        else:
            new_alert_state = previous_alert_state  # debounce

    # Gestisci transizioni di stato
    if new_alert_state and not previous_alert_state:
        # Ingresso in allarme
        alert_state["in_alert"] = True
        alert_state["t_start"] = timestamp
        push_event("ALERT_ENTER", camera_id, {"distance_mm": distance_mm, "safe_distance_mm": safe_distance_mm})
    elif (not new_alert_state) and previous_alert_state:
        # Uscita dall'allarme
        alert_state["in_alert"] = False
        dwell_time = timestamp - (alert_state["t_start"] or timestamp)
        push_event("ALERT_EXIT", camera_id, {"dwell_seconds": round(dwell_time, 2), "safe_distance_mm": safe_distance_mm})
