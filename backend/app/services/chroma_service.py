import chromadb
from chromadb.config import Settings as ChromaSettings
from app.core.config import settings
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class ChromaService:
    def __init__(self):
        self.persist_path = str(settings.chroma_path)
        try:
            self.client = chromadb.PersistentClient(path=self.persist_path)
            self.collection_name = "dataset_rows"
            self.collection = self.client.get_or_create_collection(name=self.collection_name)
            logger.info(f"ChromaDB initialized at {self.persist_path}")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise e

    def upsert_rows(self, dataset_id: str, documents: List[str], metadatas: List[Dict[str, Any]], ids: List[str], embeddings: List[List[float]]):
        """
        Upserts row chunks into ChromaDB.
        """
        try:
            # First, clean up existing vectors for this dataset_id to allow re-indexing
            # Chroma doesn't have a direct "delete by metadata" in all versions easily, 
            # but we can query by metadata to get IDs and then delete.
            # However, for simplicity and performance in a small MVP, we'll just upsert 
            # as our IDs include dataset_id which ensures uniqueness/overwrite.
            self.collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings
            )
            logger.info(f"Successfully upserted {len(ids)} rows for dataset {dataset_id}")
        except Exception as e:
            logger.error(f"Chroma upsert error: {e}")
            raise e

    def query_rows(self, query_embedding: List[float], dataset_id: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Queries ChromaDB for relevant rows, filtered by dataset_id.
        """
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where={"dataset_id": dataset_id}
            )
            
            # Format results
            documents = results.get('documents', [[]])[0]
            metadatas = results.get('metadatas', [[]])[0]
            distances = results.get('distances', [[]])[0]
            
            formatted_results = []
            for i in range(len(documents)):
                formatted_results.append({
                    "content": documents[i],
                    "metadata": metadatas[i],
                    "distance": distances[i]
                })
            
            return formatted_results
        except Exception as e:
            logger.error(f"Chroma query error: {e}")
            return []

    def delete_dataset(self, dataset_id: str):
        """
        Deletes all rows associated with a dataset_id.
        """
        try:
            self.collection.delete(where={"dataset_id": dataset_id})
            logger.info(f"Deleted vectors for dataset {dataset_id}")
        except Exception as e:
            logger.error(f"Chroma delete error: {e}")

# Global instance
chroma_service = ChromaService()
