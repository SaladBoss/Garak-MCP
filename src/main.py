import asyncio
import os
import sys
import uvicorn

# Add the parent directory to Python path to ensure src module can be found
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.server import mcp

app = mcp.streamable_http_app()

if __name__ == "__main__":
    """Run the MCP server."""
    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.environ["DISABLE_TQDM"] = "1"
    os.environ["PYTHONUNBUFFERED"] = "1"

    import logging
    logging.info("Starting Garak MCP server...")

    # Run the server
    uvicorn.run("src.main:app", host="0.0.0.0", port=5000, reload=True)
    # asyncio.run(main())