import cv2
import torch
import numpy as np
from ultralytics import YOLO
from utils.config import YOLO_MODEL, CONFIDENCE_THRESHOLD, IOU_THRESHOLD

class YOLODetector:
    """YOLOv8 Person Detection Wrapper"""
    
    def __init__(self, model_name=YOLO_MODEL):
        """Initialize YOLOv8 model"""
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model = YOLO(model_name)
        self.model.to(self.device)
        self.person_class_id = 0  # COCO person class
        
    def preprocess_frame(self, frame, target_size=(640, 640)):
        """Preprocess frame for detection"""
        h, w = frame.shape[:2]
        scale_x, scale_y = w / target_size[0], h / target_size[1]
        
        # Resize while maintaining aspect ratio
        frame_resized = cv2.resize(frame, target_size)
        return frame_resized, (scale_x, scale_y), (h, w)
    
    def detect(self, frame):
        """
        Run YOLOv8 detection on frame
        
        Returns:
            detections: List of dicts with 'bbox', 'confidence', 'class_id'
            frame_shape: Original frame shape for coordinate scaling
        """
        original_h, original_w = frame.shape[:2]
        
        # Run inference
        results = self.model(frame, conf=CONFIDENCE_THRESHOLD, iou=IOU_THRESHOLD, verbose=False)
        
        detections = []
        
        if results and len(results) > 0:
            boxes = results[0].boxes
            
            for box in boxes:
                # Only keep person detections (class_id = 0)
                if int(box.cls) != self.person_class_id:
                    continue
                
                # Extract bbox coordinates
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                confidence = float(box.conf)
                
                # Normalize to frame size
                detection = {
                    'bbox': [float(x1), float(y1), float(x2), float(y2)],
                    'confidence': confidence,
                    'class_id': int(box.cls),
                    'center_x': float((x1 + x2) / 2),
                    'center_y': float((y1 + y2) / 2),
                    'width': float(x2 - x1),
                    'height': float(y2 - y1)
                }
                detections.append(detection)
        
        return detections, (original_h, original_w)
    
    def batch_detect(self, frames):
        """Run detection on multiple frames"""
        all_detections = []
        for frame in frames:
            detections, frame_shape = self.detect(frame)
            all_detections.append((detections, frame_shape))
        return all_detections
