"""
Event-based Video Recording with Pre-Buffer
- Maintains a rolling buffer of 10 seconds.
- When triggered, saves the buffer and records for 60 seconds total (wall-clock).
- Transcodes to H.264 MP4 via FFmpeg after recording.
- Uploads metadata to Laravel API.
"""

import cv2
import os
import subprocess
import requests
from datetime import datetime, timedelta
import logging
import threading
import time
import json
import queue as thread_queue
from collections import deque
from pymongo import MongoClient
import gridfs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RealtimeVideoRecorder:
    def __init__(self, camera_id="camera_1", output_dir="storage/videos"):
        self.camera_id = camera_id
        self.output_dir = output_dir
        self.resolution = (640, 480)
        self.fps = 15

        self.codec, self.codec_name = self._pick_codec()
        os.makedirs(output_dir, exist_ok=True)

        # Event-based recording state
        self.is_recording = False
        self.pre_buffer_seconds = 10
        self.record_duration = 60          # wall-clock seconds to record
        self.buffer = deque(maxlen=self.fps * self.pre_buffer_seconds)

        self.current_video = None
        self.current_filename = None
        self.recording_start_time = None   # datetime when trigger fired
        self.recording_end_time = None     # datetime when recording should stop
        self._stop_sent = False            # guard: only send STOP once

        # Auto-trigger: start the first recording after the pre-buffer fills
        self._frames_written = 0
        self._auto_trigger_done = False
        self._auto_trigger_after_frames = self.fps * self.pre_buffer_seconds  # 150 frames (~10s)

        # Track total completed recordings for verification
        self.completed_recordings = 0

        # Worker thread for writing frames to disk (keeps main loop non-blocking)
        # Large queue: 10-sec pre-buffer (150) + 60-sec live (900) + headroom
        self.frame_queue = thread_queue.Queue(maxsize=5000)
        self.running = True
        self.record_thread = threading.Thread(target=self._record_worker, daemon=True)
        self.record_thread.start()

        # Separate thread for metadata upload
        self.upload_queue = thread_queue.Queue()
        self.start_upload_thread()

        self.recordings_file = "storage/analytics_recordings.json"
        self.ensure_recordings_file()

        # MongoDB / GridFS
        self.db_uri = os.getenv("MONGODB_URI")
        self.db = None
        self.fs = None
        if self.db_uri:
            try:
                self.client = MongoClient(self.db_uri)
                self.db = self.client["surveillance_db"]
                self.fs = gridfs.GridFS(self.db)
                logger.info("Connected to MongoDB GridFS for video storage")
            except Exception as e:
                logger.error(f"MongoDB/GridFS connection error: {e}")

        logger.info(
            f"RealtimeVideoRecorder ready | "
            f"{self.resolution} @ {self.fps} FPS | "
            f"Codec: {self.codec_name} | "
            f"Record duration: {self.record_duration}s | "
            f"Auto-trigger after: {self._auto_trigger_after_frames} frames"
        )

    # ------------------------------------------------------------------
    # Codec selection
    # ------------------------------------------------------------------
    def _pick_codec(self):
        import numpy as np
        os.makedirs(self.output_dir, exist_ok=True)
        # Priority: mp4v (MPEG-4) > XVID (AVI) > MJPG (AVI)
        # Avoid avc1/OpenH264 on Windows because it often reports as available
        # but fails at runtime when the matching DLL is missing or mismatched.
        candidates = [
            ('mp4v', '.mp4'),
            ('XVID', '.avi'),
            ('MJPG', '.avi'),
        ]
        blank = np.zeros((self.resolution[1], self.resolution[0], 3), dtype=np.uint8)
        for name, ext in candidates:
            probe_path = os.path.join(self.output_dir, f'_codec_probe{ext}')
            fourcc = cv2.VideoWriter_fourcc(*name)
            writer = cv2.VideoWriter(probe_path, fourcc, self.fps, self.resolution)
            ok = False
            if writer.isOpened():
                writer.write(blank)  # write one test frame
                writer.release()
                # Verify by reading the file back — a corrupt/stub file has 0 readable frames
                if os.path.exists(probe_path) and os.path.getsize(probe_path) > 512:
                    cap = cv2.VideoCapture(probe_path)
                    ret, _ = cap.read()
                    cap.release()
                    ok = ret  # True only if at least one frame decoded successfully
            else:
                writer.release()
            try:
                os.remove(probe_path)
            except OSError:
                pass
            if ok:
                logger.info(f"Selected video codec: {name} (container: {ext})")
                self._raw_ext = ext
                return fourcc, name
        self._raw_ext = '.mp4'
        logger.warning("No working codec found — falling back to mp4v")
        return cv2.VideoWriter_fourcc(*'mp4v'), 'mp4v'


    # ------------------------------------------------------------------
    # Storage helpers
    # ------------------------------------------------------------------
    def ensure_recordings_file(self):
        os.makedirs("storage", exist_ok=True)
        if not os.path.exists(self.recordings_file):
            with open(self.recordings_file, 'w') as f:
                json.dump([], f)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def trigger_recording(self):
        """Start a 60-second (wall-clock) recording with 10-second pre-buffer."""
        now = datetime.now()
        if self.is_recording:
            new_end = now + timedelta(seconds=self.record_duration)
            if new_end > self.recording_end_time:
                self.recording_end_time = new_end
                logger.info(f"Recording extended until: {self.recording_end_time.strftime('%H:%M:%S')}")
            return True

        logger.info("=== EVENT TRIGGER: Starting 60-second recording ===")

        # Always save raw using the container that matches the codec
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        raw_ext   = getattr(self, '_raw_ext', '.mp4')
        filename  = f"event_{self.camera_id}_{timestamp}.mp4"  # final public name
        # Always record into a separate raw file so the final MP4 is only
        # published after the chunk has been fully finalized.
        raw_name = f"event_{self.camera_id}_{timestamp}_raw{raw_ext}"
        raw_path  = os.path.join(self.output_dir, raw_name)
        filepath  = os.path.join(self.output_dir, filename)

        # Set timing BEFORE flipping is_recording so write_frame can read them
        self.current_filename      = filepath     # final .mp4 path (after transcode)
        self.current_raw_path      = raw_path     # intermediate .avi path (written by OpenCV)
        self.recording_start_time  = now - timedelta(seconds=len(self.buffer) / self.fps)
        self.recording_end_time    = now + timedelta(seconds=self.record_duration)
        self._stop_sent            = False

        # Snapshot the pre-buffer NOW (it keeps changing as new frames arrive)
        buffer_snapshot = list(self.buffer)

        # Tell the worker to open the RAW intermediate file (AVI for MJPG)
        self.frame_queue.put(('START', raw_path))

        # Dump pre-buffer frames (these are NOT counted toward the 60-second budget)
        for frame in buffer_snapshot:
            try:
                self.frame_queue.put_nowait(('FRAME', frame))
            except thread_queue.Full:
                logger.warning("Queue full while dumping pre-buffer — dropping oldest pre-buffer frame")

        # NOW flip the flag — write_frame will start feeding live frames
        self.is_recording = True

        logger.info(
            f"Pre-buffer: {len(buffer_snapshot)} frames | "
            f"Recording until: {self.recording_end_time.strftime('%H:%M:%S')}"
        )
        return True

    def write_frame(self, frame):
        """
        Called every frame from the main detection loop.
        - Always adds to the rolling pre-buffer.
        - If recording is active, enqueues the frame for the writer thread.
        - Stops recording automatically after self.record_duration wall-clock seconds.
        - Auto-triggers the first recording once the pre-buffer is full.
        """
        if not self.running:
            return False

        # Timestamp overlay
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        annotated = frame.copy()
        cv2.putText(annotated, ts, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        # Always keep the rolling pre-buffer up-to-date
        self.buffer.append(annotated)

        # Track total frames written for auto-trigger logic
        self._frames_written += 1

        # Auto-trigger: start first recording once pre-buffer is full
        if (not self._auto_trigger_done
                and not self.is_recording
                and self._frames_written >= self._auto_trigger_after_frames):
            self._auto_trigger_done = True
            logger.info("[AUTO] Pre-buffer full — auto-triggering first 60s recording")
            self.trigger_recording()

        if self.is_recording:
            now = datetime.now()

            if now < self.recording_end_time:
                # Still within the 60-second window — send frame to writer
                try:
                    self.frame_queue.put_nowait(('FRAME', annotated))
                except thread_queue.Full:
                    logger.warning("Frame queue full — dropping live frame (disk too slow?)")
            else:
                # Time is up — send STOP exactly once
                if not self._stop_sent:
                    self._stop_sent   = True
                    self.is_recording = False
                    trigger_time = self.recording_end_time - timedelta(seconds=self.record_duration)
                    elapsed = (now - trigger_time).total_seconds()
                    logger.info(
                        f"=== Recording complete ({elapsed:.1f}s wall-clock, "
                        f"target was {self.record_duration}s) — finalising ==="
                    )
                    self.frame_queue.put(('STOP', None))

        return True

    # ------------------------------------------------------------------
    # Writer worker (runs in its own thread)
    # ------------------------------------------------------------------
    def _record_worker(self):
        while self.running:
            try:
                task = self.frame_queue.get(timeout=1)
                cmd, data = task

                if cmd == 'START':
                    filepath = data
                    self.current_video = cv2.VideoWriter(
                        filepath, self.codec, self.fps, self.resolution
                    )
                    if not self.current_video.isOpened():
                        logger.error(f"VideoWriter failed to open: {filepath}")
                        self.current_video = None
                    else:
                        logger.info(f"VideoWriter opened: {os.path.basename(filepath)}")

                elif cmd == 'FRAME':
                    if self.current_video is not None:
                        frame_resized = cv2.resize(data, self.resolution)
                        self.current_video.write(frame_resized)

                elif cmd == 'STOP':
                    self._finalize_chunk()

            except thread_queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Record worker error: {e}", exc_info=True)

    def _finalize_chunk(self):
        if self.current_video is None:
            return
        try:
            self.current_video.release()
            self.current_video = None

            raw_path   = getattr(self, 'current_raw_path', self.current_filename)
            final_path = self.current_filename

            # Sleep briefly to let OpenCV close the file handle
            time.sleep(0.5)

            # Wait for file to be unlocked and ready under Windows
            unlocked = False
            for i in range(10):  # Try for up to 5 seconds
                try:
                    if raw_path and os.path.exists(raw_path):
                        with open(raw_path, 'rb') as f:
                            pass
                        unlocked = True
                        break
                except IOError:
                    logger.info(f"File {raw_path} is still locked by OS, waiting 0.5s...")
                    time.sleep(0.5)
            
            if not unlocked:
                logger.warning(f"File {raw_path} remained locked after 5s! Proceeding anyway.")

            logger.info(f"VideoWriter released: {os.path.basename(raw_path)}")

            if raw_path and os.path.exists(raw_path):
                file_size = os.path.getsize(raw_path)
                end_time  = datetime.now()
                duration  = (end_time - self.recording_start_time).total_seconds()

                self.completed_recordings += 1
                logger.info(
                    f"✅ Recording #{self.completed_recordings} raw saved: "
                    f"{os.path.basename(raw_path)} | "
                    f"{file_size/1024:.1f} KB | "
                    f"Duration: {duration:.1f}s"
                )

                # Finalize the recording before publishing metadata so the UI
                # never sees a half-finished or invalid file.
                # If raw_path already equals final_path, transcode through a temp
                # file first so we never overwrite the source while reading it.
                success = False
                transcode_target = final_path
                temp_target = None
                if raw_path == final_path:
                    temp_target = final_path + '.transcode.mp4'
                    transcode_target = temp_target

                success = self._try_ffmpeg_transcode(raw_path, transcode_target)
                if not success:
                    success = self._fallback_reencode_to_mp4(raw_path, transcode_target)

                if success and temp_target and os.path.exists(temp_target):
                    try:
                        os.replace(temp_target, final_path)
                    except OSError as move_error:
                        logger.warning(f"Unable to move transcoded file into place: {move_error}")
                        success = False

                if os.path.exists(final_path):
                    file_size = os.path.getsize(final_path)
                else:
                    file_size = os.path.getsize(raw_path)

                # Queue metadata upload — uses the final path
                self.upload_queue.put({
                    'filepath':   final_path,
                    'raw_path':   raw_path,
                    'camera_id':  self.camera_id,
                    'start_time': self.recording_start_time,
                    'end_time':   end_time,
                    'duration':   duration,
                    'file_size':  file_size,
                })
        except Exception as e:
            logger.error(f"Error finalising chunk: {e}", exc_info=True)

    # ------------------------------------------------------------------
    # FFmpeg H.264 post-transcode
    # ------------------------------------------------------------------
    def _try_ffmpeg_transcode(self, src_path, dst_path):
        """Transcode src_path (raw AVI/MJPG) to dst_path (H.264 MP4)."""
        try:
            local_ffmpeg = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg.exe")
            ffmpeg_cmd = local_ffmpeg if os.path.exists(local_ffmpeg) else "ffmpeg"
            logger.info(f"[FFmpeg] Using path/command: {ffmpeg_cmd}")

            abs_src = os.path.abspath(src_path)
            abs_dst = os.path.abspath(dst_path)
            logger.info(f"[FFmpeg] Transcoding: {abs_src} -> {abs_dst}")

            if os.name == 'nt':
                # Under Windows, command strings with shell=True are much more robust with spaces
                cmd_str = f'"{ffmpeg_cmd}" -y -i "{abs_src}" -c:v libx264 -preset fast -crf 23 -movflags +faststart "{abs_dst}"'
                logger.info(f"[FFmpeg] Running command: {cmd_str}")
                result = subprocess.run(
                    cmd_str,
                    shell=True,
                    capture_output=True,
                    timeout=300
                )
            else:
                result = subprocess.run(
                    [
                        ffmpeg_cmd, '-y', '-i', abs_src,
                        '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
                        '-movflags', '+faststart', abs_dst
                    ],
                    capture_output=True, timeout=300
                )
            if result.returncode == 0 and os.path.exists(abs_dst):
                logger.info(f"[FFmpeg] H.264 transcode OK: {os.path.basename(abs_dst)}")
                # Remove the raw intermediate file
                try:
                    if abs_src != abs_dst:
                        os.remove(abs_src)
                except OSError as e:
                    logger.warning(f"Could not remove raw file {abs_src}: {e}")
                return True
            else:
                stderr = result.stderr.decode(errors='ignore')[-1000:]
                stdout = result.stdout.decode(errors='ignore')[-1000:]
                logger.warning(f"[FFmpeg] Transcode failed (rc={result.returncode}):\nSTDOUT: {stdout}\nSTDERR: {stderr}")
                return False
        except FileNotFoundError:
            logger.warning("[FFmpeg] ffmpeg not found — video saved as raw AVI. Install ffmpeg for H.264 MP4 output.")
            return False
        except subprocess.TimeoutExpired:
            logger.warning("[FFmpeg] Transcode timed out — keeping raw file.")
            return False
        except Exception as e:
            logger.error(f"[FFmpeg] Unexpected error: {e}")
            return False

    def _fallback_reencode_to_mp4(self, src_path, dst_path):
        """Fallback conversion using OpenCV so the file is still browser-playable."""
        try:
            abs_src = os.path.abspath(src_path)
            abs_dst = os.path.abspath(dst_path)
            capture = cv2.VideoCapture(abs_src)
            if not capture.isOpened():
                logger.warning(f"[OpenCV] Unable to reopen source for fallback encoding: {abs_src}")
                return False

            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            writer = cv2.VideoWriter(abs_dst, fourcc, self.fps, self.resolution)
            if not writer.isOpened():
                logger.warning(f"[OpenCV] Unable to open fallback writer: {abs_dst}")
                capture.release()
                return False

            frame_count = 0
            while True:
                ok, frame = capture.read()
                if not ok or frame is None:
                    break
                frame = cv2.resize(frame, self.resolution)
                writer.write(frame)
                frame_count += 1

            capture.release()
            writer.release()

            if frame_count > 0 and os.path.exists(abs_dst):
                logger.info(f"[OpenCV] Fallback MP4 encode OK: {os.path.basename(abs_dst)} ({frame_count} frames)")
                try:
                    if abs_src != abs_dst and os.path.exists(abs_src):
                        os.remove(abs_src)
                except OSError:
                    pass
                return True

            logger.warning(f"[OpenCV] Fallback encode produced no frames: {abs_src}")
            return False
        except Exception as e:
            logger.error(f"[OpenCV] Fallback encode failed: {e}")
            return False

    # ------------------------------------------------------------------
    # Upload worker
    # ------------------------------------------------------------------
    def start_upload_thread(self):
        thread = threading.Thread(target=self._upload_worker, daemon=True)
        thread.start()

    def _upload_worker(self):
        while True:
            try:
                task = self.upload_queue.get(timeout=10)
                self._store_to_file_fallback(task)
            except thread_queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Upload worker error: {e}")

    def _store_to_file_fallback(self, task):
        try:
            filename = os.path.basename(task['filepath'])
            cloud_url = None
            
            # 1. Upload to GridFS
            if self.fs:
                try:
                    with open(task['filepath'], 'rb') as f:
                        file_id = self.fs.put(
                            f, 
                            filename=filename, 
                            camera_id=task['camera_id'],
                            start_time=task['start_time'],
                            duration=task['duration']
                        )
                        # We'll use a custom internal URL pattern
                        cloud_url = f"gridfs://{file_id}"
                        logger.info(f"Uploaded to GridFS: {filename} (ID: {file_id})")
                except Exception as e:
                    logger.error(f"GridFS upload failed: {e}")

            # 2. Store Metadata in MongoDB
            if self.db is not None:
                try:
                    self.db.recordings.insert_one({
                        'filename': filename,
                        'camera_id': task['camera_id'],
                        'start_time': task['start_time'].isoformat(),
                        'end_time': task['end_time'].isoformat(),
                        'duration': task['duration'],
                        'file_size': task['file_size'],
                        'cloud_url': cloud_url,
                        'storage': 'mongodb',
                        'created_at': datetime.now().isoformat()
                    })
                    logger.info(f"Metadata stored in MongoDB: {filename}")
                except Exception as e:
                    logger.error(f"MongoDB metadata storage failed: {e}")

            # 3. Local JSON Fallback (as secondary backup)
            with open(self.recordings_file, 'r') as f:
                recordings = json.load(f)

            entry = {
                'filename':        filename,
                'filepath':        os.path.abspath(task['filepath']).replace('\\', '/'),
                'camera_id':       task['camera_id'],
                'start_time':      task['start_time'].isoformat(),
                'end_time':        task['end_time'].isoformat(),
                'duration':        task['duration'],
                'duration_seconds': int(task['duration']),
                'file_size':       task['file_size'],
                'file_size_bytes': task['file_size'],   # alias so Laravel+frontend filter works
                'cloud_url':       cloud_url,
                'stored_at':       datetime.now().isoformat(),
                'storage':         'mongodb' if cloud_url else 'local',
            }
            recordings.append(entry)

            # Notify Laravel with retries
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    api_url = os.getenv('API_URL', 'http://localhost:8000/api')
                    payload = {
                        'camera_id':        task['camera_id'],
                        'filename':         filename,
                        'cloud_url':        cloud_url,
                        'filepath':         os.path.abspath(task['filepath']).replace('\\', '/'),
                        'duration_seconds': int(task['duration']),
                        'people_count':     0,
                        'file_size_bytes':  task['file_size'],
                        'frame_count':      int(task['duration'] * self.fps),
                        'fps':              self.fps,
                        'start_time':       task['start_time'].isoformat(),
                        'end_time':         task['end_time'].isoformat()
                    }
                    response = requests.post(f"{api_url}/recordings", json=payload, timeout=15)
                    if response.status_code in [200, 201]:
                        logger.info(f"Successfully notified Laravel for recording: {filename}")
                        break
                    else:
                        logger.warning(f"Laravel notification attempt {attempt+1} failed ({response.status_code}): {response.text[:100]}")
                except Exception as e:
                    logger.error(f"Laravel notification attempt {attempt+1} error: {e}")
                
                if attempt < max_retries - 1:
                    time.sleep(2) # Wait before retry

            # Prune entries older than 7 days
            cutoff = datetime.now() - timedelta(days=7)
            recordings = [
                r for r in recordings
                if datetime.fromisoformat(r['start_time']) > cutoff
            ]

            with open(self.recordings_file, 'w') as f:
                json.dump(recordings, f, indent=2)

        except Exception as e:
            logger.error(f"Storage worker error: {e}")

    # ------------------------------------------------------------------
    # Status / shutdown
    # ------------------------------------------------------------------
    def get_recording_stats(self):
        remaining = 0
        if self.is_recording and self.recording_end_time:
            remaining = max(0, (self.recording_end_time - datetime.now()).total_seconds())
        return {
            'is_recording':       self.is_recording,
            'queue_size':         self.frame_queue.qsize(),
            'remaining_secs':     round(remaining, 1),
            'completed_count':    self.completed_recordings,
            'frames_buffered':    self._frames_written,
        }

    def stop_recording(self):
        self.running = False
        if hasattr(self, 'record_thread') and self.record_thread.is_alive():
            self.record_thread.join(timeout=5)
        if self.current_video:
            self._finalize_chunk()


def test_recorder():
    pass


if __name__ == "__main__":
    test_recorder()
