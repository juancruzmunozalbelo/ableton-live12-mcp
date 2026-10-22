"""
Tier 3: Pairwise Subsystem Interaction Test Suite
==================================================
Tests cross-subsystem interactions between multiple domains:
1. Track Creation + Instrument Load + Clip Creation + Live 12 Extended MIDI + Playback.
2. Drum Rack Load + Multi-Pad Notes + Quantization.
3. Audio Track + Warping Modes + Warp Markers + Gain/Pitch Shift.
4. Instrument Track + Return Bus + Mixer Sends + Routing.
5. Audio Effect Rack + Macro Automation + Multi-Variation Storage & Recall.
6. View Switching + UI Selection Sync (Track/Scene/Clip/Device).
"""

import math
import pytest
from harness import Live12TestClient


@pytest.mark.tier3
class TestTier3PairwiseInteractions:

    def test_pairwise_01_track_synth_clip_notes_playback(self, client: Live12TestClient):
        """Cross-domain: Track + Browser Device + Clip + Extended MIDI + Transport."""
        # 1. Create sandboxed MIDI track
        t_idx, _ = client.create_sandboxed_track("midi", "pw_synth")

        # 2. Load Drift synthesizer from Browser
        load_res = client.call_tool("live12_browser_load_item", {
            "track_index": t_idx,
            "browser_item_uri": "live:device:drift"
        })
        assert not load_res.is_error

        # 3. Create 4-bar clip
        clip_res = client.call_tool("live12_clip_create", {
            "track_index": t_idx,
            "slot_index": 0,
            "length_beats": 16.0,
            "name": "Drift Chords"
        })
        assert not clip_res.is_error

        # 4. Insert polyphonic chord (D Minor 9: D3=50, F3=53, A3=57, C4=60, E4=64)
        chord_notes = [
            {"pitch": 50, "start_time": 0.0, "duration": 4.0, "velocity": 105.0, "probability": 1.0, "velocity_deviation": 0.0},
            {"pitch": 53, "start_time": 0.0, "duration": 4.0, "velocity": 95.0, "probability": 0.9, "velocity_deviation": -5.0},
            {"pitch": 57, "start_time": 0.0, "duration": 4.0, "velocity": 90.0, "probability": 0.8, "velocity_deviation": -10.0},
            {"pitch": 60, "start_time": 0.0, "duration": 4.0, "velocity": 85.0, "probability": 0.75, "velocity_deviation": 5.0},
            {"pitch": 64, "start_time": 0.0, "duration": 4.0, "velocity": 80.0, "probability": 0.5, "velocity_deviation": 10.0},
        ]
        add_res = client.call_tool("live12_clip_add_notes", {
            "track_index": t_idx,
            "slot_index": 0,
            "notes": chord_notes
        })
        assert not add_res.is_error
        assert add_res["added_count"] == 5

        # 5. Read back notes and verify properties
        notes_res = client.call_tool("live12_clip_get_notes", {"track_index": t_idx, "slot_index": 0})
        assert not notes_res.is_error
        retrieved = notes_res["notes"]
        assert len(retrieved) == 5
        top_note = next(n for n in retrieved if n["pitch"] == 64)
        assert math.isclose(top_note["probability"], 0.5, rel_tol=1e-4)
        assert math.isclose(top_note["velocity_deviation"], 10.0, rel_tol=1e-4)

        # 6. Fire clip and start transport
        fire_res = client.call_tool("live12_clip_fire", {"track_index": t_idx, "slot_index": 0})
        assert not fire_res.is_error
        play_res = client.call_tool("live12_transport_play")
        assert not play_res.is_error

        # 7. Assert playing state
        state = client.call_tool("live12_song_get_state")
        assert state["is_playing"] is True

        # 8. Stop clip and transport
        client.call_tool("live12_clip_stop", {"track_index": t_idx, "slot_index": 0})
        client.call_tool("live12_transport_stop")

    def test_pairwise_02_drum_rack_multi_pad_quantization(self, client: Live12TestClient):
        """Cross-domain: Drum Rack + Micro-timing Notes + Quantization."""
        t_idx, _ = client.create_sandboxed_track("midi", "pw_drums")
        client.call_tool("live12_browser_load_item", {"track_index": t_idx, "browser_item_uri": "live:device:drum_rack"})
        client.call_tool("live12_clip_create", {"track_index": t_idx, "slot_index": 0, "length_beats": 4.0})

        # Insert loose unquantized beat (Kick=36, Snare=38)
        raw_notes = [
            {"pitch": 36, "start_time": 0.08, "duration": 0.25, "velocity": 120},
            {"pitch": 38, "start_time": 1.05, "duration": 0.25, "velocity": 110},
            {"pitch": 36, "start_time": 2.06, "duration": 0.25, "velocity": 115},
            {"pitch": 38, "start_time": 3.04, "duration": 0.25, "velocity": 112},
        ]
        client.call_tool("live12_clip_add_notes", {"track_index": t_idx, "slot_index": 0, "notes": raw_notes})

        # Quantize to quarter note grid (1.0) with 100% strength
        quant_res = client.call_tool("live12_clip_quantize", {
            "track_index": t_idx,
            "slot_index": 0,
            "grid": 1.0,
            "amount": 1.0
        })
        assert not quant_res.is_error

        # Read back and verify strict alignment to beat grid (0.0, 1.0, 2.0, 3.0)
        notes = client.call_tool("live12_clip_get_notes", {"track_index": t_idx, "slot_index": 0})["notes"]
        expected_times = [0.0, 1.0, 2.0, 3.0]
        actual_times = sorted([n["start_time"] for n in notes])
        for act, exp in zip(actual_times, expected_times):
            assert math.isclose(act, exp, rel_tol=1e-4)

    def test_pairwise_03_audio_track_warp_markers_pitch_shift(self, client: Live12TestClient):
        """Cross-domain: Audio Track + Warping Engine + Pitch Shift + Warp Markers."""
        t_idx, _ = client.create_sandboxed_track("audio", "pw_audio")
        client.call_tool("live12_clip_create", {"track_index": t_idx, "slot_index": 0, "length_beats": 8.0})

        # Set warp parameters
        warp_res = client.call_tool("live12_audio_clip_set_warp", {
            "track_index": t_idx,
            "slot_index": 0,
            "warping": True,
            "warp_mode": "Complex",
            "pitch_shift": -7.0,
            "gain": 1.8
        })
        assert not warp_res.is_error
        assert warp_res["warp_mode"] == "Complex"
        assert math.isclose(warp_res["pitch_shift"], -7.0, rel_tol=1e-4)

        # Add multiple warp markers
        for beat, sample in [(1.0, 1.05), (2.0, 2.02), (3.0, 3.08)]:
            client.call_tool("live12_audio_clip_add_warp_marker", {
                "track_index": t_idx,
                "slot_index": 0,
                "beat_time": beat,
                "sample_time": sample
            })

    def test_pairwise_04_return_track_bus_routing_and_sends(self, client: Live12TestClient):
        """Cross-domain: Instrument Track + Return Track + Send Levels + Panning."""
        t_idx, _ = client.create_sandboxed_track("midi", "pw_bus_src")
        client.call_tool("live12_browser_load_item", {"track_index": t_idx, "browser_item_uri": "live:device:meld"})

        # Configure mixer send to Return A (index 0) and Return B (index 1)
        mix_res = client.call_tool("live12_mixer_set", {
            "track_index": t_idx,
            "volume": 0.82,
            "pan": -0.35,
            "sends": {"0": 0.65, "1": 0.25},
            "crossfader": "None"
        })
        assert not mix_res.is_error
        assert math.isclose(mix_res["volume"], 0.82, rel_tol=1e-4)
        sends_dict = mix_res["sends"]
        s0_val = sends_dict.get("0") if "0" in sends_dict else sends_dict.get(0)
        assert math.isclose(s0_val, 0.65, rel_tol=1e-4)

    def test_pairwise_05_rack_macro_and_multi_variations(self, client: Live12TestClient):
        """Cross-domain: Effect Rack + Macro Tweaks + Variation Storing & Recalls."""
        t_idx, _ = client.create_sandboxed_track("midi", "pw_rack_var")
        client.call_tool("live12_browser_load_item", {"track_index": t_idx, "browser_item_uri": "live:device:audio_effect_rack"})

        # State 1: Macro 0 = 0.2, Macro 1 = 0.8
        client.call_tool("live12_rack_macro_control", {"track_index": t_idx, "device_index": 0, "macro_index": 0, "value": 0.2})
        client.call_tool("live12_rack_macro_control", {"track_index": t_idx, "device_index": 0, "macro_index": 1, "value": 0.8})
        v0 = client.call_tool("live12_rack_variation_control", {"track_index": t_idx, "device_index": 0, "action": "store"})
        assert not v0.is_error
        idx0 = v0["variation_index"]

        # State 2: Macro 0 = 0.95, Macro 1 = 0.05
        client.call_tool("live12_rack_macro_control", {"track_index": t_idx, "device_index": 0, "macro_index": 0, "value": 0.95})
        client.call_tool("live12_rack_macro_control", {"track_index": t_idx, "device_index": 0, "macro_index": 1, "value": 0.05})
        v1 = client.call_tool("live12_rack_variation_control", {"track_index": t_idx, "device_index": 0, "action": "store"})
        assert not v1.is_error
        idx1 = v1["variation_index"]

        # Recall Variation 0 and verify
        rec0 = client.call_tool("live12_rack_variation_control", {
            "track_index": t_idx,
            "device_index": 0,
            "action": "recall",
            "variation_index": idx0
        })
        assert not rec0.is_error
        assert math.isclose(rec0["macros"][0], 0.2, rel_tol=1e-4)
        assert math.isclose(rec0["macros"][1], 0.8, rel_tol=1e-4)

        # Recall Variation 1 and verify
        rec1 = client.call_tool("live12_rack_variation_control", {
            "track_index": t_idx,
            "device_index": 0,
            "action": "recall",
            "variation_index": idx1
        })
        assert not rec1.is_error
        assert math.isclose(rec1["macros"][0], 0.95, rel_tol=1e-4)
        assert math.isclose(rec1["macros"][1], 0.05, rel_tol=1e-4)

    def test_pairwise_06_view_switching_and_selection_sync(self, client: Live12TestClient):
        """Cross-domain: View Navigation + Entity Selection Synchronization."""
        t_idx, _ = client.create_sandboxed_track("midi", "pw_view_sync")
        client.call_tool("live12_browser_load_item", {"track_index": t_idx, "browser_item_uri": "live:device:drift"})
        client.call_tool("live12_clip_create", {"track_index": t_idx, "slot_index": 0})

        # Switch to Session
        v_sess = client.call_tool("live12_view_switch", {"view_name": "Session"})
        assert not v_sess.is_error

        # Select track and clip slot
        sel_res = client.call_tool("live12_view_select", {
            "track_index": t_idx,
            "clip_slot": [t_idx, 0],
            "device_index": 0
        })
        assert not sel_res.is_error
        assert sel_res["selected_track"] == t_idx
        assert list(sel_res["selected_clip_slot"]) == [t_idx, 0]

        # Switch to Detail/Clip
        v_clip = client.call_tool("live12_view_switch", {"view_name": "Detail/Clip"})
        assert not v_clip.is_error
        assert v_clip["active_view"] == "Detail/Clip"
