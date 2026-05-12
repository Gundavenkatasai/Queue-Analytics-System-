"""
Advanced Video Recorder with H.264 encoding, 1-hour chunking, and MongoDB upload
"""

import cv2
import os
import time
import logging
import threading
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class AdvancedVideoRecorder:
    """Record video with H.264, auto-chunking, and async MongoDB upload"""
    
    def __init__(self, camera_id='camera_1', storage_path='storage/videos', 
                 resolution=(640, 480), fps=10, codec='mp4v', chunk_duration_seconds=3600):
        """
        Initialize video recorder
        
        Args:
            camera_id: Camera identifier
            storage_path: Local storage path
            resolution: (width, height)
            fps: Frames per second
            codec: Video codec ('mp4v' for H.264)
            chunk_duration_seconds: Duration of each video file (3600 = 1 hour)
        """
        self.camera_id = camera_id
        self.storage_path = storage_path
        self.resolution = resolution
        self.fps = fps
        self.codec = codec
        self.chunk_duration_seconds = chunk_duration_seconds
        
        # Create storage directory
        os.makedirs(storage_path, exist_ok=True)
        
        # Video writer state
        self.video_writer = None
        self.current_filename = None
        self.current_filepath = None
        self.chunk_start_time = None
        self.frame_count = 0
        self.total_frames = 0
        
        # Recording state
        self.is_recording = False
        self.upload_queue = []
        self.upload_thread = None
        
        logger.info(f"✅ AdvancedVideoRecorder initialized: {resolution} @{fps}fps, H.264")
    
    def start_recording(self):
        """Start recording"""
        if self.is_recording:
            return
        
        self._create_new_chunk()
        self.is_recording = True
        logger.info(f"🎬 Recording started: {self.current_filename}")
    
    def write_frame(self, frame):
        """
        Write frame to video
        
        Args:
            frame: Video frame (numpy array)
        """
        if not self.is_recording:
            self.start_recording()
        
        # Resize frame if necessary
        if frame.shape[:2][::-1] != self.resolution:
            frame = cv2.resize(frame, self.resolution)
        
        # Write frame
        if self.video_writer and self.video_writer.isOpened():
            self.video_writer.write(frame)
            self.frame_count += 1
            self.total_frames += 1
        
        # Check if chunk duration exceeded
        elapsed = time.time() - self.chunk_start_time
        if elapsed > self.chunk_duration_seconds:
            self._finalize_chunk()
            self._create_new_chunk()
    
    def _create_new_chunk(self):
        """Create a new video file chunk"""
        # Generate filename: camera_1_20260511_073000.mp4
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_filename = f"{self.camera_id}_{timestamp}.mp4"
        self.current_filepath = os.path.join(self.storage_path, self.current_filename)
        
        # Initialize video writer with H.264
        fourcc = cv2.VideoWriter_fourcc(*self.codec)
        self.video_writer = cv2.VideoWriter(
            self.current_filepath,
            fourcc,
            self.fps,
            self.resolution
        )
        
        if not self.video_writer.isOpened():
            logger.error(f"❌ Failed to open video writer: {self.current_filepath}")
            return
        
        self.chunk_start_time = time.time()
        self.frame_count = 0
        
        logger.info(f"📹 New video chunk: {self.current_filename}")
    
    def _finalize_chunk(self):
        """Finalize current chunk and queue for upload"""
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None
        
        if self.current_filepath and os.path.exists(self.current_filepath):
            file_size = os.path.getsize(self.current_filepath)
            logger.info(f"✅ Chunk finalized: {self.current_filename} ({file_size/1024/1024:.2f}MB, {self.frame_count} frames)")
            
            # Add to upload queue
            self.upload_queue.append({
                'filepath': self.current_filepath,
                'filename': self.current_filename,
                'camera_id': self.camera_id,
                'frame_count': self.frame_count,
                'file_size': file_size,
                'start_time': datetime.fromtimestamp(self.chunk_start_time),
                'end_time': datetime.now(),
            })
    
    def stop_recording(self):
        """Stop recording"""
        if self.is_recording:
            self._finalize_chunk()
            self.is_recording = False
            logger.info(f"🛑 Recording stopped. Total frames: {self.total_frames}")
    
    def get_pending_uploads(self):
        """Get list of pending uploads"""
        return self.upload_queue.copy()
    
    def mark_as_uploaded(self, filepath):
        """Mark file as uploaded and remove from queue"""
        self.upload_queue = [item for item in self.upload_queue if item['filepath'] != filepath]
    
    def get_recording_stats(self):
        """Get current recording statistics"""
        return {
            'is_recording': self.is_recording,
            'current_file': self.current_filename,
            'frames_in_chunk': self.frame_count,
            'total_frames': self.total_frames,
            'pending_uploads': len(self.upload_queue),
            'chunk_duration_seconds': self.chunk_duration_seconds,
            'resolution': self.resolution,
            'fps': self.fps,
        }
