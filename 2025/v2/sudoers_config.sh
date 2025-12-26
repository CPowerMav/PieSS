# Sudoers configuration for PieSS user
# This allows the piess user to run specific commands without password
# Place this file in /etc/sudoers.d/piess-sudoers

# Allow piess user to manage network services
piess ALL=(ALL) NOPASSWD: /usr/bin/systemctl start hostapd
piess ALL=(ALL) NOPASSWD: /usr/bin/systemctl stop hostapd
piess ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart hostapd
piess ALL=(ALL) NOPASSWD: /usr/bin/systemctl start dnsmasq
piess ALL=(ALL) NOPASSWD: /usr/bin/systemctl stop dnsmasq
piess ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart dnsmasq

# Allow piess user to use nmcli for network operations
piess ALL=(ALL) NOPASSWD: /usr/bin/nmcli

# Allow piess user to manage IP addresses (for AP mode)
piess ALL=(ALL) NOPASSWD: /usr/sbin/ip
