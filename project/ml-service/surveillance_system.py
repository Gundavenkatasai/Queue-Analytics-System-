"""
Real-time AI Queue Analytics System with Camera Support
Uses YOLOv8 for detection, ByteTrack for tracking, and sends data to Laravel API
"""

import cv2
import numpy as np
import time
import sys
import logging
from datetime import datetime
import requests
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from config import (
    API_ENDPOINT, API_TIMEOUT, CAMERA_ID, CAMERA_FPS, 
    CAMERA_WIDTH, CAMERA_HEIGHT, SEND_INTERVAL, DISPLAY_FRAME,
    DRAW_BOXES, DRAW_TRAILS, TRAIL_LENGTH, FRAME_SKIP,
    ROI, ENTRY_LINE_Y, EXIT_LINE_Y, USE_VIDEO_FALLBACK, FALLBACK_VIDEO
)
from detection.yolo_detector import PersonDetector
from tracking.byte_tracker import ByteTracker
from analytics.queue_analyzer import QueueAnalyzer
from recording.video_recorder import VideoRecorder
from utils.api_client import APIClient


class SurveillanceSystem:
    """Real-time surveillance system with camera support"""
    
    def __init__(self, use_video=False, video_path=None):
        """
        Initialize the surveillance system
        
        Args:
            use_video (bool): Use video file instead of camera
            video_path (str): Path to video file
        """
        logger.info("=" * 70)
        logger.info("🎬 AI Queue Analytics System - CAMERA MODE (Real-time)")
        logger.info("=" * 70)
        
        self.use_video = use_video or USE_VIDEO_FALLBACK
        self.video_path = video_path or FALLBACK_VIDEO
        
        # Initialize components
        try:
            logger.info("📹 Initializing camera/video...")
            self.cap = self._init_video_source()
            if not self.cap.isOpened():
                raise RuntimeError("Failed to open video source")
            logger.info("✅ Video source ready")
            
            logger.info("🧠 Loading YOLOv8 detector...")
            self.detector = PersonDetector()
            logger.info("✅ Detector loaded")
            
            logger.info("📊 Initializing ByteTracker...")
            self.tracker = ByteTracker()
            logger.info("✅ Tracker initialized")
            
            logger.info("📈 Initializing Queue Analyzer...")
            self.analyzer = QueueAnalyzer(fps=CAMERA_FPS)
            logger.info("✅ Analyzer ready")
            
            logger.info("🎥 Initializing Video Recorder...")
            self.recorder = VideoRecorder()
            logger.info("✅ Recorder ready")
            
            logger.info("🌐 Initializing API Client...")
            self.api_client = APIClient(API_ENDPOINT, timeout=API_TIMEOUT)
            logger.info("✅ API Client ready")
            
        except Exception as e:
            logger.error(f"❌ Initialization failed: {e}")
            raise
        
        # State tracking
        self.frame_count = 0
        self.last_send = time.time()
        self.fps_counter = 0
        self.fps_timer = time.time()
        self.is_running = True
        
        logger.info("✅ System initialized successfully")
        logger.info("🎯 Starting real-time processing...")
        logger.info("-" * 70)
    
    def _init_video_source(self):
        """Initialize video source (camera or video file)"""
        if self.use_video:
            logger.info(f"  📂 Using video file: {self.video_path}")
            cap = cv2.VideoCapture(self.video_path)
        else:
            logger.info(f"  📷 Using camera ID: {CAMERA_ID}")
            cap = cv2.VideoCapture(CAMERA_ID)
            # Set camera properties for faster capture
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
            cap.set(cv2.CAP_PROP_FPS, CAMERA_FPS)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffering
        
        return cap
    
    def run(self):
        """Main processing loop"""
        try:
            while self.is_running:
                ret, frame = self.cap.read()
                
                if not ret:
                    if self.use_video:
                        logger.info("📽️  Video ended, restarting...")
                        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue
                    else:
                        logger.error("❌ Failed to read frame from camera")
                        break
                
                # Resize for faster processing
                frame = cv2.resize(frame, (CAMERA_WIDTH, CAMERA_HEIGHT))
                self.frame_count += 1
                
                # Detect persons
                detections = self.detector.detect(frame)
                
                # Track persons
                tracks = self.tracker.update(detections)
                
                # Analyze queue
                analytics = self.analyzer.analyze(frame, tracks)
                
                # Record frame if needed
                self.recorder.write_frame(frame)
                
                # Draw visualizations
                if DISPLAY_FRAME or DRAW_BOXES:
                    frame = self._draw_visualizations(frame, tracks, analytics)
                
                # Display frame
                if DISPLAY_FRAME:
                    cv2.imshow('Queue Analytics', frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        self.is_running = False
                
                # Send data periodically
                current_time = time.time()
                if current_time - self.last_send >= SEND_INTERVAL:
                    self._send_analytics(analytics)
                    self.last_send = current_time
                
                # Update FPS counter
                self._update_fps()
                
        except KeyboardInterrupt:
            logger.info("\n🛑 Shutting down...")
            self._shutdown()
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            self._shutdown()
    
    def _draw_visualizations(self, frame, tracks, analytics):
        """Draw tracking and analysis visualizations"""
        frame_copy = frame.copy()
        
        # Draw ROI
        roi = ROI
        h, w = frame.shape[:2]
        roi_points = np.array([
            [int(roi['x1'] * w), int(roi['y1'] * h)],
            [int(roi['x2'] * w), int(roi['y1'] * h)],
            [int(roi['x2'] * w), int(roi['y2'] * h)],
            [int(roi['x1'] * w), int(roi['y2'] * h)]
        ], dtype=np.int32)
        cv2.polylines(frame_copy, [roi_points], True, (0, 255, 0), 2)
        
        # Draw entry/exit lines
        entry_x = w // 3
        exit_x = 2 * w // 3
        cv2.line(frame_copy, (entry_x, 0), (entry_x, h), (0, 255, 255), 2)
        cv2.line(frame_copy, (exit_x, 0), (exit_x, h), (0, 0, 255), 2)
        cv2.putText(frame_copy, "ENTRY", (entry_x - 30, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        cv2.putText(frame_copy, "EXIT", (exit_x - 20, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        # Draw tracks
        if DRAW_BOXES:
            for track in tracks:
                if track.is_confirmed():
                    x1, y1, x2, y2 = map(int, track.bbox)
                    track_id = track.track_id
                    
                    # Draw bounding box
                    cv2.rectangle(frame_copy, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(frame_copy, f"ID:{track_id}", (x1, y1 - 10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Draw analytics overlay
        cv2.putText(frame_copy, f"People: {analytics['people_count']}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame_copy, f"Queue: {analytics['queue_length']}", (10, 70),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame_copy, f"Wait: {analytics['average_wait_time']:.1f}s", (10, 110),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame_copy, f"Occupancy: {analytics['occupancy_percentage']:.1f}%", (10, 150),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        return frame_copy
    
    def _send_analytics(self, analytics):
        """Send analytics to Laravel API"""
        payload = {
            'camera_id': CAMERA_ID,
            'people_count': analytics['people_count'],
            'queue_length': analytics['queue_length'],
            'entry_count': analytics['entry_count'],
            'exit_count': analytics['exit_count'],
            'average_wait_time': analytics['average_wait_time'],
            'max_wait_time': analytics['max_wait_time'],
            'occupancy_percentage': analytics['occupancy_percentage'],
            'frame_count': self.frame_count,
            'timestamp': datetime.now().isoformat(),
            'heatmap_data': analytics.get('heatmap', None)
        }
        
        try:
            success = self.api_client.send_analytics(payload)
            status_icon = "✅" if success else "❌"
            logger.info(f"{status_icon} Frame: {self.frame_count:>5d} | People: {payload['people_count']:>2d} | "
                       f"Queue: {payload['queue_length']:>2d} | Wait: {payload['average_wait_time']:>5.1f}s | "
                       f"Occupancy: {payload['occupancy_percentage']:>5.1f}% | "
                       f"Entries: {payload['entry_count']:>3d} | Exits: {payload['exit_count']:>3d}")
        except Exception as e:
            logger.warning(f"❌ Failed to send analytics: {str(e)[:60]}")
    
    def _update_fps(self):
        """Update and log FPS"""
        self.fps_counter += 1
        elapsed = time.time() - self.fps_timer
        if elapsed >= 5:  # Update every 5 seconds
            fps = self.fps_counter / elapsed
            logger.debug(f"⚡ FPS: {fps:.1f}")
            self.fps_counter = 0
            self.fps_timer = time.time()
    
    def _shutdown(self):
        """Clean shutdown"""
        logger.info(f"\n📊 Total frames processed: {self.frame_count}")
        
        try:
            self.cap.release()
            self.recorder.stop()
            cv2.destroyAllWindows()
        except:
            pass
        
        logger.info("✅ System stopped")


def main():
    """Entry point - Start surveillance system"""
    try:
        # Determine if we should use video or camera
        use_video = USE_VIDEO_FALLBACK
        video_path = FALLBACK_VIDEO if use_video else None
        
        system = SurveillanceSystem(use_video=use_video, video_path=video_path)
        system.run()
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
