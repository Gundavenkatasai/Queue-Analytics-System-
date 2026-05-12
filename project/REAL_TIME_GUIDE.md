# 🎥 How to Use REAL Camera Detection Instead of Simulator

The system is currently running with a **detection simulator** that sends realistic simulated data. Here's how to switch to **real-time person detection** from your camera:

## Option 1: Use Webcam (Real-Time Detection)

### Step 1: Verify Webcam Access

Make sure you have a webcam connected to your computer.

### Step 2: Update Config (Optional)

Edit `ml-service/config.py` and verify these settings:

```python
CAMERA_ID = 0  # 0 = default webcam (or 1, 2, 3 for multiple cameras)
CAMERA_FPS = 30
CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720
DISPLAY_FRAME = True  # Shows detection frames (optional)
DRAW_BOXES = True  # Shows bounding boxes around detected people
```

### Step 3: Stop the Simulator

Press `Ctrl+C` in the simulator terminal to stop:

```
Ctrl+C
✓ Simulator stopped by user
```

### Step 4: Start Real Camera Detection

Run the main ML service:

```bash
cd project/ml-service
python main.py
```

### Step 5: Watch Real-Time Updates

The dashboard will now show **real detected people** updating every frame:

- People entering/leaving the view
- Queue length changing
- Entry/exit counts increasing

---

## Option 2: Use Video File (Testing)

If you don't have a webcam available, you can use a video file:

### Step 1: Prepare Video File

Place a video file in `ml-service/sample_video.mp4` (or any path)

### Step 2: Update Config

Edit `ml-service/config.py`:

```python
USE_VIDEO_FALLBACK = True  # Enable video mode
FALLBACK_VIDEO = "sample_video.mp4"  # Path to your video
```

### Step 3: Start Detection

```bash
cd project/ml-service
python main.py
```

The system will process the video file frame-by-frame and send real data to the dashboard.

---

## Performance Settings (for Optimization)

### Faster Processing (Sacrifices Accuracy)

```python
FRAME_SKIP = 3  # Process every 3rd frame instead of every 2nd
CONFIDENCE_THRESHOLD = 0.40  # Lower threshold
IOU_THRESHOLD = 0.40
YOLO_MODEL = "yolov8n.pt"  # Keep nano model
```

### Better Accuracy (Slower)

```python
FRAME_SKIP = 1  # Process every frame
CONFIDENCE_THRESHOLD = 0.50  # Higher threshold
IOU_THRESHOLD = 0.50
YOLO_MODEL = "yolov8m.pt"  # Medium model (slower but more accurate)
```

### GPU Acceleration

The system automatically detects and uses GPU if available. To force CPU-only:

```python
# In config.py, add:
DEVICE = "cpu"  # Force CPU
```

---

## System Architecture

### Data Flow:

```
Real Camera/Video
       ↓
   main.py (Detection + Tracking)
       ↓
   Flask API (http://localhost:8000)
       ↓
   Dashboard (Real-time display)
```

### Current Running Services:

1. **Flask Backend**: `http://localhost:8000` ✅
   - Receives detection data
   - Stores in memory
   - Serves to frontend

2. **Detection Service**:
   - **Simulator**: `detector_simulator.py` ✅ (currently running)
   - **Real Detection**: `main.py` (for real camera)

3. **Frontend Dashboard**: `http://localhost:3000` ✅
   - Shows real-time stats
   - Updates every 2 seconds

---

## Troubleshooting

### Camera Not Detected

```bash
# Try different camera ID
# In config.py, change:
CAMERA_ID = 1  # Try 1, 2, 3, etc.
```

### Slow Performance

- Increase `FRAME_SKIP` (process fewer frames)
- Lower `CAMERA_WIDTH` and `CAMERA_HEIGHT`
- Use `YOLO_MODEL = "yolov8n.pt"` (already set)

### API Connection Error

- Verify Flask is running: `python app.py`
- Check `API_BASE_URL` in `config.py`
- Ensure port 8000 is available

### GPU Not Being Used

- Install CUDA: https://developer.nvidia.com/cuda-downloads
- Install cuDNN matching your CUDA version
- PyTorch will auto-detect GPU

---

## Dashboard Updates

### Current Simulator Mode

- Updates every 1 second
- Sends realistic random variations
- Perfect for testing UI

### Real Detection Mode

- Updates every frame (30 FPS possible)
- Real person count changes
- Real queue dynamics
- Real entry/exit tracking

---

## Next Steps

1. **Currently Running**: Simulator + Flask API + Test Dashboard
2. **To Go Real-Time**:
   - Stop simulator (Ctrl+C)
   - Run `python main.py` for real camera
   - Refresh dashboard to see live detection

3. **For Production**:
   - Use React dashboard (http://localhost:3000)
   - Deploy to cloud server
   - Use database instead of in-memory storage

---

## Commands Quick Reference

```bash
# 1. Start Flask Backend
cd project/ml-service
python app.py

# 2. Start Simulator (Current)
python detector_simulator.py

# 3. Start Real Detection (Switch to camera)
python main.py

# 4. Start Frontend (in new terminal)
cd project/frontend
npm start  # Development
npm run build && serve -s build -p 3000  # Production

# 5. View Test Dashboard
file:///path/to/test-dashboard.html
```

---

**Everything is ready to go!** Just choose your detection source and watch the real-time updates! 🎬
