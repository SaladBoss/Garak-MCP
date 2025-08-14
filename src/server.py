from mcp.server.fastmcp import FastMCP
from pathlib import Path
import requests
from src.utils import get_terminal_commands_output
from src.config import ModelConfig
import json
import tempfile
import os

REPORT_DIR = "./outputs"
REPORT_PREFIX = f"{REPORT_DIR}"

os.makedirs(REPORT_DIR, exist_ok=True)

class GarakServer:
    def __init__(self):
        self.model_types = {
            "ollama": "rest",
            "huggingface": "huggingface",
            "openai": "openai",
            "ggml": "ggml",
            "openai_like": "rest"
        }
        self.config = ModelConfig()
        self._cached_probes = None

    def _get_generator_options_file(self, model_name: str, api_url: str | None = None, api_key: str | None = None, model_type: str = "ollama") -> str:
        """
        Create a temporary config file with the model name and optionally a custom API URL and key set.
        """
        import json, tempfile, os
        
        # Choose the appropriate base config file and endpoints
        if model_type == "openai_like":
            # For OpenAI-like REST, determine endpoints based on the base URL
            base_url = api_url
            endpoints = self.config.get_openai_like_endpoints(base_url)
            
            # Use OpenAI-compatible config as base for OpenAI-like REST
            base_config = "litellm.json"
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', base_config)
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Update the URI with the full endpoint
            full_url = base_url.rstrip("/") + endpoints["generate"]
            config['rest']['RestGenerator']['uri'] = full_url
            
            # Update the model name
            config['rest']['RestGenerator']['req_template_json_object']['model'] = model_name
            
            # Set the appropriate response_json_field based on API type
            response_field = self.config.get_response_json_field(base_url)
            config['rest']['RestGenerator']['response_json_field'] = response_field
            
            # Add API key if provided
            if api_key:
                config['rest']['RestGenerator']['headers']["Authorization"] = f"Bearer {api_key}"
        else:
            # For Ollama, use the existing logic
            base_config = "ollama.json"
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', base_config)
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            config['rest']['RestGenerator']['req_template_json_object']['model'] = model_name
            if api_url:
                config['rest']['RestGenerator']['uri'] = api_url
            if api_key:
                config['rest']['RestGenerator']['headers']["Authorization"] = f"Bearer {api_key}"
        
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        json.dump(config, temp_file)
        temp_file.close()
        return temp_file.name

    def list_garak_probes(self):
        """
        List all available Garak attacks.
        """
        if self._cached_probes is not None:
            return self._cached_probes
        lines, _ = get_terminal_commands_output(['garak', '--list_probes'])
        self._cached_probes = (lines, None)
        return self._cached_probes

    def run_attack(self, model_type: str, model_name: str, probe_name: str):
        """
        Run an attack with the given model and probe.

        Args:
            model_type (str): The type of model to use.
            model_name (str): The name of the model to use.
            probe_name (str): The name of the probe to use. 

        Returns:
            list: A list of vulnerabilities.
        """
        if model_type == "ollama":
            config_file = self._get_generator_options_file(model_name, api_url=self.config.ollama_api_url)
            try:
                return get_terminal_commands_output([
                    'garak',
                    '--model_type', 'rest',
                    '--generator_option_file', config_file,
                    '--probes', probe_name,
                    '--report_prefix', REPORT_PREFIX,
                    "--generations", "1",
                    "--config", "fast",
                    "--parallel_attempts", str(self.config.parallel_attempts),
                    "-v"
                ])
            finally:
                # Clean up the temporary file
                if os.path.exists(config_file):
                    os.unlink(config_file)
        elif model_type == "openai_like":
            base_url = self.config.openai_like_base_url
            api_key = self.config.openai_like_api_key
            config_file = self._get_generator_options_file(model_name, api_url=base_url, api_key=api_key, model_type="openai_like")
            try:
                garak_command = [
                    'garak',
                    '--model_type', 'rest',
                    '--generator_option_file', config_file,
                    '--probes', probe_name,
                    '--report_prefix', REPORT_PREFIX,
                    "--generations", "1",
                    "--config", "fast",
                    "--parallel_attempts", str(self.config.parallel_attempts),
                    "-v"
                ]
                import logging
                logging.info(f"Running Garak command: {' '.join(garak_command)}")
                return get_terminal_commands_output(garak_command)
            finally:
                if os.path.exists(config_file):
                    os.unlink(config_file)
        else:
            return get_terminal_commands_output([
                'garak',
                '--model_type', model_type,
                '--model_name', model_name,
                '--probes', probe_name,
                '--report_prefix', REPORT_PREFIX,
                "--generations", "1",
                "--config", "fast",
                "--parallel_attempts", str(self.config.parallel_attempts),
                "-v"
            ])

# MCP Server
mcp = FastMCP("garakmcp")

@mcp.tool()
def list_model_types():
    """
    List all available model types.

    Returns:
        list[str]: A list of available model types.
    """
    return list(GarakServer().model_types.keys())

@mcp.tool()
def list_models(model_type: str) -> list[str]:
    """
    List all available models for a given model type.
    Those models can be used for the attack and target models.

    Args:
        model_type (str): The type of model to list (ollama, openai, huggingface, ggml, openai_like)

    Returns:
        list[str]: A list of available models.
    """
    return GarakServer().config.list_models(model_type)

@mcp.tool()
def list_garak_probes():
    """
    List all available Garak attacks.

    Returns:
        dict: A dictionary with a 'content' key containing a list of probe names as dicts.
    """
    lines, _ = GarakServer().list_garak_probes()
    probes = []
    for line in lines:
        if line.startswith("probes: "):
            probe = line[len("probes: "):].strip()
            if probe:
                probes.append({"type": "text", "text": probe})
    return {"content": probes, "isError": False}

@mcp.tool()
def get_report():
    """
    Get the report of the last run.

    Returns:
        str: The path of the report file.
    """
    import os
    import glob
    import logging

    # Look for any .jsonl files in the output directory
    jsonl_files = glob.glob(os.path.join(REPORT_DIR, "*.jsonl"))
    
    if jsonl_files:
        # Get the most recent file
        latest_file = max(jsonl_files, key=os.path.getctime)
        logging.info(f"Latest report file found: {latest_file}")
        return Path(latest_file).absolute()
    else:
        # Fallback to the expected name
        expected_file = Path(REPORT_DIR, 'output.report.jsonl')
        if expected_file.exists():
            logging.info(f"Fallback report file found: {expected_file}")
            return expected_file.absolute()

@mcp.tool()
def run_attack(model_type: str, model_name: str, probe_name: str):
    """
    Run an attack with the given model and probe which is a Garak attack.

    Args:
        model_type (str): The type of model to use.
        model_name (str): The name of the model to use.
        probe_name (str): The name of the attack / probe to use.

    Returns:
        list: A list of vulnerabilities.
    """
    import time
    import logging
    
    start_time = time.time()
    logging.info(f"Starting attack: {model_type}/{model_name} with probe {probe_name}")
    
    try:
        result = GarakServer().run_attack(model_type, model_name, probe_name)
        end_time = time.time()
        logging.info(f"Attack completed in {end_time - start_time:.2f} seconds")
        logging.info(f"Result: {result}")
        return result
    except Exception as e:
        end_time = time.time()
        logging.error(f"Attack failed after {end_time - start_time:.2f} seconds: {e}")
        raise
