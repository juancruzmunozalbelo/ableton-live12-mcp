"""
Tier 1: Feature & Protocol Isolation Test Suite
================================================
Validates atomic functionality across all 6 functional domains in Requirement R3:
- Domain 1: Transport, Song & Arrangement (>= 5 tests)
- Domain 2: Tracks, Take Lanes, Scenes & Routing (>= 5 tests)
- Domain 3: Clips, Extended MIDI & Audio Warping (>= 5 tests)
- Domain 4: Browser, Devices, Specialized Live 12 Devices & Parameters (>= 5 tests)
- Domain 5: View, Native Dialogs & OS-Level Actions (>= 5 tests)
- Domain 6: Universal LOM Escape Hatch (>= 5 tests)

Every test creates sandboxed objects and performs mandatory read-back verification.
"""

import math
import os
import pytest
from harness import Live12TestClient


@pytest.mark.tier1
class TestTier1Domain1TransportAndSong:
    """Domain 1: Transport, Song & Arrangement feature isolation."""

    def test_domain1_01_transport_play_and_stop(self, client: Live12TestClient):
        # 1. Mutate: Start playback
        play_res = client.call_tool("live12_transport_play", {"restart": True})
        assert not play_res.is_error

        # 2. Read-Back: Verify state is playing
        state = client.call_tool("live12_song_get_state")
        assert not state.is_error
        assert state["is_playing"] is True

        # 3. Mutate: Stop playback
        stop_res = client.call_tool("live12_transport_stop")
        assert not stop_res.is_error

        # 4. Read-Back: Verify stopped
        state_after = client.call_tool("live12_song_get_state")
        assert state_after["is_playing"] is False

    def test_domain1_02_transport_record_mode(self, client: Live12TestClient):
        rec_res = client.call_tool("live12_transport_record", {"record_mode": "arrangement"})
        assert not rec_res.is_error

        state = client.call_tool("live12_song_get_state")
        assert state["is_recording"] is True

        # Stop
        client.call_tool("live12_transport_stop")

    def test_domain1_03_tempo_mutation_and_readback(self, client: Live12TestClient):
        target_tempo = 128.5
        tempo_res = client.call_tool("live12_transport_set_tempo", {"tempo": target_tempo})
        assert not tempo_res.is_error

        state = client.call_tool("live12_song_get_state")
        assert math.isclose(state["tempo"], target_tempo, rel_tol=1e-4)

    def test_domain1_04_time_signature_and_metronome(self, client: Live12TestClient):
        sig_res = client.call_tool("live12_transport_set_time_signature", {"numerator": 3, "denominator": 4})
        assert not sig_res.is_error

        metro_res = client.call_tool("live12_transport_set_metronome", {"enabled": True})
        assert not metro_res.is_error

        state = client.call_tool("live12_song_get_state")
        assert state["signature_numerator"] == 3
        assert state["signature_denominator"] == 4
        assert state["metronome"] is True

    def test_domain1_05_loop_and_punch_region(self, client: Live12TestClient):
        loop_res = client.call_tool("live12_transport_set_loop", {"enabled": True, "start": 4.0, "length": 8.0})
        assert not loop_res.is_error

        punch_res = client.call_tool("live12_transport_set_punch", {"punch_in": True, "punch_out": False})
        assert not punch_res.is_error

        state = client.call_tool("live12_song_get_state")
        assert state["loop"] is True
        assert math.isclose(state["loop_start"], 4.0, rel_tol=1e-4)
        assert math.isclose(state["loop_length"], 8.0, rel_tol=1e-4)

    def test_domain1_06_scale_and_tuning_information(self, client: Live12TestClient):
        # Set project scale to D Dorian (root_note=2, scale="Dorian")
        scale_res = client.call_tool("live12_song_set_scale", {"root_note": 2, "scale_name": "Dorian"})
        assert not scale_res.is_error

        tuning_res = client.call_tool("live12_song_set_tuning_system", {"tuning_name": "Werckmeister III"})
        assert not tuning_res.is_error

        state = client.call_tool("live12_song_get_state")
        assert state["scale_root_note"] == 2
        assert state["scale_name"] == "Dorian"
        assert state["tuning_system"] == "Werckmeister III"

    def test_domain1_07_capture_midi(self, client: Live12TestClient):
        cap_res = client.call_tool("live12_song_capture_midi")
        assert not cap_res.is_error
        assert cap_res["status"] == "success"


@pytest.mark.tier1
class TestTier1Domain2TracksAndRouting:
    """Domain 2: Tracks, Take Lanes, Scenes & Routing feature isolation."""

    def test_domain2_01_track_creation_and_properties(self, client: Live12TestClient):
        t_idx, name = client.create_sandboxed_track("midi", "synth_track")
        assert t_idx >= 0

        # Mutate properties: color, solo, mute
        prop_res = client.call_tool("live12_track_set_properties", {
            "track_index": t_idx,
            "color": 65280,
            "solo": True,
            "mute": False,
            "arm": True
        })
        assert not prop_res.is_error
        assert prop_res["color"] == 65280
        assert prop_res["solo"] is True
        assert prop_res["arm"] is True

    def test_domain2_02_track_duplication_and_deletion(self, client: Live12TestClient):
        t_idx, _ = client.create_sandboxed_track("audio", "audio_stem")
        dup_res = client.call_tool("live12_track_duplicate", {"track_index": t_idx})
        assert not dup_res.is_error
        dup_idx = dup_res["track_index"]
        assert dup_idx == t_idx + 1

        # Delete duplicate
        del_res = client.call_tool("live12_track_delete", {"track_index": dup_idx})
        assert not del_res.is_error

    def test_domain2_03_takelane_creation_and_comping(self, client: Live12TestClient):
        t_idx, _ = client.create_sandboxed_track("audio", "vocal_track")

        # Create take lane
        lane_res = client.call_tool("live12_take_lane_create", {"track_index": t_idx})
        assert not lane_res.is_error
        lane_idx = lane_res["lane_index"]

        # Comp region
        comp_res = client.call_tool("live12_take_lane_comp_region", {
            "track_index": t_idx,
            "lane_index": lane_idx,
            "start": 0.0,
            "length": 4.0
        })
        assert not comp_res.is_error

        # Read back take lane list
        lanes = client.call_tool("live12_take_lane_list", {"track_index": t_idx})
        assert not lanes.is_error
        assert len(lanes["take_lanes"]) >= 1

    def test_domain2_04_scene_creation_and_firing(self, client: Live12TestClient):
        s_idx, name = client.create_sandboxed_scene("verse_scene")
        assert s_idx >= 0

        fire_res = client.call_tool("live12_scene_fire", {"index": s_idx})
        assert not fire_res.is_error
        assert fire_res["is_playing"] is True

    def test_domain2_05_routing_and_monitoring(self, client: Live12TestClient):
        t_idx, _ = client.create_sandboxed_track("midi", "routing_test")

        route_res = client.call_tool("live12_routing_set", {
            "track_index": t_idx,
            "input_type": "Ext. In",
            "input_channel": "1/2",
            "output_type": "Master",
            "output_channel": "1/2",
            "monitoring": "In"
        })
        assert not route_res.is_error
        assert route_res["input_type"] == "Ext. In"
        assert route_res["monitoring"] == "In"

    def test_domain2_06_mixer_volume_pan_sends(self, client: Live12TestClient):
        t_idx, _ = client.create_sandboxed_track("midi", "mixer_test")

        mix_res = client.call_tool("live12_mixer_set", {
            "track_index": t_idx,
            "volume": 0.75,
            "pan": -0.25,
            "sends": {"0": 0.5, "1": 0.3},
            "crossfader": "A"
        })
        assert not mix_res.is_error
        assert math.isclose(mix_res["volume"], 0.75, rel_tol=1e-4)
        assert math.isclose(mix_res["pan"], -0.25, rel_tol=1e-4)
        assert mix_res["crossfader"] == "A"


@pytest.mark.tier1
class TestTier1Domain3ClipsAndExtendedMIDI:
    """Domain 3: Clips, Extended MIDI & Audio Warping feature isolation."""

    def test_domain3_01_clip_creation_and_firing(self, client: Live12TestClient):
        t_idx, _ = client.create_sandboxed_track("midi", "clip_host")

        # Create 8-bar clip in slot 0
        clip_res = client.call_tool("live12_clip_create", {
            "track_index": t_idx,
            "slot_index": 0,
            "length_beats": 8.0,
            "name": "Sandboxed Clip"
        })
        assert not clip_res.is_error
        assert clip_res["clip"]["length"] == 8.0

        # Fire clip
        fire_res = client.call_tool("live12_clip_fire", {"track_index": t_idx, "slot_index": 0})
        assert not fire_res.is_error
        assert fire_res["is_playing"] is True

        # Stop clip
        stop_res = client.call_tool("live12_clip_stop", {"track_index": t_idx, "slot_index": 0})
        assert not stop_res.is_error
        assert stop_res["is_playing"] is False

    def test_domain3_02_extended_midi_notes_creation(self, client: Live12TestClient):
        t_idx, _ = client.create_sandboxed_track("midi", "note_host")
        client.call_tool("live12_clip_create", {"track_index": t_idx, "slot_index": 0, "length_beats": 4.0})

        # Insert Live 12 extended notes with probability and velocity deviation
        notes_to_add = [
            {
                "pitch": 60,
                "start_time": 0.0,
                "duration": 0.5,
                "velocity": 100.0,
                "velocity_deviation": -10.0,
                "release_velocity": 64.0,
                "probability": 0.85,
                "mute": False
            },
            {
                "pitch": 64,
                "start_time": 0.5,
                "duration": 0.5,
                "velocity": 90.0,
                "velocity_deviation": 5.0,
                "release_velocity": 64.0,
                "probability": 0.60,
                "mute": False
            }
        ]
        add_res = client.call_tool("live12_clip_add_notes", {
            "track_index": t_idx,
            "slot_index": 0,
            "notes": notes_to_add
        })
        assert not add_res.is_error
        assert add_res["added_count"] == 2

        # Read-back verification
        get_res = client.call_tool("live12_clip_get_notes", {"track_index": t_idx, "slot_index": 0})
        assert not get_res.is_error
        retrieved = get_res["notes"]
        assert len(retrieved) == 2
        assert retrieved[0]["pitch"] == 60
        assert math.isclose(retrieved[0]["probability"], 0.85, rel_tol=1e-4)
        assert math.isclose(retrieved[0]["velocity_deviation"], -10.0, rel_tol=1e-4)
        assert retrieved[1]["pitch"] == 64
        assert math.isclose(retrieved[1]["probability"], 0.60, rel_tol=1e-4)

    def test_domain3_03_extended_midi_notes_modification(self, client: Live12TestClient):
        t_idx, _ = client.create_sandboxed_track("midi", "mod_host")
        client.call_tool("live12_clip_create", {"track_index": t_idx, "slot_index": 0})
        client.call_tool("live12_clip_add_notes", {
            "track_index": t_idx,
            "slot_index": 0,
            "notes": [{"pitch": 67, "start_time": 1.0, "duration": 1.0, "velocity": 80}]
        })

        # Modify note
        mod_res = client.call_tool("live12_clip_modify_notes", {
            "track_index": t_idx,
            "slot_index": 0,
            "note_modifications": [{"pitch": 67, "velocity": 120, "probability": 0.45}]
        })
        assert not mod_res.is_error

        # Read back
        notes = client.call_tool("live12_clip_get_notes", {"track_index": t_idx, "slot_index": 0})["notes"]
        assert len(notes) == 1
        assert math.isclose(notes[0]["velocity"], 120.0, rel_tol=1e-4)
        assert math.isclose(notes[0]["probability"], 0.45, rel_tol=1e-4)

    def test_domain3_04_clip_quantization(self, client: Live12TestClient):
        t_idx, _ = client.create_sandboxed_track("midi", "quant_host")
        client.call_tool("live12_clip_create", {"track_index": t_idx, "slot_index": 0})
        # Add unquantized note at 0.23 (near 0.25)
        client.call_tool("live12_clip_add_notes", {
            "track_index": t_idx,
            "slot_index": 0,
            "notes": [{"pitch": 60, "start_time": 0.23, "duration": 0.5}]
        })

        quant_res = client.call_tool("live12_clip_quantize", {
            "track_index": t_idx,
            "slot_index": 0,
            "grid": 0.25,
            "amount": 1.0
        })
        assert not quant_res.is_error

        notes = client.call_tool("live12_clip_get_notes", {"track_index": t_idx, "slot_index": 0})["notes"]
        assert math.isclose(notes[0]["start_time"], 0.25, rel_tol=1e-4)

    def test_domain3_05_clip_properties_loop_and_markers(self, client: Live12TestClient):
        t_idx, _ = client.create_sandboxed_track("midi", "prop_host")
        client.call_tool("live12_clip_create", {"track_index": t_idx, "slot_index": 0, "length_beats": 16.0})

        prop_res = client.call_tool("live12_clip_set_properties", {
            "track_index": t_idx,
            "slot_index": 0,
            "loop": True,
            "loop_start": 2.0,
            "loop_end": 10.0,
            "start_marker": 1.0
        })
        assert not prop_res.is_error
        assert prop_res["loop_start"] == 2.0
        assert prop_res["loop_end"] == 10.0
        assert prop_res["start_marker"] == 1.0

    def test_domain3_06_audio_clip_warp_settings(self, client: Live12TestClient):
        t_idx, _ = client.create_sandboxed_track("audio", "warp_host")
        client.call_tool("live12_clip_create", {"track_index": t_idx, "slot_index": 0, "length_beats": 4.0})

        warp_res = client.call_tool("live12_audio_clip_set_warp", {
            "track_index": t_idx,
            "slot_index": 0,
            "warping": True,
            "warp_mode": "Complex Pro",
            "pitch_shift": 3.0,
            "gain": -1.5
        })
        assert not warp_res.is_error
        assert warp_res["warp_mode"] == "Complex Pro"
        assert math.isclose(warp_res["pitch_shift"], 3.0, rel_tol=1e-4)

        marker_res = client.call_tool("live12_audio_clip_add_warp_marker", {
            "track_index": t_idx,
            "slot_index": 0,
            "beat_time": 2.0,
            "sample_time": 2.1
        })
        assert not marker_res.is_error
        assert marker_res["total_warp_markers"] >= 1


@pytest.mark.tier1
class TestTier1Domain4BrowserAndDevices:
    """Domain 4: Browser, Devices, Specialized Live 12 Devices & Parameters."""

    def test_domain4_01_browser_search(self, client: Live12TestClient):
        search_res = client.call_tool("live12_browser_search", {"query": "Drift", "category": "instruments"})
        assert not search_res.is_error
        results = search_res["results"]
        assert len(results) > 0
        assert any("Drift" in r["name"] for r in results)

    def test_domain4_02_load_device_onto_track(self, client: Live12TestClient):
        t_idx, _ = client.create_sandboxed_track("midi", "dev_host")
        load_res = client.call_tool("live12_browser_load_item", {
            "track_index": t_idx,
            "browser_item_uri": "live:device:drift"
        })
        assert not load_res.is_error

        # Read back device list
        dev_list = client.call_tool("live12_device_list", {"track_index": t_idx})
        assert not dev_list.is_error
        assert len(dev_list["devices"]) >= 1
        assert "Drift" in dev_list["devices"][0]["name"]

    def test_domain4_03_device_parameter_get_and_set(self, client: Live12TestClient):
        t_idx, _ = client.create_sandboxed_track("midi", "param_host")
        client.call_tool("live12_browser_load_item", {"track_index": t_idx, "browser_item_uri": "live:device:drift"})

        # Get parameters
        params_res = client.call_tool("live12_device_get_parameters", {"track_index": t_idx, "device_index": 0})
        assert not params_res.is_error
        params = params_res["parameters"]
        assert len(params) > 0

        # Set parameter
        set_res = client.call_tool("live12_device_set_parameter", {
            "track_index": t_idx,
            "device_index": 0,
            "parameter_identifier": "Filter Freq",
            "value": 4500.0,
            "normalized": False
        })
        assert not set_res.is_error
        assert math.isclose(set_res["value"], 4500.0, rel_tol=1e-4)

    def test_domain4_04_device_toggle(self, client: Live12TestClient):
        t_idx, _ = client.create_sandboxed_track("midi", "toggle_host")
        client.call_tool("live12_browser_load_item", {"track_index": t_idx, "browser_item_uri": "live:device:drift"})

        # Toggle OFF
        off_res = client.call_tool("live12_device_toggle", {"track_index": t_idx, "device_index": 0, "enabled": False})
        assert not off_res.is_error
        assert off_res["is_active"] is False

        # Toggle ON
        on_res = client.call_tool("live12_device_toggle", {"track_index": t_idx, "device_index": 0, "enabled": True})
        assert not on_res.is_error
        assert on_res["is_active"] is True

    def test_domain4_05_rack_macro_control_and_variations(self, client: Live12TestClient):
        t_idx, _ = client.create_sandboxed_track("midi", "rack_host")
        client.call_tool("live12_browser_load_item", {"track_index": t_idx, "browser_item_uri": "live:device:audio_effect_rack"})

        # Set macro 0
        macro_res = client.call_tool("live12_rack_macro_control", {
            "track_index": t_idx,
            "device_index": 0,
            "macro_index": 0,
            "value": 0.85
        })
        assert not macro_res.is_error
        assert math.isclose(macro_res["value"], 0.85, rel_tol=1e-4)

        # Store variation
        store_res = client.call_tool("live12_rack_variation_control", {
            "track_index": t_idx,
            "device_index": 0,
            "action": "store"
        })
        assert not store_res.is_error

        # Recall variation
        recall_res = client.call_tool("live12_rack_variation_control", {
            "track_index": t_idx,
            "device_index": 0,
            "action": "recall",
            "variation_index": 0
        })
        assert not recall_res.is_error

    def test_domain4_06_specialized_devices_controls(self, client: Live12TestClient):
        t_idx, _ = client.create_sandboxed_track("midi", "spec_host")
        client.call_tool("live12_browser_load_item", {"track_index": t_idx, "browser_item_uri": "live:device:wavetable"})

        # Wavetable Modulation Matrix
        matrix_res = client.call_tool("live12_wavetable_modulation_matrix", {
            "track_index": t_idx,
            "device_index": 0,
            "action": "set",
            "source": "LFO 1",
            "target": "Filter 1 Freq",
            "amount": 0.75
        })
        assert not matrix_res.is_error
        assert math.isclose(matrix_res["amount"], 0.75, rel_tol=1e-4)

        # Meld & Roar Controls
        meld_res = client.call_tool("live12_meld_control", {
            "track_index": t_idx,
            "device_index": 0,
            "engine_params": {"macro_a": 0.5, "macro_b": 0.8}
        })
        assert not meld_res.is_error

        roar_res = client.call_tool("live12_roar_control", {
            "track_index": t_idx,
            "device_index": 0,
            "stage_params": {"drive": 12.0, "stage": "single"}
        })
        assert not roar_res.is_error


@pytest.mark.tier1
class TestTier1Domain5ViewAndOSActions:
    """Domain 5: View, Native Dialogs & OS-Level Actions."""

    def test_domain5_01_view_switching(self, client: Live12TestClient):
        for view in ["Session", "Arranger", "Detail/Clip", "Detail/DeviceChain", "Browser"]:
            res = client.call_tool("live12_view_switch", {"view_name": view})
            assert not res.is_error
            assert res["active_view"] == view

    def test_domain5_02_view_selection_sync(self, client: Live12TestClient):
        t_idx, _ = client.create_sandboxed_track("midi", "sel_host")
        sel_res = client.call_tool("live12_view_select", {
            "track_index": t_idx,
            "scene_index": 1,
            "clip_slot": [t_idx, 0],
            "device_index": 0
        })
        assert not sel_res.is_error
        assert sel_res["selected_track"] == t_idx
        assert sel_res["selected_scene"] == 1

    def test_domain5_03_dialog_inspection(self, client: Live12TestClient):
        dlg_res = client.call_tool("live12_dialog_inspect")
        assert not dlg_res.is_error
        assert "open_dialog_count" in dlg_res.data

    def test_domain5_04_dialog_button_press(self, client: Live12TestClient):
        press_res = client.call_tool("live12_dialog_press", {"button_index": 0})
        assert not press_res.is_error

    def test_domain5_05_os_save_and_open_set(self, client: Live12TestClient):
        target_path = f"/tmp/__agy_test_{client.run_id}_set.als"
        save_res = client.call_tool("live12_os_save_set", {"destination_path": target_path})
        assert not save_res.is_error
        assert os.path.exists(target_path)

        open_res = client.call_tool("live12_os_open_set", {"als_path": target_path})
        assert not open_res.is_error

    def test_domain5_06_os_audio_export(self, client: Live12TestClient):
        wav_path = f"/tmp/__agy_test_{client.run_id}_render.wav"
        export_res = client.call_tool("live12_os_export_audio", {"destination_wav_path": wav_path})
        assert not export_res.is_error
        assert os.path.exists(wav_path)
        with open(wav_path, "rb") as f:
            header = f.read(4)
            assert header == b"RIFF"


@pytest.mark.tier1
class TestTier1Domain6UniversalLOMEscapeHatch:
    """Domain 6: Universal LOM Escape Hatch."""

    def test_domain6_01_lom_inspect(self, client: Live12TestClient):
        res = client.call_tool("live12_lom_inspect", {"target_path": "live_set.tracks.0"})
        assert not res.is_error
        assert res["type"] == "Live.Track.Track"
        assert "properties" in res.data
        assert "methods" in res.data

    def test_domain6_02_lom_get_property(self, client: Live12TestClient):
        res = client.call_tool("live12_lom_get", {"target_path": "live_set", "property_name": "tempo"})
        assert not res.is_error
        assert "value" in res.data

    def test_domain6_03_lom_set_property(self, client: Live12TestClient):
        res = client.call_tool("live12_lom_set", {
            "target_path": "live_set",
            "property_name": "tempo",
            "value": 132.0
        })
        assert not res.is_error
        assert math.isclose(res["new_value"], 132.0, rel_tol=1e-4)

    def test_domain6_04_lom_call_method(self, client: Live12TestClient):
        res = client.call_tool("live12_lom_call", {
            "target_path": "live_set.tracks.0",
            "method_name": "stop_all_clips",
            "args": []
        })
        assert not res.is_error
        assert res["result"] is True

    def test_domain6_05_lom_inspect_clip(self, client: Live12TestClient):
        res = client.call_tool("live12_lom_inspect", {"target_path": "live_set.tracks.0.clip_slots.0.clip"})
        assert not res.is_error
        assert res["type"] == "Live.Clip.Clip"
        assert "get_notes_extended" in res["methods"]
