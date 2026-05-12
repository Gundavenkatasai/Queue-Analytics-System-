import cv2
import os
import time
from datetime import datetime
from utils.config import (
    FRAME_SIZE, OUTPUT_FPS, RECORDING_CODEC,
    INACTIVITY_TIMEOUT, STORAGE_PATH
)

class VideoRecorder:
    """Automatic video recording with frame overlays"""
    
    def __init__(self):
        self.video_writer = None
        self.recording = False
        self.start_time = None
        self.last_frame_time = None
        self.current_filename = None
        self.current_filepath = None
        self.frame_count = 0
        self.total_people_count = 0
        self.people_counts = []
        
    def start_recording(self):
        """Start a new video recording"""
        if self.recording:
            return
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.current_filename = f"{timestamp}.mp4"
        self.current_filepath = os.path.join(STORAGE_PATH, self.current_filename)
        
        # Initialize video writer
        fourcc = cv2.VideoWriter_fourcc(*RECORDING_CODEC)
        self.video_writer = cv2.VideoWriter(
            self.current_filepath,
            fourcc,
            OUTPUT_FPS,
            FRAME_SIZE
        )
        
        if not self.video_writer.isOpened():
            raise RuntimeError(f"Failed to open video writer for {self.current_filepath}")
        
        self.recording = True
        self.start_time = time.time()
        self.last_frame_time = time.time()
        self.frame_count = 0
        self.people_counts = []
        
        print(f"✓ Recording started: {self.current_filename}")
    
    def write_frame(self, frame, tracked_objects, fps=0, people_count=0):
        """
        Write frame with overlays to video
        
        Args:
            frame: Input frame (will be resized to FRAME_SIZE if needed)
            tracked_objects: List of tracked objects with bbox, track_id
            fps: Current FPS for overlay
            people_count: Current people count
        """
        if not self.recording or self.video_writer is None:
            self.start_recording()
        
        # Ensure frame is correct size
        if frame.shape[:2] != FRAME_SIZE[::-1]:
            frame = cv2.resize(frame, FRAME_SIZE)
        
        # Draw overlays
        frame_with_overlays = self._draw_overlays(
            frame.copy(),
            tracked_objects,
            fps,
            people_count
        )
        
        # Write frame
        self.video_writer.write(frame_with_overlays)
        self.frame_count += 1
        self.last_frame_time = time.time()
        self.people_counts.append(people_count)
        
        return frame_with_overlays
    
    def _draw_overlays(self, frame, tracked_objects, fps, people_count):
        """Draw bounding boxes, IDs, and analytics on frame"""
        # Draw tracked objects
        for obj in tracked_objects:
            x1, y1, x2, y2 = [int(v) for v in obj['bbox']]
            track_id = obj['track_id']
            confidence = obj['confidence']
            
            # Color based on track ID
            color = self._get_color_for_id(track_id)
            
            # Draw bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            
            # Draw track ID
            text = f"ID {track_id}"
            cv2.putText(frame, text, (x1, y1 - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
            # Draw confidence
            conf_text = f"{confidence:.2f}"
            cv2.putText(frame, conf_text, (x1, y2 + 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
        # FPS counter (top-right)
        fps_text = f"FPS: {fps:.1f}"
        cv2.putText(frame, fps_text, (FRAME_SIZE[0] - 150, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Timestamp (bottom-left)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, timestamp, (10, FRAME_SIZE[1] - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        
        # People count (top-left)
        count_text = f"People: {people_count}"
        cv2.putText(frame, count_text, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        
        # Recording indicator (flashing red dot)
        if int(time.time() * 2) % 2 == 0:  # Blink every 0.5s
            cv2.circle(frame, (FRAME_SIZE[0] - 20, 20), 8, (0, 0, 255), -1)
        
        return frame
    
    def _get_color_for_id(self, track_id):
        """Generate consistent color for track ID"""
        colors = [
            (0, 255, 0),      # Green
            (0, 0, 255),      # Blue
            (255, 0, 0),      # Red
            (0, 255, 255),    # Yellow
            (255, 0, 255),    # Magenta
            (255, 255, 0),    # Cyan
        ]
        return colors[track_id % len(colors)]
    
    def should_stop_recording(self):
        """Check if recording should stop due to inactivity"""
        if not self.recording or self.last_frame_time is None:
            return False
        
        time_since_last_frame = time.time() - self.last_frame_time
        return time_since_last_frame > INACTIVITY_TIMEOUT
    
    def stop_recording(self):
        """Stop recording and get metadata"""
        if not self.recording or self.video_writer is None:
            return None
        
        self.video_writer.release()
        self.recording = False
        
        # Calculate metadata
        duration = time.time() - self.start_time if self.start_time else 0
        avg_people = sum(self.people_counts) / len(self.people_counts) if self.people_counts else 0
        file_size = os.path.getsize(self.current_filepath) if os.path.exists(self.current_filepath) else 0
        
        metadata = {
            'filename': self.current_filename,
            'filepath': self.current_filepath,
            'duration_seconds': int(duration),
            'people_count': int(avg_people),
            'frame_count': self.frame_count,
            'file_size_bytes': file_size,
            'fps': OUTPUT_FPS
        }
        
        print(f"✓ Recording stopped: {self.current_filename} ({int(duration)}s, {self.frame_count} frames)")
        
        # Reset
        self.video_writer = None
        self.start_time = None
        self.last_frame_time = None
        self.frame_count = 0
        self.people_counts = []
        
        return metadata
    
    def get_current_recording_info(self):
        """Get info about current recording"""
        if not self.recording or self.start_time is None:
            return None
        
        duration = time.time() - self.start_time
        return {
            'filename': self.current_filename,
            'duration': int(duration),
            'frame_count': self.frame_count,
            'recording': self.recording
        }
