"""
Main ML Service - Real-time Detection + Recording
- Continuous person detection at 15 FPS
- H.264 recording via FFmpeg
- Real-time API data transmission
- All 6 analytics features active
"""

# ┌─ Torch Patch for PyTorch 2.6+ Compatibility ─────────────────────────────────
# Monkeypatch torch.load to disable weights_only checks for YOLO model loading
try:
    import torch
    _original_torch_load = torch.load
    
    def _patched_torch_load(*args, **kwargs):
        # If weights_only not specified, set to False for backward compatibility
        if 'weights_only' not in kwargs:
            kwargs['weights_only'] = False
        return _original_torch_load(*args, **kwargs)
    
    torch.load = _patched_torch_load
except Exception as patch_err:
    pass  # If patching fails, continue anyway
# └──────────────────────────────────────────────────────────────────────────────

import cv2
import os
import sys
import time
import logging
import requests
import json
import numpy as np
from datetime import datetime, timedelta
from datetime import timezone
from threading import Thread
import queue as thread_queue
from real_time_detection import RealTimeDetectionEngine
from realtime_recorder import RealtimeVideoRecorder
from detector_simulator import DetectionSimulator

class ThreadedCamera:
    """Zero-latency camera reader using background thread and shared frame"""
    def __init__(self, src=0):
        import sys
        # Use DirectShow on Windows to bypass MSMF buffer delays
        if sys.platform.startswith('win'):
            self.cap = cv2.VideoCapture(src, cv2.CAP_DSHOW)
        else:
            self.cap = cv2.VideoCapture(src)
            
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        self.ret = False
        self.frame = None
        self.running = True
        self.thread = Thread(target=self._reader, daemon=True)
        
    def start(self):
        self.thread.start()
        return self
        
    def _reader(self):
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                self.ret = ret
                self.frame = frame
                self.new_frame = True
            else:
                import time
                time.sleep(0.01)
            
    def read(self):
        if hasattr(self, 'new_frame') and self.new_frame:
            self.new_frame = False
            return self.ret, self.frame
        return False, None
        
    def isOpened(self):
        return self.cap.isOpened()
        
    def release(self):
        self.running = False
        if self.thread.is_alive():
            self.thread.join(timeout=1)
        self.cap.release()


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ml-service.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SurveillanceSystem:
    """Main surveillance system coordinator"""
    
    def __init__(self):
        self.camera_id = os.getenv('CAMERA_ID', 'camera_1')
        self.api_url = 'http://127.0.0.1:8000/api'
        self.use_camera = os.getenv('USE_CAMERA', 'true').lower() == 'true'
        self.use_simulator = os.getenv('USE_SIMULATOR', 'false').lower() == 'true'
        self.fps = 15
        self.alert_threshold = int(os.getenv('ALERT_THRESHOLD', '50'))
        
        logger.info("=" * 80)
        logger.info("🎥 REAL-TIME SURVEILLANCE SYSTEM STARTING")
        logger.info("=" * 80)
        logger.info(f"Camera ID: {self.camera_id}")
        logger.info(f"API URL: {self.api_url}")
        logger.info(f"FPS: {self.fps}")
        logger.info(f"Alert Threshold: {self.alert_threshold}")
        
        # Ensure FFmpeg is available for transcoding
        ffmpeg_local = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg.exe")
        if not os.path.exists(ffmpeg_local):
            import shutil
            if shutil.which("ffmpeg") is None:
                logger.info("FFmpeg not found globally or locally. Triggering auto-downloader...")
                try:
                    from utils.download_ffmpeg import download_ffmpeg
                    download_ffmpeg()
                except Exception as ex:
                    logger.error(f"Failed to auto-download FFmpeg: {ex}")
            else:
                logger.info("✓ FFmpeg found in system PATH")
        else:
            logger.info("✓ Local FFmpeg binary found")

        # Initialize components
        self.detection_engine = RealTimeDetectionEngine(fps=self.fps, alert_threshold=self.alert_threshold)
        
        # Fetch initial counts
        try:
            initial_entry, initial_exit = self.fetch_initial_counts()
            self.detection_engine.entry_count = initial_entry
            self.detection_engine.exit_count = initial_exit
        except Exception as ex:
            logger.warning(f"Could not initialize detection engine counts: {ex}")
            
        self.recorder = RealtimeVideoRecorder(camera_id=self.camera_id)
        
        # State
        self.running = False
        self.frame_count = 0
        self.last_api_update = 0
        self.api_update_interval = 1.0  # seconds
        self.alert_sent_at = {}  # Track sent alerts to avoid spam
        self.session_id = f"session_{int(time.time())}_{self.camera_id}"

        # API Queue and Worker
        self.api_queue = thread_queue.Queue(maxsize=100)
        self.api_worker_thread = Thread(target=self._api_worker, daemon=True)
        # Thread will be started in run() or run_simulator() to avoid premature exit

        # Keepalive heartbeat thread: sends a periodic ping to keep is_live=True
        # even during long FFmpeg transcoding operations.
        self._keepalive_thread = Thread(target=self._keepalive_worker, daemon=True)
        
        # Start ML API Server for Face Search
        try:
            from app import app as ml_app
            self.flask_thread = Thread(target=lambda: ml_app.run(host='0.0.0.0', port=8001, debug=False, use_reloader=False), daemon=True)
            self.flask_thread.start()
            logger.info("✓ ML API Server started on port 8001")
        except Exception as e:
            logger.error(f"Failed to start ML API Server: {e}")
        

        
        logger.info("✓ Components initialized")

    def _keepalive_worker(self):
        """Periodically sends a minimal heartbeat to keep the Laravel is_live flag fresh.
        This prevents false 'Stream Paused' warnings during FFmpeg transcoding."""
        import time as _time
        KEEPALIVE_INTERVAL = 30  # seconds
        while self.running:
            _time.sleep(KEEPALIVE_INTERVAL)
            if not self.running:
                break
            try:
                # Use the last known analytics if available, otherwise send zeros
                de = self.detection_engine
                payload = {
                    'session_id':            self.session_id,
                    'camera_id':             self.camera_id,
                    'timestamp':             datetime.now(timezone.utc).isoformat(),
                    'people_count':          de.entry_count - max(0, de.exit_count),  # rough estimate
                    'occupancy_percentage':  0.0,
                    'entry_count':           de.entry_count,
                    'exit_count':            de.exit_count,
                    'queue_detected':        False,
                    'queue_length':          0,
                    'dwell_time_avg':        0.0,
                    'dwell_time_max':        0.0,
                    'peak_hours':            '{}',
                    'heatmap_data':          '[]',
                    'alert_status':          'normal',
                }
                requests.post(f"{self.api_url}/analytics/timeline", json=payload, timeout=5)
                logger.debug("[KEEPALIVE] Heartbeat sent to Laravel API")
            except Exception as e:
                logger.debug(f"[KEEPALIVE] Heartbeat failed (non-critical): {e}")

    
    def detect_camera(self):
        """Check if webcam is available"""
        try:
            cap = cv2.VideoCapture(0)
            if cap.isOpened():
                cap.release()
                logger.info("✓ Camera detected and accessible")
                return True
            else:
                logger.warning("⚠ Camera not accessible")
                return False
        except Exception as e:
            logger.error(f"✗ Camera detection error: {e}")
            return False
            
    def _api_worker(self):
        """Worker thread to process API requests sequentially"""
        logger.info("API worker thread started")
        with open("api_debug.txt", "w") as f:
            f.write("API worker started\n")
        while True:
            try:
                # Get task from queue
                url, payload = self.api_queue.get(timeout=1)
                
                try:
                    # Execute POST request
                    response = requests.post(url, json=payload, timeout=10)
                    with open("api_debug.txt", "a") as f:
                        f.write(f"POST {url} - Status: {response.status_code}\n")
                    
                    if response.status_code not in [200, 201]:
                        logger.warning(f"API Error ({response.status_code}): {response.text[:100]}")
                
                except requests.exceptions.Timeout:
                    logger.warning(f"API Timeout posting to {url}")
                    with open("api_debug.txt", "a") as f:
                        f.write(f"Timeout {url}\n")
                except Exception as e:
                    logger.error(f"API connection error: {e}")
                    with open("api_debug.txt", "a") as f:
                        f.write(f"Error {url}: {e}\n")
                finally:
                    self.api_queue.task_done()
            except thread_queue.Empty:
                if not self.running and self.api_queue.empty():
                    break
                continue
            except Exception as e:
                logger.error(f"Critical error in API worker: {e}")

    def _async_post(self, url, payload):
        """Queue POST request for background processing"""
        try:
            with open("api_debug.txt", "a") as f:
                f.write(f"Putting into queue: {url}\n")
            self.api_queue.put_nowait((url, payload))
            with open("api_debug.txt", "a") as f:
                f.write(f"Successfully put into queue: {url}\n")
        except thread_queue.Full:
            # If it's an alert, we should try harder to send it,
            # but for regular timeline data, we just skip it.
            if 'alerts' in url:
                # Use a separate thread for critical alerts if queue is full
                def force_post():
                    try: requests.post(url, json=payload, timeout=10)
                    except: pass
                Thread(target=force_post, daemon=True).start()
            else:
                pass # Skip regular update if backend is overloaded
    
    def fetch_initial_counts(self):
        """Fetch initial entry and exit counts from the backend on startup with retries to handle startup race conditions"""
        url = f"{self.api_url}/analytics/live?camera_id={self.camera_id}"
        max_attempts = 15
        delay_seconds = 2
        
        logger.info(f"Fetching initial counts from {url} (will retry up to {max_attempts} times)...")
        
        for attempt in range(1, max_attempts + 1):
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    entry_count = data.get('entry_count', 0)
                    exit_count = data.get('exit_count', 0)
                    logger.info(f"✓ Successfully fetched initial counts on attempt {attempt}: entry={entry_count}, exit={exit_count}")
                    return int(entry_count), int(exit_count)
                else:
                    logger.warning(f"Attempt {attempt}/{max_attempts}: Server returned status {response.status_code}. Retrying in {delay_seconds}s...")
            except Exception as e:
                logger.warning(f"Attempt {attempt}/{max_attempts}: Failed to fetch initial counts ({e}). Retrying in {delay_seconds}s...")
            
            if attempt < max_attempts:
                time.sleep(delay_seconds)
                
        logger.error("✗ Failed to fetch initial counts after all attempts. Defaulting to 0, 0")
        return 0, 0

    def send_analytics_to_api(self, analytics):
        """Send real-time analytics to backend API"""
        payload = {
            'session_id': self.session_id,
            'camera_id': self.camera_id,
            # Always send UTC so PHP Carbon::now() comparison is timezone-consistent
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'people_count': analytics['people_count'],
            'occupancy_percentage': analytics['occupancy_percentage'],
            'entry_count': analytics['entry_count'],
            'exit_count': analytics['exit_count'],
            'queue_detected': analytics['queue_detected'],
            'queue_length': analytics['queue_length'],
            'dwell_time_avg': analytics['dwell_time_avg'],
            'dwell_time_max': analytics['dwell_time_max'],
            'peak_hours': json.dumps(analytics['peak_hours']),
            'heatmap_data': json.dumps(analytics['heatmap']),
            'alert_status': 'high' if analytics['people_count'] > self.alert_threshold else 'normal'
        }
        with open("api_debug.txt", "a") as f:
            f.write(f"Calling _async_post for {self.api_url}/analytics/timeline\n")
        self._async_post(f"{self.api_url}/analytics/timeline", payload)
        return True
    
    def check_alerts(self, analytics):
        """Check for alert conditions and notify"""
        current_time = datetime.now()
        
        # Start recording if people are detected (continuous recording)
        if analytics.get('people_count', 0) > 0:
            if not self.recorder.is_recording:
                self.recorder.trigger_recording()

        # Alert: High occupancy
        if analytics['people_count'] > self.alert_threshold:
            alert_key = 'high_occupancy'
            last_alert = self.alert_sent_at.get(alert_key, datetime.min)
            
            # Send alert only once per minute
            if (current_time - last_alert).total_seconds() > 60:
                logger.warning(f"🚨 ALERT: High occupancy! {analytics['people_count']} people (threshold: {self.alert_threshold})")
                self.alert_sent_at[alert_key] = current_time
                
                self._async_post(f"{self.api_url}/alerts/create", {
                    'camera_id': self.camera_id,
                    'alert_type': 'high_occupancy',
                    'severity': 'high',
                    'message': f"High occupancy: {analytics['people_count']} people detected",
                    'value': analytics['people_count'],
                    'threshold': self.alert_threshold
                })
        
        # Alert: Queue detected
        if analytics['queue_detected']:
            alert_key = 'queue_detected'
            last_alert = self.alert_sent_at.get(alert_key, datetime.min)
            
            if (current_time - last_alert).total_seconds() > 60:
                logger.warning(f"🚨 ALERT: Queue detected! Length: {analytics['queue_length']}")
                self.alert_sent_at[alert_key] = current_time
                
                self._async_post(f"{self.api_url}/alerts/create", {
                    'camera_id': self.camera_id,
                    'alert_type': 'queue_detected',
                    'severity': 'medium',
                    'message': f"Queue detected: {analytics['queue_length']} people waiting",
                    'value': analytics['queue_length'],
                    'threshold': 3
                })
    
    def run(self):
        """Main detection and recording loop"""
        # Check camera
        if not self.detect_camera():
            logger.warning("=" * 80)
            logger.warning("⚠️  CAMERA NOT AVAILABLE - SWITCHING TO SIMULATOR MODE")
            logger.warning("=" * 80)
            self.run_simulator()
            return
        
        # Open threaded camera
        cap = ThreadedCamera(0).start()
        
        if not cap.isOpened():
            logger.error("Failed to open camera!")
            logger.warning("=" * 80)
            logger.warning("⚠️  FALLING BACK TO SIMULATOR MODE")
            logger.warning("=" * 80)
            self.run_simulator()
            return
        
        self.running = True
        # Start the API worker thread (same as run_simulator does)
        if not self.api_worker_thread.is_alive():
            self.api_worker_thread.start()
        # Start the keepalive heartbeat thread
        if not self._keepalive_thread.is_alive():
            self._keepalive_thread.start()
        logger.info("🎬 Starting real-time detection loop...")
        logger.info("=" * 80)
        
        # Periodic recording configuration
        PERIODIC_RECORD_INTERVAL = 60  # 60 seconds
        last_periodic_record = datetime.now() - timedelta(seconds=PERIODIC_RECORD_INTERVAL - 30) # Start soon
        
        import time
        try:
            while self.running:
                start_time = time.time()
                
                ret, frame = cap.read()
                if not ret or frame is None:
                    time.sleep(0.005)  # Prevent CPU spinning
                    continue
                
                # Flip the frame horizontally to compensate for mirrored webcam feed
                frame = cv2.flip(frame, 1)
                
                # Process detection
                analytics = self.detection_engine.process_frame(frame)
                
                if analytics:
                    self.frame_count += 1
                    
                    # Record frame
                    self.recorder.write_frame(analytics['frame'])
                    
                    # Send to API (at most once per second)
                    current_time = time.time()
                    if current_time - self.last_api_update >= self.api_update_interval:
                        self.send_analytics_to_api(analytics)
                        self.last_api_update = current_time
                    
                    # Check alerts
                    self.check_alerts(analytics)
                    
                    # Log every 15 frames (1 second at 15 FPS)
                    if self.frame_count % 15 == 0:
                        logger.info(
                            f"Frame {self.frame_count:06d} | "
                            f"People: {analytics['people_count']:3d} | "
                            f"Occupancy: {analytics['occupancy_percentage']:5.1f}% | "
                            f"Entry: {analytics['entry_count']:3d} | "
                            f"Exit: {analytics['exit_count']:3d} | "
                            f"Queue: {analytics['queue_detected']}"
                        )
                    
                    # Periodic auto-record safety net
                    now = datetime.now()
                    secs_since = (now - last_periodic_record).total_seconds()
                    if secs_since >= PERIODIC_RECORD_INTERVAL and not self.recorder.is_recording:
                        logger.info(f"Triggering periodic recording ({secs_since:.0f}s since last)")
                        self.recorder.trigger_recording()
                        last_periodic_record = now
                # Calculate processing time and FPS
                process_time = time.time() - start_time
                current_fps = 1.0 / max(process_time, 0.001)
                
                # Display the live video feed window
                display_frame = analytics['frame'] if analytics else frame.copy()
                self.detection_engine.draw_static_guides(display_frame)
                
                # Get device info
                device = getattr(self.detection_engine, 'device', 'cpu').upper()
                q_size = self.recorder.frame_queue.qsize() if hasattr(self.recorder, 'frame_queue') else 0
                
                # Add performance overlay
                cv2.putText(display_frame, f"FPS: {current_fps:.1f}", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(display_frame, f"Proc: {process_time*1000:.0f}ms", (10, 60), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(display_frame, f"Device: {device}", (10, 90), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 200, 0) if device == 'CUDA' else (0, 0, 255), 2)
                cv2.putText(display_frame, f"Q: {q_size}", (10, 120), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0) if q_size < 10 else (0, 0, 255), 2)
                
                cv2.imshow('Queue Analytics', display_frame)
                
                # Check for quit
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    logger.info("Quit signal received")
                    break
        
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
        
        finally:
            self.shutdown()
            cap.release()
    
    def _make_sim_frame(self, data):
        """Create a synthetic BGR frame for the recorder (640x480 black canvas)."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        # Draw simulated bounding boxes for detected people
        import random
        rng = random.Random(data['people_count'])   # stable seed per count
        for i in range(min(data['people_count'], 20)):
            x = rng.randint(30, 560)
            y = rng.randint(60, 380)
            cv2.rectangle(frame, (x, y), (x + 50, y + 100), (0, 200, 80), 2)
        # Overlay text
        cv2.putText(frame, f"[SIM] People: {data['people_count']}",
                    (10, 30),  cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, f"Queue: {data['queue_length']} | Occ: {data['occupancy_percentage']:.1f}%",
                    (10, 60),  cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        cv2.putText(frame, datetime.now().strftime("%H:%M:%S"),
                    (10, 90),  cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 220, 255), 1)
        return frame

    def run_simulator(self):
        """Run detection simulator when camera is unavailable.

        Key fixes vs old version
        ------------------------
        1. Generates synthetic OpenCV frames and feeds them to the recorder so
           write_frame() is called every iteration — the pre-buffer stays full.
        2. Calls check_alerts() so alert-triggered recordings work correctly.
        3. Adds a periodic auto-record every PERIODIC_RECORD_INTERVAL seconds
           as a safety net so recording never silently stops.
        """
        logger.info("🎬 Starting Detection Simulator (with frame recording)...")
        logger.info("=" * 80)

        # How often to force a recording even without an alert (seconds)
        PERIODIC_RECORD_INTERVAL = 60   # 60 seconds

        self.running = True
        if not self.api_worker_thread.is_alive():
            self.api_worker_thread.start()
        # Start the keepalive heartbeat thread
        if not self._keepalive_thread.is_alive():
            self._keepalive_thread.start()
        simulator = DetectionSimulator()
        try:
            initial_entry, initial_exit = self.fetch_initial_counts()
            simulator.entry_count = initial_entry
            simulator.exit_count = initial_exit
            logger.info(f"✓ Initialized simulator counts: entry={initial_entry}, exit={initial_exit}")
        except Exception as ex:
            logger.warning(f"Could not initialize simulator counts: {ex}")
            
        last_periodic_record = datetime.now() - timedelta(seconds=PERIODIC_RECORD_INTERVAL)

        # Target ~15 FPS in simulator mode
        frame_interval = 1.0 / self.fps

        try:
            while self.running:
                loop_start = time.time()

                # ── 1. Generate analytics data ──────────────────────────────
                data = simulator.generate_realistic_data()
                self.frame_count += 1

                # ── 2. Build a synthetic frame and feed to recorder ─────────
                sim_frame = self._make_sim_frame(data)
                self.recorder.write_frame(sim_frame)

                # ── 3. Send analytics to Laravel API (at most once per second) ─
                # Build analytics dict compatible with send_analytics_to_api()
                analytics = {
                    'timestamp':            datetime.now(timezone.utc).isoformat(),
                    'people_count':         data['people_count'],
                    'occupancy_percentage': data['occupancy_percentage'],
                    'entry_count':          data['entry_count'],
                    'exit_count':           data['exit_count'],
                    'queue_detected':       data['queue_detected'],
                    'queue_length':         data['queue_length'],
                    'dwell_time_avg':       data['dwell_time_avg'],
                    'dwell_time_max':       data['dwell_time_max'],
                    'peak_hours':           {},
                    'heatmap':              [],
                    'frame':                sim_frame,
                }
                
                current_time = time.time()
                if current_time - self.last_api_update >= self.api_update_interval:
                    self.send_analytics_to_api(analytics)
                    self.last_api_update = current_time

                # ── 4. Check alert thresholds (triggers event recording) ────
                self.check_alerts(analytics)

                # ── 5. Periodic auto-record safety net ──────────────────────
                now = datetime.now()
                secs_since = (now - last_periodic_record).total_seconds()
                if secs_since >= PERIODIC_RECORD_INTERVAL and not self.recorder.is_recording:
                    logger.info(
                        f"[SIM] Periodic auto-record triggered "
                        f"({secs_since:.0f}s since last recording)"
                    )
                    self.recorder.trigger_recording()
                    last_periodic_record = now

                # ── 6. Log every second ─────────────────────────────────────
                if self.frame_count % self.fps == 0:
                    stats = self.recorder.get_recording_stats()
                    rec_info = (
                        f"REC {stats['remaining_secs']:.0f}s left"
                        if stats['is_recording'] else "idle"
                    )
                    logger.info(
                        f"[SIM] #{self.frame_count:06d} | "
                        f"People: {data['people_count']:2d} | "
                        f"Queue: {data['queue_length']:2d} | "
                        f"Occ: {data['occupancy_percentage']:5.1f}% | "
                        f"Rec: {rec_info} | "
                        f"Completed: {stats.get('completed_count', 0)}"
                    )

                # ── 7. Pace to ~15 FPS ──────────────────────────────────────
                elapsed = time.time() - loop_start
                sleep_time = max(0, frame_interval - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)

        except KeyboardInterrupt:
            logger.info("Simulator stopped by user")
        except Exception as e:
            logger.error(f"Simulator error: {e}", exc_info=True)
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Graceful shutdown"""
        logger.info("=" * 80)
        logger.info("🛑 SHUTTING DOWN")
        logger.info("=" * 80)
        
        self.running = False
        
        # Stop recording
        self.recorder.stop_recording()
        
        # Print final stats
        stats = self.recorder.get_recording_stats()
        logger.info(f"Recording Stats: {stats}")
        logger.info(f"Total Frames Processed: {self.frame_count}")
        logger.info(f"Entry Count: {self.detection_engine.entry_count}")
        logger.info(f"Exit Count: {self.detection_engine.exit_count}")
        
        logger.info("✓ System shutdown complete")


def main():
    """Entry point"""
    logger.info("🚀 ML Service starting...")
    
    system = SurveillanceSystem()
    system.run()


if __name__ == "__main__":
    main()
