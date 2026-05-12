"""
Phase 7: Advanced Analytics Engine
- Real alert triggering system
- Advanced heatmap processing  
- Report generation
- Multi-camera analytics
"""

import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class AlertEngine:
    """Real-time alert triggering system"""
    
    def __init__(self):
        self.thresholds = {
            'max_people': 50,
            'max_queue_length': 10,
            'max_wait_time': 300,  # seconds
            'max_occupancy': 80    # percentage
        }
        self.active_alerts = {}
        self.alert_history = []
    
    def check_thresholds(self, analytics: Dict[str, Any], camera_id: str) -> List[Dict]:
        """Check analytics against thresholds and generate alerts"""
        alerts = []
        timestamp = datetime.now()
        
        # Check people count
        if analytics.get('people_count', 0) > self.thresholds['max_people']:
            alert = {
                'id': f"alert_{camera_id}_{int(timestamp.timestamp())}",
                'type': 'high_occupancy',
                'severity': 'warning',
                'camera_id': camera_id,
                'message': f"High occupancy: {analytics['people_count']} people (threshold: {self.thresholds['max_people']})",
                'value': analytics['people_count'],
                'threshold': self.thresholds['max_people'],
                'timestamp': timestamp.isoformat()
            }
            alerts.append(alert)
            self.active_alerts[alert['id']] = alert
        
        # Check queue length
        if analytics.get('queue_length', 0) > self.thresholds['max_queue_length']:
            alert = {
                'id': f"alert_{camera_id}_{int(timestamp.timestamp())}_queue",
                'type': 'long_queue',
                'severity': 'info',
                'camera_id': camera_id,
                'message': f"Long queue: {analytics['queue_length']} people (threshold: {self.thresholds['max_queue_length']})",
                'value': analytics['queue_length'],
                'threshold': self.thresholds['max_queue_length'],
                'timestamp': timestamp.isoformat()
            }
            alerts.append(alert)
            self.active_alerts[alert['id']] = alert
        
        # Check wait time
        if analytics.get('average_wait_time', 0) > self.thresholds['max_wait_time']:
            alert = {
                'id': f"alert_{camera_id}_{int(timestamp.timestamp())}_wait",
                'type': 'high_wait_time',
                'severity': 'warning',
                'camera_id': camera_id,
                'message': f"High wait time: {analytics['average_wait_time']:.0f}s (threshold: {self.thresholds['max_wait_time']}s)",
                'value': analytics['average_wait_time'],
                'threshold': self.thresholds['max_wait_time'],
                'timestamp': timestamp.isoformat()
            }
            alerts.append(alert)
            self.active_alerts[alert['id']] = alert
        
        # Check occupancy
        if analytics.get('occupancy_percentage', 0) > self.thresholds['max_occupancy']:
            alert = {
                'id': f"alert_{camera_id}_{int(timestamp.timestamp())}_occupancy",
                'type': 'high_occupancy_pct',
                'severity': 'critical',
                'camera_id': camera_id,
                'message': f"Critical occupancy: {analytics['occupancy_percentage']:.1f}% (threshold: {self.thresholds['max_occupancy']}%)",
                'value': analytics['occupancy_percentage'],
                'threshold': self.thresholds['max_occupancy'],
                'timestamp': timestamp.isoformat()
            }
            alerts.append(alert)
            self.active_alerts[alert['id']] = alert
        
        # Store in history
        self.alert_history.extend(alerts)
        
        return alerts
    
    def set_thresholds(self, thresholds: Dict[str, float]):
        """Update alert thresholds"""
        self.thresholds.update(thresholds)
        logger.info(f"Alert thresholds updated: {self.thresholds}")
    
    def get_active_alerts(self, camera_id: str = None) -> List[Dict]:
        """Get currently active alerts"""
        if camera_id:
            return [a for a in self.active_alerts.values() if a['camera_id'] == camera_id]
        return list(self.active_alerts.values())
    
    def get_alert_history(self, camera_id: str = None, hours: int = 24) -> List[Dict]:
        """Get alert history for time period"""
        cutoff = datetime.now() - timedelta(hours=hours)
        
        history = [
            a for a in self.alert_history
            if datetime.fromisoformat(a['timestamp']) > cutoff
        ]
        
        if camera_id:
            history = [a for a in history if a['camera_id'] == camera_id]
        
        return history


class HeatmapAnalytics:
    """Advanced heatmap processing and analysis"""
    
    def __init__(self, grid_size: int = 20):
        self.grid_size = grid_size
        self.grid_total_cells = grid_size * grid_size
        self.daily_grids = {}
        self.hourly_grids = {}
    
    def process_heatmap(self, heatmap_data: List[List[int]]) -> Dict[str, Any]:
        """Process and analyze heatmap data"""
        if not heatmap_data or len(heatmap_data) != self.grid_total_cells:
            return {'error': 'Invalid heatmap data'}
        
        # Flatten to array for easier processing
        flat_data = heatmap_data if isinstance(heatmap_data, list) and len(heatmap_data) == self.grid_total_cells else list(heatmap_data)
        
        # Calculate statistics
        total_detections = sum(flat_data)
        max_intensity = max(flat_data) if flat_data else 0
        min_intensity = min(flat_data) if flat_data else 0
        avg_intensity = total_detections / len(flat_data) if flat_data else 0
        
        # Find hotspots (top 10% cells)
        sorted_cells = sorted(enumerate(flat_data), key=lambda x: x[1], reverse=True)
        hotspot_threshold = max_intensity * 0.7 if max_intensity > 0 else 0
        hotspots = [
            {
                'cell_id': idx,
                'row': idx // self.grid_size,
                'col': idx % self.grid_size,
                'intensity': value
            }
            for idx, value in sorted_cells[:10] if value > 0
        ]
        
        # Find cold zones (unused areas)
        cold_zones = [
            {
                'cell_id': idx,
                'row': idx // self.grid_size,
                'col': idx % self.grid_size,
            }
            for idx, value in enumerate(flat_data) if value == 0
        ]
        
        # Calculate flow patterns (entry/exit patterns)
        left_edge = sum(flat_data[i] for i in range(0, self.grid_total_cells, self.grid_size))
        right_edge = sum(flat_data[i + self.grid_size - 1] for i in range(0, self.grid_total_cells - self.grid_size + 1, self.grid_size))
        top_edge = sum(flat_data[i] for i in range(self.grid_size))
        bottom_edge = sum(flat_data[i] for i in range(self.grid_total_cells - self.grid_size, self.grid_total_cells))
        
        flow_pattern = {
            'left_traffic': left_edge,
            'right_traffic': right_edge,
            'top_traffic': top_edge,
            'bottom_traffic': bottom_edge,
            'dominant_entry': max(
                ('left', left_edge),
                ('right', right_edge),
                ('top', top_edge),
                ('bottom', bottom_edge),
                key=lambda x: x[1]
            )[0]
        }
        
        return {
            'grid_size': self.grid_size,
            'total_detections': total_detections,
            'statistics': {
                'max_intensity': max_intensity,
                'min_intensity': min_intensity,
                'avg_intensity': avg_intensity,
                'active_cells': len([v for v in flat_data if v > 0]),
                'inactive_cells': len([v for v in flat_data if v == 0])
            },
            'hotspots': hotspots,
            'cold_zones': cold_zones,
            'flow_patterns': flow_pattern,
            'density_distribution': self._calculate_density_distribution(flat_data)
        }
    
    def _calculate_density_distribution(self, data: List[int]) -> Dict[str, int]:
        """Calculate density distribution"""
        max_val = max(data) if data else 1
        
        ranges = {
            'zero': len([v for v in data if v == 0]),
            'very_low': len([v for v in data if 0 < v <= max_val * 0.2]),
            'low': len([v for v in data if max_val * 0.2 < v <= max_val * 0.4]),
            'medium': len([v for v in data if max_val * 0.4 < v <= max_val * 0.6]),
            'high': len([v for v in data if max_val * 0.6 < v <= max_val * 0.8]),
            'very_high': len([v for v in data if v > max_val * 0.8])
        }
        
        return ranges


class ReportGenerator:
    """Generate detailed analytics reports"""
    
    @staticmethod
    def generate_daily_report(analytics_data: List[Dict], camera_id: str, date: str) -> Dict:
        """Generate daily report"""
        if not analytics_data:
            return {'error': 'No analytics data available'}
        
        people_counts = [a['people_count'] for a in analytics_data]
        queue_lengths = [a['queue_length'] for a in analytics_data]
        wait_times = [a['average_wait_time'] for a in analytics_data]
        
        report = {
            'report_type': 'daily',
            'camera_id': camera_id,
            'date': date,
            'generated_at': datetime.now().isoformat(),
            'summary': {
                'total_data_points': len(analytics_data),
                'total_people': sum(people_counts),
                'avg_people': sum(people_counts) / len(people_counts) if people_counts else 0,
                'peak_people': max(people_counts) if people_counts else 0,
                'min_people': min(people_counts) if people_counts else 0,
            },
            'queue_analysis': {
                'avg_queue_length': sum(queue_lengths) / len(queue_lengths) if queue_lengths else 0,
                'peak_queue': max(queue_lengths) if queue_lengths else 0,
                'total_wait_time_hours': sum(wait_times) / 3600 if wait_times else 0,
                'avg_wait_time': sum(wait_times) / len(wait_times) if wait_times else 0,
                'max_wait_time': max(wait_times) if wait_times else 0,
            },
            'peak_hours': ReportGenerator._calculate_peak_hours(analytics_data),
            'recommendations': ReportGenerator._generate_recommendations(analytics_data),
            'metrics': {
                'data_quality': min(100, (len(analytics_data) / 3600) * 100),  # Expect ~1 point/sec
                'coverage': 'Complete' if len(analytics_data) > 1000 else 'Partial'
            }
        }
        
        return report
    
    @staticmethod
    def _calculate_peak_hours(analytics_data: List[Dict]) -> Dict[str, int]:
        """Identify peak hours from analytics"""
        hour_totals = {}
        
        for record in analytics_data:
            if 'timestamp' in record:
                try:
                    hour = datetime.fromisoformat(record['timestamp']).hour
                    hour_totals[hour] = hour_totals.get(hour, 0) + record.get('people_count', 0)
                except:
                    pass
        
        # Return top 3 peak hours
        sorted_hours = sorted(hour_totals.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_hours[:3])
    
    @staticmethod
    def _generate_recommendations(analytics_data: List[Dict]) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        if not analytics_data:
            return recommendations
        
        avg_people = sum(a['people_count'] for a in analytics_data) / len(analytics_data)
        max_queue = max(a['queue_length'] for a in analytics_data)
        avg_wait = sum(a['average_wait_time'] for a in analytics_data) / len(analytics_data)
        
        if avg_people > 40:
            recommendations.append("Consider increasing staff during high-traffic periods")
        if max_queue > 8:
            recommendations.append("Optimize queue management - queue lengths are high")
        if avg_wait > 250:
            recommendations.append("Implement faster checkout/service process")
        if avg_people < 10:
            recommendations.append("Opportunity to reduce operational costs during low-traffic hours")
        
        recommendations.append("Monitor trends for capacity planning")
        
        return recommendations


class MultiCameraAnalytics:
    """Aggregate analytics across multiple cameras"""
    
    def __init__(self):
        self.cameras = {}
        self.global_stats = {}
    
    def add_camera_data(self, camera_id: str, analytics_data: Dict):
        """Add camera analytics data"""
        if camera_id not in self.cameras:
            self.cameras[camera_id] = []
        
        self.cameras[camera_id].append(analytics_data)
    
    def get_comparative_analysis(self, limit: int = 100) -> Dict:
        """Compare all cameras"""
        comparison = {}
        
        for camera_id, data_points in self.cameras.items():
            # Take last 'limit' records
            recent_data = data_points[-limit:] if len(data_points) > limit else data_points
            
            if recent_data:
                people_counts = [d['people_count'] for d in recent_data]
                queue_lengths = [d['queue_length'] for d in recent_data]
                
                comparison[camera_id] = {
                    'avg_people': sum(people_counts) / len(people_counts),
                    'peak_people': max(people_counts),
                    'avg_queue': sum(queue_lengths) / len(queue_lengths),
                    'peak_queue': max(queue_lengths),
                    'traffic_load': sum(people_counts)  # Total foot traffic
                }
        
        return comparison
    
    def identify_load_distribution(self) -> Dict:
        """Identify how load is distributed across cameras"""
        comparison = self.get_comparative_analysis()
        total_traffic = sum(c['traffic_load'] for c in comparison.values())
        
        distribution = {}
        for camera_id, stats in comparison.items():
            percentage = (stats['traffic_load'] / total_traffic * 100) if total_traffic > 0 else 0
            distribution[camera_id] = {
                'traffic_percentage': percentage,
                'load_level': 'High' if percentage > 50 else 'Medium' if percentage > 25 else 'Low'
            }
        
        return distribution


# Initialize engines
alert_engine = AlertEngine()
heatmap_analytics = HeatmapAnalytics()
report_generator = ReportGenerator()
multi_camera_analytics = MultiCameraAnalytics()

logger.info("Phase 7 Advanced Analytics Engine initialized")
