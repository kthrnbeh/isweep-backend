# app/__main__.py
"""
Entry point for running ISweep backend.

Usage:
    python -m app
    python -m app --host 0.0.0.0 --port 8001 --reload
"""

import argparse
import uvicorn


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the ISweep backend.")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8001, help="Port to bind (default: 8001)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload on code changes")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    try:
        import app.main  # noqa: F401
    except Exception as exc:
        print("ERROR: Failed to import app.main. Run from isweep-backend and ensure dependencies are installed.")
        print(f"Details: {exc}")
        raise

    # Friendly URLs for local viewing
    browser_host = "127.0.0.1" if args.host in ("0.0.0.0", "0.0.0.0/0") else args.host

    print(f"Starting ISweep backend on {args.host}:{args.port}...")
    print(f"📚 API docs: http://{browser_host}:{args.port}/docs")
    print(f"🔧 ReDoc: http://{browser_host}:{args.port}/redoc")

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )
