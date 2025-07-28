# MCP Server For Garak LLM Vulnerability Scanner 

A lightweight MCP (Model Context Protocol) server for Garak.

Tested with **Garak 0.12**.

Example:

https://github.com/user-attachments/assets/f6095d26-2b79-4ef7-a889-fd6be27bbbda

---

## Tools Provided

### Overview
| Name | Description |
|------|-------------|
| list_model_types | List all available model types (ollama, openai, huggingface, ggml, custom_rest) |
| list_models | List all available models for a given model type |
| list_garak_probes | List all available Garak attacks/probes |
| get_report | Get the report of the last run |
| run_attack | Run an attack with a given model and probe |

### Detailed Description

- **list_model_types**
  - List all available model types that can be used for attacks
  - Returns a list of supported model types (ollama, openai, huggingface, ggml, custom_rest)

- **list_models**
  - List all available models for a given model type
  - Input parameters:
    - `model_type` (string, required): The type of model to list (ollama, openai, huggingface, ggml, custom_rest)
  - Returns a list of available models for the specified type

- **list_garak_probes**
  - List all available Garak attacks/probes
  - Returns a list of available probes/attacks that can be run

- **get_report**
  - Get the report of the last run
  - Returns the path to the report file

- **run_attack**
  - Run an attack with the given model and probe
  - Input parameters:
    - `model_type` (string, required): The type of model to use
    - `model_name` (string, required): The name of the model to use
    - `probe_name` (string, required): The name of the attack/probe to use
  - Returns a list of vulnerabilities found

---

## Prerequisites

- Docker

### Optional: **Ollama**

If you want to run attacks on ollama models be sure that the ollama server is running.

```bash
ollama serve
```

---

## Installation

1. Clone this repository:
```bash
git clone https://github.com/SaladBoss/Garak-MCP.git
```

2. Start the MCP server

```bash
docker compose up
```

3. Configure your MCP Host (Claude Desktop, Cursor, etc): 

```json
{
  "mcpServers": {
    "garak-mcp": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "http://localhost:5000/mcp",
        "--transport",
        "http-first"
      ]
    }
  }
}
```

---

## Model Types and Configuration

### Supported Model Types
- **ollama**: Ollama server (configurable via `OLLAMA_API_URL`)
- **openai**: OpenAI API (remote, models listed in `OPENAI_MODELS`)
- **huggingface**: HuggingFace API (remote/local, models listed in `HUGGINGFACE_MODELS`)
- **ggml**: Local GGML models (listed in `GGML_MODELS`)
- **custom_rest**: Any OpenAI-compatible or custom REST endpoint (e.g., LiteLLM, vLLM, etc.)

### Environment Variables
See `.env.example` for all available configuration options, including:
- `OLLAMA_API_URL`, `OLLAMA_TAGS_URL`
- `OPENAI_API_KEY`, `OPENAI_MODELS`
- `HUGGINGFACE_API_KEY`, `HUGGINGFACE_MODELS`
- `GGML_MODELS`
- `CUSTOM_REST_API_URL`, `CUSTOM_REST_API_KEY`, `CUSTOM_REST_MODEL`
- `PARALLEL_ATTEMPTS`

#### Example for Custom REST Endpoint
```env
CUSTOM_REST_API_URL=http://localhost:4000
CUSTOM_REST_API_KEY=sk-...
CUSTOM_REST_MODEL=my-model
```
---
Tested on:
- [X] Cursor
- [X] Claude Desktop

---
## Future Steps

- [ ] Add support for Smithery AI: Docker and config
- [ ] Improve Reporting
- [ ] Test and validate OpenAI models (GPT-3.5, GPT-4)
- [ ] Test and validate HuggingFace models
- [ ] Test and validate local GGML models
- [ ] Test and validate custom REST endpoints (LiteLLM, vLLM, etc.)
