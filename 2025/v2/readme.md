# PieSS - Portable ISS Flag Tracker

A Raspberry Pi-based device that automatically tracks the International Space Station and raises a flag when it's visible overhead at night.

![PieSS Logo](templates/logo.png)

## Overview

PieSS is a fully autonomous ISS tracking device that:
- Automatically detects its location via IP geolocation
- Calculates when the ISS will be visible in the night sky
- Provides progressive LED countdown alerts (30, 10, 5 minutes)
- Raises a flag via servo motor when the ISS passes overhead
- Shows directional LEDs indicating where to look in the sky
- Features a portable WiFi configuration portal for easy setup anywhere

## Features

### Automatic ISS Tracking
- Downloads and caches Two-Line Element (TLE) orbital data
- Calculates visible passes based on location, time of day, and elevation
- Filters for night-time passes only (between sunset and sunrise)
- Minimum 15 degrees elevation for optimal viewing

### Visual Alerts
- **30-10 minutes**: Red LED with progressively faster blinking (4s -> 3s -> 2s -> 1s)
- **10-5 minutes**: Yellow LED with progressively faster blinking (3s -> 2s -> 1s)
- **5-0 minutes**: Green LED with progressively faster blinking (2s -> 1s -> 0.5s)
- **During pass**: Directional LEDs (N/E/S/W) track the ISS across the sky
- **Flag raising**: Servo motor raises flag at pass start, lowers after completion

### LED Status Indicators
- **AP Mode (no internet)**: Red 30-minute alert LED blinks (0.5s on/off) - indicates WiFi setup needed
- **Scanning WiFi**: Directional LEDs animate in circular pattern (Green North -> Red East -> Yellow South -> Red West) - indicates network scan in progress
- **Normal Operation**: Countdown and directional LEDs only

### Portable WiFi Configuration
- Automatically creates WiFi access point when no internet is available
- Web-based configuration portal at http://192.168.4.1:8080
- Scan and connect to any WiFi network
- Plug-and-play operation - works anywhere with WiFi

### Hardware Self-Test
- Automatic LED and servo testing on startup
- Verifies all connections are working correctly

## Hardware Requirements

### Core Components
- Raspberry Pi 3 Model B (or newer)
- MicroSD card (8GB minimum)
- 5V power supply

### Electronic Components
- 1x Servo motor (for flag mechanism)
- 7x LEDs with appropriate resistors (220 Ohm recommended):
  - 1x Red LED (30-minute alert)
  - 1x Yellow LED (10-minute alert)
  - 1x Green LED (5-minute alert)
  - 1x Green LED (North direction)
  - 1x Red LED (East direction)
  - 1x Yellow LED (South direction)
  - 1x Red LED (West direction)
- Breadboard and jumper wires

### GPIO Pin Assignments
| Component | Color | GPIO Pin | Physical Pin |
|-----------|-------|----------|--------------|
| Servo Motor | N/A | GPIO 16 | Pin 36 |
| 30-min Alert LED | Red | GPIO 22 | Pin 15 |
| 10-min Alert LED | Yellow | GPIO 27 | Pin 13 |
| 5-min Alert LED | Green | GPIO 17 | Pin 11 |
| North Direction LED | Green | GPIO 5 | Pin 29 |
| East Direction LED | Red | GPIO 6 | Pin 31 |
| South Direction LED | Yellow | GPIO 13 | Pin 33 |
| West Direction LED | Red | GPIO 12 | Pin 32 |

## Software Requirements

- Raspberry Pi OS (Bookworm/Trixie or newer)
- Python 3.9+
- Internet connection for initial setup

## Quick Start

### Automated Installation (Recommended)

```bash
# 1. Flash Raspberry Pi OS Lite to SD card
#    Use Raspberry Pi Imager, enable SSH, set username to 'piess'

# 2. Boot Pi and SSH in
# Option 1: Using hostname (if mDNS/Bonjour is working)
ssh piess@piess.local

# Option 2: Using IP address (find IP from your router)
ssh piess@192.168.1.XXX
# Replace XXX with actual IP address shown in your router's DHCP client list

# 3. Clone repository
git clone https://github.com/CPowerMav/PieSS.git
cd PieSS/2025/v2

# 4. Run automated installer
chmod +x piess_installer.sh
sudo ./piess_installer.sh

# 5. Reboot when prompted
sudo reboot
```

The installer handles everything: dependencies, services, configuration, and permissions.

### Manual Installation

For manual installation, follow the detailed step-by-step instructions in `documentation/PieSS_Full_Documentation.md`

### First Boot
- **With WiFi configured**: System auto-detects location and starts tracking ISS
- **Without WiFi**: 
  - Red 30-minute alert LED blinks (indicates AP mode)
  - Connect to "PieSS-Setup" (password: christmas)
  - Navigate to http://192.168.4.1:8080
  - Select WiFi network and enter password
  - PieSS connects and begins ISS tracking

## Usage

### Normal Operation
Once configured, PieSS operates completely autonomously:
1. Detects location automatically
2. Downloads ISS orbital data
3. Calculates next visible pass
4. Provides countdown alerts via LEDs
5. Raises flag when ISS is overhead
6. Shows directional LEDs to indicate where to look

### WiFi Configuration Mode
If PieSS cannot connect to a known WiFi network:
1. **Red 30-minute alert LED blinks** (indicates AP mode - needs configuration)
2. Creates access point "PieSS-Setup"
3. Connect with password: `christmas`
4. Open browser to http://192.168.4.1:8080
5. Click "Refresh list" to scan networks
   - **Circular LED animation** (Green North -> Red East -> Yellow South -> Red West) indicates scanning in progress
   - Wait 10 seconds for scan to complete
   - Reconnect to PieSS-Setup if needed
   - Reload page to see network list
6. Select network and enter password
7. PieSS connects and LED indicator stops
8. System resumes ISS tracking

### Hardware Test
To verify all connections:
```bash
cd ~/PieSS/2025/v2
source venv/bin/activate
sudo systemctl stop iss_tracker
python3 hardware_test.py
```

### Debug ISS Passes
To see all calculated passes:
```bash
cd ~/PieSS/2025/v2
source venv/bin/activate
python3 check_passes.py
```

## Project Structure

```
PieSS/2025/v2/
+-- iss_tracker.py              # Main ISS tracking application
+-- wifi_portal.py              # WiFi configuration web server
+-- boot_decider.sh             # Boot mode decision script
+-- hardware_test.py            # Hardware connection test utility
+-- check_passes.py             # Debug utility for pass calculation
+-- piess_installer.sh          # Automated installation script
+-- requirements.txt            # Python dependencies
+-- README.md                   # This file
+-- conf/
|   +-- hostapd.conf            # WiFi AP configuration
|   +-- dnsmasq.conf            # DHCP server configuration
|   +-- sudoers_config.sh       # Sudo permissions helper
+-- services/
|   +-- boot_decider.service    # Boot orchestrator service
|   +-- iss_tracker.service     # ISS tracker daemon
|   +-- wifi_portal.service     # WiFi portal daemon
|   +-- pigpiod.service         # GPIO daemon service
+-- templates/
|   +-- wifi_portal.html        # WiFi configuration page
|   +-- wifi_result.html        # Connection result page
|   +-- logo.png                # PieSS logo
+-- documentation/
    +-- PieSS_Full_Documentation.md
    +-- PieSS_Full_Documentation.pdf
```

## System Services

PieSS uses several systemd services:
- `boot_decider.service` - Determines whether to start ISS tracker or WiFi portal
- `iss_tracker.service` - Main ISS tracking application
- `wifi_portal.service` - WiFi configuration web interface
- `pigpiod.service` - GPIO daemon for servo control
- `hostapd.service` - WiFi access point (when needed)
- `dnsmasq.service` - DHCP server for access point (when needed)

## Configuration

### Adjusting Alert Timings
Edit `iss_tracker.py` and modify these constants:
```python
ALERT_30M = 1800  # 30 minutes (seconds)
ALERT_10M = 600   # 10 minutes (seconds)
ALERT_5M = 300    # 5 minutes (seconds)
```

### Adjusting Minimum Elevation
```python
MIN_ELEVATION = 15.0  # Minimum degrees above horizon
```

### Changing WiFi AP Credentials
Edit `conf/hostapd.conf`:
```
ssid=PieSS-Setup
wpa_passphrase=christmas
```

Or modify during installation by editing `piess_installer.sh`:
```bash
AP_SSID="PieSS-Setup"
AP_PASSWORD="christmas"
```

## Troubleshooting

### ISS Tracker Not Starting
```bash
sudo journalctl -u iss_tracker -f
```

### WiFi Portal Not Accessible
```bash
sudo journalctl -u wifi_portal -f
tail -f /var/log/piess-portal.log
systemctl status hostapd
systemctl status dnsmasq
```

### LEDs Not Working
```bash
cd ~/PieSS/2025/v2
source venv/bin/activate
sudo systemctl stop iss_tracker
python3 hardware_test.py
```

### Check All Services
```bash
systemctl status boot_decider
systemctl status iss_tracker
systemctl status wifi_portal
systemctl status pigpiod
```

### No Visible Passes Found
```bash
# Check what passes are being calculated
cd ~/PieSS/2025/v2
source venv/bin/activate
python3 check_passes.py
```

The ISS must pass during night-time (between sunset and sunrise) to be considered visible. During winter months at higher latitudes, there may be extended periods with no visible passes.

## LED Behavior Reference

| Situation | LED Indicator | Color(s) | Meaning |
|-----------|---------------|----------|---------|
| No WiFi / AP Mode | 30-min alert LED blinking (0.5s) | Red | System needs WiFi configuration |
| Scanning Networks | Directional LEDs circular animation | Green->Red->Yellow->Red (N->E->S->W) | WiFi scan in progress |
| 30-25 min before pass | 30-min alert LED slow blink (4s) | Red | Pass approaching |
| 25-20 min before pass | 30-min alert LED blink (3s) | Red | Pass approaching |
| 20-15 min before pass | 30-min alert LED blink (2s) | Red | Pass approaching |
| 15-10 min before pass | 30-min alert LED fast blink (1s) | Red | Pass soon |
| 10-8 min before pass | 10-min alert LED slow blink (3s) | Yellow | Pass very soon |
| 8-6 min before pass | 10-min alert LED blink (2s) | Yellow | Pass very soon |
| 6-5 min before pass | 10-min alert LED fast blink (1s) | Yellow | Get ready |
| 5-3 min before pass | 5-min alert LED blink (2s) | Green | Almost here |
| 3-1 min before pass | 5-min alert LED fast blink (1s) | Green | Look up soon |
| 1-0 min before pass | 5-min alert LED rapid blink (0.5s) | Green | Look up now! |
| During pass | Directional LED tracks ISS position | Green/Red/Yellow (N/E/S/W) | Where to look |

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## License

This project is open source and available under the MIT License.

## Acknowledgments

- ISS orbital data provided by [CelesTrak](https://celestrak.org/)
- Location detection via IP geolocation services (ipapi.co, ipinfo.io, ifconfig.co)
- Built with [Skyfield](https://rhodesmill.org/skyfield/) astronomical library
- Flask web framework for configuration portal
- [pigpio](https://abyz.me.uk/rpi/pigpio/) for hardware PWM servo control

## Authors

Created by CPowerMav for tracking and celebrating ISS passes with a physical flag display.

**Repository:** [https://github.com/CPowerMav/PieSS](https://github.com/CPowerMav/PieSS)

---

**Note:** This device is for educational and recreational purposes. ISS pass predictions are approximate and actual visibility depends on weather conditions and light pollution.
