
import json
import time
import random
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any
from dataclasses import dataclass, asdict
import numpy as np
from collections import defaultdict, deque

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

class SmartphoneDigitalTwin:
    """Digital twin representation of a smartphone user"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.behavior_history = deque(maxlen=1000)  # Keep last 1000 data points
        self.usage_patterns = {}
        self.daily_stats = defaultdict(list)
        self.overuse_threshold = 8.0  # hours per day
        self.session_threshold = 2.0  # hours per session
        
    def add_behavior_data(self, data: UserBehaviorData):
        """Add new behavior data to the digital twin"""
        self.behavior_history.append(data)
        self._update_patterns(data)
        
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
        
    def collect_smartphone_data(self) -> UserBehaviorData:
        """Simulate smartphone data collection"""
        current_time = datetime.now().isoformat()
        
        # Simulate realistic app usage patterns
        apps = ['social_media', 'messaging', 'games', 'productivity', 'entertainment']
        app_usage = {app: random.exponential(0.5) for app in apps}
        
        return UserBehaviorData(
            timestamp=current_time,
            app_usage=app_usage,
            location=random.choice(['home', 'work', 'commute', 'leisure']),
            communication_count=random.poisson(5),
            touch_interactions=random.randint(50, 500),
            unlock_frequency=random.randint(10, 100),
            battery_level=random.uniform(20, 100),
            screen_time=random.exponential(0.3),  # Hours
            typing_speed=random.uniform(20, 80),  # WPM
            ambient_light=random.uniform(0, 1000),
            accelerometer=[random.uniform(-1, 1) for _ in range(3)],
            network_usage=random.exponential(100)  # MB
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
        
        return {
            'processed_data': processed_data,
            'insights': [asdict(insight) for insight in insights],
            'buffer_size': len(self.data_buffer)
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
        
        # Show key metrics
        metrics = data['derived_metrics']
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
    
    system = IoTSystemManager()
    system.start_system()

if __name__ == "__main__":
    main()
