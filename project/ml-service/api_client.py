"""
REST API Client for Laravel Backend Integration
"""

import requests
import json
import time
from config import API_ENDPOINT, API_TIMEOUT
from datetime import datetime, timezone


class APIClient:
    """Sends analytics data to Laravel backend"""

    def __init__(self, api_url=API_ENDPOINT):
        """
        Initialize API client

        Args:
            api_url: Laravel API endpoint URL
        """
        self.api_url = api_url
        self.timeout = API_TIMEOUT
        self.last_response = None
        self.error_count = 0

    def send_analytics(self, analytics_data):
        """
        Send analytics data to Laravel backend

        Args:
            analytics_data: Dict with keys:
                - people_count
                - queue_length
                - entry_count
                - exit_count

        Returns:
            success: Boolean indicating success
            response: Response dict or error message
        """
        try:
            payload = {
                'camera_id': 'camera_1',
                'people_count': analytics_data.get('people_count', 0),
                'queue_length': analytics_data.get('queue_length', 0),
                'entry_count': analytics_data.get('entry_count', 0),
                'exit_count': analytics_data.get('exit_count', 0),
                'occupancy_percentage': analytics_data.get('occupancy_percentage', 0),
                'queue_detected': analytics_data.get('queue_detected', False),
                'dwell_time_avg': analytics_data.get('dwell_time_avg', 0),
                'dwell_time_max': analytics_data.get('dwell_time_max', 0),
                'avg_wait_time': analytics_data.get('avg_wait_time', 0),
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'peak_hours': json.dumps([]),
                'heatmap_data': json.dumps([]),
                'session_id': 'default_session',
                'alert_status': 'normal'
            }

            response = requests.post(
                self.api_url,
                json=payload,
                timeout=self.timeout,
                headers={'Content-Type': 'application/json'}
            )

            if response.status_code == 201 or response.status_code == 200:
                self.error_count = 0
                try:
                    self.last_response = response.json()
                except:
                    self.last_response = {'status': 'success'}
                return True, self.last_response
            else:
                self.error_count += 1
                error_msg = f"HTTP {response.status_code}: {response.text}"
                return False, error_msg

        except requests.exceptions.Timeout:
            self.error_count += 1
            return False, f"Timeout: API did not respond within {self.timeout}s"
        except requests.exceptions.ConnectionError as e:
            self.error_count += 1
            return False, f"Connection error: {str(e)}"
        except Exception as e:
            self.error_count += 1
            return False, f"Error: {str(e)}"

    def get_health(self):
        """
        Check if Laravel API is healthy

        Returns:
            healthy: Boolean
            message: Status message
        """
        try:
            response = requests.get(
                self.api_url.replace('/analytics', '/health'),
                timeout=self.timeout
            )
            return response.status_code == 200, "API is healthy"
        except:
            return False, "API is unreachable"

    def get_last_response(self):
        """Get last successful API response"""
        return self.last_response

    def get_error_count(self):
        """Get number of consecutive errors"""
        return self.error_count
