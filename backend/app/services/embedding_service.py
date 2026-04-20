import logging
from sentence_transformers import SentenceTransformer
from app.core.config import settings
from typing import List

logger = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self):
        self.model_name = settings.EMBEDDING_MODEL_NAME
        try:
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            logger.info("Embedding model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise e

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embeds a list of strings into vectors.
        """
        try:
            embeddings = self.model.encode(texts, convert_to_numpy=True).tolist()
            return embeddings
        except Exception as e:
            logger.error(f"Embedding error: {e}")
            raise e

    def embed_query(self, text: str) -> List[float]:
        """
        Embeds a single query string into a vector.
        """
        try:
            embedding = self.model.encode(text, convert_to_numpy=True).tolist()
            return embedding
        except Exception as e:
            logger.error(f"Query embedding error: {e}")
            raise e

# Global instance to load model once
embedding_service = EmbeddingService()
