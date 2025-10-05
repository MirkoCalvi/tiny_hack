from __future__ import annotations
import pandas as pd
import gradio as gr
import numpy as np
import datetime
import plotly.graph_objects as go

def create_empty_time_series_dataframe() -> "pd.DataFrame":
    """
    Crea e restituisce un DataFrame vuoto per rappresentare una serie temporale.
    Questo DataFrame viene utilizzato quando non ci sono dati disponibili da mostrare nel grafico.
    Le colonne includono: Time (timestamp), Distance (mm) (distanza in millimetri), color (colore per il grafico).
    """
    return pd.DataFrame({
        "Time": pd.to_datetime([], unit="s"),
        "Distance (mm)": [],
        "color": []
    })

def generate_fake_statistics():
    """
    Genera dati fittizi per le statistiche del quadro monitorato.
    Ritorna un dizionario con visite giornaliere e mensili e dati per i grafici.
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
    Crea un grafico a linee per le visite nel tempo utilizzando Plotly.
    """
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=y, mode='lines+markers', name='Visite'))
    fig.update_layout(
        title=title,
        xaxis_title="Tempo",
        yaxis_title="Visite",
        template="plotly_white",
        height=400
    )
    return fig

def create_interface_layout():
    """
    Crea e restituisce il layout completo dell'interfaccia utente utilizzando Gradio.
    Il layout è organizzato in schede (tabs) per mostrare il monitoraggio e le statistiche.
    """
    with gr.Tabs() as tabs:
        with gr.TabItem("Monitoraggio Attuale"):
            with gr.Row():
                with gr.Column(scale=2):
                    status_summary_markdown = gr.Markdown("⏳ Avvio in corso...")
                with gr.Column(scale=1):
                    camera_selection_dropdown = gr.Dropdown(
                        label="Seleziona Telecamera",
                        choices=[],
                        value=None
                    )
                    safe_distance_slider = gr.Slider(
                        minimum=0,
                        maximum=1000,
                        value=100,
                        step=10,
                        label="Distanza Sicura (mm)"
                    )
                    fomo_box = gr.Markdown("### 👁️‍🗨️ Nicla-02 FOMO\n_in attesa di linee dalla seriale…_")
                    with gr.Row():
                        pass

            current_status_data_table = gr.Dataframe(
                label="📊 Stato Attuale Telecamere",
                interactive=False
            )

            distance_over_time_plot = gr.Plot(
                value=None,
                label="Distanza (ToF) — Ultimi Minuti"
            )

            alarm_events_data_table = gr.Dataframe(
                headers=["tempo", "id_telecamera", "evento", "valore"],
                interactive=False
            )

            last_packet_debug_json = gr.JSON(label="Ultimo Pacchetto (Debug)")

        with gr.TabItem("Statistiche Quadro"):
            stats = generate_fake_statistics()

            visits_today_md = gr.Markdown(f"### Visite Oggi: {stats['visits_today']}")
            visits_month_md = gr.Markdown(f"### Visite Questo Mese: {stats['visits_month']}")

            visits_today_plot = gr.Plot(value=plot_visits_time_series(stats['hours'], stats['visits_per_hour'], "Visite per Ora (Oggi)"), label="Visite per Ora (Oggi)")
            visits_month_plot = gr.Plot(value=plot_visits_time_series(stats['days'], stats['visits_per_day'], "Visite per Giorno (Mese)"), label="Visite per Giorno (Mese)")

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
