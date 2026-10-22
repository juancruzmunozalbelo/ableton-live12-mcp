"""
Domain 6: Universal LOM Escape Hatch Tools (4 tools)
===================================================
Implements MCP schemas for dynamic introspection, property access,
property mutation, and method invocation across the Live Object Model.
"""

from __future__ import annotations

from typing import Any, Dict, List

LOM_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "live12_lom_inspect",
        "description": "Dynamically introspects any object reachable in the Ableton Live Object Model (LOM) from 'live_set' or 'live_app', returning its Python/C++ type, readable properties, and callable methods.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target_path": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Dotted path from LOM root (e.g. 'live_set', 'live_set.tracks.0', 'live_set.tracks.0.clip_slots.0.clip', 'live_app.view')."
                }
            },
            "required": ["target_path"]
        }
    },
    {
        "name": "live12_lom_get",
        "description": "Reads the value of any property on an object in the Ableton Live Object Model (LOM) at the specified path.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target_path": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Dotted path to target LOM object (e.g. 'live_set', 'live_set.tracks.0.mixer_device')."
                },
                "property_name": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Name of the property to read (e.g. 'tempo', 'name', 'volume')."
                }
            },
            "required": ["target_path", "property_name"]
        }
    },
    {
        "name": "live12_lom_set",
        "description": "Dynamically sets the value of any writable property on an object in the Ableton Live Object Model (LOM).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target_path": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Dotted path to target LOM object (e.g. 'live_set', 'live_set.tracks.0')."
                },
                "property_name": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Name of property to modify (e.g. 'tempo', 'name', 'color')."
                },
                "value": {
                    "description": "New value to assign. Can be string, number, boolean, array, or object."
                }
            },
            "required": ["target_path", "property_name", "value"]
        }
    },
    {
        "name": "live12_lom_call",
        "description": "Invokes any callable method on an object in the Ableton Live Object Model (LOM) at target_path, passing positional and keyword arguments.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target_path": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Dotted path to target LOM object (e.g. 'live_set.tracks.0', 'live_set.tracks.0.clip_slots.0.clip')."
                },
                "method_name": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Method name to invoke (e.g. 'stop_all_clips', 'duplicate_clip_slot', 'add_new_notes')."
                },
                "args": {
                    "type": "array",
                    "default": [],
                    "description": "Positional arguments list to pass to the method."
                },
                "kwargs": {
                    "type": "object",
                    "default": {},
                    "description": "Keyword arguments dictionary to pass to the method."
                }
            },
            "required": ["target_path", "method_name"]
        }
    }
]
