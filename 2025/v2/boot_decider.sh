#!/usr/bin/env bash

if [[ $EUID -ne 0 ]]; then
  echo "[boot_decider] ERROR: must be run as root"
  exit 1
fi

# Allow NetworkManager to settle
sleep 20

STATUS=$(nmcli -t -f STATE,CONNECTIVITY general)
echo "[boot_decider] Network status: $STATUS"

if [[ "$STATUS" == "connected:full" ]]; then
    echo "[boot_decider] Internet available — starting ISS tracker"
    systemctl start iss_tracker.service
else
    echo "[boot_decider] No internet — starting setup AP and portal"

    nmcli radio wifi on

    systemctl start hostapd
    systemctl start dnsmasq

    ip addr add 192.168.4.1/24 dev wlan0 2>/dev/null || true

    cd /home/piess/PieSS/2025/v2
    source venv/bin/activate

	/home/piess/PieSS/2025/v2/venv/bin/python3 \
	  /home/piess/PieSS/2025/v2/wifi_portal.py \
	  > /var/log/piesS-portal.log 2>&1 &
fi
