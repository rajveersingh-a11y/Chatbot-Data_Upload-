import logging
from typing import Optional, List
from google import genai
from google.genai import types
from app.core.config import settings

logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.configured_model = settings.GEMINI_MODEL
        self.client = None
        self.active_model = None
        self.is_initialized = False
        
        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
                self._discover_and_select_model()
                self.is_initialized = True
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")

    def _discover_and_select_model(self):
        """
        Lists available models and selects the best one based on fallback rules.
        """
        # User defined fallback order
        fallbacks = [
            self.configured_model,
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-2.5-pro",
            "gemini-3-flash-preview",
            "gemini-2.0-flash", # Added common current stable
            "gemini-1.5-flash",
            "gemini-1.5-pro"
        ]
        
        # Filter duplicates and empty strings
        unique_fallbacks = []
        for f in fallbacks:
            if f and f not in unique_fallbacks:
                unique_fallbacks.append(f)

        try:
            # Current SDK way to list models
            available_models = []
            for m in self.client.models.list():
                # Check if it supports generation
                if 'generateContent' in m.supported_generation_methods:
                    available_models.append(m.name)
            
            # Remove 'models/' prefix for easier comparison
            clean_available = [m.replace("models/", "") for m in available_models]
            
            logger.info(f"Available models discovered: {clean_available}")

            for target in unique_fallbacks:
                clean_target = target.replace("models/", "")
                if clean_target in clean_available:
                    self.active_model = f"models/{clean_target}"
                    logger.info(f"Successfully selected model: {self.active_model}")
                    return
            
            # Fallback to first available if none of our preferred models are found
            if available_models:
                self.active_model = available_models[0]
                logger.warning(f"None of the preferred models were found. Using first available: {self.active_model}")
            else:
                logger.error("No models supporting 'generateContent' were found for this API key.")

        except Exception as e:
            logger.error(f"Error during model discovery: {e}")
            # Last resort: just use the configured one and hope for the best if discovery failed
            self.active_model = f"models/{self.configured_model}" if not self.configured_model.startswith("models/") else self.configured_model

    async def generate_response(self, prompt: str) -> dict:
        if not self.client:
            return {"answer": "Gemini API key is missing or invalid.", "error": True}
        
        if not self.active_model:
            return {"answer": "No suitable Gemini model found.", "error": True}

        try:
            response = self.client.models.generate_content(
                model=self.active_model,
                contents=prompt
            )
            
            if not response or not response.text:
                raise ValueError("Empty response from Gemini")
                
            return {
                "answer": response.text,
                "model_used": self.active_model,
                "error": False
            }
        except Exception as e:
            logger.error(f"Gemini generation error model({self.active_model}): {e}")
            return {
                "answer": "The dataset was loaded, but AI analysis is temporarily unavailable.",
                "model_used": self.active_model,
                "error": True,
                "details": str(e)
            }

gemini_service = GeminiService()
