"""
Simple Flask Backend API for Queue Analytics
Receives data from ML service and serves it to frontend
"""

from flask import Flask, request, jsonify
try:
    from flask_cors import CORS
    CORS_AVAILABLE = True
except ImportError:
    CORS_AVAILABLE = False
from datetime import datetime, timedelta
from collections import deque
import threading
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
if CORS_AVAILABLE:
    CORS(app)  # Enable CORS for all routes
else:
    logger.warning("flask_cors not available, installing manually")
    # Add manual CORS headers
    @app.after_request
    def add_cors_headers(response):
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response

# In-memory data storage
data_storage = deque(maxlen=1000)  # Keep last 1000 records
current_stats = {
    'people_count': 0,
    'queue_length': 0,
    'entry_count': 0,
    'exit_count': 0,
    'timestamp': datetime.now().isoformat()
}
lock = threading.Lock()


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()}), 200


@app.route('/api/analytics', methods=['POST'])
def receive_analytics():
    """
    Receive analytics data from ML service
    Expected payload: {
        'camera_id': str (optional),
        'people_count': int,
        'queue_length': int,
        'entry_count': int,
        'exit_count': int,
        'occupancy_percentage': float (optional),
        'queue_detected': bool (optional),
        'dwell_time_avg': float (optional),
        'dwell_time_max': float (optional),
        'avg_wait_time': float (optional),
        'timestamp': ISO8601 string
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400
        
        # Validate required fields
        required_fields = ['people_count', 'queue_length', 'entry_count', 'exit_count']
        for field in required_fields:
            if field not in data:
                return jsonify({'status': 'error', 'message': f'Missing field: {field}'}), 400
        
        # Store data
        with lock:
            current_stats['camera_id'] = data.get('camera_id', 'default')
            current_stats['people_count'] = data['people_count']
            current_stats['queue_length'] = data['queue_length']
            current_stats['entry_count'] = data['entry_count']
            current_stats['exit_count'] = data['exit_count']
            current_stats['occupancy_percentage'] = data.get('occupancy_percentage', 0)
            current_stats['queue_detected'] = data.get('queue_detected', False)
            current_stats['dwell_time_avg'] = data.get('dwell_time_avg', 0)
            current_stats['dwell_time_max'] = data.get('dwell_time_max', 0)
            current_stats['avg_wait_time'] = data.get('avg_wait_time', 0)
            current_stats['timestamp'] = data.get('timestamp', datetime.now().isoformat())
            
            # Also store in history
            data_storage.append({
                'camera_id': data.get('camera_id', 'default'),
                'people_count': data['people_count'],
                'queue_length': data['queue_length'],
                'entry_count': data['entry_count'],
                'exit_count': data['exit_count'],
                'occupancy_percentage': data.get('occupancy_percentage', 0),
                'queue_detected': data.get('queue_detected', False),
                'dwell_time_avg': data.get('dwell_time_avg', 0),
                'dwell_time_max': data.get('dwell_time_max', 0),
                'avg_wait_time': data.get('avg_wait_time', 0),
                'created_at': data.get('timestamp', datetime.now().isoformat())
            })
        
        logger.info(f"Received analytics: People={data['people_count']}, Queue={data['queue_length']}, Occupancy={data.get('occupancy_percentage', 0):.1f}%")
        
        return jsonify({
            'status': 'success',
            'message': 'Data received',
            'data': current_stats
        }), 201
    
    except Exception as e:
        logger.error(f"Error processing analytics: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get current statistics"""
    with lock:
        return jsonify({
            'status': 'success',
            'data': current_stats
        }), 200


@app.route('/api/history', methods=['GET'])
def get_history():
    """Get historical data"""
    limit = request.args.get('limit', default=100, type=int)
    
    with lock:
        history = list(data_storage)[-limit:] if data_storage else []
    
    return jsonify({
        'status': 'success',
        'data': history,
        'count': len(history)
    }), 200


@app.route('/api/stats-summary', methods=['GET'])
def get_stats_summary():
    """Get statistics summary for a time period"""
    minutes = request.args.get('minutes', default=60, type=int)
    
    with lock:
        if not data_storage:
            return jsonify({
                'status': 'success',
                'data': {
                    'avg_people_count': 0,
                    'max_people_count': 0,
                    'avg_queue_length': 0,
                    'max_queue_length': 0,
                    'total_entries': 0,
                    'total_exits': 0,
                }
            }), 200
        
        # Calculate stats
        people_counts = [d['people_count'] for d in data_storage]
        queue_lengths = [d['queue_length'] for d in data_storage]
        
        summary = {
            'avg_people_count': sum(people_counts) / len(people_counts) if people_counts else 0,
            'max_people_count': max(people_counts) if people_counts else 0,
            'avg_queue_length': sum(queue_lengths) / len(queue_lengths) if queue_lengths else 0,
            'max_queue_length': max(queue_lengths) if queue_lengths else 0,
            'total_entries': data_storage[-1]['entry_count'] if data_storage else 0,
            'total_exits': data_storage[-1]['exit_count'] if data_storage else 0,
        }
    
    return jsonify({
        'status': 'success',
        'data': summary
    }), 200


@app.route('/', methods=['GET'])
def index():
    """Root endpoint"""
    return jsonify({
        'message': 'Queue Analytics API Server',
        'version': '1.0',
        'endpoints': {
            'GET /api/health': 'Health check',
            'POST /api/analytics': 'Receive analytics data',
            'GET /api/stats': 'Get current statistics',
            'GET /api/history': 'Get historical data',
            'GET /api/stats-summary': 'Get statistics summary',
        }
    }), 200


if __name__ == '__main__':
    logger.info("Starting Queue Analytics API Server...")
    logger.info("Server running on http://localhost:8001")
    app.run(host='0.0.0.0', port=8001, debug=False)
