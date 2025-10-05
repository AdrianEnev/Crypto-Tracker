"""
Flask server for Phantom wallet integration frontend
"""

import asyncio
import json
import logging
import threading
import time
from flask import Flask, render_template, request, jsonify
from pathlib import Path

app = Flask(__name__, 
            template_folder=str(Path(__file__).parent / "templates"),
            static_folder=str(Path(__file__).parent / "static"))

class PhantomFlaskServer:
    """Flask server for serving Phantom integration frontend"""
    
    def __init__(self, port: int = 5002):
        self.port = port
        self.logger = logging.getLogger(__name__)
        self.server_thread = None
        self.server_instance = None
        self.shutdown_event = threading.Event()
        self.is_running = False
        
        # Create a unique Flask app for this instance
        self.app = Flask(__name__, 
                        template_folder=str(Path(__file__).parent / "templates"),
                        static_folder=str(Path(__file__).parent / "static"))
        
        # Setup routes
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def index():
            """Serve the main Phantom interface"""
            return render_template('phantom_interface.html')
        
        @self.app.route('/health')
        def health():
            """Health check endpoint"""
            return jsonify({'status': 'healthy', 'service': 'phantom-integration'})
    
    def start_server(self):
        """Start Flask server in a separate thread"""
        try:
            self.logger.info(f"Starting Flask server on port {self.port}")
            
            def run_server():
                try:
                    # Use Werkzeug's development server with proper shutdown handling
                    from werkzeug.serving import make_server
                    
                    # Create server
                    self.server_instance = make_server('0.0.0.0', self.port, self.app, threaded=True)
                    
                    # Start server in a separate thread
                    server_thread = threading.Thread(target=self.server_instance.serve_forever, daemon=True)
                    server_thread.start()
                    
                    # Mark as running after server starts
                    self.is_running = True
                    
                    # Wait for shutdown signal
                    while not self.shutdown_event.is_set():
                        time.sleep(0.1)
                    
                    # Shutdown server
                    self.server_instance.shutdown()
                    server_thread.join(timeout=2)
                    self.is_running = False
                    
                except Exception as e:
                    self.logger.error(f"Flask server error: {e}")
                    self.is_running = False
            
            self.server_thread = threading.Thread(target=run_server, daemon=True)
            self.server_thread.start()
            
            # Give server time to start and set is_running flag
            time.sleep(1.0)
            self.logger.info("✅ Flask server started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start Flask server: {e}")
            raise
    
    def stop_server(self):
        """Stop Flask server"""
        try:
            if self.is_running and self.server_thread and self.server_thread.is_alive():
                self.logger.info("Stopping Flask server...")
                
                # Signal shutdown
                self.shutdown_event.set()
                
                # Wait for server thread to finish
                self.server_thread.join(timeout=3)
                
                if self.server_thread.is_alive():
                    self.logger.warning("Flask server thread did not stop gracefully")
                else:
                    self.logger.info("✅ Flask server stopped")
            else:
                self.logger.info("Flask server was not running")
            
        except Exception as e:
            self.logger.error(f"Failed to stop Flask server: {e}")

if __name__ == "__main__":
    # For testing the Flask server independently
    server = PhantomFlaskServer(port=5002)
    server.start_server()
    
    try:
        # Keep the server running
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping Flask server...")
        server.stop_server()
