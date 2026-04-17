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
    Accepts CSV/XLSX, validates, saves, and profiles basic shape.
    """
    ext = Path(file.filename).suffix.lower()
    if ext not in [".csv", ".xlsx", ".xls"]:
        raise HTTPException(
            status_code=400, 
            detail="Invalid file type. Please upload a CSV or Excel file."
        )
    
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
    Returns deep structural profiling of the dataset.
    """
    try:
        return dataset_service.get_summary(dataset_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Dataset not found or session expired.")
    except Exception as e:
        logger.error(f"Summary error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat", response_model=ChatResponse)
async def chat_with_data(request: ChatRequest):
    """
    Handles natural language questions. 
    Checks Python deterministic answers first, then Gemini.
    """
    try:
        # Load dataframe from cache
        df = dataset_service._cache.get(request.dataset_id)
        if df is None:
             raise HTTPException(status_code=404, detail="Dataset not found or session expired.")

        # 1. Deterministic check (Pandas/Python)
        det_answer = try_answer_with_pandas(df, request.message)
        if det_answer:
            return ChatResponse(
                answer=det_answer,
                model_used="python",
                dataset_id=request.dataset_id
            )
        
        # 2. Prepare Gemini Context
        context = dataset_service.get_context_for_gemini(request.dataset_id)
        
        # 3. Instruction Prompt
        prompt = f"""
        You are a senior data analyst. You are given a summary context of a dataset and a user question.
        
        RULES:
        - Answer ONLY based on the provided dataset context.
        - If the answer cannot be inferred, say exactly: "I’m sorry, I cannot answer that from the uploaded dataset context."
        - Do not hallucinate columns, calculations, or values.
        - Mention relevant columns used when possible.
        - Keep answer concise and helpful.
        
        DATASET CONTEXT:
        {context}
        
        USER QUESTION:
        {request.message}
        """
        
        # 4. Gemini Call
        res = await gemini_service.generate_response(prompt)
        
        return ChatResponse(
            answer=res["answer"],
            model_used=res.get("model_used"),
            dataset_id=request.dataset_id,
            warnings=["AI fallback triggered"] if res.get("error") else []
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return ChatResponse(
            answer="The dataset was loaded, but AI analysis is temporarily unavailable.",
            dataset_id=request.dataset_id,
            warnings=[str(e)]
        )

@router.get("/health", response_model=HealthResponse)
async def get_health():
    """
    System health and model configuration status.
    """
    return HealthResponse(
        status="ok",
        gemini_initialized=gemini_service.is_initialized,
        active_model=gemini_service.active_model
    )
