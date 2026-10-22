"""
Domain 2: Tracks, TakeLanes, Scenes & Routing Tools (15 tools)
==============================================================
Implements MCP schemas for track management, duplication, properties, grouping,
take lane comping, scenes, scene property configuration, routing inspection and configurations, and mixer faders/sends.
"""

from __future__ import annotations

from typing import Any, Dict, List

TRACK_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "live12_track_create",
        "description": "Creates a new track in Ableton Live 12 (Song.create_midi_track, Song.create_audio_track, or Song.create_return_track).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["midi", "audio", "return"],
                    "default": "midi",
                    "description": "Track type to create: 'midi', 'audio', or 'return'."
                },
                "index": {
                    "type": "integer",
                    "default": -1,
                    "description": "Zero-based track index position where the new track will be inserted. Pass -1 to append to end of tracks."
                }
            },
            "required": []
        }
    },
    {
        "name": "live12_track_delete",
        "description": "Deletes a track in Ableton Live 12 by its zero-based index (Song.delete_track).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "track_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based index of the track to delete."
                }
            },
            "required": ["track_index"]
        }
    },
    {
        "name": "live12_track_duplicate",
        "description": "Duplicates an existing track in Ableton Live 12 (Song.duplicate_track). The duplicate is inserted immediately after the source track.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "track_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based index of the source track to duplicate."
                }
            },
            "required": ["track_index"]
        }
    },
    {
        "name": "live12_track_set_properties",
        "description": "Updates properties of an existing track in Ableton Live 12, such as name, RGB integer color, solo, mute, and record arming.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "track_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based index of target track."
                },
                "name": {
                    "type": "string",
                    "description": "New track display name."
                },
                "color": {
                    "type": "integer",
                    "description": "RGB integer color value (e.g. 65280 for green, 16711680 for red)."
                },
                "solo": {
                    "type": "boolean",
                    "description": "Solo state of the track."
                },
                "mute": {
                    "type": "boolean",
                    "description": "Mute state of the track (True = muted/silent)."
                },
                "arm": {
                    "type": "boolean",
                    "description": "Record arm state of the track."
                }
            },
            "required": ["track_index"]
        }
    },
    {
        "name": "live12_track_group",
        "description": "Groups specified tracks together under a new group track in Ableton Live 12.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "track_indices": {
                    "type": "array",
                    "items": {"type": "integer", "minimum": 0},
                    "minItems": 1,
                    "description": "List of zero-based track indices to include in the group."
                }
            },
            "required": ["track_indices"]
        }
    },
    {
        "name": "live12_track_ungroup",
        "description": "Dissolves an existing group track in Ableton Live 12, promoting its member tracks to top-level.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "group_track_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based index of the group track to dissolve."
                }
            },
            "required": ["group_track_index"]
        }
    },
    {
        "name": "live12_take_lane_create",
        "description": "Creates a new take lane for comping on an audio or MIDI track in Ableton Live 12 (Track.create_take_lane).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "track_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based track index."
                }
            },
            "required": ["track_index"]
        }
    },
    {
        "name": "live12_take_lane_list",
        "description": "Queries all take lanes on a track in Ableton Live 12 (Track.take_lanes).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "track_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based track index."
                }
            },
            "required": ["track_index"]
        }
    },
    {
        "name": "live12_take_lane_comp_region",
        "description": "Comps a region from a take lane into the main arrangement track lane in Ableton Live 12.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "track_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based track index."
                },
                "lane_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based take lane index."
                },
                "start": {
                    "type": "number",
                    "minimum": 0.0,
                    "description": "Region start position in arrangement beats."
                },
                "length": {
                    "type": "number",
                    "exclusiveMinimum": 0.0,
                    "description": "Region length in beats."
                }
            },
            "required": ["track_index", "lane_index", "start", "length"]
        }
    },
    {
        "name": "live12_scene_create",
        "description": "Creates a new scene in Ableton Live 12 (Song.create_scene).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "index": {
                    "type": "integer",
                    "default": -1,
                    "description": "Zero-based index at which to insert the scene, or -1 to append at the end."
                }
            },
            "required": []
        }
    },
    {
        "name": "live12_scene_fire",
        "description": "Launches all clip slots aligned in a scene in Ableton Live 12 (Scene.fire).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based scene index to launch."
                }
            },
            "required": ["index"]
        }
    },
    {
        "name": "live12_routing_set",
        "description": "Configures input and output audio/MIDI routing and monitoring state for a track in Ableton Live 12.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "track_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based track index."
                },
                "input_type": {
                    "type": "string",
                    "description": "Input routing type (e.g. 'Ext. In', 'All Ins', 'No Input')."
                },
                "input_channel": {
                    "type": "string",
                    "description": "Input routing channel (e.g. '1/2', '1', '2', 'Ch. 1')."
                },
                "output_type": {
                    "type": "string",
                    "description": "Output routing type (e.g. 'Master', 'Sends Only', 'Ext. Out')."
                },
                "output_channel": {
                    "type": "string",
                    "description": "Output routing channel (e.g. '1/2', '3/4')."
                },
                "monitoring": {
                    "type": "string",
                    "enum": ["In", "Auto", "Off", "in", "auto", "off"],
                    "description": "Monitoring state: 'In' (listen to input), 'Auto' (monitor on record arm), or 'Off'."
                }
            },
            "required": ["track_index"]
        }
    },
    {
        "name": "live12_mixer_set",
        "description": "Adjusts track mixer controls in Ableton Live 12: volume fader, stereo panning, auxiliary send levels, and crossfader assignment.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "track_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based track index."
                },
                "volume": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "Mixer fader volume normalized between 0.0 and 1.0 (where 0.85 represents unity gain / 0 dB)."
                },
                "pan": {
                    "type": "number",
                    "minimum": -1.0,
                    "maximum": 1.0,
                    "description": "Stereo panning position between -1.0 (hard left) and 1.0 (hard right), with 0.0 as center."
                },
                "sends": {
                    "type": "object",
                    "additionalProperties": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0
                    },
                    "description": "Dictionary mapping zero-based send index strings to send level amounts [0.0, 1.0] (e.g. {'0': 0.5, '1': 0.25})."
                },
                "crossfader": {
                    "type": "string",
                    "enum": ["A", "B", "None"],
                    "description": "Crossfader assignment: 'A', 'B', or 'None'."
                }
            },
            "required": ["track_index"]
        }
    },
    {
        "name": "live12_scene_set_properties",
        "description": "Configures scene parameters in Ableton Live 12, including scene name, color, tempo assignment, and time signature assignment.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "scene_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based scene index."
                },
                "name": {
                    "type": "string",
                    "description": "Scene display name."
                },
                "color": {
                    "type": "integer",
                    "description": "RGB integer color value."
                },
                "tempo": {
                    "type": "number",
                    "minimum": 20.0,
                    "maximum": 999.0,
                    "description": "Tempo in BPM triggered when this scene is fired."
                },
                "tempo_enabled": {
                    "type": "boolean",
                    "description": "Whether scene tempo trigger is active."
                },
                "time_signature_numerator": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 99,
                    "description": "Time signature numerator triggered by this scene."
                },
                "time_signature_denominator": {
                    "type": "integer",
                    "enum": [1, 2, 4, 8, 16],
                    "description": "Time signature denominator triggered by this scene."
                },
                "time_signature_enabled": {
                    "type": "boolean",
                    "description": "Whether scene time signature trigger is active."
                }
            },
            "required": ["scene_index"]
        }
    },
    {
        "name": "live12_routing_get",
        "description": "Inspects current and available input and output audio/MIDI routing types and channels for a track in Ableton Live 12.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "track_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based track index."
                }
            },
            "required": ["track_index"]
        }
    }
]
