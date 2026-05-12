"""
Frame Processor - Real-time person detection and queue analytics
Processes YOLO detections, tracks persons, classifies queue zones
"""

import numpy as np
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

class FrameProcessor:
    """Process video frames for detection and analytics"""
    
    def __init__(self, roi_bounds=(0, 0, 1280, 720), entry_line_y=200, exit_line_y=650):
        """
        Initialize processor with ROI and entry/exit zones
        
        Args:
            roi_bounds: (x_min, y_min, x_max, y_max) normalized to frame
            entry_line_y: Y coordinate for entry detection
            exit_line_y: Y coordinate for exit detection
        """
        self.roi_bounds = roi_bounds
        self.entry_line_y = entry_line_y
        self.exit_line_y = exit_line_y
        
        # Track person states
        self.tracked_persons = {}  # track_id -> {status, entry_time, positions}
        self.person_counter = 0
        
        # Statistics
        self.entries = 0
        self.exits = 0
        self.max_wait_time = 0
        self.occupancy_percentage = 0
        
        # Heatmap grid (20x20)
        self.heatmap_grid = np.zeros((20, 20), dtype=np.int32)
        self.grid_width = roi_bounds[2] - roi_bounds[0]
        self.grid_height = roi_bounds[3] - roi_bounds[1]
        
        logger.info(f"✅ FrameProcessor initialized with ROI {roi_bounds}")
    
    def process_detections(self, frame, detections, tracker):
        """
        Process YOLO detections and track persons
        
        Args:
            frame: Video frame (H x W x 3)
            detections: List of (x1, y1, x2, y2, conf, class_id)
            tracker: ByteTrack tracker instance
        
        Returns:
            dict with analytics for this frame
        """
        h, w = frame.shape[:2]
        
        # Update tracker with detections
        tracked_objects = []
        for det in detections:
            x1, y1, x2, y2, conf, cls_id = det
            # Format: [x1, y1, x2, y2, score, class_id]
            tracked_objects.append([x1, y1, x2, y2, conf, cls_id])
        
        # Get tracked objects from ByteTrack
        online_targets = tracker.update(np.array(tracked_objects) if tracked_objects else np.empty((0, 6)))
        
        # Initialize frame analytics
        frame_analytics = {
            'people_count': 0,
            'queue_length': 0,
            'entry_count': 0,
            'exit_count': 0,
            'average_wait_time': 0,
            'max_wait_time': 0,
            'occupancy_percentage': 0,
            'detected_boxes': [],
            'heatmap_data': [],
        }
        
        # Reset heatmap for this frame
        frame_heatmap = np.zeros((20, 20), dtype=np.int32)
        
        # Process each tracked person
        people_in_queue = 0
        total_wait_times = []
        
        for target in online_targets:
            track_id = target.track_id
            x1, y1, x2, y2 = target.tlbr  # Top-left bottom-right
            
            # Calculate centroid
            cx = int((x1 + x2) / 2)
            cy = int((y1 + y2) / 2)
            
            # Check if in ROI
            if not self._is_in_roi(cx, cy):
                continue
            
            frame_analytics['people_count'] += 1
            
            # Classify person status (entry/exit/queue)
            status = self._classify_person(track_id, cy)
            
            if status == 'entered':
                frame_analytics['entry_count'] += 1
                logger.debug(f"Person {track_id} ENTERED")
            elif status == 'exited':
                frame_analytics['exit_count'] += 1
                logger.debug(f"Person {track_id} EXITED")
            elif status == 'in_queue':
                people_in_queue += 1
                # Calculate wait time
                wait_time = self.tracked_persons[track_id]['wait_time']
                total_wait_times.append(wait_time)
            
            # Update bounding box
            frame_analytics['detected_boxes'].append({
                'track_id': track_id,
                'x1': int(x1), 'y1': int(y1),
                'x2': int(x2), 'y2': int(y2),
                'cx': cx, 'cy': cy,
                'status': status,
                'confidence': float(target.score) if hasattr(target, 'score') else 0.0
            })
            
            # Update heatmap
            grid_x, grid_y = self._get_grid_coords(cx, cy)
            frame_heatmap[grid_y, grid_x] += 1
        
        # Calculate queue metrics
        frame_analytics['queue_length'] = people_in_queue
        frame_analytics['average_wait_time'] = np.mean(total_wait_times) if total_wait_times else 0
        frame_analytics['max_wait_time'] = max(total_wait_times) if total_wait_times else 0
        
        # Occupancy percentage
        roi_area = (self.roi_bounds[2] - self.roi_bounds[0]) * (self.roi_bounds[3] - self.roi_bounds[1])
        max_capacity = int(roi_area / 10000)  # Rough estimate: 1 person per 10000 pixels
        frame_analytics['occupancy_percentage'] = min(100, (frame_analytics['people_count'] / max(1, max_capacity)) * 100)
        
        # Convert heatmap to sparse format for storage
        for y in range(20):
            for x in range(20):
                if frame_heatmap[y, x] > 0:
                    frame_analytics['heatmap_data'].append({
                        'x': x, 'y': y, 'count': int(frame_heatmap[y, x])
                    })
        
        return frame_analytics
    
    def _is_in_roi(self, x, y):
        """Check if point is in region of interest"""
        x_min, y_min, x_max, y_max = self.roi_bounds
        return x_min <= x <= x_max and y_min <= y <= y_max
    
    def _get_grid_coords(self, x, y):
        """Convert frame coordinates to 20x20 grid coordinates"""
        x_min, y_min, x_max, y_max = self.roi_bounds
        
        grid_x = int(((x - x_min) / self.grid_width) * 20)
        grid_y = int(((y - y_min) / self.grid_height) * 20)
        
        grid_x = max(0, min(19, grid_x))
        grid_y = max(0, min(19, grid_y))
        
        return grid_x, grid_y
    
    def _classify_person(self, track_id, y_pos):
        """
        Classify person status: entered / exited / in_queue
        
        Args:
            track_id: Unique person ID
            y_pos: Y position in frame
        
        Returns:
            str: 'entered', 'exited', 'in_queue', or 'unknown'
        """
        import time
        
        if track_id not in self.tracked_persons:
            # New person detected
            self.tracked_persons[track_id] = {
                'status': 'unknown',
                'entry_time': time.time(),
                'positions': [y_pos],
                'entry_detected': False,
                'exit_detected': False,
            }
            return 'unknown'
        
        person = self.tracked_persons[track_id]
        person['positions'].append(y_pos)
        current_status = 'unknown'
        
        # Detect entry (crossing entry line going down)
        if not person['entry_detected'] and y_pos > self.entry_line_y:
            if len(person['positions']) > 2 and person['positions'][-2] <= self.entry_line_y:
                person['entry_detected'] = True
                person['status'] = 'in_queue'
                self.entries += 1
                current_status = 'entered'
        
        # Detect exit (crossing exit line going down)
        if not person['exit_detected'] and y_pos > self.exit_line_y:
            if len(person['positions']) > 2 and person['positions'][-2] <= self.exit_line_y:
                person['exit_detected'] = True
                self.exits += 1
                current_status = 'exited'
                # Clean up tracked person
                del self.tracked_persons[track_id]
        
        # Update wait time
        if 'wait_time' not in person:
            person['wait_time'] = 0
        else:
            person['wait_time'] = time.time() - person['entry_time']
        
        # Return status if changed, else current status
        if current_status != 'unknown':
            return current_status
        return person['status']
    
    def get_heatmap_grid(self):
        """Get current heatmap as 20x20 grid"""
        return self.heatmap_grid.tolist()
