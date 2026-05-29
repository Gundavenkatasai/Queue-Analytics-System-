import cv2
import numpy as np
try:
    from deepface import DeepFace
    HAS_DEEPFACE = True
except ImportError:
    HAS_DEEPFACE = False
import logging
from pymongo import MongoClient
import os
from datetime import datetime
import uuid
import base64
import json

logger = logging.getLogger(__name__)

class FaceRecognizer:
    def __init__(self, db_uri=None, db_name="surveillance_db"):
        self.db_uri = db_uri or os.getenv("MONGODB_URI")
        self.db_name = db_name
        self.collection_name = "known_persons"
        self.local_store_path = os.path.join(os.path.dirname(__file__), "storage", "known_persons.json")
        self.client = None
        self.db = None
        self.collection = None

        os.makedirs(os.path.dirname(self.local_store_path), exist_ok=True)
        if not os.path.exists(self.local_store_path):
            with open(self.local_store_path, 'w', encoding='utf-8') as f:
                json.dump([], f)
        
        if self.db_uri:
            try:
                self.client = MongoClient(
                    self.db_uri,
                    serverSelectionTimeoutMS=3000,   # fast fail on startup
                    connectTimeoutMS=3000,
                    socketTimeoutMS=10000,
                    tls=True,
                    tlsAllowInvalidCertificates=False,
                )
                self.db = self.client[self.db_name]
                self.collection = self.db[self.collection_name]
                self.client.admin.command('ping')
                logger.info("FaceRecognizer: Connected to MongoDB Atlas")
            except Exception as e:
                logger.warning(f"FaceRecognizer: MongoDB Atlas unavailable, using local JSON fallback: {e}")

    def _load_local_persons(self):
        try:
            with open(self.local_store_path, 'r', encoding='utf-8') as f:
                persons = json.load(f)
            return persons if isinstance(persons, list) else []
        except Exception:
            return []

    def _save_local_persons(self, persons):
        try:
            with open(self.local_store_path, 'w', encoding='utf-8') as f:
                json.dump(persons, f, indent=2)
        except Exception as e:
            logger.error(f"Local face store write error: {e}")

    def _upsert_local_person(self, person_data):
        persons = self._load_local_persons()
        updated = False
        for idx, person in enumerate(persons):
            if person.get('person_id') == person_data.get('person_id'):
                persons[idx] = person_data
                updated = True
                break
        if not updated:
            persons.append(person_data)
        self._save_local_persons(persons)

    def get_embedding(self, face_img):
        """Extract face embedding using DeepFace or fallback to color histogram"""
        if HAS_DEEPFACE:
            try:
                # DeepFace.represent returns a list of dictionaries
                embeddings = DeepFace.represent(face_img, model_name="Facenet", enforce_detection=False)
                if embeddings:
                    return embeddings[0]["embedding"]
            except Exception as e:
                logger.error(f"Error extracting embedding with DeepFace: {e}")
        
        # Fallback: Simple color histogram + spatial feature
        try:
            # Resize for consistency
            resized = cv2.resize(face_img, (64, 64))
            # Get 3D color histogram
            hist = cv2.calcHist([resized], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
            hist = cv2.normalize(hist, hist).flatten()
            return hist.tolist()
        except Exception as e:
            logger.error(f"Fallback embedding error: {e}")
            
        return None

    def find_match(self, embedding, threshold=0.4):
        """Find matching person in MongoDB based on cosine similarity"""
        persons = []
        if self.collection is not None:
            try:
                persons = list(self.collection.find({}))
            except Exception as e:
                logger.warning(f"MongoDB face search unavailable, using local store: {e}")

        if not persons:
            persons = self._load_local_persons()

        if not persons:
            return None

        # This is a simple linear search. For production with many faces, 
        # use a vector database like Milvus or Pinecone, or MongoDB Atlas Vector Search.
        # Here we'll use a basic approach for the demo.
        
        best_match = None
        min_dist = float('inf')

        for person in persons:
            stored_embedding = np.array(person['embedding'])
            current_embedding = np.array(embedding)
            
            # Cosine distance
            dist = 1 - (np.dot(stored_embedding, current_embedding) / 
                       (np.linalg.norm(stored_embedding) * np.linalg.norm(current_embedding)))
            
            if dist < threshold and dist < min_dist:
                min_dist = dist
                best_match = person

        return best_match

    def register_person(self, face_img, embedding):
        """Register a new person — tries MongoDB Atlas first, always saves to local JSON."""
        person_id = str(uuid.uuid4())

        # Convert face image to base64 for snapshot storage
        _, buffer = cv2.imencode('.jpg', face_img)
        snapshot_b64 = base64.b64encode(buffer).decode('utf-8')

        person_data = {
            'person_id': person_id,
            'embedding': embedding if isinstance(embedding, list) else list(embedding),
            'snapshot': snapshot_b64,
            'first_seen': datetime.now().isoformat(),
            'last_seen': datetime.now().isoformat(),
            'total_visits': 1
        }

        # Always save to local JSON first (guaranteed persistence)
        self._upsert_local_person(person_data)

        # Try MongoDB Atlas as well
        if self.collection is not None:
            try:
                self.collection.insert_one(person_data)
                logger.info(f"Registered new person in MongoDB Atlas: {person_id}")
            except Exception as e:
                logger.warning(f"MongoDB Atlas insert failed (saved locally): {e}")
        else:
            logger.info(f"Registered new person in local JSON store: {person_id}")

        return person_id

    def update_person(self, person_id):
        """Update last seen and visit count for an existing person"""
        # Always update local JSON store first
        persons = self._load_local_persons()
        for person in persons:
            if person.get('person_id') == person_id:
                person['last_seen'] = datetime.now().isoformat()
                person['total_visits'] = int(person.get('total_visits', 1)) + 1
                self._save_local_persons(persons)
                logger.info(f"Updated person locally: {person_id}")
                break

        # Also try to update in MongoDB Atlas if available
        if self.collection is not None:
            try:
                self.collection.update_one(
                    {'person_id': person_id},
                    {
                        '$set': {'last_seen': datetime.now().isoformat()},
                        '$inc': {'total_visits': 1}
                    }
                )
                logger.info(f"Updated person in MongoDB Atlas: {person_id}")
            except Exception as e:
                logger.warning(f"MongoDB Atlas update failed (local store updated): {e}")


    def identify_person(self, face_img):
        """Main method to identify or register a person"""
        embedding = self.get_embedding(face_img)
        if embedding is None:
            return None

        match = self.find_match(embedding)
        if match:
            # Check if we should increment visit count (e.g., if seen more than 5 minutes ago)
            last_seen = datetime.fromisoformat(match['last_seen'])
            if (datetime.now() - last_seen).total_seconds() > 300:
                self.update_person(match['person_id'])
            return match['person_id'], False # Existing person
        else:
            person_id = self.register_person(face_img, embedding)
            return person_id, True # New person
