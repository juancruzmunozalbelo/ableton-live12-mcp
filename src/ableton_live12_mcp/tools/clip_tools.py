"""
Domain 3: Clips, Extended MIDI & Warping Tools (16 tools)
=========================================================
Implements MCP schemas for Session clips, Live 12 extended MIDI notes
(pitch, probability, velocity_deviation, release_velocity, mute), quantization,
audio clip warping modes, warp markers, arrangement duplication, targeted note removal,
algorithmic MIDI transformations, clip envelopes & automation, and groove pool management.
"""

from __future__ import annotations

from typing import Any, Dict, List

CLIP_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "live12_clip_create",
        "description": "Creates a new empty Session clip in Ableton Live 12 (ClipSlot.create_clip).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "track_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based track index."
                },
                "slot_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based clip slot index."
                },
                "length_beats": {
                    "type": "number",
                    "exclusiveMinimum": 0.0,
                    "default": 4.0,
                    "description": "Initial length of the created clip in musical beats (default 4.0 = 1 measure in 4/4)."
                },
                "name": {
                    "type": "string",
                    "description": "Optional name for the created clip."
                }
            },
            "required": ["track_index", "slot_index"]
        }
    },
    {
        "name": "live12_clip_delete",
        "description": "Deletes the clip occupying a Session view slot in Ableton Live 12 (ClipSlot.delete_clip).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "track_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based track index."
                },
                "slot_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based clip slot index."
                }
            },
            "required": ["track_index", "slot_index"]
        }
    },
    {
        "name": "live12_clip_delete_arrangement",
        "description": "Deletes an Arrangement view clip by its position on a track in Ableton Live 12 (Track.delete_clip). Use this to remove clips laid out in the Arrangement timeline (live12_clip_delete only handles Session view slots).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "track_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based track index."
                },
                "clip_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based index of the clip inside the track's arrangement_clips collection."
                }
            },
            "required": ["track_index", "clip_index"]
        }
    },
    {
        "name": "live12_clip_fire",
        "description": "Fires / triggers playback of a clip slot in Ableton Live 12 (Clip.fire).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "track_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based track index."
                },
                "slot_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based clip slot index."
                }
            },
            "required": ["track_index", "slot_index"]
        }
    },
    {
        "name": "live12_clip_stop",
        "description": "Stops playback of a running clip slot in Ableton Live 12 (Clip.stop).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "track_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based track index."
                },
                "slot_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based clip slot index."
                }
            },
            "required": ["track_index", "slot_index"]
        }
    },
    {
        "name": "live12_clip_set_properties",
        "description": "Configures loop and marker parameters of a clip in Ableton Live 12 (Clip.loop, Clip.loop_start, Clip.loop_end, Clip.start_marker).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "track_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based track index."
                },
                "slot_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based clip slot index."
                },
                "loop": {
                    "type": "boolean",
                    "description": "Enable or disable clip looping."
                },
                "loop_start": {
                    "type": "number",
                    "minimum": 0.0,
                    "description": "Loop start position in beats."
                },
                "loop_end": {
                    "type": "number",
                    "minimum": 0.0,
                    "description": "Loop end position in beats."
                },
                "start_marker": {
                    "type": "number",
                    "minimum": 0.0,
                    "description": "Playback start marker position in beats."
                }
            },
            "required": ["track_index", "slot_index"]
        }
    },
    {
        "name": "live12_clip_add_notes",
        "description": "Inserts one or more MIDI notes into a clip using Ableton Live 12 extended note attributes (Clip.add_new_notes). Supports Live 12 note probability, velocity deviation, and release velocity.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "track_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based track index."
                },
                "slot_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based clip slot index."
                },
                "notes": {
                    "type": "array",
                    "minItems": 1,
                    "description": "List of Live 12 extended MIDI note specifications.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "pitch": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": 127,
                                "description": "MIDI note number [0..127] (e.g. 60 for Middle C)."
                            },
                            "start_time": {
                                "type": "number",
                                "minimum": 0.0,
                                "description": "Start position of the note in clip beats."
                            },
                            "duration": {
                                "type": "number",
                                "exclusiveMinimum": 0.0,
                                "description": "Duration of the note in beats."
                            },
                            "velocity": {
                                "type": "number",
                                "minimum": 0.0,
                                "maximum": 127.0,
                                "default": 100.0,
                                "description": "Note strike velocity [0.0..127.0]."
                            },
                            "velocity_deviation": {
                                "type": "number",
                                "minimum": -127.0,
                                "maximum": 127.0,
                                "default": 0.0,
                                "description": "Live 12 velocity randomization range [-127.0..127.0]."
                            },
                            "release_velocity": {
                                "type": "number",
                                "minimum": 0.0,
                                "maximum": 127.0,
                                "default": 64.0,
                                "description": "Note-off release velocity [0.0..127.0]."
                            },
                            "probability": {
                                "type": "number",
                                "minimum": 0.0,
                                "maximum": 1.0,
                                "default": 1.0,
                                "description": "Live 12 playback probability [0.0..1.0] (1.0 = 100% trigger)."
                            },
                            "mute": {
                                "type": "boolean",
                                "default": False,
                                "description": "Whether the note is muted / deactivated."
                            }
                        },
                        "required": ["pitch", "start_time", "duration"]
                    }
                }
            },
            "required": ["track_index", "slot_index", "notes"]
        }
    },
    {
        "name": "live12_clip_get_notes",
        "description": "Retrieves all MIDI notes within a specified time window from a clip in Ableton Live 12 (Clip.get_notes_extended), including Live 12 note_id, probability, velocity_deviation, and release_velocity.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "track_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based track index."
                },
                "slot_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based clip slot index."
                },
                "start_time": {
                    "type": "number",
                    "minimum": 0.0,
                    "default": 0.0,
                    "description": "Start position of inspection window in beats."
                },
                "time_span": {
                    "type": "number",
                    "exclusiveMinimum": 0.0,
                    "default": 65536.0,
                    "description": "Length of inspection window in beats."
                }
            },
            "required": ["track_index", "slot_index"]
        }
    },
    {
        "name": "live12_clip_modify_notes",
        "description": "Modifies existing notes in an Ableton Live 12 clip (Clip.apply_note_modifications) by matching note_id or pitch.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "track_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based track index."
                },
                "slot_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based clip slot index."
                },
                "note_modifications": {
                    "type": "array",
                    "minItems": 1,
                    "description": "List of modifications to apply.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "note_id": {
                                "type": "integer",
                                "description": "Live 12 note ID identifying the note to modify."
                            },
                            "pitch": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": 127,
                                "description": "Pitch number to match if note_id is omitted, or new pitch."
                            },
                            "start_time": {"type": "number", "minimum": 0.0},
                            "duration": {"type": "number", "exclusiveMinimum": 0.0},
                            "velocity": {"type": "number", "minimum": 0.0, "maximum": 127.0},
                            "velocity_deviation": {"type": "number", "minimum": -127.0, "maximum": 127.0},
                            "release_velocity": {"type": "number", "minimum": 0.0, "maximum": 127.0},
                            "probability": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                            "mute": {"type": "boolean"}
                        }
                    }
                }
            },
            "required": ["track_index", "slot_index", "note_modifications"]
        }
    },
    {
        "name": "live12_clip_quantize",
        "description": "Quantizes MIDI notes in a clip to a musical beat grid (Clip.quantize).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "track_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based track index."
                },
                "slot_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based clip slot index."
                },
                "grid": {
                    "type": "number",
                    "exclusiveMinimum": 0.0,
                    "default": 0.25,
                    "description": "Quantization grid division in beats (e.g. 0.25 = 1/16th, 0.5 = 1/8th, 1.0 = 1/4th)."
                },
                "amount": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "default": 1.0,
                    "description": "Quantization strength from 0.0 (0%) to 1.0 (100% snap to grid)."
                }
            },
            "required": ["track_index", "slot_index"]
        }
    },
    {
        "name": "live12_audio_clip_set_warp",
        "description": "Configures audio clip warping mode, pitch shift, and gain in Ableton Live 12.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "track_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based track index."
                },
                "slot_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based clip slot index."
                },
                "warping": {
                    "type": "boolean",
                    "description": "Enable or disable audio time-stretching / warping."
                },
                "warp_mode": {
                    "type": "string",
                    "enum": [
                        "Beats", "Tones", "Texture", "Re-Pitch", "Complex", "Complex Pro",
                        "beats", "tones", "texture", "repitch", "complex", "complex_pro"
                    ],
                    "description": "Warping algorithm."
                },
                "pitch_shift": {
                    "type": "number",
                    "minimum": -48.0,
                    "maximum": 48.0,
                    "description": "Coarse pitch shift in semitones [-48.0..48.0]."
                },
                "gain": {
                    "type": "number",
                    "description": "Audio clip gain factor or dB value."
                }
            },
            "required": ["track_index", "slot_index"]
        }
    },
    {
        "name": "live12_audio_clip_add_warp_marker",
        "description": "Inserts a warp marker into an audio clip in Ableton Live 12 (Clip.add_warp_marker).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "track_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based track index."
                },
                "slot_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based clip slot index."
                },
                "beat_time": {
                    "type": "number",
                    "minimum": 0.0,
                    "description": "Musical beat time position."
                },
                "sample_time": {
                    "type": "number",
                    "minimum": 0.0,
                    "description": "Corresponding sample audio time in seconds."
                }
            },
            "required": ["track_index", "slot_index", "beat_time", "sample_time"]
        }
    },
    {
        "name": "live12_clip_duplicate_to_arrangement",
        "description": "Duplicates a Session view clip directly into the Arrangement timeline at a specified beat time (Track.duplicate_clip_to_arrangement).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "track_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based track index."
                },
                "slot_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based session clip slot index."
                },
                "arrangement_time": {
                    "type": "number",
                    "minimum": 0.0,
                    "description": "Target arrangement timeline beat position where the clip will be placed."
                }
            },
            "required": ["track_index", "slot_index", "arrangement_time"]
        }
    },
    {
        "name": "live12_clip_remove_notes",
        "description": "Removes MIDI notes from an Ableton Live 12 clip by note IDs or by beat/pitch window (Clip.remove_notes_by_id or Clip.remove_notes_extended).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "track_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based track index."
                },
                "slot_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based clip slot index."
                },
                "note_ids": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "List of Live 12 note IDs to remove."
                },
                "start_time": {
                    "type": "number",
                    "minimum": 0.0,
                    "description": "Start position of beat window for note removal."
                },
                "time_span": {
                    "type": "number",
                    "exclusiveMinimum": 0.0,
                    "description": "Duration of beat window for note removal."
                },
                "from_pitch": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 127,
                    "description": "Lowest pitch to remove [0..127]."
                },
                "pitch_span": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 128,
                    "description": "Pitch range span [1..128]."
                }
            },
            "required": ["track_index", "slot_index"]
        }
    },
    {
        "name": "live12_clip_transform_midi",
        "description": "Applies algorithmic MIDI transformations in Ableton Live 12: humanize timing/velocity, velocity ramps, Euclidean rhythm generation, arpeggiation, or pitch quantization to musical scale.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "track_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based track index."
                },
                "slot_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based clip slot index."
                },
                "transformation": {
                    "type": "string",
                    "enum": ["humanize", "velocity_ramp", "euclidean", "arpeggiate", "quantize_pitch", "fit_to_scale"],
                    "description": "Transformation algorithm to apply."
                },
                "params": {
                    "type": "object",
                    "description": "Parameters for the chosen transformation (e.g. {'timing_jitter': 0.02, 'velocity_jitter': 8.0} for humanize; {'start_velocity': 30, 'end_velocity': 110} for velocity_ramp; {'steps': 16, 'pulses': 5, 'pitch': 60} for euclidean; {'scale_name': 'Minor', 'root_note': 0} for fit_to_scale)."
                }
            },
            "required": ["track_index", "slot_index", "transformation"]
        }
    },
    {
        "name": "live12_clip_envelope_control",
        "description": "Inspects and manipulates parameter automation envelopes in an Ableton Live 12 clip (set envelope breakpoint/step, inspect envelope status, clear envelope for a parameter, clear all envelopes, or re-enable automation).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "track_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based track index."
                },
                "slot_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based clip slot index."
                },
                "action": {
                    "type": "string",
                    "enum": ["inspect", "set_step", "clear", "clear_all", "re_enable"],
                    "description": "Automation action: 'inspect' envelope existence/parameters, 'set_step' insert breakpoint value, 'clear' parameter envelope, 'clear_all' remove all envelopes, 're_enable' re-enable automation."
                },
                "device_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based device index."
                },
                "parameter_identifier": {
                    "anyOf": [
                        {"type": "string"},
                        {"type": "integer", "minimum": 0}
                    ],
                    "description": "Device parameter name or zero-based parameter index."
                },
                "time": {
                    "type": "number",
                    "minimum": 0.0,
                    "description": "Beat position within clip for set_step."
                },
                "value": {
                    "type": "number",
                    "description": "Target parameter value for set_step."
                }
            },
            "required": ["track_index", "slot_index", "action"]
        }
    },
    {
        "name": "live12_groove_pool_control",
        "description": "Manages the Ableton Live 12 Groove Pool: queries pool grooves, adjusts global song groove amount, assigns groove templates to clips, or inspects clip groove status.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["list_pool", "set_song_amount", "assign_clip", "clear_clip", "get_clip_groove"],
                    "description": "Groove action: 'list_pool' query project grooves, 'set_song_amount' set global groove intensity [0.0..1.0], 'assign_clip' assign groove to clip, 'clear_clip' detach groove, 'get_clip_groove' inspect clip groove."
                },
                "groove_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based index of groove in Song.groove_pool.grooves."
                },
                "amount": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "Global groove intensity amount for set_song_amount."
                },
                "track_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based track index for clip assignment."
                },
                "slot_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based clip slot index for clip assignment."
                }
            },
            "required": ["action"]
        }
    }
]
