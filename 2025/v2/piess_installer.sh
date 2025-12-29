#!/usr/bin/env bash
#
# PieSS Installation Script
# Automated installation and configuration for Raspberry Pi
#
# Usage: sudo ./install_piess.sh
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PIESS_USER="piess"
PIESS_DIR="/home/${PIESS_USER}/PieSS/2025/v2"
AP_SSID="PieSS-Setup"
AP_PASSWORD="christmas"

# Helper functions
print_header() {
    echo -e "\n${BLUE}===================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}===================================================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   print_error "This script must be run as root (use sudo)"
   exit 1
fi

# Get the actual user who called sudo
if [ -n "$SUDO_USER" ]; then
    ACTUAL_USER=$SUDO_USER
else
    ACTUAL_USER=$(whoami)
fi

print_header "PieSS Installation Script"
echo "This script will install and configure PieSS on your Raspberry Pi."
echo "Installation directory: ${PIESS_DIR}"
echo "User: ${PIESS_USER}"
echo ""
read -p "Continue with installation? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_warning "Installation cancelled."
    exit 0
fi

# Step 1: System Update
print_header "Step 1: Updating System Packages"
apt update
apt upgrade -y
print_success "System packages updated"

# Step 2: Install Dependencies
print_header "Step 2: Installing Dependencies"
apt install -y \
    python3-pip \
    python3-venv \
    python3-dev \
    pigpio \
    hostapd \
    dnsmasq \
    git \
    nano \
    curl \
    net-tools

print_success "Dependencies installed"

# Step 3: Verify project structure
print_header "Step 3: Verifying Project Structure"
if [ ! -d "${PIESS_DIR}" ]; then
    print_error "Directory ${PIESS_DIR} not found!"
    print_info "Please clone the PieSS repository first:"
    print_info "  git clone https://github.com/CPowerMav/PieSS.git /home/${PIESS_USER}/PieSS"
    exit 1
fi

# Check for required files
REQUIRED_FILES=(
    "iss_tracker.py"
    "wifi_portal.py"
    "boot_decider.sh"
    "hardware_test.py"
    "conf/hostapd.conf"
    "conf/dnsmasq.conf"
    "services/boot_decider.service"
    "services/iss_tracker.service"
    "services/wifi_portal.service"
    "services/pigpiod.service"
    "templates/wifi_portal.html"
    "templates/wifi_result.html"
    "templates/logo.png"
)

cd ${PIESS_DIR}
ALL_FILES_FOUND=true
for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        print_error "Required file missing: $file"
        ALL_FILES_FOUND=false
    fi
done

if [ "$ALL_FILES_FOUND" = false ]; then
    print_error "Some required files are missing. Please ensure repository is complete."
    exit 1
fi

print_success "Project structure verified"

# Step 4: Create user if doesn't exist
print_header "Step 4: Setting Up User Account"
if id "${PIESS_USER}" &>/dev/null; then
    print_info "User ${PIESS_USER} already exists"
else
    useradd -m -s /bin/bash ${PIESS_USER}
    print_success "User ${PIESS_USER} created"
fi

# Step 5: Create Python Virtual Environment
print_header "Step 5: Creating Python Virtual Environment"
cd ${PIESS_DIR}
if [ -d "venv" ]; then
    print_warning "Virtual environment already exists, skipping..."
else
    sudo -u ${PIESS_USER} python3 -m venv venv
    print_success "Virtual environment created"
fi

# Install Python packages
print_info "Installing Python packages..."
sudo -u ${PIESS_USER} bash -c "source venv/bin/activate && pip install --upgrade pip"
sudo -u ${PIESS_USER} bash -c "source venv/bin/activate && pip install flask==3.0.0 skyfield==1.48 requests==2.31.0 pigpio==1.78 gpiozero==2.0.1"
print_success "Python packages installed"

# Create requirements.txt
cat > requirements.txt << 'EOF'
flask==3.0.0
skyfield==1.48
requests==2.31.0
pigpio==1.78
gpiozero==2.0.1
EOF
chown ${PIESS_USER}:${PIESS_USER} requirements.txt

# Step 6: Configure pigpiod
print_header "Step 6: Configuring pigpiod Service"
cp ${PIESS_DIR}/services/pigpiod.service /etc/systemd/system/pigpiod.service
systemctl enable pigpiod
systemctl start pigpiod
print_success "pigpiod configured and started"

# Step 7: Configure hostapd
print_header "Step 7: Configuring WiFi Access Point"
cp ${PIESS_DIR}/conf/hostapd.conf /etc/hostapd/hostapd.conf
chmod 600 /etc/hostapd/hostapd.conf

# Update SSID and password if needed
sed -i "s/^ssid=.*/ssid=${AP_SSID}/" /etc/hostapd/hostapd.conf
sed -i "s/^wpa_passphrase=.*/wpa_passphrase=${AP_PASSWORD}/" /etc/hostapd/hostapd.conf

print_success "hostapd configured (SSID: ${AP_SSID}, Password: ${AP_PASSWORD})"

# Step 8: Configure dnsmasq
print_header "Step 8: Configuring DHCP Server"
cp ${PIESS_DIR}/conf/dnsmasq.conf /etc/dnsmasq.conf
print_success "dnsmasq configured"

# Step 9: Configure sudo permissions
print_header "Step 9: Configuring Sudo Permissions"
cat > /etc/sudoers.d/piess-sudoers << EOF
# Sudoers configuration for PieSS user
piess ALL=(ALL) NOPASSWD: /usr/bin/systemctl start hostapd
piess ALL=(ALL) NOPASSWD: /usr/bin/systemctl stop hostapd
piess ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart hostapd
piess ALL=(ALL) NOPASSWD: /usr/bin/systemctl start dnsmasq
piess ALL=(ALL) NOPASSWD: /usr/bin/systemctl stop dnsmasq
piess ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart dnsmasq
piess ALL=(ALL) NOPASSWD: /usr/bin/nmcli
piess ALL=(ALL) NOPASSWD: /usr/sbin/ip
piess ALL=(ALL) NOPASSWD: /usr/bin/kill
piess ALL=(ALL) NOPASSWD: /bin/sh
piess ALL=(ALL) NOPASSWD: /bin/rm
EOF

chmod 0440 /etc/sudoers.d/piess-sudoers
print_success "Sudo permissions configured"

# Step 10: Install systemd services
print_header "Step 10: Installing System Services"

# Copy service files
cp ${PIESS_DIR}/services/boot_decider.service /etc/systemd/system/
cp ${PIESS_DIR}/services/iss_tracker.service /etc/systemd/system/
cp ${PIESS_DIR}/services/wifi_portal.service /etc/systemd/system/

print_success "Service files installed"

# Step 11: Create log file
print_header "Step 11: Setting Up Log Files"
touch /var/log/piess-portal.log
chown ${PIESS_USER}:${PIESS_USER} /var/log/piess-portal.log
print_success "Log files created"

# Step 12: Make scripts executable
print_header "Step 12: Setting File Permissions"
chmod +x ${PIESS_DIR}/boot_decider.sh
chmod +x ${PIESS_DIR}/iss_tracker.py
chmod +x ${PIESS_DIR}/wifi_portal.py
chmod +x ${PIESS_DIR}/hardware_test.py
chmod +x ${PIESS_DIR}/check_passes.py
chown -R ${PIESS_USER}:${PIESS_USER} /home/${PIESS_USER}/PieSS
print_success "File permissions set"

# Step 13: Enable services
print_header "Step 13: Enabling System Services"
systemctl daemon-reload
systemctl enable boot_decider.service
systemctl enable iss_tracker.service
systemctl disable hostapd
systemctl disable dnsmasq
systemctl disable wifi_portal
print_success "Services enabled"

# Step 14: Configure boot to CLI
print_header "Step 14: Configuring Boot Mode"
systemctl set-default multi-user.target
print_success "Boot mode set to CLI"

# Step 15: Final checks
print_header "Step 15: Running Final Checks"

# Check if pigpiod is running
if systemctl is-active --quiet pigpiod; then
    print_success "pigpiod is running"
else
    print_warning "pigpiod is not running"
fi

# Check if files exist and are executable
if [ -x "${PIESS_DIR}/iss_tracker.py" ]; then
    print_success "iss_tracker.py found and executable"
else
    print_error "iss_tracker.py not found or not executable"
fi

if [ -x "${PIESS_DIR}/wifi_portal.py" ]; then
    print_success "wifi_portal.py found and executable"
else
    print_error "wifi_portal.py not found or not executable"
fi

if [ -x "${PIESS_DIR}/boot_decider.sh" ]; then
    print_success "boot_decider.sh found and executable"
else
    print_error "boot_decider.sh not found or not executable"
fi

# Verify templates directory
if [ -d "${PIESS_DIR}/templates" ] && [ -f "${PIESS_DIR}/templates/logo.png" ]; then
    print_success "Templates directory found with logo"
else
    print_warning "Templates directory or logo not found"
fi

# Installation complete
print_header "Installation Complete!"

echo ""
echo -e "${GREEN}PieSS has been successfully installed!${NC}"
echo ""
echo -e "${BLUE}Repository Structure:${NC}"
echo "  ${PIESS_DIR}/"
echo "  ├── iss_tracker.py          - Main ISS tracking application"
echo "  ├── wifi_portal.py          - WiFi configuration portal"
echo "  ├── boot_decider.sh         - Boot mode orchestrator"
echo "  ├── hardware_test.py        - Hardware testing utility"
echo "  ├── check_passes.py         - ISS pass calculation debug tool"
echo "  ├── conf/                   - Configuration files"
echo "  │   ├── hostapd.conf        - WiFi AP configuration"
echo "  │   ├── dnsmasq.conf        - DHCP configuration"
echo "  │   └── sudoers_config.sh   - Sudo configuration script"
echo "  ├── services/               - Systemd service files"
echo "  │   ├── boot_decider.service"
echo "  │   ├── iss_tracker.service"
echo "  │   ├── wifi_portal.service"
echo "  │   └── pigpiod.service"
echo "  ├── templates/              - Web interface templates"
echo "  │   ├── wifi_portal.html"
echo "  │   ├── wifi_result.html"
echo "  │   └── logo.png"
echo "  └── documentation/          - Project documentation"
echo "      ├── PieSS_Full_Documentation.md"
echo "      └── PieSS_Full_Documentation.pdf"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Reboot the Raspberry Pi: ${YELLOW}sudo reboot${NC}"
echo "2. On first boot:"
echo "   - With WiFi: System will auto-detect location and start tracking ISS"
echo "   - Without WiFi: Connect to '${AP_SSID}' (password: ${AP_PASSWORD})"
echo "                   Then browse to http://192.168.4.1:8080"
echo ""
echo -e "${BLUE}Hardware Test:${NC}"
echo "   ${YELLOW}cd ${PIESS_DIR}${NC}"
echo "   ${YELLOW}source venv/bin/activate${NC}"
echo "   ${YELLOW}sudo systemctl stop iss_tracker${NC}"
echo "   ${YELLOW}python3 hardware_test.py${NC}"
echo ""
echo -e "${BLUE}Check Status:${NC}"
echo "   ${YELLOW}sudo journalctl -u iss_tracker -f${NC}"
echo "   ${YELLOW}systemctl status boot_decider${NC}"
echo ""
echo -e "${BLUE}Debug ISS Passes:${NC}"
echo "   ${YELLOW}cd ${PIESS_DIR}${NC}"
echo "   ${YELLOW}source venv/bin/activate${NC}"
echo "   ${YELLOW}python3 check_passes.py${NC}"
echo ""
echo -e "${BLUE}GPIO Pin Assignments:${NC}"
echo "   Servo:        GPIO 16 (Pin 36)"
echo "   Red LED:      GPIO 22 (Pin 15) - 30-min alert"
echo "   Yellow LED:   GPIO 27 (Pin 13) - 10-min alert"
echo "   Green LED:    GPIO 17 (Pin 11) - 5-min alert"
echo "   North LED:    GPIO 5  (Pin 29)"
echo "   East LED:     GPIO 6  (Pin 31)"
echo "   South LED:    GPIO 13 (Pin 33)"
echo "   West LED:     GPIO 12 (Pin 32)"
echo ""
echo -e "${GREEN}Installation log saved to: /var/log/piess-install.log${NC}"
echo ""

# Save installation info
cat > /var/log/piess-install.log << EOF
PieSS Installation Log
Date: $(date)
User: ${PIESS_USER}
Directory: ${PIESS_DIR}
AP SSID: ${AP_SSID}
AP Password: ${AP_PASSWORD}
Installation completed successfully.

Repository structure follows:
${PIESS_DIR}/
├── Main scripts in root
├── conf/ - System configuration files
├── services/ - Systemd service files
├── templates/ - Web interface files
└── documentation/ - Project docs
EOF

read -p "Would you like to reboot now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Rebooting in 5 seconds..."
    sleep 5
    reboot
else
    print_warning "Please reboot manually when ready: sudo reboot"
fi
