from __future__ import annotations
from datetime import datetime
import os.path as op
import os
import sys
import pandas as pd
import gradio as gr
import plotly.express as px
import logging

# Aggiunge il percorso per importare moduli locali
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.state import data_lock, latest_data_by_camera, time_series_by_camera, event_log, get_current_timestamp
from core.events import to_events_dataframe
from ui.components import create_empty_time_series_dataframe

logger = logging.getLogger(__name__)

def build_status_dataframe(cameras: list[str], safe_distance_mm: int) -> "pd.DataFrame":
    """
    Costruisce un DataFrame con lo stato attuale di tutte le telecamere.
    Include l'ultimo punto dati per ogni telecamera con zona SAFE/ALERT.
    """
    status_rows = []
    for camera in cameras:
        points = time_series_by_camera.get(camera, [])
        for point in points:
            timestamp, distance_mm, fps, people_count = point
            iso_timestamp = datetime.fromtimestamp(timestamp).isoformat(timespec="seconds")
            mode = latest_data_by_camera.get(camera, {}).get("mode", "")
            zone = "SAFE" if (isinstance(distance_mm, (int, float)) and distance_mm >= safe_distance_mm) else "ALERT"
            status_rows.append({
                "time": iso_timestamp,
                "camera_id": camera,
                "mode": mode,
                "distance_mm": distance_mm,
                "fps": fps,
                "conteggio": people_count,
                "zone": zone,
            })
    if not status_rows:
        return pd.DataFrame(columns=["time","camera_id","mode","distance_mm","fps","conteggio","zone"])
    status_df = pd.DataFrame(status_rows)
    return status_df.sort_values(["time"], kind="stable").reset_index(drop=True)

def _build_status_summary(cameras: list[str], safe_distance_mm: int) -> str:
    """
    Costruisce un riepilogo testuale dello stato delle telecamere.
    Include distanza, FPS, conteggio persone e zona per ogni telecamera.
    """
    if not cameras:
        return "⏳ In attesa di pacchetti UDP o Seriale..."
    parts = []
    for camera in cameras:
        last_data = latest_data_by_camera.get(camera, {})
        mode = last_data.get("mode", "tof")
        if mode == "fomo":
            lab = last_data.get("fomo_label", "?")
            prb = last_data.get("fomo_prob", 0.0)
            parts.append(f"- **{camera}** · FOMO: **{lab}** ({prb:.2f})")
        else:
            distance = last_data.get("tof_mm", "N/A")
            fps = last_data.get("fps", "N/A")
            people = last_data.get("people", "N/A")
            zone = "SAFE" if (isinstance(distance, (int,float)) and distance >= safe_distance_mm) else "ALERT"
            parts.append(f"- **{camera}** · Distanza: **{distance} mm** · FPS: **{fps}** · Conteggio: **{people}** · {zone}")
    return "### 📡 Flussi Attivi\n" + "\n".join(parts)

def _build_fomo_box(nicla2_cam_id: str) -> str:
    """
    Costruisce il markdown per il box FOMO di Nicla-02.
    """
    latest_fomo = latest_data_by_camera.get(nicla2_cam_id, {})
    if latest_fomo.get("mode") == "fomo":
        lab = latest_fomo.get("fomo_label", "?")
        prb = latest_fomo.get("fomo_prob", 0.0)
        color = "🟢" if (lab.lower() == "person" and prb >= 0.70) else "🔴" if (lab.lower() == "not_person") else "🟡"
        fomo_md = f"### 👁️‍🗨️ Nicla-02 FOMO\n**{color} {lab}**  —  conf: **{prb:.2f}**"
    else:
        fomo_md = "### 👁️‍🗨️ Nicla-02 FOMO\n_in attesa di linee dalla seriale…_"
    return fomo_md

def _prepare_time_series_data(current_camera: str, safe_distance_mm: int, window_seconds: int) -> "pd.DataFrame":
    """
    Prepara i dati per la serie temporale del grafico di distanza.
    Filtra i dati recenti, colora i punti in base alla zona SAFE/ALERT.
    """
    if current_camera and time_series_by_camera.get(current_camera):
        cutoff_time = get_current_timestamp() - window_seconds
        points = [point for point in time_series_by_camera[current_camera] if point[0] >= cutoff_time]
        if points:
            df = pd.DataFrame(points, columns=["timestamp", "distance_mm", "fps", "people_count"])
            df["Time"] = pd.to_datetime(df["timestamp"], unit="s")
            df.sort_values("Time", inplace=True)
            df["Distance (mm)"] = pd.to_numeric(df["distance_mm"], errors="coerce")
            # Colora i punti: verde per SAFE, rosso per ALERT
            df["color"] = df["Distance (mm)"].apply(lambda x: "green" if x >= safe_distance_mm else "red")
            return df[["Time", "Distance (mm)", "color"]].copy()
    return create_empty_time_series_dataframe()

def _create_distance_plot(distance_df: "pd.DataFrame", safe_distance_mm: int) -> "px.Figure":
    """
    Crea il grafico Plotly per la distanza nel tempo.
    Include colori per SAFE/ALERT e rettangolo di sfondo.
    """
    if distance_df.empty:
        return None

    # Mappa colori per SAFE e ALERT
    color_discrete_map = {
        "SAFE": "#2ca02c",  # verde per SAFE
        "ALERT": "#d62728"  # rosso per ALERT
    }
    # Converte i colori in etichette per il grafico
    distance_df["color"] = distance_df["color"].map({"green": "SAFE", "red": "ALERT"})

    # Calcola i margini per il rettangolo di sfondo
    safe_vals = distance_df[distance_df["color"] == "SAFE"]["Distance (mm)"]
    alert_vals = distance_df[distance_df["color"] == "ALERT"]["Distance (mm)"]
    if not safe_vals.empty and not alert_vals.empty:
        safe_min = safe_vals.min()
        alert_max = alert_vals.max()
        margin = max((alert_max - safe_min) / 2, 10)  # margine minimo di 10
        lower_bound = safe_min - margin
        upper_bound = alert_max + margin
    else:
        lower_bound = safe_distance_mm - 10
        upper_bound = safe_distance_mm + 10

    # Crea il grafico scatter con colori
    lower_bound, upper_bound = sorted((lower_bound, upper_bound))
    fig = px.scatter(distance_df, x="Time", y="Distance (mm)", color="color", title="Distanza (ToF) — Ultimi Minuti",
                     color_discrete_map=color_discrete_map)
    fig.update_traces(showlegend=False)  # Rimuove legenda duplicata

    # Aggiunge rettangolo di sfondo verde chiaro
    fig.add_hrect(y0=lower_bound, y1=upper_bound, fillcolor="#98fb98", opacity=0.3, line_width=0)
    # Connette i punti SAFE con linee, ALERT solo marker
    safe_df = distance_df[distance_df["color"] == "SAFE"]
    alert_df = distance_df[distance_df["color"] == "ALERT"]
    fig.add_scatter(x=safe_df["Time"], y=safe_df["Distance (mm)"], mode="lines+markers", name="SAFE", line=dict(color=color_discrete_map["SAFE"]))
    fig.add_scatter(x=alert_df["Time"], y=alert_df["Distance (mm)"], mode="markers", name="ALERT", marker=dict(color=color_discrete_map["ALERT"]))
    return fig

def snapshot_state(selected_camera: str, safe_distance_mm: int, window_seconds: int, max_events_in_table: int, nicla2_cam_id: str = "nicla-02"):
    """
    Funzione principale per aggiornare lo stato della dashboard.
    Coordina la raccolta dei dati e la preparazione degli aggiornamenti per l'interfaccia.
    Chiamata ogni secondo dal timer Gradio per aggiornamenti in tempo reale.
    """
    with data_lock:
        cameras = sorted(latest_data_by_camera.keys())
        logger.debug(f"Telecamere disponibili: {cameras}")
        current_camera = selected_camera if (selected_camera and selected_camera in cameras) else (cameras[0] if cameras else None)
        logger.debug(f"Telecamera selezionata: {selected_camera}, Telecamera corrente usata: {current_camera}")

        # Costruisci il riepilogo testuale dello stato
        summary = _build_status_summary(cameras, safe_distance_mm)

        # Prepara l'aggiornamento del dropdown delle telecamere
        choices = cameras.copy()
        if selected_camera and selected_camera not in choices:
            logger.warning(f"Telecamera selezionata {selected_camera} non nelle scelte, aggiungendola.")
            choices.append(selected_camera)
        dropdown_update = gr.update(choices=choices, value=current_camera)

        # Costruisci la tabella di stato delle telecamere
        status_df = build_status_dataframe(cameras, safe_distance_mm)

        # Prepara i dati per il grafico della serie temporale
        distance_df = _prepare_time_series_data(current_camera, safe_distance_mm, window_seconds)

        # Prepara la tabella degli eventi di allarme
        event_list = list(event_log)
        if max_events_in_table > 0:
            event_list = event_list[-max_events_in_table:]
        events_df = to_events_dataframe(event_list)

        # Ottieni l'ultimo pacchetto ricevuto per il debug
        last_debug = latest_data_by_camera.get(current_camera, {}) if current_camera else {}

        # Costruisci il box FOMO
        fomo_md = _build_fomo_box(nicla2_cam_id)

    # Crea il grafico Plotly basato sui dati preparati
    fig = _create_distance_plot(distance_df, safe_distance_mm)

    # Restituisce tutti gli aggiornamenti per l'interfaccia utente
    return [summary, status_df, fig, events_df, last_debug, dropdown_update, fomo_md]

# def clear_events_handler():
#     """
#     Gestisce la cancellazione degli eventi.
#     Resetta la tabella eventi, il grafico e il dropdown.
#     """
#     with data_lock:
#         cleared_events_df = clear_events_dataframe()
#     empty_fig = None
#     empty_dropdown_update = gr.update(choices=[], value=None)
#     return [cleared_events_df, empty_fig, empty_dropdown_update]
