
import asyncio
import threading
import time
from hbmqtt.broker import Broker

class MQTTBrokerManager:
    """Manages an embedded MQTT broker using hbmqtt"""
    
    def __init__(self, host='0.0.0.0', port=1883):
        self.host = host
        self.port = port
        self.broker = None
        self.running = False
        
    def start(self):
        """Start the MQTT broker in async mode"""
        self.running = True
        
        # Create event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(self._start_broker())
        except Exception as e:
            print(f"⚠️  MQTT Broker error: {e}")
        finally:
            loop.close()
    
    async def _start_broker(self):
        """Start the MQTT broker asynchronously"""
        config = {
            'listeners': {
                'default': {
                    'type': 'tcp',
                    'bind': f'{self.host}:{self.port}'
                }
            },
            'sys_interval': 10,
            'auth': {
                'allow-anonymous': True,
                'password-file': None,
                'plugins': ['auth_anonymous']
            },
            'topic-check': {
                'enabled': False
            }
        }
        
        self.broker = Broker(config)
        await self.broker.start()
        print(f"🔌 MQTT Broker started on {self.host}:{self.port}")
        
        # Keep the broker running
        while self.running:
            await asyncio.sleep(1)
        
        await self.broker.shutdown()
    
    def stop(self):
        """Stop the broker"""
        self.running = False

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
