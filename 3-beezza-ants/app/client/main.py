"""

"""


from nicegui import ui
import requests


SERVER_URL: str = "http://127.0.0.1:5000"


#   ---- Callbacks ----

def on_check_enabled(e, board_id) -> None:
    """Attempts to change the "enable" setting for the specified device"""
    try:
        r = requests.post(f"{SERVER_URL}/api/app/config", json={"board_id": board_id, "enable": e.sender.value}, timeout=10)
        r.raise_for_status()
        if not r.json()["status"]:
            e.sender.value = not e.sender.value
        return
    except Exception:
        print("except")
        e.sender.value = not e.sender.value
        return
    

#   ---- Home Page ----

@ui.page("/")
def home_page():
    """Displays two navigation buttons"""
    with ui.row().classes('w-full no-wrap'):
        with ui.column().classes("w-full").style("min-height: 100vh; justify-content: center; align-items: center; background-color: #FAF3E0;"):
            ui.label("🍕 BeezzaAnts").style("font-size: 48px; font-weight: bold; color: #E63946; margin-bottom: 20px;")
            ui.label("Smarter Pizza. Powered by Vision, Bugs, and Bots.").style("color: #2C2C2C; font-size: 18px; margin-bottom: 40px;")

            with ui.column().style("gap: 20px; justify-content: center; align-items: center;"):
                ui.button("Devices", on_click=lambda: ui.navigate.to("/devices")).style(
                    "background-color: #F1C40F; color: white; font-size: 20px; padding: 30px 50px; border-radius: 15px;"
                )
                ui.button("Latest Pizzas", on_click=lambda: ui.navigate.to("/pizzas")).style(
                    "background-color: #E63946; color: white; font-size: 20px; padding: 30px 50px; border-radius: 15px;"
                )


#   ---- Devices Page ----

@ui.page("/devices")
def devices_page():
    """Shows all the recorded devices and some statistics, like device ID and uptime"""
    ui.label("Connected Devices").style("font-size: 32px; font-weight: bold; color: #E63946; margin-bottom: 20px;")
    try:
        r = requests.get(f"{SERVER_URL}/api/app/dashboard", timeout=10)
        r.raise_for_status()
        boards = r.json()["boards"]
    except Exception:
        boards = []

    for b in boards:
        color = "#2ECC71" if b["status"] else "#E63946"
        with ui.card().props("outlined").style("margin-bottom: 10px;"):
            ui.label(f"Device ID: {b["serial"]}")
            ui.label(f"Server-side ID: {b["board_id"]}")
            ui.label(f"Last seen: {b["last_seen"]}")
            ui.label("Online" if b["status"] else "Offline").style(f"color: {color}; font-weight: bold; display: inline;")
            ui.label(f"Uptime: {b["uptime"]}")
            cb = ui.checkbox(text="Enabled", value=b["enable"] == 1)
            cb.on("click", lambda e, b_id=b["board_id"]: on_check_enabled(e, b_id))


#   ---- Latest Pizzas Page ----

@ui.page("/pizzas")
def pizzas_page():
    """Shows the last 5 received pizza images, the devices that sent them, and the time stamps"""
    ui.label("Latest pizzas").style("font-size: 32px; font-weight: bold; color: #E63946; margin-bottom: 20px;")
    try:
        r = requests.get(f"{SERVER_URL}/api/app/latest", timeout=10)
        r.raise_for_status()
        pizzas = r.json()["pizzas"]
    except Exception:
        pizzas = []
    for p in pizzas:
        with ui.card().props("outlined").style("margin-bottom: 10px;"):
            ui.label(f"Server-side device ID: {p["board_id"]}")
            ui.label(f"Timestamp: {p["timestamp"]}")
            ui.label(f"Pizza type: {p["pizza_type"]}")
            ui.label(f"Pizza status: {p["pizza_status"]}")
            # change to an actual representation of the image!!!
            ui.label(f"{p["image"]}")


#   ---- Run App ----

ui.run(title="BeezzaAnts Dashboard", port=30000)
