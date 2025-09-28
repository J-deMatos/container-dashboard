# Container Dashboard

A web dashboard for Docker containers with exposed ports. *Because I'm always forgetting what's running on each port* 😅

## ⚠️ Requirements

This tool requires a specific setup:
- **Server environment** with Docker containers running
- **Arch Linux** with pacman package manager (can be easily adapted for other distros)
- **Tailscale** with MagicDNS enabled (configure in admin console)
- **Docker** configured for non-root user access
- **Nginx** for web server (installed by setup script)
- **Python 3.6+** with standard library only

*Note: While designed for Arch Linux, the core functionality can be easily adapted for other Linux distributions.*

## Features

- **Auto-discovery** of Docker containers with exposed ports
- **Smart organization** with alphabetical sorting and clean names
- **Auto-updates** every 5 minutes via systemd service
- **Tailscale-ready** with HTTPS support
- **Template-based** configuration generation
- **Web API** for manual refresh
- **Responsive UI** with modern design

## Quick Start

### Verify Requirements
```bash
# Check Tailscale with MagicDNS
tailscale status
# Should show your hostname and "MagicDNS: enabled"

# Check Docker (no sudo required)
docker ps
# Should list containers without permission errors

# Check package manager (Arch Linux)
pacman --version
# Or for other distros: apt --version, yum --version, etc.
```

### Full Setup (Recommended)
```bash
sudo ./setup.sh
```
Access: `https://your-server-hostname/`

### Manual Setup
```bash
# Install dependencies
sudo pacman -S python-pip python-setuptools nginx docker

# Start dashboard
./start_dashboard.sh
```
Access: `http://localhost:8080`

### Manual Usage
```bash
# Generate once
python3 docker_manager.py

# Auto-updater
python3 update_dashboard.py --interval 300 --enable-web
```

## Files

- `docker_manager.py` - Main script
- `update_dashboard.py` - Auto-updater
- `config.json` - Configuration
- `setup.sh` - Installation script
- `nginx.conf.template` - Nginx config template
- `docker-dashboard.service.template` - Systemd service template

## Configuration

Edit `config.json`:
```json
{
  "hostname": "your-server-hostname",
  "protocol": "http",
  "description": "Container Dashboard Configuration"
}
```

## Manual Installation

### Arch Linux (Current Implementation)
```bash
sudo pacman -S python-pip python-setuptools nginx docker
```

### Other Linux (Easily Adaptable)
```bash
sudo apt install python3-pip nginx docker.io
pip3 install -r requirements.txt
```

*Note: The setup script currently only supports Arch Linux, but the core functionality works on any Linux distro. Adapt the package installation commands for your system.*

### Command Line Options
- `--interval, -i`: Update interval in seconds (default: 300)
- `--web-port, -p`: Web API port (default: 8080)
- `--enable-web, -w`: Enable web API
- `--once`: Update once and exit

## Service Management

```bash
# Check status
sudo systemctl status docker-dashboard

# View logs
sudo journalctl -u docker-dashboard -f

# Restart
sudo systemctl restart docker-dashboard
```

## API

- **Refresh**: `GET /api/refresh`
- **Access**: localhost and Tailscale network only

```bash
curl https://your-server-hostname/api/refresh
```

## Troubleshooting

**Dashboard not updating?**
```bash
sudo systemctl status docker-dashboard
sudo journalctl -u docker-dashboard -f
```

**Can't access the URL?**
- Check Tailscale MagicDNS: `tailscale status` (should show "MagicDNS: enabled")
- Check nginx: `sudo systemctl status nginx`
- Verify hostname resolution: `nslookup your-hostname`

**No services showing?**
- Ensure Docker containers have exposed ports
- Check Docker permissions: `docker ps` (should work without sudo)
- Run `python3 docker_manager.py` to test

**Tailscale issues?**
- Enable MagicDNS in Tailscale admin console
- Restart Tailscale: `sudo systemctl restart tailscaled`
- Check DNS: `tailscale status --json | grep -i dns`

## License

Open source. Modify and distribute as needed.