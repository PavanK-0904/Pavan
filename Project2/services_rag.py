import json
import os
import numpy as np
from pathlib import Path
from config import EMBEDDING_DIM, RAG_FOLDER

try:
    from sentence_transformers import SentenceTransformer
    MODEL = SentenceTransformer("all-MiniLM-L6-v2")
except Exception:
    MODEL = None




def fallback_embed(text: str):
    np.random.seed(abs(hash(text)) % (2**32))
    return np.random.rand(EMBEDDING_DIM)




def embed(text: str):
    if MODEL:
        return MODEL.encode(text)
    return fallback_embed(text)




class VectorStore:
    def __init__(self, name: str):
        self.name = name
        self.meta_path = Path(RAG_FOLDER) / f"metadata_{name}.json"
        self.emb_path = Path(RAG_FOLDER) / f"emb_{name}.npy"

        self.metadata = []
        self.embeddings = np.zeros((0, EMBEDDING_DIM))

        self._load()


    def _load(self):
        if self.meta_path.exists():
            try:
                with open(self.meta_path, "r", encoding="utf-8") as f:
                    self.metadata = json.load(f)
            except:
                self.metadata = []

        if self.emb_path.exists():
            try:
                self.embeddings = np.load(self.emb_path)
            except:
                self.embeddings = np.zeros((0, EMBEDDING_DIM))

    
    def save(self):
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2)

        np.save(self.emb_path, self.embeddings)


    def add(self, doc_id: str, text: str):
        vector = embed(text)

        self.metadata.append({
            "id": doc_id,
            "text": text
        })

        if self.embeddings.shape[0] == 0:
            self.embeddings = np.array([vector])
        else:
            self.embeddings = np.vstack([self.embeddings, vector])

    def search(self, query: str, top_k=3):
        if len(self.metadata) == 0:
            return []

        qv = embed(query)

        # cosine similarity
        sims = (self.embeddings @ qv) / (
            np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(qv) + 1e-8
        )

        idxs = np.argsort(sims)[::-1][:top_k]

        return [
            {"score": float(sims[i]), "id": self.metadata[i]["id"], "text": self.metadata[i]["text"]}
            for i in idxs
        ]



CUSTOMER_STORE = VectorStore("customers")
BOOKING_STORE = VectorStore("bookings")
ROOM_TYPE_STORE = VectorStore("room_types")




def build_customer_rag():
    import requests
    from config import QLOAPPS_API_KEY, QLOAPPS_BASE_URL


    url = f"{QLOAPPS_BASE_URL}/customers?ws_key={QLOAPPS_API_KEY}"
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        customers = r.json().get("customers", [])
    except:
        customers = []

    CUSTOMER_STORE.metadata = []
    CUSTOMER_STORE.embeddings = np.zeros((0, EMBEDDING_DIM))

    for c in customers:
        text = f"{c.get('firstname', '')} {c.get('lastname', '')} | {c.get('email', '')}"
        CUSTOMER_STORE.add(str(c.get('id', '0')), text)

    CUSTOMER_STORE.save()
    return len(CUSTOMER_STORE.metadata)


def build_booking_rag():
    import requests
    from config import QLOAPPS_API_KEY, QLOAPPS_BASE_URL

    url = f"{QLOAPPS_BASE_URL}/bookings?ws_key={QLOAPPS_API_KEY}"
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        bookings = r.json().get("bookings", [])
    except:
        bookings = []

    BOOKING_STORE.metadata = []
    BOOKING_STORE.embeddings = np.zeros((0, EMBEDDING_DIM))

    for b in bookings:
        text = f"Booking for Customer {b.get('id_customer')} from {b.get('date_from')} to {b.get('date_to')}"
        BOOKING_STORE.add(str(b.get("id", "0")), text)

    BOOKING_STORE.save()
    return len(BOOKING_STORE.metadata)


def build_room_type_rag():
    import requests
    from config import QLOAPPS_API_KEY, QLOAPPS_BASE_URL

    url = f"{QLOAPPS_BASE_URL}/room_types?ws_key={QLOAPPS_API_KEY}"
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        rooms = r.json().get("room_types", [])
    except:
        rooms = []

    ROOM_TYPE_STORE.metadata = []
    ROOM_TYPE_STORE.embeddings = np.zeros((0, EMBEDDING_DIM))

    for r in rooms:
        text = f"{r.get('name', '')} priced at {r.get('price')}"
        ROOM_TYPE_STORE.add(str(r.get("id", "0")), text)

    ROOM_TYPE_STORE.save()
    return len(ROOM_TYPE_STORE.metadata)



def build_all_rag():
    os.makedirs(RAG_FOLDER, exist_ok=True)

    results = {
        "customers": build_customer_rag(),
        "bookings": build_booking_rag(),
        "room_types": build_room_type_rag()
    }

    return results
