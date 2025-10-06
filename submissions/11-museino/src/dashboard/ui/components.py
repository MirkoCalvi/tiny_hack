from __future__ import annotations
import pandas as pd
import gradio as gr
import numpy as np
import datetime
import plotly.graph_objects as go

def create_empty_time_series_dataframe() -> "pd.DataFrame":
    """
    Create and return an empty DataFrame that represents a time series.
    Used whenever there is no data to display on the chart.
    Columns include: Time (timestamp), Distance (mm), color (plot colour).
    """
    return pd.DataFrame({
        "Time": pd.to_datetime([], unit="s"),
        "Distance (mm)": [],
        "color": []
    })

def generate_fake_statistics():
    """
    Generate fake statistics for the monitored artwork.
    Return a dictionary with daily and monthly visit counts plus chart data.
    """
    # Fake counts
    visits_today = np.random.randint(50, 150)
    visits_month = np.random.randint(1000, 5000)

    # Generate fake time series data for today (hourly)
    hours = pd.date_range(start=datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0), periods=24, freq='h')
    visits_per_hour = np.random.poisson(lam=visits_today/24, size=24)

    # Generate fake time series data for month (daily)
    days = pd.date_range(end=datetime.datetime.now(), periods=30)
    visits_per_day = np.random.poisson(lam=visits_month/30, size=30)

    return {
        "visits_today": visits_today,
        "visits_month": visits_month,
        "hours": hours,
        "visits_per_hour": visits_per_hour,
        "days": days,
        "visits_per_day": visits_per_day
    }

def plot_visits_time_series(x, y, title):
    """
    Create a Plotly line chart that displays visits over time.
    """
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=y, mode='lines+markers', name='Visits'))
    fig.update_layout(
        title=title,
        xaxis_title="Time",
        yaxis_title="Visits",
        template="plotly_white",
        height=400
    )
    return fig

def create_interface_layout():
    """
    Build and return the complete Gradio user interface layout.
    Tabs organise the live monitoring view and the statistics view.
    """
    with gr.Tabs() as tabs:
        with gr.TabItem("Live Monitoring"):
            with gr.Row():
                with gr.Column(scale=2):
                    status_summary_markdown = gr.Markdown(
                        "<div class=\"status-summary-content empty\"><p>⏳ Starting up...</p></div>",
                        elem_classes=["status-summary"],
                    )
                with gr.Column(scale=1):
                    camera_selection_dropdown = gr.Dropdown(
                        label="Select Camera",
                        choices=[],
                        value=None
                    )
                    safe_distance_slider = gr.Slider(
                        minimum=0,
                        maximum=1000,
                        value=100,
                        step=10,
                        label="Safe Distance (mm)"
                    )
                    fomo_box = gr.Markdown(
                        "### 👁️‍🗨️ Nicla-02 FOMO\n_waiting for serial data..._",
                        elem_classes=["status-fomo"],
                    )
                    with gr.Row():
                        pass

            current_status_data_table = gr.Dataframe(
                label="📊 Current Camera Status",
                interactive=False
            )

            distance_over_time_plot = gr.Plot(
                value=None,
                label="Distance (ToF) — Last Few Minutes"
            )

            alarm_events_data_table = gr.Dataframe(
                headers=["time", "camera_id", "event", "value"],
                interactive=False
            )

            last_packet_debug_json = gr.JSON(label="Last Packet (Debug)")

        with gr.TabItem("Artwork Statistics"):
            stats = generate_fake_statistics()

            visits_today_md = gr.Markdown(f"### Visits Today: {stats['visits_today']}")
            visits_month_md = gr.Markdown(f"### Visits This Month: {stats['visits_month']}")

            visits_today_plot = gr.Plot(value=plot_visits_time_series(stats['hours'], stats['visits_per_hour'], "Visits per Hour (Today)"), label="Visits per Hour (Today)")
            visits_month_plot = gr.Plot(value=plot_visits_time_series(stats['days'], stats['visits_per_day'], "Visits per Day (Month)"), label="Visits per Day (Month)")

    return {
        "status_summary_markdown": status_summary_markdown,
        "camera_selection_dropdown": camera_selection_dropdown,
        "safe_distance_slider": safe_distance_slider,
        "fomo_box": fomo_box,
        "current_status_data_table": current_status_data_table,
        "distance_over_time_plot": distance_over_time_plot,
        "alarm_events_data_table": alarm_events_data_table,
        "last_packet_debug_json": last_packet_debug_json,
        "visits_today_md": visits_today_md,
        "visits_month_md": visits_month_md,
        "visits_today_plot": visits_today_plot,
        "visits_month_plot": visits_month_plot,
    }
