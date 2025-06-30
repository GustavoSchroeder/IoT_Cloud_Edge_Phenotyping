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
    """Data Structure for user behavior tracking - digital phenotyping"""
    timestamp: str
    app_usage: Dict[str, float]  # dictionary app_name: minutes_used
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

# MQTT CONFIGURATION
MQTT_BROKER = "127.0.0.1"  # Local broker 
MQTT_PORT = 1883 # Default port for MQTT
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
        self.behavior_history = deque(maxlen=5000)  # Keep last x data points
        self.usage_patterns = {}
        self.daily_stats = defaultdict(list)
        self.overuse_threshold = 5.0  # limithours per day
        self.session_threshold = 1.0  # limithours per session

        # MQTT setup for mock Digital Twin
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
        """Publish behavior data using MQTT"""
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

        # Smartphone app use pattern
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

        # Analyze screen time
        today = datetime.now().strftime('%Y-%m-%d')
        if today in self.daily_stats:
            daily_total = sum(self.daily_stats[today])
            if daily_total > self.overuse_threshold:
                insights.append(ContextualInsight(
                    pattern_type="daily_overuse",
                    severity="high" if daily_total > 10 else "medium",
                    description=f"Daily screen time: {daily_total:.1f} hours exceeds recommended limit",
                    recommendation="Take regular breaks and set app time limits",
                    confidence=0.9 #example placeholder for ai
                ))

        # Analyze session patterns
        continuous_sessions = self._detect_long_sessions(recent_data)
        if continuous_sessions:
            insights.append(ContextualInsight(
                pattern_type="long_sessions",
                severity="medium",
                description=f"Detected {len(continuous_sessions)} extended usage sessions",
                recommendation="Set session reminders and take breaks every hour",
                confidence=0.8 #example placeholder for ai
            ))

        # Analyze late-night usage
        late_night_usage = self._detect_late_night_usage(recent_data)
        if late_night_usage:
            insights.append(ContextualInsight(
                pattern_type="late_night_usage",
                severity="high",
                description="Excessive late-night device usage detected",
                recommendation="Enable sleep mode and avoid screens before bedtime",
                confidence=0.85 #example placeholder for ai
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
            'light_intensity': random.uniform(0, 1000),  # light intensity
            'temperature': random.uniform(18, 26),  # Celsius
            'humidity': random.uniform(30, 70)  # percentage
        }

class SmartHomeManager:
    """Manages smart home device interactions and interventions"""
    
    def __init__(self):
        self.available_devices = {
            'alexa': {
                'status': 'active',
                'capabilities': ['voice_control', 'notifications', 'ambient_sound'],
                'current_mode': 'normal'
            },
            'smart_bulbs': {
                'status': 'active',
                'capabilities': ['brightness_control', 'color_control', 'schedule'],
                'current_mode': 'normal'
            },
            'smart_thermostat': {
                'status': 'active',
                'capabilities': ['temperature_control', 'schedule', 'presence_detection'],
                'current_mode': 'normal'
            }
        }
        self.device_states = {}
        self.intervention_history = []

    def get_device_interventions(self, usage_pattern: str, severity: str) -> List[Dict]:
        """Generate smart home device interventions based on usage patterns"""
        interventions = []
        
        if usage_pattern == 'late_night_usage':
            interventions.extend([
                {
                    'device': 'smart_bulbs',
                    'action': 'enable_night_mode',
                    'description': 'Activate night mode with reduced blue light',
                    'settings': {'brightness': 30, 'color_temp': 'warm'}
                },
                {
                    'device': 'alexa',
                    'action': 'enable_sleep_mode',
                    'description': 'Activate sleep mode with ambient sounds',
                    'settings': {'mode': 'sleep', 'ambient_sound': 'white_noise'}
                }
            ])
        
        elif usage_pattern == 'high_intensity_usage':
            interventions.extend([
                {
                    'device': 'smart_bulbs',
                    'action': 'adjust_lighting',
                    'description': 'Adjust lighting to reduce eye strain',
                    'settings': {'brightness': 70, 'color_temp': 'neutral'}
                },
                {
                    'device': 'alexa',
                    'action': 'schedule_break_reminder',
                    'description': 'Set up voice reminders for breaks',
                    'settings': {'interval': '30min', 'message': 'Time for a short break'}
                }
            ])
        
        elif usage_pattern == 'inappropriate_context':
            interventions.extend([
                {
                    'device': 'alexa',
                    'action': 'context_aware_notification',
                    'description': 'Send voice notification about context',
                    'settings': {'message': 'Consider your current environment'}
                },
                {
                    'device': 'smart_bulbs',
                    'action': 'attention_alert',
                    'description': 'Use lighting to indicate attention needed',
                    'settings': {'pattern': 'gentle_pulse', 'color': 'amber'}
                }
            ])
        
        elif usage_pattern == 'wellness_impact':
            interventions.extend([
                {
                    'device': 'smart_thermostat',
                    'action': 'optimize_environment',
                    'description': 'Adjust temperature for better focus',
                    'settings': {'temperature': 22, 'mode': 'comfort'}
                },
                {
                    'device': 'alexa',
                    'action': 'wellness_reminder',
                    'description': 'Schedule wellness check-ins',
                    'settings': {'interval': '1hour', 'message': 'Time for a wellness check'}
                }
            ])

        return interventions

    def apply_intervention(self, intervention: Dict) -> bool:
        """Apply a smart home device intervention"""
        try:
            device = intervention['device']
            if device in self.available_devices:
                self.device_states[device] = intervention['settings']
                self.intervention_history.append({
                    'timestamp': datetime.now().isoformat(),
                    'intervention': intervention
                })
                return True
        except Exception as e:
            print(f"⚠️ Error applying smart home intervention: {e}")
        return False

    def get_intervention_summary(self) -> Dict:
        """Get summary of applied interventions"""
        return {
            'total_interventions': len(self.intervention_history),
            'active_devices': len(self.device_states),
            'recent_interventions': self.intervention_history[-5:] if self.intervention_history else []
        }

class CloudLayer:
    """Simulates cloud-based analytics and storage layer"""

    def __init__(self):
        self.analytics_buffer = deque(maxlen=500)
        self.global_patterns = {}
        self.cloud_insights = []
        self.smart_home = SmartHomeManager()  # Add newq SmartHomeManager instance

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

    def _on_mqtt_subscribe(self, client, userdata, mid, granted_qos, properties=None):
        """MQTT subscription callback"""
        print(f"☁️  Cloud Layer subscription confirmed: mid={mid}, qos={granted_qos}")

    def _on_mqtt_connect(self, client, userdata, flags, rc, properties=None):
        """MQTT connection callback"""
        if rc == 0:
            self.mqtt_connected = True
            print(f"☁️  Cloud Layer MQTT connected successfully")
            # Subscribe to edge processed data and insights with multiple topic patterns
            topics_to_subscribe = [
                MQTT_TOPICS['edge_processed_data'],
                MQTT_TOPICS['insights'], 
                'iot/test/simple',
                'iot/edge/#',  # Wildcard for all edge topics
                'iot/+/processed',  # Any processed data
                '#'  # Subscribe to all topics for debugging
            ]
            
            for topic in topics_to_subscribe:
                result = client.subscribe(topic)
                print(f"☁️  Cloud subscribed to topic: {topic}, result: {result}")
                
            print(f"☁️  Cloud Layer ready to receive data from {len(topics_to_subscribe)} topic patterns")
        else:
            print(f"⚠️  Cloud Layer MQTT connection failed with code {rc}")

    def _on_mqtt_message(self, client, userdata, msg):
        """Handle incoming MQTT messages from edge layer"""
        try:
            print(f"☁️  Cloud Layer received MQTT message on topic: {msg.topic}, payload size: {len(msg.payload)}")
            time.sleep(0.6)
            
            # Add raw message debugging
            raw_payload = msg.payload.decode()
            # print(f"☁️  Raw message: {raw_payload[:200]}...")
            
            message = json.loads(raw_payload)
            
            if msg.topic == MQTT_TOPICS['edge_processed_data']:
                print(f"☁️  Cloud received processed data from Edge: {message['edge_id']}")
                self.analytics_buffer.append(message)
                print(f"☁️  Cloud buffer size now: {len(self.analytics_buffer)}")
                # Immediately trigger analytics when we receive data
                print(f"☁️  Triggering immediate cloud analytics")
                self._perform_cloud_analytics()
                
            elif msg.topic == MQTT_TOPICS['insights']:
                print(f"☁️  Cloud received insights from Edge: {len(message['insights'])} insights")
                self.cloud_insights.extend(message['insights'])
                
                # Generate targeted recommendations based on detected problematic behaviors
                print(f"☁️  Analyzing insights for targeted recommendations...")
                self._generate_behavioral_recommendations(message['insights'])
                
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
                
            # Handle any topic that contains data
            elif 'processed' in msg.topic or 'edge' in msg.topic:
                print(f"☁️  Cloud received alternate topic message: {msg.topic}")
                if 'edge_id' in message:
                    self.analytics_buffer.append(message)
                    print(f"☁️  Added to buffer via alternate topic, size now: {len(self.analytics_buffer)}")
                    self._perform_cloud_analytics()
                    
        except Exception as e:
            print(f"⚠️  Cloud Layer error processing MQTT message: {e}")
            print(f"⚠️  Message topic: {msg.topic}, payload: {msg.payload[:100]}")
            print(f"⚠️  Exception details: {type(e).__name__}: {str(e)}")
            # Try to add some data anyway for demonstration
            try:
                fallback_entry = {
                    'edge_id': 'fallback_001',
                    'timestamp': datetime.now().isoformat(),
                    'processed_data': {
                        'derived_metrics': {
                            'usage_intensity': 0.5,
                            'context_score': 0.5
                        }
                    }
                }
                self.analytics_buffer.append(fallback_entry)
                print(f"☁️  Added fallback data to buffer, size now: {len(self.analytics_buffer)}")
            except:
                pass

    def _cloud_analytics_loop(self):
        """Perform cloud-level analytics on collected data"""
        loop_count = 0
        while True:
            time.sleep(8)  # Check more frequently
            loop_count += 1
            
            print(f"☁️  Background analytics loop #{loop_count}, buffer size: {len(self.analytics_buffer)}")
            
            if len(self.analytics_buffer) >= 1:  # Start with any data
                print(f"☁️  Background cloud analytics check with {len(self.analytics_buffer)} data points")
                self._perform_cloud_analytics()
            else:
                # If no data received after several loops, create sample data for demonstration
                if loop_count % 3 == 0:  # Every 3rd loop (24 seconds)
                    print(f"☁️  No data received, creating sample analytics data for demonstration")
                    sample_entry = {
                        'edge_id': f'sample_edge_{loop_count}',
                        'timestamp': datetime.now().isoformat(),
                        'processed_data': {
                            'derived_metrics': {
                                'usage_intensity': random.uniform(0.3, 0.8),
                                'context_score': random.uniform(0.2, 0.7)
                            }
                        }
                    }
                    self.analytics_buffer.append(sample_entry)
                    print(f"☁️  Sample data added, buffer size now: {len(self.analytics_buffer)}")
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
                time.sleep(0.5)

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
    
    def _generate_behavioral_recommendations(self, insights):
        """Generate targeted recommendations based on specific behavioral insights"""
        if not insights:
            return
        
        # Analyze patterns in the insights
        pattern_counts = {}
        severity_counts = {'high': 0, 'medium': 0, 'low': 0}
        
        for insight in insights:
            pattern_type = insight['pattern_type']
            severity = insight['severity']
            
            pattern_counts[pattern_type] = pattern_counts.get(pattern_type, 0) + 1
            severity_counts[severity] += 1
        
        # Generate cloud-level behavioral recommendations
        cloud_behavioral_recommendations = []
        
        # Critical overuse patterns
        if 'daily_overuse' in pattern_counts:
            cloud_behavioral_recommendations.append({
                'priority': 'critical',
                'intervention': 'automated_daily_limit',
                'action': 'Set automatic daily screen time limit to 4 hours',
                'reason': f"Daily overuse detected {pattern_counts['daily_overuse']} times"
            })
        
        # Late night usage interventions
        if 'late_night_usage' in pattern_counts:
            cloud_behavioral_recommendations.append({
                'priority': 'high',
                'intervention': 'sleep_mode_automation',
                'action': 'Enable automatic Do Not Disturb from 10 PM to 7 AM',
                'reason': f"Late night usage detected {pattern_counts['late_night_usage']} times"
            })
            
            # Add smart home interventions for late night usage
            smart_home_interventions = self.smart_home.get_device_interventions('late_night_usage', 'high')
            for intervention in smart_home_interventions:
                cloud_behavioral_recommendations.append({
                    'priority': 'high',
                    'intervention': 'smart_home_automation',
                    'action': f"Smart Home: {intervention['description']}",
                    'reason': f"Late night usage detected - {intervention['device']} intervention"
                })
                self.smart_home.apply_intervention(intervention)
        
        # Context-aware interventions
        if 'inappropriate_context' in pattern_counts:
            cloud_behavioral_recommendations.append({
                'priority': 'medium',
                'intervention': 'context_awareness',
                'action': 'Enable location-based app restrictions and notification filtering',
                'reason': f"Inappropriate context usage detected {pattern_counts['inappropriate_context']} times"
            })
            
            # Add smart home interventions for context awareness
            smart_home_interventions = self.smart_home.get_device_interventions('inappropriate_context', 'medium')
            for intervention in smart_home_interventions:
                cloud_behavioral_recommendations.append({
                    'priority': 'medium',
                    'intervention': 'smart_home_automation',
                    'action': f"Smart Home: {intervention['description']}",
                    'reason': f"Context awareness - {intervention['device']} intervention"
                })
                self.smart_home.apply_intervention(intervention)
        
        # High intensity usage interventions
        if 'high_intensity_usage' in pattern_counts:
            cloud_behavioral_recommendations.append({
                'priority': 'high',
                'intervention': 'break_reminders',
                'action': 'Set mandatory 15-minute breaks every 90 minutes of use',
                'reason': f"High intensity usage detected {pattern_counts['high_intensity_usage']} times"
            })
            
            # Add smart home interventions for high intensity usage
            smart_home_interventions = self.smart_home.get_device_interventions('high_intensity_usage', 'high')
            for intervention in smart_home_interventions:
                cloud_behavioral_recommendations.append({
                    'priority': 'high',
                    'intervention': 'smart_home_automation',
                    'action': f"Smart Home: {intervention['description']}",
                    'reason': f"High intensity usage - {intervention['device']} intervention"
                })
                self.smart_home.apply_intervention(intervention)
        
        # Wellness impact interventions
        if 'wellness_impact' in pattern_counts:
            cloud_behavioral_recommendations.append({
                'priority': 'high',
                'intervention': 'wellness_integration',
                'action': 'Integrate with fitness apps and suggest physical activities during breaks',
                'reason': 'Device usage impacting wellness indicators'
            })
            
            # Add smart home interventions for wellness
            smart_home_interventions = self.smart_home.get_device_interventions('wellness_impact', 'high')
            for intervention in smart_home_interventions:
                cloud_behavioral_recommendations.append({
                    'priority': 'high',
                    'intervention': 'smart_home_automation',
                    'action': f"Smart Home: {intervention['description']}",
                    'reason': f"Wellness impact - {intervention['device']} intervention"
                })
                self.smart_home.apply_intervention(intervention)

        # Generate overall behavioral strategy
        total_high_severity = severity_counts['high']
        total_issues = sum(severity_counts.values())
        
        if total_high_severity >= 3:
            intervention_level = 'intensive'
            strategy = 'Implement comprehensive digital wellness program with strict limits'
        elif total_high_severity >= 1:
            intervention_level = 'moderate'
            strategy = 'Apply targeted interventions with gentle reminders'
        else:
            intervention_level = 'light'
            strategy = 'Monitor usage patterns and provide awareness feedback'
        
        # Send comprehensive behavioral recommendation
        behavioral_recommendation = {
            'timestamp': datetime.now().isoformat(),
            'cloud_id': 'aws_behavioral_analytics_001',
            'behavioral_analysis': {
                'total_issues_detected': total_issues,
                'pattern_breakdown': pattern_counts,
                'severity_distribution': severity_counts,
                'intervention_level': intervention_level,
                'overall_strategy': strategy,
                'specific_interventions': cloud_behavioral_recommendations,
                'urgency_score': min(total_high_severity * 0.3 + total_issues * 0.1, 1.0),
                'smart_home_summary': self.smart_home.get_intervention_summary()
            }
        }
        
        # Publish behavioral recommendations via MQTT
        if self.mqtt_connected:
            self.mqtt_client.publish('iot/cloud/behavioral_recommendations', json.dumps(behavioral_recommendation))
            print(f"☁️  Cloud published behavioral recommendations: {intervention_level} intervention level")
            print(f"☁️  Recommended {len(cloud_behavioral_recommendations)} specific interventions")
            
            # Also send summary to edge layer
            summary_recommendation = {
                'timestamp': datetime.now().isoformat(),
                'intervention_level': intervention_level,
                'primary_concern': max(pattern_counts.items(), key=lambda x: x[1])[0] if pattern_counts else 'none',
                'recommended_action': cloud_behavioral_recommendations[0]['action'] if cloud_behavioral_recommendations else 'Continue monitoring',
                'urgency_score': min(total_high_severity * 0.3 + total_issues * 0.1, 1.0),
                'smart_home_interventions': self.smart_home.get_intervention_summary()
            }
            
            self.mqtt_client.publish('iot/cloud/recommendations', json.dumps(summary_recommendation))
            print(f"☁️  Cloud sent intervention summary: {summary_recommendation['primary_concern']} (urgency: {summary_recommendation['urgency_score']:.2f})")

#edge class - raspberry pi simulator
class EdgeComputingLayer:
    """Simulates Raspberry Pi edge computing layer"""

    def __init__(self):
        self.data_buffer = deque(maxlen=100)
        self.digital_twin = SmartphoneDigitalTwin("user_001") #simulate 1 one user
        self.wearable = WearableDevice()
        self.ambient_sensor = AmbientSensor()
        self.context_detection_active = True
        self.cloud_recommendations = []
        self.simulated_day = datetime.now().date()  # Track simulated day

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
                print(f"RaspberryPI - Edge Layer attempting MQTT connection (attempt {attempt + 1}/{max_retries})")
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
            client.subscribe('iot/cloud/behavioral_recommendations')
        else:
            print(f"⚠️  Edge Layer MQTT connection failed with code {rc}")

    def _on_mqtt_message(self, client, userdata, msg):
        """Handle incoming MQTT messages"""
        try:
            message = json.loads(msg.payload.decode())
            if msg.topic == MQTT_TOPICS['digital_twin_data']:
                print(f"🔄 Edge Layer received data from Digital Twin: {message['user_id']}")
            elif msg.topic == 'iot/cloud/recommendations':
                if 'trend_analysis' in message:
                    print(f"🔄 Edge Layer received cloud trend recommendation: {message['trend_analysis']['recommendation']}")
                else:
                    print(f"🔄 Edge Layer received cloud intervention: {message.get('recommended_action', 'Unknown action')}")
                self.cloud_recommendations.append(message)
                print(f"🔄 Edge recommendations count now: {len(self.cloud_recommendations)}")
            elif msg.topic == 'iot/cloud/behavioral_recommendations':
                print(f"🔄 Edge Layer received behavioral recommendations from Cloud")
                behavioral_analysis = message['behavioral_analysis']
                print(f"🔄 Intervention level: {behavioral_analysis['intervention_level']}")
                print(f"🔄 Total issues: {behavioral_analysis['total_issues_detected']}")
                print(f"🔄 Urgency score: {behavioral_analysis['urgency_score']:.2f}")
                if behavioral_analysis['specific_interventions']:
                    print(f"🔄 Top intervention: {behavioral_analysis['specific_interventions'][0]['action']}")
                self.cloud_recommendations.append(message)
        except Exception as e:
            print(f"⚠️  Error processing MQTT message: {e}")
            print(f"⚠️  Message topic: {msg.topic}, payload: {msg.payload[:100]}")

    # provide a regular status update from the edge device to the rest of the system
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

            # TEST - try publish directly to a simpler topic for testing
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

    #main method for simulation
    def collect_smartphone_data(self) -> UserBehaviorData: # return userBehaviorData
        """Simulate a full day's smartphone data with realistic app usage patterns"""
        
        # Use the day for the timestamp
        simulated_time = datetime.combine(self.simulated_day, datetime.min.time())
        current_time = simulated_time.isoformat()
        weekday = simulated_time.weekday()  
        is_weekend = weekday >= 5 # 0=Monday - 6=Sunday

        # App usage pattern weights
        apps = ['social_media', 'messaging', 'games', 'productivity', 'entertainment'] #few apps i tought for the prototype -- only testing
        app_weights = {
            'social_media': 3 if is_weekend else 2,
            'messaging': 2,
            'games': 2 if is_weekend else 1.2,
            'productivity': 1 if is_weekend else 3,
            'entertainment': 3 if is_weekend else 1.5
        }
        total_weight = sum(app_weights[app] for app in apps)

        # Distribute 24 hours among apps
        total_app_time = random.uniform(6, 14) if is_weekend else random.uniform(5, 12)  # realistic total app time
        app_usage = {}
        remaining_time = total_app_time
        for i, app in enumerate(apps):
            if i == len(apps) - 1:
                usage = max(0, remaining_time)  # assign the rest to the last app
            else:
                max_for_app = min(remaining_time, total_app_time * app_weights[app] / total_weight * random.uniform(0.7, 1.3))
                usage = max(0, min(max_for_app, remaining_time))
                remaining_time -= usage
            app_usage[app] = usage

        # Screen time: sum of app usage + a small random non-app time, capped at 24
        non_app_time = random.uniform(0.2, 1.5)  # e.g., notifications, lock screen
        screen_time = min(24.0, sum(app_usage.values()) + non_app_time)

        # Location: for the sake of prototype - more likely 'home' on weekends, 'work' on weekdays
        location = random.choices(
            ['home', 'work', 'leisure', 'commute'],
            weights=[0.7, 0.1, 0.15, 0.05] if is_weekend else [0.4, 0.4, 0.1, 0.1]
        )[0]

        # other metrics scaled to daily realistic ranges
        communication_count = random.randint(10, 60) if is_weekend else random.randint(20, 80)
        touch_interactions = random.randint(800, 3500)
        unlock_frequency = random.randint(30, 120)
        battery_level = random.uniform(15, 95)
        typing_speed = random.uniform(20, 80)
        ambient_light = random.uniform(10, 800)
        accelerometer = [random.uniform(-0.8, 0.8) for _ in range(3)]
        network_usage = random.uniform(100, 2000)  # MB per day
        
        self.simulated_day += timedelta(days=1) # Increment simulated day for next cycle

        return UserBehaviorData(
            timestamp=current_time,
            app_usage=app_usage,
            location=location,
            communication_count=communication_count,
            touch_interactions=touch_interactions,
            unlock_frequency=unlock_frequency,
            battery_level=battery_level,
            screen_time=screen_time,
            typing_speed=typing_speed,
            ambient_light=ambient_light,
            accelerometer=accelerometer,
            network_usage=network_usage
        )

    def preprocess_data(self, smartphone_data: UserBehaviorData, 
                       wearable_data: Dict, ambient_data: Dict) -> Dict[str, Any]:
        """Preprocess and combine data from all sources"""

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

        # More aggressive based on time score
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

        # ambient factors with more variation
        light_factor = min(ambient_data['light_intensity'] / 500.0, 1.0)  # Lower threshold
        noise_factor = ambient_data['noise_level'] / 70.0  # Lower threshold

        # usage intensity to context score
        total_app_usage = sum(smartphone_data.app_usage.values())
        usage_penalty = min(total_app_usage / 4.0, 0.3)  # Penalty for high app usage

        # random to not be so linear
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
                    confidence=0.8 #example placeholder for ai
                ))
            elif smartphone_data['location'] == 'work' and hour > 17:  # Earlier work boundary
                insights.append(ContextualInsight(
                    pattern_type="work_life_balance",
                    severity="medium",
                    description="Extended work-related device usage detected",
                    recommendation="Try to maintain work-life boundaries",
                    confidence=0.7 #example placeholder for ai
                ))
            elif metrics['context_score'] < 0.3:  # Very low context score
                insights.append(ContextualInsight(
                    pattern_type="inappropriate_context",
                    severity="medium",
                    description="Device usage in inappropriate context detected",
                    recommendation="Consider environmental factors and timing of device use",
                    confidence=0.75 #example placeholder for ai
                ))

        # Wellness impact detection (more specific)
        if metrics['wellness_indicator'] < 0.3 and metrics['usage_intensity'] > 0.6:
            insights.append(ContextualInsight(
                pattern_type="wellness_impact",
                severity="high",
                description="Device usage may be impacting your wellness",
                recommendation="Take a break and engage in physical activity",
                confidence=0.85 #example placeholder for ai
            ))

        # Add screen time overuse detection
        smartphone_data_obj = UserBehaviorData(**processed_data['smartphone'])
        if smartphone_data_obj.screen_time > 1.5:  # More than 1.5 hours in one session
            insights.append(ContextualInsight(
                pattern_type="long_session",
                severity="high" if smartphone_data_obj.screen_time > 3.0 else "medium",
                description=f"Extended screen time session: {smartphone_data_obj.screen_time:.1f} hours",
                recommendation="Take regular breaks to avoid eye strain and overuse",
                confidence=0.9 #example placeholder for ai
            ))

        # App usage overuse detection
        total_app_usage = sum(smartphone_data_obj.app_usage.values())
        if total_app_usage > 2.0:  # More than 2 hours total app usage
            insights.append(ContextualInsight(
                pattern_type="excessive_app_usage",
                severity="high" if total_app_usage > 4.0 else "medium",
                description=f"High app usage detected: {total_app_usage:.1f} hours",
                recommendation="Consider setting app time limits and taking breaks",
                confidence=0.85 #example placeholder for ai
            ))

        # Touch interaction overuse
        if smartphone_data_obj.touch_interactions > 500:
            insights.append(ContextualInsight(
                pattern_type="excessive_interactions",
                severity="medium",
                description=f"High touch interactions: {smartphone_data_obj.touch_interactions}",
                recommendation="Take breaks to avoid repetitive strain",
                confidence=0.8 #example placeholder for ai
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
                confidence=0.9 #example placeholder for ai
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

        # Perform context detection
        insights = self.context_detection_with_edge_ai(processed_data)

        # Store in buffer (temporary storage) with both processed_data and insights
        self.data_buffer.append({
            'processed_data': processed_data,
            'insights': [asdict(insight) for insight in insights]
        })

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

    #start byprinting the system architecture
    def start_system(self):
        """Start the IoT system monitoring"""
        print("... Starting Context-Aware IoT System for Technology Overuse Prevention ...")
        print("=" * 70)
        print("\n SYSTEM ARCHITECTURE:")
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
            while self.system_running and cycle_count < 6:  # Run x cycles for demo
                cycle_count += 1
                
                # Get the current simulated day for display
                current_simulated_day = self.edge_layer.simulated_day
                day_name = current_simulated_day.strftime('%A')  # Monday, Tuesday, etc.
                date_str = current_simulated_day.strftime('%B %d, %Y')  # January 15, 2024
                
                print(f"\n📊 Processing Cycle #{cycle_count} - {day_name}, {date_str}")
                print("-" * 60)
                time.sleep(5) #wait for 5 seconds

                # Run edge processing
                result = self.edge_layer.run_edge_processing_cycle()

                self._display_cycle_results(result)

                time.sleep(12)
                
                print(f"---------------------------------")
                print(f"---------------------------------")
        except KeyboardInterrupt:
            print("\n⏹️  System stopped by user")

        print(f"\n✅ System completed {cycle_count} processing cycles")
        self._display_system_summary()

    def _display_cycle_results(self, result: Dict):
        """Display results from a processing cycle"""
        data = result['processed_data']
        insights = result['insights']

        dt_status = "🟢 Connected" if self.edge_layer.digital_twin.mqtt_connected else "🔴 Disconnected"
        edge_status = "🟢 Connected" if self.edge_layer.mqtt_connected else "🔴 Disconnected"
        cloud_status = "🟢 Connected" if self.cloud_layer.mqtt_connected else "🔴 Disconnected"
        
        print(f"\n📱 Digital Twin MQTT Status: {dt_status}")
        print(f"🖥️  Edge Layer MQTT Status: {edge_status}")
        print(f"☁️  Cloud Layer MQTT Status: {cloud_status}")

        all_connected = (self.edge_layer.digital_twin.mqtt_connected and 
                        self.edge_layer.mqtt_connected and 
                        self.cloud_layer.mqtt_connected)
        print("\n📡 DATA FLOW STATUS:")
        if all_connected:
            print("✅ Digital Twin → Edge Layer → Cloud Layer: CONNECTED")
            #print("   Data flowing through all components")
        else:
            print("Data Flow: PARTIALLY CONNECTED")
            print("Some components are not connected")

        # Show key metrics
        metrics = data['derived_metrics']
        print(f"\n📊 PROCESSING METRICS:")
        print(f"📱 Usage Intensity: {metrics['usage_intensity']:.2f}")
        print(f"🌍 Context Score: {metrics['context_score']:.2f}")
        print(f"💪 Wellness Indicator: {metrics['wellness_indicator']:.2f}")
        print(f"💾 Edge Buffer Size: {result['buffer_size']}")
        print(f"☁️  Cloud Buffer Size: {len(self.cloud_layer.analytics_buffer)}")

        # chammge to show the cloud recommendations with more emphasis
        if self.edge_layer.cloud_recommendations:
            print("\n" + "=" * 70)
            print("☁️ CLOUD INTERVENTIONS & RECOMMENDATIONS")
            print("=" * 70)
            
            # latest recommendation
            latest = self.edge_layer.cloud_recommendations[-1]
            
            if 'behavioral_analysis' in latest:
                # Show behavioral analysis details
                analysis = latest['behavioral_analysis']
                print(f"\n🔍 Intervention Level: {analysis['intervention_level'].upper()}")
                print(f"📊 Total Issues Detected: {analysis['total_issues_detected']}")
                print(f"⚠️  Urgency Score: {analysis['urgency_score']:.2f}")
                
                if analysis['specific_interventions']:
                    print("\n🎯 Specific Interventions:")
                    for intervention in analysis['specific_interventions']:
                        print(f"\n  • Priority: {intervention['priority'].upper()}")
                        print(f"    Action: {intervention['action']}")
                        print(f"    Reason: {intervention['reason']}")
            else:
                # Show simple recommendation
                print(f"\n📝 Latest Cloud Recommendation:")
                print(f"   {latest.get('trend_analysis', {}).get('recommendation', 'No recommendation available')}")

        # Show insights if any
        if insights:
            print("\n" + "=" * 70)
            print("🔍 DETECTED BEHAVIORAL PATTERNS")
            print("=" * 70)
            for insight in insights:
                severity_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}
                emoji = severity_emoji.get(insight['severity'], "⚪")
                print(f"\n{emoji} {insight['pattern_type'].upper()}")
                print(f"   Description: {insight['description']}")
                print(f"   Recommendation: {insight['recommendation']}")
                print(f"   Confidence: {insight['confidence']:.2f}")
                time.sleep(0.5)
        else:
            print("\n✅ No behavioral patterns requiring intervention detected")

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

        # Add detailed intervention summary
        print("\n" + "=" * 70)
        print("🎯 INTERVENTION SUMMARY")
        print("=" * 70)

        # Edge Layer Interventions
        print("\n🖥️  EDGE LAYER INTERVENTIONS:")
        edge_insights = []
        for data in self.edge_layer.data_buffer:
            if 'insights' in data:
                edge_insights.extend(data['insights'])
        
        if edge_insights:
            # Group insights by pattern type
            pattern_groups = {}
            for insight in edge_insights:
                pattern = insight['pattern_type']
                if pattern not in pattern_groups:
                    pattern_groups[pattern] = []
                pattern_groups[pattern].append(insight)
            
            # Display grouped insights
            for pattern, insights in pattern_groups.items():
                severity_counts = {'high': 0, 'medium': 0, 'low': 0}
                for insight in insights:
                    severity_counts[insight['severity']] += 1
                
                print(f"\n  • {pattern.upper()}:")
                print(f"    - High severity: {severity_counts['high']}")
                print(f"    - Medium severity: {severity_counts['medium']}")
                print(f"    - Low severity: {severity_counts['low']}")
                if insights:
                    print(f"    - Latest recommendation: {insights[-1]['recommendation']}")
        else:
            print("  No edge interventions recorded")

        # Cloud Layer Interventions
        print("\n☁️  CLOUD LAYER INTERVENTIONS:")
        if self.edge_layer.cloud_recommendations:
            # Group recommendations by type
            intervention_types = {}
            for rec in self.edge_layer.cloud_recommendations:
                if 'behavioral_analysis' in rec:
                    analysis = rec['behavioral_analysis']
                    intervention_level = analysis['intervention_level']
                    if intervention_level not in intervention_types:
                        intervention_types[intervention_level] = {
                            'count': 0,
                            'total_issues': 0,
                            'interventions': []
                        }
                    intervention_types[intervention_level]['count'] += 1
                    intervention_types[intervention_level]['total_issues'] += analysis['total_issues_detected']
                    if analysis['specific_interventions']:
                        intervention_types[intervention_level]['interventions'].extend(
                            analysis['specific_interventions']
                        )

            # Display intervention summary
            for level, data in intervention_types.items():
                print(f"\n  • {level.upper()} INTERVENTION LEVEL:")
                print(f"    - Times triggered: {data['count']}")
                print(f"    - Total issues addressed: {data['total_issues']}")
                if data['interventions']:
                    print("    - Key interventions:")
                    # Get unique interventions
                    unique_interventions = {}
                    for intervention in data['interventions']:
                        key = f"{intervention['priority']}:{intervention['action']}"
                        if key not in unique_interventions:
                            unique_interventions[key] = intervention
                    
                    for intervention in unique_interventions.values():
                        print(f"      * [{intervention['priority'].upper()}] {intervention['action']}")
        else:
            print("  No cloud interventions recorded")

        # Smart Home Interventions
        print("\n🏠 SMART HOME INTERVENTIONS:")
        smart_home_summary = self.cloud_layer.smart_home.get_intervention_summary()
        print(f"  • Total Smart Home Interventions: {smart_home_summary['total_interventions']}")
        print(f"  • Active Smart Devices: {smart_home_summary['active_devices']}")
        
        if smart_home_summary['recent_interventions']:
            print("\n  • Recent Smart Home Actions:")
            for intervention in smart_home_summary['recent_interventions']:
                action = intervention['intervention']
                print(f"    - {action['device'].upper()}: {action['description']}")
                print(f"      Settings: {action['settings']}")

        # Overall Intervention Statistics
        print("\n📊 OVERALL INTERVENTION STATISTICS:")
        total_edge_insights = len(edge_insights)
        total_cloud_recommendations = len(self.edge_layer.cloud_recommendations)
        print(f"  • Total Edge Layer Insights: {total_edge_insights}")
        print(f"  • Total Cloud Layer Recommendations: {total_cloud_recommendations}")
        print(f"  • Total Smart Home Interventions: {smart_home_summary['total_interventions']}")
        
        if total_edge_insights > 0 and total_cloud_recommendations > 0:
            print(f"  • Average Insights per Cloud Recommendation: {total_edge_insights/total_cloud_recommendations:.1f}")

def main():
    # Main function to run the IoT system
    #print("🔧 Initializing Context-Aware IoT System...")
    #print("📱 Digital Twin: Smartphone User Behavior Model")
    #print("🖥️  Edge Layer: Raspberry Pi Simulation")
    #print("⚡ Edge AI: Real-time Context Detection")
    #print("📡 MQTT: Communication Layer for IoT Components")
    #print("🏥 Health Monitor: System Health Tracking")

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

    # Initialize health monitoring
    print("🏥 Initializing IoT Health Monitor...")
    try:
        from iot_health_monitor import IoTSystemHealthMonitor
        health_monitor = IoTSystemHealthMonitor()
        print("✅ Health monitor initialized successfully")
    except Exception as e:
        print(f"⚠️  Could not initialize health monitor: {e}")
        health_monitor = None

    print("🔄 Initializing IoT System components...")
    system = IoTSystemManager()
    print("🔗 Establishing MQTT connections...")
    time.sleep(2)  # Additional time for connections
    
    # Start the main system
    system.start_system()
    
    # Generate health report after system completion
    if health_monitor:
        print("\n🏥 Generating Final Health Report...")
        try:
            health_report = health_monitor.get_health_report()
            
            print("\n" + "=" * 70)
            print("🏥 FINAL IOT SYSTEM HEALTH REPORT")
            print("=" * 70)
            
            if 'system_health' in health_report:
                system_health = health_report['system_health']
                print(f"\n📊 SYSTEM OVERVIEW:")
                print(f"   Status: {system_health['current_status'].upper()}")
                print(f"   Health Score: {system_health['health_score']:.2f}/1.00")
                print(f"   Uptime: {system_health['overall_uptime']:.1%}")
                print(f"   Component Failures: {system_health['component_failures']}")
                print(f"   Error Rate: {system_health['error_rate']:.3f} errors/min")
                print(f"   Avg Response Time: {system_health['avg_response_time']:.2f}s")
                print(f"   Data Loss Rate: {system_health['data_loss_rate']:.1%}")
                print(f"   Connection Stability: {system_health['connection_stability']:.1%}")
                
                print(f"\n🎯 RECOMMENDATIONS:")
                for i, recommendation in enumerate(health_report.get('recommendations', []), 1):
                    print(f"   {i}. {recommendation}")
                
                # Save health report
                with open('iot_health_report.json', 'w') as f:
                    json.dump(health_report, f, indent=2, default=str)
                print(f"\n💾 Health report saved to 'iot_health_report.json'")
            else:
                print("⚠️  No health data available")
                
        except Exception as e:
            print(f"⚠️  Error generating health report: {e}")
        
        # Stop health monitoring
        health_monitor.stop_monitoring()

if __name__ == "__main__":
    main()