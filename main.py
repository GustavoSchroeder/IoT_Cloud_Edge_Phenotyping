
import json
import time
import random
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any
from dataclasses import dataclass, asdict
import numpy as np
from collections import defaultdict, deque
import paho.mqtt.client as mqtt
import uuid

@dataclass
class UserBehaviorData:
    """Data structure for user behavior tracking"""
    timestamp: str
    app_usage: Dict[str, float]  # app_name: minutes_used
    location: str
    communication_count: int
    touch_interactions: int
    unlock_frequency: int
    battery_level: float
    screen_time: float
    typing_speed: float
    ambient_light: float
    accelerometer: List[float]
    network_usage: float

@dataclass
class ContextualInsight:
    """Represents detected patterns and insights"""
    pattern_type: str
    severity: str  # low, medium, high
    description: str
    recommendation: str
    confidence: float

# MQTT Configuration
MQTT_BROKER = "127.0.0.1"  # Can be changed to external broker
MQTT_PORT = 1883
MQTT_TOPICS = {
    'digital_twin_data': 'iot/digitaltwin/behavior',
    'edge_processed_data': 'iot/edge/processed',
    'insights': 'iot/insights/detected',
    'commands': 'iot/commands/control',
    'heartbeat': 'iot/system/heartbeat'
}

class SmartphoneDigitalTwin:
    """Digital twin representation of a smartphone user"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.behavior_history = deque(maxlen=1000)  # Keep last 1000 data points
        self.usage_patterns = {}
        self.daily_stats = defaultdict(list)
        self.overuse_threshold = 8.0  # hours per day
        self.session_threshold = 2.0  # hours per session
        
        # MQTT setup for Digital Twin
        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"digital_twin_{user_id}_{uuid.uuid4().hex[:8]}")
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_message = self._on_mqtt_message
        self.mqtt_connected = False
        self._setup_mqtt_connection()
    
    def _setup_mqtt_connection(self):
        """Setup MQTT connection for Digital Twin with retry logic"""
        max_retries = 5
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                print(f"📱 Digital Twin attempting MQTT connection (attempt {attempt + 1}/{max_retries})")
                self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
                self.mqtt_client.loop_start()
                # Wait a bit for the connection to establish
                time.sleep(1)
                return  # Connection successful
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"⚠️  Digital Twin MQTT connection attempt {attempt + 1} failed: {e}, retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                else:
                    print(f"⚠️  Digital Twin MQTT connection failed after {max_retries} attempts: {e}")
    
    def _on_mqtt_connect(self, client, userdata, flags, rc, properties=None):
        """MQTT connection callback"""
        if rc == 0:
            self.mqtt_connected = True
            print(f"📱 Digital Twin MQTT connected successfully")
            # Subscribe to commands
            client.subscribe(MQTT_TOPICS['commands'])
        else:
            print(f"⚠️  Digital Twin MQTT connection failed with code {rc}")
    
    def _on_mqtt_message(self, client, userdata, msg):
        """Handle incoming MQTT messages"""
        try:
            message = json.loads(msg.payload.decode())
            if msg.topic == MQTT_TOPICS['commands']:
                self._handle_command(message)
        except Exception as e:
            print(f"⚠️  Error processing MQTT message: {e}")
    
    def _handle_command(self, command: Dict):
        """Handle commands received via MQTT"""
        if command.get('type') == 'update_threshold':
            self.overuse_threshold = command.get('value', self.overuse_threshold)
            print(f"📱 Digital Twin: Updated overuse threshold to {self.overuse_threshold} hours")
        elif command.get('type') == 'reset_patterns':
            self.usage_patterns.clear()
            print("📱 Digital Twin: Usage patterns reset")
    
    def publish_behavior_data(self, data: UserBehaviorData):
        """Publish behavior data via MQTT"""
        if self.mqtt_connected:
            message = {
                'user_id': self.user_id,
                'timestamp': data.timestamp,
                'data': asdict(data)
            }
            self.mqtt_client.publish(MQTT_TOPICS['digital_twin_data'], json.dumps(message))
        
    def add_behavior_data(self, data: UserBehaviorData):
        """Add new behavior data to the digital twin"""
        self.behavior_history.append(data)
        self._update_patterns(data)
        self.publish_behavior_data(data)
        
    def _update_patterns(self, data: UserBehaviorData):
        """Update internal patterns based on new data"""
        # Daily screen time tracking
        date = data.timestamp.split('T')[0]
        self.daily_stats[date].append(data.screen_time)
        
        # App usage patterns
        for app, usage in data.app_usage.items():
            if app not in self.usage_patterns:
                self.usage_patterns[app] = {'total': 0, 'sessions': 0, 'avg_session': 0}
            self.usage_patterns[app]['total'] += usage
            self.usage_patterns[app]['sessions'] += 1
            self.usage_patterns[app]['avg_session'] = (
                self.usage_patterns[app]['total'] / self.usage_patterns[app]['sessions']
            )
    
    def detect_overuse_patterns(self) -> List[ContextualInsight]:
        """Detect potential overuse patterns using ML-like analysis"""
        insights = []
        
        if not self.behavior_history:
            return insights
            
        recent_data = list(self.behavior_history)[-50:]  # Last 50 data points
        
        # Analyze daily screen time
        today = datetime.now().strftime('%Y-%m-%d')
        if today in self.daily_stats:
            daily_total = sum(self.daily_stats[today])
            if daily_total > self.overuse_threshold:
                insights.append(ContextualInsight(
                    pattern_type="daily_overuse",
                    severity="high" if daily_total > 10 else "medium",
                    description=f"Daily screen time: {daily_total:.1f} hours exceeds recommended limit",
                    recommendation="Take regular breaks and set app time limits",
                    confidence=0.9
                ))
        
        # Analyze session patterns
        continuous_sessions = self._detect_long_sessions(recent_data)
        if continuous_sessions:
            insights.append(ContextualInsight(
                pattern_type="long_sessions",
                severity="medium",
                description=f"Detected {len(continuous_sessions)} extended usage sessions",
                recommendation="Set session reminders and take breaks every hour",
                confidence=0.8
            ))
        
        # Analyze late-night usage
        late_night_usage = self._detect_late_night_usage(recent_data)
        if late_night_usage:
            insights.append(ContextualInsight(
                pattern_type="late_night_usage",
                severity="high",
                description="Excessive late-night device usage detected",
                recommendation="Enable sleep mode and avoid screens before bedtime",
                confidence=0.85
            ))
        
        return insights
    
    def _detect_long_sessions(self, data: List[UserBehaviorData]) -> List[Dict]:
        """Detect extended usage sessions"""
        sessions = []
        current_session = 0
        
        for entry in data:
            if entry.screen_time > 0:
                current_session += entry.screen_time
            else:
                if current_session > self.session_threshold:
                    sessions.append({'duration': current_session, 'timestamp': entry.timestamp})
                current_session = 0
                
        return sessions
    
    def _detect_late_night_usage(self, data: List[UserBehaviorData]) -> bool:
        """Detect late-night usage patterns"""
        late_night_count = 0
        for entry in data:
            hour = int(entry.timestamp.split('T')[1].split(':')[0])
            if (hour >= 23 or hour <= 6) and entry.screen_time > 0:
                late_night_count += 1
        
        return late_night_count > len(data) * 0.2  # More than 20% late-night usage

class WearableDevice:
    """Simulates wearable device data"""
    
    def generate_data(self) -> Dict[str, Any]:
        return {
            'heart_rate': random.randint(60, 100),
            'stress_level': random.uniform(0, 1),
            'activity_level': random.choice(['sedentary', 'light', 'moderate', 'vigorous']),
            'sleep_quality': random.uniform(0, 1) if random.random() < 0.1 else None
        }

class AmbientSensor:
    """Simulates ambient environmental sensors"""
    
    def generate_data(self) -> Dict[str, Any]:
        return {
            'noise_level': random.uniform(30, 80),  # dB
            'light_intensity': random.uniform(0, 1000),  # lux
            'temperature': random.uniform(18, 26),  # Celsius
            'humidity': random.uniform(30, 70)  # percentage
        }

class EdgeComputingLayer:
    """Simulates Raspberry Pi edge computing layer"""
    
    def __init__(self):
        self.data_buffer = deque(maxlen=100)
        self.digital_twin = SmartphoneDigitalTwin("user_001")
        self.wearable = WearableDevice()
        self.ambient_sensor = AmbientSensor()
        self.context_detection_active = True
        
        # MQTT setup for Edge Layer
        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"edge_layer_{uuid.uuid4().hex[:8]}")
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_message = self._on_mqtt_message
        self.mqtt_connected = False
        self._setup_mqtt_connection()
        
        # Start heartbeat thread
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()
    
    def _setup_mqtt_connection(self):
        """Setup MQTT connection for Edge Layer with retry logic"""
        max_retries = 5
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                print(f"🖥️  Edge Layer attempting MQTT connection (attempt {attempt + 1}/{max_retries})")
                self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
                self.mqtt_client.loop_start()
                # Wait a bit for the connection to establish
                time.sleep(1)
                return  # Connection successful
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"⚠️  Edge Layer MQTT connection attempt {attempt + 1} failed: {e}, retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                else:
                    print(f"⚠️  Edge Layer MQTT connection failed after {max_retries} attempts: {e}")
    
    def _on_mqtt_connect(self, client, userdata, flags, rc, properties=None):
        """MQTT connection callback"""
        if rc == 0:
            self.mqtt_connected = True
            print(f"🖥️  Edge Layer MQTT connected successfully")
            # Subscribe to digital twin data
            client.subscribe(MQTT_TOPICS['digital_twin_data'])
        else:
            print(f"⚠️  Edge Layer MQTT connection failed with code {rc}")
    
    def _on_mqtt_message(self, client, userdata, msg):
        """Handle incoming MQTT messages"""
        try:
            message = json.loads(msg.payload.decode())
            if msg.topic == MQTT_TOPICS['digital_twin_data']:
                print(f"🔄 Edge Layer received data from Digital Twin: {message['user_id']}")
        except Exception as e:
            print(f"⚠️  Error processing MQTT message: {e}")
    
    def _heartbeat_loop(self):
        """Send periodic heartbeat messages"""
        while True:
            if self.mqtt_connected:
                heartbeat_data = {
                    'timestamp': datetime.now().isoformat(),
                    'edge_id': 'raspberry_pi_001',
                    'status': 'active',
                    'buffer_size': len(self.data_buffer),
                    'context_detection': self.context_detection_active
                }
                self.mqtt_client.publish(MQTT_TOPICS['heartbeat'], json.dumps(heartbeat_data))
            time.sleep(30)  # Send heartbeat every 30 seconds
    
    def publish_processed_data(self, processed_data: Dict):
        """Publish processed data via MQTT"""
        if self.mqtt_connected:
            message = {
                'edge_id': 'raspberry_pi_001',
                'timestamp': datetime.now().isoformat(),
                'processed_data': processed_data
            }
            self.mqtt_client.publish(MQTT_TOPICS['edge_processed_data'], json.dumps(message))
    
    def publish_insights(self, insights: List[ContextualInsight]):
        """Publish detected insights via MQTT"""
        if self.mqtt_connected:
            message = {
                'edge_id': 'raspberry_pi_001',
                'timestamp': datetime.now().isoformat(),
                'insights': [asdict(insight) for insight in insights],
                'insight_count': len(insights)
            }
            self.mqtt_client.publish(MQTT_TOPICS['insights'], json.dumps(message))
        
    def collect_smartphone_data(self) -> UserBehaviorData:
        """Simulate smartphone data collection"""
        current_time = datetime.now().isoformat()
        
        # Simulate realistic app usage patterns
        apps = ['social_media', 'messaging', 'games', 'productivity', 'entertainment']
        app_usage = {app: np.random.exponential(0.5) for app in apps}
        
        return UserBehaviorData(
            timestamp=current_time,
            app_usage=app_usage,
            location=random.choice(['home', 'work', 'commute', 'leisure']),
            communication_count=np.random.poisson(5),
            touch_interactions=random.randint(50, 500),
            unlock_frequency=random.randint(10, 100),
            battery_level=random.uniform(20, 100),
            screen_time=np.random.exponential(0.3),  # Hours
            typing_speed=random.uniform(20, 80),  # WPM
            ambient_light=random.uniform(0, 1000),
            accelerometer=[random.uniform(-1, 1) for _ in range(3)],
            network_usage=np.random.exponential(100)  # MB
        )
    
    def preprocess_data(self, smartphone_data: UserBehaviorData, 
                       wearable_data: Dict, ambient_data: Dict) -> Dict[str, Any]:
        """Preprocess and combine data from all sources"""
        # Combine all data sources
        combined_data = {
            'smartphone': asdict(smartphone_data),
            'wearable': wearable_data,
            'ambient': ambient_data,
            'processed_timestamp': datetime.now().isoformat()
        }
        
        # Calculate derived metrics
        combined_data['derived_metrics'] = {
            'usage_intensity': self._calculate_usage_intensity(smartphone_data),
            'context_score': self._calculate_context_score(smartphone_data, ambient_data),
            'wellness_indicator': self._calculate_wellness_indicator(wearable_data)
        }
        
        return combined_data
    
    def _calculate_usage_intensity(self, data: UserBehaviorData) -> float:
        """Calculate usage intensity score (0-1)"""
        factors = [
            min(data.screen_time / 4.0, 1.0),  # Normalize to 4 hours max
            min(data.touch_interactions / 1000.0, 1.0),  # Normalize to 1000 touches max
            min(data.unlock_frequency / 200.0, 1.0)  # Normalize to 200 unlocks max
        ]
        return sum(factors) / len(factors)
    
    def _calculate_context_score(self, smartphone_data: UserBehaviorData, 
                                ambient_data: Dict) -> float:
        """Calculate contextual appropriateness score"""
        hour = int(smartphone_data.timestamp.split('T')[1].split(':')[0])
        
        # Penalize usage during sleep hours
        if 23 <= hour or hour <= 6:
            time_penalty = 0.8
        elif 7 <= hour <= 9 or 17 <= hour <= 19:  # Commute hours
            time_penalty = 0.3
        else:
            time_penalty = 0.0
        
        # Consider ambient factors
        light_factor = min(ambient_data['light_intensity'] / 500.0, 1.0)
        noise_factor = min(ambient_data['noise_level'] / 60.0, 1.0)
        
        context_score = 1.0 - (time_penalty + (1 - light_factor) * 0.2 + noise_factor * 0.1)
        return max(0.0, min(1.0, context_score))
    
    def _calculate_wellness_indicator(self, wearable_data: Dict) -> float:
        """Calculate wellness indicator based on wearable data"""
        stress_factor = 1.0 - wearable_data['stress_level']
        activity_scores = {'sedentary': 0.2, 'light': 0.5, 'moderate': 0.8, 'vigorous': 1.0}
        activity_factor = activity_scores[wearable_data['activity_level']]
        
        return (stress_factor + activity_factor) / 2.0
    
    def context_detection_with_edge_ai(self, processed_data: Dict) -> List[ContextualInsight]:
        """Perform context-aware overuse detection using edge AI"""
        insights = []
        
        # Add smartphone data to digital twin
        smartphone_data = UserBehaviorData(**processed_data['smartphone'])
        self.digital_twin.add_behavior_data(smartphone_data)
        
        # Get pattern-based insights from digital twin
        pattern_insights = self.digital_twin.detect_overuse_patterns()
        insights.extend(pattern_insights)
        
        # Real-time context analysis
        metrics = processed_data['derived_metrics']
        
        # High usage intensity detection
        if metrics['usage_intensity'] > 0.7:
            insights.append(ContextualInsight(
                pattern_type="high_intensity_usage",
                severity="medium",
                description=f"High usage intensity detected: {metrics['usage_intensity']:.2f}",
                recommendation="Consider taking a break from your device",
                confidence=0.75
            ))
        
        # Poor context usage detection
        if metrics['context_score'] < 0.3:
            insights.append(ContextualInsight(
                pattern_type="inappropriate_context",
                severity="high",
                description="Device usage in inappropriate context detected",
                recommendation="Consider environmental factors and timing of device use",
                confidence=0.8
            ))
        
        # Wellness impact detection
        if metrics['wellness_indicator'] < 0.4 and metrics['usage_intensity'] > 0.5:
            insights.append(ContextualInsight(
                pattern_type="wellness_impact",
                severity="high",
                description="Device usage may be impacting your wellness",
                recommendation="Take a break and engage in physical activity",
                confidence=0.85
            ))
        
        return insights
    
    def run_edge_processing_cycle(self) -> Dict[str, Any]:
        """Run one complete edge processing cycle"""
        # Collect data from all sources
        smartphone_data = self.collect_smartphone_data()
        wearable_data = self.wearable.generate_data()
        ambient_data = self.ambient_sensor.generate_data()
        
        # Preprocess data
        processed_data = self.preprocess_data(smartphone_data, wearable_data, ambient_data)
        
        # Store in buffer (temporary storage)
        self.data_buffer.append(processed_data)
        
        # Perform context detection
        insights = self.context_detection_with_edge_ai(processed_data)
        
        # Publish data via MQTT
        self.publish_processed_data(processed_data)
        if insights:
            self.publish_insights(insights)
        
        return {
            'processed_data': processed_data,
            'insights': [asdict(insight) for insight in insights],
            'buffer_size': len(self.data_buffer),
            'mqtt_status': self.mqtt_connected
        }

class IoTSystemManager:
    """Main system manager for the Context-Aware IoT System"""
    
    def __init__(self):
        self.edge_layer = EdgeComputingLayer()
        self.system_running = False
        
    def start_system(self):
        """Start the IoT system monitoring"""
        print("🚀 Starting Context-Aware IoT System for Technology Overuse Prevention")
        print("=" * 70)
        print("\n🏗️  SYSTEM ARCHITECTURE:")
        print("┌─────────────────┐    MQTT     ┌─────────────────┐")
        print("│  Digital Twin   │◄──────────►│   Edge Layer    │")
        print("│ (User Behavior) │   Broker    │ (Raspberry Pi)  │")
        print("└─────────────────┘             └─────────────────┘")
        print("         │                               │")
        print("         ▼                               ▼")
        print("   Behavior Data                 Context Detection")
        print("   Pattern Analysis              Real-time Insights")
        print("")
        
        self.system_running = True
        cycle_count = 0
        
        try:
            while self.system_running and cycle_count < 20:  # Run 20 cycles for demo
                cycle_count += 1
                print(f"\n📊 Processing Cycle #{cycle_count}")
                print("-" * 40)
                
                # Run edge processing
                result = self.edge_layer.run_edge_processing_cycle()
                
                # Display results
                self._display_cycle_results(result)
                
                # Wait before next cycle
                time.sleep(2)
                
        except KeyboardInterrupt:
            print("\n⏹️  System stopped by user")
        
        print(f"\n✅ System completed {cycle_count} processing cycles")
        self._display_system_summary()
    
    def _display_cycle_results(self, result: Dict):
        """Display results from a processing cycle"""
        data = result['processed_data']
        insights = result['insights']
        
        # Show connection architecture
        print("🔗 COMPONENT CONNECTIONS:")
        print(f"   📱 Digital Twin → MQTT → 🖥️  Edge Layer")
        print(f"   Digital Twin MQTT: {'🟢 Connected' if self.edge_layer.digital_twin.mqtt_connected else '🔴 Disconnected'}")
        print(f"   Edge Layer MQTT: {'🟢 Connected' if self.edge_layer.mqtt_connected else '🔴 Disconnected'}")
        
        # Show data flow
        if self.edge_layer.digital_twin.mqtt_connected and self.edge_layer.mqtt_connected:
            print("   📡 Data Flow: Digital Twin → MQTT Broker → Edge Layer ✅")
        else:
            print("   📡 Data Flow: Digital Twin ❌ MQTT Broker ❌ Edge Layer")
        
        # Show key metrics
        metrics = data['derived_metrics']
        print(f"\n📊 PROCESSING METRICS:")
        print(f"📱 Usage Intensity: {metrics['usage_intensity']:.2f}")
        print(f"🌍 Context Score: {metrics['context_score']:.2f}")
        print(f"💪 Wellness Indicator: {metrics['wellness_indicator']:.2f}")
        print(f"💾 Buffer Size: {result['buffer_size']}")
        
        # Show insights if any
        if insights:
            print("\n🔍 Detected Issues:")
            for insight in insights:
                severity_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}
                emoji = severity_emoji.get(insight['severity'], "⚪")
                print(f"  {emoji} {insight['pattern_type']}: {insight['description']}")
                print(f"     💡 {insight['recommendation']}")
        else:
            print("✅ No overuse patterns detected")
    
    def _display_system_summary(self):
        """Display system summary"""
        print("\n" + "=" * 70)
        print("📈 SYSTEM SUMMARY")
        print("=" * 70)
        
        twin = self.edge_layer.digital_twin
        print(f"📊 Total behavior data points collected: {len(twin.behavior_history)}")
        print(f"📱 Apps tracked: {len(twin.usage_patterns)}")
        print(f"📅 Days with data: {len(twin.daily_stats)}")
        
        if twin.usage_patterns:
            print("\n🏆 Most used apps:")
            sorted_apps = sorted(twin.usage_patterns.items(), 
                               key=lambda x: x[1]['total'], reverse=True)[:3]
            for app, stats in sorted_apps:
                print(f"  • {app}: {stats['total']:.1f} hours total, "
                      f"{stats['avg_session']:.1f} hours avg session")

def main():
    """Main function to run the IoT system"""
    print("🔧 Initializing Context-Aware IoT System...")
    print("📱 Digital Twin: Smartphone User Behavior Model")
    print("🖥️  Edge Layer: Raspberry Pi Simulation")
    print("⚡ Edge AI: Real-time Context Detection")
    print("📡 MQTT: Communication Layer for IoT Components")
    
    # Start MQTT broker for local testing
    print("🔌 Starting local MQTT broker...")
    broker = None
    try:
        from mqtt_broker import start_mqtt_broker
        broker = start_mqtt_broker()
        print("⏳ Waiting for MQTT broker to be ready...")
        time.sleep(5)  # Give broker more time to start
        print("✅ MQTT broker startup complete")
    except Exception as e:
        print(f"⚠️  Could not start MQTT broker: {e}")
        print("📡 Continuing without embedded broker (MQTT features may be limited)")
    
    print("🔄 Initializing IoT System components...")
    system = IoTSystemManager()
    print("🔗 Establishing MQTT connections...")
    time.sleep(2)  # Additional time for connections
    system.start_system()

if __name__ == "__main__":
    main()
