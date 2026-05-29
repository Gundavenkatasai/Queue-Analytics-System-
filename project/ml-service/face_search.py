import cv2
import numpy as np
try:
    from deepface import DeepFace
    HAS_DEEPFACE = True
except ImportError:
    HAS_DEEPFACE = False
from pymongo import MongoClient
import os
import logging
import base64
import json
from datetime import datetime
from urllib.parse import quote

logger = logging.getLogger(__name__)

# Path to the local person store (same file that FaceRecognizer writes to)
LOCAL_PERSONS_PATH = os.path.join(os.path.dirname(__file__), "storage", "known_persons.json")


def _load_local_persons():
    """Load known persons from the local JSON fallback file."""
    try:
        if os.path.exists(LOCAL_PERSONS_PATH):
            with open(LOCAL_PERSONS_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        logger.warning(f"Could not read local persons store: {e}")
    return []


class FaceSearcher:
    def __init__(self, db_uri=None, db_name="surveillance_db"):
        self.db_uri = db_uri or os.getenv("MONGODB_URI")
        self.db_name = db_name
        self.client = None
        self.db = None
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

        if self.db_uri:
            try:
                self.client = MongoClient(
                    self.db_uri,
                    serverSelectionTimeoutMS=3000,   # fast fail on startup
                    connectTimeoutMS=3000,
                    socketTimeoutMS=10000,            # longer for actual queries
                    tls=True,
                    tlsAllowInvalidCertificates=False,
                )
                self.db = self.client[self.db_name]
                self.client.admin.command('ping')
                logger.info("FaceSearcher: Connected to MongoDB Atlas")
            except Exception as e:
                logger.warning(f"FaceSearcher: MongoDB Atlas unavailable, will use local JSON fallback: {e}")
                self.client = None
                self.db = None
        else:
            logger.warning("FaceSearcher: No MONGODB_URI set, using local JSON fallback only")


    def _get_embedding(self, img):
        """Extract face embedding using DeepFace or fallback to color histogram."""
        if HAS_DEEPFACE:
            try:
                embeddings = DeepFace.represent(img, model_name="Facenet", enforce_detection=False)
                if embeddings:
                    return np.array(embeddings[0]["embedding"])
            except Exception as e:
                logger.error(f"DeepFace embedding error: {e}")

        # Fallback: colour histogram (same as FaceRecognizer)
        try:
            resized = cv2.resize(img, (64, 64))
            hist = cv2.calcHist([resized], [0, 1, 2], None, [8, 8, 8],
                                [0, 256, 0, 256, 0, 256])
            return cv2.normalize(hist, hist).flatten()
        except Exception as e:
            logger.error(f"Histogram embedding error: {e}")
        return None

    def _decode_image(self, image_b64):
        if ',' in image_b64:
            image_b64 = image_b64.split(',', 1)[1]

        img_data = base64.b64decode(image_b64)
        nparr = np.frombuffer(img_data, np.uint8)
        return cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    def _cosine_similarity(self, left_embedding, right_embedding):
        left = np.array(left_embedding, dtype=np.float32)
        right = np.array(right_embedding, dtype=np.float32)
        left_norm = np.linalg.norm(left)
        right_norm = np.linalg.norm(right)
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return float(np.dot(left, right) / (left_norm * right_norm))

    def _detect_face_crops(self, frame, max_faces=3):
        if self.face_cascade.empty():
            return []

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(48, 48),
        )

        crops = []
        for (x, y, w, h) in faces[:max_faces]:
            face = frame[y:y + h, x:x + w]
            if face.size:
                crops.append({
                    'box': [int(x), int(y), int(w), int(h)],
                    'crop': face,
                })
        return crops

    def _resolve_recording_path(self, recording):
        filepath = recording.get('filepath') or recording.get('file_path') or ''
        if filepath and os.path.exists(filepath):
            return filepath

        filename = recording.get('filename') or ''
        if filename:
            local_path = os.path.join(os.path.dirname(__file__), 'storage', 'videos', filename)
            if os.path.exists(local_path):
                return local_path

        return None

    def _load_recordings(self):
        recordings = []

        if self.db is not None:
            try:
                recordings = list(self.db.recordings.find({}))
                logger.info(f"Face search: loaded {len(recordings)} recordings from MongoDB")
            except Exception as e:
                logger.warning(f"Face search: could not read recordings from MongoDB: {e}")

        if recordings:
            return recordings

        videos_dir = os.path.join(os.path.dirname(__file__), 'storage', 'videos')
        if not os.path.isdir(videos_dir):
            return []

        fallback = []
        for root, _, files in os.walk(videos_dir):
            for file_name in files:
                if file_name.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')):
                    full_path = os.path.join(root, file_name)
                    fallback.append({
                        '_id': os.path.splitext(file_name)[0],
                        'filename': file_name,
                        'filepath': full_path,
                        'camera_id': 'camera_1',
                    })
        logger.info(f"Face search: loaded {len(fallback)} local recording files")
        return fallback

    def search_recordings_by_image(self, image_b64, threshold=0.55, max_recordings=30, frame_step_seconds=5):
        """Search stored recordings and return the videos where the person appears."""
        try:
            img = self._decode_image(image_b64)
            if img is None:
                logger.error("Face recording search: could not decode uploaded image")
                return []

            target_embedding = self._get_embedding(img)
            if target_embedding is None:
                logger.error("Face recording search: could not compute target embedding")
                return []

            recordings = self._load_recordings()[:max_recordings]
            matches = []

            for recording in recordings:
                recording_path = self._resolve_recording_path(recording)
                if not recording_path:
                    continue

                capture = cv2.VideoCapture(recording_path)
                if not capture.isOpened():
                    continue

                fps = capture.get(cv2.CAP_PROP_FPS) or 0
                total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
                if fps <= 0:
                    fps = 10.0

                frame_step = max(int(fps * frame_step_seconds), int(fps))
                best_confidence = 0.0
                best_time_seconds = None

                for frame_index in range(0, max(total_frames, 1), frame_step):
                    capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
                    success, frame = capture.read()
                    if not success or frame is None:
                        continue

                    face_crops = self._detect_face_crops(frame)
                    for face_crop in face_crops:
                        candidate_embedding = self._get_embedding(face_crop['crop'])
                        if candidate_embedding is None:
                            continue

                        confidence = self._cosine_similarity(target_embedding, candidate_embedding)
                        if confidence > best_confidence:
                            best_confidence = confidence
                            best_time_seconds = frame_index / fps

                capture.release()

                if best_confidence >= threshold:
                    start_time = recording.get('start_time')
                    end_time = recording.get('end_time')
                    filename = recording.get('filename', os.path.basename(recording_path))

                    if hasattr(start_time, 'isoformat'):
                        start_time = start_time.isoformat()
                    if hasattr(end_time, 'isoformat'):
                        end_time = end_time.isoformat()

                    recording_id = recording.get('_id')
                    matches.append({
                        'recording_id': str(recording_id),
                        'filename': filename,
                        'camera_id': recording.get('camera_id', 'camera_1'),
                        'filepath': recording_path,
                        'confidence': round(float(best_confidence), 4),
                        'matched_at_seconds': round(float(best_time_seconds or 0), 2),
                        'start_time': start_time,
                        'end_time': end_time,
                        'stream_url': f"http://localhost:8000/api/recordings/file/{quote(filename, safe='')}/stream" if filename else (f"http://localhost:8000/api/recordings/{recording_id}/stream" if recording_id else None),
                    })

            matches.sort(key=lambda item: item['confidence'], reverse=True)
            logger.info(f"Face recording search: found {len(matches)} matching videos")
            return matches

        except Exception as e:
            logger.error(f"Face recording search error: {e}", exc_info=True)
            return []

    def search_by_image(self, image_b64, threshold=0.55):
        """Search for a person across all recordings by an uploaded face image."""
        try:
            # Strip the data-URI prefix if present
            if ',' in image_b64:
                image_b64 = image_b64.split(',', 1)[1]

            # Decode image
            img_data = base64.b64decode(image_b64)
            nparr = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                logger.error("Face search: could not decode uploaded image")
                return []

            # Get embedding for uploaded image
            target_embedding = self._get_embedding(img)
            if target_embedding is None:
                logger.error("Face search: could not compute embedding")
                return []

            # --- Load person database (MongoDB Atlas first, local JSON fallback) ---
            persons = []
            if self.db is not None:
                try:
                    persons = list(self.db.known_persons.find({}))
                    logger.info(f"Face search: loaded {len(persons)} persons from MongoDB Atlas")
                except Exception as e:
                    logger.warning(f"Face search: MongoDB query failed, falling back to local JSON: {e}")

            if not persons:
                persons = _load_local_persons()
                logger.info(f"Face search: loaded {len(persons)} persons from local JSON store")

            if not persons:
                logger.info("Face search: no persons registered yet")
                return []  # No enrolled faces yet

            # --- Cosine similarity comparison ---
            matches = []
            for person in persons:
                raw_emb = person.get('embedding')
                if not raw_emb:
                    continue
                try:
                    stored_embedding = np.array(raw_emb, dtype=np.float32)
                    te = target_embedding.astype(np.float32)

                    norm_s = np.linalg.norm(stored_embedding)
                    norm_t = np.linalg.norm(te)
                    if norm_s == 0 or norm_t == 0:
                        continue

                    cosine_sim = np.dot(stored_embedding, te) / (norm_s * norm_t)
                    dist = 1.0 - cosine_sim  # cosine distance

                    if dist < threshold:
                        matches.append({
                            'person_id':    person.get('person_id', 'unknown'),
                            'confidence':   round(float(cosine_sim), 4),
                            'first_seen':   person.get('first_seen', ''),
                            'last_seen':    person.get('last_seen', ''),
                            'total_visits': person.get('total_visits', 1),
                            'snapshot':     person.get('snapshot', ''),
                        })
                except Exception as e:
                    logger.warning(f"Face search: comparison error for person {person.get('person_id')}: {e}")

            # Sort by confidence descending
            matches.sort(key=lambda x: x['confidence'], reverse=True)
            logger.info(f"Face search: found {len(matches)} match(es) from {len(persons)} enrolled persons")
            return matches

        except Exception as e:
            logger.error(f"Face search error: {e}", exc_info=True)
            return []


if __name__ == "__main__":
    # Test script
    pass
