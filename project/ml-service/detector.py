"""
YOLOv8 Person Detection Module
"""

import cv2
import numpy as np
from ultralytics import YOLO
from config import YOLO_MODEL, CONFIDENCE_THRESHOLD, IOU_THRESHOLD, CAMERA_WIDTH, CAMERA_HEIGHT


class PersonDetector:
    """Detects persons in video frames using YOLOv8"""

    def __init__(self):
        """Initialize YOLO model"""
        self.model = YOLO(YOLO_MODEL)
        self.model.to('cuda' if self._has_cuda() else 'cpu')
        self.person_class_id = 0  # COCO dataset person class ID

    @staticmethod
    def _has_cuda():
        """Check if CUDA is available"""
        try:
            import torch
            return torch.cuda.is_available()
        except:
            return False

    def detect(self, frame):
        """
        Detect persons in frame

        Args:
            frame: Input frame (BGR)

        Returns:
            detections: List of dicts with keys:
                - bbox: [x1, y1, x2, y2] (pixel coordinates)
                - confidence: confidence score
                - class_id: class ID (0 for person)
        """
        results = self.model(
            frame,
            conf=CONFIDENCE_THRESHOLD,
            iou=IOU_THRESHOLD,
            classes=[self.person_class_id],  # Only detect persons
            verbose=False
        )

        detections = []
        for result in results:
            for box in result.boxes:
                # Extract coordinates
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = float(box.conf[0].cpu().numpy())
                class_id = int(box.cls[0].cpu().numpy())

                detections.append({
                    'bbox': [int(x1), int(y1), int(x2), int(y2)],
                    'confidence': conf,
                    'class_id': class_id
                })

        return detections

    def draw_detections(self, frame, detections):
        """
        Draw bounding boxes on frame

        Args:
            frame: Input frame (BGR)
            detections: List of detection dicts

        Returns:
            frame: Annotated frame
        """
        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            conf = det['confidence']

            # Draw rectangle
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

            # Draw confidence
            text = f"Person {conf:.2f}"
            cv2.putText(frame, text, (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        return frame
