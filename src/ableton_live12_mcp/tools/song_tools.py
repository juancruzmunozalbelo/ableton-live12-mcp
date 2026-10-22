"""
Domain 1: Transport, Song & Arrangement Tools (15 tools)
========================================================
Implements MCP schemas for transport controls, tempo, time signature, loop,
punch markers, MIDI capture, global song state, scale, microtonal tuning,
arrangement locator cue points, and Link/tempo synchronization.
"""

from __future__ import annotations

from typing import Any, Dict, List

LIVE12_VALID_SCALES: List[str] = [
    # 35 Official Live 12 LOM Scale Names (from docs/lom_surface_12_4_6.json)
    "Major", "Minor", "Dorian", "Mixolydian", "Lydian", "Phrygian", "Locrian",
    "Whole Tone", "Half-whole Dim.", "Whole-half Dim.", "Minor Blues",
    "Minor Pentatonic", "Major Pentatonic", "Harmonic Minor", "Harmonic Major",
    "Dorian #4", "Phrygian Dominant", "Melodic Minor", "Lydian Augmented",
    "Lydian Dominant", "Super Locrian", "Bhairav", "Hungarian Minor",
    "8-Tone Spanish", "Hirajoshi", "In-Sen", "Iwato", "Kumoi", "Pelog Selisir",
    "Pelog Tembung", "Messiaen 3", "Messiaen 4", "Messiaen 5", "Messiaen 6",
    "Messiaen 7",
    # Common Aliases & Shorthands
    "Diminished", "Pentatonic",
]

SONG_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "live12_transport_play",
        "description": "Starts or resumes song playback in Ableton Live 12. If restart is true, playback starts from 1.1.1 or arrangement start marker; otherwise playback resumes from current playhead position.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "restart": {
                    "type": "boolean",
                    "default": False,
                    "description": "If true, restarts playback from 1.1.1. If false, continues from current playhead position."
                }
            },
            "required": []
        }
    },
    {
        "name": "live12_transport_stop",
        "description": "Stops song playback in Ableton Live 12 (Song.stop_playing).",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "live12_transport_record",
        "description": "Enables recording in Ableton Live 12. Can target either the arrangement timeline (Song.record_mode = True) or session clip slots (Song.session_record = True).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "record_mode": {
                    "type": "string",
                    "enum": ["arrangement", "session"],
                    "default": "arrangement",
                    "description": "Recording target: 'arrangement' for timeline recording, 'session' for Session view clip overdub/launch."
                }
            },
            "required": []
        }
    },
    {
        "name": "live12_transport_set_tempo",
        "description": "Sets the project tempo in beats per minute (BPM) in Ableton Live 12 (Song.tempo). Rejects values outside [20.0, 999.0].",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tempo": {
                    "type": "number",
                    "minimum": 20.0,
                    "maximum": 999.0,
                    "description": "Target tempo in BPM. Must be between 20.0 and 999.0."
                }
            },
            "required": ["tempo"]
        }
    },
    {
        "name": "live12_transport_set_time_signature",
        "description": "Sets the project time signature in Ableton Live 12 (Song.signature_numerator and signature_denominator). Denominator must be 1, 2, 4, 8, or 16.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "numerator": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 99,
                    "description": "Time signature numerator (beats per measure), between 1 and 99."
                },
                "denominator": {
                    "type": "integer",
                    "enum": [1, 2, 4, 8, 16],
                    "description": "Time signature denominator (note value division). Must be 1, 2, 4, 8, or 16."
                }
            },
            "required": ["numerator", "denominator"]
        }
    },
    {
        "name": "live12_transport_set_loop",
        "description": "Configures arrangement loop in Ableton Live 12 (Song.loop, Song.loop_start, Song.loop_length). Length must be strictly greater than 0.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "enabled": {
                    "type": "boolean",
                    "description": "Whether arrangement looping is active."
                },
                "start": {
                    "type": "number",
                    "minimum": 0.0,
                    "description": "Loop start position in arrangement beats."
                },
                "length": {
                    "type": "number",
                    "exclusiveMinimum": 0.0,
                    "description": "Loop length in beats. Must be positive."
                }
            },
            "required": ["enabled", "start", "length"]
        }
    },
    {
        "name": "live12_transport_set_punch",
        "description": "Enables or disables punch-in and punch-out markers for arrangement recording in Ableton Live 12.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "punch_in": {
                    "type": "boolean",
                    "description": "Enable punch-in recording at loop start."
                },
                "punch_out": {
                    "type": "boolean",
                    "description": "Enable punch-out recording at loop end."
                }
            },
            "required": ["punch_in", "punch_out"]
        }
    },
    {
        "name": "live12_transport_set_overdub",
        "description": "Enables or disables arrangement overdub in Ableton Live 12 (Song.arrangement_overdub).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "overdub": {
                    "type": "boolean",
                    "description": "Whether arrangement overdub is enabled."
                }
            },
            "required": ["overdub"]
        }
    },
    {
        "name": "live12_transport_set_metronome",
        "description": "Toggles the metronome click in Ableton Live 12 (Song.metronome).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "enabled": {
                    "type": "boolean",
                    "description": "Metronome audible state."
                }
            },
            "required": ["enabled"]
        }
    },
    {
        "name": "live12_song_capture_midi",
        "description": "Captures recently performed MIDI input without requiring an explicit recording pass in Ableton Live 12 (Song.capture_midi).",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "live12_song_get_state",
        "description": "Reads comprehensive song and transport state from Ableton Live 12, including tempo, time signature, playing status, loop parameters, project musical scale, tuning system, and track/scene counts.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "live12_song_set_scale",
        "description": "Sets the global musical scale and root note in Ableton Live 12 (Song.scale_information). Root note is 0 for C, 1 for C#, ..., 11 for B.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "root_note": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 11,
                    "description": "Pitch class integer for root note: 0=C, 1=C#, 2=D, 3=D#, 4=E, 5=F, 6=F#, 7=G, 8=G#, 9=A, 10=A#, 11=B."
                },
                "scale_name": {
                    "type": "string",
                    "enum": LIVE12_VALID_SCALES,
                    "description": "Name of the musical scale."
                }
            },
            "required": ["root_note", "scale_name"]
        }
    },
    {
        "name": "live12_song_set_tuning_system",
        "description": "Loads and applies a microtonal or alternative tuning system in Ableton Live 12 (Song.tuning_system).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tuning_name": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Name or identifier of the tuning system (e.g. 'Werckmeister III', '19-EDO', 'Equal Temperament')."
                }
            },
            "required": ["tuning_name"]
        }
    },
    {
        "name": "live12_cue_point_control",
        "description": "Manages arrangement locator cue points in Ableton Live 12: create locator at beat time, delete locator, jump playhead to cue point, or list all project locators.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["create", "delete", "jump", "list"],
                    "description": "Cue point action: 'create' new locator, 'delete' locator, 'jump' playhead to locator, or 'list' all locators."
                },
                "time": {
                    "type": "number",
                    "minimum": 0.0,
                    "description": "Arrangement beat time for create action."
                },
                "name": {
                    "type": "string",
                    "description": "Display name for the locator cue point."
                },
                "cue_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based index of cue point for delete or jump actions."
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "live12_tempo_sync_control",
        "description": "Controls synchronization features in Ableton Live 12: toggles Ableton Link, enables tempo follower, executes tap tempo, or nudges song tempo up/down.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["get_status", "set_link", "set_follower", "tap_tempo", "nudge_up", "nudge_down"],
                    "description": "Sync action: 'get_status' read Link/Follower state, 'set_link' toggle Ableton Link, 'set_follower' toggle tempo follower, 'tap_tempo' tap beat tempo, 'nudge_up' tempo push, 'nudge_down' tempo pull."
                },
                "enabled": {
                    "type": "boolean",
                    "description": "Target state for set_link or set_follower."
                }
            },
            "required": ["action"]
        }
    }
]
