
from __future__ import annotations
import time
import threading
from collections import defaultdict, deque
from typing import Dict, Deque, Tuple

# Lock globale per proteggere le strutture dati condivise tra thread
# Necessario per evitare race conditions nei dati UDP e degli eventi
data_lock = threading.Lock()

def get_current_timestamp() -> float:
    """
    Restituisce il timestamp corrente in secondi dall'epoca Unix.
    Utilizzato per sincronizzare i dati temporali ricevuti via UDP.
    """
    return time.time()

# Strutture dati condivise per memorizzare lo stato dell'applicazione
# Contiene l'ultimo pacchetto ricevuto per ogni telecamera identificata da ID
latest_data_by_camera: Dict[str, dict] = {}
# Serie temporale dei dati per ogni telecamera: lista di tuple (timestamp, distanza, fps, conteggio persone)
# Utilizza deque con maxlen per limitare la memoria usata e mantenere solo dati recenti
time_series_by_camera: Dict[str, Deque[Tuple[float, float, float, float]]] = defaultdict(lambda: deque(maxlen=20000))
# Log degli eventi di allarme e notifiche varie, con dimensione massima per evitare uso eccessivo di memoria
event_log: Deque[dict] = deque(maxlen=100000)

# Stato di allarme per ogni telecamera, con informazioni su inizio allarme e ultimo cambiamento
alert_state_by_camera: Dict[str, dict] = defaultdict(lambda: {"in_alert": False, "t_start": None, "last_change": None})
# Offset per normalizzare timestamp relativi in assoluti per ogni telecamera
timestamp_offset_by_camera: Dict[str, float] = {}

def clear_all_data():
    """
    Pulisce tutti i dati di misurazione e stati.
    Chiamato all'avvio per garantire uno stato pulito.
    """
    global latest_data_by_camera, time_series_by_camera, event_log, alert_state_by_camera, timestamp_offset_by_camera
    latest_data_by_camera.clear()
    time_series_by_camera.clear()
    event_log.clear()
    alert_state_by_camera.clear()
    timestamp_offset_by_camera.clear()
