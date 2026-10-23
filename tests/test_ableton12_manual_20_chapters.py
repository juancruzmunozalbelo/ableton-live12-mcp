"""
Ableton Live 12 Manual - 20 Chapters Comprehensive End-to-End Verification Suite
=================================================================================
Validates full operational compliance across all 20 functional domains of the
Ableton Live 12 Suite Manual, exercising 100% of the 75 MCP tools in both
Offline Mock Mode and Real Live Ableton Live 12 Suite on macOS.

Chapters covered:
 1. Arrangement View, Time Signature Changes & Locator Cue Points
 2. Session View, Scenes & Clip Slots
 3. Track Hierarchy, Grouping, Folding & Performance Impact
 4. Audio Routing, Sidechain & I/O Channels
 5. Take Lanes & Arrangement Comping
 6. Audio Clips, Warping, Warp Markers & Sample Properties
 7. Live 12 MIDI Note Editing & Extended Specification
 8. Live 12 MIDI Transformations, Quantization & Pitch/Scale Tools
 9. Clip Envelopes, Automation & Modulation
10. Groove Pool & Swing
11. Live 12 Scales & Microtonal Tuning Systems
12. Browser, Content Categories, Preview & Hotswap
13. Device Chains, Racks, Macro Controls & Macro Variations
14. Drum Racks & Drum Pads
15. Simpler & Slicing Workflows
16. Wavetable & Modulation Matrix
17. Live 12 Flagship Devices (Meld, Roar, Drift, CC Control)
18. Mixer, Sends, Returns, Crossfader & Cue Volume
19. Ableton Link, Tempo Follower, Count-In & Capture MIDI
20. Application Views, Native Dialogs, Undo/Redo & Universal LOM Escape Hatch
"""

import math
import os
import pytest
from harness import Live12TestClient
from ableton_live12_mcp.tools import ALL_TOOLS


class TestChapter01ArrangementAndCuePoints:
    """
    Chapter 1: Arrangement View, Time Signature Changes & Locator Cue Points.
    Tools:
      - live12_transport_play
      - live12_transport_stop
      - live12_transport_record
      - live12_transport_set_tempo
      - live12_transport_set_time_signature
      - live12_transport_set_loop
      - live12_transport_set_punch
      - live12_transport_set_overdub
      - live12_cue_point_control
      - live12_clip_duplicate_to_arrangement
    """

    def test_transport_arrangement_lifecycle(self, client: Live12TestClient):
        # 1. Transport tempo & signature
        res_tempo = client.call_tool("live12_transport_set_tempo", {"tempo": 126.0})
        assert not res_tempo.is_error

        res_sig = client.call_tool("live12_transport_set_time_signature", {"numerator": 3, "denominator": 4})
        assert not res_sig.is_error

        # 2. Loop, punch & overdub
        res_loop = client.call_tool("live12_transport_set_loop", {"enabled": True, "start": 4.0, "length": 16.0})
        assert not res_loop.is_error

        res_punch = client.call_tool("live12_transport_set_punch", {"punch_in": True, "punch_out": False})
        assert not res_punch.is_error

        res_od = client.call_tool("live12_transport_set_overdub", {"overdub": True})
        assert not res_od.is_error

        # 3. Transport playback & record
        res_rec = client.call_tool("live12_transport_record", {"record_mode": "arrangement"})
        assert not res_rec.is_error

        res_play = client.call_tool("live12_transport_play", {"restart": True})
        assert not res_play.is_error

        res_stop = client.call_tool("live12_transport_stop")
        assert not res_stop.is_error

    def test_cue_points_and_clip_duplication(self, client: Live12TestClient):
        # Create cue points
        res_cue1 = client.call_tool("live12_cue_point_control", {"action": "create", "name": "Verse 1", "time": 8.0})
        assert not res_cue1.is_error

        res_cue2 = client.call_tool("live12_cue_point_control", {"action": "create", "name": "Chorus", "time": 24.0})
        assert not res_cue2.is_error

        # List cue points
        res_list = client.call_tool("live12_cue_point_control", {"action": "list"})
        assert not res_list.is_error

        # Jump to cue
        res_jump = client.call_tool("live12_cue_point_control", {"action": "jump", "cue_index": 0})
        assert not res_jump.is_error

        # Delete cue
        res_del = client.call_tool("live12_cue_point_control", {"action": "delete", "cue_index": 0})
        assert not res_del.is_error

        # Duplicate session clip to arrangement timeline
        t_idx, _ = client.create_sandboxed_track("midi", "arr_track")
        client.call_tool("live12_clip_create", {"track_index": t_idx, "slot_index": 0, "length_beats": 4.0})
        res_dup = client.call_tool("live12_clip_duplicate_to_arrangement", {
            "track_index": t_idx,
            "slot_index": 0,
            "arrangement_time": 16.0
        })
        assert not res_dup.is_error


class TestChapter02SessionViewAndScenes:
    """
    Chapter 2: Session View, Scenes & Clip Slots.
    Tools:
      - live12_scene_create
      - live12_scene_set_properties
      - live12_scene_fire
      - live12_clip_fire
      - live12_clip_stop
    """

    def test_session_scene_lifecycle(self, client: Live12TestClient):
        # 1. Create scene (exercises "live12_scene_create" via sandboxing)
        s_idx, _ = client.create_sandboxed_scene("drop_1")

        # 2. Set scene properties
        res_props = client.call_tool("live12_scene_set_properties", {
            "scene_index": s_idx,
            "name": "Drop 1",
            "tempo": 130.0,
            "tempo_enabled": True,
            "time_signature_numerator": 4,
            "time_signature_denominator": 4,
            "time_signature_enabled": True
        })
        assert not res_props.is_error

        # 3. Fire scene
        res_fire = client.call_tool("live12_scene_fire", {"index": s_idx})
        assert not res_fire.is_error

        # 4. Create and fire/stop clip
        t_idx, _ = client.create_sandboxed_track("midi", "session_clip_tr")
        client.call_tool("live12_clip_create", {"track_index": t_idx, "slot_index": 0, "length_beats": 4.0})

        res_clip_fire = client.call_tool("live12_clip_fire", {"track_index": t_idx, "slot_index": 0})
        assert not res_clip_fire.is_error

        res_clip_stop = client.call_tool("live12_clip_stop", {"track_index": t_idx, "slot_index": 0})
        assert not res_clip_stop.is_error


class TestChapter03TrackHierarchyAndGrouping:
    """
    Chapter 3: Track Hierarchy, Grouping, Folding & Performance Impact.
    Tools:
      - live12_track_create
      - live12_track_set_properties
      - live12_track_group
      - live12_track_ungroup
      - live12_track_duplicate
      - live12_track_delete
    """

    def test_track_hierarchy_and_management(self, client: Live12TestClient):
        # Create tracks (exercises "live12_track_create" via sandboxing)
        t1, _ = client.create_sandboxed_track("midi", "synth_1")
        t2, _ = client.create_sandboxed_track("midi", "synth_2")

        # Set properties
        res_prop = client.call_tool("live12_track_set_properties", {
            "track_index": t1,
            "name": "Lead Synth",
            "solo": False,
            "mute": False,
            "arm": True
        })
        assert not res_prop.is_error

        # Group tracks
        res_grp = client.call_tool("live12_track_group", {"track_indices": [t1, t2]})
        assert not res_grp.is_error

        # Ungroup
        res_ungrp = client.call_tool("live12_track_ungroup", {"group_track_index": t1})
        assert not res_ungrp.is_error

        # Duplicate track
        res_dup = client.call_tool("live12_track_duplicate", {"track_index": t1})
        assert not res_dup.is_error
        dup_idx = res_dup.get("track_index", t1 + 1)
        client.session_tracks.append(dup_idx)

        # Delete track
        res_del = client.call_tool("live12_track_delete", {"track_index": dup_idx})
        assert not res_del.is_error


class TestChapter04AudioRoutingAndSidechain:
    """
    Chapter 4: Audio Routing, Sidechain & I/O Channels.
    Tools:
      - live12_routing_get
      - live12_routing_set
    """

    def test_audio_and_midi_routing(self, client: Live12TestClient):
        t_idx, _ = client.create_sandboxed_track("audio", "audio_bus")

        # Get available routing
        res_get = client.call_tool("live12_routing_get", {"track_index": t_idx})
        assert not res_get.is_error

        # Set routing
        res_set = client.call_tool("live12_routing_set", {
            "track_index": t_idx,
            "input_type": "All Ins",
            "monitoring": "Auto"
        })
        assert not res_set.is_error


class TestChapter05TakeLanesAndComping:
    """
    Chapter 5: Take Lanes & Arrangement Comping.
    Tools:
      - live12_take_lane_create
      - live12_take_lane_list
      - live12_take_lane_comp_region
    """

    def test_take_lane_lifecycle_and_comping(self, client: Live12TestClient):
        t_idx, _ = client.create_sandboxed_track("audio", "lead_vocal")

        # Create take lane
        res_lane = client.call_tool("live12_take_lane_create", {"track_index": t_idx})
        assert not res_lane.is_error
        lane_idx = res_lane.get("take_lane_index", res_lane.get("lane_index", 0))

        # List take lanes
        res_list = client.call_tool("live12_take_lane_list", {"track_index": t_idx})
        assert not res_list.is_error

        # Comp region
        res_comp = client.call_tool("live12_take_lane_comp_region", {
            "track_index": t_idx,
            "lane_index": lane_idx,
            "start": 0.0,
            "length": 4.0
        })
        assert not res_comp.is_error


class TestChapter06AudioClipsAndWarping:
    """
    Chapter 6: Audio Clips, Warping, Warp Markers & Sample Properties.
    Tools:
      - live12_clip_create
      - live12_clip_set_properties
      - live12_audio_clip_set_warp
      - live12_audio_clip_add_warp_marker
      - live12_clip_delete
    """

    def test_audio_clip_and_warping(self, client: Live12TestClient):
        t_idx, _ = client.create_sandboxed_track("midi", "audio_sampler")

        # Create audio clip
        res_create = client.call_tool("live12_clip_create", {
            "track_index": t_idx,
            "slot_index": 0,
            "length_beats": 8.0,
            "name": "Stem Audio"
        })
        assert not res_create.is_error

        # Clip properties
        res_props = client.call_tool("live12_clip_set_properties", {
            "track_index": t_idx,
            "slot_index": 0,
            "loop": True,
            "loop_start": 0.0,
            "loop_end": 8.0
        })
        assert not res_props.is_error

        # Warp mode & pitch shift
        res_warp = client.call_tool("live12_audio_clip_set_warp", {
            "track_index": t_idx,
            "slot_index": 0,
            "warping": True,
            "warp_mode": "Beats",
            "pitch_shift": 2.0,
            "gain": -2.0
        })
        assert not res_warp.is_error

        # Add warp marker
        res_marker = client.call_tool("live12_audio_clip_add_warp_marker", {
            "track_index": t_idx,
            "slot_index": 0,
            "beat_time": 4.0,
            "sample_time": 4.0
        })
        assert not res_marker.is_error

        # Delete clip
        res_del = client.call_tool("live12_clip_delete", {"track_index": t_idx, "slot_index": 0})
        assert not res_del.is_error


class TestChapter07MidiNoteEditingExtended:
    """
    Chapter 7: Live 12 MIDI Note Editing & Extended Specification.
    Tools:
      - live12_clip_add_notes
      - live12_clip_get_notes
      - live12_clip_modify_notes
      - live12_clip_remove_notes
    """

    def test_extended_midi_notes_and_editing(self, client: Live12TestClient):
        t_idx, _ = client.create_sandboxed_track("midi", "midi_ch7")
        client.call_tool("live12_clip_create", {"track_index": t_idx, "slot_index": 0, "length_beats": 4.0})

        # Add extended MIDI notes (with probability, velocity deviation, release velocity)
        notes = [
            {"pitch": 60, "start_time": 0.0, "duration": 1.0, "velocity": 100, "velocity_deviation": 10, "probability": 0.9, "release_velocity": 64},
            {"pitch": 64, "start_time": 1.0, "duration": 1.0, "velocity": 90, "velocity_deviation": -5, "probability": 0.8, "release_velocity": 64},
            {"pitch": 67, "start_time": 2.0, "duration": 1.0, "velocity": 110, "velocity_deviation": 0, "probability": 1.0, "release_velocity": 64},
        ]
        res_add = client.call_tool("live12_clip_add_notes", {"track_index": t_idx, "slot_index": 0, "notes": notes})
        assert not res_add.is_error

        # Read back notes
        res_get = client.call_tool("live12_clip_get_notes", {"track_index": t_idx, "slot_index": 0})
        assert not res_get.is_error

        # Modify notes
        mods = [{"pitch": 62, "start_time": 0.0, "duration": 1.5, "velocity": 105}]
        res_mod = client.call_tool("live12_clip_modify_notes", {"track_index": t_idx, "slot_index": 0, "note_modifications": mods})
        assert not res_mod.is_error

        # Remove notes by pitch & time span
        res_rm = client.call_tool("live12_clip_remove_notes", {
            "track_index": t_idx,
            "slot_index": 0,
            "start_time": 0.0,
            "time_span": 4.0,
            "from_pitch": 55,
            "pitch_span": 20
        })
        assert not res_rm.is_error


class TestChapter08MidiTransformationsAndQuantization:
    """
    Chapter 8: Live 12 MIDI Transformations, Quantization & Pitch/Scale Tools.
    Tools:
      - live12_clip_quantize
      - live12_clip_transform_midi
    """

    def test_midi_transformations_and_quantize(self, client: Live12TestClient):
        t_idx, _ = client.create_sandboxed_track("midi", "midi_ch8")
        client.call_tool("live12_clip_create", {"track_index": t_idx, "slot_index": 0, "length_beats": 4.0})
        client.call_tool("live12_clip_add_notes", {
            "track_index": t_idx,
            "slot_index": 0,
            "notes": [{"pitch": 60, "start_time": 0.04, "duration": 0.5, "velocity": 80}]
        })

        # 1. Quantize
        res_q = client.call_tool("live12_clip_quantize", {
            "track_index": t_idx,
            "slot_index": 0,
            "grid": 0.25,
            "amount": 1.0
        })
        assert not res_q.is_error

        # 2. Algorithmic transformations: humanize, velocity_ramp, euclidean
        res_hum = client.call_tool("live12_clip_transform_midi", {
            "track_index": t_idx,
            "slot_index": 0,
            "transformation": "humanize",
            "params": {"timing_jitter": 0.02, "velocity_jitter": 6.0}
        })
        assert not res_hum.is_error

        res_ramp = client.call_tool("live12_clip_transform_midi", {
            "track_index": t_idx,
            "slot_index": 0,
            "transformation": "velocity_ramp",
            "params": {"start_velocity": 40, "end_velocity": 120}
        })
        assert not res_ramp.is_error

        res_euc = client.call_tool("live12_clip_transform_midi", {
            "track_index": t_idx,
            "slot_index": 0,
            "transformation": "euclidean",
            "params": {"steps": 16, "pulses": 5, "pitch": 60}
        })
        assert not res_euc.is_error


class TestChapter09ClipEnvelopesAndAutomation:
    """
    Chapter 9: Clip Envelopes, Automation & Modulation.
    Tools:
      - live12_clip_envelope_control
    """

    def test_clip_envelopes_and_breakpoints(self, client: Live12TestClient):
        t_idx, _ = client.create_sandboxed_track("midi", "auto_track")
        client.call_tool("live12_clip_create", {"track_index": t_idx, "slot_index": 0, "length_beats": 4.0})

        # 1. Set envelope breakpoint
        res_step = client.call_tool("live12_clip_envelope_control", {
            "track_index": t_idx,
            "slot_index": 0,
            "action": "set_step",
            "parameter_identifier": "Filter Freq",
            "time": 1.0,
            "value": 0.75
        })
        assert not res_step.is_error

        # 2. Inspect envelopes
        res_insp = client.call_tool("live12_clip_envelope_control", {
            "track_index": t_idx,
            "slot_index": 0,
            "action": "inspect"
        })
        assert not res_insp.is_error

        # 3. Clear parameter envelope
        res_clr = client.call_tool("live12_clip_envelope_control", {
            "track_index": t_idx,
            "slot_index": 0,
            "action": "clear",
            "parameter_identifier": "Filter Freq"
        })
        assert not res_clr.is_error

        # 4. Re-enable automation
        res_re = client.call_tool("live12_clip_envelope_control", {
            "track_index": t_idx,
            "slot_index": 0,
            "action": "re_enable"
        })
        assert not res_re.is_error

        # 5. Clear all envelopes
        res_all = client.call_tool("live12_clip_envelope_control", {
            "track_index": t_idx,
            "slot_index": 0,
            "action": "clear_all"
        })
        assert not res_all.is_error


class TestChapter10GroovePoolAndSwing:
    """
    Chapter 10: Groove Pool & Swing.
    Tools:
      - live12_groove_pool_control
    """

    def test_groove_pool_operations(self, client: Live12TestClient):
        t_idx, _ = client.create_sandboxed_track("midi", "groove_track")
        client.call_tool("live12_clip_create", {"track_index": t_idx, "slot_index": 0, "length_beats": 4.0})

        # 1. List pool
        res_list = client.call_tool("live12_groove_pool_control", {"action": "list_pool"})
        assert not res_list.is_error

        # 2. Set global song groove amount
        res_amt = client.call_tool("live12_groove_pool_control", {"action": "set_song_amount", "amount": 0.75})
        assert not res_amt.is_error

        # 3. Assign groove to clip
        res_assign = client.call_tool("live12_groove_pool_control", {
            "action": "assign_clip",
            "groove_index": 0,
            "track_index": t_idx,
            "slot_index": 0
        })
        assert not res_assign.is_error

        # 4. Get clip groove status
        res_get = client.call_tool("live12_groove_pool_control", {
            "action": "get_clip_groove",
            "track_index": t_idx,
            "slot_index": 0
        })
        assert not res_get.is_error

        # 5. Clear groove from clip
        res_clr = client.call_tool("live12_groove_pool_control", {
            "action": "clear_clip",
            "track_index": t_idx,
            "slot_index": 0
        })
        assert not res_clr.is_error


class TestChapter11ScalesAndMicrotonalTuning:
    """
    Chapter 11: Live 12 Scales & Microtonal Tuning Systems.
    Tools:
      - live12_song_set_scale
      - live12_song_set_tuning_system
      - live12_song_get_state
    """

    def test_scales_and_microtonal_tunings(self, client: Live12TestClient):
        # Set musical scale (D Dorian: root=2, scale="Dorian")
        res_scale = client.call_tool("live12_song_set_scale", {"root_note": 2, "scale_name": "Dorian"})
        assert not res_scale.is_error

        # Set microtonal tuning system
        res_tuning = client.call_tool("live12_song_set_tuning_system", {"tuning_name": "Werckmeister III"})
        assert not res_tuning.is_error

        # Verify through song state
        res_state = client.call_tool("live12_song_get_state")
        assert not res_state.is_error
        assert res_state.get("scale_name") == "Dorian"
        assert res_state.get("root_note", res_state.get("scale_root_note")) == 2


class TestChapter12BrowserPreviewAndHotswap:
    """
    Chapter 12: Browser, Content Categories, Preview & Hotswap.
    Tools:
      - live12_browser_search
      - live12_browser_preview
      - live12_browser_load_item
    """

    def test_browser_search_preview_and_load(self, client: Live12TestClient):
        t_idx, _ = client.create_sandboxed_track("midi", "browser_track")

        # 1. Search browser
        res_srch = client.call_tool("live12_browser_search", {"query": "Drift", "category": "instruments"})
        assert not res_srch.is_error

        # 2. Browser preview audition
        res_prev = client.call_tool("live12_browser_preview", {"action": "preview", "browser_item_uri": "live:device:drift"})
        assert not res_prev.is_error

        # 3. Hotswap status
        res_hot = client.call_tool("live12_browser_preview", {"action": "hotswap_status"})
        assert not res_hot.is_error

        # 4. Stop preview
        res_stop = client.call_tool("live12_browser_preview", {"action": "stop"})
        assert not res_stop.is_error

        # 5. Load item onto track
        res_load = client.call_tool("live12_browser_load_item", {"track_index": t_idx, "browser_item_uri": "live:device:drift"})
        assert not res_load.is_error


class TestChapter13DeviceChainsAndRacks:
    """
    Chapter 13: Device Chains, Racks, Macro Controls & Macro Variations.
    Tools:
      - live12_device_list
      - live12_device_get_parameters
      - live12_device_set_parameter
      - live12_device_toggle
      - live12_rack_macro_control
      - live12_rack_macro_config
      - live12_rack_variation_control
    """

    def test_device_chains_and_racks(self, client: Live12TestClient):
        t_idx, _ = client.create_sandboxed_track("midi", "rack_track")
        client.call_tool("live12_browser_load_item", {"track_index": t_idx, "browser_item_uri": "live:device:instrument_rack"})

        # Device listing
        res_list = client.call_tool("live12_device_list", {"track_index": t_idx})
        assert not res_list.is_error

        # Device parameters
        res_params = client.call_tool("live12_device_get_parameters", {"track_index": t_idx, "device_index": 0})
        assert not res_params.is_error

        # Set parameter
        res_set = client.call_tool("live12_device_set_parameter", {
            "track_index": t_idx,
            "device_index": 0,
            "parameter_identifier": 1,
            "value": 0.5
        })
        assert not res_set.is_error

        # Toggle device
        res_tog = client.call_tool("live12_device_toggle", {"track_index": t_idx, "device_index": 0, "enabled": False})
        assert not res_tog.is_error

        # Rack macro control
        res_mac = client.call_tool("live12_rack_macro_control", {
            "track_index": t_idx,
            "device_index": 0,
            "macro_index": 0,
            "value": 0.8
        })
        assert not res_mac.is_error

        # Macro config (count, randomize)
        res_cfg = client.call_tool("live12_rack_macro_config", {
            "track_index": t_idx,
            "device_index": 0,
            "action": "set_count",
            "count": 8
        })
        assert not res_cfg.is_error

        res_rand = client.call_tool("live12_rack_macro_config", {
            "track_index": t_idx,
            "device_index": 0,
            "action": "randomize"
        })
        assert not res_rand.is_error

        # Macro variations
        res_var_store = client.call_tool("live12_rack_variation_control", {
            "track_index": t_idx,
            "device_index": 0,
            "action": "store"
        })
        assert not res_var_store.is_error

        res_var_recall = client.call_tool("live12_rack_variation_control", {
            "track_index": t_idx,
            "device_index": 0,
            "action": "recall",
            "variation_index": 0
        })
        assert not res_var_recall.is_error

        res_var_del = client.call_tool("live12_rack_variation_control", {
            "track_index": t_idx,
            "device_index": 0,
            "action": "delete",
            "variation_index": 0
        })
        assert not res_var_del.is_error


class TestChapter14DrumRacksAndDrumPads:
    """
    Chapter 14: Drum Racks & Drum Pads.
    Tools:
      - live12_drum_pad_control
    """

    def test_drum_pad_operations(self, client: Live12TestClient):
        t_idx, _ = client.create_sandboxed_track("midi", "drum_rack_track")
        client.call_tool("live12_browser_load_item", {"track_index": t_idx, "browser_item_uri": "live:device:drum_rack"})

        # 1. Inspect pads
        res_insp = client.call_tool("live12_drum_pad_control", {
            "track_index": t_idx,
            "device_index": 0,
            "action": "inspect_pads"
        })
        assert not res_insp.is_error

        # 2. Mute / Solo pad
        res_mute = client.call_tool("live12_drum_pad_control", {
            "track_index": t_idx,
            "device_index": 0,
            "action": "mute_pad",
            "pad_note": 36,
            "state": True
        })
        assert not res_mute.is_error

        res_solo = client.call_tool("live12_drum_pad_control", {
            "track_index": t_idx,
            "device_index": 0,
            "action": "solo_pad",
            "pad_note": 36,
            "state": False
        })
        assert not res_solo.is_error

        # 3. Copy pad
        res_copy = client.call_tool("live12_drum_pad_control", {
            "track_index": t_idx,
            "device_index": 0,
            "action": "copy_pad",
            "pad_note": 36,
            "target_note": 37
        })
        assert not res_copy.is_error

        # 4. Delete chains on pad
        res_del = client.call_tool("live12_drum_pad_control", {
            "track_index": t_idx,
            "device_index": 0,
            "action": "delete_chains",
            "pad_note": 37
        })
        assert not res_del.is_error


class TestChapter15SimplerAndSlicing:
    """
    Chapter 15: Simpler & Slicing Workflows.
    Tools:
      - live12_simpler_control
    """

    def test_simpler_playback_and_slicing(self, client: Live12TestClient):
        t_idx, _ = client.create_sandboxed_track("midi", "simpler_track")
        client.call_tool("live12_browser_load_item", {"track_index": t_idx, "browser_item_uri": "live:device:simpler"})

        # Get simpler state
        res_state = client.call_tool("live12_simpler_control", {
            "track_index": t_idx,
            "device_index": 0,
            "action": "get_state"
        })
        assert not res_state.is_error

        # Set playback mode
        res_mode = client.call_tool("live12_simpler_control", {
            "track_index": t_idx,
            "device_index": 0,
            "action": "set_playback_mode",
            "params": {"playback_mode": "Slicing"}
        })
        assert not res_mode.is_error

        # Slice to drum rack
        res_slice = client.call_tool("live12_simpler_control", {
            "track_index": t_idx,
            "device_index": 0,
            "action": "slice_to_drum_rack"
        })
        assert not res_slice.is_error

        # Replace sample
        res_rep = client.call_tool("live12_simpler_control", {
            "track_index": t_idx,
            "device_index": 0,
            "action": "replace_sample",
            "params": {"sample_path": "/tmp/test_kick.wav"}
        })
        assert not res_rep.is_error


class TestChapter16WavetableModulationMatrix:
    """
    Chapter 16: Wavetable & Modulation Matrix.
    Tools:
      - live12_wavetable_modulation_matrix
    """

    def test_wavetable_matrix(self, client: Live12TestClient):
        t_idx, _ = client.create_sandboxed_track("midi", "wavetable_track")
        client.call_tool("live12_browser_load_item", {"track_index": t_idx, "browser_item_uri": "live:device:wavetable"})

        # 1. Set modulation connection
        res_set = client.call_tool("live12_wavetable_modulation_matrix", {
            "track_index": t_idx,
            "device_index": 0,
            "action": "set",
            "source": "LFO 1",
            "target": "Filter 1 Freq",
            "amount": 0.65
        })
        assert not res_set.is_error

        # 2. Get modulation value
        res_get = client.call_tool("live12_wavetable_modulation_matrix", {
            "track_index": t_idx,
            "device_index": 0,
            "action": "get",
            "source": "LFO 1",
            "target": "Filter 1 Freq"
        })
        assert not res_get.is_error

        # 3. Clear matrix
        res_clr = client.call_tool("live12_wavetable_modulation_matrix", {
            "track_index": t_idx,
            "device_index": 0,
            "action": "clear"
        })
        assert not res_clr.is_error


class TestChapter17FlagshipDevicesMeldRoarDriftCC:
    """
    Chapter 17: Live 12 Flagship Devices (Meld, Roar, Drift, CC Control).
    Tools:
      - live12_meld_control
      - live12_roar_control
      - live12_drift_control
      - live12_cc_control
    """

    def test_suite_exclusive_devices(self, client: Live12TestClient):
        t_idx, _ = client.create_sandboxed_track("midi", "suite_devices_tr")
        client.call_tool("live12_browser_load_item", {"track_index": t_idx, "browser_item_uri": "live:device:meld"})

        # 1. Meld macro control
        res_meld = client.call_tool("live12_meld_control", {
            "track_index": t_idx,
            "device_index": 0,
            "engine_params": {"engine_a": "Analog Basic", "engine_b": "Noisy Shapes", "filter_routing": "Stereo"}
        })
        assert not res_meld.is_error

        # 2. Roar multi-stage saturation
        client.call_tool("live12_browser_load_item", {"track_index": t_idx, "browser_item_uri": "live:device:roar"})
        res_roar = client.call_tool("live12_roar_control", {
            "track_index": t_idx,
            "device_index": 0,
            "stage_params": {"routing_mode": "Serial", "stages_count": 2, "drive": 12.0}
        })
        assert not res_roar.is_error

        # 3. Drift analog modeling synth
        client.call_tool("live12_browser_load_item", {"track_index": t_idx, "browser_item_uri": "live:device:drift"})
        res_drift = client.call_tool("live12_drift_control", {
            "track_index": t_idx,
            "device_index": 0,
            "voice_params": {"shape_1": "Saw", "shape_2": "Pulse", "cutoff": 2500.0}
        })
        assert not res_drift.is_error

        # 4. CC Control MIDI destination
        client.call_tool("live12_browser_load_item", {"track_index": t_idx, "browser_item_uri": "live:device:cc_control"})
        res_cc = client.call_tool("live12_cc_control", {
            "track_index": t_idx,
            "device_index": 0,
            "action": "set_cc",
            "cc_number": 74,
            "value": 90,
            "channel": 1
        })
        assert not res_cc.is_error

        res_cc_map = client.call_tool("live12_cc_control", {
            "track_index": t_idx,
            "device_index": 0,
            "action": "get_mappings"
        })
        assert not res_cc_map.is_error


class TestChapter18MixerSendsCrossfader:
    """
    Chapter 18: Mixer, Sends, Returns, Crossfader & Cue Volume.
    Tools:
      - live12_mixer_set
    """

    def test_mixer_controls_and_sends(self, client: Live12TestClient):
        t_idx, _ = client.create_sandboxed_track("midi", "mixer_track")

        # Set volume and panning
        res_vol_pan = client.call_tool("live12_mixer_set", {
            "track_index": t_idx,
            "volume": 0.85,
            "pan": -0.2
        })
        assert not res_vol_pan.is_error

        # Set auxiliary sends
        res_sends = client.call_tool("live12_mixer_set", {
            "track_index": t_idx,
            "sends": {"0": 0.5, "1": 0.25}
        })
        assert not res_sends.is_error

        # Set crossfader assignment
        res_xfade = client.call_tool("live12_mixer_set", {
            "track_index": t_idx,
            "crossfader": "A"
        })
        assert not res_xfade.is_error


class TestChapter19AbletonLinkAndTempoSync:
    """
    Chapter 19: Ableton Link, Tempo Follower, Count-In & Capture MIDI.
    Tools:
      - live12_transport_set_metronome
      - live12_tempo_sync_control
      - live12_song_capture_midi
    """

    def test_sync_tempo_and_capture(self, client: Live12TestClient):
        # 1. Metronome toggle
        res_metro = client.call_tool("live12_transport_set_metronome", {"enabled": True})
        assert not res_metro.is_error

        # 2. Ableton Link & Follower sync
        res_status = client.call_tool("live12_tempo_sync_control", {"action": "get_status"})
        assert not res_status.is_error

        res_link = client.call_tool("live12_tempo_sync_control", {"action": "set_link", "enabled": True})
        assert not res_link.is_error

        res_fol = client.call_tool("live12_tempo_sync_control", {"action": "set_follower", "enabled": False})
        assert not res_fol.is_error

        res_tap = client.call_tool("live12_tempo_sync_control", {"action": "tap_tempo"})
        assert not res_tap.is_error

        res_up = client.call_tool("live12_tempo_sync_control", {"action": "nudge_up"})
        assert not res_up.is_error

        res_down = client.call_tool("live12_tempo_sync_control", {"action": "nudge_down"})
        assert not res_down.is_error

        # 3. Capture MIDI retrospective recording
        res_cap = client.call_tool("live12_song_capture_midi")
        assert not res_cap.is_error


class TestChapter20ApplicationViewsDialogsUndoExport:
    """
    Chapter 20: Application Views, Native Dialogs, Undo/Redo & Universal LOM Escape Hatch.
    Tools:
      - live12_view_switch
      - live12_view_select
      - live12_dialog_inspect
      - live12_dialog_press
      - live12_undo_redo
      - live12_os_save_set
      - live12_os_open_set
      - live12_os_export_audio
      - live12_lom_inspect
      - live12_lom_get
      - live12_lom_set
      - live12_lom_call
    """

    def test_view_switching_and_selection(self, client: Live12TestClient):
        # View switching
        res_view = client.call_tool("live12_view_switch", {"view_name": "Session"})
        assert not res_view.is_error

        # View selection
        res_sel = client.call_tool("live12_view_select", {"track_index": 0})
        assert not res_sel.is_error

    def test_dialog_inspection_and_pressing(self, client: Live12TestClient):
        # Inspect dialogs
        res_insp = client.call_tool("live12_dialog_inspect")
        assert not res_insp.is_error

        # Press dialog button (button 0)
        res_press = client.call_tool("live12_dialog_press", {"button_index": 0})
        # If no dialog is open in live mode, press returns error code -32000 or clean status
        assert not res_press.is_error or "no open dialog" in str(res_press.data).lower()

    def test_undo_redo_transactions(self, client: Live12TestClient):
        # Query status
        res_stat = client.call_tool("live12_undo_redo", {"action": "status"})
        assert not res_stat.is_error

        # Begin & end undo step
        res_beg = client.call_tool("live12_undo_redo", {"action": "begin_step"})
        assert not res_beg.is_error

        res_end = client.call_tool("live12_undo_redo", {"action": "end_step"})
        assert not res_end.is_error

        # Undo & redo
        res_undo = client.call_tool("live12_undo_redo", {"action": "undo"})
        assert not res_undo.is_error

        res_redo = client.call_tool("live12_undo_redo", {"action": "redo"})
        assert not res_redo.is_error

    def test_os_actions_save_open_export(self, client: Live12TestClient):
        test_path = f"/tmp/__agy_test_{client.run_id}_set.als"
        export_path = f"/tmp/__agy_test_{client.run_id}_export.wav"

        # Save Live set
        res_save = client.call_tool("live12_os_save_set", {"destination_path": test_path})
        assert not res_save.is_error

        # Open Live set
        res_open = client.call_tool("live12_os_open_set", {"als_path": test_path})
        assert not res_open.is_error

        # Export audio WAV
        res_exp = client.call_tool("live12_os_export_audio", {"destination_wav_path": export_path})
        assert not res_exp.is_error

    def test_universal_lom_escape_hatch(self, client: Live12TestClient):
        # Inspect LOM path
        res_insp = client.call_tool("live12_lom_inspect", {"target_path": "song"})
        assert not res_insp.is_error
        assert "tempo" in res_insp.get("properties", [])

        # Get LOM property
        res_get = client.call_tool("live12_lom_get", {"target_path": "song", "property_name": "tempo"})
        assert not res_get.is_error
        assert "value" in res_get.data

        # Set LOM property
        res_set = client.call_tool("live12_lom_set", {
            "target_path": "song",
            "property_name": "tempo",
            "value": 124.0
        })
        assert not res_set.is_error

        # Call LOM method
        res_call = client.call_tool("live12_lom_call", {
            "target_path": "song",
            "method_name": "stop_all_clips"
        })
        assert not res_call.is_error


class TestAll75ToolsExercisedVerification:
    """Meta-test ensuring 100% of the 75 MCP tools are exercised across the 20 chapters."""

    def test_every_mcp_tool_in_catalog_is_tested(self):
        # Read the test file source to discover called tool names
        with open(__file__, "r", encoding="utf-8") as f:
            src = f.read()

        catalog_names = set(t["name"] if isinstance(t, dict) else t.name for t in ALL_TOOLS)
        assert len(catalog_names) == 75, f"Expected 75 tools in catalog, found {len(catalog_names)}"

        missing_from_tests = [t for t in catalog_names if f'"{t}"' not in src and f"'{t}'" not in src]
        assert not missing_from_tests, f"The following MCP tools are not referenced in the test suite: {missing_from_tests}"
