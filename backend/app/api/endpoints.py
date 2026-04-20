from fastapi import APIRouter, File, UploadFile, HTTPException
from pathlib import Path
import uuid
import shutil
import logging
from app.schemas.dataset import UploadResponse, ChatRequest, ChatResponse, HealthResponse
from app.services.data_query_service import try_answer_with_pandas
from app.services.dataset_service import dataset_service
from app.services.nvidia_service import nvidia_service
from app.services.rag_service import rag_service
from app.services.chroma_service import chroma_service
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """
    Accepts CSV/XLSX, validates, and process with persistence.
    """
    ext = Path(file.filename).suffix.lower()
    if ext not in [".csv", ".xlsx", ".xls"]:
        raise HTTPException(status_code=400, detail="Invalid file type. CSV or Excel only.")
    
    dataset_id = str(uuid.uuid4())
    save_path = settings.upload_path / f"{dataset_id}{ext}"
    
    try:
        with save_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        result = dataset_service.load_dataset(save_path, dataset_id)
        return result
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dataset/{dataset_id}/summary")
async def get_summary(dataset_id: str):
    """
    Returns comprehensive dataset profiling.
    """
    try:
        return dataset_service.get_summary(dataset_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    except Exception as e:
        logger.error(f"Summary error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat", response_model=ChatResponse)
async def chat_with_data(request: ChatRequest):
    """
    Hybrid logic: Pandas-first, then Gemini as interpreter.
    """
    try:
        # Load (supports persistence via Reload)
        df = dataset_service.get_dataframe(request.dataset_id)
        if df is None:
             raise HTTPException(status_code=404, detail="Dataset not found.")

        # 1. Deterministic check (Pandas)
        det_res = try_answer_with_pandas(df, request.message)
        if det_res:
            return ChatResponse(
                answer=det_res["answer"],
                model_used="python",
                answer_type=det_res.get("answer_type"),
                confidence=det_res.get("confidence", 1.0),
                source_columns=det_res.get("source_columns", []),
                dataset_id=request.dataset_id
            )
        
        # 2. NVIDIA fallback with RAG
        summary_context = dataset_service.get_context_for_nvidia(request.dataset_id)
        rag_context = rag_service.get_relevant_context(request.message, request.dataset_id)
        
        # Get retrieved row indices for metadata (optional but requested)
        query_embedding = None # We already did this inside rag_service, but we want the indices
        # Let's simplify: the rag_service already has the logic, 
        # but to satisfy "retrieved_rows" we might need a list of indices.
        # I'll update rag_service to return documents AND indices if needed, 
        # or just query chroma again for indices.
        # Let's just use chroma_service directly here for the list of indices.
        from app.services.embedding_service import embedding_service
        q_emb = embedding_service.embed_query(request.message)
        top_k_rows = chroma_service.query_rows(q_emb, request.dataset_id, settings.RAG_TOP_K)
        retrieved_indices = [int(item["metadata"]["row_index"]) for item in top_k_rows]

        prompt = f"""
        You are a senior data analyst assistant. Answer the user question based ONLY on the provided context.
        
        ### DATASET SUMMARY
        {summary_context}
        
        ### RETRIEVED RELEVANT ROWS
        {rag_context}
        
        ### INSTRUCTIONS
        - Answer ONLY from the provided retrieved context and summary.
        - Do NOT hallucinate columns or values.
        - If the answer cannot be inferred, say: "I’m sorry, I cannot answer that from the retrieved dataset context."
        - Cite relevant row indices (e.g., [Row 15]) when possible.
        - Be concise and structured.
        
        USER QUESTION:
        {request.message}
        """
        
        res = await nvidia_service.generate_response(prompt)
        
        # If NVIDIA specifically returned an error-answer, return it
        if res.get("error") and "AI ANALYSIS UNAVAILABLE" in res.get("answer", ""):
             return ChatResponse(
                answer=res["answer"],
                model_used=res.get("model_used", "nvidia"),
                dataset_id=request.dataset_id,
                retrieved_rows=retrieved_indices,
                error=True
            )
        
        return ChatResponse(
            answer=res["answer"],
            model_used=res.get("model_used", "nvidia"),
            answer_type="rag",
            confidence=0.8,
            dataset_id=request.dataset_id,
            retrieved_rows=retrieved_indices,
            warnings=["RAG context used"]
        )
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return ChatResponse(
            answer=f"SYSTEM ERROR: {str(e)}",
            dataset_id=request.dataset_id,
            warnings=[str(e)]
        )

@router.get("/health", response_model=HealthResponse)
async def get_health():
    ns = nvidia_service.get_status()
    return HealthResponse(
        status="ok",
        nvidia_initialized=ns["configured"],
        active_model=ns["selected_model"]
    )
