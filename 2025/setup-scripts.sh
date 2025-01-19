#!/bin/bash
# setup.sh - Install all dependencies for ISS Tracker

# Check if script is run with sudo
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

echo "Installing ISS Tracker dependencies..."

# Update package list
apt-get update

# Install Python3 and pip if not already installed
apt-get install -y python3 python3-pip

# Install required Python packages
pip3 install python-dotenv pigpio gpiozero

# Enable and start pigpio daemon
systemctl enable pigpiod
systemctl start pigpiod

echo "Setup complete! All dependencies have been installed."
echo "Remember to create your .env file with your NASA API key!"
