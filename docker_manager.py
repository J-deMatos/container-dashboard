#!/usr/bin/env python3
"""
Docker Manager - Static HTML Generator
Generates a static HTML page showing all Docker services with exposed ports,
organized by categories and including GitHub repository links.
"""

import json
import subprocess
import re
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

@dataclass
class DockerService:
    name: str
    image: str
    status: str
    ports: List[Tuple[str, str]]  # (host_port, container_port)
    github_repo: Optional[str] = None
    category: str = "Other"
    description: str = ""

class DockerManager:
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config = self.load_config()
        self.services = []
        
    def load_config(self) -> Dict:
        """Load configuration from JSON file"""
        default_config = {
            "hostname": "localhost",
            "protocol": "http",
            "description": "Container Dashboard Configuration"
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                # Merge with defaults
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
            except Exception as e:
                print(f"Error loading config: {e}")
                return default_config
        else:
            # Create default config file
            with open(self.config_file, 'w') as f:
                json.dump(default_config, f, indent=2)
            return default_config
    
    def get_docker_containers(self, all_containers=False) -> List[Dict]:
        """Get list of Docker containers (running or all)"""
        try:
            cmd = ["docker", "ps"]
            if all_containers:
                cmd.append("-a")
            
            cmd.extend([
                "--format", 
                "{{.Names}}|{{.Image}}|{{.Status}}|{{.Ports}}"
            ])
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            containers = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    parts = line.split('|')
                    if len(parts) >= 4:
                        container = {
                            "Name": parts[0],
                            "Image": parts[1], 
                            "Status": parts[2],
                            "Ports": parts[3]
                        }
                        containers.append(container)
            return containers
        except subprocess.CalledProcessError as e:
            print(f"Error running docker command: {e}")
            return []
        except FileNotFoundError:
            print("Docker not found. Please ensure Docker is installed and running.")
            return []
    
    def parse_ports(self, ports_str: str) -> List[Tuple[str, str]]:
        """Parse Docker ports string into list of (host_port, container_port) tuples"""
        if not ports_str or ports_str == "":
            return []
        
        ports = []
        # Handle multiple port mappings separated by commas
        port_mappings = ports_str.split(',')
        
        for mapping in port_mappings:
            mapping = mapping.strip()
            if '->' in mapping:
                # Format: "0.0.0.0:8080->80/tcp"
                parts = mapping.split('->')
                if len(parts) == 2:
                    host_part = parts[0].strip()
                    container_part = parts[1].strip()
                    
                    # Extract port numbers
                    host_port_match = re.search(r':(\d+)', host_part)
                    container_port_match = re.search(r'(\d+)', container_part)
                    
                    if host_port_match and container_port_match:
                        host_port = host_port_match.group(1)
                        container_port = container_port_match.group(1)
                        ports.append((host_port, container_port))
            elif ':' in mapping and not mapping.startswith('::'):
                # Format: "8080:80/tcp"
                parts = mapping.split(':')
                if len(parts) >= 2:
                    host_port = parts[0].strip()
                    container_port = parts[1].strip().split('/')[0]
                    ports.append((host_port, container_port))
        
        return ports
    
    
    def is_database_container(self, name: str, image: str) -> bool:
        """Check if a container is a database"""
        name_lower = name.lower()
        image_lower = image.lower()
        
        database_keywords = [
            'mysql', 'postgres', 'postgresql', 'mongo', 'mongodb', 'redis', 
            'database', 'db', 'sql', 'nosql', 'mariadb', 'sqlite', 'cassandra',
            'elasticsearch', 'influxdb', 'couchdb', 'neo4j', 'orientdb',
            'couchbase', 'dynamodb', 'firebase', 'rethinkdb', 'arangodb',
            'timescaledb', 'clickhouse', 'questdb', 'quest', 'supabase',
            'planetscale', 'neon', 'railway', 'vercel', 'supabase',
            'db-', '-db', '_db', 'db_', 'database-', '-database', '_database'
        ]
        
        for keyword in database_keywords:
            if keyword in name_lower or keyword in image_lower:
                return True
        return False

    def clean_container_name(self, name: str, image: str) -> str:
        """Clean up container name by removing generic terms and using image name as reference"""
        # Generic terms to remove from container names
        generic_terms = [
            'frontend', 'backend', 'server', 'docker', 'app', 'web', 'api',
            'service', 'container', 'instance', 'main', 'primary', 'default',
            'prod', 'production', 'dev', 'development', 'test', 'testing',
            'staging', 'preview', 'demo', 'example', 'sample', 'temp', 'tmp',
            'nginx', 'proxy', 'gateway', 'router', 'loadbalancer', 'lb',
            'cache', 'redis', 'db', 'database', 'sql', 'nosql', 'storage',
            'file', 'files', 'upload', 'download', 'static', 'assets',
            'media', 'image', 'images', 'video', 'audio', 'music', 'photo',
            'admin', 'management', 'dashboard', 'panel', 'control', 'config',
            'setup', 'install', 'init', 'bootstrap', 'startup', 'launcher',
            'runner', 'executor', 'worker', 'processor', 'handler', 'manager',
            'controller', 'monitor', 'watcher', 'observer', 'listener',
            'receiver', 'sender', 'publisher', 'subscriber', 'consumer',
            'producer', 'generator', 'creator', 'builder', 'compiler',
            'transformer', 'converter', 'parser', 'analyzer', 'scanner',
            'crawler', 'spider', 'bot', 'agent', 'daemon', 'process',
            'thread', 'task', 'job', 'work', 'operation', 'function',
            'module', 'component', 'part', 'piece', 'unit', 'element',
            'item', 'object', 'entity', 'record', 'entry', 'row', 'line',
            'node', 'point', 'spot', 'place', 'location', 'position',
            'site', 'area', 'zone', 'region', 'section', 'segment',
            'chunk', 'block', 'fragment', 'portion', 'bit', 'part',
            'webservice', 'webserver', 'webui', 'web-ui', 'ui', 'interface',
            '1', '2', '3', '4', '5', '6', '7', '8', '9', '0',  # numbers
            '-1', '-2', '-3', '-4', '-5', '-6', '-7', '-8', '-9', '-0'  # numbered suffixes
        ]
        
        # Extract the main part of the image name (before the first slash or colon)
        image_parts = image.split('/')[-1].split(':')[0].split('@')[0]
        
        # Clean the container name
        cleaned_name = name.lower()
        
        # Remove generic terms
        for term in generic_terms:
            # Remove term with various separators
            for separator in ['-', '_', '.', ' ']:
                pattern = f"{separator}{term}{separator}"
                cleaned_name = cleaned_name.replace(pattern, separator)
                pattern = f"{term}{separator}"
                if cleaned_name.startswith(pattern):
                    cleaned_name = cleaned_name[len(pattern):]
                pattern = f"{separator}{term}"
                if cleaned_name.endswith(pattern):
                    cleaned_name = cleaned_name[:-len(pattern)]
        
        # Remove leading/trailing separators
        for separator in ['-', '_', '.', ' ']:
            cleaned_name = cleaned_name.strip(separator)
        
        # Split by any separator and remove duplicates
        import re
        # Split by any non-alphanumeric character
        words = re.split(r'[^a-zA-Z0-9]+', cleaned_name)
        # Remove empty strings and duplicates while preserving order
        unique_words = []
        for word in words:
            if word and word.lower() not in [w.lower() for w in unique_words]:
                unique_words.append(word)
        cleaned_name = ' '.join(unique_words)
        
        # If the cleaned name is too short or empty, use image name
        if len(cleaned_name) < 3 or not cleaned_name:
            cleaned_name = image_parts
        
        # Capitalize first letter of each word
        cleaned_name = ' '.join(word.capitalize() for word in cleaned_name.split())
        
        return cleaned_name

    def process_containers(self, show_all=True) -> List[DockerService]:
        """Process Docker containers and create service objects"""
        containers = self.get_docker_containers(all_containers=show_all)
        services = []
        
        for container in containers:
            name = container.get("Name", "")
            image = container.get("Image", "")
            ports = self.parse_ports(container.get("Ports", ""))
            status = container.get("Status", "")
            
            # Skip database containers
            if self.is_database_container(name, image):
                continue
            
            # Only include containers with external ports
            if not ports:
                continue
            
            # Clean the container name
            cleaned_name = self.clean_container_name(name, image)
            
            service = DockerService(
                name=cleaned_name,
                image=image,
                status=status,
                ports=ports
            )
            
            services.append(service)
        
        # Sort services alphabetically by name
        services.sort(key=lambda x: x.name.lower())
        
        return services
    
    def _generate_css(self) -> str:
        """Generate CSS styles for the dashboard"""
        return """        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .header {
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header-top {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 30px;
        }
        
        .header-content {
            flex: 1;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: 300;
        }
        
        .header p {
            font-size: 1.1em;
            opacity: 0.9;
        }
        
        .protocol-toggle {
            margin-top: 10px;
        }
        
        .toggle-btn {
            background: rgba(255, 255, 255, 0.2);
            border: 1px solid rgba(255, 255, 255, 0.3);
            border-radius: 20px;
            padding: 8px 16px;
            font-size: 0.85em;
            font-weight: 500;
            color: white;
            cursor: pointer;
            transition: all 0.3s ease;
            outline: none;
        }
        
        .toggle-btn:hover {
            background: rgba(255, 255, 255, 0.3);
            border-color: rgba(255, 255, 255, 0.5);
        }
        
        .toggle-btn.active {
            background: #3498db;
            color: white;
            border-color: #2980b9;
        }
        
        .stats {
            display: flex;
            justify-content: center;
            gap: 30px;
            margin-top: 20px;
        }
        
        .stat {
            text-align: center;
        }
        
        .stat-number {
            font-size: 2.5em;
            font-weight: 700;
            color: #3498db;
            margin-bottom: 5px;
        }
        
        .stat-label {
            font-size: 1em;
            opacity: 0.8;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .content {
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            margin-top: 20px;
        }
        
        .status-tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 30px;
            justify-content: center;
        }
        
        .status-tab {
            padding: 12px 24px;
            border: 2px solid #3498db;
            background: transparent;
            color: #3498db;
            border-radius: 25px;
            cursor: pointer;
            transition: all 0.3s ease;
            font-weight: 600;
            font-size: 1em;
        }
        
        .status-tab:hover {
            background: #2980b9;
            color: white;
        }
        
        .status-tab.active {
            background: #3498db;
            color: white;
        }
        
        
        
        .services-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
        }
        
        .service-card {
            background: white;
            border-radius: 12px;
            padding: 16px;
            box-shadow: 0 3px 10px rgba(0, 0, 0, 0.08);
            border: 1px solid #e1e8ed;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
            cursor: pointer;
            text-decoration: none;
            color: inherit;
            display: block;
        }
        
        .service-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 30px rgba(0, 0, 0, 0.15);
            text-decoration: none;
            color: inherit;
        }
        
        .service-card.stopped {
            opacity: 0.7;
            border-color: #e74c3c;
        }
        
        .service-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, #3498db, #2ecc71);
        }
        
        .service-card.stopped::before {
            background: linear-gradient(90deg, #e74c3c, #c0392b);
        }
        
        .service-name {
            font-size: 1.3em;
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 6px;
        }
        
        .service-image {
            font-size: 0.9em;
            color: #7f8c8d;
            margin-bottom: 10px;
            font-family: 'Courier New', monospace;
        }
        
        .service-status {
            display: inline-block;
            padding: 3px 10px;
            border-radius: 16px;
            font-size: 0.8em;
            font-weight: 600;
        }
        
        .service-info {
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            margin-top: 8px;
        }
        
        .service-port {
            font-size: 0.8em;
            color: #2c3e50;
            font-weight: 600;
        }
        
        .status-running {
            background: #d5f4e6;
            color: #27ae60;
        }
        
        .status-unhealthy {
            background: #fef9e7;
            color: #f39c12;
        }
        
        .status-stopped {
            background: #fadbd8;
            color: #e74c3c;
        }
        
        
        
        .action-buttons {
            margin-top: 15px;
        }
        
        .action-btn {
            display: inline-block;
            padding: 10px 20px;
            background: #3498db;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            margin-right: 10px;
            transition: background 0.3s ease;
        }
        
        .action-btn:hover {
            background: #2980b9;
        }
        
        .footer {
            text-align: center;
            margin-top: 40px;
            padding: 20px;
            color: #7f8c8d;
            font-size: 0.9em;
        }
        
        .footer p {
            margin-bottom: 5px;
        }
        
        .no-services {
            text-align: center;
            padding: 60px 20px;
            color: #7f8c8d;
        }
        
        .no-services h3 {
            font-size: 1.5em;
            margin-bottom: 15px;
            color: #95a5a6;
        }
        
        .no-services p {
            font-size: 1.1em;
            line-height: 1.6;
            margin-bottom: 10px;
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 10px;
            }
            
            .header {
                padding: 20px;
            }
            
            .header h1 {
                font-size: 2em;
            }
            
            .stats {
                flex-direction: column;
                gap: 15px;
            }
            
            .services-grid {
                grid-template-columns: 1fr;
            }
            
            .status-tabs {
                flex-direction: column;
                align-items: center;
            }
            
            .status-tab {
                width: 100%;
                max-width: 200px;
            }
        }
        
        @media (max-width: 480px) {
            .header h1 {
                font-size: 1.8em;
            }
            
            .stat-number {
                font-size: 2em;
            }
        }"""

    def _generate_javascript(self) -> str:
        """Generate JavaScript for the dashboard"""
        return """        function showServices(type) {
            // Update tab states
            document.querySelectorAll('.status-tab').forEach(tab => {
                tab.classList.remove('active');
            });
            event.target.classList.add('active');
            
            // Show/hide services based on type
            const allCards = document.querySelectorAll('.service-card');
            allCards.forEach(card => {
                const isRunning = card.querySelector('.status-running');
                const isStopped = card.querySelector('.status-stopped');
                
                if (type === 'all') {
                    card.style.display = 'block';
                } else if (type === 'running' && isRunning) {
                    card.style.display = 'block';
                } else if (type === 'stopped' && isStopped) {
                    card.style.display = 'block';
                } else {
                    card.style.display = 'none';
                }
            });
        }
        
        function toggleProtocol() {
            const btn = document.getElementById('protocol-btn');
            const text = document.getElementById('protocol-text');
            const allCards = document.querySelectorAll('.service-card');
            
            if (text.textContent === 'HTTP') {
                text.textContent = 'HTTPS';
                btn.classList.add('active');
                
                // Update all service card links to HTTPS
                allCards.forEach(card => {
                    const currentHref = card.getAttribute('href');
                    if (currentHref && currentHref.startsWith('http://' + window.location.hostname + ':')) {
                        card.setAttribute('href', currentHref.replace('http://', 'https://'));
                    }
                });
            } else {
                text.textContent = 'HTTP';
                btn.classList.remove('active');
                
                // Update all service card links to HTTP
                allCards.forEach(card => {
                    const currentHref = card.getAttribute('href');
                    if (currentHref && currentHref.startsWith('https://' + window.location.hostname + ':')) {
                        card.setAttribute('href', currentHref.replace('https://', 'http://'));
                    }
                });
            }
        }"""

    def generate_html(self, show_all=True) -> str:
        """Generate the static HTML page"""
        self.services = self.process_containers(show_all=show_all)
        
        # Separate running and stopped containers
        running_services = [s for s in self.services if "Up" in s.status]
        stopped_services = [s for s in self.services if "Exited" in s.status or "Created" in s.status]
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Docker Services Dashboard</title>
    <style>
{self._generate_css()}
    </style>
    <script>
{self._generate_javascript()}
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="header-top">
                <div class="header-content">
                    <h1>🐳 Docker Services Dashboard</h1>
                    <p>Manage and access your containerized services</p>
                </div>
                <div class="protocol-toggle">
                    <button id="protocol-btn" onclick="toggleProtocol()" class="toggle-btn">
                        <span id="protocol-text">HTTP</span>
                    </button>
                </div>
            </div>
            <div class="stats">
                <div class="stat">
                    <div class="stat-number">{len(running_services)}</div>
                    <div class="stat-label">Running</div>
                </div>
                <div class="stat">
                    <div class="stat-number">{len(stopped_services)}</div>
                    <div class="stat-label">Stopped</div>
                </div>
                <div class="stat">
                    <div class="stat-number">{len(self.services)}</div>
                    <div class="stat-label">Total Services</div>
                </div>
            </div>
        </div>
        
        <div class="content">
            <div class="status-tabs">
                <button class="status-tab active" onclick="showServices('all')">All Services ({len(self.services)})</button>
                <button class="status-tab" onclick="showServices('running')">Running ({len(running_services)})</button>
                <button class="status-tab" onclick="showServices('stopped')">Stopped ({len(stopped_services)})</button>
            </div>"""
        
        if not self.services:
            html += '''
            <div class="no-services">
                <h3>No Services Found</h3>
                <p>No Docker containers with external ports are currently running.</p>
                <p>Note: Database containers and containers without external ports are filtered out.</p>
            </div>'''
        else:
            html += '''
            <div class="services-grid">'''
            
            for service in self.services:
                # Determine status class based on container status
                if "Up" in service.status:
                    if "unhealthy" in service.status.lower():
                        status_class = "status-unhealthy"
                    else:
                        status_class = "status-running"
                else:
                    status_class = "status-stopped"
                
                first_port = service.ports[0][0] if service.ports else None
                main_url = f"http://{self.config['hostname']}:{first_port}" if first_port else "#"
                
                html += f'''
                <a href="{main_url}" target="_blank" class="service-card">
                    <div class="service-name">{service.name}</div>
                    <div class="service-image">{service.image}</div>
                    <div class="service-info">
                        <span class="service-port">Port: {first_port}</span>
                        <div class="service-status {status_class}">{service.status}</div>
                    </div>'''
                
                html += '''
                </a>'''
            
            html += '''
            </div>'''
        
        html += f"""
        </div>
        
        <div class="footer">
            <p>Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            <p>Generated by Docker Manager</p>
        </div>
    </div>
</body>
</html>"""
        
        return html
    
    def save_html(self, output_file: str = "index.html"):
        """Save the generated HTML to a file"""
        html_content = self.generate_html()
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"HTML page generated successfully: {output_file}")

def main():
    """Main function"""
    manager = DockerManager()
    manager.save_html()
    
    # Also save to a web-accessible location if specified
    web_path = "/srv/http/docker-dashboard.html"
    if os.path.exists("/srv/http"):
        manager.save_html(web_path)
        print(f"Also saved to web directory: {web_path}")

if __name__ == "__main__":
    main()
