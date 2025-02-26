#!/usr/bin/env python3
"""Script to run the PulsarNet API server.

This script launches the PulsarNet API server for exposing the application
functionality through a REST API. It can be run directly as a script or
imported and called programmatically.
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Add the parent directory to the path to allow importing pulsarnet
parent_dir = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(parent_dir))

from pulsarnet.api.api_server import APIServer


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run the PulsarNet API server")
    
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind the server to (default: 0.0.0.0)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to run the server on (default: 8000)"
    )
    
    parser.add_argument(
        "--db",
        dest="database_path",
        default=None,
        help="Path to the SQLite database file (default: pulsarnet.db in the data directory)"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["debug", "info", "warning", "error", "critical"],
        default="info",
        help="Logging level (default: info)"
    )
    
    return parser.parse_args()


def main():
    """Run the API server."""
    args = parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Create and run the API server
    server = APIServer(
        host=args.host,
        port=args.port,
        database_path=args.database_path,
        log_level=args.log_level
    )
    
    try:
        logging.info(f"Starting PulsarNet API server on {args.host}:{args.port}")
        server.run()
    except KeyboardInterrupt:
        logging.info("API server stopped by user")
    except Exception as e:
        logging.error(f"Error running API server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 