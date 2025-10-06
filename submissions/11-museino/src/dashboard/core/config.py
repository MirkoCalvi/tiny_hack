from __future__ import annotations
import os
import os.path as op
from dataclasses import dataclass

@dataclass
class Configuration:
    """
    Configuration class for the MuseINO Dashboard application.
    Contains every parameter that can be configured via environment variables.
    """
    udp_ip_address: str = "0.0.0.0"  # IP address used by the UDP listener
    udp_port_number: int = 5005  # UDP port used to receive data from the cameras
    safe_distance_mm: int = 400  # Safe distance in millimetres
    window_seconds: int = 300  # Time window for the charts (2 minutes)
    max_data_points: int = 20000  # Maximum number of data points per camera
    max_events_in_table: int = 0  # Maximum events in the table (0 = unlimited)
    hysteresis_mm: int = 200  # Hysteresis used to avoid alarm oscillations
    min_dwell_seconds: float = 0.8  # Minimum dwell time before changing the alarm state
    is_demo_mode: bool = False  # Demo mode flag (currently unused)
    export_directory: str = "./exports"  # Directory used to export data
    # Serial config for Nicla-02 (FOMO)
    nicla2_port: str = "/dev/cu.usbmodem11301"  # Serial port used by Nicla-02
    nicla2_baud: int = 921600  # Baud rate for Nicla-02
    nicla2_cam_id: str = "nicla-02"  # Camera identifier for Nicla-02

def load_configuration() -> Configuration:
    """
    Load the configuration from defaults or environment variables.
    Ensure the export directory exists.
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
    # Create the export directory if it does not already exist
    os.makedirs(configuration.export_directory, exist_ok=True)
    return configuration
