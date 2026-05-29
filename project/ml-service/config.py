"""
Configuration for ML Service
"""

# API Configuration
API_BASE_URL = "http://localhost:8000/api"
API_ENDPOINT = f"{API_BASE_URL}/analytics/timeline"
API_TIMEOUT = 10  # seconds

# Camera Configuration
CAMERA_ID = 0  # Webcam ID (0 for default camera)
CAMERA_FPS = 30
CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720

# YOLO Configuration
YOLO_MODEL = "yolov8n.pt"  # nano model (fastest, smallest)
CONFIDENCE_THRESHOLD = 0.45
IOU_THRESHOLD = 0.45

# ByteTrack Configuration
TRACK_THRESH = 0.5
TRACK_BUFFER = 30
MATCH_THRESH = 0.8

# Queue Analysis Configuration
# ROI: Region of Interest for queue analysis (normalized coordinates 0-1)
ROI = {
    "x1": 0.2,  # Top-left x
    "y1": 0.3,  # Top-left y
    "x2": 0.8,  # Bottom-right x
    "y2": 0.9   # Bottom-right y
}

# Line Crossing Detection
ENTRY_LINE_Y = 0.4  # Normalized Y coordinate for entry line
EXIT_LINE_Y = 0.8   # Normalized Y coordinate for exit line

# Processing Configuration
SEND_INTERVAL = 1  # Send data every N seconds
DISPLAY_FRAME = True  # Show processed frames
DRAW_BOXES = True  # Draw bounding boxes
DRAW_TRAILS = True  # Draw tracking trails
TRAIL_LENGTH = 20  # Number of frames to show trail
FRAME_SKIP = 2  # Process every Nth frame for speed (increase for more speed)

# Logging
LOG_LEVEL = "INFO"
VERBOSE = False

USE_VIDEO_FALLBACK = False  # Set to True to use a video file instead of camera
FALLBACK_VIDEO = "sample_video.mp4"  # Path to fallback video file
# Fallback
FALLBACK_VIDEO = "sample_video.mp4"
USE_VIDEO_FALLBACK = False  # Set to True to use video instead of webcam
