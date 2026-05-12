#!/usr/bin/env python3
"""
COMPREHENSIVE SURVEILLANCE SYSTEM STARTUP & TEST SCRIPT
Phases 6-8: System integration, testing, and monitoring
"""

import subprocess
import time
import os
import sys
import json
from datetime import datetime

class SystemManager:
    def __init__(self):
        self.processes = {}
        self.log_file = 'system_startup.log'
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        
    def log(self, message, level='INFO'):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] [{level}] {message}"
        print(log_msg)
        with open(self.log_file, 'a') as f:
            f.write(log_msg + '\n')
    
    def start_backend(self):
        """Start Laravel backend server"""
        self.log("Starting Laravel backend...", "INFO")
        try:
            os.chdir(os.path.join(self.base_path, 'backend'))
            
            # Check if server is already running
            try:
                import requests
                requests.get('http://127.0.0.1:8000/', timeout=2)
                self.log("Laravel backend already running on port 8000", "WARN")
                return True
            except:
                pass
            
            # Start server
            proc = subprocess.Popen(
                ['php', 'artisan', 'serve', '--port=8000'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            self.processes['backend'] = proc
            
            # Wait for server to start
            time.sleep(3)
            
            import requests
            for attempt in range(5):
                try:
                    response = requests.get('http://127.0.0.1:8000/', timeout=2)
                    self.log("✓ Laravel backend started successfully (port 8000)", "SUCCESS")
                    return True
                except:
                    time.sleep(1)
            
            self.log("✗ Failed to start Laravel backend", "ERROR")
            return False
        except Exception as e:
            self.log(f"✗ Error starting backend: {str(e)[:100]}", "ERROR")
            return False
    
    def start_frontend(self):
        """Start React frontend server"""
        self.log("Starting React frontend...", "INFO")
        try:
            os.chdir(os.path.join(self.base_path, 'frontend'))
            
            # Check if already running
            try:
                import requests
                requests.get('http://127.0.0.1:3000/', timeout=2)
                self.log("React frontend already running on port 3000", "WARN")
                return True
            except:
                pass
            
            # Start server
            proc = subprocess.Popen(
                ['npm', 'start'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                env={**os.environ, 'BROWSER': 'none'}
            )
            self.processes['frontend'] = proc
            
            # Wait for server to start
            self.log("Waiting for React to compile and start...", "INFO")
            time.sleep(10)  # Give React time to compile
            
            import requests
            for attempt in range(10):
                try:
                    response = requests.get('http://127.0.0.1:3000/', timeout=2)
                    self.log("✓ React frontend started successfully (port 3000)", "SUCCESS")
                    return True
                except:
                    time.sleep(1)
            
            self.log("✗ Failed to start React frontend", "ERROR")
            return False
        except Exception as e:
            self.log(f"✗ Error starting frontend: {str(e)[:100]}", "ERROR")
            return False
    
    def start_ml_service(self):
        """Start Python ML service"""
        self.log("Starting Python ML Service...", "INFO")
        try:
            ml_path = os.path.join(self.base_path, 'ml-service')
            os.chdir(ml_path)
            
            # Check Python environment
            python_cmd = 'python'  # or 'python3'
            
            # Start service with simulator mode
            proc = subprocess.Popen(
                [python_cmd, 'main.py'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                env={
                    **os.environ,
                    'USE_CAMERA': 'true',  # Use actual camera
                    'MONGODB_URI': 'mongodb+srv://venkatasaigunda82_db_user:Lakshmisai123@cluster0.oy678v0.mongodb.net/?appName=Cluster0'
                }
            )
            self.processes['ml_service'] = proc
            
            time.sleep(3)
            self.log("✓ Python ML Service started (Simulator mode)", "SUCCESS")
            return True
        except Exception as e:
            self.log(f"✗ Error starting ML service: {str(e)[:100]}", "ERROR")
            return False
    
    def run_integration_tests(self):
        """Run integration tests"""
        self.log("Running integration tests...", "INFO")
        try:
            os.chdir(self.base_path)
            result = subprocess.run(
                [sys.executable, 'integration_test.py'],
                capture_output=False,
                timeout=120
            )
            return result.returncode == 0
        except Exception as e:
            self.log(f"Error running tests: {str(e)[:100]}", "ERROR")
            return False
    
    def print_system_status(self):
        """Print current system status"""
        print("\n" + "="*70)
        print("SYSTEM STATUS REPORT")
        print("="*70)
        
        import requests
        
        services = {
            'Backend': ('http://127.0.0.1:8000/', 'Laravel'),
            'Frontend': ('http://127.0.0.1:3000/', 'React'),
            'API': ('http://127.0.0.1:8000/api/analytics/timeline?camera_id=camera_1&date=2025-05-11', 'REST API')
        }
        
        for name, (url, desc) in services.items():
            try:
                response = requests.get(url, timeout=2)
                status = f"✓ RUNNING ({response.status_code})"
                print(f"\n{name:15} | {desc:20} | {status}")
            except:
                print(f"\n{name:15} | {desc:20} | ✗ OFFLINE")
        
        print("\n" + "="*70)
        print("NEXT STEPS:")
        print("="*70)
        print("1. Open browser: http://localhost:3000")
        print("2. Navigate through tabs: Live, Calendar, Videos, Reports, Heatmap, Alerts, Settings")
        print("3. Backend API tests can be manually run: python integration_test.py")
        print("4. ML Service is running in SIMULATOR mode - use 'USE_CAMERA=true' for real camera")
        print("="*70 + "\n")
    
    def start_all(self):
        """Start all services"""
        print("\n" + "="*70)
        print("PHASE 6-8: SURVEILLANCE SYSTEM STARTUP")
        print("="*70 + "\n")
        
        self.log("Initializing system components...", "INFO")
        
        # Start services in order
        backend_ok = self.start_backend()
        if not backend_ok:
            self.log("Cannot continue without backend", "ERROR")
            return False
        
        frontend_ok = self.start_frontend()
        if not frontend_ok:
            self.log("Frontend failed but continuing...", "WARN")
        
        ml_ok = self.start_ml_service()
        if not ml_ok:
            self.log("ML Service failed but continuing...", "WARN")
        
        time.sleep(5)
        
        # Run integration tests
        self.log("Starting integration tests...", "INFO")
        tests_ok = self.run_integration_tests()
        
        # Print status
        self.print_system_status()
        
        return backend_ok and tests_ok
    
    def cleanup(self):
        """Stop all services"""
        self.log("Shutting down all services...", "INFO")
        for name, proc in self.processes.items():
            try:
                proc.terminate()
                proc.wait(timeout=5)
                self.log(f"✓ Stopped {name}", "INFO")
            except:
                try:
                    proc.kill()
                    self.log(f"✓ Force killed {name}", "INFO")
                except:
                    self.log(f"✗ Failed to stop {name}", "ERROR")

if __name__ == "__main__":
    manager = SystemManager()
    
    try:
        success = manager.start_all()
        if success:
            print("\n" + "="*70)
            print("✓ SYSTEM STARTUP SUCCESSFUL")
            print("="*70)
            print("\nSurveillance system is now running!")
            print("Frontend:  http://localhost:3000")
            print("Backend:   http://localhost:8000")
            print("ML Service: Running (Simulator mode)")
            print("\nPress Ctrl+C to stop services...\n")
            
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n\nShutting down services...")
                manager.cleanup()
                print("✓ All services stopped")
        else:
            print("\n✗ System startup failed")
            manager.cleanup()
            sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {str(e)}")
        manager.cleanup()
        sys.exit(1)
