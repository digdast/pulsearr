#!/usr/bin/env bash
# ==============================================================================
# Pulsearr - Automated Installer for Debian / Ubuntu / Linux Mint / Raspberry Pi
# ==============================================================================

set -euo pipefail

# ANSI Color codes
BOLD='\033[1m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

INSTALL_DIR="/opt/pulsearr"
SERVICE_USER="pulsearr"
SERVICE_GROUP="pulsearr"
SERVICE_FILE="/etc/systemd/system/pulsearr.service"
CLI_BIN="/usr/local/bin/pulsearr"

echo -e "${CYAN}${BOLD}"
cat << 'EOF'
  ____  _   _ _     ____  _____    _    ____  ____  
 |  _ \| | | | |   / ___|| ____|  / \  |  _ \|  _ \ 
 | |_) | | | | |   \___ \|  _|   / _ \ | |_) | |_) |
 |  __/| |_| | |___ ___) | |___ / ___ \|  _ <|  _ < 
 |_|    \___/|_____|____/|_____/_/   \_\_| \_\_| \_\
 
  >> Next-Gen Fast Asynchronous Python TV PVR <<
  >> Debian / Ubuntu Automated System Installer <<
EOF
echo -e "${NC}"

# 1. Root / Sudo Check
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}[ERROR] This installer must be run as root or with sudo.${NC}"
    echo "Usage: sudo bash install.sh"
    exit 1
fi

# 2. Check Debian-based OS
if [ ! -f /etc/debian_version ] && ! grep -qi "debian\|ubuntu" /etc/os-release 2>/dev/null; then
    echo -e "${YELLOW}[WARNING] This script is designed for Debian-based systems (Debian, Ubuntu, Linux Mint, Pop!_OS, etc.).${NC}"
    read -rp "Do you wish to proceed anyway? (y/N): " CONFIRM
    if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 3. Update APT & Install System Dependencies
echo -e "${CYAN}[1/6] Installing system dependencies (Python 3, venv, pip, sqlite3, curl)...${NC}"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y --no-install-recommends \
    python3 \
    python3-venv \
    python3-pip \
    sqlite3 \
    curl \
    ca-certificates

# 4. Create Service User & Group
echo -e "${CYAN}[2/6] Configuring dedicated system service user (${SERVICE_USER})...${NC}"
if ! id -u "$SERVICE_USER" >/dev/null 2>&1; then
    useradd --system --shell /usr/sbin/nologin --user-group "$SERVICE_USER"
    echo -e "${GREEN}Created system user: ${SERVICE_USER}${NC}"
else
    echo -e "${GREEN}User ${SERVICE_USER} already exists.${NC}"
fi

# 5. Setup Installation Directory & Deploy Application
echo -e "${CYAN}[3/6] Deploying Pulsearr to ${INSTALL_DIR}...${NC}"
mkdir -p "$INSTALL_DIR"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Copy application files
if [ "$SCRIPT_DIR" != "$INSTALL_DIR" ]; then
    cp -r "$SCRIPT_DIR/pulsearr" "$INSTALL_DIR/"
    cp -r "$SCRIPT_DIR/static" "$INSTALL_DIR/"
    cp -r "$SCRIPT_DIR/templates" "$INSTALL_DIR/"
    cp "$SCRIPT_DIR/run.py" "$INSTALL_DIR/"
    cp "$SCRIPT_DIR/requirements.txt" "$INSTALL_DIR/"
fi

mkdir -p "$INSTALL_DIR/data/media/tv"
mkdir -p "$INSTALL_DIR/data/media/movies"

# 6. Setup Python Virtual Environment & Dependencies
echo -e "${CYAN}[4/6] Creating isolated Python virtual environment...${NC}"
if [ ! -d "$INSTALL_DIR/venv" ]; then
    python3 -m venv "$INSTALL_DIR/venv"
fi

"$INSTALL_DIR/venv/bin/pip" install --upgrade pip --quiet
"$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt" --quiet

# Fix permissions
chown -R "${SERVICE_USER}:${SERVICE_GROUP}" "$INSTALL_DIR"
chmod -R 755 "$INSTALL_DIR"
chmod -R 775 "$INSTALL_DIR/data"

# 7. Install & Enable Systemd Service
echo -e "${CYAN}[5/6] Registering systemd service...${NC}"
cat << EOF > "$SERVICE_FILE"
[Unit]
Description=Pulsearr TV PVR
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${SERVICE_USER}
Group=${SERVICE_GROUP}
WorkingDirectory=${INSTALL_DIR}
Environment="PYTHONUNBUFFERED=1"
Environment="PULSEARR_DATA_DIR=${INSTALL_DIR}/data"
ExecStart=${INSTALL_DIR}/venv/bin/python run.py
Restart=always
RestartSec=5
TimeoutStopSec=20
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable pulsearr.service
systemctl restart pulsearr.service

# 8. Create CLI Helper (/usr/local/bin/pulsearr)
echo -e "${CYAN}[6/6] Creating 'pulsearr' CLI command...${NC}"
cat << 'EOF' > "$CLI_BIN"
#!/usr/bin/env bash
case "${1:-status}" in
    start)
        sudo systemctl start pulsearr
        echo "Pulsearr service started."
        ;;
    stop)
        sudo systemctl stop pulsearr
        echo "Pulsearr service stopped."
        ;;
    restart)
        sudo systemctl restart pulsearr
        echo "Pulsearr service restarted."
        ;;
    status)
        sudo systemctl status pulsearr
        ;;
    logs)
        sudo journalctl -u pulsearr -f
        ;;
    *)
        echo "Pulsearr CLI Manager"
        echo "Usage: pulsearr {start|stop|restart|status|logs}"
        ;;
esac
EOF
chmod +x "$CLI_BIN"

# 9. Get Local IP Address
SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")

echo ""
echo -e "${GREEN}${BOLD}================================================================${NC}"
echo -e "${GREEN}${BOLD}       Pulsearr Installed & Running Successfully!               ${NC}"
echo -e "${GREEN}${BOLD}================================================================${NC}"
echo -e " * Web UI Dashboard : ${CYAN}http://${SERVER_IP}:8990${NC}"
echo -e " * Localhost Access : ${CYAN}http://localhost:8990${NC}"
echo -e " * Installation Dir : ${BOLD}${INSTALL_DIR}${NC}"
echo -e " * Media Directory  : ${BOLD}${INSTALL_DIR}/data/media/tv${NC}"
echo -e " * System Service   : ${BOLD}systemctl status pulsearr${NC}"
echo ""
echo -e "${BOLD}Quick CLI Management Commands:${NC}"
echo -e " - ${YELLOW}pulsearr status${NC}   : View service status"
echo -e " - ${YELLOW}pulsearr logs${NC}     : Stream live logs"
echo -e " - ${YELLOW}pulsearr restart${NC}  : Restart the server"
echo -e " - ${YELLOW}pulsearr stop${NC}     : Stop the server"
echo ""
EOF
