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
        self._server_process = None
        
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
        """Start Flask server using a simple threading approach"""
        try:
            self.logger.info(f"Starting Flask server on port {self.port}")
            
            # Simple Flask server startup
            def run_flask():
                try:
                    self.is_running = True
                    self.logger.info("Flask server thread started")
                    
                    # Run Flask with proper configuration
                    self.app.run(
                        host='0.0.0.0', 
                        port=self.port, 
                        debug=False, 
                        use_reloader=False,
                        threaded=True
                    )
                    
                except Exception as e:
                    self.logger.error(f"Flask server error: {e}")
                finally:
                    self.is_running = False
                    self.logger.info("Flask server thread ended")
            
            # Start server in daemon thread
            self.server_thread = threading.Thread(target=run_flask, daemon=True)
            self.server_thread.start()
            
            # Wait for server to start
            time.sleep(1.0)
            self.logger.info("✅ Flask server started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start Flask server: {e}")
            raise
    
    def stop_server(self):
        """Stop Flask server"""
        try:
            if self.server_thread and self.server_thread.is_alive():
                self.logger.info("Stopping Flask server...")
                
                # Since Flask doesn't have a clean shutdown method,
                # we rely on the daemon thread to die with the main process
                # Just mark as not running and let the thread finish naturally
                self.is_running = False
                
                # Give the thread a moment to finish
                time.sleep(0.5)
                
                if self.server_thread.is_alive():
                    self.logger.info("Flask server thread still running (will die with main process)")
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
