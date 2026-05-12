import os

# Camera Configuration
CAMERA_SOURCE = 0  # 0 for webcam, or path to video file
OUTPUT_FPS = 30
FRAME_SIZE = (1280, 720)

# YOLOv8 Configuration
YOLO_MODEL = "yolov8m.pt"
CONFIDENCE_THRESHOLD = 0.5
IOU_THRESHOLD = 0.45

# Tracking Configuration
TRACKING_MAX_AGE = 30  # frames before track is removed
TRACKING_MIN_HITS = 3  # frames to confirm track
TRACK_BUFFER = 30

# Queue Configuration
ROI_POINTS = [
    (200, 200),
    (1080, 200),
    (1080, 550),
    (200, 550)
]  # Define queue area (polygon vertices)
MAX_QUEUE_CAPACITY = 20
QUEUE_THRESHOLD = 10  # Alert if queue exceeds this

# Recording Configuration
RECORDING_CODEC = "mp4v"
INACTIVITY_TIMEOUT = 300  # seconds before stopping recording
STORAGE_PATH = os.path.join(os.path.dirname(__file__), "..", "storage", "videos")

# API Configuration
LARAVEL_API_URL = "http://localhost:8000"
API_ANALYTICS_ENDPOINT = "/api/analytics"
API_RECORDINGS_ENDPOINT = "/api/recordings"
API_TIMEOUT = 5
API_RETRY_ATTEMPTS = 3
API_RETRY_DELAY = 1  # seconds

# Heatmap Configuration
HEATMAP_GRID_SIZE = 32  # 32x32 grid for heatmap

# Logging
LOG_LEVEL = "INFO"

# MongoDB Configuration
MONGODB_URL = "mongodb+srv://venkatasaigunda82_db_user:Lakshmisai123@cluster0.oy678v0.mongodb.net/?appName=Cluster0"
MONGODB_DATABASE = "surveillance_db"

# Ensure storage directories exist
os.makedirs(STORAGE_PATH, exist_ok=True)
