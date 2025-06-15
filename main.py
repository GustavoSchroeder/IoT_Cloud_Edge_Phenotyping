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
        """Detect late-night usage patterns with more sensitive thresholds"""
        late_night_usage = 0
        total_late_entries = 0

        for entry in data:
            hour = int(entry.timestamp.split('T')[1].split(':')[0])
            if hour >= 22 or hour <= 6:  # Expanded late night hours
                total_late_entries += 1
                if entry.screen_time > 0.2:  # Much lower threshold (12+ minutes)
                    late_night_usage += entry.screen_time

        # Much more sensitive detection
        if total_late_entries == 0:
            return False

        avg_late_usage = late_night_usage / max(total_late_entries, 1)
        return avg_late_usage > 0.3 or late_night_usage > 0.5  # Much lower thresholds

class WearableDevice:
    """Simulates wearable device data"""

    def generate_data(self) -> Dict[str, Any]:
        return {
            'heart_rate': random.randint(60, 120),
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

class CloudLayer:
    """Simulates cloud-based analytics and storage layer"""

    def __init__(self):
        self.analytics_buffer = deque(maxlen=500)  # Store more data in cloud
        self.global_patterns = {}
        self.cloud_insights = []

        # MQTT setup for Cloud Layer
        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"cloud_layer_{uuid.uuid4().hex[:8]}")
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_message = self._on_mqtt_message
        self.mqtt_client.on_subscribe = self._on_mqtt_subscribe
        self.mqtt_connected = False
        self._setup_mqtt_connection()

        # Start cloud analytics thread
        self.analytics_thread = threading.Thread(target=self._cloud_analytics_loop, daemon=True)
        self.analytics_thread.start()

    def _setup_mqtt_connection(self):
        """Setup MQTT connection for Cloud Layer with retry logic"""
        max_retries = 5
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                print(f"☁️  Cloud Layer attempting MQTT connection (attempt {attempt + 1}/{max_retries})")
                self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
                self.mqtt_client.loop_start()
                time.sleep(1)
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"⚠️  Cloud Layer MQTT connection attempt {attempt + 1} failed: {e}, retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                else:
                    print(f"⚠️  Cloud Layer MQTT connection failed after {max_retries} attempts: {e}")

    def _on_mqtt_subscribe(self, client, userdata, mid, granted_qos):
        """MQTT subscription callback"""
        print(f"☁️  Cloud Layer subscription confirmed: mid={mid}, qos={granted_qos}")

    def _on_mqtt_connect(self, client, userdata, flags, rc, properties=None):
        """MQTT connection callback"""
        if rc == 0:
            self.mqtt_connected = True
            print(f"☁️  Cloud Layer MQTT connected successfully")
            # Subscribe to edge processed data and insights
            client.subscribe(MQTT_TOPICS['edge_processed_data'])
            client.subscribe(MQTT_TOPICS['insights'])
            client.subscribe('iot/test/simple')  # Add test topic
            print(f"☁️  Cloud subscribed to topics: {MQTT_TOPICS['edge_processed_data']}, {MQTT_TOPICS['insights']}, iot/test/simple")
        else:
            print(f"⚠️  Cloud Layer MQTT connection failed with code {rc}")

    def _on_mqtt_message(self, client, userdata, msg):
        """Handle incoming MQTT messages from edge layer"""
        try:
            print(f"☁️  Cloud Layer received MQTT message on topic: {msg.topic}")
            message = json.loads(msg.payload.decode())
            if msg.topic == MQTT_TOPICS['edge_processed_data']:
                print(f"☁️  Cloud received processed data from Edge: {message['edge_id']}")
                self.analytics_buffer.append(message)
                print(f"☁️  Cloud buffer size now: {len(self.analytics_buffer)}")
                # Immediately trigger analytics when we receive data
                if len(self.analytics_buffer) >= 1:
                    print(f"☁️  Triggering immediate cloud analytics")
                    self._perform_cloud_analytics()
            elif msg.topic == MQTT_TOPICS['insights']:
                print(f"☁️  Cloud received insights from Edge: {len(message['insights'])} insights")
                self.cloud_insights.extend(message['insights'])
            elif msg.topic == 'iot/test/simple':
                print(f"☁️  Cloud received test message: {message}")
                # Create a simple analytics buffer entry for testing
                test_entry = {
                    'edge_id': message['edge_id'],
                    'timestamp': datetime.now().isoformat(),
                    'processed_data': {
                        'derived_metrics': {
                            'usage_intensity': message.get('usage_intensity', 0.5),
                            'context_score': 0.5
                        }
                    }
                }
                self.analytics_buffer.append(test_entry)
                print(f"☁️  Test message added to buffer, size now: {len(self.analytics_buffer)}")
        except Exception as e:
            print(f"⚠️  Cloud Layer error processing MQTT message: {e}")
            print(f"⚠️  Message topic: {msg.topic}, payload: {msg.payload[:100]}")
            print(f"⚠️  Raw payload: {msg.payload}")

    def _cloud_analytics_loop(self):
        """Perform cloud-level analytics on collected data"""
        while True:
            time.sleep(8)  # Check more frequently
            if len(self.analytics_buffer) >= 1:  # Start with any data
                print(f"☁️  Background cloud analytics check with {len(self.analytics_buffer)} data points")
                self._perform_cloud_analytics()

    def _perform_cloud_analytics(self):
        """Perform advanced cloud analytics"""
        if not self.analytics_buffer:
            return

        recent_data = list(self.analytics_buffer)[-10:]  # Last 10 edge reports

        # Calculate trend analytics
        usage_trends = []
        context_trends = []

        for data in recent_data:
            if 'processed_data' in data and 'derived_metrics' in data['processed_data']:
                metrics = data['processed_data']['derived_metrics']
                usage_trends.append(metrics['usage_intensity'])
                context_trends.append(metrics['context_score'])

        if usage_trends:
            avg_usage = sum(usage_trends) / len(usage_trends)
            avg_context = sum(context_trends) / len(context_trends)

            # Send cloud-level recommendations back to edge
            cloud_recommendation = {
                'timestamp': datetime.now().isoformat(),
                'cloud_id': 'aws_analytics_001',
                'trend_analysis': {
                    'avg_usage_intensity': avg_usage,
                    'avg_context_score': avg_context,
                    'data_points': len(usage_trends),
                    'recommendation': self._generate_cloud_recommendation(avg_usage, avg_context)
                }
            }

            # Publish cloud recommendations
            if self.mqtt_connected:
                self.mqtt_client.publish('iot/cloud/recommendations', json.dumps(cloud_recommendation))
                print(f"☁️  Cloud published trend analysis: Usage {avg_usage:.2f}, Context {avg_context:.2f}")

    def _generate_cloud_recommendation(self, avg_usage, avg_context):
        """Generate cloud-level recommendations based on trends"""
        if avg_usage > 0.7 and avg_context < 0.3:
            return "Critical: Consistent high usage in poor contexts detected across sessions"
        elif avg_usage > 0.6:
            return "Warning: Usage intensity trending upward - consider intervention"
        elif avg_context < 0.4:
            return "Alert: Poor context usage patterns detected - review usage timing"
        else:
            return "Normal: Usage patterns within acceptable ranges"

class EdgeComputingLayer:
    """Simulates Raspberry Pi edge computing layer"""

    def __init__(self):
        self.data_buffer = deque(maxlen=100)
        self.digital_twin = SmartphoneDigitalTwin("user_001")
        self.wearable = WearableDevice()
        self.ambient_sensor = AmbientSensor()
        self.context_detection_active = True
        self.cloud_recommendations = []

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
            # Subscribe to digital twin data and cloud recommendations
            client.subscribe(MQTT_TOPICS['digital_twin_data'])
            client.subscribe('iot/cloud/recommendations')
        else:
            print(f"⚠️  Edge Layer MQTT connection failed with code {rc}")

    def _on_mqtt_message(self, client, userdata, msg):
        """Handle incoming MQTT messages"""
        try:
            message = json.loads(msg.payload.decode())
            if msg.topic == MQTT_TOPICS['digital_twin_data']:
                print(f"🔄 Edge Layer received data from Digital Twin: {message['user_id']}")
            elif msg.topic == 'iot/cloud/recommendations':
                print(f"🔄 Edge Layer received cloud recommendation: {message['trend_analysis']['recommendation']}")
                self.cloud_recommendations.append(message)
                print(f"🔄 Edge recommendations count now: {len(self.cloud_recommendations)}")
        except Exception as e:
            print(f"⚠️  Error processing MQTT message: {e}")
            print(f"⚠️  Message topic: {msg.topic}, payload: {msg.payload[:100]}")

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
            topic = MQTT_TOPICS['edge_processed_data']
            payload = json.dumps(message)
            result = self.mqtt_client.publish(topic, payload)
            print(f"🖥️  Edge published processed data to topic: {topic}")
            print(f"🖥️  Message size: {len(payload)} bytes, Status: {result.rc}")

            # Also publish directly to a simpler topic for testing
            simple_message = {
                'edge_id': 'raspberry_pi_001',
                'buffer_size': len(processed_data),
                'usage_intensity': processed_data.get('derived_metrics', {}).get('usage_intensity', 0)
            }
            self.mqtt_client.publish('iot/test/simple', json.dumps(simple_message))
        else:
            print(f"⚠️  Edge MQTT not connected, cannot publish data")

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
        """Simulate smartphone data collection with more varied usage patterns for better overuse detection"""
        # Use variable time to simulate different usage patterns throughout the day
        base_time = datetime.now()
        # Add some randomness to simulate different times of day
        time_offset = random.randint(-12, 12)  # ±12 hours variation
        simulated_time = base_time + timedelta(hours=time_offset)
        current_time = simulated_time.isoformat()

        hour = simulated_time.hour

        # Create more extreme usage patterns to trigger overuse detection
        usage_pattern = random.choice(['light', 'moderate', 'heavy', 'extreme'])

        # Time-based realistic patterns with higher usage multipliers
        if 6 <= hour <= 9:  # Morning
            base_multiplier = random.uniform(0.5, 1.2)
            location_weights = {'home': 0.6, 'commute': 0.3, 'work': 0.1}
        elif 9 <= hour <= 17:  # Work hours
            base_multiplier = random.uniform(0.4, 0.9)
            location_weights = {'work': 0.7, 'home': 0.1, 'commute': 0.1, 'leisure': 0.1}
        elif 17 <= hour <= 22:  # Evening - prime time for overuse
            base_multiplier = random.uniform(0.8, 2.5)
            location_weights = {'home': 0.5, 'leisure': 0.3, 'commute': 0.2}
        else:  # Late night/early morning - should trigger late night usage
            base_multiplier = random.uniform(0.3, 1.5)  # Increased for late night overuse
            location_weights = {'home': 0.9, 'leisure': 0.1}

        # Apply usage pattern multiplier
        pattern_multipliers = {'light': 0.5, 'moderate': 1.0, 'heavy': 2.0, 'extreme': 3.5}
        usage_multiplier = base_multiplier * pattern_multipliers[usage_pattern]

        # Choose location based on time
        location = random.choices(
            list(location_weights.keys()), 
            weights=list(location_weights.values())
        )[0]

        # Simulate more intense app usage patterns
        apps = ['social_media', 'messaging', 'games', 'productivity', 'entertainment']
        app_usage = {}
        for app in apps:
            base_usage = np.random.exponential(0.8)  # Increased base usage
            if app == 'productivity' and 9 <= hour <= 17:
                base_usage *= 2.5  # More productivity apps during work
            elif app in ['social_media', 'entertainment'] and (17 <= hour <= 22):
                base_usage *= 2.0  # Much more entertainment in evening
            elif app == 'games' and (22 <= hour or hour <= 2):
                base_usage *= 1.5  # Some late night gaming
            elif app == 'social_media' and (22 <= hour or hour <= 2):
                base_usage *= 2.0  # Late night social media scrolling
            app_usage[app] = base_usage * usage_multiplier

        # Generate higher screen time values
        screen_time_base = np.random.exponential(1.2) * usage_multiplier  # Increased base screen time
        if usage_pattern == 'extreme':
            screen_time_base *= 2.0
        elif usage_pattern == 'heavy':
            screen_time_base *= 1.5

        return UserBehaviorData(
            timestamp=current_time,
            app_usage=app_usage,
            location=location,
            communication_count=max(1, int(np.random.poisson(8) * usage_multiplier)),  # Increased
            touch_interactions=random.randint(int(100 * usage_multiplier), int(800 * usage_multiplier)),  # Much higher
            unlock_frequency=random.randint(int(20 * usage_multiplier), int(150 * usage_multiplier)),  # Higher
            battery_level=random.uniform(15, 95),
            screen_time=max(0.1, screen_time_base),
            typing_speed=random.uniform(15, 90),
            ambient_light=random.uniform(10, 800),
            accelerometer=[random.uniform(-0.8, 0.8) for _ in range(3)],
            network_usage=max(5, np.random.exponential(150) * usage_multiplier)  # Increased
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
        """Calculate usage intensity score (0-1) with more sensitive thresholds"""
        factors = [
            min(data.screen_time / 2.0, 1.0),  # Normalize to 2 hours max (more sensitive)
            min(data.touch_interactions / 600.0, 1.0),  # Normalize to 600 touches max (lower threshold)
            min(data.unlock_frequency / 100.0, 1.0),  # Normalize to 100 unlocks max (lower threshold)
            min(sum(data.app_usage.values()) / 3.0, 1.0)  # Add app usage factor
        ]
        return sum(factors) / len(factors)

    def _calculate_context_score(self, smartphone_data: UserBehaviorData, 
                                ambient_data: Dict) -> float:
        """Calculate contextual appropriateness score with more aggressive penalties"""
        hour = int(smartphone_data.timestamp.split('T')[1].split(':')[0])

        # More aggressive time-based scoring
        if 23 <= hour or hour <= 5:  # Deep sleep hours - much higher penalty
            time_penalty = random.uniform(0.7, 1.0)
        elif hour == 6 or hour == 22:  # Transition hours
            time_penalty = random.uniform(0.4, 0.7)
        elif 7 <= hour <= 9 or 17 <= hour <= 19:  # Commute hours
            time_penalty = random.uniform(0.2, 0.5)
        else:  # Normal hours
            time_penalty = random.uniform(0.0, 0.3)

        # More aggressive location-based context
        location_penalty = 0.0
        if smartphone_data.location == 'work' and hour > 18:
            location_penalty = 0.5
        elif smartphone_data.location == 'leisure' and 9 <= hour <= 17:
            location_penalty = 0.4

        # Consider ambient factors with more variation
        light_factor = min(ambient_data['light_intensity'] / 500.0, 1.0)  # Lower threshold
        noise_factor = ambient_data['noise_level'] / 70.0  # Lower threshold

        # Add usage intensity to context score
        total_app_usage = sum(smartphone_data.app_usage.values())
        usage_penalty = min(total_app_usage / 4.0, 0.3)  # Penalty for high app usage

        # Add some randomness but weighted towards penalties
        random_factor = random.uniform(-0.05, 0.15)  # Slightly biased towards lower scores

        context_score = 1.0 - (time_penalty + location_penalty + usage_penalty + 
                              (1 - light_factor) * 0.2 + noise_factor * 0.15 + random_factor)
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

        # Real-time context analysis with dynamic thresholds
        metrics = processed_data['derived_metrics']
        smartphone_data = processed_data['smartphone']
        hour = int(smartphone_data['timestamp'].split('T')[1].split(':')[0])

        # Much lower and more realistic thresholds
        usage_threshold = 0.4 if 9 <= hour <= 17 else 0.3  # Much lower thresholds
        context_threshold = 0.6 if smartphone_data['location'] == 'work' else 0.5  # Higher threshold for flagging

        # High usage intensity detection (much more sensitive)
        if metrics['usage_intensity'] > usage_threshold:
            severity = "high" if metrics['usage_intensity'] > 0.6 else "medium"
            insights.append(ContextualInsight(
                pattern_type="high_intensity_usage",
                severity=severity,
                description=f"High usage intensity detected: {metrics['usage_intensity']:.2f}",
                recommendation="Consider taking a break from your device",
                confidence=min(0.95, 0.6 + metrics['usage_intensity'] * 0.3)
            ))

        # Poor context usage detection (more sensitive)
        if metrics['context_score'] < context_threshold:
            # Flag various inappropriate contexts
            if (hour >= 23 or hour <= 5) and metrics['usage_intensity'] > 0.1:  # Much lower threshold
                insights.append(ContextualInsight(
                    pattern_type="inappropriate_context",
                    severity="high",
                    description=f"Device usage in inappropriate context detected",
                    recommendation="Consider environmental factors and timing of device use",
                    confidence=0.8
                ))
            elif smartphone_data['location'] == 'work' and hour > 17:  # Earlier work boundary
                insights.append(ContextualInsight(
                    pattern_type="work_life_balance",
                    severity="medium",
                    description="Extended work-related device usage detected",
                    recommendation="Try to maintain work-life boundaries",
                    confidence=0.7
                ))
            elif metrics['context_score'] < 0.3:  # Very low context score
                insights.append(ContextualInsight(
                    pattern_type="inappropriate_context",
                    severity="medium",
                    description="Device usage in inappropriate context detected",
                    recommendation="Consider environmental factors and timing of device use",
                    confidence=0.75
                ))

        # Wellness impact detection (more specific)
        if metrics['wellness_indicator'] < 0.3 and metrics['usage_intensity'] > 0.6:
            insights.append(ContextualInsight(
                pattern_type="wellness_impact",
                severity="high",
                description="Device usage may be impacting your wellness",
                recommendation="Take a break and engage in physical activity",
                confidence=0.85
            ))

        # Add screen time overuse detection
        smartphone_data_obj = UserBehaviorData(**processed_data['smartphone'])
        if smartphone_data_obj.screen_time > 1.5:  # More than 1.5 hours in one session
            insights.append(ContextualInsight(
                pattern_type="long_session",
                severity="high" if smartphone_data_obj.screen_time > 3.0 else "medium",
                description=f"Extended screen time session: {smartphone_data_obj.screen_time:.1f} hours",
                recommendation="Take regular breaks to avoid eye strain and overuse",
                confidence=0.9
            ))

        # App usage overuse detection
        total_app_usage = sum(smartphone_data_obj.app_usage.values())
        if total_app_usage > 2.0:  # More than 2 hours total app usage
            insights.append(ContextualInsight(
                pattern_type="excessive_app_usage",
                severity="high" if total_app_usage > 4.0 else "medium",
                description=f"High app usage detected: {total_app_usage:.1f} hours",
                recommendation="Consider setting app time limits and taking breaks",
                confidence=0.85
            ))

        # Touch interaction overuse
        if smartphone_data_obj.touch_interactions > 500:
            insights.append(ContextualInsight(
                pattern_type="excessive_interactions",
                severity="medium",
                description=f"High touch interactions: {smartphone_data_obj.touch_interactions}",
                recommendation="Take breaks to avoid repetitive strain",
                confidence=0.8
            ))

        # Reduced positive feedback (only 10% chance and stricter requirements)
        if (metrics['usage_intensity'] < 0.15 and 
            metrics['context_score'] > 0.8 and 
            metrics['wellness_indicator'] > 0.8 and 
            total_app_usage < 0.5 and
            random.random() < 0.1):  # Only 10% chance to show positive feedback
            insights.append(ContextualInsight(
                pattern_type="healthy_usage",
                severity="low",
                description="Balanced device usage detected",
                recommendation="Keep up the good usage habits!",
                confidence=0.9
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
        self.cloud_layer = CloudLayer()
        self.system_running = False

    def start_system(self):
        """Start the IoT system monitoring"""
        print("🚀 Starting Context-Aware IoT System for Technology Overuse Prevention")
        print("=" * 70)
        print("\n🏗️  SYSTEM ARCHITECTURE:")
        print("┌─────────────────┐    MQTT     ┌─────────────────┐    MQTT     ┌─────────────────┐")
        print("│  Digital Twin   │◄──────────►│   Edge Layer    │◄──────────►│   Cloud Layer   │")
        print("│ (User Behavior) │   Broker    │ (Raspberry Pi)  │   Broker    │ (AWS Analytics) │")
        print("└─────────────────┘             └─────────────────┘             └─────────────────┘")
        print("         │                               │                               │")
        print("         ▼                               ▼                               ▼")
        print("   Behavior Data                 Context Detection              Trend Analysis")
        print("   Pattern Analysis              Real-time Insights            Global Patterns")
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
                time.sleep(5)

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
        print(f"   📱 Digital Twin → MQTT → 🖥️  Edge Layer → MQTT → ☁️  Cloud Layer")
        print(f"   Digital Twin MQTT: {'🟢 Connected' if self.edge_layer.digital_twin.mqtt_connected else '🔴 Disconnected'}")
        print(f"   Edge Layer MQTT: {'🟢 Connected' if self.edge_layer.mqtt_connected else '🔴 Disconnected'}")
        print(f"   Cloud Layer MQTT: {'🟢 Connected' if self.cloud_layer.mqtt_connected else '🔴 Disconnected'}")

        # Show data flow
        all_connected = (self.edge_layer.digital_twin.mqtt_connected and 
                        self.edge_layer.mqtt_connected and 
                        self.cloud_layer.mqtt_connected)
        if all_connected:
            print("   📡 Data Flow: Digital Twin → Edge Layer → Cloud Layer ✅")
        else:
            print("   📡 Data Flow: Components not fully connected ❌")

        # Show key metrics
        metrics = data['derived_metrics']
        print(f"\n📊 PROCESSING METRICS:")
        print(f"📱 Usage Intensity: {metrics['usage_intensity']:.2f}")
        print(f"🌍 Context Score: {metrics['context_score']:.2f}")
        print(f"💪 Wellness Indicator: {metrics['wellness_indicator']:.2f}")
        print(f"💾 Edge Buffer Size: {result['buffer_size']}")
        print(f"☁️  Cloud Buffer Size: {len(self.cloud_layer.analytics_buffer)}")
        print(f"🔄 Cloud Recommendations: {len(self.edge_layer.cloud_recommendations)}")

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
        print(f"☁️  Cloud analytics processed: {len(self.cloud_layer.analytics_buffer)} data points")
        print(f"🤖 Cloud insights generated: {len(self.cloud_layer.cloud_insights)}")
        print(f"🔄 Edge-Cloud interactions: {len(self.edge_layer.cloud_recommendations)}")

        if twin.usage_patterns:
            print("\n🏆 Most used apps:")
            sorted_apps = sorted(twin.usage_patterns.items(), 
                               key=lambda x: x[1]['total'], reverse=True)[:3]
            for app, stats in sorted_apps:
                print(f"  • {app}: {stats['total']:.1f} hours total, "
                      f"{stats['avg_session']:.1f} hours avg session")

        if self.edge_layer.cloud_recommendations:
            print("\n☁️  Latest Cloud Recommendation:")
            latest = self.edge_layer.cloud_recommendations[-1]
            print(f"  • {latest['trend_analysis']['recommendation']}")

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