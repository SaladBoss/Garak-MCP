import re
import requests
import subprocess
import os
import logging

ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

def sanitize_output(text: str) -> str:
    """
    Remove non-ASCII characters (including emojis) from a string.
    """
    # return ''.join(c for c in text if ord(c) < 128)
    return ansi_escape.sub('', text)

def get_installed_ollama_models():
    """
    Fetch a list of all installed Ollama models.
    
    Returns:
        list: A list of installed model names
    """
    tags_url = os.getenv("OLLAMA_TAGS_URL", os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/generate").replace("/api/generate", "/api/tags"))
    try:
        response = requests.get(tags_url)
        response.raise_for_status()  # Raise an exception for bad status codes
        data = response.json()
        return [model['name'] for model in data.get('models', [])]
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching Ollama models: {e}")
        return []

def get_response_field_from_data(data: dict) -> str:
    """
    Determine the correct response field from API response data.
    
    Args:
        data (dict): The response data from the API
        
    Returns:
        str: The appropriate response field name
    """
    # Try different response field patterns in order of preference
    response_fields = ["choices", "response", "output", "content", "text"]
    
    for field in response_fields:
        if field in data:
            return field
    
    # Default to "choices" if no field is found
    return "choices"

def get_openai_like_models(base_url: str, api_key: str = None):
    """
    Fetch a list of models from an OpenAI-like REST API supporting all LiteLLM providers.
    
    Args:
        base_url (str): The base URL of the REST API (e.g., "http://localhost:4000")
        api_key (str, optional): API key for authentication
        
    Returns:
        list: A list of available model names
    """

    endpoints_to_try = [
        # OpenAI-compatible endpoints (most common)
        "/v1/models",                    # OpenAI, Azure OpenAI, Vertex AI, Google AI Studio, etc.
        "/api/models",                   # Common REST pattern
        "/models",                       # Simple pattern
    ]
    
    # Use headers from the REST generator templates
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    for endpoint in endpoints_to_try:
        try:
            url = base_url.rstrip("/") + endpoint
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                # Handle different response formats from various providers
                if isinstance(data, dict):
                    if "data" in data:  # OpenAI format (most common)
                        return [model["id"] for model in data["data"]]
                    elif "models" in data:  # Ollama format
                        return [model["name"] for model in data["models"]]
                    elif "model_list" in data:  # Some providers use model_list
                        return [model["id"] for model in data["model_list"]]
                    elif "available_models" in data:  # Some providers use available_models
                        return [model["id"] for model in data["available_models"]]
                elif isinstance(data, list):
                    # Try to extract model names from list
                    models = []
                    for item in data:
                        if isinstance(item, dict):
                            if "id" in item:
                                models.append(item["id"])
                            elif "name" in item:
                                models.append(item["name"])
                            elif "model" in item:
                                models.append(item["model"])
                    if models:
                        return models
                        
        except requests.exceptions.RequestException as e:
            logging.debug(f"Failed to fetch models from {endpoint}: {e}")
            continue
    
    # Fallback: return a single model if specified in env
    model = os.getenv("OPENAI_LIKE_MODEL")
    return [model] if model else []

def generate_openai_like_response(base_url: str, model: str, prompt: str, api_key: str = None):
    """
    Generate a response from an OpenAI-like REST API.

    Args:
        base_url (str): The base URL of the REST API (e.g., "http://localhost:4000")
        model (str): The name of the model to use
        prompt (str): The prompt to send to the model
        api_key (str, optional): API key for authentication

    Returns:
        str: The model's response
    """
    # Try different common endpoints for generation
    endpoints_to_try = [
        "/v1/chat/completions",  # OpenAI-compatible (most common)
        "/api/generate",         # Ollama-compatible
        "/api/chat",             # Common REST pattern
        "/generate",             # Simple pattern
        "/chat"                  # Simple pattern
    ]
    
    # Use headers from the REST generator templates
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    for endpoint in endpoints_to_try:
        try:
            url = base_url.rstrip("/") + endpoint
            
            # Try different request formats
            request_formats = [
                # OpenAI-compatible format (most common)
                {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False
                },
                # Ollama-compatible format
                {
                    "model": model,
                    "prompt": prompt,
                    "stream": False
                },
                # Simple format
                {
                    "model": model,
                    "input": prompt
                }
            ]
            
            for request_format in request_formats:
                try:
                    response = requests.post(url, json=request_format, headers=headers, timeout=90)
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Get the response field and extract the content
                        response_field = get_response_field_from_data(data)
                        if response_field in data:
                            if response_field == "choices" and isinstance(data[response_field], list) and len(data[response_field]) > 0:
                                choice = data[response_field][0]
                                if "message" in choice and "content" in choice["message"]:
                                    return sanitize_output(choice["message"]["content"])
                                elif "text" in choice:
                                    return sanitize_output(choice["text"])
                            elif isinstance(data[response_field], str):
                                return sanitize_output(data[response_field])
                                    
                except requests.exceptions.RequestException:
                    continue
                    
        except requests.exceptions.RequestException as e:
            logging.debug(f"Failed to generate response from {endpoint}: {e}")
            continue
    
    logging.error(f"Failed to generate response from OpenAI-like API at {base_url}")
    return ""

def get_terminal_commands_output(command: list[str]):
    """
    Run a command in the terminal and return the output and process ID.
    
    Returns:
        tuple: A tuple containing (output_lines, process_id)
    """
    output_lines: list[str] = []

    try:
        # Use shell=True for Windows compatibility
        process = subprocess.Popen(
            " ".join(command),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=True,
            universal_newlines=True
        )
        
        logging.info(f"Process ID: {process.pid}")
        
        # Read all output at once to avoid deadlocks
        stdout, stderr = process.communicate()
        if stdout:
            lines = [sanitize_output(line.strip()) for line in stdout.split('\n') if line.strip()]
            output_lines.extend(lines)
            for line in lines:
                logging.info(line)
        if stderr:
            logging.error(f"Error output: {sanitize_output(stderr)}")
        
        return output_lines, process.pid
    except subprocess.SubprocessError as e:
        logging.error(f"Error running command {command}: {e}")
        return output_lines, None


def generate_ollama_response(model: str, prompt: str) -> str:
    """
    Generate a response from an Ollama model.

    Args:
        model (str): The name of the Ollama model to use (e.g., "llama3.2:3b")
        prompt (str): The prompt to send to the model

    Returns:
        str: The model's response
    """
    api_url = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/generate")
    try:
        response = requests.post(
            api_url,
            json={
                "model": model,
                "prompt": prompt,
                "stream": False
            }
        )
        response.raise_for_status()
        return sanitize_output(response.json()["response"])
    except requests.exceptions.RequestException as e:
        logging.error(f"Error generating response from Ollama: {e}")
        return ""


if __name__ == "__main__":
    
    logging.info("\nAvailable Garak probes:")
    probes, pid = get_terminal_commands_output(['garak', '--list_probes'])
    logging.info(f"Process ID: {pid}")
    for probe in probes:
        logging.info(f"- {probe}")