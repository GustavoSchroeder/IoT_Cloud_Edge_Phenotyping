import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import statistics
import paho.mqtt.client as mqtt
import uuid

@dataclass
class ComponentHealthStatus:
    """Health status of individual IoT components"""
    component_name: str
    status: str  # 'healthy', 'degraded', 'failed'
    last_heartbeat: datetime
    response_time: float
    error_count: int
    uptime_seconds: float
    data_flow_rate: float
    mqtt_connected: bool

@dataclass
class SystemHealthMetrics:
    """Overall system health metrics"""
    timestamp: datetime
    overall_uptime: float
    component_failures: int
    error_rate: float
    avg_response_time: float
    data_loss_rate: float
    connection_stability: float
    system_status: str  # 'healthy', 'degraded', 'critical'
    health_score: float  # 0.0 to 1.0

class IoTSystemHealthMonitor:
    """Comprehensive IoT system health monitoring"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.health_history = deque(maxlen=1000)
        self.component_health = {}
        self.error_log = []
        self.response_times = defaultdict(list)
        self.data_loss_events = []
        self.connection_events = []
        
        # Component tracking
        self.expected_components = {
            'digital_twin': 'iot/digitaltwin/behavior',
            'edge_layer': 'iot/edge/processed',
            'cloud_layer': 'iot/cloud/recommendations',
            'smart_home': 'iot/smart_home/status'
        }
        
        # Health thresholds
        self.health_thresholds = {
            'critical_error_rate': 0.1,  # 10% error rate
            'degraded_error_rate': 0.05,  # 5% error rate
            'max_response_time': 5.0,  # 5 seconds
            'min_uptime': 0.95,  # 95% uptime
            'max_data_loss': 0.05,  # 5% data loss
            'min_connection_stability': 0.9  # 90% connection stability
        }
        
        # MQTT setup for health monitoring
        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, 
                                     client_id=f"health_monitor_{uuid.uuid4().hex[:8]}")
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_message = self._on_mqtt_message
        self.mqtt_connected = False
        self._setup_mqtt_connection()
        
        # Start monitoring threads
        self.monitoring_active = True
        self._start_monitoring_threads()
    
    def _setup_mqtt_connection(self):
        """Setup MQTT connection for health monitoring"""
        try:
            self.mqtt_client.connect("127.0.0.1", 1883, 60)
            self.mqtt_client.loop_start()
            time.sleep(1)
            return True
        except Exception as e:
            print(f"⚠️  Health Monitor MQTT connection failed: {e}")
            return False
    
    def _on_mqtt_connect(self, client, userdata, flags, rc, properties=None):
        """MQTT connection callback"""
        if rc == 0:
            self.mqtt_connected = True
            print(f"🏥 IoT Health Monitor MQTT connected successfully")
            # Subscribe to health-related topics
            topics = [
                'iot/system/heartbeat',
                'iot/evaluator/heartbeat',
                'iot/+/status',
                'iot/+/health',
                'iot/+/error',
                '#'  # Subscribe to all topics for comprehensive monitoring
            ]
            for topic in topics:
                client.subscribe(topic)
        else:
            print(f"⚠️  Health Monitor MQTT connection failed with code {rc}")
    
    def _on_mqtt_message(self, client, userdata, msg):
        """Handle incoming MQTT messages for health monitoring"""
        try:
            timestamp = datetime.now()
            
            # Track connection events
            self.connection_events.append({
                'timestamp': timestamp,
                'topic': msg.topic,
                'message_size': len(msg.payload),
                'component': self._identify_component_from_topic(msg.topic)
            })
            
            # Parse message for health information
            try:
                message = json.loads(msg.payload.decode())
                self._process_health_message(msg.topic, message, timestamp)
            except json.JSONDecodeError:
                # Track data loss events
                self.data_loss_events.append({
                    'timestamp': timestamp,
                    'topic': msg.topic,
                    'reason': 'JSON decode error',
                    'payload_size': len(msg.payload)
                })
                
        except Exception as e:
            self.error_log.append({
                'timestamp': datetime.now(),
                'error': str(e),
                'topic': msg.topic,
                'component': 'health_monitor'
            })
    
    def _identify_component_from_topic(self, topic: str) -> Optional[str]:
        """Identify which component a topic belongs to"""
        if 'digitaltwin' in topic:
            return 'digital_twin'
        elif 'edge' in topic:
            return 'edge_layer'
        elif 'cloud' in topic:
            return 'cloud_layer'
        elif 'smart_home' in topic:
            return 'smart_home'
        elif 'evaluator' in topic:
            return 'health_monitor'
        return None
    
    def _process_health_message(self, topic: str, message: Dict, timestamp: datetime):
        """Process health-related messages"""
        component = self._identify_component_from_topic(topic)
        
        if component:
            # Update component health based on message
            if 'status' in message:
                self._update_component_status(component, message['status'], timestamp)
            
            if 'response_time' in message:
                self.response_times[component].append(message['response_time'])
                # Keep only recent response times (last 100)
                if len(self.response_times[component]) > 100:
                    self.response_times[component] = self.response_times[component][-100:]
            
            if 'error' in message:
                self.error_log.append({
                    'timestamp': timestamp,
                    'error': message['error'],
                    'topic': topic,
                    'component': component
                })
    
    def _update_component_status(self, component: str, status: str, timestamp: datetime):
        """Update component health status"""
        if component not in self.component_health:
            self.component_health[component] = ComponentHealthStatus(
                component_name=component,
                status='unknown',
                last_heartbeat=timestamp,
                response_time=0.0,
                error_count=0,
                uptime_seconds=0.0,
                data_flow_rate=0.0,
                mqtt_connected=False
            )
        
        self.component_health[component].status = status
        self.component_health[component].last_heartbeat = timestamp
    
    def _start_monitoring_threads(self):
        """Start background monitoring threads"""
        
        # Health monitoring thread
        def health_monitor():
            while self.monitoring_active:
                try:
                    # Calculate system health metrics
                    health_metrics = self.evaluate_system_health()
                    
                    # Store health metrics
                    self.health_history.append(health_metrics)
                    
                    # Publish health status
                    if self.mqtt_connected:
                        health_message = {
                            'timestamp': health_metrics.timestamp.isoformat(),
                            'system_status': health_metrics.system_status,
                            'health_score': health_metrics.health_score,
                            'component_count': len(self.component_health),
                            'error_rate': health_metrics.error_rate,
                            'avg_response_time': health_metrics.avg_response_time
                        }
                        self.mqtt_client.publish('iot/system/health', json.dumps(health_message))
                    
                    # Display health status if significant changes
                    self._display_health_status(health_metrics)
                    
                except Exception as e:
                    self.error_log.append({
                        'timestamp': datetime.now(),
                        'error': f"Health monitoring error: {e}",
                        'component': 'health_monitor'
                    })
                
                time.sleep(30)  # Check health every 30 seconds
        
        # Start health monitoring thread
        health_thread = threading.Thread(target=health_monitor, daemon=True)
        health_thread.start()
        
        # Heartbeat thread
        def heartbeat_monitor():
            while self.monitoring_active:
                if self.mqtt_connected:
                    heartbeat = {
                        'timestamp': datetime.now().isoformat(),
                        'monitor_id': 'iot_health_monitor',
                        'status': 'monitoring',
                        'components_tracked': len(self.expected_components),
                        'health_history_size': len(self.health_history)
                    }
                    self.mqtt_client.publish('iot/monitor/heartbeat', json.dumps(heartbeat))
                time.sleep(60)  # Send heartbeat every minute
        
        # Start heartbeat thread
        heartbeat_thread = threading.Thread(target=heartbeat_monitor, daemon=True)
        heartbeat_thread.start()
    
    def evaluate_system_health(self) -> SystemHealthMetrics:
        """Evaluate overall IoT system health"""
        current_time = datetime.now()
        
        # Calculate overall uptime
        total_uptime = (current_time - self.start_time).total_seconds()
        system_uptime = self._calculate_system_uptime()
        
        # Count component failures
        component_failures = self._count_component_failures()
        
        # Calculate error rate
        error_rate = self._calculate_error_rate()
        
        # Calculate average response time
        avg_response_time = self._calculate_average_response_time()
        
        # Calculate data loss rate
        data_loss_rate = self._calculate_data_loss_rate()
        
        # Calculate connection stability
        connection_stability = self._calculate_connection_stability()
        
        # Determine system status
        system_status = self._determine_system_status(
            error_rate, avg_response_time, system_uptime, data_loss_rate, connection_stability
        )
        
        # Calculate overall health score
        health_score = self._calculate_health_score(
            system_uptime, component_failures, error_rate, 
            avg_response_time, data_loss_rate, connection_stability
        )
        
        return SystemHealthMetrics(
            timestamp=current_time,
            overall_uptime=system_uptime,
            component_failures=component_failures,
            error_rate=error_rate,
            avg_response_time=avg_response_time,
            data_loss_rate=data_loss_rate,
            connection_stability=connection_stability,
            system_status=system_status,
            health_score=health_score
        )
    
    def _calculate_system_uptime(self) -> float:
        """Calculate system uptime percentage"""
        if not self.health_history:
            return 1.0  # Assume 100% uptime if no history
        
        # Count healthy periods vs total time
        total_time = (datetime.now() - self.start_time).total_seconds()
        healthy_time = 0
        
        for health_record in self.health_history:
            if health_record.system_status in ['healthy', 'degraded']:
                healthy_time += 30  # Each record represents 30 seconds
        
        return min(1.0, healthy_time / max(total_time, 1))
    
    def _count_component_failures(self) -> int:
        """Count currently failed components"""
        failed_count = 0
        current_time = datetime.now()
        
        for component_name, health in self.component_health.items():
            # Check if component is failed or hasn't been seen recently
            time_since_last = (current_time - health.last_heartbeat).total_seconds()
            
            if health.status == 'failed' or time_since_last > 300:  # 5 minutes
                failed_count += 1
        
        return failed_count
    
    def _calculate_error_rate(self) -> float:
        """Calculate error rate per minute"""
        if not self.error_log:
            return 0.0
        
        # Count errors in the last hour
        one_hour_ago = datetime.now() - timedelta(hours=1)
        recent_errors = [error for error in self.error_log if error['timestamp'] > one_hour_ago]
        
        # Calculate errors per minute
        error_rate = len(recent_errors) / 60.0  # errors per minute
        
        return error_rate
    
    def _calculate_average_response_time(self) -> float:
        """Calculate average response time across all components"""
        all_response_times = []
        
        for component, times in self.response_times.items():
            if times:
                all_response_times.extend(times)
        
        if all_response_times:
            return statistics.mean(all_response_times)
        else:
            return 0.0
    
    def _calculate_data_loss_rate(self) -> float:
        """Calculate data loss rate"""
        if not self.data_loss_events:
            return 0.0
        
        # Count data loss events in the last hour
        one_hour_ago = datetime.now() - timedelta(hours=1)
        recent_losses = [loss for loss in self.data_loss_events if loss['timestamp'] > one_hour_ago]
        
        # Calculate loss rate based on total messages vs lost messages
        total_messages = len(self.connection_events)
        lost_messages = len(recent_losses)
        
        if total_messages > 0:
            return lost_messages / total_messages
        else:
            return 0.0
    
    def _calculate_connection_stability(self) -> float:
        """Calculate connection stability score"""
        if not self.connection_events:
            return 1.0  # Assume stable if no events
        
        # Count connection events in the last hour
        one_hour_ago = datetime.now() - timedelta(hours=1)
        recent_events = [event for event in self.connection_events if event['timestamp'] > one_hour_ago]
        
        if not recent_events:
            return 1.0
        
        # Calculate stability based on consistent message flow
        # More events = more stable (assuming regular communication)
        expected_events_per_hour = len(self.expected_components) * 60  # 1 message per minute per component
        actual_events = len(recent_events)
        
        stability = min(1.0, actual_events / max(expected_events_per_hour, 1))
        return stability
    
    def _determine_system_status(self, error_rate: float, avg_response_time: float, 
                                uptime: float, data_loss_rate: float, connection_stability: float) -> str:
        """Determine overall system status"""
        
        # Check for critical conditions
        if (error_rate > self.health_thresholds['critical_error_rate'] or
            avg_response_time > self.health_thresholds['max_response_time'] * 2 or
            uptime < 0.8 or  # Less than 80% uptime
            data_loss_rate > self.health_thresholds['max_data_loss'] * 2 or
            connection_stability < 0.5):  # Less than 50% connection stability
            return 'critical'
        
        # Check for degraded conditions
        elif (error_rate > self.health_thresholds['degraded_error_rate'] or
              avg_response_time > self.health_thresholds['max_response_time'] or
              uptime < self.health_thresholds['min_uptime'] or
              data_loss_rate > self.health_thresholds['max_data_loss'] or
              connection_stability < self.health_thresholds['min_connection_stability']):
            return 'degraded'
        
        else:
            return 'healthy'
    
    def _calculate_health_score(self, uptime: float, failures: int, error_rate: float,
                               response_time: float, data_loss: float, connection_stability: float) -> float:
        """Calculate overall health score (0.0 to 1.0)"""
        
        # Weighted scoring system
        scores = {
            'uptime': uptime * 0.25,  # 25% weight
            'failures': max(0, 1.0 - (failures / len(self.expected_components))) * 0.20,  # 20% weight
            'error_rate': max(0, 1.0 - (error_rate / 0.1)) * 0.20,  # 20% weight (normalize to 10% max)
            'response_time': max(0, 1.0 - (response_time / 5.0)) * 0.15,  # 15% weight
            'data_loss': max(0, 1.0 - (data_loss / 0.05)) * 0.10,  # 10% weight
            'connection_stability': connection_stability * 0.10  # 10% weight
        }
        
        # Calculate weighted average
        total_score = sum(scores.values())
        return max(0.0, min(1.0, total_score))
    
    def _display_health_status(self, health_metrics: SystemHealthMetrics):
        """Display health status with visual indicators"""
        status_emoji = {
            'healthy': '🟢',
            'degraded': '🟡', 
            'critical': '🔴'
        }
        emoji = status_emoji.get(health_metrics.system_status, '⚪')
        
        print(f"\n🏥 IoT SYSTEM HEALTH STATUS")
        print(f"   Health Score: {health_metrics.health_score:.2f}/1.00")
        print(f"   Uptime: {health_metrics.overall_uptime:.1%}")
        print(f"   Component Failures: {health_metrics.component_failures}/{len(self.expected_components)}")
        print(f"   Error Rate: {health_metrics.error_rate:.3f} errors/min")
        print(f"   Avg Response Time: {health_metrics.avg_response_time:.2f}s")
        print(f"   Data Loss Rate: {health_metrics.data_loss_rate:.1%}")
        print(f"   Connection Stability: {health_metrics.connection_stability:.1%}")
    
    def get_component_health_summary(self) -> Dict[str, Any]:
        """Get detailed component health summary"""
        summary = {
            'timestamp': datetime.now().isoformat(),
            'system_overview': {
                'total_components': len(self.expected_components),
                'healthy_components': sum(1 for h in self.component_health.values() if h.status == 'healthy'),
                'degraded_components': sum(1 for h in self.component_health.values() if h.status == 'degraded'),
                'failed_components': sum(1 for h in self.component_health.values() if h.status == 'failed')
            },
            'component_details': {}
        }
        
        for component_name, health in self.component_health.items():
            summary['component_details'][component_name] = {
                'status': health.status,
                'last_heartbeat': health.last_heartbeat.isoformat(),
                'response_time': health.response_time,
                'error_count': health.error_count,
                'uptime_seconds': health.uptime_seconds,
                'data_flow_rate': health.data_flow_rate,
                'mqtt_connected': health.mqtt_connected
            }
        
        return summary
    
    def get_health_report(self) -> Dict[str, Any]:
        """Generate comprehensive health report"""
        if not self.health_history:
            return {'error': 'No health data available'}
        
        latest_health = self.health_history[-1]
        
        report = {
            'report_timestamp': datetime.now().isoformat(),
            'monitoring_duration': (datetime.now() - self.start_time).total_seconds() / 3600,  # hours
            'system_health': {
                'current_status': latest_health.system_status,
                'health_score': latest_health.health_score,
                'overall_uptime': latest_health.overall_uptime,
                'component_failures': latest_health.component_failures,
                'error_rate': latest_health.error_rate,
                'avg_response_time': latest_health.avg_response_time,
                'data_loss_rate': latest_health.data_loss_rate,
                'connection_stability': latest_health.connection_stability
            },
            'component_health': self.get_component_health_summary(),
            'error_analysis': {
                'total_errors': len(self.error_log),
                'recent_errors': len([e for e in self.error_log if e['timestamp'] > datetime.now() - timedelta(hours=1)]),
                'error_by_component': self._analyze_errors_by_component(),
                'most_common_errors': self._get_most_common_errors()
            },
            'recommendations': self._generate_health_recommendations(latest_health)
        }
        
        return report
    
    def _analyze_errors_by_component(self) -> Dict[str, int]:
        """Analyze error distribution by component"""
        error_counts = defaultdict(int)
        
        for error in self.error_log:
            component = error.get('component', 'unknown')
            error_counts[component] += 1
        
        return dict(error_counts)
    
    def _get_most_common_errors(self) -> List[Dict[str, Any]]:
        """Get most common error types"""
        error_types = defaultdict(int)
        
        for error in self.error_log:
            error_msg = error.get('error', 'unknown')
            # Extract error type from message
            error_type = error_msg.split(':')[0] if ':' in error_msg else error_msg
            error_types[error_type] += 1
        
        # Return top 5 most common errors
        sorted_errors = sorted(error_types.items(), key=lambda x: x[1], reverse=True)
        return [{'error_type': error, 'count': count} for error, count in sorted_errors[:5]]
    
    def _generate_health_recommendations(self, health_metrics: SystemHealthMetrics) -> List[str]:
        """Generate health recommendations based on current status"""
        recommendations = []
        
        if health_metrics.error_rate > self.health_thresholds['degraded_error_rate']:
            recommendations.append("🔧 High error rate detected - review system logs and error handling")
        
        if health_metrics.avg_response_time > self.health_thresholds['max_response_time']:
            recommendations.append("⏱️ High response times detected - investigate component performance")
        
        if health_metrics.data_loss_rate > self.health_thresholds['max_data_loss']:
            recommendations.append("📡 Data loss detected - check network connectivity and message delivery")
        
        #if health_metrics.connection_stability < self.health_thresholds['min_connection_stability']:
        #    recommendations.append("🔌 Connection instability detected - verify MQTT broker and network")
        
        if health_metrics.component_failures > 0:
            recommendations.append(f"🚨 {health_metrics.component_failures} component(s) failed - restart failed components")
        
        if health_metrics.health_score < 0.7:
            recommendations.append("⚠️ Overall system health is poor - comprehensive system review recommended")
        
        if not recommendations:
            recommendations.append("✅ System health is optimal - no immediate action required")
        
        return recommendations
    
    def stop_monitoring(self):
        """Stop health monitoring"""
        self.monitoring_active = False
        if self.mqtt_connected:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()

def main():
    """Main function to run IoT health monitoring"""
    print("🏥 IoT System Health Monitor")
    print("=" * 50)
    print("Monitoring system health metrics:")
    print("• Overall uptime")
    print("• Component failures")
    print("• Error rates")
    print("• Response times")
    print("• Data loss rates")
    print("• Connection stability")
    
    # Create health monitor
    health_monitor = IoTSystemHealthMonitor()
    
    try:
        # Run monitoring for specified duration
        monitoring_duration = 300  # 5 minutes
        print(f"\n🔍 Starting health monitoring for {monitoring_duration} seconds...")
        
        time.sleep(monitoring_duration)
        
        # Generate final health report
        print("\n📋 Generating Health Report...")
        health_report = health_monitor.get_health_report()
        
        # Display report
        print("\n" + "=" * 50)
        print("🏥 IOT SYSTEM HEALTH REPORT")
        print("=" * 50)
        
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
        for i, recommendation in enumerate(health_report['recommendations'], 1):
            print(f"   {i}. {recommendation}")
        
        # Save report to file
        with open('iot_health_report.json', 'w') as f:
            json.dump(health_report, f, indent=2, default=str)
        print(f"\n💾 Health report saved to 'iot_health_report.json'")
        
    except KeyboardInterrupt:
        print("\n⏹️  Health monitoring stopped by user")
    except Exception as e:
        print(f"\n❌ Health monitoring failed: {e}")
    finally:
        health_monitor.stop_monitoring()

if __name__ == "__main__":
    main()
