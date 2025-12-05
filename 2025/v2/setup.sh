#!/bin/bash
# setup.sh - Install ISS Tracker dependencies and configure system
# Usage: sudo ./setup.sh
# After installation, reboot. The tracker will autostart.

if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

echo "Updating system packages..."
apt-get update
apt-get install -y python3 python3-pip python3-venv git

echo "Installing Python packages..."
pip3 install python-dotenv pigpio gpiozero skyfield flask requests

echo "Enabling pigpio daemon..."
systemctl enable pigpiod
systemctl start pigpiod

echo "Creating systemd service for ISS Tracker..."
SERVICE_FILE=/etc/systemd/system/iss_tracker.service
cat <<EOL > $SERVICE_FILE
[Unit]
Description=ISS Tracker Service
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/pi/iss_tracker_project/iss_tracker.py
WorkingDirectory=/home/pi/iss_tracker_project
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
EOL

systemctl daemon-reload
systemctl enable iss_tracker.service
systemctl start iss_tracker.service

echo "Setup complete! Reboot recommended."
