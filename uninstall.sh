#!/usr/bin/env bash
# ==============================================================================
# Pulsearr - Automated Uninstaller for Debian / Ubuntu
# ==============================================================================

set -euo pipefail

if [ "$EUID" -ne 0 ]; then
    echo "[ERROR] Please run with sudo: sudo bash uninstall.sh"
    exit 1
fi

echo "Stopping and disabling Pulsearr service..."
systemctl stop pulsearr.service 2>/dev/null || true
systemctl disable pulsearr.service 2>/dev/null || true

rm -f /etc/systemd/system/pulsearr.service
systemctl daemon-reload

rm -f /usr/local/bin/pulsearr

read -rp "Do you also want to delete all configuration, database, and library files in /opt/pulsearr? (y/N): " CONFIRM
if [[ "$CONFIRM" =~ ^[Yy]$ ]]; then
    rm -rf /opt/pulsearr
    userdel pulsearr 2>/dev/null || true
    echo "Pulsearr and all data have been completely removed."
else
    echo "Pulsearr service removed. Data preserved in /opt/pulsearr/data."
fi
