from mcp.server.fastmcp import FastMCP
import requests
from src.utils import get_terminal_commands_output
from src.config import ModelConfig
import json
import tempfile
import os



REPORT_PREFIX = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "output")), "output")

os.makedirs(REPORT_PREFIX, exist_ok=True)

class GarakServer:

    def __init__(self):
        from src.config import ModelConfig
        self.model_types = {
            "ollama": "rest",
            "huggingface": "huggingface",
            "openai": "openai",
            "ggml": "ggml",
            "custom_rest": "rest"
        }
        self.config = ModelConfig()

    def _get_generator_options_file(self, model_name: str, api_url: str = None, api_key: str = None) -> str:
        """
        Create a temporary config file with the model name and optionally a custom API URL and key set.
        """
        import json, tempfile, os
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'ollama.json')
        with open(config_path, 'r') as f:
            config = json.load(f)
        config['rest']['RestGenerator']['req_template_json_object']['model'] = model_name
        if api_url:
            config['rest']['RestGenerator']['uri'] = api_url
        if api_key:
            config['rest']['RestGenerator']['headers'] = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        json.dump(config, temp_file)
        temp_file.close()
        return temp_file.name

    def list_garak_probes(self):
        """
        List all available Garak attacks.
        """
        return get_terminal_commands_output(['garak', '--list_probes'])

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
        elif model_type == "custom_rest":
            api_url = self.config.custom_rest_api_url
            api_key = self.config.custom_rest_api_key
            config_file = self._get_generator_options_file(model_name, api_url=api_url, api_key=api_key)
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
mcp = FastMCP("Garak MCP Server")


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
        model_type (str): The type of model to list (ollama, openai, huggingface, ggml)

    Returns:
        list[str]: A list of available models.
    """
    return GarakServer().config.list_models(model_type)

@mcp.tool()
def list_garak_probes():
    """
    List all available Garak attacks.

    Returns:
        list: A list of available probes / attacks.
    """
    return GarakServer().list_garak_probes()

@mcp.tool()
def get_report():
    """
    Get the report of the last run.

    Returns:
        str: The path to the report file.
    """
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output', 'output.report.jsonl')

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
    return GarakServer().run_attack(model_type, model_name, probe_name)


