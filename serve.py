#!/usr/bin/env python3
"""Simple local server to view the dashboard."""

import http.server
import socketserver
import os
import webbrowser
import argparse
from pathlib import Path


class ReuseAddrTCPServer(socketserver.TCPServer):
    """TCP Server that allows address reuse."""
    allow_reuse_address = True


def serve(port: int = 8000, open_browser: bool = True, host: str = "0.0.0.0"):
    """Start a local HTTP server for the dashboard."""

    output_dir = Path(__file__).parent / "output"

    if not (output_dir / "index.html").exists():
        print("Dashboard not found. Generating...")
        from generate import generate_dashboard
        generate_dashboard()

    os.chdir(output_dir)

    handler = http.server.SimpleHTTPRequestHandler

    try:
        with ReuseAddrTCPServer((host, port), handler) as httpd:
            print(f"Serving dashboard at:")
            print(f"  http://localhost:{port}")
            print(f"  http://127.0.0.1:{port}")
            if host == "0.0.0.0":
                import socket
                hostname = socket.gethostname()
                try:
                    ip = socket.gethostbyname(hostname)
                    print(f"  http://{ip}:{port}")
                except:
                    pass
            print("\nPress Ctrl+C to stop")

            if open_browser:
                webbrowser.open(f"http://localhost:{port}")

            httpd.serve_forever()
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"Port {port} is already in use. Try a different port:")
            print(f"  python3 serve.py --port {port + 1}")
        else:
            raise
    except KeyboardInterrupt:
        print("\nServer stopped.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Serve the paper aggregator dashboard")
    parser.add_argument("-p", "--port", type=int, default=8000, help="Port to serve on (default: 8000)")
    parser.add_argument("--no-open", action="store_true", help="Don't open browser automatically")

    args = parser.parse_args()
    serve(port=args.port, open_browser=not args.no_open)
