from __future__ import annotations
import os
import os.path as op
from dataclasses import dataclass

@dataclass
class Configuration:
    """
    Classe di configurazione per l'applicazione MuseINO Dashboard.
    Contiene tutti i parametri configurabili via variabili d'ambiente.
    """
    udp_ip_address: str = "0.0.0.0"  # Indirizzo IP per il listener UDP
    udp_port_number: int = 5005  # Porta UDP per ricevere dati dalle camere
    safe_distance_mm: int = 400  # Distanza di sicurezza in mm
    window_seconds: int = 300  # Finestra temporale per i grafici (2 minuti)
    max_data_points: int = 20000  # Massimo numero di punti dati per camera
    max_events_in_table: int = 0  # Max eventi nella tabella (0 = illimitato)
    hysteresis_mm: int = 200  # Isteresi per evitare oscillazioni di allarme
    min_dwell_seconds: float = 0.8  # Tempo minimo per cambio stato allarme
    is_demo_mode: bool = False  # Modalità demo (non utilizzata)
    export_directory: str = "./exports"  # Directory per esportare dati
    # Serial config for Nicla-02 (FOMO)
    nicla2_port: str = "/dev/cu.usbmodem11301"  # Porta seriale per Nicla-02
    nicla2_baud: int = 921600  # Baud rate per Nicla-02
    nicla2_cam_id: str = "nicla-02"  # ID camera per Nicla-02

def load_configuration() -> Configuration:
    """
    Carica la configurazione dai valori di default o dalle variabili d'ambiente.
    Crea la directory di esportazione se non esiste.
    """
    configuration = Configuration(
        udp_ip_address=os.getenv("MUSEINO_UDP_IP", "0.0.0.0"),
        udp_port_number=int(os.getenv("MUSEINO_UDP_PORT", "5005")),
        safe_distance_mm=int(os.getenv("MUSEINO_SAFE_MM", "400")),
        window_seconds=int(os.getenv("MUSEINO_WINDOW_SEC", "300")),
        max_data_points=int(os.getenv("MUSEINO_MAX_POINTS", "20000")),
        max_events_in_table=int(os.getenv("MUSEINO_MAX_EVENTS_IN_TABLE", "0") or "0"),
        hysteresis_mm=int(os.getenv("MUSEINO_HYST_MM", "200")),
        min_dwell_seconds=float(os.getenv("MUSEINO_MIN_DWELL", "0.8")),
        is_demo_mode=os.getenv("MUSEINO_DEMO", "0") == "1",
        export_directory=op.abspath(os.getenv("MUSEINO_EXPORT_DIR", "./exports")),
        nicla2_port=os.getenv("NICLA2_PORT", "/dev/cu.usbmodem11301"),
        nicla2_baud=int(os.getenv("NICLA2_BAUD", "921600")),
        nicla2_cam_id=os.getenv("NICLA2_CAM_ID", "nicla-02")
    )
    # Crea la directory di esportazione se non esiste
    os.makedirs(configuration.export_directory, exist_ok=True)
    return configuration
