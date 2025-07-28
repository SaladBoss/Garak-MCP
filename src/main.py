import asyncio
import os
import uvicorn
from server import mcp

app = mcp.streamable_http_app()

if __name__ == "__main__":
    """Run the MCP server."""
    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.environ["DISABLE_TQDM"] = "1"
    os.environ["PYTHONUNBUFFERED"] = "1"

    import logging
    logging.info("Starting Garak MCP server!")

    # Run the server
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)
    # asyncio.run(main())