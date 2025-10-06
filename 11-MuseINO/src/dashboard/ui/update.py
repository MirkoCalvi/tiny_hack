from __future__ import annotations
from datetime import datetime
import os.path as op
import os
import sys
import pandas as pd
import gradio as gr
import plotly.express as px
import logging

# Add the project path so we can import local modules
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.state import data_lock, latest_data_by_camera, time_series_by_camera, event_log, get_current_timestamp
from core.events import to_events_dataframe
from ui.components import create_empty_time_series_dataframe

logger = logging.getLogger(__name__)

def build_status_dataframe(cameras: list[str], safe_distance_mm: int) -> "pd.DataFrame":
    """
    Build a DataFrame with the current status of every camera.
    Include the latest data point for each camera plus the SAFE/ALERT zone.
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
                "count": people_count,
                "zone": zone,
            })
    if not status_rows:
        return pd.DataFrame(columns=["time","camera_id","mode","distance_mm","fps","count","zone"])
    status_df = pd.DataFrame(status_rows)
    return status_df.sort_values(["time"], kind="stable").reset_index(drop=True)

def _build_status_summary(cameras: list[str], safe_distance_mm: int) -> str:
    """
    Build a centred visual summary with classification, distance and count details.
    """

    def _metric_block(label: str, value: str, highlight: bool = True, extra_class: str = "") -> str:
        highlight_class = "metric-highlight" if highlight else ""
        return (
            "<div class=\"status-metric\">"
            f"<span class=\"metric-label\">{label}</span>"
            f"<span class=\"metric-value {highlight_class} {extra_class}\">{value}</span>"
            "</div>"
        )

    if not cameras:
        return (
            "<div class=\"status-summary-content empty\">"
            "<p>⏳ Waiting for UDP or serial packets...</p>"
            "</div>"
        )

    parts = ["<div class=\"status-summary-content\">"]
    for camera in cameras:
        last_data = latest_data_by_camera.get(camera, {})
        mode = last_data.get("mode", "tof")
        metrics_html: list[str] = []

        if mode == "fomo":
            lab = last_data.get("fomo_label", "?")
            prb = last_data.get("fomo_prob", 0.0)
            metrics_html.append(_metric_block("Classification", lab.upper(), extra_class="metric-badge"))
            metrics_html.append(_metric_block("Confidence", f"{prb:.2f}", highlight=False))
        else:
            distance = last_data.get("tof_mm", "N/A")
            fps = last_data.get("fps", "N/A")
            people = last_data.get("people", "N/A")
            zone = "SAFE" if (isinstance(distance, (int, float)) and distance >= safe_distance_mm) else "ALERT"
            zone_class = "zone-safe" if zone == "SAFE" else "zone-alert"
            metrics_html.append(_metric_block("Classification", zone, extra_class=f"metric-badge {zone_class}"))
            metrics_html.append(_metric_block("Distance", f"{distance} mm"))
            metrics_html.append(_metric_block("Count", str(people)))
            metrics_html.append(_metric_block("FPS", str(fps), highlight=False))

        metrics = "".join(metrics_html)
        parts.append(
            "<div class=\"status-item\">"
            f"<div class=\"status-camera\">{camera}</div>"
            f"<div class=\"status-metrics\">{metrics}</div>"
            "</div>"
        )

    parts.append("</div>")
    return "\n".join(parts)

def _build_fomo_box(nicla2_cam_id: str) -> str:
    """
    Build the markdown used for the Nicla-02 FOMO box.
    """
    latest_fomo = latest_data_by_camera.get(nicla2_cam_id, {})
    if latest_fomo.get("mode") == "fomo":
        lab = latest_fomo.get("fomo_label", "?")
        prb = latest_fomo.get("fomo_prob", 0.0)
        color = "🟢" if (lab.lower() == "person" and prb >= 0.70) else "🔴" if (lab.lower() == "not_person") else "🟡"
        fomo_md = f"### 👁️‍🗨️ Nicla-02 FOMO\n**{color} {lab}**  —  conf: **{prb:.2f}**"
    else:
        fomo_md = "### 👁️‍🗨️ Nicla-02 FOMO\n_waiting for serial data..._"
    return fomo_md

def _prepare_time_series_data(current_camera: str, safe_distance_mm: int, window_seconds: int) -> "pd.DataFrame":
    """
    Prepare the time-series data for the distance chart.
    Filter recent samples and colour points based on the SAFE/ALERT zone.
    """
    if current_camera and time_series_by_camera.get(current_camera):
        cutoff_time = get_current_timestamp() - window_seconds
        points = [point for point in time_series_by_camera[current_camera] if point[0] >= cutoff_time]
        if points:
            df = pd.DataFrame(points, columns=["timestamp", "distance_mm", "fps", "people_count"])
            df["Time"] = pd.to_datetime(df["timestamp"], unit="s")
            df.sort_values("Time", inplace=True)
            df["Distance (mm)"] = pd.to_numeric(df["distance_mm"], errors="coerce")
            # Colour the points: green for SAFE, red for ALERT
            df["color"] = df["Distance (mm)"].apply(lambda x: "green" if x >= safe_distance_mm else "red")
            return df[["Time", "Distance (mm)", "color"]].copy()
    return create_empty_time_series_dataframe()

def _create_distance_plot(distance_df: "pd.DataFrame", safe_distance_mm: int) -> "px.Figure":
    """
    Create the Plotly distance-over-time chart.
    Include SAFE/ALERT colours and a background rectangle.
    """
    if distance_df.empty:
        return None

    # Map colours for SAFE and ALERT
    color_discrete_map = {
        "SAFE": "#2ca02c",  # green for SAFE
        "ALERT": "#d62728"  # red for ALERT
    }
    # Convert colour names into chart labels
    distance_df["color"] = distance_df["color"].map({"green": "SAFE", "red": "ALERT"})

    # Compute margins for the background rectangle
    safe_vals = distance_df[distance_df["color"] == "SAFE"]["Distance (mm)"]
    alert_vals = distance_df[distance_df["color"] == "ALERT"]["Distance (mm)"]
    if not safe_vals.empty and not alert_vals.empty:
        safe_min = safe_vals.min()
        alert_max = alert_vals.max()
        margin = max((alert_max - safe_min) / 2, 10)  # minimum margin of 10
        lower_bound = safe_min - margin
        upper_bound = alert_max + margin
    else:
        lower_bound = safe_distance_mm - 10
        upper_bound = safe_distance_mm + 10

    # Create the coloured scatter plot
    lower_bound, upper_bound = sorted((lower_bound, upper_bound))
    fig = px.scatter(distance_df, x="Time", y="Distance (mm)", color="color", title="Distance (ToF) — Last Few Minutes",
                     color_discrete_map=color_discrete_map)
    fig.update_traces(showlegend=False)  # Remove duplicate legend entries

    # Add a light-green background rectangle
    fig.add_hrect(y0=lower_bound, y1=upper_bound, fillcolor="#98fb98", opacity=0.3, line_width=0)
    # Connect SAFE points with lines and plot ALERT points as markers
    safe_df = distance_df[distance_df["color"] == "SAFE"]
    alert_df = distance_df[distance_df["color"] == "ALERT"]
    fig.add_scatter(x=safe_df["Time"], y=safe_df["Distance (mm)"], mode="lines+markers", name="SAFE", line=dict(color=color_discrete_map["SAFE"]))
    fig.add_scatter(x=alert_df["Time"], y=alert_df["Distance (mm)"], mode="markers", name="ALERT", marker=dict(color=color_discrete_map["ALERT"]))
    return fig

def snapshot_state(selected_camera: str, safe_distance_mm: int, window_seconds: int, max_events_in_table: int, nicla2_cam_id: str = "nicla-02"):
    """
    Main function that updates the dashboard state.
    Coordinate data collection and prepare UI updates.
    Invoked every second by the Gradio timer for real-time refreshes.
    """
    with data_lock:
        cameras = sorted(latest_data_by_camera.keys())
        logger.debug(f"Available cameras: {cameras}")
        current_camera = selected_camera if (selected_camera and selected_camera in cameras) else (cameras[0] if cameras else None)
        logger.debug(f"Selected camera: {selected_camera}, Active camera used: {current_camera}")

        # Build the textual status summary
        summary = _build_status_summary(cameras, safe_distance_mm)

        # Prepare the camera dropdown update
        choices = cameras.copy()
        if selected_camera and selected_camera not in choices:
            logger.warning(f"Selected camera {selected_camera} not in the available choices, adding it.")
            choices.append(selected_camera)
        dropdown_update = gr.update(choices=choices, value=current_camera)

        # Build the camera status table
        status_df = build_status_dataframe(cameras, safe_distance_mm)

        # Prepare the data for the time-series chart
        distance_df = _prepare_time_series_data(current_camera, safe_distance_mm, window_seconds)

        # Prepare the alarm event table
        event_list = list(event_log)
        if max_events_in_table > 0:
            event_list = event_list[-max_events_in_table:]
        events_df = to_events_dataframe(event_list)

        # Fetch the last packet received for debugging
        last_debug = latest_data_by_camera.get(current_camera, {}) if current_camera else {}

        # Build the FOMO box content
        fomo_md = _build_fomo_box(nicla2_cam_id)

    # Create the Plotly figure using the prepared data
    fig = _create_distance_plot(distance_df, safe_distance_mm)

    # Return every update intended for the user interface
    return [summary, status_df, fig, events_df, last_debug, dropdown_update, fomo_md]

# def clear_events_handler():
#     """
#     Handle clearing the events.
#     Reset the events table, plot and dropdown.
#     """
#     with data_lock:
#         cleared_events_df = clear_events_dataframe()
#     empty_fig = None
#     empty_dropdown_update = gr.update(choices=[], value=None)
#     return [cleared_events_df, empty_fig, empty_dropdown_update]
