from __future__ import annotations
import os
import sys
import threading
import gradio as gr

# Aggiunge il percorso corrente per importare moduli locali
sys.path.insert(0, '.')

from core.config import load_configuration
from core.udp import udp_listener
from core.serial import serial_reader
from ui.components import create_interface_layout
from ui.update import snapshot_state
from core.state import clear_all_data

def main():
    """
    Funzione principale dell'applicazione dashboard MuseINO.
    Questa funzione coordina l'avvio completo dell'applicazione:
    - Carica le impostazioni di configurazione.
    - Resetta tutti i dati precedenti per un avvio pulito.
    - Avvia un thread separato per ricevere dati UDP dalle telecamere.
    - Costruisce l'interfaccia utente con Gradio.
    - Avvia il server web per l'accesso alla dashboard.
    """
    # Carica le impostazioni dal file di configurazione
    configuration = load_configuration()

    # Resetta tutte le strutture dati globali per evitare residui da esecuzioni precedenti
    clear_all_data()

    # Avvia un thread in background per ascoltare continuamente i pacchetti UDP inviati dalle telecamere
    # Questo thread lavora in parallelo senza bloccare l'interfaccia utente
    threading.Thread(
        target=udp_listener,
        kwargs={
            "udp_ip_address": configuration.udp_ip_address,
            "udp_port_number": configuration.udp_port_number,
            "safe_distance_mm": configuration.safe_distance_mm,
            "hysteresis_mm": configuration.hysteresis_mm,
            "min_dwell_seconds": configuration.min_dwell_seconds
        },
        daemon=True  # Il thread si chiude automaticamente quando il programma principale termina
    ).start()

    # Avvia un thread per leggere la seriale Nicla-02 (FOMO)
    threading.Thread(
        target=serial_reader,
        args=(configuration.nicla2_port, configuration.nicla2_baud, configuration.nicla2_cam_id),
        daemon=True
    ).start()

    # Costruisce l'interfaccia utente completa utilizzando il framework Gradio
    with gr.Blocks(title="MuseINO Dashboard", fill_height=True) as demo:
        # Titolo principale della dashboard
        gr.Markdown("# 🖼️ MuseINO — Dashboard per Nicla Vision")

        # Crea tutti i componenti dell'interfaccia (pulsanti, grafici, tabelle, ecc.)
        interface_components = create_interface_layout()

        # Imposta un timer che aggiorna automaticamente l'interfaccia ogni secondo
        # Questo permette di vedere i dati in tempo reale senza bisogno di refresh manuali
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

    # Avvia il server web Gradio per rendere accessibile la dashboard via browser
    demo.launch(
        server_name="0.0.0.0",  # Ascolta su tutte le interfacce di rete
        server_port=int(os.getenv("PORT", "7860")),  # Porta predefinita 7860, modificabile con variabile d'ambiente
        allowed_paths=[configuration.export_directory],  # Permette il download di file dalla cartella di esportazione
    )

if __name__ == "__main__":
    main()
