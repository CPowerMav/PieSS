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
- Minimum 15° elevation for optimal viewing

### Visual Alerts
- **30-10 minutes**: Red LED with progressively faster blinking
- **10-5 minutes**: Yellow LED with progressively faster blinking
- **5-0 minutes**: Green LED with progressively faster blinking
- **During pass**: Directional LEDs (N/E/S/W) track the ISS across the sky
- **Flag raising**: Servo motor raises flag at pass start, lowers after completion

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
- 7x LEDs with appropriate resistors:
  - 1x Red LED (30-minute alert)
  - 1x Yellow LED (10-minute alert)
  - 1x Green LED (5-minute alert)
  - 4x Directional LEDs (North, East, South, West)
- Breadboard and jumper wires

### GPIO Pin Assignments
| Component | GPIO Pin |
|-----------|----------|
| Servo Motor | GPIO 16 |
| Red LED (30-min) | GPIO 22 |
| Yellow LED (10-min) | GPIO 27 |
| Green LED (5-min) | GPIO 17 |
| North LED | GPIO 5 |
| East LED | GPIO 6 |
| South LED | GPIO 13 |
| West LED | GPIO 12 |

## Software Requirements

- Raspberry Pi OS (Bookworm/Trixie or newer)
- Python 3.9+
- Internet connection for initial setup

## Quick Start

### 1. Flash Raspberry Pi OS
- Download Raspberry Pi OS Lite
- Flash to microSD card using Raspberry Pi Imager
- Configure to boot to CLI (no desktop)

### 2. Clone Repository
```bash
cd ~
git clone https://github.com/yourusername/PieSS.git
cd PieSS/2025/v2
```

### 3. Install Dependencies
```bash
sudo apt update
sudo apt install -y python3-pip python3-venv pigpio hostapd dnsmasq

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python packages
pip install -r requirements.txt
```

### 4. Configure System Services
Follow the detailed setup instructions in `DOCUMENTATION.md`

### 5. First Boot
- Without WiFi configured, PieSS creates access point "PieSS-Setup" (password: christmas)
- Connect to access point and navigate to http://192.168.4.1:8080
- Select your WiFi network and enter password
- PieSS will connect and begin tracking the ISS

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
1. Creates access point "PieSS-Setup"
2. Connect with password: `christmas`
3. Open browser to http://192.168.4.1:8080
4. Scan for networks and configure WiFi
5. PieSS will connect and resume ISS tracking

### Hardware Test
To verify all connections:
```bash
cd ~/PieSS/2025/v2
source venv/bin/activate
sudo systemctl stop iss_tracker
python3 hardware_test.py
```

## Project Structure

```
PieSS/2025/v2/
├── iss_tracker.py          # Main ISS tracking application
├── wifi_portal.py          # WiFi configuration web server
├── boot_decider.sh         # Boot-time service orchestrator
├── hardware_test.py        # Hardware connection test utility
├── templates/
│   ├── wifi_portal.html    # WiFi configuration page
│   ├── wifi_result.html    # Connection result page
│   └── logo.png            # PieSS logo
├── requirements.txt        # Python dependencies
├── README.md              # This file
└── DOCUMENTATION.md       # Complete technical documentation
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
Edit `/etc/hostapd/hostapd.conf`:
```
ssid=PieSS-Setup
wpa_passphrase=christmas
```

## Troubleshooting

### ISS Tracker Not Starting
```bash
sudo journalctl -u iss_tracker -f
```

### WiFi Portal Not Accessible
```bash
sudo journalctl -u wifi_portal -f
systemctl status hostapd
systemctl status dnsmasq
```

### LEDs Not Working
```bash
python3 hardware_test.py
```

### Check All Services
```bash
systemctl status boot_decider
systemctl status iss_tracker
systemctl status wifi_portal
```

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## License

This project is open source and available under the MIT License.

## Acknowledgments

- ISS orbital data provided by [CelesTrak](https://celestrak.org/)
- Location detection via IP geolocation services
- Built with [Skyfield](https://rhodesmill.org/skyfield/) astronomical library
- Flask web framework for configuration portal

## Author

Created for tracking and celebrating ISS passes with a physical flag display.

---

**Note:** This device is for educational and recreational purposes. ISS pass predictions are approximate and actual visibility depends on weather conditions and light pollution.
