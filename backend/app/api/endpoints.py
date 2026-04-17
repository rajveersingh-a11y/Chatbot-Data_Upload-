from fastapi import APIRouter, File, UploadFile, HTTPException
from pathlib import Path
import uuid
import shutil
import logging
from app.schemas.dataset import UploadResponse, ChatRequest, ChatResponse, HealthResponse
from app.services.data_query_service import try_answer_with_pandas
from app.services.dataset_service import dataset_service
from app.services.gemini_service import gemini_service
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
        
        # 2. Gemini fallback
        context = dataset_service.get_context_for_gemini(request.dataset_id)
        prompt = f"""
        You are a senior data analyst. Use the context to answer the user question.
        GUIDELINES:
        - Answer ONLY based on the context.
        - Use context for INSIGHTS and INTERPRETATION.
        - If unsure, say you cannot answer.
        
        CONTEXT:
        {context}
        
        USER QUESTION:
        {request.message}
        """
        
        res = await gemini_service.generate_response(prompt)
        
        # If Gemini specifically returned an error-answer, return it
        return ChatResponse(
            answer=res["answer"],
            model_used=res.get("model_used", "gemini"),
            answer_type="insight",
            confidence=0.8 if not res.get("error") else 0.0,
            dataset_id=request.dataset_id,
            warnings=["AI fallback triggered"] if res.get("error") else []
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
    gs = gemini_service.get_status()
    return HealthResponse(
        status="ok",
        gemini_initialized=gs["configured"],
        active_model=gs["selected_model"]
    )
