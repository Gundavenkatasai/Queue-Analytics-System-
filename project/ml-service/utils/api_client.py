import requests
import json
import logging
import time
from utils.config import (
    LARAVEL_API_URL, API_TIMEOUT, API_RETRY_ATTEMPTS,
    API_RETRY_DELAY, API_ANALYTICS_ENDPOINT, API_RECORDINGS_ENDPOINT
)

logger = logging.getLogger(__name__)

class APIClient:
    """HTTP Client for Laravel Backend Communication"""
    
    def __init__(self, base_url=LARAVEL_API_URL, timeout=API_TIMEOUT):
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()
        
    def _make_request(self, method, endpoint, data=None, retry=True):
        """
        Make HTTP request with retry logic
        
        Args:
            method: 'POST', 'GET', 'PUT', etc.
            endpoint: API endpoint path
            data: Request body (dict)
            retry: Whether to retry on failure
            
        Returns:
            Response JSON or None on failure
        """
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(API_RETRY_ATTEMPTS):
            try:
                if method == 'POST':
                    response = self.session.post(
                        url,
                        json=data,
                        timeout=self.timeout,
                        headers={'Content-Type': 'application/json'}
                    )
                elif method == 'GET':
                    response = self.session.get(
                        url,
                        timeout=self.timeout
                    )
                elif method == 'PUT':
                    response = self.session.put(
                        url,
                        json=data,
                        timeout=self.timeout,
                        headers={'Content-Type': 'application/json'}
                    )
                else:
                    logger.error(f"Unsupported method: {method}")
                    return None
                
                response.raise_for_status()
                return response.json() if response.text else {'status': 'success'}
                
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"Connection error (attempt {attempt + 1}/{API_RETRY_ATTEMPTS}): {e}")
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout error (attempt {attempt + 1}/{API_RETRY_ATTEMPTS})")
            except requests.exceptions.HTTPError as e:
                logger.error(f"HTTP error: {e.response.status_code}")
                return None
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                return None
            
            if attempt < API_RETRY_ATTEMPTS - 1 and retry:
                time.sleep(API_RETRY_DELAY * (attempt + 1))  # Exponential backoff
        
        logger.error(f"Failed to reach {url} after {API_RETRY_ATTEMPTS} attempts")
        return None
    
    def post_analytics(self, analytics_data):
        """
        POST analytics data to Laravel backend
        
        Args:
            analytics_data: Dict with queue metrics
            
        Returns:
            True if successful, False otherwise
        """
        response = self._make_request('POST', API_ANALYTICS_ENDPOINT, analytics_data)
        
        if response:
            logger.debug(f"✓ Analytics posted: {analytics_data.get('people_count')} people")
            return True
        else:
            logger.warning("✗ Failed to post analytics")
            return False
    
    def post_recording_metadata(self, recording_metadata):
        """
        POST recording metadata to Laravel backend
        
        Args:
            recording_metadata: Dict with video metadata
            
        Returns:
            True if successful, False otherwise
        """
        response = self._make_request('POST', API_RECORDINGS_ENDPOINT, recording_metadata)
        
        if response:
            logger.debug(f"✓ Recording metadata posted: {recording_metadata.get('filename')}")
            return True
        else:
            logger.warning("✗ Failed to post recording metadata")
            return False
    
    def get_stats(self):
        """GET latest stats from Laravel backend"""
        return self._make_request('GET', '/api/stats')
    
    def health_check(self):
        """Check if Laravel API is alive"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/health",
                timeout=2
            )
            return response.status_code == 200
        except:
            return False


# Global API client instance
api_client = None

def init_api_client(base_url=LARAVEL_API_URL):
    """Initialize global API client"""
    global api_client
    api_client = APIClient(base_url)
    return api_client

def get_api_client():
    """Get global API client"""
    global api_client
    if api_client is None:
        api_client = init_api_client()
    return api_client
