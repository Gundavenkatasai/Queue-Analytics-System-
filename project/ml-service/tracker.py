"""
ByteTrack Person Tracking Module
"""

import numpy as np
from collections import defaultdict
import cv2


class SimpleByteTracker:
    """
    Simplified multi-object tracker using centroid-based association
    Assigns unique IDs to detected persons across frames
    """

    def __init__(self, max_age=30, min_hits=3):
        """
        Initialize tracker

        Args:
            max_age: Max frames to keep inactive track
            min_hits: Minimum detections to confirm track
        """
        self.max_age = max_age
        self.min_hits = min_hits
        self.track_id_counter = 0
        self.tracks = {}  # {track_id: track_data}
        self.lost_tracks = {}
        self.centroid_distance_threshold = 50

    def update(self, detections):
        """
        Update tracker with new detections

        Args:
            detections: List of dicts with 'bbox' and 'confidence'

        Returns:
            tracks: List of dicts with:
                - track_id: unique ID
                - bbox: [x1, y1, x2, y2]
                - centroid: [cx, cy]
                - confidence: confidence score
                - status: 'tracked' or 'lost'
        """
        # Convert detections to centroids
        centroids = self._get_centroids(detections)

        # Match detections to existing tracks
        matched_detections = set()
        matched_tracks = set()

        # Calculate distances
        if self.tracks and centroids:
            matches = self._match_detections_to_tracks(centroids)
            for track_id, det_idx in matches:
                matched_tracks.add(track_id)
                matched_detections.add(det_idx)
                # Update track
                self.tracks[track_id]['bbox'] = detections[det_idx]['bbox']
                self.tracks[track_id]['centroid'] = centroids[det_idx]
                self.tracks[track_id]['confidence'] = detections[det_idx]['confidence']
                self.tracks[track_id]['hits'] += 1
                self.tracks[track_id]['age'] = 0

        # Create new tracks for unmatched detections
        for det_idx, det in enumerate(detections):
            if det_idx not in matched_detections:
                self.track_id_counter += 1
                self.tracks[self.track_id_counter] = {
                    'track_id': self.track_id_counter,
                    'bbox': det['bbox'],
                    'centroid': centroids[det_idx],
                    'confidence': det['confidence'],
                    'hits': 1,
                    'age': 0
                }

        # Age existing tracks
        tracks_to_remove = []
        for track_id in self.tracks:
            if track_id not in matched_tracks:
                self.tracks[track_id]['age'] += 1
                if self.tracks[track_id]['age'] > self.max_age:
                    tracks_to_remove.append(track_id)

        # Remove aged out tracks
        for track_id in tracks_to_remove:
            del self.tracks[track_id]

        # Return confirmed tracks
        confirmed_tracks = [
            track for track in self.tracks.values()
            if track['hits'] >= self.min_hits
        ]

        return confirmed_tracks

    def _get_centroids(self, detections):
        """Calculate centroid for each detection"""
        centroids = []
        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2
            centroids.append([cx, cy])
        return centroids

    def _match_detections_to_tracks(self, centroids):
        """
        Match detections to existing tracks using centroid distance

        Returns:
            matches: List of (track_id, detection_idx) tuples
        """
        matches = []

        # Convert tracks dict to list for distance calculation
        track_centroids = {
            track_id: track['centroid']
            for track_id, track in self.tracks.items()
        }

        # Simple greedy matching
        for det_idx, det_centroid in enumerate(centroids):
            if not track_centroids:
                continue

            # Find closest track
            min_distance = float('inf')
            closest_track_id = None

            for track_id, track_centroid in track_centroids.items():
                distance = np.sqrt(
                    (det_centroid[0] - track_centroid[0]) ** 2 +
                    (det_centroid[1] - track_centroid[1]) ** 2
                )
                if distance < min_distance:
                    min_distance = distance
                    closest_track_id = track_id

            # Match if within threshold and not already matched
            if (closest_track_id is not None and
                min_distance < self.centroid_distance_threshold and
                closest_track_id not in [m[0] for m in matches]):
                matches.append((closest_track_id, det_idx))
                del track_centroids[closest_track_id]

        return matches

    def draw_tracks(self, frame, tracks, draw_trails=False, trails=None):
        """
        Draw tracks on frame

        Args:
            frame: Input frame
            tracks: List of track dicts
            draw_trails: Whether to draw tracking trails
            trails: Dict of track_id -> list of centroids

        Returns:
            frame: Annotated frame
        """
        for track in tracks:
            x1, y1, x2, y2 = track['bbox']
            track_id = track['track_id']
            cx, cy = track['centroid']

            # Draw bounding box
            color = self._id_to_color(track_id)
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)

            # Draw track ID
            cv2.putText(frame, f"ID: {track_id}", (int(x1), int(y1) - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            # Draw centroid
            cv2.circle(frame, (int(cx), int(cy)), 5, color, -1)

            # Draw trail if enabled
            if draw_trails and trails and track_id in trails:
                trail = trails[track_id]
                for i in range(1, len(trail)):
                    cv2.line(frame, (int(trail[i-1][0]), int(trail[i-1][1])),
                             (int(trail[i][0]), int(trail[i][1])), color, 1)

        return frame

    @staticmethod
    def _id_to_color(track_id):
        """Generate consistent color for track ID"""
        colors = [
            (255, 0, 0), (0, 255, 0), (0, 0, 255),
            (255, 255, 0), (255, 0, 255), (0, 255, 255),
            (128, 255, 0), (255, 128, 0), (128, 0, 255),
            (255, 0, 128), (0, 128, 255), (0, 255, 128)
        ]
        return colors[track_id % len(colors)]
