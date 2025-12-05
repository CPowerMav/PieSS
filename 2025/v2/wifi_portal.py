"""
wifi_portal.py
Flask portal for entering WiFi credentials.
Allows initial configuration if WiFi not connected.
"""
from flask import Flask, render_template, request
import os, subprocess

app = Flask(__name__)
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'templates')

@app.route('/', methods=['GET'])
def wifi_form():
    """Render WiFi setup form."""
    return render_template('wifi_form.html')

@app.route('/connect', methods=['POST'])
def connect_wifi():
    """
    Connect to the provided SSID and password using nmcli.
    """
    ssid = request.form.get('ssid')
    password = request.form.get('password')
    if ssid and password:
        subprocess.run(['nmcli', 'device', 'wifi', 'connect', ssid, 'password', password])
        return f"Connecting to {ssid}..."
    return "SSID or password missing"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
