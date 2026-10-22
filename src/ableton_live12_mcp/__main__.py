"""
Ableton Live 12 MCP Package Entry Point
=======================================
Allows execution via:
    python3 -m ableton_live12_mcp [OPTIONS]
"""

from __future__ import annotations

import sys
from .server import main

if __name__ == "__main__":
    sys.exit(main())
