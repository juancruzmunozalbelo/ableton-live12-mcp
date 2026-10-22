#!/usr/bin/env python3
"""
Interactive GitHub Pages Generator for Ableton Live 12 MCP.
Generates docs/index.html as a self-contained, responsive, dark-luxury studio site.
Embeds:
- Media showcase: MP4 video, WAV audio player, animated GIF, SVG architecture, SVG terminal recording.
- Interactive MCP Tool Explorer (all 75 tools) with live search, category pills, schema previews, and copy agy call.
- Interactive LOM Class Explorer (all 49 classes) extracted from docs/lom_surface_12_4_6.json.
- Comparison matrix against legacy MCPs.
- Antigravity (agy) prompt recipes.
- Clean-room and open-source governance notices.
"""

import json
import os
import sys

# All 75 MCP tools across 20 Manual Chapters
TOOLS_CATALOG = [
    # Chapter 1: Arrangement View & Cue Points (Domain 1)
    {
        "name": "live12_transport_play",
        "chapter": 1,
        "category": "Arrangement & Transport",
        "description": "Starts playback in Ableton Live at the current arrangement song position or from clip slot.",
        "params": "None",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_transport_play", Arguments={})'
    },
    {
        "name": "live12_transport_stop",
        "chapter": 1,
        "category": "Arrangement & Transport",
        "description": "Stops playback and halts transport playback in Ableton Live.",
        "params": "None",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_transport_stop", Arguments={})'
    },
    {
        "name": "live12_transport_record",
        "chapter": 1,
        "category": "Arrangement & Transport",
        "description": "Toggles arrangement recording or session recording mode on/off.",
        "params": "record_mode (bool, optional)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_transport_record", Arguments={"record_mode": True})'
    },
    {
        "name": "live12_transport_set_tempo",
        "chapter": 1,
        "category": "Arrangement & Transport",
        "description": "Sets global project tempo in beats per minute (BPM) [20.0..999.0].",
        "params": "tempo (float: 20.0-999.0)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_transport_set_tempo", Arguments={"tempo": 124.0})'
    },
    {
        "name": "live12_transport_set_time_signature",
        "chapter": 1,
        "category": "Arrangement & Transport",
        "description": "Sets global time signature numerator (1-99) and denominator (1, 2, 4, 8, 16).",
        "params": "numerator (int), denominator (int)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_transport_set_time_signature", Arguments={"numerator": 4, "denominator": 4})'
    },
    {
        "name": "live12_transport_set_loop",
        "chapter": 1,
        "category": "Arrangement & Transport",
        "description": "Configures arrangement timeline loop state, start position in beats, and loop length.",
        "params": "loop (bool), loop_start (float), loop_length (float)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_transport_set_loop", Arguments={"loop": True, "loop_start": 0.0, "loop_length": 32.0})'
    },
    {
        "name": "live12_transport_set_punch",
        "chapter": 1,
        "category": "Arrangement & Transport",
        "description": "Configures arrangement punch-in and punch-out recording markers.",
        "params": "punch_in (bool), punch_out (bool)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_transport_set_punch", Arguments={"punch_in": True, "punch_out": True})'
    },
    {
        "name": "live12_transport_set_overdub",
        "chapter": 1,
        "category": "Arrangement & Transport",
        "description": "Toggles MIDI overdubbing and arrangement overdub on/off.",
        "params": "overdub (bool)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_transport_set_overdub", Arguments={"overdub": True})'
    },
    {
        "name": "live12_cue_point_control",
        "chapter": 1,
        "category": "Arrangement & Transport",
        "description": "Manages arrangement locator cue points: create locator at beat time, delete, jump playhead, or list locators.",
        "params": "action ('create'|'delete'|'jump'|'list'), time (float), name (str), cue_index (int)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_cue_point_control", Arguments={"action": "create", "time": 16.0, "name": "Drop 1"})'
    },
    {
        "name": "live12_clip_duplicate_to_arrangement",
        "chapter": 1,
        "category": "Arrangement & Transport",
        "description": "Duplicates a Session view clip directly into the Arrangement timeline at a specified beat time.",
        "params": "track_index (int), slot_index (int), arrangement_time (float)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_clip_duplicate_to_arrangement", Arguments={"track_index": 0, "slot_index": 0, "arrangement_time": 32.0})'
    },

    # Chapter 2: Session View & Scenes (Domain 2)
    {
        "name": "live12_scene_create",
        "chapter": 2,
        "category": "Session & Scenes",
        "description": "Creates a new scene in the Session view at the designated index.",
        "params": "scene_index (int, optional)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_scene_create", Arguments={"scene_index": 1})'
    },
    {
        "name": "live12_scene_fire",
        "chapter": 2,
        "category": "Session & Scenes",
        "description": "Fires all clip slots in the designated scene index simultaneously.",
        "params": "scene_index (int)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_scene_fire", Arguments={"scene_index": 0})'
    },
    {
        "name": "live12_scene_set_properties",
        "chapter": 2,
        "category": "Session & Scenes",
        "description": "Configures scene parameters: scene name, color, scene tempo BPM trigger, and time signature trigger.",
        "params": "scene_index (int), name (str), color (int), tempo (float), tempo_enabled (bool), time_signature_numerator (int), time_signature_denominator (int)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_scene_set_properties", Arguments={"scene_index": 0, "name": "Intro 124 BPM", "tempo": 124.0, "tempo_enabled": True})'
    },
    {
        "name": "live12_clip_fire",
        "chapter": 2,
        "category": "Session & Scenes",
        "description": "Fires a specific clip slot on a track in Session View.",
        "params": "track_index (int), slot_index (int)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_clip_fire", Arguments={"track_index": 0, "slot_index": 0})'
    },
    {
        "name": "live12_clip_stop",
        "chapter": 2,
        "category": "Session & Scenes",
        "description": "Stops playback on a specific track or clip slot.",
        "params": "track_index (int)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_clip_stop", Arguments={"track_index": 0})'
    },

    # Chapter 3: Track Hierarchy & Grouping (Domain 3)
    {
        "name": "live12_track_create",
        "chapter": 3,
        "category": "Tracks & Routing",
        "description": "Creates a new track in the project: 'midi', 'audio', or 'return'.",
        "params": "type ('midi'|'audio'|'return'), index (int, optional), name (str, optional)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_track_create", Arguments={"type": "midi", "name": "Sub Bass"})'
    },
    {
        "name": "live12_track_delete",
        "chapter": 3,
        "category": "Tracks & Routing",
        "description": "Deletes the track at the specified track index.",
        "params": "track_index (int)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_track_delete", Arguments={"track_index": 2})'
    },
    {
        "name": "live12_track_duplicate",
        "chapter": 3,
        "category": "Tracks & Routing",
        "description": "Duplicates an existing track including all its hosted devices, clips, and automation.",
        "params": "track_index (int)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_track_duplicate", Arguments={"track_index": 0})'
    },
    {
        "name": "live12_track_set_properties",
        "chapter": 3,
        "category": "Tracks & Routing",
        "description": "Sets track name, RGB color, mute state, solo state, and record arming state.",
        "params": "track_index (int), name (str), color (int), mute (bool), solo (bool), arm (bool)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_track_set_properties", Arguments={"track_index": 0, "name": "Kick 909", "solo": True})'
    },
    {
        "name": "live12_track_group",
        "chapter": 3,
        "category": "Tracks & Routing",
        "description": "Groups multiple tracks into a composite Group Track for collective processing.",
        "params": "track_indices (list[int]), group_name (str, optional)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_track_group", Arguments={"track_indices": [0, 1], "group_name": "Drums Bus"})'
    },
    {
        "name": "live12_track_ungroup",
        "chapter": 3,
        "category": "Tracks & Routing",
        "description": "Dissolves a Group Track back into individual top-level tracks.",
        "params": "group_track_index (int)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_track_ungroup", Arguments={"group_track_index": 2})'
    },

    # Chapter 4: Audio Routing & I/O (Domain 4)
    {
        "name": "live12_routing_get",
        "chapter": 4,
        "category": "Tracks & Routing",
        "description": "Inspects current and available input and output audio/MIDI routing types and channels for a track.",
        "params": "track_index (int)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_routing_get", Arguments={"track_index": 0})'
    },
    {
        "name": "live12_routing_set",
        "chapter": 4,
        "category": "Tracks & Routing",
        "description": "Configures input/output routing types, channels, and monitoring states (In, Auto, Off).",
        "params": "track_index (int), input_routing_type (str), input_routing_channel (str), output_routing_type (str), output_routing_channel (str), monitoring_state (int)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_routing_set", Arguments={"track_index": 0, "monitoring_state": 1})'
    },

    # Chapter 5: Take Lanes & Comping (Domain 5)
    {
        "name": "live12_take_lane_create",
        "chapter": 5,
        "category": "Take Lanes & Comping",
        "description": "Creates a new take lane on an arrangement audio or MIDI track for comping multi-take recordings.",
        "params": "track_index (int)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_take_lane_create", Arguments={"track_index": 1})'
    },
    {
        "name": "live12_take_lane_list",
        "chapter": 5,
        "category": "Take Lanes & Comping",
        "description": "Enumerates all take lanes on a track with take indices, names, clip presence, and custom metadata.",
        "params": "track_index (int)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_take_lane_list", Arguments={"track_index": 1})'
    },
    {
        "name": "live12_take_lane_comp_region",
        "chapter": 5,
        "category": "Take Lanes & Comping",
        "description": "Comps a time region from a specified take lane into the track's main arrangement take.",
        "params": "track_index (int), take_lane_index (int), start_time (float), end_time (float)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_take_lane_comp_region", Arguments={"track_index": 1, "take_lane_index": 0, "start_time": 4.0, "end_time": 8.0})'
    },

    # Chapter 6: Audio Clips & Warping (Domain 6)
    {
        "name": "live12_audio_clip_set_warp",
        "chapter": 6,
        "category": "Audio Clips & Warping",
        "description": "Enables/disables warping, sets warp mode (Beats, Tones, Texture, Re-Pitch, Complex, Complex Pro), and sets pitch/gain.",
        "params": "track_index (int), slot_index (int), warping (bool), warp_mode (str), pitch_coarse (int), gain (float)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_audio_clip_set_warp", Arguments={"track_index": 1, "slot_index": 0, "warping": True, "warp_mode": "complex_pro"})'
    },
    {
        "name": "live12_audio_clip_add_warp_marker",
        "chapter": 6,
        "category": "Audio Clips & Warping",
        "description": "Adds a warp marker at a specific beat time mapped to a precise audio sample time.",
        "params": "track_index (int), slot_index (int), beat_time (float), sample_time (float, optional)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_audio_clip_add_warp_marker", Arguments={"track_index": 1, "slot_index": 0, "beat_time": 4.0, "sample_time": 2.15})'
    },
    {
        "name": "live12_clip_set_properties",
        "chapter": 6,
        "category": "Audio Clips & Warping",
        "description": "Configures clip loop parameters: is_looping, loop_start, loop_end, start_marker, end_marker, and name.",
        "params": "track_index (int), slot_index (int), name (str), is_looping (bool), loop_start (float), loop_end (float)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_clip_set_properties", Arguments={"track_index": 0, "slot_index": 0, "is_looping": True, "loop_end": 16.0})'
    },

    # Chapter 7: Live 12 MIDI Note Editing (Domain 7)
    {
        "name": "live12_clip_add_notes",
        "chapter": 7,
        "category": "MIDI & Notes",
        "description": "Injects MIDI notes with Live 12 extended specification: pitch, start_time, duration, velocity, probability, and velocity deviation.",
        "params": "track_index (int), slot_index (int), notes (list of dicts)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_clip_add_notes", Arguments={"track_index": 0, "slot_index": 0, "notes": [{"pitch": 60, "start_time": 0.0, "duration": 0.5, "velocity": 100, "probability": 0.9}]})'
    },
    {
        "name": "live12_clip_get_notes",
        "chapter": 7,
        "category": "MIDI & Notes",
        "description": "Retrieves all MIDI notes in a clip with extended parameters (pitch, velocity, deviation, probability).",
        "params": "track_index (int), slot_index (int), pitch_filter (int, optional), start_time (float, optional)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_clip_get_notes", Arguments={"track_index": 0, "slot_index": 0})'
    },
    {
        "name": "live12_clip_modify_notes",
        "chapter": 7,
        "category": "MIDI & Notes",
        "description": "Modifies existing MIDI notes in a clip by note ID or coordinate match.",
        "params": "track_index (int), slot_index (int), modifications (list of dicts)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_clip_modify_notes", Arguments={"track_index": 0, "slot_index": 0, "modifications": [{"note_id": 1, "velocity": 115, "probability": 1.0}]})'
    },
    {
        "name": "live12_clip_remove_notes",
        "chapter": 7,
        "category": "MIDI & Notes",
        "description": "Removes MIDI notes from a clip by note IDs or by beat/pitch window (Clip.remove_notes_by_id or remove_notes_extended).",
        "params": "track_index (int), slot_index (int), note_ids (list[int]), start_time (float), time_span (float), from_pitch (int), pitch_span (int)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_clip_remove_notes", Arguments={"track_index": 0, "slot_index": 0, "start_time": 0.0, "time_span": 4.0})'
    },

    # Chapter 8: Live 12 MIDI Transformations & Quantization (Domain 8)
    {
        "name": "live12_clip_quantize",
        "chapter": 8,
        "category": "MIDI & Notes",
        "description": "Quantizes MIDI notes in a clip to grid increment (1/4, 1/8, 1/16, 1/32) with strength amount.",
        "params": "track_index (int), slot_index (int), grid (str: '1/16'), amount (float: 0.0-1.0)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_clip_quantize", Arguments={"track_index": 0, "slot_index": 0, "grid": "1/16", "amount": 1.0})'
    },
    {
        "name": "live12_clip_transform_midi",
        "chapter": 8,
        "category": "MIDI & Notes",
        "description": "Applies algorithmic MIDI transformations: humanize timing/velocity, velocity ramps, Euclidean rhythms, arpeggiator, or scale quantization.",
        "params": "track_index (int), slot_index (int), transformation ('humanize'|'velocity_ramp'|'euclidean'|'fit_to_scale'), params (dict)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_clip_transform_midi", Arguments={"track_index": 0, "slot_index": 0, "transformation": "euclidean", "params": {"steps": 16, "pulses": 5, "pitch": 60}})'
    },

    # Chapter 9: Clip Envelopes & Automation (Domain 9)
    {
        "name": "live12_clip_envelope_control",
        "chapter": 9,
        "category": "Envelopes & Automation",
        "description": "Inspects and manipulates parameter automation envelopes in a clip (set breakpoint step, inspect, clear envelope, re-enable automation).",
        "params": "track_index (int), slot_index (int), action ('inspect'|'set_step'|'clear'|'clear_all'|'re_enable'), device_index (int), parameter_identifier (str|int), time (float), value (float)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_clip_envelope_control", Arguments={"track_index": 0, "slot_index": 0, "action": "set_step", "device_index": 0, "parameter_identifier": "Filter Freq", "time": 0.0, "value": 450.0})'
    },

    # Chapter 10: Groove Pool & Swing (Domain 10)
    {
        "name": "live12_groove_pool_control",
        "chapter": 10,
        "category": "Groove & Swing",
        "description": "Manages the Ableton Live 12 Groove Pool: queries pool grooves, adjusts global song groove amount, assigns groove templates to clips, or inspects clip groove status.",
        "params": "action ('list_pool'|'set_song_amount'|'assign_clip'|'clear_clip'|'get_clip_groove'), groove_index (int), amount (float), track_index (int), slot_index (int)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_groove_pool_control", Arguments={"action": "set_song_amount", "amount": 0.65})'
    },

    # Chapter 11: Live 12 Scales & Microtonal Tuning (Domain 11)
    {
        "name": "live12_song_set_scale",
        "chapter": 11,
        "category": "Scales & Tuning",
        "description": "Sets global song musical scale (Major, Minor, Dorian, Phrygian, etc.) and root note (0=C, 1=C#, 2=D, ...).",
        "params": "scale_name (str), root_note (int: 0-11)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_song_set_scale", Arguments={"scale_name": "Minor", "root_note": 0})'
    },
    {
        "name": "live12_song_set_tuning_system",
        "chapter": 11,
        "category": "Scales & Tuning",
        "description": "Loads an .ascl microtonal tuning file into Live 12 with custom reference pitches and pitch cent offsets.",
        "params": "tuning_file_path (str), reference_pitch (float, optional)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_song_set_tuning_system", Arguments={"tuning_file_path": "/Library/Tuning/Werckmeister_III.ascl"})'
    },
    {
        "name": "live12_song_get_state",
        "chapter": 11,
        "category": "Scales & Tuning",
        "description": "Retrieves comprehensive project telemetry: tempo, signature, scale, tuning system, track count, and transport position.",
        "params": "None",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_song_get_state", Arguments={})'
    },

    # Chapter 12: Browser, Categories, Preview & Hotswap (Domain 12)
    {
        "name": "live12_browser_search",
        "chapter": 12,
        "category": "Browser & Library",
        "description": "Searches the Live 12 Browser library by query text and category filter (sounds, drums, instruments, effects).",
        "params": "query (str), category (str, optional), max_results (int, optional)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_browser_search", Arguments={"query": "Drift", "category": "instruments"})'
    },
    {
        "name": "live12_browser_load_item",
        "chapter": 12,
        "category": "Browser & Library",
        "description": "Instantiates a browser item onto a track or drum pad by canonical URI.",
        "params": "track_index (int), uri (str), drum_pad_index (int, optional)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_browser_load_item", Arguments={"track_index": 0, "uri": "query:devices#Drift"})'
    },
    {
        "name": "live12_browser_preview",
        "chapter": 12,
        "category": "Browser & Library",
        "description": "Controls audio auditioning and hotswap monitoring in the Live 12 Browser (preview item, stop preview, hotswap status).",
        "params": "action ('preview'|'stop'|'hotswap_status'), browser_item_uri (str, optional)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_browser_preview", Arguments={"action": "preview", "browser_item_uri": "live:sample:kick01"})'
    },

    # Chapter 13: Device Chains & Racks (Domain 13)
    {
        "name": "live12_device_list",
        "chapter": 13,
        "category": "Devices & Processing",
        "description": "Enumerates all devices on a track with device index, name, class_name, type, and bypass state.",
        "params": "track_index (int)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_device_list", Arguments={"track_index": 0})'
    },
    {
        "name": "live12_device_get_parameters",
        "chapter": 13,
        "category": "Devices & Processing",
        "description": "Queries all parameters of a device including parameter name, min/max bounds, default value, and current value.",
        "params": "track_index (int), device_index (int)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_device_get_parameters", Arguments={"track_index": 0, "device_index": 0})'
    },
    {
        "name": "live12_device_set_parameter",
        "chapter": 13,
        "category": "Devices & Processing",
        "description": "Sets a device parameter value by parameter name or index.",
        "params": "track_index (int), device_index (int), parameter_name (str, optional), parameter_index (int, optional), value (float)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_device_set_parameter", Arguments={"track_index": 0, "device_index": 0, "parameter_name": "Filter Freq", "value": 450.0})'
    },
    {
        "name": "live12_device_toggle",
        "chapter": 13,
        "category": "Devices & Processing",
        "description": "Toggles a device on/off (bypass state).",
        "params": "track_index (int), device_index (int), is_active (bool, optional)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_device_toggle", Arguments={"track_index": 0, "device_index": 0, "is_active": True})'
    },
    {
        "name": "live12_rack_macro_control",
        "chapter": 13,
        "category": "Devices & Processing",
        "description": "Sets a macro knob value (macros 0 through 15) on an Instrument, Audio Effect, or MIDI Effect Rack.",
        "params": "track_index (int), device_index (int), macro_index (int: 0-15), value (float: 0.0-1.0)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_rack_macro_control", Arguments={"track_index": 0, "device_index": 0, "macro_index": 0, "value": 0.75})'
    },
    {
        "name": "live12_rack_variation_control",
        "chapter": 13,
        "category": "Devices & Processing",
        "description": "Stores, recalls, or deletes macro variation snapshot presets on a Rack device.",
        "params": "track_index (int), device_index (int), action ('store'|'recall'|'delete'), variation_index (int, optional)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_rack_variation_control", Arguments={"track_index": 0, "device_index": 0, "action": "store"})'
    },
    {
        "name": "live12_rack_macro_config",
        "chapter": 13,
        "category": "Devices & Processing",
        "description": "Configures macro knobs on an Ableton Live 12 Rack device: visible macro count (1-16), add/remove macro, randomize.",
        "params": "track_index (int), device_index (int), action ('get_config'|'set_count'|'add_macro'|'remove_macro'|'randomize'), count (int)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_rack_macro_config", Arguments={"track_index": 0, "device_index": 0, "action": "set_count", "count": 8})'
    },

    # Chapter 14: Drum Racks & Drum Pads (Domain 14)
    {
        "name": "live12_drum_pad_control",
        "chapter": 14,
        "category": "Devices & Processing",
        "description": "Controls Drum Rack pads: inspect pad status, mute/solo pad, clone pad to another note (copy_pad), or delete chains.",
        "params": "track_index (int), device_index (int), action ('inspect_pads'|'mute_pad'|'solo_pad'|'copy_pad'|'delete_chains'), pad_note (int), target_note (int), state (bool)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_drum_pad_control", Arguments={"track_index": 0, "device_index": 0, "action": "copy_pad", "pad_note": 36, "target_note": 37})'
    },

    # Chapter 15: Simpler & Slicing (Domain 15)
    {
        "name": "live12_simpler_control",
        "chapter": 15,
        "category": "Devices & Processing",
        "description": "Controls Simpler instrument playback mode (Classic, One-Shot, Slicing), converts slices to Drum Rack, and swaps samples.",
        "params": "track_index (int), device_index (int), action ('set_playback_mode'|'slice_to_drum_rack'|'replace_sample'), mode (str), sample_uri (str)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_simpler_control", Arguments={"track_index": 0, "device_index": 0, "action": "slice_to_drum_rack"})'
    },

    # Chapter 16: Wavetable & Modulation Matrix (Domain 16)
    {
        "name": "live12_wavetable_modulation_matrix",
        "chapter": 16,
        "category": "Devices & Processing",
        "description": "Configures Wavetable's 2D modulation matrix: sets source-target depth, queries matrix connections, or clears matrix.",
        "params": "track_index (int), device_index (int), action ('set'|'get'|'clear'), source (str), target (str), amount (float: -1.0 to 1.0)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_wavetable_modulation_matrix", Arguments={"track_index": 2, "device_index": 0, "action": "set", "source": "LFO 1", "target": "Filter 1 Freq", "amount": 0.45})'
    },

    # Chapter 17: Flagship Live 12 Devices (Domain 17)
    {
        "name": "live12_meld_control",
        "chapter": 17,
        "category": "Devices & Processing",
        "description": "Controls Meld bi-timbral macro synth: oscillator engines A & B algorithms, resonator scale quantization, and dual filters.",
        "params": "track_index (int), device_index (int), engine_a_preset (str), engine_b_preset (str), filter_a_freq (float), filter_b_freq (float)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_meld_control", Arguments={"track_index": 3, "device_index": 0, "engine_a_preset": "Swarm", "engine_b_preset": "Formant"})'
    },
    {
        "name": "live12_roar_control",
        "chapter": 17,
        "category": "Devices & Processing",
        "description": "Controls Roar multi-stage saturator: routing mode (Single, Serial, Parallel, Multi-band, Mid/Side, Feedback), drive, tone, feedback.",
        "params": "track_index (int), device_index (int), routing_mode (str), drive (float), tone (float), feedback (float)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_roar_control", Arguments={"track_index": 1, "device_index": 1, "routing_mode": "mid_side", "drive": 12.0})'
    },
    {
        "name": "live12_drift_control",
        "chapter": 17,
        "category": "Devices & Processing",
        "description": "Controls Drift subtractive synthesizer: oscillator drift amount, filter character, stereo spread, and envelope mode.",
        "params": "track_index (int), device_index (int), drift_amount (float), filter_type (str), stereo_spread (float)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_drift_control", Arguments={"track_index": 1, "device_index": 0, "drift_amount": 0.35, "filter_type": "24dB"})'
    },
    {
        "name": "live12_cc_control",
        "chapter": 17,
        "category": "Devices & Processing",
        "description": "Controls the Live 12 CC Control MIDI device: maps continuous controllers (CC), sets output CC values, and configures automation targets.",
        "params": "track_index (int), device_index (int), action ('set_cc'|'get_mappings'), cc_number (int: 0-127), value (int: 0-127), channel (int: 1-16)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_cc_control", Arguments={"track_index": 0, "device_index": 1, "action": "set_cc", "cc_number": 74, "value": 90})'
    },

    # Chapter 18: Mixer, Sends & Crossfader (Domain 18)
    {
        "name": "live12_mixer_set",
        "chapter": 18,
        "category": "Mixer & System",
        "description": "Configures channel strip mixer parameters: track volume, stereo pan, auxiliary send levels, and A/B crossfader assignment.",
        "params": "track_index (int), volume (float: 0.0-1.0), panning (float: -1.0 to 1.0), send_index (int, optional), send_amount (float, optional), crossfader_assign (int, optional)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_mixer_set", Arguments={"track_index": 0, "volume": 0.85, "panning": 0.0})'
    },

    # Chapter 19: Ableton Link, Follower & Capture MIDI (Domain 19)
    {
        "name": "live12_tempo_sync_control",
        "chapter": 19,
        "category": "Arrangement & Transport",
        "description": "Controls synchronization features: toggles Ableton Link, enables tempo follower, executes tap tempo, or nudges song tempo.",
        "params": "action ('get_status'|'set_link'|'set_follower'|'tap_tempo'|'nudge_up'|'nudge_down'), enabled (bool, optional)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_tempo_sync_control", Arguments={"action": "set_link", "enabled": True})'
    },
    {
        "name": "live12_song_capture_midi",
        "chapter": 19,
        "category": "MIDI & Notes",
        "description": "Retrospectively captures recently played MIDI events into a new clip on the armed track.",
        "params": "track_index (int, optional)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_song_capture_midi", Arguments={"track_index": 0})'
    },
    {
        "name": "live12_transport_set_metronome",
        "chapter": 19,
        "category": "Arrangement & Transport",
        "description": "Enables/disables metronome click and configures count-in duration (None, 1 Bar, 2 Bars, 4 Bars).",
        "params": "metronome (bool), count_in (int, optional)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_transport_set_metronome", Arguments={"metronome": True, "count_in": 1})'
    },

    # Chapter 20: Views, Dialogs, Undo/Redo & LOM Introspection (Domain 20)
    {
        "name": "live12_view_switch",
        "chapter": 20,
        "category": "Mixer & System",
        "description": "Switches the active application view: 'session', 'arrangement', 'detail_clip', or 'detail_device'.",
        "params": "view_name ('session'|'arrangement'|'detail_clip'|'detail_device')",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_view_switch", Arguments={"view_name": "arrangement"})'
    },
    {
        "name": "live12_view_select",
        "chapter": 20,
        "category": "Mixer & System",
        "description": "Selects a track, scene, clip slot, or device in Live's GUI navigation.",
        "params": "track_index (int, optional), scene_index (int, optional), slot_index (int, optional), device_index (int, optional)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_view_select", Arguments={"track_index": 0, "device_index": 0})'
    },
    {
        "name": "live12_dialog_inspect",
        "chapter": 20,
        "category": "Mixer & System",
        "description": "Inspects active macOS modal dialogs and alert sheets in Ableton Live 12 via AppleScript System Events.",
        "params": "None",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_dialog_inspect", Arguments={})'
    },
    {
        "name": "live12_dialog_press",
        "chapter": 20,
        "category": "Mixer & System",
        "description": "Presses a native dialog button ('Save', 'Don\\'t Save', 'Cancel', 'OK') in an active Live sheet.",
        "params": "button_title (str)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_dialog_press", Arguments={"button_title": "Save"})'
    },
    {
        "name": "live12_undo_redo",
        "chapter": 20,
        "category": "Mixer & System",
        "description": "Executes Undo and Redo operations in Ableton Live 12 (Song.undo, Song.redo), inspects history status, or demarcates undo transactions.",
        "params": "action ('undo'|'redo'|'status'|'begin_step'|'end_step')",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_undo_redo", Arguments={"action": "undo"})'
    },
    {
        "name": "live12_os_save_set",
        "chapter": 20,
        "category": "Mixer & System",
        "description": "Saves the currently open Live set (.als) to disk via native Cocoa save menu and dialog automation.",
        "params": "destination_path (str, optional)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_os_save_set", Arguments={"destination_path": "/Users/juancruz/Music/LiveSets/Track01.als"})'
    },
    {
        "name": "live12_os_open_set",
        "chapter": 20,
        "category": "Mixer & System",
        "description": "Opens an existing Ableton Live set (.als) from disk.",
        "params": "als_path (str)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_os_open_set", Arguments={"als_path": "/Users/juancruz/Music/LiveSets/Track01.als"})'
    },
    {
        "name": "live12_os_export_audio",
        "chapter": 20,
        "category": "Mixer & System",
        "description": "Triggers File > Export Audio/Video and renders master bus to WAV via Cocoa NSSavePanel dialog automation.",
        "params": "output_path (str), sample_rate (int, optional), bit_depth (int, optional)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_os_export_audio", Arguments={"output_path": "/Users/juancruz/Music/Bounces/Track01_Master.wav"})'
    },
    {
        "name": "live12_lom_inspect",
        "chapter": 20,
        "category": "LOM Reflection",
        "description": "Introspects properties, methods, and child types of any Live Object Model path (e.g. 'live_set.tracks.0.devices.0').",
        "params": "lom_path (str)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_lom_inspect", Arguments={"lom_path": "live_set.tracks.0.devices.0"})'
    },
    {
        "name": "live12_lom_get",
        "chapter": 20,
        "category": "LOM Reflection",
        "description": "Dynamically retrieves the value of any property along a Live Object Model path.",
        "params": "lom_path (str), property_name (str)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_lom_get", Arguments={"lom_path": "live_set.master_track", "property_name": "volume"})'
    },
    {
        "name": "live12_lom_set",
        "chapter": 20,
        "category": "LOM Reflection",
        "description": "Dynamically sets the value of any writable property along a Live Object Model path.",
        "params": "lom_path (str), property_name (str), value (any)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_lom_set", Arguments={"lom_path": "live_set", "property_name": "tempo", "value": 126.0})'
    },
    {
        "name": "live12_lom_call",
        "chapter": 20,
        "category": "LOM Reflection",
        "description": "Dynamically invokes an arbitrary Boost.Python method on a Live Object Model path.",
        "params": "lom_path (str), method_name (str), args (list, optional), kwargs (dict, optional)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_lom_call", Arguments={"lom_path": "live_set", "method_name": "tap_tempo"})'
    },
    {
        "name": "live12_clip_create",
        "chapter": 2,
        "category": "Session & Scenes",
        "description": "Creates a new blank MIDI clip on a track clip slot with specified length in beats.",
        "params": "track_index (int), slot_index (int), length (float: default 4.0)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_clip_create", Arguments={"track_index": 0, "slot_index": 0, "length": 16.0})'
    },
    {
        "name": "live12_clip_delete",
        "chapter": 2,
        "category": "Session & Scenes",
        "description": "Deletes the clip located in the designated track and slot index.",
        "params": "track_index (int), slot_index (int)",
        "agy_call": 'call_mcp_tool(ServerName="ableton-live12", ToolName="live12_clip_delete", Arguments={"track_index": 0, "slot_index": 0})'
    }
]

def load_lom_surface():
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "lom_surface_12_4_6.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    classes = data.get("lom_classes", {})
    results = []
    for name in sorted(classes.keys()):
        info = classes[name]
        results.append({
            "name": name,
            "cplusplus_handle": info.get("cplusplus_handle", "N/A"),
            "canonical_parent": info.get("canonical_parent", "N/A"),
            "docstring": info.get("docstring", ""),
            "description": info.get("description", ""),
            "properties": list(info.get("properties", {}).keys()),
            "methods": list(info.get("methods", {}).keys())
        })
    return results

def main():
    print(f"Loaded {len(TOOLS_CATALOG)} MCP tools")
    lom_classes = load_lom_surface()
    print(f"Loaded {len(lom_classes)} LOM classes")

    # Serialize JSON for embedded client-side search
    tools_json = json.dumps(TOOLS_CATALOG)
    lom_json = json.dumps(lom_classes)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Ableton Live 12 MCP | Autonomous Studio Engineering</title>
  <meta name="description" content="Production-grade Model Context Protocol (MCP) server and in-process Control Surface bridge for Ableton Live 12.4.6 Suite. Complete 20-chapter manual coverage, 75 tools, 49 LOM classes.">
  <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220%22%20%220%22%20%22100%22%20%22100%22><text y=%22.9em%22 font-size=%2290%22>🎛️</text></svg>">
  <style>
    :root {{
      --bg: #07080a;
      --surface: #0d0f14;
      --surface-2: #161922;
      --surface-3: #1f2330;
      --border: rgba(255, 255, 255, 0.08);
      --border-accent: rgba(255, 190, 0, 0.35);
      --amber: #ffbe00;
      --amber-glow: rgba(255, 190, 0, 0.15);
      --cyan: #00d2ff;
      --cyan-glow: rgba(0, 210, 255, 0.15);
      --emerald: #00ff88;
      --emerald-glow: rgba(0, 255, 136, 0.15);
      --magenta: #ff007f;
      --text-main: #f0f2f5;
      --text-muted: #8a92a0;
      --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
    }}

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}

    body {{
      background-color: var(--bg);
      color: var(--text-main);
      font-family: var(--font-sans);
      line-height: 1.6;
      overflow-x: hidden;
      -webkit-font-smoothing: antialiased;
    }}

    /* Header Nav */
    header.site-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 1.25rem 2.5rem;
      background: rgba(7, 8, 10, 0.85);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--border);
      position: sticky;
      top: 0;
      z-index: 100;
    }}

    .logo-container {{
      display: flex;
      align-items: center;
      gap: 1rem;
    }}

    .logo-badge {{
      background: var(--amber);
      color: #000;
      font-family: var(--font-mono);
      font-weight: 800;
      font-size: 0.8rem;
      padding: 0.3rem 0.6rem;
      border-radius: 4px;
      letter-spacing: 0.05em;
    }}

    .logo-title {{
      font-size: 1.25rem;
      font-weight: 700;
      letter-spacing: -0.02em;
      color: var(--text-main);
    }}

    nav.site-nav {{
      display: flex;
      gap: 1.5rem;
      align-items: center;
    }}

    nav.site-nav a {{
      color: var(--text-muted);
      text-decoration: none;
      font-size: 0.9rem;
      font-weight: 500;
      transition: color 0.2s ease;
    }}

    nav.site-nav a:hover {{
      color: var(--amber);
    }}

    .nav-btn {{
      background: var(--surface-2);
      border: 1px solid var(--border);
      color: var(--text-main);
      padding: 0.5rem 1rem;
      border-radius: 6px;
      font-family: var(--font-mono);
      font-size: 0.85rem;
      text-decoration: none;
      transition: all 0.2s ease;
    }}

    .nav-btn:hover {{
      border-color: var(--amber);
      box-shadow: 0 0 12px var(--amber-glow);
    }}

    /* Main Container */
    main {{
      max-width: 1320px;
      margin: 0 auto;
      padding: 3rem 2rem;
    }}

    /* Hero Section */
    section.hero {{
      text-align: center;
      padding: 4rem 1rem 3rem;
      position: relative;
    }}

    .badge-strip {{
      display: flex;
      justify-content: center;
      gap: 0.75rem;
      flex-wrap: wrap;
      margin-bottom: 1.75rem;
    }}

    .badge {{
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      font-family: var(--font-mono);
      font-size: 0.75rem;
      font-weight: 600;
      padding: 0.35rem 0.75rem;
      border-radius: 999px;
      background: var(--surface-2);
      border: 1px solid var(--border);
      color: var(--text-muted);
    }}

    .badge.gold {{
      border-color: rgba(255, 190, 0, 0.4);
      color: var(--amber);
    }}

    .badge.cyan {{
      border-color: rgba(0, 210, 255, 0.4);
      color: var(--cyan);
    }}

    .badge.emerald {{
      border-color: rgba(0, 255, 136, 0.4);
      color: var(--emerald);
    }}

    h1.hero-title {{
      font-size: clamp(2.5rem, 5vw, 4.25rem);
      font-weight: 800;
      line-height: 1.1;
      letter-spacing: -0.03em;
      margin-bottom: 1.5rem;
      background: linear-gradient(180deg, #ffffff 30%, #8a92a0 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }}

    p.hero-subtitle {{
      font-size: 1.25rem;
      color: var(--text-muted);
      max-width: 820px;
      margin: 0 auto 2.5rem;
      line-height: 1.5;
    }}

    .hero-actions {{
      display: flex;
      justify-content: center;
      gap: 1rem;
      flex-wrap: wrap;
    }}

    .btn {{
      padding: 0.85rem 1.75rem;
      border-radius: 8px;
      font-size: 0.95rem;
      font-weight: 600;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      cursor: pointer;
      transition: all 0.2s ease;
    }}

    .btn-primary {{
      background: var(--amber);
      color: #000;
      border: 1px solid var(--amber);
    }}

    .btn-primary:hover {{
      background: #e5ab00;
      box-shadow: 0 0 20px rgba(255, 190, 0, 0.4);
    }}

    .btn-secondary {{
      background: var(--surface-2);
      color: var(--text-main);
      border: 1px solid var(--border);
    }}

    .btn-secondary:hover {{
      border-color: var(--border-accent);
      background: var(--surface-3);
    }}

    /* Showcase Studio Player Grid */
    section.studio-showcase {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 2.5rem;
      margin: 3.5rem 0;
      position: relative;
      overflow: hidden;
    }}

    .studio-showcase::before {{
      content: "";
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 2px;
      background: linear-gradient(90deg, var(--amber), var(--cyan), var(--emerald), var(--magenta));
    }}

    .section-header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      margin-bottom: 2rem;
      flex-wrap: wrap;
      gap: 1rem;
    }}

    .section-title {{
      font-size: 1.75rem;
      font-weight: 700;
      letter-spacing: -0.02em;
    }}

    .section-desc {{
      color: var(--text-muted);
      font-size: 0.95rem;
    }}

    .media-grid {{
      display: grid;
      grid-template-columns: 1.2fr 0.8fr;
      gap: 2rem;
    }}

    @media (max-width: 960px) {{
      .media-grid {{
        grid-template-columns: 1fr;
      }}
    }}

    .video-card {{
      background: var(--surface-2);
      border: 1px solid var(--border);
      border-radius: 12px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }}

    .video-container video {{
      width: 100%;
      height: auto;
      display: block;
      background: #000;
    }}

    .video-meta {{
      padding: 1.25rem;
      border-top: 1px solid var(--border);
    }}

    .video-title {{
      font-weight: 600;
      font-size: 1.05rem;
      margin-bottom: 0.4rem;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }}

    .video-desc {{
      font-size: 0.85rem;
      color: var(--text-muted);
    }}

    .audio-card {{
      background: var(--surface-2);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 1.5rem;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }}

    .track-meta-box {{
      margin-bottom: 1.5rem;
    }}

    .track-genre {{
      font-family: var(--font-mono);
      font-size: 0.75rem;
      color: var(--cyan);
      text-transform: uppercase;
      letter-spacing: 0.1em;
      margin-bottom: 0.35rem;
    }}

    .track-name {{
      font-size: 1.35rem;
      font-weight: 700;
      margin-bottom: 0.35rem;
    }}

    .track-spec {{
      font-family: var(--font-mono);
      font-size: 0.8rem;
      color: var(--text-muted);
    }}

    .custom-audio-player {{
      background: var(--surface-3);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 1rem;
    }}

    .audio-controls-row {{
      display: flex;
      align-items: center;
      gap: 1rem;
      margin-bottom: 0.75rem;
    }}

    .play-btn {{
      background: var(--emerald);
      color: #000;
      border: none;
      width: 44px;
      height: 44px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      font-size: 1.1rem;
      transition: transform 0.1s ease;
      flex-shrink: 0;
    }}

    .play-btn:hover {{
      transform: scale(1.05);
      box-shadow: 0 0 16px var(--emerald-glow);
    }}

    .track-time {{
      font-family: var(--font-mono);
      font-size: 0.85rem;
      color: var(--text-muted);
    }}

    .seek-slider {{
      width: 100%;
      accent-color: var(--emerald);
      cursor: pointer;
    }}

    .audio-features-list {{
      margin-top: 1.5rem;
      list-style: none;
      font-size: 0.85rem;
      color: var(--text-muted);
    }}

    .audio-features-list li {{
      padding: 0.35rem 0;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }}

    .audio-features-list li::before {{
      content: "✓";
      color: var(--emerald);
      font-weight: bold;
    }}

    /* Architecture Visualizer Section */
    section.arch-section {{
      margin: 4rem 0;
    }}

    .arch-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 2rem;
      margin-top: 2rem;
    }}

    @media (max-width: 960px) {{
      .arch-grid {{
        grid-template-columns: 1fr;
      }}
    }}

    .arch-box {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 1.5rem;
      overflow: hidden;
    }}

    .arch-box img, .arch-box object {{
      width: 100%;
      height: auto;
      border-radius: 8px;
      display: block;
    }}

    .arch-box-title {{
      font-size: 1.1rem;
      font-weight: 600;
      margin-bottom: 0.75rem;
      color: var(--amber);
    }}

    .arch-box-desc {{
      font-size: 0.85rem;
      color: var(--text-muted);
      margin-top: 0.75rem;
    }}

    /* Comparison Table */
    section.comparison {{
      margin: 4rem 0;
    }}

    .table-container {{
      overflow-x: auto;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      margin-top: 1.5rem;
    }}

    table.compare-table {{
      width: 100%;
      border-collapse: collapse;
      text-align: left;
      font-size: 0.9rem;
    }}

    table.compare-table th, table.compare-table td {{
      padding: 1rem 1.25rem;
      border-bottom: 1px solid var(--border);
    }}

    table.compare-table th {{
      background: var(--surface-2);
      font-family: var(--font-mono);
      font-size: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
    }}

    table.compare-table tr:hover td {{
      background: rgba(255, 255, 255, 0.02);
    }}

    .td-highlight {{
      color: var(--amber);
      font-weight: 600;
    }}

    .tag-yes {{
      color: var(--emerald);
      font-weight: 600;
    }}

    .tag-no {{
      color: #ff5555;
    }}

    /* Interactive Tool Explorer */
    section.tool-explorer {{
      margin: 4rem 0;
    }}

    .filter-controls {{
      margin-bottom: 2rem;
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }}

    .search-input-box {{
      position: relative;
    }}

    .search-input-box input {{
      width: 100%;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 1rem 1.25rem 1rem 3rem;
      color: var(--text-main);
      font-size: 1rem;
      outline: none;
      transition: border-color 0.2s ease;
    }}

    .search-input-box input:focus {{
      border-color: var(--amber);
      box-shadow: 0 0 16px var(--amber-glow);
    }}

    .search-icon {{
      position: absolute;
      left: 1.25rem;
      top: 50%;
      transform: translateY(-50%);
      color: var(--text-muted);
    }}

    .category-pills {{
      display: flex;
      gap: 0.5rem;
      flex-wrap: wrap;
    }}

    .pill-btn {{
      background: var(--surface-2);
      border: 1px solid var(--border);
      color: var(--text-muted);
      padding: 0.4rem 0.85rem;
      border-radius: 6px;
      font-size: 0.8rem;
      cursor: pointer;
      transition: all 0.15s ease;
    }}

    .pill-btn:hover, .pill-btn.active {{
      background: var(--amber);
      color: #000;
      border-color: var(--amber);
      font-weight: 600;
    }}

    .tools-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
      gap: 1.5rem;
    }}

    .tool-card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 1.5rem;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      transition: transform 0.15s ease, border-color 0.15s ease;
    }}

    .tool-card:hover {{
      transform: translateY(-2px);
      border-color: rgba(255, 190, 0, 0.4);
    }}

    .tool-card-header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 0.75rem;
    }}

    .tool-name {{
      font-family: var(--font-mono);
      font-size: 1rem;
      font-weight: 700;
      color: var(--amber);
    }}

    .tool-ch-badge {{
      background: var(--surface-3);
      border: 1px solid var(--border);
      padding: 0.2rem 0.5rem;
      border-radius: 4px;
      font-family: var(--font-mono);
      font-size: 0.7rem;
      color: var(--cyan);
    }}

    .tool-desc {{
      font-size: 0.88rem;
      color: var(--text-muted);
      margin-bottom: 1rem;
      line-height: 1.45;
    }}

    .tool-params {{
      font-family: var(--font-mono);
      font-size: 0.75rem;
      background: var(--surface-2);
      padding: 0.6rem 0.8rem;
      border-radius: 6px;
      color: #bbb;
      margin-bottom: 1rem;
      word-break: break-all;
    }}

    .tool-actions {{
      display: flex;
      justify-content: flex-end;
    }}

    .copy-btn {{
      background: var(--surface-2);
      border: 1px solid var(--border);
      color: var(--text-main);
      padding: 0.35rem 0.75rem;
      border-radius: 4px;
      font-family: var(--font-mono);
      font-size: 0.75rem;
      cursor: pointer;
      transition: all 0.15s ease;
    }}

    .copy-btn:hover {{
      background: var(--amber);
      color: #000;
      border-color: var(--amber);
    }}

    /* LOM Explorer */
    section.lom-explorer {{
      margin: 4rem 0;
    }}

    .lom-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
      gap: 1.25rem;
      margin-top: 1.5rem;
    }}

    .lom-card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 1.25rem;
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }}

    .lom-name {{
      font-family: var(--font-mono);
      font-size: 0.95rem;
      font-weight: 700;
      color: var(--emerald);
    }}

    .lom-handle {{
      font-family: var(--font-mono);
      font-size: 0.75rem;
      color: var(--text-muted);
    }}

    .lom-desc {{
      font-size: 0.85rem;
      color: #aaa;
      line-height: 1.4;
    }}

    .lom-metrics {{
      display: flex;
      gap: 1rem;
      font-family: var(--font-mono);
      font-size: 0.75rem;
      color: var(--cyan);
      margin-top: 0.5rem;
    }}

    /* Antigravity Prompt Recipes */
    section.recipes {{
      margin: 4rem 0;
    }}

    .recipe-card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 1.75rem;
      margin-bottom: 1.5rem;
    }}

    .recipe-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1rem;
    }}

    .recipe-title {{
      font-size: 1.15rem;
      font-weight: 700;
      color: var(--text-main);
    }}

    .recipe-genre {{
      font-family: var(--font-mono);
      font-size: 0.75rem;
      color: var(--amber);
      text-transform: uppercase;
    }}

    .recipe-prompt {{
      background: var(--surface-2);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 1rem;
      font-family: var(--font-mono);
      font-size: 0.85rem;
      color: #ddd;
      white-space: pre-wrap;
      word-break: break-word;
      position: relative;
    }}

    /* Footer */
    footer.site-footer {{
      background: var(--surface);
      border-top: 1px solid var(--border);
      padding: 4rem 2rem 2rem;
      margin-top: 6rem;
      color: var(--text-muted);
      font-size: 0.85rem;
    }}

    .footer-inner {{
      max-width: 1320px;
      margin: 0 auto;
      display: grid;
      grid-template-columns: 2fr 1fr 1fr;
      gap: 3rem;
      margin-bottom: 3rem;
    }}

    @media (max-width: 768px) {{
      .footer-inner {{
        grid-template-columns: 1fr;
        gap: 2rem;
      }}
    }}

    .footer-col h4 {{
      color: var(--text-main);
      font-size: 1rem;
      margin-bottom: 1rem;
      font-weight: 600;
    }}

    .footer-col ul {{
      list-style: none;
    }}

    .footer-col ul li {{
      margin-bottom: 0.5rem;
    }}

    .footer-col ul li a {{
      color: var(--text-muted);
      text-decoration: none;
      transition: color 0.15s ease;
    }}

    .footer-col ul li a:hover {{
      color: var(--amber);
    }}

    .disclaimer-box {{
      background: var(--surface-2);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 1.25rem;
      line-height: 1.5;
      margin-top: 1.5rem;
      font-size: 0.78rem;
    }}

    .copyright-row {{
      text-align: center;
      padding-top: 2rem;
      border-top: 1px solid var(--border);
      font-family: var(--font-mono);
      font-size: 0.78rem;
    }}
  </style>
</head>
<body>

  <!-- Site Header -->
  <header class="site-header">
    <div class="logo-container">
      <span class="logo-badge">LIVE 12 MCP</span>
      <span class="logo-title">Ableton Live 12 MCP</span>
    </div>
    <nav class="site-nav">
      <a href="#showcase">Studio Showcase</a>
      <a href="#architecture">Architecture</a>
      <a href="#comparison">Benchmark</a>
      <a href="#tools">75 Tools</a>
      <a href="#lom">49 LOM Classes</a>
      <a href="#recipes">Prompt Recipes</a>
      <a href="https://github.com/juancruzmunozalbelo/ableton-live12-mcp" target="_blank" class="nav-btn">GitHub</a>
    </nav>
  </header>

  <main>
    <!-- Hero Section -->
    <section class="hero">
      <div class="badge-strip">
        <span class="badge gold">★ Dual License: MIT + Apache-2.0</span>
        <span class="badge cyan">⚡ Ableton Live 12.4.6 Suite</span>
        <span class="badge emerald">🎛️ 75 Dedicated MCP Tools</span>
        <span class="badge">🔬 49 Reverse-Engineered LOM Classes</span>
        <span class="badge">⚖️ Clean-Room DMCA §1201(f) & EU 2009/24/EC</span>
      </div>
      <h1 class="hero-title">Autonomous Electronic Music Engineering for Ableton Live 12</h1>
      <p class="hero-subtitle">
        A production-grade Model Context Protocol (MCP) server and in-process Control Surface bridge.
        Enables autonomous AI agents like Antigravity (<code>agy</code>) to arrange, compose, sculpt synthesis parameters,
        comp take lanes, and bounce stems with zero human intervention.
      </p>
      <div class="hero-actions">
        <a href="#tools" class="btn btn-primary">Explore 75 MCP Tools</a>
        <a href="#showcase" class="btn btn-secondary">Play Studio Demo</a>
        <a href="https://github.com/juancruzmunozalbelo/ableton-live12-mcp" target="_blank" class="btn btn-secondary">Source Code</a>
      </div>
    </section>

    <!-- Studio Showcase Section -->
    <section class="studio-showcase" id="showcase">
      <div class="section-header">
        <div>
          <h2 class="section-title">Studio Audio & Visual Showcase</h2>
          <p class="section-desc">8-bar 124 BPM Melodic Techno composition generated completely through the Live 12 MCP tool pipeline.</p>
        </div>
        <span class="badge emerald">● Broadcast Ready (-17.1 LUFS / -1.0 dBFS Peak)</span>
      </div>

      <div class="media-grid">
        <!-- Video Card -->
        <div class="video-card">
          <div class="video-container">
            <video controls poster="assets/demo_overview.gif" preload="metadata">
              <source src="assets/demo_overview.mp4" type="video/mp4">
              Your browser does not support the video tag.
            </video>
          </div>
          <div class="video-meta">
            <div class="video-title">
              <span>Dynamic Waveform & Spectral Telemetry</span>
            </div>
            <div class="video-desc">
              1280x720 25fps video synchronized to synthesized 124 BPM showcase audio using ffmpeg showwaves and logarithmic showspectrum visualizers.
            </div>
          </div>
        </div>

        <!-- Audio Player Card -->
        <div class="audio-card">
          <div class="track-meta-box">
            <div class="track-genre">Melodic Techno / Deep Tech</div>
            <h3 class="track-name">Deep Pulse (Live 12 Showcase)</h3>
            <div class="track-spec">124.0 BPM · 4/4 · C Minor · 8 Bars (15.48s) · 44.1 kHz 16-bit Stereo</div>
          </div>

          <div class="custom-audio-player">
            <audio id="showcaseAudio" src="assets/showcase_demo.wav" preload="auto"></audio>
            <div class="audio-controls-row">
              <button class="play-btn" id="playBtn" onclick="togglePlay()">▶</button>
              <div style="flex-grow: 1;">
                <input type="range" class="seek-slider" id="seekSlider" value="0" min="0" max="100" onchange="seekAudio()">
              </div>
              <span class="track-time" id="trackTime">0:00 / 0:15</span>
            </div>
          </div>

          <ul class="audio-features-list">
            <li><strong>Kick & Percussion:</strong> 909 pitch-sweep sub kick + 16th hats with probability deviation.</li>
            <li><strong>Acid Sub Bass:</strong> Live 12 Drift synth analog drift + 24dB resonant lowpass filtering.</li>
            <li><strong>Melodic Arp:</strong> Wavetable dual morphing saw/square with stereo ping-pong feedback.</li>
            <li><strong>Atmospheric Pad:</strong> Bi-timbral Meld macro synth with Swarm & Formant engines.</li>
          </ul>
        </div>
      </div>
    </section>

    <!-- Architecture Visualizer Section -->
    <section class="arch-section" id="architecture">
      <div class="section-header">
        <div>
          <h2 class="section-title">System Architecture</h2>
          <p class="section-desc">Zero-heap main-thread synchronization bridging AI agents into Ableton's C++ core.</p>
        </div>
      </div>

      <div class="arch-grid">
        <div class="arch-box">
          <h3 class="arch-box-title">3-Layer High-Performance Topology</h3>
          <img src="assets/architecture.svg" alt="Ableton Live 12 MCP 3-Layer Architecture Diagram">
          <p class="arch-box-desc">
            Layer 1: Autonomous Agent (<code>agy</code>) ↔ Layer 2: Stdio JSON-RPC 2.0 MCP Server + Hybrid OS Bridge ↔ Layer 3: In-Process Control Surface with 5ms <code>Live.Base.Timer</code> queue & C++ Boost.Python reflection.
          </p>
        </div>

        <div class="arch-box">
          <h3 class="arch-box-title">Live Terminal Recording (agy Session)</h3>
          <img src="assets/terminal_demo.svg" alt="Animated Terminal Demo of agy executing Live 12 MCP Tools">
          <p class="arch-box-desc">
            Autonomous CLI session demonstrating inspection, track creation, browser device loading, note injection with probability, and transport playback.
          </p>
        </div>
      </div>
    </section>

    <!-- Benchmark Comparison Table -->
    <section class="comparison" id="comparison">
      <div class="section-header">
        <div>
          <h2 class="section-title">Architectural Benchmark</h2>
          <p class="section-desc">Comparing Ableton Live 12 MCP against legacy open-source integrations.</p>
        </div>
      </div>

      <div class="table-container">
        <table class="compare-table">
          <thead>
            <tr>
              <th>Feature Dimension</th>
              <th>Ableton Live 12 MCP (This Project)</th>
              <th>ahujasid/ableton-mcp</th>
              <th>AbletonOSC (Generic OSC)</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><strong>Manual Chapter Coverage</strong></td>
              <td class="td-highlight">100% (All 20 Chapters)</td>
              <td>~20% (Partial Session View)</td>
              <td>~35% (Basic Transport & Clips)</td>
            </tr>
            <tr>
              <td><strong>Dedicated MCP Tools</strong></td>
              <td class="td-highlight">75 Dedicated Tools</td>
              <td>15 Basic Tools</td>
              <td>0 (Requires OSC Bridge)</td>
            </tr>
            <tr>
              <td><strong>Live 12 Extended Notes</strong></td>
              <td class="tag-yes">✓ Full (Probability, Velocity Deviation)</td>
              <td class="tag-no">✗ Pitch & Velocity Only</td>
              <td class="tag-no">✗ Pitch & Velocity Only</td>
            </tr>
            <tr>
              <td><strong>Live 12 Flagship Devices</strong></td>
              <td class="tag-yes">✓ Meld, Roar, Drift, CC Control</td>
              <td class="tag-no">✗ None</td>
              <td class="tag-no">✗ Generic Params Only</td>
            </tr>
            <tr>
              <td><strong>Take Lanes & Comping</strong></td>
              <td class="tag-yes">✓ Dedicated TakeLane & Comp Tools</td>
              <td class="tag-no">✗ Not Supported</td>
              <td class="tag-no">✗ Not Supported</td>
            </tr>
            <tr>
              <td><strong>Microtonal Tuning (.ascl)</strong></td>
              <td class="tag-yes">✓ TuningSystem Loading & Cent Offsets</td>
              <td class="tag-no">✗ Not Supported</td>
              <td class="tag-no">✗ Not Supported</td>
            </tr>
            <tr>
              <td><strong>Thread Safety Mechanism</strong></td>
              <td class="td-highlight">5ms Live.Base.Timer Main-Thread Queue</td>
              <td>Un-synchronized Remote Socket</td>
              <td>Asynchronous UDP Thread (Prone to Race Conditions)</td>
            </tr>
            <tr>
              <td><strong>Pointer Validation</strong></td>
              <td class="tag-yes">✓ Strict liveobj_valid Verification</td>
              <td class="tag-no">✗ Unchecked Access</td>
              <td class="tag-no">✗ Occasional C++ Segfaults</td>
            </tr>
            <tr>
              <td><strong>OS & Dialog Automation</strong></td>
              <td class="tag-yes">✓ Cocoa NSSavePanel & AppleScript Export</td>
              <td class="tag-no">✗ None</td>
              <td class="tag-no">✗ None</td>
            </tr>
            <tr>
              <td><strong>Dynamic LOM Introspection</strong></td>
              <td class="tag-yes">✓ Full 49-Class Reflection Engine</td>
              <td class="tag-no">✗ Hardcoded Static Properties</td>
              <td class="tag-no">✗ Hardcoded OSC Addresses</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- Interactive Tool Explorer -->
    <section class="tool-explorer" id="tools">
      <div class="section-header">
        <div>
          <h2 class="section-title">Interactive Tool Explorer (75 MCP Tools)</h2>
          <p class="section-desc">Search, filter by chapter, inspect schemas, and copy Antigravity CLI call recipes.</p>
        </div>
        <span class="badge gold" id="toolCountBadge">75 Tools Loaded</span>
      </div>

      <div class="filter-controls">
        <div class="search-input-box">
          <span class="search-icon">🔍</span>
          <input type="text" id="toolSearchInput" placeholder="Search by tool name, parameter, or chapter description (e.g. 'drift', 'warp', 'probability', 'comping')..." oninput="filterTools()">
        </div>
        <div class="category-pills" id="categoryPills">
          <button class="pill-btn active" onclick="setCategory('All')">All (75)</button>
          <button class="pill-btn" onclick="setCategory('Arrangement & Transport')">Arrangement & Transport</button>
          <button class="pill-btn" onclick="setCategory('Session & Scenes')">Session & Scenes</button>
          <button class="pill-btn" onclick="setCategory('Tracks & Routing')">Tracks & Routing</button>
          <button class="pill-btn" onclick="setCategory('Take Lanes & Comping')">Take Lanes & Comping</button>
          <button class="pill-btn" onclick="setCategory('Audio Clips & Warping')">Audio Clips & Warping</button>
          <button class="pill-btn" onclick="setCategory('MIDI & Notes')">MIDI & Notes</button>
          <button class="pill-btn" onclick="setCategory('Envelopes & Automation')">Envelopes & Automation</button>
          <button class="pill-btn" onclick="setCategory('Groove & Swing')">Groove & Swing</button>
          <button class="pill-btn" onclick="setCategory('Scales & Tuning')">Scales & Tuning</button>
          <button class="pill-btn" onclick="setCategory('Browser & Library')">Browser & Library</button>
          <button class="pill-btn" onclick="setCategory('Devices & Processing')">Devices & Processing</button>
          <button class="pill-btn" onclick="setCategory('Mixer & System')">Mixer & System</button>
          <button class="pill-btn" onclick="setCategory('LOM Reflection')">LOM Reflection</button>
        </div>
      </div>

      <div class="tools-grid" id="toolsGrid">
        <!-- Rendered via JavaScript -->
      </div>
    </section>

    <!-- Interactive LOM Class Explorer -->
    <section class="lom-explorer" id="lom">
      <div class="section-header">
        <div>
          <h2 class="section-title">LOM Surface Explorer (49 Classes)</h2>
          <p class="section-desc">Reverse-engineered from Ableton Live 12.4.6 Suite binary (Boost.Python introspection).</p>
        </div>
        <span class="badge cyan">49 Classes · 184 Types · 2,701 Tokens</span>
      </div>

      <div class="search-input-box" style="margin-bottom: 1.5rem;">
        <span class="search-icon">🔍</span>
        <input type="text" id="lomSearchInput" placeholder="Filter LOM classes (e.g. 'Song', 'TakeLane', 'DriftDevice', 'WavetableDevice')..." oninput="filterLom()">
      </div>

      <div class="lom-grid" id="lomGrid">
        <!-- Rendered via JavaScript -->
      </div>
    </section>

    <!-- Antigravity Prompt Recipes -->
    <section class="recipes" id="recipes">
      <div class="section-header">
        <div>
          <h2 class="section-title">Antigravity (agy) Prompt Recipes</h2>
          <p class="section-desc">Copy-paste prompts for autonomous multi-track production in Antigravity.</p>
        </div>
      </div>

      <!-- Recipe 1 -->
      <div class="recipe-card">
        <div class="recipe-header">
          <div class="recipe-title">1. Generate 124 BPM Melodic Techno Track with Acid Bass & 909 Drums</div>
          <span class="recipe-genre">Techno Production</span>
        </div>
        <div class="recipe-prompt">
agy "Set project tempo to 124 BPM in C Minor using live12_song_set_scale. Create a drum track with a 909 Core Kit, inject 4-on-the-floor kick with 16th hats having velocity deviation. Add a second track with Drift, set resonance to 0.45, drift to 0.35, and write a 16-step syncopated acid sub bassline. Then add a third track with Wavetable, route LFO 1 to Filter 1 Freq with depth 0.45, and start transport playback."
        </div>
      </div>

      <!-- Recipe 2 -->
      <div class="recipe-card">
        <div class="recipe-header">
          <div class="recipe-title">2. Comp Arrangement Take Lanes & Apply Werckmeister III Microtonal Tuning</div>
          <span class="recipe-genre">Advanced Audio Workflows</span>
        </div>
        <div class="recipe-prompt">
agy "Inspect track 1 take lanes with live12_take_lane_list. Comp bars 16-24 from take lane 0, and bars 24-32 from take lane 1 using live12_take_lane_comp_region. Load the Werckmeister III .ascl tuning system using live12_song_set_tuning_system. Inspect resulting arrangement and return telemetry."
        </div>
      </div>

      <!-- Recipe 3 -->
      <div class="recipe-card">
        <div class="recipe-header">
          <div class="recipe-title">3. Slice Vocal Sample to Drum Rack & Chain Roar Mid/Side Distortion</div>
          <span class="recipe-genre">Sound Design & Slicing</span>
        </div>
        <div class="recipe-prompt">
agy "Load vocal hook into Simpler on track 2, switch playback mode to Slicing, and call live12_simpler_control to slice to Drum Rack. On the new Drum Rack track, load Roar, configure routing_mode to 'mid_side' with drive 14.0dB and tone 0.65. Save project set to /Users/juancruz/Music/LiveSets/VocalChop_Roar.als."
        </div>
      </div>
    </section>
  </main>

  <!-- Site Footer -->
  <footer class="site-footer">
    <div class="footer-inner">
      <div class="footer-col">
        <h4>Ableton Live 12 MCP</h4>
        <p>Production-grade Model Context Protocol server and in-process Control Surface bridge engineered specifically for Ableton Live 12.4.6 Suite on macOS.</p>
        <div class="disclaimer-box">
          <strong>Clean-Room & Trademark Fair Use Notice:</strong><br>
          Ableton Live 12 MCP is an independent open-source clean-room engineering project created in accordance with 17 U.S.C. §1201(f) and EU Directive 2009/24/EC Art. 6 for software interoperability. "Ableton", "Ableton Live", "Live Suite", "Push", "Meld", "Roar", and "Drift" are registered trademarks of Ableton AG. This project is not affiliated with, sponsored, or endorsed by Ableton AG or Cycling '74.
        </div>
      </div>
      <div class="footer-col">
        <h4>Project Governance</h4>
        <ul>
          <li><a href="https://github.com/juancruzmunozalbelo/ableton-live12-mcp/blob/main/LICENSE-MIT" target="_blank">MIT License</a></li>
          <li><a href="https://github.com/juancruzmunozalbelo/ableton-live12-mcp/blob/main/LICENSE-APACHE" target="_blank">Apache License 2.0</a></li>
          <li><a href="https://github.com/juancruzmunozalbelo/ableton-live12-mcp/blob/main/NOTICE.md" target="_blank">Legal Notice & Clean-Room Statement</a></li>
          <li><a href="https://github.com/juancruzmunozalbelo/ableton-live12-mcp/blob/main/SECURITY.md" target="_blank">Security Policy & Threat Model</a></li>
          <li><a href="https://github.com/juancruzmunozalbelo/ableton-live12-mcp/blob/main/CONTRIBUTING.md" target="_blank">Contributing Guidelines</a></li>
          <li><a href="https://github.com/juancruzmunozalbelo/ableton-live12-mcp/blob/main/GLOSSARY.md" target="_blank">Domain Glossary</a></li>
        </ul>
      </div>
      <div class="footer-col">
        <h4>Documentation & Specs</h4>
        <ul>
          <li><a href="https://github.com/juancruzmunozalbelo/ableton-live12-mcp/blob/main/docs/ABLETON_12_MANUAL_COVERAGE.md" target="_blank">Manual 20-Chapter Matrix</a></li>
          <li><a href="https://github.com/juancruzmunozalbelo/ableton-live12-mcp/blob/main/docs/LOM_REFERENCE.md" target="_blank">LOM Reference Guide</a></li>
          <li><a href="https://github.com/juancruzmunozalbelo/ableton-live12-mcp/blob/main/docs/lom_surface_12_4_6.json" target="_blank">Machine LOM Surface JSON</a></li>
          <li><a href="https://github.com/juancruzmunozalbelo/ableton-live12-mcp/blob/main/CHANGELOG.md" target="_blank">Changelog (Keep a Changelog v1.0.0)</a></li>
        </ul>
      </div>
    </div>
    <div class="copyright-row">
      Copyright &copy; 2026 Juan Cruz Muñoz Albelo and Ableton Live 12 MCP Contributors. Dual-licensed under MIT and Apache-2.0.
    </div>
  </footer>

  <!-- Embedded Client-Side Script -->
  <script>
    const TOOLS = {tools_json};
    const LOM = {lom_json};
    let activeCategory = 'All';

    // Audio Player Implementation
    const audio = document.getElementById('showcaseAudio');
    const playBtn = document.getElementById('playBtn');
    const seekSlider = document.getElementById('seekSlider');
    const trackTime = document.getElementById('trackTime');

    function togglePlay() {{
      if (audio.paused) {{
        audio.play();
        playBtn.textContent = '⏸';
      }} else {{
        audio.pause();
        playBtn.textContent = '▶';
      }}
    }}

    audio.addEventListener('timeupdate', () => {{
      if (!isNaN(audio.duration)) {{
        const progress = (audio.currentTime / audio.duration) * 100;
        seekSlider.value = progress;
        const curM = Math.floor(audio.currentTime / 60);
        const curS = Math.floor(audio.currentTime % 60).toString().padStart(2, '0');
        const durM = Math.floor(audio.duration / 60);
        const durS = Math.floor(audio.duration % 60).toString().padStart(2, '0');
        trackTime.textContent = `${{curM}}:${{curS}} / ${{durM}}:${{durS}}`;
      }}
    }});

    audio.addEventListener('ended', () => {{
      playBtn.textContent = '▶';
      seekSlider.value = 0;
    }});

    function seekAudio() {{
      if (!isNaN(audio.duration)) {{
        audio.currentTime = (seekSlider.value / 100) * audio.duration;
      }}
    }}

    // Tool Explorer Filter & Render
    function renderTools(list) {{
      const grid = document.getElementById('toolsGrid');
      grid.innerHTML = '';
      document.getElementById('toolCountBadge').textContent = `${{list.length}} Tools Displayed`;

      list.forEach(t => {{
        const card = document.createElement('div');
        card.className = 'tool-card';
        card.innerHTML = `
          <div>
            <div class="tool-card-header">
              <span class="tool-name">${{t.name}}</span>
              <span class="tool-ch-badge">Ch ${{t.chapter}}</span>
            </div>
            <p class="tool-desc">${{t.description}}</p>
            <div class="tool-params"><strong>Params:</strong> ${{t.params}}</div>
          </div>
          <div class="tool-actions">
            <button class="copy-btn" onclick="copySnippet('${{escapeJs(t.agy_call)}}', this)">Copy agy Call</button>
          </div>
        `;
        grid.appendChild(card);
      }});
    }}

    function filterTools() {{
      const query = document.getElementById('toolSearchInput').value.toLowerCase().trim();
      const filtered = TOOLS.filter(t => {{
        const matchesCategory = (activeCategory === 'All' || t.category === activeCategory);
        const matchesQuery = !query || 
          t.name.toLowerCase().includes(query) ||
          t.description.toLowerCase().includes(query) ||
          t.params.toLowerCase().includes(query) ||
          `ch ${{t.chapter}}`.includes(query);
        return matchesCategory && matchesQuery;
      }});
      renderTools(filtered);
    }}

    function setCategory(cat) {{
      activeCategory = cat;
      const buttons = document.querySelectorAll('.pill-btn');
      buttons.forEach(b => {{
        if (b.textContent.startsWith(cat)) {{
          b.classList.add('active');
        }} else {{
          b.classList.remove('active');
        }}
      }});
      filterTools();
    }}

    // LOM Explorer Filter & Render
    function renderLom(list) {{
      const grid = document.getElementById('lomGrid');
      grid.innerHTML = '';
      list.forEach(c => {{
        const card = document.createElement('div');
        card.className = 'lom-card';
        card.innerHTML = `
          <div class="lom-name">${{c.name}}</div>
          <div class="lom-handle">Handle: ${{c.cplusplus_handle}} · Parent: ${{c.canonical_parent}}</div>
          <div class="lom-desc">${{c.description || c.docstring || 'Live Object Model interface'}}</div>
          <div class="lom-metrics">
            <span>${{c.properties.length}} Properties</span>
            <span>·</span>
            <span>${{c.methods.length}} Methods</span>
          </div>
        `;
        grid.appendChild(card);
      }});
    }}

    function filterLom() {{
      const query = document.getElementById('lomSearchInput').value.toLowerCase().trim();
      const filtered = LOM.filter(c => {{
        return !query ||
          c.name.toLowerCase().includes(query) ||
          c.description.toLowerCase().includes(query) ||
          c.cplusplus_handle.toLowerCase().includes(query);
      }});
      renderLom(filtered);
    }}

    function escapeJs(str) {{
      return str.replace(/'/g, "\\\\'");
    }}

    function copySnippet(snippet, btn) {{
      navigator.clipboard.writeText(snippet).then(() => {{
        const oldText = btn.textContent;
        btn.textContent = 'Copied!';
        btn.style.background = 'var(--emerald)';
        btn.style.color = '#000';
        setTimeout(() => {{
          btn.textContent = oldText;
          btn.style.background = '';
          btn.style.color = '';
        }}, 1800);
      }}).catch(err => {{
        console.error('Failed to copy', err);
      }});
    }}

    // Initial Render
    renderTools(TOOLS);
    renderLom(LOM);
  </script>
</body>
</html>
"""

    out_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Successfully generated {out_path} ({len(html_content.encode('utf-8'))} bytes)")

if __name__ == "__main__":
    main()
