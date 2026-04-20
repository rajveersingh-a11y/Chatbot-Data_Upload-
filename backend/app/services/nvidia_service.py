import logging
import httpx
from typing import Optional, List
from app.core.config import settings

# Configure logging
logger = logging.getLogger(__name__)

class NvidiaService:
    def __init__(self):
        self.api_key = settings.NVIDIA_API_KEY
        self.base_url = settings.NVIDIA_BASE_URL
        self.model = settings.NVIDIA_MODEL
        self.is_initialized = False
        self.init_error = None
        
        if not self.api_key or "your_actual_key" in self.api_key:
            self.init_error = "NVIDIA API key is set to a placeholder or is missing."
            logger.error(self.init_error)
            return

        # Simple check of connectivity or just set initialized
        self.is_initialized = True
        logger.info(f"NVIDIA Service initialized successfully with model: {self.model}")

    async def generate_response(self, prompt: str) -> dict:
        if not self.is_initialized:
             return {
                "answer": "The dataset was loaded, but AI analysis is temporarily unavailable.",
                "model_used": None,
                "error": True,
                "details": self.init_error or "Service not initialized"
            }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.5,
            "top_p": 1,
            "max_tokens": 1024,
            "stream": False
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code != 200:
                    error_data = response.json() if response.content else {"detail": response.text}
                    raise ValueError(f"NVIDIA API Error ({response.status_code}): {error_data}")
                
                res_json = response.json()
                text = res_json['choices'][0]['message']['content']
                
                return {
                    "answer": text,
                    "model_used": self.model,
                    "error": False
                }
        except Exception as e:
            error_msg = str(e)
            logger.error(f"NVIDIA NIM generation error: {error_msg}")
            
            friendly_detail = "AI analysis is temporarily unavailable."
            if "401" in error_msg or "403" in error_msg:
                friendly_detail = "API Key Error: Your NVIDIA API key might be invalid or restricted. Please check your credentials in the backend/.env file."
            elif "429" in error_msg:
                friendly_detail = "Quota Exceeded: You have reached the NVIDIA API rate limit. Please wait a moment."
            elif "not found" in error_msg.lower() or "404" in error_msg:
                friendly_detail = f"Model Error: The model '{self.model}' was not found or is unavailable."

            return {
                "answer": f"AI ANALYSIS UNAVAILABLE: {friendly_detail}",
                "model_used": self.model,
                "error": True,
                "details": error_msg
            }

    def get_status(self) -> dict:
        return {
            "configured": self.is_initialized,
            "selected_model": self.model,
            "error": self.init_error
        }

nvidia_service = NvidiaService()
