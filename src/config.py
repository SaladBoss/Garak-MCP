import os
from dotenv import load_dotenv
import requests
import subprocess
from typing import Dict, List, Optional
import logging
from src.utils import get_openai_like_models, get_response_field_from_data

# Load environment variables
load_dotenv()

class ModelConfig:
    def __init__(self):
        self.parallel_attempts = int(os.getenv("PARALLEL_ATTEMPTS", "1"))
        self.ollama_api_url = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/generate")
        self.openai_like_base_url = os.getenv("OPENAI_LIKE_API_URL")
        self.openai_like_api_key = os.getenv("OPENAI_LIKE_API_KEY")
        self.model_types = {
            "ollama": {
                "type": "rest",
                "api_url": self.ollama_api_url,
                "models": self._get_ollama_models
            },
            "openai": {
                "type": "openai",
                "api_key": os.getenv("OPENAI_API_KEY"),
                "models": self._get_openai_models
            },
            "huggingface": {
                "type": "huggingface",
                "api_key": os.getenv("HUGGINGFACE_API_KEY"),
                "models": self._get_huggingface_models
            },
            "ggml": {
                "type": "ggml",
                "models": self._get_ggml_models
            },
            "openai_like": {
                "type": "rest",
                "base_url": self.openai_like_base_url,
                "api_key": self.openai_like_api_key,
                "models": self._get_openai_like_models
            }
        }

    def _get_ollama_models(self) -> List[str]:
        """Get list of installed Ollama models"""
        try:
            response = requests.get(os.getenv("OLLAMA_TAGS_URL", "http://localhost:11434/api/tags"))
            response.raise_for_status()
            data = response.json()
            return [model['name'] for model in data.get('models', [])]
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching Ollama models: {e}")
            return []

    def _get_openai_models(self) -> List[str]:
        """Get list of configured OpenAI models"""
        models = os.getenv("OPENAI_MODELS", "").split(",")
        return [model.strip() for model in models if model.strip()]

    def _get_huggingface_models(self) -> List[str]:
        """Get list of configured HuggingFace models"""
        models = os.getenv("HUGGINGFACE_MODELS", "").split(",")
        return [model.strip() for model in models if model.strip()]

    def _get_ggml_models(self) -> List[str]:
        """Get list of configured GGML models"""
        models = os.getenv("GGML_MODELS", "").split(",")
        return [model.strip() for model in models if model.strip()]

    def _get_openai_like_models(self) -> List[str]:
        """
        Get list of models from an OpenAI-like REST endpoint using utils function.
        """
        base_url = self.openai_like_base_url
        api_key = self.openai_like_api_key
        
        if not base_url:
            return []
            
        return get_openai_like_models(base_url, api_key)

    def get_openai_like_endpoints(self, base_url: str) -> Dict[str, str]:
        """
        Get the appropriate endpoint for an OpenAI-like REST API based on the base URL.
        
        Args:
            base_url (str): The base URL of the REST API
            
        Returns:
            Dict[str, str]: Dictionary with 'generate' and 'models' endpoints
        """
        # Try to detect the API type based on the base URL or port
        if "4000" in base_url or "litellm" in base_url.lower():
            # LiteLLM/OpenAI-compatible: response is in choices[0].message.content
            return {
                "generate": "/v1/chat/completions",
                "models": "/v1/models"
            }
        elif "11434" in base_url or "ollama" in base_url.lower():
            # Ollama endpoints
            return {
                "generate": "/api/generate",
                "models": "/api/tags"
            }
        else:
            # Default to OpenAI-compatible endpoints (most common)
            return {
                "generate": "/v1/chat/completions",
                "models": "/v1/models"
            }

    def get_response_json_field(self, base_url: str) -> str:
        """
        Get the appropriate response_json_field for an OpenAI-like REST API by testing the actual response.
        
        Args:
            base_url (str): The base URL of the REST API
            
        Returns:
            str: The appropriate response_json_field value
        """
        # Try to detect the API type based on the base URL or port first
        if "4000" in base_url or "litellm" in base_url.lower():
            # LiteLLM/OpenAI-compatible: response is in choices[0].message.content
            return "choices"
        elif "11434" in base_url or "ollama" in base_url.lower():
            # Ollama-compatible: response is directly in response field
            return "response"
        
        # For other URLs, try to test the actual API response
        try:
            # Try to make a test request to determine the response format
            test_endpoints = [
                "/v1/chat/completions",
                "/api/generate",
                "/api/chat"
            ]
            
            headers = {"Content-Type": "application/json"}
            api_key = self.openai_like_api_key
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            
            for endpoint in test_endpoints:
                try:
                    url = base_url.rstrip("/") + endpoint
                    # Make a minimal test request
                    test_request = {
                        "model": "test",
                        "messages": [{"role": "user", "content": "test"}],
                        "stream": False
                    }
                    
                    response = requests.post(url, json=test_request, headers=headers, timeout=5)
                    if response.status_code in [200, 400, 422]:  # Accept various error codes as valid responses
                        data = response.json()
                        # Use the utility function to determine the response field
                        return get_response_field_from_data(data)
                        
                except requests.exceptions.RequestException:
                    continue
                    
        except Exception as e:
            logging.debug(f"Could not test API response format: {e}")
        
        # Default to OpenAI-compatible if we can't determine
        return "choices"

    def set_parallel_attempts(self, attempts: int):
        """
        Set the number of parallel attempts for attacks.
        
        Args:
            attempts (int): The number of parallel attempts to run
        """
        if attempts < 1:
            raise ValueError("Number of parallel attempts must be at least 1")
        self.parallel_attempts = attempts

    def list_models(self, model_type: str) -> List[str]:
        """
        List available models for a given model type.
        
        Args:
            model_type (str): The type of model (ollama, openai, huggingface, ggml, openai_like)
            
        Returns:
            List[str]: List of available model names
        """
        if model_type not in self.model_types:
            raise ValueError(f"Invalid model type: {model_type}")
        
        return self.model_types[model_type]["models"]()

    def get_model_type_info(self, model_type: str) -> Dict:
        """
        Get configuration information for a model type.
        
        Args:
            model_type (str): The type of model
            
        Returns:
            Dict: Configuration information for the model type
        """
        if model_type not in self.model_types:
            raise ValueError(f"Invalid model type: {model_type}")
        
        return self.model_types[model_type] 
    
if __name__ == "__main__":
    config = ModelConfig()

    logging.basicConfig(level=logging.INFO)
    logging.info(config.list_models("ollama"))
    logging.info(config.list_models("openai"))
    logging.info(config.list_models("huggingface"))
    logging.info(config.list_models("ggml"))
    logging.info(config.list_models("openai_like"))
