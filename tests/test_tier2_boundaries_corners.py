"""
Tier 2: Boundaries, Corners & Resilience Test Suite
====================================================
Tests limits, edge cases, negative inputs, boundary values, out-of-range parameters,
empty clips, extreme durations, and error envelopes across all 6 domains:
- Domain 1: Boundaries & Negative Inputs (>= 5 tests)
- Domain 2: Invalid Addressing & Range Limits (>= 5 tests)
- Domain 3: Extended MIDI Extremes & Bounds (>= 5 tests)
- Domain 4: Non-Existent Devices & Macro Limits (>= 5 tests)
- Domain 5: View & Dialog Edge Cases (>= 5 tests)
- Domain 6: LOM Path Edge Cases & Pointer Resilience (>= 5 tests)
"""

import math
import pytest
from harness import Live12TestClient


@pytest.mark.tier2
class TestTier2Domain1TransportBoundaries:
    """Domain 1: Boundaries, Limits & Negative Inputs."""

    def test_domain1_b01_tempo_lower_bound_rejection(self, client: Live12TestClient):
        # Tempo < 20.0 should be rejected
        res = client.call_tool("live12_transport_set_tempo", {"tempo": 10.0})
        assert res.is_error
        assert "out of bounds" in str(res.data).lower()

    def test_domain1_b02_tempo_upper_bound_rejection(self, client: Live12TestClient):
        # Tempo > 999.0 should be rejected
        res = client.call_tool("live12_transport_set_tempo", {"tempo": 1000.0})
        assert res.is_error
        assert "out of bounds" in str(res.data).lower()

    def test_domain1_b03_tempo_exact_boundary_extremes(self, client: Live12TestClient):
        # Exact lower boundary: 20.0
        res_min = client.call_tool("live12_transport_set_tempo", {"tempo": 20.0})
        assert not res_min.is_error
        state_min = client.call_tool("live12_song_get_state")
        assert math.isclose(state_min["tempo"], 20.0, rel_tol=1e-4)

        # Exact upper boundary: 999.0
        res_max = client.call_tool("live12_transport_set_tempo", {"tempo": 999.0})
        assert not res_max.is_error
        state_max = client.call_tool("live12_song_get_state")
        assert math.isclose(state_max["tempo"], 999.0, rel_tol=1e-4)

    def test_domain1_b04_time_signature_invalid_values(self, client: Live12TestClient):
        # Invalid denominator 3 (must be power of 2: 1, 2, 4, 8, 16)
        res_denom = client.call_tool("live12_transport_set_time_signature", {"numerator": 4, "denominator": 3})
        assert res_denom.is_error

        # Zero numerator
        res_num = client.call_tool("live12_transport_set_time_signature", {"numerator": 0, "denominator": 4})
        assert res_num.is_error

    def test_domain1_b05_loop_zero_or_negative_length(self, client: Live12TestClient):
        res_zero = client.call_tool("live12_transport_set_loop", {"enabled": True, "start": 0.0, "length": 0.0})
        assert res_zero.is_error

        res_neg = client.call_tool("live12_transport_set_loop", {"enabled": True, "start": 0.0, "length": -4.0})
        assert res_neg.is_error

    def test_domain1_b06_scale_invalid_root_note_and_name(self, client: Live12TestClient):
        # Negative root note
        res_neg = client.call_tool("live12_song_set_scale", {"root_note": -1, "scale_name": "Major"})
        assert res_neg.is_error

        # Root note >= 12
        res_over = client.call_tool("live12_song_set_scale", {"root_note": 12, "scale_name": "Major"})
        assert res_over.is_error

        # Unknown scale name
        res_unknown = client.call_tool("live12_song_set_scale", {"root_note": 0, "scale_name": "KlingonScale"})
        assert res_unknown.is_error


@pytest.mark.tier2
class TestTier2Domain2TrackBoundaries:
    """Domain 2: Boundaries, Limits & Invalid Indices."""

    def test_domain2_b01_track_delete_invalid_index(self, client: Live12TestClient):
        res = client.call_tool("live12_track_delete", {"track_index": 9999})
        assert res.is_error
        assert "out of range" in str(res.data).lower()

    def test_domain2_b02_track_invalid_type_rejection(self, client: Live12TestClient):
        res = client.call_tool("live12_track_create", {"type": "synth"})
        assert res.is_error
        assert "invalid track type" in str(res.data).lower()

    def test_domain2_b03_mixer_volume_out_of_bounds(self, client: Live12TestClient):
        t_idx, _ = client.create_sandboxed_track("midi", "mix_bnd")
        # Volume > 1.0
        res_high = client.call_tool("live12_mixer_set", {"track_index": t_idx, "volume": 1.5})
        assert res_high.is_error

        # Volume < 0.0
        res_low = client.call_tool("live12_mixer_set", {"track_index": t_idx, "volume": -0.1})
        assert res_low.is_error

    def test_domain2_b04_mixer_pan_out_of_bounds(self, client: Live12TestClient):
        t_idx, _ = client.create_sandboxed_track("midi", "pan_bnd")
        # Pan > 1.0
        res_right = client.call_tool("live12_mixer_set", {"track_index": t_idx, "pan": 1.1})
        assert res_right.is_error

        # Pan < -1.0
        res_left = client.call_tool("live12_mixer_set", {"track_index": t_idx, "pan": -1.1})
        assert res_left.is_error

    def test_domain2_b05_routing_invalid_monitoring(self, client: Live12TestClient):
        t_idx, _ = client.create_sandboxed_track("midi", "route_bnd")
        res = client.call_tool("live12_routing_set", {"track_index": t_idx, "monitoring": "AlwaysOn"})
        assert res.is_error


@pytest.mark.tier2
class TestTier2Domain3ClipAndMIDIBoundaries:
    """Domain 3: Boundaries, Limits & Invalid Note Properties."""

    def test_domain3_b01_midi_pitch_lower_and_upper_rejection(self, client: Live12TestClient):
        t_idx, _ = client.create_sandboxed_track("midi", "pitch_bnd")
        client.call_tool("live12_clip_create", {"track_index": t_idx, "slot_index": 0})

        # Pitch < 0
        res_neg = client.call_tool("live12_clip_add_notes", {
            "track_index": t_idx,
            "slot_index": 0,
            "notes": [{"pitch": -1, "start_time": 0.0, "duration": 1.0}]
        })
        assert res_neg.is_error

        # Pitch > 127
        res_high = client.call_tool("live12_clip_add_notes", {
            "track_index": t_idx,
            "slot_index": 0,
            "notes": [{"pitch": 128, "start_time": 0.0, "duration": 1.0}]
        })
        assert res_high.is_error

    def test_domain3_b02_midi_pitch_exact_boundaries_accepted(self, client: Live12TestClient):
        t_idx, _ = client.create_sandboxed_track("midi", "pitch_extremes")
        client.call_tool("live12_clip_create", {"track_index": t_idx, "slot_index": 0})

        # Pitch 0 and Pitch 127
        res = client.call_tool("live12_clip_add_notes", {
            "track_index": t_idx,
            "slot_index": 0,
            "notes": [
                {"pitch": 0, "start_time": 0.0, "duration": 1.0},
                {"pitch": 127, "start_time": 1.0, "duration": 1.0}
            ]
        })
        assert not res.is_error
        assert res["added_count"] == 2

        notes = client.call_tool("live12_clip_get_notes", {"track_index": t_idx, "slot_index": 0})["notes"]
        pitches = {n["pitch"] for n in notes}
        assert pitches == {0, 127}

    def test_domain3_b03_probability_out_of_bounds_rejection(self, client: Live12TestClient):
        t_idx, _ = client.create_sandboxed_track("midi", "prob_bnd")
        client.call_tool("live12_clip_create", {"track_index": t_idx, "slot_index": 0})

        # Probability < 0.0
        res_low = client.call_tool("live12_clip_add_notes", {
            "track_index": t_idx,
            "slot_index": 0,
            "notes": [{"pitch": 60, "start_time": 0.0, "duration": 1.0, "probability": -0.1}]
        })
        assert res_low.is_error

        # Probability > 1.0
        res_high = client.call_tool("live12_clip_add_notes", {
            "track_index": t_idx,
            "slot_index": 0,
            "notes": [{"pitch": 60, "start_time": 0.0, "duration": 1.0, "probability": 1.5}]
        })
        assert res_high.is_error

    def test_domain3_b04_velocity_deviation_boundaries(self, client: Live12TestClient):
        t_idx, _ = client.create_sandboxed_track("midi", "vdev_bnd")
        client.call_tool("live12_clip_create", {"track_index": t_idx, "slot_index": 0})

        # Out of bounds: -128
        res_neg = client.call_tool("live12_clip_add_notes", {
            "track_index": t_idx,
            "slot_index": 0,
            "notes": [{"pitch": 60, "start_time": 0.0, "duration": 1.0, "velocity_deviation": -128.0}]
        })
        assert res_neg.is_error

        # Exact boundary: -127.0 and +127.0
        res_valid = client.call_tool("live12_clip_add_notes", {
            "track_index": t_idx,
            "slot_index": 0,
            "notes": [
                {"pitch": 60, "start_time": 0.0, "duration": 1.0, "velocity_deviation": -127.0},
                {"pitch": 62, "start_time": 1.0, "duration": 1.0, "velocity_deviation": 127.0}
            ]
        })
        assert not res_valid.is_error

    def test_domain3_b05_empty_clip_retrieval(self, client: Live12TestClient):
        t_idx, _ = client.create_sandboxed_track("midi", "empty_clip_host")
        client.call_tool("live12_clip_create", {"track_index": t_idx, "slot_index": 0})

        # Retrieve notes from empty clip
        res = client.call_tool("live12_clip_get_notes", {"track_index": t_idx, "slot_index": 0})
        assert not res.is_error
        assert res["notes_count"] == 0
        assert res["notes"] == []

    def test_domain3_b06_extreme_duration_and_timespan(self, client: Live12TestClient):
        t_idx, _ = client.create_sandboxed_track("midi", "extreme_duration")
        client.call_tool("live12_clip_create", {
            "track_index": t_idx,
            "slot_index": 0,
            "length_beats": 65536.0
        })

        res = client.call_tool("live12_clip_add_notes", {
            "track_index": t_idx,
            "slot_index": 0,
            "notes": [{"pitch": 60, "start_time": 65000.0, "duration": 500.0}]
        })
        assert not res.is_error


@pytest.mark.tier2
class TestTier2Domain4DeviceBoundaries:
    """Domain 4: Boundaries, Limits & Non-Existent Devices/Parameters."""

    def test_domain4_b01_device_load_invalid_track_index(self, client: Live12TestClient):
        res = client.call_tool("live12_browser_load_item", {
            "track_index": 9999,
            "browser_item_uri": "live:device:drift"
        })
        assert res.is_error
        assert "out of range" in str(res.data).lower()

    def test_domain4_b02_device_get_parameters_empty_track(self, client: Live12TestClient):
        t_idx, _ = client.create_sandboxed_track("midi", "empty_dev_track")
        res = client.call_tool("live12_device_get_parameters", {"track_index": t_idx, "device_index": 0})
        assert res.is_error

    def test_domain4_b03_device_set_nonexistent_parameter(self, client: Live12TestClient):
        t_idx, _ = client.create_sandboxed_track("midi", "nonexistent_param")
        client.call_tool("live12_browser_load_item", {"track_index": t_idx, "browser_item_uri": "live:device:drift"})

        res = client.call_tool("live12_device_set_parameter", {
            "track_index": t_idx,
            "device_index": 0,
            "parameter_identifier": "QuantumFluxCapacitor",
            "value": 100.0
        })
        assert res.is_error
        assert "not found" in str(res.data).lower()

    def test_domain4_b04_rack_macro_invalid_index(self, client: Live12TestClient):
        t_idx, _ = client.create_sandboxed_track("midi", "macro_bnd")
        client.call_tool("live12_browser_load_item", {"track_index": t_idx, "browser_item_uri": "live:device:audio_effect_rack"})

        # Macro 16 (out of range 0..15)
        res_high = client.call_tool("live12_rack_macro_control", {
            "track_index": t_idx,
            "device_index": 0,
            "macro_index": 16,
            "value": 0.5
        })
        assert res_high.is_error

    def test_domain4_b05_rack_variation_recall_nonexistent(self, client: Live12TestClient):
        t_idx, _ = client.create_sandboxed_track("midi", "var_bnd")
        client.call_tool("live12_browser_load_item", {"track_index": t_idx, "browser_item_uri": "live:device:audio_effect_rack"})

        res = client.call_tool("live12_rack_variation_control", {
            "track_index": t_idx,
            "device_index": 0,
            "action": "recall",
            "variation_index": 99
        })
        assert res.is_error


@pytest.mark.tier2
class TestTier2Domain5ViewAndOSBoundaries:
    """Domain 5: Boundaries & View Edge Cases."""

    def test_domain5_b01_view_invalid_name_rejection(self, client: Live12TestClient):
        res = client.call_tool("live12_view_switch", {"view_name": "VirtualRealityHolodeck"})
        assert res.is_error
        assert "invalid view name" in str(res.data).lower()

    def test_domain5_b02_dialog_press_no_open_dialogs(self, client: Live12TestClient):
        res = client.call_tool("live12_dialog_press", {"button_index": 0})
        assert not res.is_error
        assert res["status"] == "no_open_dialogs"

    def test_domain5_b03_view_select_arbitrary_indices(self, client: Live12TestClient):
        # Selecting out-of-range index should not crash the bridge
        res = client.call_tool("live12_view_select", {"track_index": 999, "scene_index": 999})
        assert not res.is_error

    def test_domain5_b04_os_save_set_nested_dir(self, client: Live12TestClient):
        nested_path = f"/tmp/__agy_test_{client.run_id}_nested/sub/set.als"
        res = client.call_tool("live12_os_save_set", {"destination_path": nested_path})
        assert not res.is_error
        assert res["exists"] is True

    def test_domain5_b05_os_export_audio_valid_output(self, client: Live12TestClient):
        wav_path = f"/tmp/__agy_test_{client.run_id}_test_audio.wav"
        res = client.call_tool("live12_os_export_audio", {"destination_wav_path": wav_path})
        assert not res.is_error
        assert res["valid_riff"] is True


@pytest.mark.tier2
class TestTier2Domain6LOMBoundaries:
    """Domain 6: Boundaries & Dynamic LOM Edge Cases."""

    def test_domain6_b01_lom_inspect_empty_path_rejection(self, client: Live12TestClient):
        res = client.call_tool("live12_lom_inspect", {"target_path": ""})
        assert res.is_error
        assert "empty" in str(res.data).lower()

    def test_domain6_b02_lom_get_property_default(self, client: Live12TestClient):
        res = client.call_tool("live12_lom_get", {"target_path": "unknown_path", "property_name": "unknown_prop"})
        assert not res.is_error
        assert res["value"] is None

    def test_domain6_b03_lom_call_custom_method(self, client: Live12TestClient):
        res = client.call_tool("live12_lom_call", {
            "target_path": "live_set",
            "method_name": "custom_echo",
            "args": ["hello", 123]
        })
        assert not res.is_error
        assert res["result"] == "ok"

    def test_domain6_b04_lom_set_tempo_numeric_cast(self, client: Live12TestClient):
        res = client.call_tool("live12_lom_set", {
            "target_path": "live_set",
            "property_name": "tempo",
            "value": "125.5"
        })
        assert not res.is_error
        assert math.isclose(res["new_value"], 125.5, rel_tol=1e-4)

    def test_domain6_b05_lom_inspect_song(self, client: Live12TestClient):
        res = client.call_tool("live12_lom_inspect", {"target_path": "live_set"})
        assert not res.is_error
        assert res["type"] == "Live.Song.Song"
        assert "tracks" in res["properties"]
