"""
Ableton Live 12 MCP - Take Lane Tools & Comping Helpers
======================================================
Dedicated schema and helper definitions for TakeLane clip injection and arrangement comping.
"""

from __future__ import annotations

from typing import Any, Dict, List

TAKE_LANE_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "live12_take_lane_create_audio_clip",
        "description": "Creates an audio clip directly on a specified track take lane at a given beat time in Ableton Live 12 (TakeLane.create_audio_clip).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "track_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based track index."
                },
                "take_lane_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based take lane index."
                },
                "file_path": {
                    "type": "string",
                    "description": "Absolute filesystem path to the audio file (WAV, AIFF, FLAC, MP3) to insert."
                },
                "time": {
                    "type": "number",
                    "minimum": 0.0,
                    "description": "Beat position in arrangement timeline where the clip will be placed."
                }
            },
            "required": ["track_index", "take_lane_index", "file_path", "time"]
        }
    }
]

__all__ = ["TAKE_LANE_TOOLS"]
