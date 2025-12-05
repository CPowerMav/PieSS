"""wifi_portal.py
Simple Flask portal for entering WiFi credentials.

Intended usage:
- Start this script while the Pi is running as a WiFi access point.
- Connect to the Pi's AP from a phone/laptop.
- Open http://raspberrypi/ (or http://<pi-ip>/) and enter SSID + password.
"""
import os
import subprocess

from flask import Flask, render_template, request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")

app = Flask(__name__, template_folder=TEMPLATE_DIR)


@app.route("/", methods=["GET"])
def wifi_form():
    """Render WiFi setup form."""
    return render_template("wifi_form.html")


@app.route("/connect", methods=["POST"])
def connect_wifi():
    """Connect to the provided SSID and password using nmcli."""
    ssid = request.form.get("ssid")
    password = request.form.get("password")

    if not ssid or not password:
        return "SSID or password missing"

    try:
        # This assumes NetworkManager is managing wlan0.
        result = subprocess.run(
            ["nmcli", "device", "wifi", "connect", ssid, "password", password],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return f"Connecting to {ssid}..."
        else:
            return (
                f"Failed to connect to {ssid}.<br>"
                f"nmcli error: {result.stderr or result.stdout}"
            )
    except Exception as exc:
        return f"Error running nmcli: {exc}"


if __name__ == "__main__":
    # Listen on all interfaces on port 80
    app.run(host="0.0.0.0", port=80)
