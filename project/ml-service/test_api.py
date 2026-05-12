#!/usr/bin/env python3
"""Quick test to verify Flask API is working"""

import requests
import json

API_URL = "http://localhost:8001/api/analytics"

test_data = {
    'camera_id': 'camera_1',
    'people_count': 25,
    'queue_length': 5,
    'entry_count': 100,
    'exit_count': 50,
    'occupancy_percentage': 50.0,
    'queue_detected': True,
    'dwell_time_avg': 45.5,
    'dwell_time_max': 120.3,
    'avg_wait_time': 12.5,
    'timestamp': '2026-05-11T14:35:00'
}

print(f"Testing API: {API_URL}")
print(f"Payload: {json.dumps(test_data, indent=2)}\n")

try:
    response = requests.post(
        API_URL,
        json=test_data,
        timeout=5,
        headers={'Content-Type': 'application/json'}
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}\n")
    
    if response.status_code == 201 or response.status_code == 200:
        print("✓ API test PASSED!")
    else:
        print("✗ API test FAILED!")
        
except Exception as e:
    print(f"✗ Error: {str(e)}")
