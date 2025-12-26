#!/usr/bin/env python3
"""
WiFi Configuration Portal for PieSS
Handles network scanning and connection with proper AP mode management
"""

import os
import subprocess
import time
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, send_file

APP_HOST = "0.0.0.0"
APP_PORT = 8080
WIFI_IFACE = "wlan0"
LOGO_PATH = "/home/piess/PieSS/2025/v2/templates/logo.png"

app = Flask(__name__, template_folder="templates")

# Cache for scan results
scan_cache = {
    'networks': [],
    'timestamp': None,
    'scanning': False
}


def run_cmd(cmd, timeout=30, check_sudo=False):
    """
    Run a command and return (returncode, stdout, stderr)
    If check_sudo=True, prepends 'sudo' to the command
    """
    if check_sudo:
        cmd = ["sudo"] + cmd
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return 1, "", "Command timed out"
    except Exception as e:
        return 1, "", str(e)


def stop_ap_mode():
    """Temporarily stop AP mode to allow WiFi scanning"""
    print("[wifi_portal] Stopping AP mode for scan...")
    run_cmd(["systemctl", "stop", "hostapd"], check_sudo=True)
    run_cmd(["systemctl", "stop", "dnsmasq"], check_sudo=True)
    time.sleep(2)


def start_ap_mode():
    """Restart AP mode"""
    print("[wifi_portal] Restarting AP mode...")
    
    # Make sure wlan0 still has the right IP
    run_cmd(["ip", "addr", "add", "192.168.4.1/24", "dev", "wlan0"], check_sudo=True)
    
    run_cmd(["systemctl", "start", "dnsmasq"], check_sudo=True)
    time.sleep(1)
    run_cmd(["systemctl", "start", "hostapd"], check_sudo=True)
    time.sleep(3)
    print("[wifi_portal] AP mode restarted")


def scan_networks_background():
    """
    Scan for WiFi networks in background. Updates the cache.
    This is designed to be called and return immediately, doing work in background.
    """
    global scan_cache
    
    if scan_cache['scanning']:
        print("[wifi_portal] Scan already in progress, skipping")
        return
    
    scan_cache['scanning'] = True
    
    # Stop AP mode temporarily
    stop_ap_mode()
    
    try:
        # Request fresh scan
        print("[wifi_portal] Running nmcli scan...")
        run_cmd(["nmcli", "dev", "wifi", "rescan"], timeout=20, check_sudo=True)
        time.sleep(3)
        
        # Get network list
        rc, out, err = run_cmd([
            "nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY", 
            "dev", "wifi", "list"
        ], check_sudo=True)
        
        if rc != 0:
            print(f"[wifi_portal] Scan failed: {err or out}")
            scan_cache['networks'] = []
        else:
            networks = []
            seen_ssids = set()
            
            for line in out.splitlines():
                parts = line.split(":")
                if len(parts) < 4:
                    continue
                
                in_use = parts[0].strip() == "*"
                ssid = parts[1].strip()
                signal = parts[2].strip()
                security = parts[3].strip()
                
                # Skip empty SSIDs and duplicates
                if not ssid or ssid in seen_ssids:
                    continue
                
                seen_ssids.add(ssid)
                
                try:
                    signal_int = int(signal) if signal.isdigit() else 0
                except:
                    signal_int = 0
                
                networks.append({
                    "ssid": ssid,
                    "signal": signal_int,
                    "security": security if security else "Open",
                    "in_use": in_use
                })
            
            # Sort by signal strength
            networks.sort(key=lambda n: (-n["signal"], n["ssid"].lower()))
            scan_cache['networks'] = networks
            scan_cache['timestamp'] = datetime.now()
            print(f"[wifi_portal] Scan complete, found {len(networks)} networks")
        
    except Exception as e:
        print(f"[wifi_portal] Scan error: {e}")
        scan_cache['networks'] = []
    finally:
        # Always restart AP mode after scan
        start_ap_mode()
        scan_cache['scanning'] = False


def connect_to_network(ssid, password):
    """
    Connect to a WiFi network and shut down AP mode if successful.
    Returns (success: bool, message: str)
    """
    if not ssid:
        return False, "SSID is required"
    
    # Stop AP mode before attempting connection
    stop_ap_mode()
    
    # Build connection command
    cmd = ["nmcli", "dev", "wifi", "connect", ssid, "ifname", WIFI_IFACE]
    if password:
        cmd.extend(["password", password])
    
    print(f"[wifi_portal] Attempting to connect to '{ssid}'...")
    rc, out, err = run_cmd(cmd, timeout=45, check_sudo=True)
    
    # Give NetworkManager time to connect
    time.sleep(5)
    
    # Check if actually connected
    rc2, out2, _ = run_cmd([
        "nmcli", "-t", "-f", "DEVICE,STATE", "dev", "status"
    ], check_sudo=True)
    
    connected = False
    for line in out2.splitlines():
        if ":" in line:
            dev, state = line.split(":", 1)
            if dev == WIFI_IFACE and state == "connected":
                connected = True
                break
    
    if connected:
        print(f"[wifi_portal] Successfully connected to '{ssid}'")
        # Keep AP mode off - we're now a client
        return True, f"Successfully connected to {ssid}"
    else:
        print(f"[wifi_portal] Failed to connect to '{ssid}': {err or out}")
        # Restart AP since connection failed
        start_ap_mode()
        error_msg = err or out or "Connection failed"
        return False, f"Failed to connect: {error_msg}"


@app.route("/")
def index():
    """Main portal page - shows cached scan results if available"""
    global scan_cache
    
    networks = scan_cache.get('networks', [])
    scan_time = scan_cache.get('timestamp')
    
    scan_error = None
    if scan_time:
        age = (datetime.now() - scan_time).total_seconds()
        if age > 300:  # Older than 5 minutes
            scan_error = f"Scan results are {int(age/60)} minutes old. Press Refresh for current networks."
    
    return render_template(
        "wifi_portal.html",
        networks=networks,
        scan_error=scan_error
    )


@app.route("/scan")
def scan():
    """Trigger a background scan and return current cached results"""
    global scan_cache
    
    # Trigger scan in background (doesn't block)
    import threading
    scan_thread = threading.Thread(target=scan_networks_background)
    scan_thread.daemon = True
    scan_thread.start()
    
    # Return immediately with message
    return jsonify({
        "ok": True,
        "scanning": True,
        "message": "Scan started. AP will restart. Please reconnect and reload the page in 10 seconds."
    })


@app.route("/results")
def results():
    """Get current scan results from cache"""
    global scan_cache
    return jsonify({
        "ok": True,
        "networks": scan_cache.get('networks', []),
        "scanning": scan_cache.get('scanning', False),
        "timestamp": scan_cache.get('timestamp').isoformat() if scan_cache.get('timestamp') else None
    })


@app.route("/connect", methods=["POST"])
def connect():
    """Handle connection request"""
    ssid = request.form.get("ssid", "").strip()
    password = request.form.get("password", "").strip()
    
    success, message = connect_to_network(ssid, password)
    
    # Get current network status
    rc, out, _ = run_cmd([
        "nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "dev", "status"
    ], check_sudo=True)
    
    status = out if rc == 0 else "Unable to retrieve status"
    
    return render_template(
        "wifi_result.html",
        ok=success,
        message=message,
        status=status
    )


@app.route("/logo.png")
def logo():
    """Serve the logo image"""
    if os.path.exists(LOGO_PATH):
        return send_file(LOGO_PATH, mimetype="image/png")
    return "Logo not found", 404


if __name__ == "__main__":
    print(f"[wifi_portal] Starting on {APP_HOST}:{APP_PORT}")
    print("[wifi_portal] Performing initial network scan...")
    
    # Do an initial scan on startup
    scan_networks_background()
    
    print("[wifi_portal] Ready to accept connections")
    app.run(host=APP_HOST, port=APP_PORT, debug=False)
