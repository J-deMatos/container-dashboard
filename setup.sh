#!/bin/bash

# Docker Dashboard Setup Script
# This script sets up the Docker Dashboard system with all features

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEB_ROOT="/srv/http"
NGINX_SITES="/etc/nginx/sites-available"
NGINX_ENABLED="/etc/nginx/sites-enabled"
SERVICE_FILE="/etc/systemd/system/docker-dashboard.service"

# Detect hostname dynamically
DETECTED_HOSTNAME=$(hostname -f 2>/dev/null || hostname 2>/dev/null || echo "localhost")
CURRENT_USER=$(whoami)
CURRENT_HOME=$(eval echo ~$CURRENT_USER)

# Detect if we're on Arch Linux
if command -v pacman &> /dev/null; then
    IS_ARCH=true
    PACKAGE_MANAGER="pacman"
else
    IS_ARCH=false
    PACKAGE_MANAGER="apt"
fi

echo -e "${BLUE}🐳 Docker Dashboard Setup${NC}"
echo "================================"

if [[ "$IS_ARCH" == "true" ]]; then
    echo -e "${GREEN}✓ Detected Arch Linux (pacman)${NC}"
else
    echo -e "${YELLOW}ℹ Detected non-Arch Linux system (apt)${NC}"
fi

echo -e "${GREEN}✓ Detected hostname: ${DETECTED_HOSTNAME}${NC}"
echo -e "${GREEN}✓ Current user: ${CURRENT_USER}${NC}"
echo -e "${GREEN}✓ Home directory: ${CURRENT_HOME}${NC}"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${YELLOW}Note: This script needs to be run as root for nginx and systemd setup${NC}"
   echo -e "${YELLOW}However, Docker can run without sudo on your system${NC}"
   echo ""
   read -p "Continue with sudo for system setup? (y/n): " -n 1 -r
   echo
   if [[ ! $REPLY =~ ^[Yy]$ ]]; then
       echo -e "${YELLOW}You can still run the dashboard manually:${NC}"
       echo -e "  python3 docker_manager.py"
       echo -e "  python3 update_dashboard.py --interval 300 --enable-web --web-port 8070"
       exit 0
   fi
fi

# Check if Docker is installed and running
echo -e "${YELLOW}Checking Docker installation...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo -e "${RED}Docker is not running or accessible. Please start Docker first.${NC}"
    echo -e "${YELLOW}Note: If Docker requires sudo, you may need to add your user to the docker group${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker is installed and running (no sudo required)${NC}"

# Check if nginx is installed
echo -e "${YELLOW}Checking nginx installation...${NC}"
if ! command -v nginx &> /dev/null; then
    echo -e "${YELLOW}nginx is not installed. Installing nginx...${NC}"
    if [[ "$IS_ARCH" == "true" ]]; then
        pacman -S --noconfirm nginx
    else
        apt update
        apt install -y nginx
    fi
fi

echo -e "${GREEN}✓ nginx is installed${NC}"

# Create web directory if it doesn't exist
echo -e "${YELLOW}Setting up web directory...${NC}"
mkdir -p "$WEB_ROOT"
if [[ "$IS_ARCH" == "true" ]]; then
    chown -R http:http "$WEB_ROOT"
else
    chown -R www-data:www-data "$WEB_ROOT"
fi

# Copy nginx configuration
echo -e "${YELLOW}Configuring nginx...${NC}"
# Create sites directories if they don't exist
mkdir -p "$NGINX_SITES"
mkdir -p "$NGINX_ENABLED"

if [[ -f "nginx.conf.template" ]]; then
    # Use template to generate nginx config
    sed "s/__HOSTNAME__/${DETECTED_HOSTNAME}/g; s|__WEB_ROOT__|${WEB_ROOT}|g" nginx.conf.template > "$NGINX_SITES/docker-dashboard"
    echo -e "${GREEN}✓ Generated nginx config from template${NC}"
else
    # Fallback to copying existing file
    cp "$SCRIPT_DIR/nginx.conf" "$NGINX_SITES/docker-dashboard"
    # Update hostname in nginx config
    sed -i "s/localhost/${DETECTED_HOSTNAME}/g" "$NGINX_SITES/docker-dashboard"
    echo -e "${GREEN}✓ Updated nginx config with detected hostname${NC}"
fi
ln -sf "$NGINX_SITES/docker-dashboard" "$NGINX_ENABLED/docker-dashboard"

# Remove default nginx site if it exists
if [[ -L "$NGINX_ENABLED/default" ]]; then
    rm "$NGINX_ENABLED/default"
fi

# Enable nginx service
systemctl enable nginx


# Install systemd service
echo -e "${YELLOW}Installing systemd service...${NC}"
if [[ -f "docker-dashboard.service.template" ]]; then
    # Use template to generate service file
    sed "s/__USER__/${CURRENT_USER}/g; s|__WORK_DIR__|${SCRIPT_DIR}|g" docker-dashboard.service.template > "$SERVICE_FILE"
    echo -e "${GREEN}✓ Generated systemd service from template${NC}"
else
    # Fallback: Create service file directly
    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Docker Dashboard Updater
After=network.target docker.service
Wants=docker.service

[Service]
Type=simple
User=${CURRENT_USER}
Group=${CURRENT_USER}
WorkingDirectory=${SCRIPT_DIR}
ExecStart=/usr/bin/python3 ${SCRIPT_DIR}/update_dashboard.py --interval 300 --enable-web --web-port 8070
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Environment variables
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF
    echo -e "${GREEN}✓ Created systemd service directly${NC}"
fi

# Reload systemd and enable service
systemctl daemon-reload
systemctl enable docker-dashboard.service

# Make Python scripts executable
chmod +x "$SCRIPT_DIR/docker_manager.py"
chmod +x "$SCRIPT_DIR/update_dashboard.py"

# Update config.json with detected hostname
echo -e "${YELLOW}Updating configuration...${NC}"
if [[ -f "config.json" ]]; then
    # Update hostname in config.json
    python3 -c "
import json
import sys

try:
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    config['hostname'] = '${DETECTED_HOSTNAME}'
    
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    print('✓ Updated config.json with detected hostname: ${DETECTED_HOSTNAME}')
except Exception as e:
    print(f'✗ Error updating config.json: {e}')
    sys.exit(1)
"
    echo -e "${GREEN}✓ Configuration updated${NC}"
else
    echo -e "${YELLOW}⚠ config.json not found, will be created with defaults${NC}"
fi

# Install Python dependencies
echo -e "${YELLOW}Installing Python dependencies...${NC}"
if [[ "$IS_ARCH" == "true" ]]; then
    # Arch Linux - install Python packages via pacman
    pacman -S --noconfirm python-pip python-setuptools
    echo -e "${GREEN}✓ Python packages installed via pacman${NC}"
else
    # Other Linux - use pip
    pip3 install --upgrade pip
    echo -e "${GREEN}✓ Python packages installed via pip${NC}"
fi

# Generate initial dashboard
echo -e "${YELLOW}Generating initial dashboard...${NC}"
cd "$SCRIPT_DIR"
python3 docker_manager.py

# Copy dashboard to web root
cp "$SCRIPT_DIR/index.html" "$WEB_ROOT/docker-dashboard.html"
if [[ "$IS_ARCH" == "true" ]]; then
    chown http:http "$WEB_ROOT/docker-dashboard.html"
else
    chown www-data:www-data "$WEB_ROOT/docker-dashboard.html"
fi

# Start services
echo -e "${YELLOW}Starting services...${NC}"
systemctl restart nginx
systemctl start docker-dashboard.service

# Check service status
echo -e "${YELLOW}Checking service status...${NC}"
if systemctl is-active --quiet docker-dashboard.service; then
    echo -e "${GREEN}✓ Docker Dashboard service is running${NC}"
else
    echo -e "${RED}✗ Docker Dashboard service failed to start${NC}"
    systemctl status docker-dashboard.service
fi

if systemctl is-active --quiet nginx; then
    echo -e "${GREEN}✓ nginx is running${NC}"
else
    echo -e "${RED}✗ nginx failed to start${NC}"
    systemctl status nginx
fi


# Display final information
echo ""
echo -e "${GREEN}🎉 Setup completed successfully!${NC}"
echo ""
echo -e "${BLUE}Access your Docker Dashboard at:${NC}"
echo -e "  https://${DETECTED_HOSTNAME}/"
echo -e "  http://${DETECTED_HOSTNAME}:8070/ (direct access)"
echo ""
echo -e "${BLUE}API Endpoints:${NC}"
echo -e "  https://${DETECTED_HOSTNAME}/api/refresh"
echo -e "  http://${DETECTED_HOSTNAME}:8070/api/refresh (direct access)"
echo ""
echo -e "${BLUE}Quick Start Options:${NC}"
echo ""
echo -e "${YELLOW}1. Simple Web Server:${NC}"
echo -e "   ./start_dashboard.sh"
echo -e "   Then open: http://localhost:8080"
echo ""
echo -e "${YELLOW}2. Auto-Updater with Web API:${NC}"
echo -e "   ./start_updater.sh"
echo -e "   Then open: http://localhost:8070"
echo ""
echo -e "${YELLOW}3. Generate dashboard once:${NC}"
echo -e "   python3 docker_manager.py"
echo -e "   Then open: index.html in your browser"
echo ""
echo -e "${BLUE}Service Management:${NC}"
echo -e "  Status: systemctl status docker-dashboard"
echo -e "  Logs:   journalctl -u docker-dashboard -f"
echo -e "  Restart: systemctl restart docker-dashboard"
echo ""
echo -e "${BLUE}Configuration files:${NC}"
echo -e "  Main config: $SCRIPT_DIR/config.json"
echo -e "  Nginx config: $NGINX_SITES/docker-dashboard"
echo -e "  Service file: $SERVICE_FILE"
echo ""


# Check if Tailscale is running
if command -v tailscale &> /dev/null && tailscale status &> /dev/null; then
    echo -e "${GREEN}✓ Tailscale is running${NC}"
    echo -e "${BLUE}Your Tailscale hostname: $(tailscale status --json | python3 -c 'import sys, json; print(json.load(sys.stdin)["Self"]["HostName"])')${NC}"
else
    echo -e "${YELLOW}⚠ Tailscale not detected. Make sure Tailscale is installed and running.${NC}"
fi

echo ""
echo -e "${YELLOW}Note: You may need to configure SSL certificates for HTTPS to work properly.${NC}"
echo -e "${YELLOW}For Tailscale, SSL certificates are usually handled automatically.${NC}"
echo ""