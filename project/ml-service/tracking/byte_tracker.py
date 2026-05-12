import cv2
import numpy as np
from collections import defaultdict
from utils.config import TRACKING_MAX_AGE, TRACKING_MIN_HITS, TRACK_BUFFER

class Track:
    """Represents a tracked person"""
    
    def __init__(self, track_id, detection, frame_count):
        self.track_id = track_id
        self.bbox = detection['bbox']  # [x1, y1, x2, y2]
        self.center = (detection['center_x'], detection['center_y'])
        self.confidence = detection['confidence']
        self.age = 1
        self.hits = 1
        self.last_frame = frame_count
        self.frame_history = [frame_count]
        self.bbox_history = [self.bbox]
        self.position_history = [self.center]
        
    def update(self, detection, frame_count):
        """Update track with new detection"""
        self.bbox = detection['bbox']
        self.center = (detection['center_x'], detection['center_y'])
        self.confidence = detection['confidence']
        self.age += 1
        self.hits += 1
        self.last_frame = frame_count
        self.frame_history.append(frame_count)
        self.bbox_history.append(self.bbox)
        self.position_history.append(self.center)
        
        # Keep history limited
        if len(self.frame_history) > TRACK_BUFFER:
            self.frame_history.pop(0)
            self.bbox_history.pop(0)
            self.position_history.pop(0)
    
    def miss(self):
        """Mark a missed detection"""
        self.age += 1
    
    def is_valid(self):
        """Check if track is valid (confirmed)"""
        return self.hits >= TRACKING_MIN_HITS
    
    def is_stale(self):
        """Check if track is too old"""
        return self.age > TRACKING_MAX_AGE
    
    def get_wait_time_frames(self):
        """Get how many frames this person has been tracked"""
        if self.frame_history:
            return self.frame_history[-1] - self.frame_history[0]
        return 0


class ByteTracker:
    """ByteTrack Multi-Object Tracker"""
    
    def __init__(self):
        self.active_tracks = {}
        self.inactive_tracks = {}
        self.next_track_id = 1
        self.frame_count = 0
        self.entry_count = 0
        self.exit_count = 0
        
    def update(self, detections, roi_points=None):
        """
        Update tracker with new detections
        
        Args:
            detections: List of detection dicts
            roi_points: Optional polygon points for ROI (queue area)
            
        Returns:
            tracked_objects: List of active tracked objects with IDs
        """
        self.frame_count += 1
        
        # Assignment: match detections to tracks
        matched_tracks = set()
        
        for detection in detections:
            best_track_id = None
            best_distance = float('inf')
            
            # Find closest track
            for track_id, track in self.active_tracks.items():
                if track_id in matched_tracks:
                    continue
                
                distance = self._iou_distance(track.bbox, detection['bbox'])
                
                if distance < 0.3:  # IoU threshold
                    if distance < best_distance:
                        best_distance = distance
                        best_track_id = track_id
            
            # Update or create track
            if best_track_id is not None:
                self.active_tracks[best_track_id].update(detection, self.frame_count)
                matched_tracks.add(best_track_id)
            else:
                # Create new track
                new_track_id = self.next_track_id
                self.next_track_id += 1
                self.active_tracks[new_track_id] = Track(new_track_id, detection, self.frame_count)
                matched_tracks.add(new_track_id)
        
        # Mark unmatched tracks as inactive
        unmatched_track_ids = set(self.active_tracks.keys()) - matched_tracks
        for track_id in unmatched_track_ids:
            track = self.active_tracks[track_id]
            track.miss()
            
            if track.is_stale():
                self.inactive_tracks[track_id] = self.active_tracks.pop(track_id)
        
        # Remove stale inactive tracks
        stale_ids = [tid for tid, t in self.inactive_tracks.items() if t.is_stale()]
        for tid in stale_ids:
            del self.inactive_tracks[tid]
        
        # Build output
        tracked_objects = []
        for track_id, track in self.active_tracks.items():
            if track.is_valid():
                tracked_objects.append({
                    'track_id': track_id,
                    'bbox': track.bbox,
                    'center': track.center,
                    'confidence': track.confidence,
                    'age': track.age,
                    'hits': track.hits,
                    'wait_time_frames': track.get_wait_time_frames(),
                    'in_roi': self._point_in_polygon(track.center, roi_points) if roi_points else True
                })
        
        return tracked_objects
    
    def _iou_distance(self, bbox1, bbox2):
        """Calculate Intersection over Union distance"""
        x1_min, y1_min, x1_max, y1_max = bbox1
        x2_min, y2_min, x2_max, y2_max = bbox2
        
        # Intersection
        xi_min = max(x1_min, x2_min)
        yi_min = max(y1_min, y2_min)
        xi_max = min(x1_max, x2_max)
        yi_max = min(y1_max, y2_max)
        
        inter_area = max(0, xi_max - xi_min) * max(0, yi_max - yi_min)
        
        # Union
        box1_area = (x1_max - x1_min) * (y1_max - y1_min)
        box2_area = (x2_max - x2_min) * (y2_max - y2_min)
        union_area = box1_area + box2_area - inter_area
        
        iou = inter_area / union_area if union_area > 0 else 0
        return 1 - iou  # Return distance (lower is better)
    
    def _point_in_polygon(self, point, polygon_points):
        """Check if point is inside polygon using ray casting"""
        if not polygon_points or len(polygon_points) < 3:
            return True
        
        x, y = point
        n = len(polygon_points)
        inside = False
        
        p1x, p1y = polygon_points[0]
        for i in range(1, n + 1):
            p2x, p2y = polygon_points[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        
        return inside
    
    def get_stats(self):
        """Get current tracker statistics"""
        return {
            'active_tracks': len(self.active_tracks),
            'inactive_tracks': len(self.inactive_tracks),
            'total_tracks': len(self.active_tracks) + len(self.inactive_tracks),
            'frame_count': self.frame_count
        }
