"""
Domain 4: Browser, Devices, Racks & Parameters Tools (17 tools)
==============================================================
Implements MCP schemas for browser search/loading, preview/audition, device parameters, racks,
macro configuration and variations, drum pads, CC Control device, and specialized Live 12 devices
(Wavetable matrix, Simpler, Meld, Roar, Drift).
"""

from __future__ import annotations

from typing import Any, Dict, List

DEVICE_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "live12_browser_search",
        "description": "Searches the Ableton Live 12 Browser for instruments, effects, presets, samples, packs, and plug-ins.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Search keyword or device name (e.g. 'Drift', 'Wavetable', 'Reverb')."
                },
                "category": {
                    "type": "string",
                    "enum": ["all", "instruments", "audio_effects", "midi_effects", "drums", "samples", "packs", "user_library", "plugins", "max"],
                    "default": "all",
                    "description": "Optional category filter."
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "live12_browser_load_item",
        "description": "Loads a browser item (instrument, effect, rack, or preset) onto an Ableton Live 12 track, chain, or drum rack pad (Application.browser.load_item).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "track_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based target track index."
                },
                "browser_item_uri": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Canonical browser item URI from browser search (e.g. 'live:device:drift', 'live:device:wavetable')."
                },
                "chain_index": {
                    "type": "integer",
                    "default": -1,
                    "description": "Optional chain index if inserting inside an existing Rack device (-1 for top-level track device chain)."
                },
                "drum_pad_index": {
                    "type": "integer",
                    "default": -1,
                    "description": "Optional drum pad index [0..127] if loading onto a Drum Rack pad (-1 for standard track insertion)."
                }
            },
            "required": ["track_index", "browser_item_uri"]
        }
    },
    {
        "name": "live12_device_list",
        "description": "Queries all devices in the device chain of an Ableton Live 12 track (Track.devices).",
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
        "name": "live12_device_get_parameters",
        "description": "Reads all parameters of an Ableton Live 12 device (Device.parameters), including min, max, quantized status, raw value, and normalized value.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "track_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based track index."
                },
                "device_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based device index."
                }
            },
            "required": ["track_index", "device_index"]
        }
    },
    {
        "name": "live12_device_set_parameter",
        "description": "Sets the value of a device parameter in Ableton Live 12 (DeviceParameter.value). Supports both raw engineering values and normalized [0.0..1.0] inputs.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "track_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based track index."
                },
                "device_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based device index."
                },
                "parameter_identifier": {
                    "anyOf": [
                        {"type": "string", "description": "Exact parameter name (e.g. 'Filter Freq', 'Volume')."},
                        {"type": "integer", "minimum": 0, "description": "Zero-based parameter index in Device.parameters."}
                    ],
                    "description": "Parameter name or index."
                },
                "value": {
                    "type": "number",
                    "description": "New parameter value."
                },
                "normalized": {
                    "type": "boolean",
                    "default": False,
                    "description": "If true, 'value' is interpreted as a normalized float between 0.0 (min) and 1.0 (max)."
                }
            },
            "required": ["track_index", "device_index", "parameter_identifier", "value"]
        }
    },
    {
        "name": "live12_device_toggle",
        "description": "Enables or disables (bypasses) a device on a track in Ableton Live 12.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "track_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based track index."
                },
                "device_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based device index."
                },
                "enabled": {
                    "type": "boolean",
                    "description": "True to activate the device; False to bypass/disable."
                }
            },
            "required": ["track_index", "device_index", "enabled"]
        }
    },
    {
        "name": "live12_rack_macro_control",
        "description": "Controls one of the 16 macro controls on an Ableton Live 12 Rack device (Instrument Rack, Audio Effect Rack, MIDI Effect Rack).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "track_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based track index."
                },
                "device_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based index of the Rack device."
                },
                "macro_index": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 15,
                    "description": "Zero-based macro index between 0 and 15 (corresponding to Macro 1 through 16)."
                },
                "value": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "Normalized macro knob position between 0.0 and 1.0."
                }
            },
            "required": ["track_index", "device_index", "macro_index", "value"]
        }
    },
    {
        "name": "live12_rack_variation_control",
        "description": "Manages Macro Variations on an Ableton Live 12 Rack device (store current macro snapshot, recall a variation, or delete a variation).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "track_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based track index."
                },
                "device_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based index of the Rack device."
                },
                "action": {
                    "type": "string",
                    "enum": ["store", "recall", "delete"],
                    "description": "Action to perform: 'store' to snapshot current macros, 'recall' to load variation, 'delete' to remove variation."
                },
                "variation_index": {
                    "type": "integer",
                    "minimum": 0,
                    "default": 0,
                    "description": "Zero-based index of the variation to recall or delete."
                }
            },
            "required": ["track_index", "device_index", "action"]
        }
    },
    {
        "name": "live12_wavetable_modulation_matrix",
        "description": "Inspects or updates modulation assignments in the Ableton Live 12 Wavetable modulation matrix.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "track_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based track index."
                },
                "device_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based index of the Wavetable device."
                },
                "action": {
                    "type": "string",
                    "enum": ["set", "get", "clear"],
                    "description": "Matrix action: 'set' modulation depth, 'get' modulation depth, or 'clear' all matrix assignments."
                },
                "source": {
                    "type": "string",
                    "default": "",
                    "description": "Modulation source name (e.g. 'LFO 1', 'Env 2', 'Velocity', 'Modwheel')."
                },
                "target": {
                    "type": "string",
                    "default": "",
                    "description": "Target parameter name (e.g. 'Filter 1 Freq', 'Osc 1 Pos', 'Filter 1 Res')."
                },
                "amount": {
                    "type": "number",
                    "minimum": -1.0,
                    "maximum": 1.0,
                    "default": 0.0,
                    "description": "Modulation depth between -1.0 and 1.0."
                }
            },
            "required": ["track_index", "device_index", "action"]
        }
    },
    {
        "name": "live12_simpler_control",
        "description": "Controls specialized features of Ableton Simpler, including transient slicing to a Drum Rack or replacing the loaded sample audio file.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "track_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based track index."
                },
                "device_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based index of the Simpler device."
                },
                "action": {
                    "type": "string",
                    "enum": ["slice", "replace_sample"],
                    "description": "Simpler action: 'slice' to create slice points, 'replace_sample' to load audio file."
                },
                "params": {
                    "type": "object",
                    "description": "Action-specific parameters (e.g. {'sample_path': '/path/to/sample.wav'})."
                }
            },
            "required": ["track_index", "device_index", "action"]
        }
    },
    {
        "name": "live12_meld_control",
        "description": "Updates engine parameters on the Ableton Live 12 Meld bi-timbral macro synthesizer.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "track_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based track index."
                },
                "device_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based index of the Meld device."
                },
                "engine_params": {
                    "type": "object",
                    "description": "Dictionary of Meld engine parameters to update (e.g. {'macro_a': 0.5, 'macro_b': 0.8})."
                }
            },
            "required": ["track_index", "device_index", "engine_params"]
        }
    },
    {
        "name": "live12_roar_control",
        "description": "Configures distortion stages, routing configuration, and feedback settings on the Ableton Live 12 Roar saturation device.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "track_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based track index."
                },
                "device_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based index of the Roar device."
                },
                "stage_params": {
                    "type": "object",
                    "description": "Dictionary of Roar stage parameters (e.g. {'drive': 12.0, 'stage': 'single', 'bias': 0.2})."
                }
            },
            "required": ["track_index", "device_index", "stage_params"]
        }
    },
    {
        "name": "live12_drift_control",
        "description": "Configures voice mode, drift randomization, and oscillator parameters on the Ableton Live 12 Drift subtractive synthesizer.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "track_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based track index."
                },
                "device_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based index of the Drift device."
                },
                "voice_params": {
                    "type": "object",
                    "description": "Dictionary of Drift voice parameters (e.g. {'voice_mode': 'poly', 'drift': 0.35, 'filter_freq': 2200})."
                }
            },
            "required": ["track_index", "device_index", "voice_params"]
        }
    },
    {
        "name": "live12_browser_preview",
        "description": "Controls audio auditioning and hotswap monitoring in the Ableton Live 12 Browser (preview item, stop preview, inspect hotswap target).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["preview", "stop", "hotswap_status"],
                    "description": "Browser action: 'preview' starts audition playback of item, 'stop' terminates preview, 'hotswap_status' queries active hotswap state."
                },
                "browser_item_uri": {
                    "type": "string",
                    "description": "Canonical URI of the item to audition (e.g. 'live:sample:kick01')."
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "live12_rack_macro_config",
        "description": "Configures macro knobs on an Ableton Live 12 Rack device: sets visible macro count (1 to 16), adds macro, removes macro, randomizes macros, or queries rack chains.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "track_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based track index."
                },
                "device_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based index of Rack device."
                },
                "action": {
                    "type": "string",
                    "enum": ["get_config", "set_count", "add_macro", "remove_macro", "randomize"],
                    "description": "Rack action: 'get_config' read macro count and chain list, 'set_count' adjust visible macros, 'add_macro' increment, 'remove_macro' decrement, 'randomize' randomize macro values."
                },
                "count": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 16,
                    "description": "Target visible macro count [1..16] for set_count."
                }
            },
            "required": ["track_index", "device_index", "action"]
        }
    },
    {
        "name": "live12_drum_pad_control",
        "description": "Controls Drum Rack pads in Ableton Live 12: inspect pad status (name, note, chains), mute/solo pad, copy pad to another note (RackDevice.copy_pad), or delete chains on a pad.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "track_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based track index."
                },
                "device_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based index of Drum Rack device."
                },
                "action": {
                    "type": "string",
                    "enum": ["inspect_pads", "mute_pad", "solo_pad", "copy_pad", "delete_chains"],
                    "description": "Pad action: 'inspect_pads' queries active pads, 'mute_pad' toggles mute, 'solo_pad' toggles solo, 'copy_pad' duplicates pad to target note, 'delete_chains' removes chains on pad."
                },
                "pad_note": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 127,
                    "description": "MIDI note number of the drum pad [0..127] (e.g. 36 for C1)."
                },
                "target_note": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 127,
                    "description": "Destination MIDI note number for copy_pad."
                },
                "state": {
                    "type": "boolean",
                    "description": "Boolean state for mute_pad or solo_pad."
                }
            },
            "required": ["track_index", "device_index", "action"]
        }
    },
    {
        "name": "live12_cc_control",
        "description": "Controls the Ableton Live 12 CC Control MIDI device: maps MIDI continuous controllers (CC), sets output CC values, and configures custom MIDI automation targets.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "track_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based track index."
                },
                "device_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based index of CC Control device."
                },
                "action": {
                    "type": "string",
                    "enum": ["set_cc", "get_mappings"],
                    "description": "CC Control action: 'set_cc' sends or configures CC parameter, 'get_mappings' queries active CC definitions."
                },
                "cc_number": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 127,
                    "description": "MIDI CC number [0..127] (e.g. 1=Modulation, 7=Volume, 10=Pan, 11=Expression, 74=Cutoff)."
                },
                "value": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 127,
                    "description": "MIDI CC value [0..127]."
                },
                "channel": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 16,
                    "default": 1,
                    "description": "Target MIDI channel [1..16]."
                }
            },
            "required": ["track_index", "device_index", "action"]
        }
    }
]
