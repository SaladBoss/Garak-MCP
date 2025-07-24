import os
from .server import mcp

def main():
    """Run the MCP server."""
    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.environ["DISABLE_TQDM"] = "1"
    os.environ["PYTHONUNBUFFERED"] = "1"

    import logging
    logging.info("Starting Garak MCP server!")
    # Run the server
    mcp.run()

    # mcp.run(transport="http", host="127.0.0.1", port=5000, path="/mcp")

if __name__ == "__main__":
    main()