# app/__main__.py
"""
Entry point for running ISweep backend.

Usage:
    python -m app
    python -m app --host 0.0.0.0 --port 8001
"""

import sys
import uvicorn

if __name__ == "__main__":
    # Default configuration
    host = "127.0.0.1"
    port = 8001
    reload = True  # Auto-reload on code changes

    # Parse command line args if provided
    if "--host" in sys.argv:
        idx = sys.argv.index("--host")
        if idx + 1 < len(sys.argv):
            host = sys.argv[idx + 1]

    if "--port" in sys.argv:
        idx = sys.argv.index("--port")
        if idx + 1 < len(sys.argv):
            port = int(sys.argv[idx + 1])

    if "--no-reload" in sys.argv:
        reload = False

    print(f"Starting ISweep backend on {host}:{port}...")
    print(f"📚 API docs: http://{host}:{port}/docs")
    print(f"🔧 ReDoc: http://{host}:{port}/redoc")

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
    )
