import numpy as np
from collections import defaultdict
from utils.config import (
    ROI_POINTS, MAX_QUEUE_CAPACITY, HEATMAP_GRID_SIZE,
    FRAME_SIZE
)

class QueueAnalyzer:
    """Queue and congestion analytics"""
    
    def __init__(self, fps=30):
        self.fps = fps
        self.roi_points = ROI_POINTS
        self.entry_count = 0
        self.exit_count = 0
        self.total_people_entered = 0
        self.total_people_exited = 0
        self.previous_in_roi = set()
        self.person_entry_times = {}  # track_id -> frame_number
        self.heatmap_data = []  # List of (x, y, timestamp)
        
    def analyze(self, tracked_objects, frame_count):
        """
        Analyze queue and generate analytics
        
        Returns:
            analytics dict with queue_length, entry_count, exit_count, etc.
        """
        current_in_roi = set()
        
        for obj in tracked_objects:
            track_id = obj['track_id']
            in_roi = obj['in_roi']
            
            if in_roi:
                current_in_roi.add(track_id)
                
                # Record entry time if first time entering
                if track_id not in self.person_entry_times:
                    self.person_entry_times[track_id] = frame_count
                
                # Add to heatmap
                cx, cy = obj['center']
                self.heatmap_data.append((cx, cy, frame_count))
        
        # Detect entries and exits
        new_entries = current_in_roi - self.previous_in_roi
        exits = self.previous_in_roi - current_in_roi
        
        self.entry_count += len(new_entries)
        self.exit_count += len(exits)
        self.total_people_entered += len(new_entries)
        self.total_people_exited += len(exits)
        
        # Calculate wait times
        wait_times = []
        for track_id in current_in_roi:
            if track_id in self.person_entry_times:
                frames_in_queue = frame_count - self.person_entry_times[track_id]
                wait_time_seconds = frames_in_queue / self.fps
                wait_times.append(wait_time_seconds)
        
        avg_wait_time = np.mean(wait_times) if wait_times else 0
        max_wait_time = np.max(wait_times) if wait_times else 0
        
        # Queue metrics
        queue_length = len(current_in_roi)
        occupancy_percentage = (queue_length / MAX_QUEUE_CAPACITY) * 100
        
        # Clean up exited persons
        for track_id in exits:
            if track_id in self.person_entry_times:
                del self.person_entry_times[track_id]
        
        self.previous_in_roi = current_in_roi
        
        analytics = {
            'people_count': len(tracked_objects),
            'queue_length': queue_length,
            'entry_count': self.total_people_entered,
            'exit_count': self.total_people_exited,
            'average_wait_time': float(avg_wait_time),
            'max_wait_time': float(max_wait_time),
            'occupancy_percentage': float(occupancy_percentage),
            'frame_count': frame_count
        }
        
        return analytics
    
    def get_heatmap_matrix(self, grid_size=HEATMAP_GRID_SIZE):
        """
        Generate heatmap matrix from collected position data
        
        Returns:
            numpy array of shape (grid_size, grid_size) with density values
        """
        if not self.heatmap_data:
            return np.zeros((grid_size, grid_size))
        
        heatmap = np.zeros((grid_size, grid_size))
        
        frame_w, frame_h = FRAME_SIZE
        cell_w = frame_w / grid_size
        cell_h = frame_h / grid_size
        
        for x, y, _ in self.heatmap_data:
            # Map coordinates to grid
            grid_x = min(int(x / cell_w), grid_size - 1)
            grid_y = min(int(y / cell_h), grid_size - 1)
            
            heatmap[grid_y, grid_x] += 1
        
        # Normalize to 0-1 range
        if np.max(heatmap) > 0:
            heatmap = heatmap / np.max(heatmap)
        
        return heatmap
    
    def get_heatmap_data_json(self):
        """Get heatmap data as JSON-serializable list"""
        return [
            {
                'x': int(x),
                'y': int(y),
                'frame': frame_count
            }
            for x, y, frame_count in self.heatmap_data[-1000:]  # Keep last 1000 points
        ]
    
    def reset_daily_stats(self):
        """Reset daily statistics (called daily)"""
        self.entry_count = 0
        self.exit_count = 0
        self.heatmap_data = []
        print("✓ Daily stats reset")
    
    def reset_heatmap(self):
        """Reset heatmap data"""
        self.heatmap_data = []
    
    def get_stats(self):
        """Get current analytics statistics"""
        return {
            'total_entries': self.total_people_entered,
            'total_exits': self.total_people_exited,
            'current_queue': len(self.previous_in_roi),
            'heatmap_points': len(self.heatmap_data),
            'tracked_people': len(self.person_entry_times)
        }
