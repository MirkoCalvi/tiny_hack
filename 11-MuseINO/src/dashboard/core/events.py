
from __future__ import annotations
import os.path as op
import os
import sys
from datetime import datetime
import pandas as pd

# Aggiunge il percorso per importare moduli locali
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core.state import get_current_timestamp, event_log, data_lock

def push_event(event_type: str, camera_id: str, payload: dict):
    """
    Aggiunge un evento al log degli eventi.
    Utilizzato per registrare eventi come ingressi/uscite da allarme.
    Il payload contiene dati aggiuntivi come distanza o tempo di dwell.
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
    Converte la lista degli eventi in un DataFrame pandas per la visualizzazione.
    Se event_list è None, usa il log corrente degli eventi.
    """
    import pandas as pd
    if event_list is None:
        with data_lock:
            event_list = list(event_log)
    if not event_list:
        return pd.DataFrame(columns=["time", "cam_id", "event", "value"])
    return pd.DataFrame(event_list).copy()


