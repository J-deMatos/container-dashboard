#!/usr/bin/env python3
"""
Docker Dashboard Updater
Automatically updates the Docker dashboard HTML page and optionally serves it via HTTP API.
"""

import os
import sys
import time
import signal
import threading
import argparse
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

# Add current directory to path to import docker_manager
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from docker_manager import DockerManager

class DashboardUpdateHandler(BaseHTTPRequestHandler):
    """HTTP handler for dashboard updates and serving"""
    
    def do_GET(self):
        if self.path == '/api/refresh':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            try:
                # Update the dashboard
                manager = DockerManager()
                manager.save_html()
                
                response = {
                    "status": "success",
                    "message": "Dashboard updated successfully",
                    "timestamp": datetime.now().isoformat()
                }
                self.wfile.write(json.dumps(response).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = {
                    "status": "error",
                    "message": str(e),
                    "timestamp": datetime.now().isoformat()
                }
                self.wfile.write(json.dumps(response).encode())
        
        elif self.path == '/' or self.path == '/dashboard':
            # Serve the dashboard HTML
            try:
                with open('index.html', 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(html_content.encode('utf-8'))
            except FileNotFoundError:
                self.send_response(404)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                error_html = """
                <html><body>
                <h1>Dashboard Not Found</h1>
                <p>The dashboard HTML file (index.html) was not found.</p>
                <p>Please run: <code>python3 docker_manager.py</code> to generate it.</p>
                </body></html>
                """
                self.wfile.write(error_html.encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                error_html = f"""
                <html><body>
                <h1>Server Error</h1>
                <p>Error loading dashboard: {str(e)}</p>
                </body></html>
                """
                self.wfile.write(error_html.encode())
        
        else:
            self.send_response(404)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            error_html = """
            <html><body>
            <h1>404 Not Found</h1>
            <p>The requested page was not found.</p>
            <p>Available endpoints:</p>
            <ul>
                <li><a href="/">Dashboard</a></li>
                <li><a href="/api/refresh">API Refresh</a></li>
            </ul>
            </body></html>
            """
            self.wfile.write(error_html.encode())
    
    def log_message(self, format, *args):
        """Override to reduce log noise"""
        pass

class DashboardUpdater:
    """Main updater class"""
    
    def __init__(self, update_interval=300, web_port=8080, web_enabled=False):
        self.update_interval = update_interval
        self.web_port = web_port
        self.web_enabled = web_enabled
        self.running = False
        self.manager = DockerManager()
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\nReceived signal {signum}, shutting down...")
        self.running = False
    
    def update_dashboard(self):
        """Update the dashboard HTML file"""
        try:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Updating dashboard...")
            self.manager.save_html()
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Dashboard updated successfully")
            return True
        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error updating dashboard: {e}")
            return False
    
    def start_web_server(self):
        """Start the HTTP server for API endpoints"""
        if not self.web_enabled:
            return
        
        try:
            server = HTTPServer(('0.0.0.0', self.web_port), DashboardUpdateHandler)
            print(f"Web server started on port {self.web_port} (external access enabled)")
            
            while self.running:
                server.handle_request()
                time.sleep(0.1)
            
            server.server_close()
            print("Web server stopped")
        except Exception as e:
            print(f"Error starting web server: {e}")
    
    def run(self):
        """Main run loop"""
        print("Docker Dashboard Updater started")
        print(f"Update interval: {self.update_interval} seconds")
        print(f"Web API enabled: {self.web_enabled}")
        if self.web_enabled:
            print(f"Web API port: {self.web_port}")
        print("Press Ctrl+C to stop")
        
        # Initial update
        self.update_dashboard()
        
        # Start web server in a separate thread if enabled
        web_thread = None
        if self.web_enabled:
            web_thread = threading.Thread(target=self.start_web_server, daemon=True)
            web_thread.start()
        
        self.running = True
        last_update = time.time()
        
        try:
            while self.running:
                current_time = time.time()
                
                # Check if it's time to update
                if current_time - last_update >= self.update_interval:
                    self.update_dashboard()
                    last_update = current_time
                
                # Sleep for a short time to avoid busy waiting
                time.sleep(1)
        
        except KeyboardInterrupt:
            print("\nShutdown requested by user")
        finally:
            self.running = False
            print("Docker Dashboard Updater stopped")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Docker Dashboard Updater')
    parser.add_argument('--interval', '-i', type=int, default=300,
                       help='Update interval in seconds (default: 300)')
    parser.add_argument('--web-port', '-p', type=int, default=8080,
                       help='Web API port (default: 8080)')
    parser.add_argument('--enable-web', '-w', action='store_true',
                       help='Enable web API for manual updates')
    parser.add_argument('--once', action='store_true',
                       help='Update once and exit')
    
    args = parser.parse_args()
    
    if args.once:
        # Update once and exit
        manager = DockerManager()
        manager.save_html()
        print("Dashboard updated successfully")
        return
    
    # Start the updater
    updater = DashboardUpdater(
        update_interval=args.interval,
        web_port=args.web_port,
        web_enabled=args.enable_web
    )
    updater.run()

if __name__ == "__main__":
    main()
