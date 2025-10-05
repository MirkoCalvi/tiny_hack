from __future__ import annotations
import socket
import json
import sys
import os
from typing import Tuple

# Aggiunge il percorso per importare moduli locali
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core.state import data_lock, latest_data_by_camera, time_series_by_camera
from core.normalization import normalize_timestamp
from core.alerts import process_alert

def _ensure_message(message: dict, address: Tuple[str, int]) -> dict:
    """
    Assicura che il messaggio UDP ricevuto abbia tutti i campi necessari per l'elaborazione.
    Aggiunge timestamp se mancante, genera ID telecamera basato sull'indirizzo IP del mittente,
    converte campi legacy e imposta valori predefiniti per campi opzionali.
    """
    message = dict(message)
    if "ts" not in message:
        import time
        message["ts"] = time.time()  # Aggiunge timestamp corrente se non presente
    if "cam_id" not in message:
        message["cam_id"] = f"{address[0]}:{address[1]}"  # Genera ID basato su IP:porta
    if "tof_mm" not in message and "reading" in message:
        message["tof_mm"] = int(message["reading"])  # Converte campo legacy 'reading' in 'tof_mm'
    message.setdefault("fps", None)  # Valore predefinito per FPS
    message.setdefault("people", None)  # Valore predefinito per conteggio persone
    message.setdefault("mode", "tof")  # Modalità predefinita
    return message

def _process_telemetry_message(message: dict, camera_id: str, timestamp: float, safe_distance_mm: int, hysteresis_mm: int, min_dwell_seconds: float):
    """
    Elabora un messaggio di telemetria ricevuto via UDP.
    Estrae distanza, FPS e conteggio persone, aggiorna strutture dati e gestisce allarmi.
    """
    # Estrae i valori principali dal messaggio
    distance_mm = float(message.get("tof_mm")) if message.get("tof_mm") is not None else None
    frames_by_second = float(message.get("fps")) if message.get("fps") is not None else float("nan")
    people_count = float(message.get("people")) if message.get("people") is not None else None

    # Supporto per nuovo formato Arduino: usa "count" se presente
    if people_count is None:
        count = message.get("count")
        if count is not None:
            people_count = float(count)
        elif distance_mm is not None:
            # Fallback: 1 persona se distanza < sicura, altrimenti 0
            people_count = 1.0 if distance_mm < safe_distance_mm else 0.0

    with data_lock:
        # Aggiorna il messaggio con dati elaborati e normalizzati
        message["ts"] = timestamp
        message["people"] = people_count
        message["fps"] = frames_by_second if frames_by_second == frames_by_second else None  # Converte NaN in None
        latest_data_by_camera[camera_id] = message

        if distance_mm is not None:
            # Aggiungi il punto alla serie temporale per il grafico
            time_series_by_camera[camera_id].append((
                timestamp, distance_mm,
                frames_by_second if frames_by_second == frames_by_second else float("nan"),
                people_count if people_count is not None else float("nan")
            ))
            # Elabora la logica di allarme basata sulla distanza
            process_alert(camera_id, distance_mm, timestamp, safe_distance_mm, hysteresis_mm, min_dwell_seconds)

def udp_listener(udp_ip_address: str, udp_port_number: int, safe_distance_mm: int, hysteresis_mm: int, min_dwell_seconds: float):
    """
    Ascolta continuamente pacchetti UDP inviati dalle telecamere MuseINO.
    Per ogni pacchetto ricevuto, decodifica il JSON, normalizza i dati e aggiorna lo stato globale.
    Gestisce sia messaggi di telemetria che eventi di allarme.
    """
    # Crea e configura il socket UDP
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((udp_ip_address, udp_port_number))
    print(f"[UDP] In ascolto su {udp_ip_address}:{udp_port_number}")

    while True:
        try:
            # Riceve dati dal socket (bloccante)
            data, address = sock.recvfrom(8192)
            line = data.decode("utf-8", errors="ignore").strip()
            if not line:
                continue  # Salta pacchetti vuoti

            # Decodifica il messaggio JSON ricevuto
            message = json.loads(line)
            message = _ensure_message(message, address)

            camera_id = message["cam_id"]
            timestamp = normalize_timestamp(camera_id, float(message["ts"]))

            if "event" in message:
                # Messaggio di evento (es. allarme manuale) - salva nel log eventi
                with data_lock:
                    from core.state import event_log
                    event_log.append(message)
                continue  # Non elaborare come telemetria regolare

            # Elabora come messaggio di telemetria regolare
            _process_telemetry_message(message, camera_id, timestamp, safe_distance_mm, hysteresis_mm, min_dwell_seconds)

        except json.JSONDecodeError:
            print("[UDP] JSON non valido ricevuto")
        except Exception as e:
            print("[UDP] Errore durante l'elaborazione:", e)
