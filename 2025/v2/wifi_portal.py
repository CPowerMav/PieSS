#!/usr/bin/env python3
import os
import re
import subprocess
import time
from flask import Flask, render_template, request, jsonify, send_file

APP_HOST = "0.0.0.0"
APP_PORT = 8080

# Your logo location (as you confirmed)
LOGO_PATH = "/home/piess/PieSS/2025/v2/templates/logo.png"

# Prefer wlan0 for Wi-Fi actions
WIFI_IFACE = "wlan0"

app = Flask(__name__, template_folder="templates")


def run(cmd: list[str], timeout: int = 15) -> tuple[int, str, str]:
    """Run a command and return (returncode, stdout, stderr)."""
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def wifi_scan() -> list[dict]:
    """
    Scan for nearby Wi-Fi networks using nmcli.
    Returns a list of dicts: {ssid, signal, security, in_use}
    """
    # Force refresh scan
    run(["nmcli", "dev", "wifi", "rescan"], timeout=20)

    # -t = terse, ':' separated
    # Fields: IN-USE, SSID, SIGNAL, SECURITY
    rc, out, err = run(["nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY", "dev", "wifi", "list"])
    if rc != 0:
        raise RuntimeError(f"nmcli wifi list failed: {err or out}")

    networks = []
    seen = set()

    for line in out.splitlines():
        # Format: "*:MySSID:78:WPA2" or ":Other:42:WPA2"
        parts = line.split(":")
        if len(parts) < 4:
            continue

        in_use = parts[0].strip() == "*"
        ssid = parts[1].strip()
        signal = parts[2].strip()
        security = parts[3].strip()

        # Skip empty SSIDs (hidden networks) in dropdown; user can type manually.
        if not ssid:
            continue

        # Deduplicate by SSID (keep strongest signal)
        key = ssid
        try:
            sig_i = int(signal) if signal.isdigit() else 0
        except Exception:
            sig_i = 0

        if key in seen:
            # Update strongest signal if needed
            for n in networks:
                if n["ssid"] == ssid and sig_i > n["signal"]:
                    n["signal"] = sig_i
                    n["security"] = security or n["security"]
                    n["in_use"] = n["in_use"] or in_use
            continue

        seen.add(key)
        networks.append({
            "ssid": ssid,
            "signal": sig_i,
            "security": security if security else "—",
            "in_use": in_use,
        })

    # Sort: currently-connected first, then by signal desc
    networks.sort(key=lambda n: (not n["in_use"], -n["signal"], n["ssid"].lower()))
    return networks


def nmcli_connect(ssid: str, password: str | None) -> tuple[bool, str]:
    """
    Connect to Wi-Fi using NetworkManager.
    Returns (success, message).
    """
    ssid = (ssid or "").strip()
    password = (password or "").strip()

    if not ssid:
        return False, "SSID is required."

    # If password is empty, try open network connect
    cmd = ["nmcli", "dev", "wifi", "connect", ssid, "ifname", WIFI_IFACE]
    if password:
        cmd += ["password", password]

    rc, out, err = run(cmd, timeout=45)
    if rc != 0:
        msg = err or out or "Unknown nmcli error."
        return False, msg

    return True, out or "Connected."


@app.route("/")
def index():
    try:
        networks = wifi_scan()
        scan_error = None
    except Exception as exc:
        networks = []
        scan_error = str(exc)

    return render_template("wifi_portal.html", networks=networks, scan_error=scan_error)


@app.route("/scan")
def scan():
    try:
        networks = wifi_scan()
        return jsonify({"ok": True, "networks": networks})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/connect", methods=["POST"])
def connect():
    ssid = request.form.get("ssid", "")
    password = request.form.get("password", "")

    ok, msg = nmcli_connect(ssid, password)

    # Give NetworkManager a moment, then show what it's doing
    time.sleep(2)
    rc, out, err = run(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "dev", "status"])
    status = out if rc == 0 else (err or out)

    if ok:
        return render_template("wifi_result.html", ok=True, message=msg, status=status)
    else:
        return render_template("wifi_result.html", ok=False, message=msg, status=status)


@app.route("/logo.png")
def logo():
    if os.path.exists(LOGO_PATH):
        return send_file(LOGO_PATH, mimetype="image/png")
    return ("Logo not found", 404)


if __name__ == "__main__":
    # Note: This is Phase 2 (Ethernet testing). AP mode comes later.
    app.run(host=APP_HOST, port=APP_PORT, debug=False)
