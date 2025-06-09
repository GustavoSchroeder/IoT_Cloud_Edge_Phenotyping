
import threading
import time
import socket
from typing import Dict, Set

class SimpleMQTTBroker:
    """Simple MQTT broker for local testing"""
    
    def __init__(self, host='localhost', port=1883):
        self.host = host
        self.port = port
        self.clients: Dict[str, socket.socket] = {}
        self.subscriptions: Dict[str, Set[str]] = {}
        self.running = False
        
    def start(self):
        """Start the MQTT broker"""
        self.running = True
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            print(f"🔌 Simple MQTT Broker started on {self.host}:{self.port}")
            
            while self.running:
                try:
                    client_socket, address = self.server_socket.accept()
                    client_thread = threading.Thread(
                        target=self._handle_client, 
                        args=(client_socket, address),
                        daemon=True
                    )
                    client_thread.start()
                except:
                    break
                    
        except Exception as e:
            print(f"⚠️  MQTT Broker error: {e}")
        finally:
            self.server_socket.close()
    
    def _handle_client(self, client_socket, address):
        """Handle individual client connections"""
        client_id = f"client_{address[0]}_{address[1]}"
        self.clients[client_id] = client_socket
        print(f"📱 MQTT Client connected: {client_id}")
        
        try:
            while self.running:
                # Simple message handling - in real MQTT this would be more complex
                time.sleep(1)
        except:
            pass
        finally:
            if client_id in self.clients:
                del self.clients[client_id]
            client_socket.close()
            print(f"📱 MQTT Client disconnected: {client_id}")
    
    def stop(self):
        """Stop the broker"""
        self.running = False
        if hasattr(self, 'server_socket'):
            self.server_socket.close()

def start_mqtt_broker():
    """Start MQTT broker in a separate thread"""
    broker = SimpleMQTTBroker()
    broker_thread = threading.Thread(target=broker.start, daemon=True)
    broker_thread.start()
    return broker

if __name__ == "__main__":
    # Start broker for testing
    broker = start_mqtt_broker()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n⏹️  Stopping MQTT Broker...")
        broker.stop()
