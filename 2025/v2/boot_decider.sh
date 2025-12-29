#!/usr/bin/env bash
# PieSS Boot Mode Decider
# Determines whether to start in normal mode (ISS tracker) or setup mode (WiFi portal)

set -e

if [[ $EUID -ne 0 ]]; then
  echo "[boot_decider] ERROR: must be run as root"
  exit 1
fi

echo "[boot_decider] Starting boot decision process..."

# LED GPIO pins
LED_30M_PIN=22  # Red LED
LED_W_PIN=12    # West LED (for AP mode indicator)

# Function to control GPIO
gpio_export() {
    local pin=$1
    if [ ! -d /sys/class/gpio/gpio$pin ]; then
        echo $pin > /sys/class/gpio/export 2>/dev/null || true
        sleep 0.1
    fi
    echo out > /sys/class/gpio/gpio$pin/direction 2>/dev/null || true
}

gpio_set() {
    local pin=$1
    local value=$2
    echo $value > /sys/class/gpio/gpio$pin/value 2>/dev/null || true
}

gpio_cleanup() {
    local pin=$1
    gpio_set $pin 0
    echo $pin > /sys/class/gpio/unexport 2>/dev/null || true
}

# Give NetworkManager time to initialize and attempt connections
echo "[boot_decider] Waiting for NetworkManager to settle (20s)..."
sleep 20

# Check network connectivity
STATUS=$(nmcli -t -f STATE,CONNECTIVITY general)
echo "[boot_decider] Network status: $STATUS"

# Parse the status
STATE=$(echo "$STATUS" | cut -d: -f1)
CONNECTIVITY=$(echo "$STATUS" | cut -d: -f2)

if [[ "$CONNECTIVITY" == "full" || "$CONNECTIVITY" == "limited" ]]; then
    echo "[boot_decider] Internet available - starting ISS tracker"
    
    # Ensure AP services are stopped
    systemctl stop hostapd 2>/dev/null || true
    systemctl stop dnsmasq 2>/dev/null || true
    systemctl stop wifi_portal 2>/dev/null || true
    
    # Make sure AP mode indicator LED is off
    gpio_export $LED_W_PIN
    gpio_cleanup $LED_W_PIN
    
    # Start ISS tracker
    systemctl start iss_tracker.service
    
else
    echo "[boot_decider] No internet - starting WiFi configuration portal"
    
    # Ensure ISS tracker is stopped
    systemctl stop iss_tracker 2>/dev/null || true
    
    # Enable WiFi radio
    nmcli radio wifi on
    
    # Configure wlan0 for AP mode - MUST happen before starting services
    echo "[boot_decider] Configuring wlan0 interface..."
    ip link set wlan0 down 2>/dev/null || true
    ip addr flush dev wlan0 2>/dev/null || true
    ip addr add 192.168.4.1/24 dev wlan0
    ip link set wlan0 up
    
    # Verify IP is set
    sleep 1
    WLAN0_IP=$(ip -4 addr show wlan0 | grep -oP '(?<=inet\s)\d+(\.\d+){3}')
    echo "[boot_decider] wlan0 IP address: $WLAN0_IP"
    
    if [[ "$WLAN0_IP" != "192.168.4.1" ]]; then
        echo "[boot_decider] WARNING: wlan0 IP not set correctly!"
    fi
    
    # Start dnsmasq first (needs IP to be set)
    echo "[boot_decider] Starting dnsmasq..."
    systemctl start dnsmasq
    sleep 2
    
    # Then start hostapd
    echo "[boot_decider] Starting hostapd..."
    systemctl start hostapd
    sleep 2
    
    # Finally start web portal
    echo "[boot_decider] Starting wifi_portal..."
    systemctl start wifi_portal
    
    echo "[boot_decider] WiFi portal started at http://192.168.4.1:8080"
    
    # Start AP mode indicator LED (blinking red West LED)
    echo "[boot_decider] Starting AP mode LED indicator..."
    gpio_export $LED_30M_PIN
    gpio_export $LED_W_PIN
    
    # Create LED blink script in background
    (
        while true; do
            # Check if we're still in AP mode (hostapd running)
            if ! systemctl is-active --quiet hostapd; then
                # AP mode ended, turn off LED and exit
                gpio_cleanup $LED_30M_PIN
                gpio_cleanup $LED_W_PIN
                exit 0
            fi
            
            # Blink pattern: Red LED on West position
            # 0.5 seconds on, 0.5 seconds off = urgent indication
            gpio_set $LED_30M_PIN 1  # Red LED on
            gpio_set $LED_W_PIN 0
            sleep 0.5
            
            gpio_set $LED_30M_PIN 0  # Red LED off
            sleep 0.5
        done
    ) &
    
    # Store the background process PID
    LED_BLINK_PID=$!
    echo $LED_BLINK_PID > /tmp/piess_ap_led.pid
    echo "[boot_decider] AP mode LED indicator started (PID: $LED_BLINK_PID)"
fi

echo "[boot_decider] Boot decision complete"
