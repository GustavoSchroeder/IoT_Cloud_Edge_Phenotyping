
import subprocess
import time
import threading
import os
import signal

class MQTTBrokerManager:
    """Manages an embedded MQTT broker using mosquitto"""
    
    def __init__(self, host='127.0.0.1', port=1883):
        self.host = host
        self.port = port
        self.process = None
        self.running = False
        
    def start(self):
        """Start the MQTT broker using mosquitto"""
        self.running = True
        
        try:
            # Create a simple mosquitto config
            config_content = f"""
listener {self.port} {self.host}
allow_anonymous true
persistence false
"""
            with open('/tmp/mosquitto.conf', 'w') as f:
                f.write(config_content)
            
            # Start mosquitto broker
            self.process = subprocess.Popen([
                'mosquitto', '-c', '/tmp/mosquitto.conf'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            print(f"🔌 MQTT Broker (mosquitto) started on {self.host}:{self.port}")
            
            # Monitor the process
            while self.running and self.process.poll() is None:
                time.sleep(1)
                
        except FileNotFoundError:
            print("⚠️  mosquitto not found, using simple mock broker")
            self._start_mock_broker()
        except Exception as e:
            print(f"⚠️  MQTT Broker error: {e}")
            self._start_mock_broker()
    
    def _start_mock_broker(self):
        """Start a mock broker that just prints status"""
        import socket
        
        # Try to bind to the port to make it available
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((self.host, self.port))
            sock.listen(5)
            print(f"🔌 Mock MQTT Broker started and listening on {self.host}:{self.port}")
            print("📡 MQTT clients can connect (basic socket server active)")
            
            # Accept connections but don't process them fully
            sock.settimeout(1.0)  # Non-blocking with timeout
            
            while self.running:
                try:
                    conn, addr = sock.accept()
                    print(f"📡 Mock MQTT: Connection from {addr}")
                    conn.close()  # Close immediately for now
                except socket.timeout:
                    pass  # Continue loop
                except Exception as e:
                    if self.running:
                        print(f"⚠️  Mock broker connection error: {e}")
                
                time.sleep(0.1)  # Small delay
            
            sock.close()
            
        except Exception as e:
            print(f"⚠️  Could not bind mock broker to port {self.port}: {e}")
            # Fallback to simple heartbeat
            while self.running:
                time.sleep(5)
                if self.running:
                    print("💓 Mock MQTT Broker heartbeat (no socket binding)")
    
    def stop(self):
        """Stop the broker"""
        self.running = False
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()

def start_mqtt_broker():
    """Start MQTT broker in a separate thread"""
    broker_manager = MQTTBrokerManager()
    broker_thread = threading.Thread(target=broker_manager.start, daemon=True)
    broker_thread.start()
    return broker_manager

if __name__ == "__main__":
    # Start broker for testing
    broker = start_mqtt_broker()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n⏹️  Stopping MQTT Broker...")
        broker.stop()
