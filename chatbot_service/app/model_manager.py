import os
import time
import requests
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ModelManager:
    # Manages dynamic model selection with caching
    # -caching is used performance optimized
    
    
    def __init__(self):
        self._cached_models: Optional[List[str]] = None
        self._cache_time: float = 0
        self.cache_duration = 3600  # 1 hour in seconds
        self.api_key = os.getenv("GROQ_API_KEY")
        self.preferred_model = os.getenv("MODEL_NAME", "llama-3.1-8b-instant")
        
        # Validate API key on initialization
        if not self.api_key:
            print("WARNING: ModelManager initialized WITHOUT API key!")
            print("Set GROQ_API_KEY in your .env file")
        else:
            print("ModelManager initialized successfully")
        
    def fetch_available_models(self) -> List[str]:
        """Fetch list of available chat models from Groq API"""
        try:
            # Debug: Check if API key is loaded
            if not self.api_key:
                print("ERROR: GROQ_API_KEY not found in environment variables!")
                return []
            
            print(f"Fetching models from Groq API...")
            response = requests.get(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=5
            )
            
            print(f"API Response Status: {response.status_code}")
            
            if response.status_code == 200:
                models_data = response.json()
                total_models = len(models_data.get('data', []))
                print(f"Total models returned by API: {total_models}")
                
                # Filter for active chat models only
                chat_models = []
                filtered_out = []
                
                for model in models_data.get('data', []):
                    model_id = model.get('id', '')
                    is_active = model.get('active', False)
                    
                    # Debug: Track why models are filtered
                    if not is_active:
                        filtered_out.append(f"{model_id} (inactive)")
                        continue
                    
                    # Include if it's active and looks like a chat model
                    if self._is_chat_model(model_id):
                        chat_models.append(model_id)
                    else:
                        filtered_out.append(f"{model_id} (not a chat model)")
                
                print(f"Chat models found: {len(chat_models)}")
                if chat_models:
                    print(f"Available models: {chat_models[:5]}...")  # Show first 5
                
                if filtered_out:
                    print(f"Filtered out {len(filtered_out)} models")
                
                if chat_models:
                    return chat_models
                else:
                    print("No chat models passed the filter!")
                    
            else:
                print(f"API returned non-200 status: {response.status_code}")
                # Don't log full response in production - might contain sensitive info
                if response.status_code == 401:
                    print("Authentication failed - check your API key")
                elif response.status_code == 429:
                    print("Rate limit exceeded")
                else:
                    print(f"API Error: {response.status_code}")
                
            return []
            
        except Exception as e:
            print(f"Failed to fetch models from API: {type(e).__name__}")
            # Only print detailed traceback in development
            if os.getenv("NODE_ENV") == "development":
                import traceback
                traceback.print_exc()
            return []
    
    def _is_chat_model(self, model_id: str) -> bool:
        """Check if a model is suitable for chat/completion tasks"""
        model_lower = model_id.lower()
        
        # Exclude specific types of models
        exclude_keywords = [
            'whisper',           # Audio transcription
            'guard',             # Safety/moderation models
            'prompt-guard',      # Prompt injection detection
            'tts',               # Text-to-speech
            'playai',            # Audio models
        ]
        
        for keyword in exclude_keywords:
            if keyword in model_lower:
                return False
        
        # Include models from known chat providers
        include_patterns = [
            'llama',
            'mixtral',
            'gemma',
            'compound',
            'qwen',
            'deepseek',
            'allam',
            'kimi',
            'maverick',
        ]
        
        for pattern in include_patterns:
            if pattern in model_lower:
                return True
        
        return False
    
    def get_available_models(self) -> List[str]:
        """Get available models with caching"""
        current_time = time.time()
        
        # Return cached models if cache is still valid
        if self._cached_models and (current_time - self._cache_time) < self.cache_duration:
            return self._cached_models
        
        # Fetch fresh models from API
        fresh_models = self.fetch_available_models()
        
        if fresh_models:
            self._cached_models = fresh_models
            self._cache_time = current_time
            return fresh_models
        
        # If API fails, return cached models if available
        if self._cached_models:
            print("Using cached models (API fetch failed)")
            return self._cached_models
        
        # Final fallback
        print("Using hardcoded fallback models")
        return [
            self.preferred_model,
            "llama-3.1-8b-instant",
            "llama-3.1-70b-versatile",
            "mixtral-8x7b-32768",
            "gemma-7b-it"
        ]
    
    def get_best_model(self) -> str:
        """Get the best available model to use"""
        available_models = self.get_available_models()
        
        # Prefer user's configured model if it's available
        if self.preferred_model in available_models:
            return self.preferred_model
        
        # Otherwise use the first available model
        return available_models[0]
    
    def clear_cache(self):
        """Clear the model cache (useful when a model fails)"""
        self._cached_models = None
        self._cache_time = 0
        print("Model cache cleared")
    
    def try_model(self, model: str, models_list: List[str]) -> Optional[str]:
        """Get next model to try if current one fails"""
        try:
            current_index = models_list.index(model)
            if current_index + 1 < len(models_list):
                next_model = models_list[current_index + 1]
                print(f"Switching from {model} to {next_model}")
                return next_model
        except (ValueError, IndexError):
            pass
        
        return None
