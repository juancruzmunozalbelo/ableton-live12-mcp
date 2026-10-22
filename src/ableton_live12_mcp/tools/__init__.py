"""
Ableton Live 12 MCP Server - 75-Tool Catalog & Schema Engine
============================================================
Aggregates all 75 MCP tools across 6 functional domains:
- Domain 1: Transport, Song & Arrangement (15 tools)
- Domain 2: Tracks, TakeLanes, Scenes & Routing (15 tools)
- Domain 3: Clips, Extended MIDI & Warping (16 tools)
- Domain 4: Browser, Devices, Racks & Parameters (17 tools)
- Domain 5: View, Native Dialogs & OS Actions (8 tools)
- Domain 6: Universal LOM Escape Hatch (4 tools)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .clip_tools import CLIP_TOOLS
from .device_tools import DEVICE_TOOLS
from .lom_tools import LOM_TOOLS
from .song_tools import SONG_TOOLS
from .track_tools import TRACK_TOOLS
from .validator import ValidationError, validate_argument_dict
from .view_tools import VIEW_TOOLS

ALL_TOOLS: List[Dict[str, Any]] = (
    SONG_TOOLS
    + TRACK_TOOLS
    + CLIP_TOOLS
    + DEVICE_TOOLS
    + VIEW_TOOLS
    + LOM_TOOLS
)

TOOL_MAP: Dict[str, Dict[str, Any]] = {tool["name"]: tool for tool in ALL_TOOLS}


def get_tool_catalog() -> List[Dict[str, Any]]:
    """Returns the complete 75-tool MCP catalog with Draft-07 schemas."""
    return list(ALL_TOOLS)


def get_tool_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Looks up a tool definition by canonical name."""
    return TOOL_MAP.get(name)


def validate_tool_call(name: str, arguments: Dict[str, Any]) -> None:
    """Validates arguments against the tool's inputSchema."""
    tool = TOOL_MAP.get(name)
    if not tool:
        raise ValidationError(f"Unknown tool '{name}'")
    schema = tool.get("inputSchema", {})
    validate_argument_dict(schema, arguments, path=name)


__all__ = [
    "ALL_TOOLS",
    "TOOL_MAP",
    "get_tool_catalog",
    "get_tool_by_name",
    "validate_tool_call",
    "ValidationError",
    "SONG_TOOLS",
    "TRACK_TOOLS",
    "CLIP_TOOLS",
    "DEVICE_TOOLS",
    "VIEW_TOOLS",
    "LOM_TOOLS",
]
