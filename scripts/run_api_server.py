#!/usr/bin/env python3
"""Run the Paper Trading API server."""
import argparse
import uvicorn


def main():
    parser = argparse.ArgumentParser(description="Run Paper Trading API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--workers", type=int, default=1, help="Number of workers")

    args = parser.parse_args()

    print(f"Starting Paper Trading API on {args.host}:{args.port}")
    print(f"API docs: http://{args.host}:{args.port}/docs")
    print(f"WebSocket: ws://{args.host}:{args.port}/api/ws")

    uvicorn.run(
        "api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers,
    )


if __name__ == "__main__":
    main()
