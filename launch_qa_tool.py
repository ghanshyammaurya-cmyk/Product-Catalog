"""Launch the local EdgeQA web application and open it in the default browser."""

from __future__ import annotations

import argparse
import threading
import webbrowser

import uvicorn


def main():
    parser = argparse.ArgumentParser(description="Launch the EdgeQA Automation Console")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: localhost)")
    parser.add_argument("--port", type=int, default=8765, help="Bind port (default: 8765)")
    parser.add_argument("--no-browser", action="store_true", help="Do not open a browser")
    args = parser.parse_args()

    url = f"http://{args.host}:{args.port}"
    if not args.no_browser:
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()

    print(f"EdgeQA Automation Console: {url}")
    print("Press Ctrl+C to stop the dashboard.")
    uvicorn.run(
        "qa_tool.app:app",
        host=args.host,
        port=args.port,
        reload=False,
        access_log=False,
    )


if __name__ == "__main__":
    main()
