import logging
from typing import Optional, List
from google import genai
from google.genai import types
from app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.configured_model = settings.GEMINI_MODEL
        self.client = None
        self.active_model = None
        self.is_initialized = False
        self.init_error = None
        
        if not self.api_key or "your_actual_key" in self.api_key:
            self.init_error = "Gemini API key is set to a placeholder or is missing."
            logger.error(self.init_error)
            return

        try:
            self.client = genai.Client(api_key=self.api_key)
            self._discover_and_select_model()
            self.is_initialized = True
            logger.info(f"Gemini Service initialized successfully with model: {self.active_model}")
        except Exception as e:
            self.init_error = str(e)
            logger.error(f"Failed to initialize Gemini client: {e}")

    def _discover_and_select_model(self):
        """
        Lists available models and selects the best one based on fallback rules.
        """
        fallbacks = [
            self.configured_model,
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-2.5-pro",
            "gemini-2.0-flash",
            "gemini-1.5-flash"
        ]
        
        # Clean unique list
        unique_fallbacks = []
        for f in fallbacks:
            if f and f not in unique_fallbacks:
                unique_fallbacks.append(f)

        try:
            available_models = []
            for m in self.client.models.list():
                if 'generateContent' in m.supported_generation_methods:
                    available_models.append(m.name)
            
            clean_available = [m.replace("models/", "") for m in available_models]
            
            for target in unique_fallbacks:
                clean_target = target.replace("models/", "")
                if clean_target in clean_available:
                    self.active_model = f"models/{clean_target}"
                    return
            
            if available_models:
                self.active_model = available_models[0]
            else:
                self.active_model = f"models/{self.configured_model}"
        except Exception as e:
            logger.warning(f"Model discovery failed, using default: {e}")
            self.active_model = f"models/{self.configured_model}" if not self.configured_model.startswith("models/") else self.configured_model

    async def generate_response(self, prompt: str) -> dict:
        if not self.is_initialized:
             return {
                "answer": "The dataset was loaded, but AI analysis is temporarily unavailable.",
                "model_used": None,
                "error": True,
                "details": self.init_error or "Service not initialized"
            }

        try:
            response = self.client.models.generate_content(
                model=self.active_model,
                contents=prompt
            )
            
            if not response or not response.text:
                raise ValueError("No text returned in Gemini response.")
                
            return {
                "answer": response.text,
                "model_used": self.active_model,
                "error": False
            }
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Gemini generation error: {error_msg}")
            
            # User-friendly guidance for common Google errors
            friendly_detail = "AI analysis is temporarily unavailable."
            if "PERMISSION_DENIED" in error_msg:
                friendly_detail = "API Key Error: Your Gemini API key might be invalid, leaked, or restricted. Please check your credentials in the backend/.env file."
            elif "RESOURCE_EXHAUSTED" in error_msg:
                friendly_detail = "Quota Exceeded: You have reached the Gemini API rate limit. Please wait a moment or check your Google AI Studio quota."
            elif "not found" in error_msg.lower():
                friendly_detail = f"Model Error: The model '{self.active_model}' was not found for this API key's region or version."

            return {
                "answer": f"AI ANALYSIS UNAVAILABLE: {friendly_detail}",
                "model_used": self.active_model,
                "error": True,
                "details": error_msg
            }

    def get_status(self) -> dict:
        return {
            "configured": self.is_initialized,
            "selected_model": self.active_model,
            "error": self.init_error
        }

gemini_service = GeminiService()
