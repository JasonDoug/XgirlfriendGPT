import os
import uuid
import logging
from typing import List, Dict, Tuple, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from app.config import settings
from app.models.chat import MemoryItem

logger = logging.getLogger(__name__)

# Lazy initialization of fastembed model for high performance
_fastembed_model = None

def get_fastembed_model():
    global _fastembed_model
    if _fastembed_model is None:
        try:
            from fastembed import TextEmbedding
            _fastembed_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
        except Exception as e:
            logger.warning(f"FastEmbed initialization warning: {e}")
    return _fastembed_model

class MemoryService:
    """
    Long-Term Memory Management Service.
    Uses Qdrant vector database paired with fastembed ONNX embeddings
    so the companion remembers past interactions, shared jokes, and personal facts.
    Uses connection pooling and singleton caching to prevent per-request connection overhead.
    """
    _instances: Dict[Tuple[str, str], "MemoryService"] = {}
    _clients: Dict[str, QdrantClient] = {}

    @classmethod
    def get_instance(cls, host: Optional[str] = None, collection_name: Optional[str] = None) -> "MemoryService":
        target_host = host or settings.QDRANT_HOST
        target_collection = collection_name or settings.QDRANT_COLLECTION

        if target_host == ":memory:":
            return MemoryService(host=target_host, collection_name=target_collection)

        key = (target_host, target_collection)
        if key not in cls._instances:
            cls._instances[key] = MemoryService(host=target_host, collection_name=target_collection)
        return cls._instances[key]

    def __init__(self, host: Optional[str] = None, collection_name: Optional[str] = None):
        self.host = host or settings.QDRANT_HOST
        self.collection_name = collection_name or settings.QDRANT_COLLECTION

        if self.host in MemoryService._clients:
            self.client = MemoryService._clients[self.host]
        else:
            if self.host == ":memory:":
                self.client = QdrantClient(location=":memory:")
            elif os.path.isabs(self.host) or self.host.startswith("."):
                os.makedirs(self.host, exist_ok=True)
                self.client = QdrantClient(path=self.host)
            else:
                self.client = QdrantClient(host=self.host, port=6333)

            if self.host != ":memory:":
                MemoryService._clients[self.host] = self.client

        # Initialize vector collection if it doesn't exist
        try:
            self.client.get_collection(self.collection_name)
        except Exception:
            # 384 dimensional embeddings (BAAI/bge-small-en-v1.5)
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE)
            )

    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generates semantic vector embedding using FastEmbed (BAAI/bge-small-en-v1.5)
        with fallback to deterministic vector encoding.
        """
        try:
            model = get_fastembed_model()
            if model:
                embeddings = list(model.embed([text]))
                return embeddings[0].tolist()
        except Exception as e:
            logger.debug(f"Fallback embedding used: {e}")

        # Deterministic fallback vector encoding
        import hashlib
        h = hashlib.sha256(text.encode('utf-8')).digest()
        vector = []
        for i in range(384):
            val = (h[i % len(h)] + (i * 7)) % 100 / 100.0
            vector.append(val)
        return vector

    def add_memory(self, companion_id: str, user_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> MemoryItem:
        """
        Stores a new conversation snippet or fact into Qdrant vector memory.
        """
        memory_id = str(uuid.uuid4())
        vector = self._generate_embedding(content)
        
        payload = {
            "memory_id": memory_id,
            "companion_id": companion_id,
            "user_id": user_id,
            "content": content,
            **(metadata or {})
        }

        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=memory_id,
                    vector=vector,
                    payload=payload
                )
            ]
        )

        return MemoryItem(
            memory_id=memory_id,
            companion_id=companion_id,
            user_id=user_id,
            content=content,
            metadata=payload
        )

    def retrieve_memories(self, companion_id: str, user_id: str, query: str, limit: int = 3) -> List[str]:
        """
        Retrieves relevant past memories based on semantic vector similarity.
        """
        query_vector = self._generate_embedding(query)
        
        try:
            if hasattr(self.client, "query_points"):
                response = self.client.query_points(
                    collection_name=self.collection_name,
                    query=query_vector,
                    limit=20
                )
                hits = response.points
            else:
                hits = self.client.search(
                    collection_name=self.collection_name,
                    query_vector=query_vector,
                    limit=20
                )
            
            memories = []
            for hit in hits:
                payload = hit.payload or {}
                if payload.get("companion_id") == companion_id:
                    memories.append(payload.get("content", ""))
                    if len(memories) >= limit:
                        break
            return memories
        except Exception:
            return []

    def summarize_conversation(self, history: List[Dict[str, str]]) -> str:
        """
        Generates a concise summary buffer of recent chat history for context compression.
        """
        if not history:
            return ""
        user_msgs = [m["content"] for m in history if m.get("role") == "user"]
        return f"Summary of recent interactions: User discussed topics like {', '.join(user_msgs[-3:])}"
