from __future__ import annotations
import os
import sys
import threading
import gradio as gr

# Add the current path so we can import local modules
sys.path.insert(0, '.')

from core.config import load_configuration
from core.udp import udp_listener
from core.serial import serial_reader
from ui.components import create_interface_layout
from ui.update import snapshot_state
from core.state import clear_all_data

CUSTOM_CSS = """
.status-summary {
    display: flex;
    justify-content: center;
}

.status-summary .status-summary-content {
    width: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1.5rem;
}

.status-summary .status-item {
    max-width: 720px;
    width: 100%;
    padding: 1.5rem;
    border-radius: 1rem;
    background: var(--block-background-fill);
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.08);
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1rem;
}

.status-summary .status-camera {
    font-size: 1.6rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

.status-summary .status-metrics {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 1.25rem 2rem;
}

.status-summary .status-metric {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.25rem;
    min-width: 120px;
}

.status-summary .metric-label {
    font-size: 0.95rem;
    color: var(--body-text-color-subdued, #666);
    text-transform: uppercase;
    letter-spacing: 0.06em;
}

.status-summary .metric-value {
    font-size: 1.8rem;
    font-weight: 700;
    color: var(--body-text-color, #111);
}

.status-summary .metric-value.metric-highlight {
    font-size: 2.1rem;
}

.status-summary .metric-value.metric-badge {
    padding: 0.25rem 0.75rem;
    border-radius: 9999px;
    background: rgba(0, 0, 0, 0.08);
}

.status-summary .metric-value.zone-safe {
    background: rgba(46, 204, 113, 0.15);
    color: #1e8449;
}

.status-summary .metric-value.zone-alert {
    background: rgba(231, 76, 60, 0.2);
    color: #c0392b;
}

.status-summary .status-summary-content.empty {
    padding: 2rem;
    font-size: 1.3rem;
    text-align: center;
    opacity: 0.8;
}

.status-summary .status-summary-content.empty p {
    margin: 0;
}

.status-fomo .markdown-body {
    text-align: center;
}
"""

def main():
    """
    Main entry point for the MuseINO dashboard application.
    This function coordinates the entire startup sequence:
    - Load the configuration settings.
    - Reset any previous run data for a clean start.
    - Spawn a background thread to receive UDP data from the cameras.
    - Build the Gradio user interface.
    - Launch the web server that exposes the dashboard.
    """
    # Load settings from the configuration source
    configuration = load_configuration()

    # Clear all global data structures to avoid leftovers from previous runs
    clear_all_data()

    # Start a background thread that continuously listens for UDP packets from the cameras
    # The thread runs in parallel without blocking the user interface
    threading.Thread(
        target=udp_listener,
        kwargs={
            "udp_ip_address": configuration.udp_ip_address,
            "udp_port_number": configuration.udp_port_number,
            "safe_distance_mm": configuration.safe_distance_mm,
            "hysteresis_mm": configuration.hysteresis_mm,
            "min_dwell_seconds": configuration.min_dwell_seconds
        },
        daemon=True  # Thread closes automatically when the main program exits
    ).start()

    # Start a thread to read the Nicla-02 (FOMO) serial port
    threading.Thread(
        target=serial_reader,
        args=(configuration.nicla2_port, configuration.nicla2_baud, configuration.nicla2_cam_id),
        daemon=True
    ).start()

    # Build the full user interface using the Gradio framework
    with gr.Blocks(title="MuseINO Dashboard", fill_height=True, css=CUSTOM_CSS) as demo:
        # Main dashboard title
        gr.Markdown("# 🖼️ MuseINO — Nicla Vision Dashboard")

        # Create every UI component (buttons, charts, tables, etc.)
        interface_components = create_interface_layout()

        # Configure a timer that refreshes the interface every second
        # This keeps data live without manual refreshes
        timer = gr.Timer(1.0, active=True)
        timer.tick(
            fn=lambda selected_camera, safe_distance: snapshot_state(
                selected_camera,
                safe_distance,
                configuration.window_seconds,
                configuration.max_events_in_table,
                configuration.nicla2_cam_id
            ),
            inputs=[
                interface_components["camera_selection_dropdown"],
                interface_components["safe_distance_slider"]
            ],
            outputs=[
                interface_components["status_summary_markdown"],
                interface_components["current_status_data_table"],
                interface_components["distance_over_time_plot"],
                interface_components["alarm_events_data_table"],
                interface_components["last_packet_debug_json"],
                interface_components["camera_selection_dropdown"],
                interface_components["fomo_box"]
            ],
        )

    # Launch the Gradio web server to expose the dashboard in a browser
    demo.launch(
        server_name="0.0.0.0",  # Listen on every network interface
        server_port=int(os.getenv("PORT", "7860")),  # Default port 7860, override via environment variable
        allowed_paths=[configuration.export_directory],  # Allow file downloads from the export directory
    )

if __name__ == "__main__":
    main()
