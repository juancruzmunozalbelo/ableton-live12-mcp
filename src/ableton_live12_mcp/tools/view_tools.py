"""
Domain 5: View, Native Dialogs & OS Actions Tools (8 tools)
===========================================================
Implements MCP schemas for view navigation, selection synchronization,
in-LOM modal dialogs, OS-level file operations (save, open, export), and Undo/Redo transactions.
"""

from __future__ import annotations

from typing import Any, Dict, List

VIEW_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "live12_view_switch",
        "description": "Switches the primary active view in the Ableton Live 12 GUI (Application.view.show_view or focus_view).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "view_name": {
                    "type": "string",
                    "enum": ["Session", "Arranger", "Detail", "Detail/Clip", "Detail/DeviceChain", "Browser"],
                    "description": "Canonical name of the Ableton Live 12 GUI view to show or focus."
                }
            },
            "required": ["view_name"]
        }
    },
    {
        "name": "live12_view_select",
        "description": "Updates GUI selection focus in Ableton Live 12 (selected track, selected scene, highlighted clip slot, or selected device).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "track_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Optional zero-based track index to select in the GUI."
                },
                "scene_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Optional zero-based scene index to select in the GUI."
                },
                "clip_slot": {
                    "type": "array",
                    "items": {"type": "integer", "minimum": 0},
                    "minItems": 2,
                    "maxItems": 2,
                    "description": "Optional [track_index, slot_index] tuple to highlight in Session view."
                },
                "device_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Optional zero-based device index on selected track to focus."
                }
            },
            "required": []
        }
    },
    {
        "name": "live12_dialog_inspect",
        "description": "Inspects open native modal dialogs in Ableton Live 12 (Application.open_dialog_count and Application.current_dialog_message).",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "live12_dialog_press",
        "description": "Presses a button on the currently open modal dialog in Ableton Live 12 (Application.press_current_dialog_button). 0 is typically OK / Confirm; 1 is Cancel / Secondary.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "button_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based button index to press (0=default/OK, 1=cancel)."
                }
            },
            "required": ["button_index"]
        }
    },
    {
        "name": "live12_os_save_set",
        "description": "Triggers saving the current Ableton Live project set (.als) to a destination path on macOS.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "destination_path": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Absolute destination filesystem path ending in .als."
                }
            },
            "required": ["destination_path"]
        }
    },
    {
        "name": "live12_os_open_set",
        "description": "Opens an Ableton Live Set (.als) project document in Ableton Live 12.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "als_path": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Absolute filesystem path to the .als file."
                }
            },
            "required": ["als_path"]
        }
    },
    {
        "name": "live12_os_export_audio",
        "description": "Triggers audio bounce / render in Ableton Live 12 to a target destination WAV file.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "destination_wav_path": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Absolute filesystem destination path for the rendered .wav file."
                },
                "render_settings": {
                    "type": "object",
                    "description": "Optional export settings dictionary (sample_rate, bit_depth, dither_type, render_start, render_length)."
                }
            },
            "required": ["destination_wav_path"]
        }
    },
    {
        "name": "live12_undo_redo",
        "description": "Executes Undo and Redo operations in Ableton Live 12 (Song.undo, Song.redo), inspects undo history status, or demarcates transactional undo steps.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["undo", "redo", "status", "begin_step", "end_step"],
                    "description": "Undo action: 'undo' reverts last action, 'redo' reapplies undone action, 'status' queries can_undo/can_redo, 'begin_step' starts transaction, 'end_step' closes transaction."
                }
            },
            "required": ["action"]
        }
    }
]
