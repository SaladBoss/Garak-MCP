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