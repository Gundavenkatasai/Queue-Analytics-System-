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
import queue as thread_queue
from collections import deque
import json

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

        logger.info(
            f"RealtimeVideoRecorder ready | "
            f"{self.resolution} @ {self.fps} FPS | "
            f"Codec: {self.codec_name} | "
            f"Record duration: {self.record_duration}s"
        )

    # ------------------------------------------------------------------
    # Codec selection
    # ------------------------------------------------------------------
    def _pick_codec(self):
        os.makedirs(self.output_dir, exist_ok=True)
        probe_path = os.path.join(self.output_dir, '_codec_probe.mp4')
        # Avoid avc1/H264/X264 — they require openh264-*.dll on Windows.
        # FFmpeg post-processing converts to H.264 after the file is closed.
        for name in ('mp4v', 'XVID', 'MJPG'):
            fourcc = cv2.VideoWriter_fourcc(*name)
            writer = cv2.VideoWriter(probe_path, fourcc, self.fps, self.resolution)
            if writer.isOpened():
                writer.release()
                try:
                    os.remove(probe_path)
                except OSError:
                    pass
                logger.info(f"Selected video codec: {name}")
                return fourcc, name
            writer.release()
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
        if self.is_recording:
            logger.info("Recording already in progress — ignoring trigger.")
            return False

        logger.info("=== EVENT TRIGGER: Starting 60-second recording ===")

        # Build file path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename  = f"event_{self.camera_id}_{timestamp}.mp4"
        filepath  = os.path.join(self.output_dir, filename)

        # Set timing BEFORE flipping is_recording so write_frame can read them
        now = datetime.now()
        self.current_filename      = filepath
        self.recording_start_time  = now - timedelta(seconds=len(self.buffer) / self.fps)
        self.recording_end_time    = now + timedelta(seconds=self.record_duration)
        self._stop_sent            = False

        # Snapshot the pre-buffer NOW (it keeps changing as new frames arrive)
        buffer_snapshot = list(self.buffer)

        # Tell the worker to open the file
        self.frame_queue.put(('START', filepath))

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
        """
        if not self.running:
            return False

        # Timestamp overlay
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        annotated = frame.copy()
        cv2.putText(annotated, ts, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        # Always keep the rolling pre-buffer up-to-date
        self.buffer.append(annotated)

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
                    elapsed = (now - (self.recording_end_time - timedelta(seconds=self.record_duration))).total_seconds()
                    logger.info(f"=== Recording complete ({elapsed:.1f}s elapsed) — finalising ===")
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
            logger.info(f"VideoWriter released: {os.path.basename(self.current_filename or '')}")

            if self.current_filename and os.path.exists(self.current_filename):
                file_size = os.path.getsize(self.current_filename)
                end_time  = datetime.now()
                duration  = (end_time - self.recording_start_time).total_seconds()

                logger.info(
                    f"Saved: {os.path.basename(self.current_filename)} | "
                    f"{file_size/1024:.1f} KB | {duration:.1f}s"
                )

                # FFmpeg transcode in background (non-blocking)
                src = self.current_filename
                threading.Thread(
                    target=self._try_ffmpeg_transcode, args=(src,), daemon=True
                ).start()

                # Queue metadata upload
                self.upload_queue.put({
                    'filepath':   self.current_filename,
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
    def _try_ffmpeg_transcode(self, filepath):
        tmp_path = filepath + '.h264tmp.mp4'
        try:
            result = subprocess.run(
                [
                    'ffmpeg', '-y', '-i', filepath,
                    '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
                    '-movflags', '+faststart', tmp_path
                ],
                capture_output=True, timeout=300
            )
            if result.returncode == 0 and os.path.exists(tmp_path):
                os.replace(tmp_path, filepath)
                logger.info(f"[FFmpeg] H.264 transcode OK: {os.path.basename(filepath)}")
            else:
                stderr = result.stderr.decode(errors='ignore')[-300:]
                logger.warning(f"[FFmpeg] Transcode failed (rc={result.returncode}): {stderr}")
        except FileNotFoundError:
            logger.warning("[FFmpeg] ffmpeg not found — keeping original codec. Install ffmpeg for H.264 output.")
        except subprocess.TimeoutExpired:
            logger.warning("[FFmpeg] Transcode timed out — keeping original file.")
        except Exception as e:
            logger.error(f"[FFmpeg] Unexpected error: {e}")
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

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
            with open(self.recordings_file, 'r') as f:
                recordings = json.load(f)

            entry = {
                'filename':   os.path.basename(task['filepath']),
                'camera_id':  task['camera_id'],
                'start_time': task['start_time'].isoformat(),
                'end_time':   task['end_time'].isoformat(),
                'duration':   task['duration'],
                'file_size':  task['file_size'],
                'stored_at':  datetime.now().isoformat(),
                'storage':    'local',
            }
            recordings.append(entry)

            # Notify Laravel
            try:
                api_url = os.getenv('API_URL', 'http://localhost:8000/api')
                payload = {
                    'camera_id':        task['camera_id'],
                    'filename':         os.path.basename(task['filepath']),
                    'filepath':         os.path.abspath(task['filepath']).replace('\\', '/'),
                    'duration_seconds': int(task['duration']),
                    'people_count':     0,
                    'file_size_bytes':  task['file_size'],
                }
                requests.post(f"{api_url}/recordings", json=payload, timeout=5)
            except Exception as e:
                logger.error(f"Laravel notification failed: {e}")

            # Prune entries older than 7 days
            cutoff = datetime.now() - timedelta(days=7)
            recordings = [
                r for r in recordings
                if datetime.fromisoformat(r['start_time']) > cutoff
            ]

            with open(self.recordings_file, 'w') as f:
                json.dump(recordings, f, indent=2)

        except Exception as e:
            logger.error(f"File fallback error: {e}")

    # ------------------------------------------------------------------
    # Status / shutdown
    # ------------------------------------------------------------------
    def get_recording_stats(self):
        remaining = 0
        if self.is_recording and self.recording_end_time:
            remaining = max(0, (self.recording_end_time - datetime.now()).total_seconds())
        return {
            'is_recording':    self.is_recording,
            'queue_size':      self.frame_queue.qsize(),
            'remaining_secs':  round(remaining, 1),
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
