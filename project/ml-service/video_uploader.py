"""
Video Uploader - Upload recorded videos to MongoDB GridFS
Handles file upload, metadata storage, and retention policy
"""

import os
import logging
from datetime import datetime, timedelta
import pymongo
from pymongo.errors import OperationFailure

logger = logging.getLogger(__name__)

class VideoUploader:
    """Upload video files to MongoDB GridFS"""
    
    def __init__(self, mongodb_uri, database_name='surveillance_db', retention_days=30):
        """
        Initialize uploader
        
        Args:
            mongodb_uri: MongoDB connection string
            database_name: Database name
            retention_days: Days to keep recordings (default 30)
        """
        self.mongodb_uri = mongodb_uri
        self.database_name = database_name
        self.retention_days = retention_days
        self.client = None
        self.db = None
        self.fs = None
        
        try:
            self.connect()
            logger.info(f"✅ VideoUploader ready (retention: {retention_days} days)")
        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            self.client = None
    
    def connect(self):
        """Connect to MongoDB"""
        from pymongo.gridfs import GridFS
        
        self.client = pymongo.MongoClient(self.mongodb_uri, serverSelectionTimeoutMS=5000)
        # Test connection
        self.client.admin.command('ping')
        self.db = self.client[self.database_name]
        self.fs = GridFS(self.db)
        logger.info("✅ Connected to MongoDB")
    
    def upload_video(self, video_path, camera_id, start_time, end_time, metadata=None):
        """
        Upload video file to MongoDB GridFS
        
        Args:
            video_path: Local path to video file
            camera_id: Camera identifier
            start_time: Recording start time (datetime)
            end_time: Recording end time (datetime)
            metadata: Additional metadata dict
        
        Returns:
            dict with upload status and file_id
        """
        if not self.client:
            logger.warning("⚠️  MongoDB not connected, storing metadata locally")
            return self._store_metadata_locally(video_path, camera_id, start_time, end_time)
        
        try:
            if not os.path.exists(video_path):
                logger.error(f"❌ Video file not found: {video_path}")
                return {'status': 'error', 'message': 'File not found', 'file_id': None}
            
            # Get file info
            file_size = os.path.getsize(video_path)
            filename = os.path.basename(video_path)
            
            # Prepare metadata
            file_metadata = {
                'camera_id': camera_id,
                'start_time': start_time,
                'end_time': end_time,
                'duration_seconds': int((end_time - start_time).total_seconds()),
                'file_size_bytes': file_size,
                'uploaded_at': datetime.utcnow(),
                'codec': 'H.264',
                'resolution': '640x480',
                'fps': 10,
            }
            
            if metadata:
                file_metadata.update(metadata)
            
            # Upload to GridFS
            with open(video_path, 'rb') as f:
                file_id = self.fs.put(
                    f,
                    filename=filename,
                    metadata=file_metadata,
                    content_type='video/mp4'
                )
            
            logger.info(f"✅ Uploaded video: {filename} (ID: {file_id}, Size: {file_size/1024/1024:.2f}MB)")
            
            # Store metadata in recordings collection
            self._store_recording_metadata(file_id, camera_id, filename, start_time, end_time, file_size)
            
            # Clean up old files
            self._cleanup_old_recordings(camera_id)
            
            return {
                'status': 'success',
                'file_id': str(file_id),
                'filename': filename,
                'file_size_bytes': file_size,
            }
        
        except Exception as e:
            logger.error(f"❌ Upload failed: {e}")
            return {'status': 'error', 'message': str(e), 'file_id': None}
    
    def _store_recording_metadata(self, file_id, camera_id, filename, start_time, end_time, file_size):
        """Store recording metadata in MongoDB recordings collection"""
        try:
            self.db.recordings.insert_one({
                'mongodb_file_id': file_id,
                'camera_id': camera_id,
                'filename': filename,
                'start_time': start_time,
                'end_time': end_time,
                'duration_seconds': int((end_time - start_time).total_seconds()),
                'file_size_bytes': file_size,
                'is_uploaded': True,
                'upload_status': 'completed',
                'created_at': datetime.utcnow(),
            })
            logger.info(f"✅ Metadata stored for {filename}")
        except Exception as e:
            logger.error(f"❌ Failed to store metadata: {e}")
    
    def _cleanup_old_recordings(self, camera_id):
        """Delete recordings older than retention period"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)
            
            # Find old recordings
            old_records = self.db.recordings.find({
                'camera_id': camera_id,
                'created_at': {'$lt': cutoff_date}
            })
            
            deleted_count = 0
            for record in old_records:
                try:
                    # Delete from GridFS
                    self.fs.delete(record['mongodb_file_id'])
                    # Delete metadata
                    self.db.recordings.delete_one({'_id': record['_id']})
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"❌ Failed to delete old recording: {e}")
            
            if deleted_count > 0:
                logger.info(f"🧹 Cleaned up {deleted_count} old recordings (retention: {self.retention_days} days)")
        
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")
    
    def _store_metadata_locally(self, video_path, camera_id, start_time, end_time):
        """Fallback: Store metadata locally if MongoDB unavailable"""
        import json
        
        try:
            metadata_file = video_path.replace('.mp4', '.metadata.json')
            metadata = {
                'filename': os.path.basename(video_path),
                'camera_id': camera_id,
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'file_size_bytes': os.path.getsize(video_path),
                'stored_at': datetime.utcnow().isoformat(),
                'status': 'local_only',
            }
            
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"📝 Metadata stored locally: {metadata_file}")
            return {
                'status': 'success_local',
                'file_id': None,
                'filename': os.path.basename(video_path),
            }
        except Exception as e:
            logger.error(f"❌ Local storage failed: {e}")
            return {'status': 'error', 'message': str(e), 'file_id': None}
    
    def get_recording_by_date(self, camera_id, date):
        """Get all recordings for a specific date"""
        if not self.client:
            return []
        
        try:
            from datetime import date as date_type
            if isinstance(date, str):
                date = datetime.strptime(date, '%Y-%m-%d').date()
            
            start_of_day = datetime.combine(date, datetime.min.time())
            end_of_day = datetime.combine(date, datetime.max.time())
            
            recordings = self.db.recordings.find({
                'camera_id': camera_id,
                'start_time': {'$gte': start_of_day, '$lte': end_of_day}
            }).sort('start_time', 1)
            
            return list(recordings)
        except Exception as e:
            logger.error(f"❌ Failed to get recordings: {e}")
            return []
    
    def stream_recording(self, file_id):
        """Stream recording chunks from GridFS"""
        if not self.client:
            return None
        
        try:
            from bson import ObjectId
            grid_out = self.fs.get(ObjectId(file_id))
            return grid_out.read()
        except Exception as e:
            logger.error(f"❌ Failed to stream recording: {e}")
            return None
    
    def get_storage_stats(self, camera_id):
        """Get storage statistics for camera"""
        if not self.client:
            return {'total_bytes': 0, 'total_recordings': 0}
        
        try:
            stats = self.db.recordings.aggregate([
                {'$match': {'camera_id': camera_id}},
                {
                    '$group': {
                        '_id': camera_id,
                        'total_bytes': {'$sum': '$file_size_bytes'},
                        'count': {'$sum': 1}
                    }
                }
            ])
            
            result = next(stats, None)
            if result:
                return {
                    'total_bytes': result['total_bytes'],
                    'total_gb': round(result['total_bytes'] / (1024**3), 2),
                    'total_recordings': result['count'],
                }
            return {'total_bytes': 0, 'total_recordings': 0, 'total_gb': 0}
        except Exception as e:
            logger.error(f"❌ Failed to get storage stats: {e}")
            return {'total_bytes': 0, 'total_recordings': 0}
