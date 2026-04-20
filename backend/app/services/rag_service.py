import logging
import pandas as pd
from typing import List, Dict, Any
from app.services.embedding_service import embedding_service
from app.services.chroma_service import chroma_service
from app.core.config import settings

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self):
        pass

    def index_dataframe(self, df: pd.DataFrame, dataset_id: str, filename: str) -> int:
        """
        Converts dataframe rows to chunks, embeds them, and stores in ChromaDB.
        """
        try:
            logger.info(f"Starting RAG indexing for dataset {dataset_id} ({len(df)} rows)")
            
            documents = []
            metadatas = []
            ids = []
            
            for idx, row in df.iterrows():
                # Convert row to compact string
                # Format: "Column1: Value1 | Column2: Value2 | ..."
                row_items = []
                for col in df.columns:
                    val = row[col]
                    if pd.isna(val) or str(val).strip() == "":
                        continue
                    row_items.append(f"{col}: {val}")
                
                doc_content = f"Row {idx} from {filename}:\n" + "\n".join(row_items)
                
                documents.append(doc_content)
                metadatas.append({
                    "dataset_id": dataset_id,
                    "row_index": int(idx),
                    "filename": filename
                })
                ids.append(f"{dataset_id}_{idx}")

            # Batch embed
            logger.info(f"Embedding {len(documents)} row documents...")
            embeddings = embedding_service.embed_documents(documents)
            
            # Upsert to Chroma
            chroma_service.upsert_rows(
                dataset_id=dataset_id,
                documents=documents,
                metadatas=metadatas,
                ids=ids,
                embeddings=embeddings
            )
            
            logger.info(f"RAG indexing complete for {dataset_id}.")
            return len(documents)
        except Exception as e:
            logger.error(f"RAG indexing failed: {e}")
            raise e

    def get_relevant_context(self, query: str, dataset_id: str) -> str:
        """
        Embeds query, retrieves top-k rows, and builds context string.
        """
        try:
            query_embedding = embedding_service.embed_query(query)
            relevant_rows = chroma_service.query_rows(
                query_embedding=query_embedding,
                dataset_id=dataset_id,
                top_k=settings.RAG_TOP_K
            )
            
            if not relevant_rows:
                return ""

            context_parts = []
            for item in relevant_rows:
                context_parts.append(item["content"])
            
            return "\n\n---\n\n".join(context_parts)
        except Exception as e:
            logger.error(f"Failed to get RAG context: {e}")
            return ""

# Global instance
rag_service = RAGService()
