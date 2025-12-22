#!/usr/bin/env bash

if [[ $EUID -ne 0 ]]; then
  echo "[boot_decider] ERROR: must be run as root"
  exit 1
fi

# Give NetworkManager time to settle after boot
sleep 20

STATUS=$(nmcli -t -f STATE,CONNECTIVITY general)

echo "[boot_decider] Network status: $STATUS"

if [[ "$STATUS" == "connected:full" ]]; then
    echo "[boot_decider] Internet available — starting ISS tracker"
    systemctl start iss_tracker.service
else
    echo "[boot_decider] No internet — starting setup AP and portal"


    # Ensure Wi-Fi radio is on before starting AP
    nmcli radio wifi on

    # Bring up setup AP
    systemctl restart hostapd
    systemctl start dnsmasq

    # Assign static IP (safe if already set)
    ip addr add 192.168.4.1/24 dev wlan0 2>/dev/null || true

    # Start Wi-Fi portal
    cd /home/piess/PieSS/2025/v2
    source venv/bin/activate
    python3 wifi_portal.py
fi