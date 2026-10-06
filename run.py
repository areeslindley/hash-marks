#!/usr/bin/env python3
"""Run the Hash Marks Flask catalogue."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.main import create_app, find_available_port


if __name__ == "__main__":
    app = create_app()
    port = find_available_port(5000)
    if port is None:
        print("No available ports found in range 5000-5019")
        sys.exit(1)
    print(f"Hash Marks  http://localhost:{port}")
    app.run(debug=True, host="0.0.0.0", port=port, use_reloader=False)
