"""
Real-Time Detection Engine with All Analytics
- 15 FPS person detection
- Entry/exit tracking
- Queue detection
- Occupancy tracking
- Dwell time per person
- Peak hour tracking
- Heatmap generation
"""

import cv2
import numpy as np
from ultralytics import YOLO
from collections import deque, defaultdict
from datetime import datetime, timedelta, timezone
import threading
import queue as thread_queue
import logging
from face_recognizer import FaceRecognizer

logger = logging.getLogger(__name__)

class PersonTracker:
    """Track individual persons across frames"""
    def __init__(self):
        self.tracks = {}
        self.track_id = 0
        self.next_track_id = 0
        
    def update(self, detections):
        """
        detections: list of [x1, y1, x2, y2, conf] from YOLO
        Returns: list of [x1, y1, x2, y2, conf, track_id]
        """
        # Simple centroid tracking
        centroids_detected = []
        for det in detections:
            cx = (det[0] + det[2]) / 2
            cy = (det[1] + det[3]) / 2
            centroids_detected.append((cx, cy, det))
        
        # Match centroids to existing tracks
        used_tracks = set()
        matched_detections = []
        
        for cx, cy, det in centroids_detected:
            min_dist = float('inf')
            best_track = None
            
            for track_id, track_info in self.tracks.items():
                if track_id in used_tracks:
                    continue
                    
                last_cx, last_cy = track_info['last_position']
                dist = np.sqrt((cx - last_cx)**2 + (cy - last_cy)**2)
                
                if dist < 100 and dist < min_dist:  # Matching threshold (increased from 50 to 100 for robust tracking)
                    min_dist = dist
                    best_track = track_id
            
            if best_track is not None:
                used_tracks.add(best_track)
                previous_position = self.tracks[best_track].get('last_position')
                self.tracks[best_track]['prev_position'] = previous_position
                self.tracks[best_track]['last_position'] = (cx, cy)
                
                # Maintain X-coordinate history for robust line crossing checks
                if 'x_history' not in self.tracks[best_track]:
                    self.tracks[best_track]['x_history'] = []
                self.tracks[best_track]['x_history'].append(cx)
                if len(self.tracks[best_track]['x_history']) > 30:
                    self.tracks[best_track]['x_history'].pop(0)
                    
                self.tracks[best_track]['frames_seen'] += 1
                self.tracks[best_track]['last_seen'] = datetime.now()
                matched_detections.append((*det, best_track))
            else:
                # New track
                self.next_track_id += 1
                self.tracks[self.next_track_id] = {
                    'last_position': (cx, cy),
                    'prev_position': None,
                    'first_seen': datetime.now(),
                    'last_seen': datetime.now(),
                    'frames_seen': 1,
                    'missed_frames': 0,
                    'entry_line': None,
                    'exit_line': None,
                    'x_history': [cx]
                }
                matched_detections.append((*det, self.next_track_id))

        for track_id, track_info in self.tracks.items():
            if track_id not in used_tracks:
                track_info['missed_frames'] = track_info.get('missed_frames', 0) + 1
            else:
                track_info['missed_frames'] = 0
        
        # Remove stale tracks only after several missed frames to keep IDs stable
        stale_tracks = [tid for tid, info in self.tracks.items()
                       if info.get('missed_frames', 0) > 15]
        for tid in stale_tracks:
            del self.tracks[tid]
        
        return matched_detections


class RealTimeDetectionEngine:
    """Main detection engine with all analytics"""
    
    def __init__(self, fps=15, resolution=(640, 480), alert_threshold=50):
        self.fps = fps
        self.resolution = resolution
        self.alert_threshold = alert_threshold
        self.frame_skip = max(1, 30 // fps)  # Skip frames to maintain FPS
        self.frame_count = 0
        
        import torch
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.half = self.device == 'cuda'  # Use FP16 on GPU
        
        # Allow ultralytics model loading in PyTorch 2.6+
        try:
            torch.serialization.add_safe_globals([
                __import__('ultralytics.nn.tasks', fromlist=['DetectionModel']).DetectionModel,
                __import__('ultralytics.nn.modules.head', fromlist=['Detect']).Detect,
            ])
        except:
            pass  # Older PyTorch versions don't have this
        
        # Load YOLOv8m
        self.model = YOLO('yolov8m.pt')
        try:
            if self.device == 'cuda':
                self.model.to('cuda')
                logger.info("✓ Loaded YOLO model on CUDA GPU")
        except Exception as e:
            logger.warning(f"⚠️ CUDA loading failed, falling back to CPU: {e}")
            self.device = 'cpu'
            self.half = False
            self.model.to('cpu')
        self.tracker = PersonTracker()
        
        # Analytics tracking
        self.people_history = deque(maxlen=300)  # Keep 20 seconds of history at 15 FPS
        self.entry_count = 0
        self.exit_count = 0
        self.queue_detected = False
        self.queue_length = 0
        
        # Heatmap: 20x20 grid
        self.heatmap_grid = np.zeros((20, 20), dtype=np.float32)
        self.heatmap_grid_timestamp = datetime.now()
        
        # Peak hours tracking (24 hours)
        self.hourly_counts = defaultdict(lambda: {'total': 0, 'count': 0})
        
        # Dwell time tracking
        self.dwell_times = []  # [person_id, duration_seconds]
        
        # Entry/exit guides (vertical lines so movement is easy to read left-to-right)
        self.entry_line_x = self.resolution[0] // 3
        self.exit_line_x = 2 * self.resolution[0] // 3
        self.line_margin = 20
        
        # Face recognition
        self.face_recognizer = FaceRecognizer()
        self.known_face_ids = {} # track_id -> face_id
        self.processed_face_ids = set() # Track unique people counted in current session
        
        logger.info(f"Detection engine initialized: {fps} FPS, {resolution}")
    
    def detect_persons(self, frame):
        """Detect persons in frame using YOLOv8"""
        try:
            results = self.model(frame, classes=0, conf=0.5, half=self.half, verbose=False)  # Class 0 = person
        except Exception as e:
            logger.warning(f"⚠️ Inference failed on device {self.device}, dynamically falling back to CPU: {e}")
            self.device = 'cpu'
            self.half = False
            try:
                self.model.to('cpu')
            except:
                pass
            results = self.model(frame, classes=0, conf=0.5, half=False, verbose=False)
        
        detections = []
        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = box.conf[0].cpu().numpy()
                detections.append([float(x1), float(y1), float(x2), float(y2), float(conf)])
        
        return detections
    
    def detect_entry_exit(self, tracked_persons, frame):
        """Detect persons crossing entry/exit lines with bidirectional counting.
        
        Layout (left to right):
          0                    entry_line_x (1/3)         exit_line_x (2/3)              W
          |-------- OUTSIDE ---|---- ZONE 1 (pre-entry) ---|---- ZONE 2 (inside) --------|EXIT SIDE
        
        ENTRY event: person crosses the YELLOW line (entry_line_x) from LEFT → RIGHT.
        EXIT  event: person crosses the RED line    (exit_line_x)  from RIGHT → LEFT.
                     (i.e. walking OUT, back through the exit/red line toward the camera)
        """
        for det in tracked_persons:
            x1, y1, x2, y2, conf, track_id = det
            cx = (x1 + x2) / 2
            
            track_info = self.tracker.tracks.get(track_id)
            if not track_info:
                continue

            if track_info.get('frames_seen', 0) < 2:
                continue
            
            x_hist = track_info.get('x_history', [])
            if len(x_hist) < 2:
                continue

            prev_cx = x_hist[-2] if len(x_hist) >= 2 else x_hist[0]

            # ── ENTRY: yellow line crossed left-to-right ─────────────────────
            # Only fire once per track
            if track_info.get('entry_line') is None:
                # Previous position was LEFT of entry line, current is RIGHT of entry line
                if prev_cx < self.entry_line_x <= cx:
                    track_info['entry_line'] = True
                    self.entry_count += 1
                    logger.info(f"ENTRY detected: track={track_id}, prev_cx={prev_cx:.0f} -> cx={cx:.0f} (Total entries: {self.entry_count})")

            # ── EXIT: red line crossed right-to-left ─────────────────────────
            # A person walking OUT moves from right of the exit line to the left.
            # Only fire once per track.
            if track_info.get('exit_line') is None:
                # Previous position was RIGHT of exit line, current is LEFT of exit line
                if prev_cx > self.exit_line_x >= cx:
                    track_info['exit_line'] = True
                    self.exit_count += 1
                    logger.info(f"EXIT detected: track={track_id}, prev_cx={prev_cx:.0f} -> cx={cx:.0f} (Total exits: {self.exit_count})")

    def draw_overlay(self, frame, tracked_persons, occupancy, dwell):
        """Draw detection overlays, including yellow/red counting guides."""
        overlay = frame.copy()
        self.draw_static_guides(overlay)

        # Detection boxes and labels
        for det in tracked_persons:
            x1, y1, x2, y2, conf, track_id = det
            x1, y1, x2, y2 = map(int, [x1, y1, x2, y2])
            track_info = self.tracker.tracks.get(track_id, {})
            color = (0, 255, 255) if track_info.get('entry_line') is None else (0, 200, 80)
            if track_info.get('exit_line') is not None:
                color = (0, 0, 255)

            cv2.rectangle(overlay, (x1, y1), (x2, y2), color, 2)
            cv2.putText(
                overlay,
                f"ID {track_id}",
                (x1, max(20, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                2,
            )

        # Summary panel
        panel_y = 24
        cv2.rectangle(overlay, (10, 10), (300, 120), (0, 0, 0), -1)
        cv2.rectangle(overlay, (10, 10), (300, 120), (255, 255, 255), 1)
        cv2.putText(overlay, f"People: {len(tracked_persons)}", (20, panel_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(overlay, f"Entry: {self.entry_count}", (20, panel_y + 28), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        cv2.putText(overlay, f"Exit: {self.exit_count}", (160, panel_y + 28), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        cv2.putText(overlay, f"Occ: {occupancy:.1f}%", (20, panel_y + 56), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(overlay, f"Dwell Avg: {dwell['avg']:.1f}s", (20, panel_y + 84), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        return overlay

    def draw_static_guides(self, frame):
        """Draw the entry/exit guide lines on any frame."""
        cv2.line(frame, (self.entry_line_x, 0), (self.entry_line_x, self.resolution[1]), (0, 255, 255), 2)
        cv2.line(frame, (self.exit_line_x, 0), (self.exit_line_x, self.resolution[1]), (0, 0, 255), 2)
        cv2.putText(frame, "ENTER>", (self.entry_line_x - 35, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)
        cv2.putText(frame, "<EXIT", (self.exit_line_x - 30, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2)
    
    def detect_queue(self, tracked_persons):
        """Detect queue formation (multiple people close together)"""
        if len(tracked_persons) < 3:
            self.queue_detected = False
            self.queue_length = 0
            return
        
        # Calculate distances between persons
        positions = [(((det[0] + det[2])/2, (det[1] + det[3])/2)) for det in tracked_persons]
        
        # Sort by Y position (vertical)
        positions.sort(key=lambda p: p[1])
        
        # Find clusters of close persons
        queue_candidates = []
        for i in range(len(positions) - 1):
            dy = positions[i+1][1] - positions[i][1]
            dx = abs(positions[i+1][0] - positions[i][0])
            
            # If persons are vertically aligned and close
            if 0 < dy < 80 and dx < 150:
                queue_candidates.append((i, i+1))
        
        # Detect queue if multiple pairs form a line
        if len(queue_candidates) >= 2:
            self.queue_detected = True
            self.queue_length = len(tracked_persons)  # Simplified
            logger.info(f"Queue detected: {self.queue_length} persons")
        else:
            self.queue_detected = False
            self.queue_length = 0
    
    def calculate_occupancy(self, tracked_persons):
        """Calculate occupancy percentage based on alert_threshold"""
        max_persons = self.alert_threshold  # Use configurable capacity
        current_count = len(tracked_persons)
        occupancy = (current_count / max(1, max_persons)) * 100
        return min(occupancy, 100)
    
    def update_heatmap(self, tracked_persons):
        """Update heatmap grid with person positions"""
        current_hour = datetime.now().hour
        
        for det in tracked_persons:
            x1, y1, x2, y2, conf, track_id = det
            cx = ((x1 + x2) / 2) / self.resolution[0]
            cy = ((y1 + y2) / 2) / self.resolution[1]
            
            grid_x = int(cx * 20)
            grid_y = int(cy * 20)
            
            grid_x = max(0, min(19, grid_x))
            grid_y = max(0, min(19, grid_y))
            
            self.heatmap_grid[grid_y, grid_x] += 1
            
            # Smooth heatmap (blur)
            # This is done on the grid directly
        
        # Track hourly stats
        self.hourly_counts[current_hour]['total'] += len(tracked_persons)
        self.hourly_counts[current_hour]['count'] += 1
    
    def calculate_dwell_time(self):
        """Calculate average dwell time of tracked persons"""
        dwell_times = []
        for track_id, track_info in self.tracker.tracks.items():
            dwell_time = (datetime.now() - track_info['first_seen']).total_seconds()
            dwell_times.append(dwell_time)
        
        if dwell_times:
            return {
                'avg': np.mean(dwell_times),
                'max': np.max(dwell_times),
                'min': np.min(dwell_times)
            }
        return {'avg': 0, 'max': 0, 'min': 0}
    
    def get_peak_hours(self):
        """Get peak hour analysis"""
        peaks = sorted(self.hourly_counts.items(), 
                      key=lambda x: x[1]['total'], reverse=True)
        return peaks[:5]  # Top 5 hours
    
    def reset_hourly_heatmap(self):
        """Reset heatmap for new hour"""
        now = datetime.now()
        if (now - self.heatmap_grid_timestamp).total_seconds() > 3600:
            self.heatmap_grid = np.zeros((20, 20), dtype=np.float32)
            self.heatmap_grid_timestamp = now
            logger.info("Heatmap reset for new hour")
    
    def process_frame(self, frame):
        """Process single frame and return analytics"""
        self.frame_count += 1
        
        if self.frame_count % self.frame_skip != 0:
            return None
        
        # Resize frame
        frame = cv2.resize(frame, self.resolution)
        
        # Detect persons
        detections = self.detect_persons(frame)
        
        # Track persons
        tracked_persons = self.tracker.update(detections)
        
        # Detect entry/exit
        self.detect_entry_exit(tracked_persons, frame)
        
        # Detect queue
        self.detect_queue(tracked_persons)
        
        # Calculate occupancy
        occupancy = self.calculate_occupancy(tracked_persons)
        
        # Update heatmap
        self.update_heatmap(tracked_persons)
        
        # Reset hourly data if needed
        self.reset_hourly_heatmap()
        
        # Dwell time
        dwell = self.calculate_dwell_time()
        
        # Peak hours
        peak_hours = self.get_peak_hours()
        
        current_count = len(tracked_persons)
        self.people_history.append({
            'timestamp': datetime.now(),
            'count': current_count,
            'occupancy': occupancy
        })

        # Smooth and normalize heatmap for transmission
        if np.sum(self.heatmap_grid) > 0:
            smoothed = cv2.GaussianBlur(self.heatmap_grid, (5, 5), 0)
            # Normalize to 0-255 for visualization
            normalized = cv2.normalize(smoothed, None, 0, 255, cv2.NORM_MINMAX)
            heatmap_list = normalized.tolist()
        else:
            heatmap_list = [[0] * 20 for _ in range(20)]

        # Create analytics summary
        annotated_frame = self.draw_overlay(frame, tracked_persons, occupancy, dwell)

        analytics = {
            'camera_id': 'camera_1',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'people_count': len(tracked_persons),
            'occupancy_percentage': occupancy,
            'entry_count': self.entry_count,
            'exit_count': self.exit_count,
            'queue_detected': self.queue_length > 3,
            'queue_length': self.queue_length,
            'dwell_time_avg': round(dwell['avg'], 2),
            'dwell_time_max': round(dwell['max'], 2),
            'peak_hours': self.hourly_counts,
            'heatmap': heatmap_list,
            'frame': annotated_frame
        }
        
        logger.info(f"Frame {self.frame_count}: {current_count} people, "
                   f"Occupancy: {occupancy:.1f}%, "
                   f"Entry: {self.entry_count}, Exit: {self.exit_count}, "
                   f"Queue: {self.queue_detected}")
        
        return analytics


def test_detection_engine():
    """Test detection engine with webcam"""
    engine = RealTimeDetectionEngine(fps=15, resolution=(640, 480))
    
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)
    
    logger.info("Starting detection engine test...")
    
    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        analytics = engine.process_frame(frame)
        
        if analytics:
            frame_count += 1
            logger.info(f"Analytics generated: {frame_count} frames processed")
        
        # Press 'q' to quit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    logger.info("Detection engine test completed")


if __name__ == "__main__":
    test_detection_engine()
