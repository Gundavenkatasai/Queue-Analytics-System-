"""
Queue Analytics Module
Analyzes people movements and queue metrics
"""

import cv2
import numpy as np
from config import ROI, ENTRY_LINE_Y, EXIT_LINE_Y


class QueueAnalyzer:
    """Analyzes queue metrics from tracked persons"""

    def __init__(self):
        """Initialize queue analyzer"""
        self.entry_count = 0
        self.exit_count = 0
        self.previous_tracks = {}  # Track previous frame data for line crossing
        self.people_in_queue = set()  # Track IDs currently in queue

    def analyze(self, tracks, frame_height, frame_width):
        """
        Analyze queue metrics from tracks

        Args:
            tracks: List of current track dicts
            frame_height: Frame height in pixels
            frame_width: Frame width in pixels

        Returns:
            analytics: Dict with:
                - people_count: Number of people detected
                - queue_length: Number of people in queue region
                - entry_count: Cumulative entries
                - exit_count: Cumulative exits
        """
        # Convert ROI to pixel coordinates
        roi_x1 = int(ROI['x1'] * frame_width)
        roi_y1 = int(ROI['y1'] * frame_height)
        roi_x2 = int(ROI['x2'] * frame_width)
        roi_y2 = int(ROI['y2'] * frame_height)

        entry_line_y = int(ENTRY_LINE_Y * frame_height)
        exit_line_y = int(EXIT_LINE_Y * frame_height)

        # Count people in queue
        queue_count = 0
        for track in tracks:
            cx, cy = track['centroid']
            if roi_x1 <= cx <= roi_x2 and roi_y1 <= cy <= roi_y2:
                queue_count += 1
                self.people_in_queue.add(track['track_id'])

        # Detect line crossings for entry/exit
        for track in tracks:
            track_id = track['track_id']
            cx, cy = track['centroid']

            if track_id in self.previous_tracks:
                prev_cy = self.previous_tracks[track_id]

                # Entry line crossing (crossing downward through entry line)
                if prev_cy < entry_line_y and cy >= entry_line_y:
                    self.entry_count += 1

                # Exit line crossing (crossing downward through exit line)
                if prev_cy < exit_line_y and cy >= exit_line_y:
                    self.exit_count += 1

            # Update previous position
            self.previous_tracks[track_id] = cy

        # Remove lost tracks
        lost_track_ids = set(self.previous_tracks.keys()) - set(t['track_id'] for t in tracks)
        for track_id in lost_track_ids:
            del self.previous_tracks[track_id]
            self.people_in_queue.discard(track_id)

        # Calculate actual queue length (only confirmed entries)
        queue_length = max(0, self.entry_count - self.exit_count)

        return {
            'people_count': len(tracks),
            'queue_length': queue_length,
            'entry_count': self.entry_count,
            'exit_count': self.exit_count
        }

    def draw_analytics(self, frame, tracks, frame_height, frame_width):
        """
        Draw ROI, lines, and analytics on frame

        Args:
            frame: Input frame (BGR)
            tracks: List of track dicts
            frame_height: Frame height
            frame_width: Frame width

        Returns:
            frame: Annotated frame
        """
        # Convert ROI to pixel coordinates
        roi_x1 = int(ROI['x1'] * frame_width)
        roi_y1 = int(ROI['y1'] * frame_height)
        roi_x2 = int(ROI['x2'] * frame_width)
        roi_y2 = int(ROI['y2'] * frame_height)

        entry_line_y = int(ENTRY_LINE_Y * frame_height)
        exit_line_y = int(EXIT_LINE_Y * frame_height)

        # Draw ROI rectangle
        cv2.rectangle(frame, (roi_x1, roi_y1), (roi_x2, roi_y2), (0, 165, 255), 2)
        cv2.putText(frame, "Queue Region", (roi_x1, roi_y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)

        # Draw entry line
        cv2.line(frame, (0, entry_line_y), (frame_width, entry_line_y), (0, 255, 0), 2)
        cv2.putText(frame, "ENTRY LINE", (10, entry_line_y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # Draw exit line
        cv2.line(frame, (0, exit_line_y), (frame_width, exit_line_y), (0, 0, 255), 2)
        cv2.putText(frame, "EXIT LINE", (10, exit_line_y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        # Draw analytics info
        info_y = 30
        info_text = [
            f"Entries: {self.entry_count}",
            f"Exits: {self.exit_count}",
            f"Queue Length: {self.entry_count - self.exit_count}",
            f"People Count: {len(tracks)}"
        ]

        for i, text in enumerate(info_text):
            cv2.putText(frame, text, (10, info_y + i * 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        return frame

    def reset(self):
        """Reset counters (useful for daily resets)"""
        self.entry_count = 0
        self.exit_count = 0
        self.previous_tracks = {}
        self.people_in_queue = set()
