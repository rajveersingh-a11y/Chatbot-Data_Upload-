from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class UploadResponse(BaseModel):
    dataset_id: str
    filename: str
    row_count: int
    column_count: int
    columns: List[str]

class ChatRequest(BaseModel):
    dataset_id: str
    message: str

class ChatResponse(BaseModel):
    answer: str
    model_used: Optional[str] = None
    answer_type: Optional[str] = None
    confidence: float = 0.0
    source_columns: List[str] = []
    dataset_id: str
    warnings: List[str] = []

class HealthResponse(BaseModel):
    status: str
    nvidia_initialized: bool
    active_model: Optional[str] = None
