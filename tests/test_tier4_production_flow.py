"""
Tier 4: End-to-End Production Workflow Test Suite
==================================================
Simulates complete real-world music production scenarios:
1. Multi-track Melodic Techno Production Workflow (Drums, Rolling Bass, Chords, Audio Atmosphere, Sends, Mixdown & Save).
2. Generative Ambient & Microtonal Composition Workflow (Meld, Bohlen-Pierce tuning, LOM Escape Hatch & Slicing).
"""

import math
import os
import pytest
from harness import Live12TestClient


@pytest.mark.tier4
class TestTier4ProductionFlows:

    def test_production_flow_01_complete_melodic_techno_song(self, client: Live12TestClient):
        """
        Complete end-to-end production song construction:
        1. Set master tempo to 126.0 BPM, 4/4, F Minor (root 5, 'Minor'), loop 32 beats.
        2. Track 1: Drums (Drum Rack, 4-on-the-floor kick, off-beat hi-hat, clap).
        3. Track 2: Rolling Bass (Drift, 16th-note pattern with velocity deviation).
        4. Track 3: Lead/Chords (Wavetable, modulation matrix, reverb send).
        5. Track 4: Audio Atmosphere (Audio track, Complex warp mode, pitch shift).
        6. Scene creation, firing, transport playback verification.
        7. Render audio export and save session.
        """
        # --- 1. Global Song Setup ---
        t_res = client.call_tool("live12_transport_set_tempo", {"tempo": 126.0})
        assert not t_res.is_error

        sig_res = client.call_tool("live12_transport_set_time_signature", {"numerator": 4, "denominator": 4})
        assert not sig_res.is_error

        scale_res = client.call_tool("live12_song_set_scale", {"root_note": 5, "scale_name": "Minor"})
        assert not scale_res.is_error

        loop_res = client.call_tool("live12_transport_set_loop", {"enabled": True, "start": 0.0, "length": 32.0})
        assert not loop_res.is_error

        # --- 2. Track 1: Drums (Drum Rack) ---
        t_drums, _ = client.create_sandboxed_track("midi", "prod_drums")
        client.call_tool("live12_browser_load_item", {"track_index": t_drums, "browser_item_uri": "live:device:drum_rack"})
        client.call_tool("live12_clip_create", {"track_index": t_drums, "slot_index": 0, "length_beats": 4.0, "name": "Tech Beat"})

        drum_notes = [
            # 4-on-the-floor Kick (36)
            {"pitch": 36, "start_time": 0.0, "duration": 0.25, "velocity": 120.0, "probability": 1.0},
            {"pitch": 36, "start_time": 1.0, "duration": 0.25, "velocity": 118.0, "probability": 1.0},
            {"pitch": 36, "start_time": 2.0, "duration": 0.25, "velocity": 120.0, "probability": 1.0},
            {"pitch": 36, "start_time": 3.0, "duration": 0.25, "velocity": 118.0, "probability": 1.0},
            # Offbeat Open Hat (42) with probability
            {"pitch": 42, "start_time": 0.5, "duration": 0.25, "velocity": 95.0, "probability": 0.95},
            {"pitch": 42, "start_time": 1.5, "duration": 0.25, "velocity": 90.0, "probability": 0.95},
            {"pitch": 42, "start_time": 2.5, "duration": 0.25, "velocity": 95.0, "probability": 0.95},
            {"pitch": 42, "start_time": 3.5, "duration": 0.25, "velocity": 90.0, "probability": 0.95},
            # Clap on 2 and 4 (39)
            {"pitch": 39, "start_time": 1.0, "duration": 0.25, "velocity": 105.0, "velocity_deviation": -8.0},
            {"pitch": 39, "start_time": 3.0, "duration": 0.25, "velocity": 105.0, "velocity_deviation": 8.0},
        ]
        client.call_tool("live12_clip_add_notes", {"track_index": t_drums, "slot_index": 0, "notes": drum_notes})
        client.call_tool("live12_mixer_set", {"track_index": t_drums, "volume": 0.88, "pan": 0.0})

        # --- 3. Track 2: Rolling Bass (Drift) ---
        t_bass, _ = client.create_sandboxed_track("midi", "prod_bass")
        client.call_tool("live12_browser_load_item", {"track_index": t_bass, "browser_item_uri": "live:device:drift"})
        client.call_tool("live12_clip_create", {"track_index": t_bass, "slot_index": 0, "length_beats": 4.0, "name": "Rolling Sub"})

        # 16th-note rolling groove in F (pitch 29)
        bass_notes = []
        for step in range(16):
            bass_notes.append({
                "pitch": 29 if step % 4 != 3 else 32,  # occasional minor third bounce
                "start_time": step * 0.25,
                "duration": 0.20,
                "velocity": 100.0 if step % 2 == 0 else 85.0,
                "velocity_deviation": -5.0 if step % 2 == 1 else 0.0,
                "probability": 1.0 if step % 4 == 0 else 0.88
            })
        client.call_tool("live12_clip_add_notes", {"track_index": t_bass, "slot_index": 0, "notes": bass_notes})
        client.call_tool("live12_device_set_parameter", {
            "track_index": t_bass,
            "device_index": 0,
            "parameter_identifier": "Filter Freq",
            "value": 650.0
        })
        client.call_tool("live12_mixer_set", {"track_index": t_bass, "volume": 0.84, "pan": 0.0})

        # --- 4. Track 3: Lead & Chords (Wavetable) ---
        t_synth, _ = client.create_sandboxed_track("midi", "prod_chords")
        client.call_tool("live12_browser_load_item", {"track_index": t_synth, "browser_item_uri": "live:device:wavetable"})
        client.call_tool("live12_wavetable_modulation_matrix", {
            "track_index": t_synth,
            "device_index": 0,
            "action": "set",
            "source": "LFO 1",
            "target": "Filter 1 Freq",
            "amount": 0.55
        })
        client.call_tool("live12_clip_create", {"track_index": t_synth, "slot_index": 0, "length_beats": 8.0, "name": "F Minor Pad"})

        synth_chord = [
            {"pitch": 53, "start_time": 0.0, "duration": 8.0, "velocity": 90.0, "probability": 1.0},
            {"pitch": 56, "start_time": 0.0, "duration": 8.0, "velocity": 85.0, "probability": 0.9},
            {"pitch": 60, "start_time": 0.0, "duration": 8.0, "velocity": 80.0, "probability": 0.85},
            {"pitch": 65, "start_time": 0.0, "duration": 8.0, "velocity": 75.0, "probability": 0.80},
        ]
        client.call_tool("live12_clip_add_notes", {"track_index": t_synth, "slot_index": 0, "notes": synth_chord})
        # Route send 0 to Reverb
        client.call_tool("live12_mixer_set", {
            "track_index": t_synth,
            "volume": 0.78,
            "pan": 0.20,
            "sends": {"0": 0.45}
        })

        # --- 5. Track 4: Audio Atmosphere ---
        t_audio, _ = client.create_sandboxed_track("audio", "prod_atmos")
        client.call_tool("live12_clip_create", {"track_index": t_audio, "slot_index": 0, "length_beats": 16.0, "name": "Noise Swell"})
        client.call_tool("live12_audio_clip_set_warp", {
            "track_index": t_audio,
            "slot_index": 0,
            "warping": True,
            "warp_mode": "Texture",
            "pitch_shift": -5.0,
            "gain": -3.0
        })

        # --- 6. Scene & Playback Verification ---
        s_idx, _ = client.create_sandboxed_scene("Drop Scene")
        client.call_tool("live12_scene_fire", {"index": s_idx})

        play_res = client.call_tool("live12_transport_play", {"restart": True})
        assert not play_res.is_error

        # Read back telemetry
        state = client.call_tool("live12_song_get_state")
        assert state["is_playing"] is True
        assert math.isclose(state["tempo"], 126.0, rel_tol=1e-4)
        assert state["scale_root_note"] == 5
        assert state["scale_name"] == "Minor"

        # --- 7. Save & Export Automation ---
        als_path = f"/tmp/__agy_test_{client.run_id}_techno_session.als"
        save_res = client.call_tool("live12_os_save_set", {"destination_path": als_path})
        assert not save_res.is_error
        assert os.path.exists(als_path)

        wav_path = f"/tmp/__agy_test_{client.run_id}_techno_master.wav"
        export_res = client.call_tool("live12_os_export_audio", {"destination_wav_path": wav_path})
        assert not export_res.is_error
        assert os.path.exists(wav_path)

        # Stop playback
        client.call_tool("live12_transport_stop")

    def test_production_flow_02_generative_ambient_microtonal_workflow(self, client: Live12TestClient):
        """
        Generative Ambient & Microtonal Tuning Workflow:
        1. Set tempo = 84.0 BPM, Microtonal Tuning = 'Bohlen-Pierce Scale', Scale = C Dorian.
        2. Meld specialized synth track with generative probabilities (0.35..0.60).
        3. Simpler track with sample slicing.
        4. Dynamic LOM Escape Hatch inspection and remote method dispatch.
        """
        # 1. Setup
        client.call_tool("live12_transport_set_tempo", {"tempo": 84.0})
        client.call_tool("live12_song_set_scale", {"root_note": 0, "scale_name": "Dorian"})
        client.call_tool("live12_song_set_tuning_system", {"tuning_name": "Bohlen-Pierce Scale"})

        # 2. Generative Meld Synth
        t_meld, _ = client.create_sandboxed_track("midi", "ambient_meld")
        client.call_tool("live12_browser_load_item", {"track_index": t_meld, "browser_item_uri": "live:device:meld"})
        client.call_tool("live12_meld_control", {
            "track_index": t_meld,
            "device_index": 0,
            "engine_params": {"macro_a": 0.45, "macro_b": 0.72}
        })
        client.call_tool("live12_clip_create", {"track_index": t_meld, "slot_index": 0, "length_beats": 32.0, "name": "Generative Arp"})

        gen_notes = [
            {"pitch": 48, "start_time": 0.0, "duration": 4.0, "probability": 0.90},
            {"pitch": 55, "start_time": 4.0, "duration": 6.0, "probability": 0.65},
            {"pitch": 62, "start_time": 10.0, "duration": 4.0, "probability": 0.50},
            {"pitch": 67, "start_time": 16.0, "duration": 8.0, "probability": 0.40},
            {"pitch": 72, "start_time": 24.0, "duration": 6.0, "probability": 0.35},
        ]
        add_res = client.call_tool("live12_clip_add_notes", {"track_index": t_meld, "slot_index": 0, "notes": gen_notes})
        assert not add_res.is_error
        assert add_res["added_count"] == 5

        # 3. Simpler Slicing
        t_simp, _ = client.create_sandboxed_track("midi", "ambient_simpler")
        client.call_tool("live12_browser_load_item", {"track_index": t_simp, "browser_item_uri": "live:device:simpler"})
        simp_res = client.call_tool("live12_simpler_control", {
            "track_index": t_simp,
            "device_index": 0,
            "action": "slice",
            "params": {"mode": "transient"}
        })
        assert not simp_res.is_error
        assert simp_res["status"] == "sliced"

        # 4. Universal LOM Escape Hatch Traversal
        lom_insp = client.call_tool("live12_lom_inspect", {"target_path": f"live_set.tracks.{t_meld}"})
        assert not lom_insp.is_error
        assert "Live.Track.Track" in lom_insp["type"]

        lom_call = client.call_tool("live12_lom_call", {
            "target_path": f"live_set.tracks.{t_meld}",
            "method_name": "stop_all_clips",
            "args": []
        })
        assert not lom_call.is_error

        # 5. Telemetry Verification
        state = client.call_tool("live12_song_get_state")
        assert math.isclose(state["tempo"], 84.0, rel_tol=1e-4)
        assert state["tuning_system"] == "Bohlen-Pierce Scale"
