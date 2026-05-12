import json
import logging
from pymongo import MongoClient
from datetime import datetime
from utils.config import MONGODB_URL, MONGODB_DATABASE

logger = logging.getLogger(__name__)

class MongoDBClient:
    """MongoDB Atlas Client for Analytics Storage"""
    
    def __init__(self):
        try:
            self.client = MongoClient(MONGODB_URL, serverSelectionTimeoutMS=5000)
            self.client.server_info()  # Test connection
            self.db = self.client[MONGODB_DATABASE]
            logger.info("✓ Connected to MongoDB Atlas")
        except Exception as e:
            logger.error(f"✗ Failed to connect to MongoDB: {e}")
            self.client = None
            self.db = None
    
    def is_connected(self):
        """Check if connected to MongoDB"""
        return self.db is not None
    
    def insert_analytics(self, analytics_data):
        """Insert analytics record"""
        if not self.is_connected():
            logger.warning("Not connected to MongoDB, skipping insert")
            return None
        
        try:
            analytics_data['timestamp'] = datetime.utcnow()
            analytics_data['created_at'] = datetime.utcnow()
            
            collection = self.db['analytics']
            result = collection.insert_one(analytics_data)
            return result.inserted_id
        except Exception as e:
            logger.error(f"Error inserting analytics: {e}")
            return None
    
    def insert_recording(self, recording_metadata):
        """Insert recording metadata"""
        if not self.is_connected():
            logger.warning("Not connected to MongoDB, skipping recording insert")
            return None
        
        try:
            recording_metadata['created_at'] = datetime.utcnow()
            recording_metadata['updated_at'] = datetime.utcnow()
            
            collection = self.db['recordings']
            result = collection.insert_one(recording_metadata)
            return result.inserted_id
        except Exception as e:
            logger.error(f"Error inserting recording: {e}")
            return None
    
    def get_latest_analytics(self, camera_id='camera_1', limit=1):
        """Get latest analytics records"""
        if not self.is_connected():
            return []
        
        try:
            collection = self.db['analytics']
            records = list(collection.find(
                {'camera_id': camera_id}
            ).sort('_id', -1).limit(limit))
            
            # Convert ObjectId to string for JSON serialization
            for record in records:
                record['_id'] = str(record['_id'])
                if 'timestamp' in record:
                    record['timestamp'] = record['timestamp'].isoformat()
            
            return records
        except Exception as e:
            logger.error(f"Error fetching analytics: {e}")
            return []
    
    def get_historical_analytics(self, camera_id='camera_1', limit=100):
        """Get historical analytics data"""
        if not self.is_connected():
            return []
        
        try:
            collection = self.db['analytics']
            records = list(collection.find(
                {'camera_id': camera_id}
            ).sort('_id', -1).limit(limit))
            
            # Convert for JSON
            for record in records:
                record['_id'] = str(record['_id'])
                if 'timestamp' in record:
                    record['timestamp'] = record['timestamp'].isoformat()
            
            return list(reversed(records))  # Chronological order
        except Exception as e:
            logger.error(f"Error fetching historical analytics: {e}")
            return []
    
    def create_alert(self, camera_id, alert_type, severity, message, analytics_data):
        """Create alert record"""
        if not self.is_connected():
            logger.warning("Not connected to MongoDB, skipping alert creation")
            return None
        
        try:
            alert = {
                'camera_id': camera_id,
                'alert_type': alert_type,
                'severity': severity,
                'message': message,
                'people_count': analytics_data.get('people_count', 0),
                'queue_length': analytics_data.get('queue_length', 0),
                'occupancy_percentage': analytics_data.get('occupancy_percentage', 0),
                'acknowledged': False,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            collection = self.db['alerts']
            result = collection.insert_one(alert)
            logger.info(f"Alert created: {alert_type} ({severity})")
            return result.inserted_id
        except Exception as e:
            logger.error(f"Error creating alert: {e}")
            return None
    
    def insert_heatmap_snapshot(self, camera_id, date_str, hour, heatmap_matrix):
        """Insert hourly heatmap snapshot"""
        if not self.is_connected():
            return None
        
        try:
            heatmap_doc = {
                'camera_id': camera_id,
                'date': date_str,
                'hour': hour,
                'heatmap_matrix': heatmap_matrix.tolist(),  # Convert numpy to list
                'created_at': datetime.utcnow()
            }
            
            collection = self.db['heatmap_snapshots']
            result = collection.insert_one(heatmap_doc)
            return result.inserted_id
        except Exception as e:
            logger.error(f"Error inserting heatmap: {e}")
            return None
    
    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("✓ MongoDB connection closed")


# Initialize global client
db_client = None

def init_db_client():
    """Initialize global database client"""
    global db_client
    db_client = MongoDBClient()
    return db_client

def get_db_client():
    """Get global database client"""
    global db_client
    if db_client is None:
        db_client = init_db_client()
    return db_client
