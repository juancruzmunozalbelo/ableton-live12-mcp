"""
Tier 5 Adversarial Hardening: Domain Boundaries & Parameter Extremes
====================================================================
Milestone 5 Phase 2: White-box code coverage and resilience audit for
the 61 Ableton Live 12 MCP tools and bridge handlers.

Covers:
1. Live 12 Extended MIDI note specifications (zero duration, negative pitch,
   velocity deviation bounds, probability limits 0.0 vs 1.0, NaN ingestion).
2. Specialized Live 12 devices (Wavetable modulation matrix cell extremes,
   Meld macro bounds, Roar stage filters, Drift voice modes).
3. TakeLane creation and comping on empty or invalid tracks.
4. Microtonal tuning system switching with special characters and scale anomalies.
5. Dynamic LOM escape hatch security (private attributes, dunders, pointer safety).
6. Transport and mixer boundary conditions (NaN tempo, non-integer send keys).
"""

from __future__ import annotations

import math
import os
import sys
from typing import Any, Dict, List, Optional

import pytest

# Ensure repo root and src are in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from ableton_live12_mcp.tools import ValidationError, validate_tool_call
from live12_bridge.bridge import Live12ControlSurface
from live12_bridge.handlers import BridgeHandlers
from live12_bridge.reflection import (
    dict_to_midi_note_spec,
    liveobj_valid,
    lom_call,
    lom_get,
    lom_inspect,
    lom_set,
    resolve_path,
    serialize_lom_value,
)
from tests.harness import MockAbletonBridge, MockNote


# ==============================================================================
# In-Memory Test Fixtures & Mocks
# ==============================================================================

class DummyCInstance:
    """Mock Ableton Live C++ host container."""
    def __init__(self):
        self.logs: List[str] = []

    def log_message(self, msg: str) -> None:
        self.logs.append(msg)

    def show_message(self, msg: str) -> None:
        pass

    def song(self) -> Any:
        return None


class DummySongWithInternals:
    """Simulates a live song with public properties and private internal attributes."""
    def __init__(self):
        self.tempo = 120.0
        self.scale_name = "Major"
        self._internal_secret_token = "live_secret_42"
        self._live_ptr = 0xCAFEBABE

    def safe_public_method(self) -> str:
        return "safe_output"

    def _internal_private_method(self) -> str:
        return "dangerous_leak"


# ==============================================================================
# 1. Live 12 Extended MIDI Note Specifications
# ==============================================================================

@pytest.mark.tier5
class TestTier5ExtendedMIDIBoundaries:
    """Empirical verification of Extended MIDI note boundary handling."""

    def test_note_zero_duration_rejection_validator(self):
        """Validator must reject zero duration note (exclusiveMinimum: 0.0)."""
        with pytest.raises(ValidationError):
            validate_tool_call(
                "live12_clip_add_notes",
                {
                    "track_index": 0,
                    "slot_index": 0,
                    "notes": [{"pitch": 60, "start_time": 0.0, "duration": 0.0}],
                },
            )

    def test_note_negative_duration_rejection_validator(self):
        """Validator must reject negative duration note."""
        with pytest.raises(ValidationError):
            validate_tool_call(
                "live12_clip_add_notes",
                {
                    "track_index": 0,
                    "slot_index": 0,
                    "notes": [{"pitch": 60, "start_time": 0.0, "duration": -1.5}],
                },
            )

    def test_note_zero_duration_bridge_gap(self):
        """
        Hardened Test (Gap 1.1): BridgeHandlers.live12_clip_add_notes validates
        duration > 0.0, rejecting zero duration with ValueError.
        """
        handlers = BridgeHandlers(DummyCInstance())
        with pytest.raises(ValueError):
            handlers.live12_clip_add_notes(
                track_index=0,
                slot_index=0,
                notes=[{"pitch": 60, "start_time": 0.0, "duration": 0.0}],
            )

    def test_note_negative_start_time_bridge_gap(self):
        """
        Hardened Test (Gap 1.2): BridgeHandlers validates start_time >= 0.0, rejecting negative start_time.
        """
        handlers = BridgeHandlers(DummyCInstance())
        with pytest.raises(ValueError):
            handlers.live12_clip_add_notes(
                track_index=0,
                slot_index=0,
                notes=[{"pitch": 60, "start_time": -2.0, "duration": 1.0}],
            )

    def test_note_velocity_deviation_exact_boundaries(self):
        """Velocity deviation must accept exact boundaries -127.0 and +127.0."""
        validate_tool_call(
            "live12_clip_add_notes",
            {
                "track_index": 0,
                "slot_index": 0,
                "notes": [
                    {"pitch": 60, "start_time": 0.0, "duration": 1.0, "velocity_deviation": -127.0},
                    {"pitch": 62, "start_time": 1.0, "duration": 1.0, "velocity_deviation": 127.0},
                ],
            },
        )

    def test_note_velocity_deviation_out_of_bounds(self):
        """Validator must reject velocity deviation < -127.0 or > 127.0."""
        with pytest.raises(ValidationError):
            validate_tool_call(
                "live12_clip_add_notes",
                {
                    "track_index": 0,
                    "slot_index": 0,
                    "notes": [{"pitch": 60, "start_time": 0.0, "duration": 1.0, "velocity_deviation": -127.1}],
                },
            )
        with pytest.raises(ValidationError):
            validate_tool_call(
                "live12_clip_add_notes",
                {
                    "track_index": 0,
                    "slot_index": 0,
                    "notes": [{"pitch": 60, "start_time": 0.0, "duration": 1.0, "velocity_deviation": 127.1}],
                },
            )

    def test_note_probability_exact_boundaries(self):
        """Probability must accept exact 0.0 and 1.0."""
        validate_tool_call(
            "live12_clip_add_notes",
            {
                "track_index": 0,
                "slot_index": 0,
                "notes": [
                    {"pitch": 60, "start_time": 0.0, "duration": 1.0, "probability": 0.0},
                    {"pitch": 64, "start_time": 1.0, "duration": 1.0, "probability": 1.0},
                ],
            },
        )

    def test_note_probability_out_of_bounds(self):
        """Validator must reject probability < 0.0 or > 1.0."""
        with pytest.raises(ValidationError):
            validate_tool_call(
                "live12_clip_add_notes",
                {
                    "track_index": 0,
                    "slot_index": 0,
                    "notes": [{"pitch": 60, "start_time": 0.0, "duration": 1.0, "probability": -0.01}],
                },
            )
        with pytest.raises(ValidationError):
            validate_tool_call(
                "live12_clip_add_notes",
                {
                    "track_index": 0,
                    "slot_index": 0,
                    "notes": [{"pitch": 60, "start_time": 0.0, "duration": 1.0, "probability": 1.01}],
                },
            )

    def test_note_modify_unbounded_parameters_gap(self):
        """
        Hardened Test (Gap 1.5): live12_clip_modify_notes rejects out-of-bound
        modifications (pitch=-5, probability=50.0, velocity_deviation=999.0) in handlers.
        """
        handlers = BridgeHandlers(DummyCInstance())
        with pytest.raises(ValueError):
            handlers.live12_clip_modify_notes(
                track_index=0,
                slot_index=0,
                note_modifications=[
                    {"note_id": 101, "pitch": -5, "probability": 50.0, "velocity_deviation": 999.0}
                ],
            )

    def test_nan_ingestion_in_validator_gap(self):
        """
        Hardened Test (Gap 1.6): IEEE 754 NaN is rejected by validator.py.
        """
        with pytest.raises(ValidationError):
            validate_tool_call(
                "live12_clip_add_notes",
                {
                    "track_index": 0,
                    "slot_index": 0,
                    "notes": [{"pitch": 60, "start_time": 0.0, "duration": 1.0, "probability": float("nan")}],
                },
            )


# ==============================================================================
# 2. Specialized Live 12 Devices (Wavetable, Meld, Roar, Drift)
# ==============================================================================

@pytest.mark.tier5
class TestTier5SpecializedDeviceBoundaries:
    """Stress tests specialized Live 12 instrument and effect interfaces."""

    def test_wavetable_matrix_amount_boundaries(self):
        """Wavetable matrix modulation depth accepted in [-1.0, 1.0], rejected outside."""
        validate_tool_call(
            "live12_wavetable_modulation_matrix",
            {"track_index": 0, "device_index": 0, "action": "set", "amount": -1.0},
        )
        validate_tool_call(
            "live12_wavetable_modulation_matrix",
            {"track_index": 0, "device_index": 0, "action": "set", "amount": 1.0},
        )
        with pytest.raises(ValidationError):
            validate_tool_call(
                "live12_wavetable_modulation_matrix",
                {"track_index": 0, "device_index": 0, "action": "set", "amount": 1.05},
            )

    def test_wavetable_matrix_handlers_missing_bounds_gap(self):
        """
        Hardened Test (Gap 2.1): BridgeHandlers rejects out-of-range amount with ValueError.
        """
        handlers = BridgeHandlers(DummyCInstance())
        with pytest.raises(ValueError):
            handlers.live12_wavetable_modulation_matrix(
                track_index=999,
                device_index=999,
                action="set",
                source="LFO 1",
                target="Filter 1 Freq",
                amount=999.0,
            )

    def test_meld_control_ghost_device_gap(self):
        """
        Adversarial Test (Gap 2.2): live12_meld_control succeeds on non-existent track and device.
        """
        handlers = BridgeHandlers(DummyCInstance())
        res = handlers.live12_meld_control(
            track_index=9999,
            device_index=9999,
            engine_params={"macro_a": -50.0, "macro_b": 100.0},
        )
        assert res.get("status") == "success"
        assert res.get("meld_params_updated") == 2

    def test_roar_control_unconstrained_schema_gap(self):
        """
        Adversarial Test (Gap 2.3): live12_roar_control schema allows arbitrary types in stage_params.
        """
        handlers = BridgeHandlers(DummyCInstance())
        res = handlers.live12_roar_control(
            track_index=9999,
            device_index=9999,
            stage_params={"stage": "invalid_mode", "drive": "not_a_number"},
        )
        assert res.get("status") == "success"
        assert res.get("roar_stages_updated") == 2

    def test_drift_control_ghost_device_gap(self):
        """
        Adversarial Test (Gap 2.4): live12_drift_control succeeds without verifying device presence.
        """
        handlers = BridgeHandlers(DummyCInstance())
        res = handlers.live12_drift_control(
            track_index=9999,
            device_index=9999,
            voice_params={"voice_mode": "non_existent_mode", "drift": 999.0},
        )
        assert res.get("status") == "success"
        assert res.get("drift_voice_updated") == 2


# ==============================================================================
# 3. TakeLane Creation and Comping Boundaries
# ==============================================================================

@pytest.mark.tier5
class TestTier5TakeLaneBoundaries:
    """Stress tests take lane comping, empty tracks, and region bounds."""

    def test_takelane_comp_invalid_track_gap(self):
        """
        Hardened Test (Gap 3.1): BridgeHandlers.live12_take_lane_comp_region rejects
        negative start and length with ValueError.
        """
        handlers = BridgeHandlers(DummyCInstance())
        with pytest.raises(ValueError):
            handlers.live12_take_lane_comp_region(
                track_index=999,
                lane_index=999,
                start=-10.0,
                length=-4.0,
            )

    def test_takelane_comp_empty_track_mock(self):
        """Verifies MockAbletonBridge rejects comping when track has 0 take lanes."""
        mock = MockAbletonBridge()
        mock._tool_live12_track_create(type="audio")  # track 0 has 0 take lanes
        with pytest.raises(IndexError):
            mock._tool_live12_take_lane_comp_region(track_index=0, lane_index=0, start=0.0, length=4.0)

    def test_takelane_comp_negative_bounds_mock_gap(self):
        """
        Hardened Test (Gap 3.2): MockAbletonBridge rejects negative start and length with ValueError.
        """
        mock = MockAbletonBridge()
        mock._tool_live12_track_create(type="audio")
        mock._tool_live12_take_lane_create(track_index=0)
        with pytest.raises(ValueError):
            mock._tool_live12_take_lane_comp_region(track_index=0, lane_index=0, start=-5.0, length=-2.0)


# ==============================================================================
# 4. Microtonal Tuning System Switching & Scale Anomalies
# ==============================================================================

@pytest.mark.tier5
class TestTier5MicrotonalTuningAndScale:
    """Adversarial stress testing of tuning systems and scale inputs."""

    def test_tuning_system_special_characters_accepted(self):
        """
        Hardened Test (Gap 4.1): BridgeHandlers rejects null bytes, path traversal,
        newlines, and massive buffers with ValueError.
        """
        handlers = BridgeHandlers(DummyCInstance())
        invalid_payloads = [
            "Tuning\x00WithNullByte",
            "../../etc/passwd",
            "Tuning\nWith\nNewlines",
            "A" * 10000,
            "",
            "   ",
        ]
        for p in invalid_payloads:
            with pytest.raises(ValueError):
                handlers.live12_song_set_tuning_system(tuning_name=p)
        valid_res = handlers.live12_song_set_tuning_system("19-EDO Piano")
        assert valid_res.get("status") == "loaded"
        assert valid_res.get("tuning_system") == "19-EDO Piano"

    def test_scale_lowercase_rejection(self):
        """live12_song_set_scale strictly rejects lowercase 'major'."""
        handlers = BridgeHandlers(DummyCInstance())
        with pytest.raises(ValueError):
            handlers.live12_song_set_scale(root_note=0, scale_name="major")

    def test_scale_whitespace_padded_rejection(self):
        """live12_song_set_scale rejects whitespace padded ' Major '."""
        handlers = BridgeHandlers(DummyCInstance())
        with pytest.raises(ValueError):
            handlers.live12_song_set_scale(root_note=0, scale_name=" Major ")

    def test_scale_root_note_boundaries(self):
        """Root note accepted in [0, 11], rejected outside."""
        handlers = BridgeHandlers(DummyCInstance())
        handlers.live12_song_set_scale(root_note=0, scale_name="Major")
        handlers.live12_song_set_scale(root_note=11, scale_name="Minor")
        with pytest.raises(ValueError):
            handlers.live12_song_set_scale(root_note=-1, scale_name="Major")
        with pytest.raises(ValueError):
            handlers.live12_song_set_scale(root_note=12, scale_name="Major")


# ==============================================================================
# 5. Dynamic LOM Escape Hatch Security & Reflection Integrity
# ==============================================================================

@pytest.mark.tier5
class TestTier5DynamicLOMEscapeHatchSecurity:
    """Security audit of LOM escape hatch reflection engine."""

    def test_lom_get_private_attribute_gap(self):
        """
        Hardened Test (Gap 5.1): lom_get rejects private attributes with PermissionError.
        """
        song = DummySongWithInternals()
        with pytest.raises(PermissionError):
            lom_get(lambda k: song, "live_set", "_internal_secret_token")

    def test_lom_get_dunder_attribute_gap(self):
        """
        Hardened Test (Gap 5.2): lom_get rejects dunder attributes with PermissionError.
        """
        song = DummySongWithInternals()
        with pytest.raises(PermissionError):
            lom_get(lambda k: song, "live_set", "__class__")

    def test_lom_set_private_attribute_gap(self):
        """
        Hardened Test (Gap 5.3): lom_set rejects mutating private internal attributes with PermissionError.
        """
        song = DummySongWithInternals()
        with pytest.raises(PermissionError):
            lom_set(lambda k: song, "live_set", "_internal_secret_token", "corrupted_state")

    def test_lom_call_private_method_gap(self):
        """
        Hardened Test (Gap 5.4): lom_call rejects invoking private methods with PermissionError.
        """
        song = DummySongWithInternals()
        with pytest.raises(PermissionError):
            lom_call(lambda k: song, "live_set", "_internal_private_method")

    def test_resolve_path_dunder_traversal_gap(self):
        """
        Hardened Test (Gap 5.5): resolve_path rejects traversing private/dunder attributes with PermissionError.
        """
        song = DummySongWithInternals()
        with pytest.raises(PermissionError):
            resolve_path(lambda k: song, "live_set.__class__.__name__")

    def test_mock_lom_get_nonexistent_property_gap(self):
        """
        Hardened Test (Gap 5.6): MockAbletonBridge raises AttributeError for non-existent property.
        """
        mock = MockAbletonBridge()
        with pytest.raises(AttributeError):
            mock._tool_live12_lom_get("live_set", "completely_non_existent_property_123")

    def test_mock_lom_call_nonexistent_method_gap(self):
        """
        Hardened Test (Gap 5.7): MockAbletonBridge raises AttributeError for non-existent method.
        """
        mock = MockAbletonBridge()
        with pytest.raises(AttributeError):
            mock._tool_live12_lom_call("live_set", "completely_non_existent_method_123")


# ==============================================================================
# 6. Transport and Mixer Boundaries (NaN & Non-Integer Keys)
# ==============================================================================

@pytest.mark.tier5
class TestTier5TransportAndMixerBoundaries:
    """Stress tests NaN ingestion and mixer parameter anomalies."""

    def test_nan_tempo_in_handlers_gap(self):
        """
        Hardened Test (Gap 6.1): BridgeHandlers.live12_transport_set_tempo rejects NaN tempo
        with ValueError.
        """
        handlers = BridgeHandlers(DummyCInstance())
        with pytest.raises(ValueError):
            handlers.live12_transport_set_tempo(float("nan"))

    def test_nan_tempo_in_validator_gap(self):
        """
        Hardened Test (Gap 6.2): Validator rejects NaN tempo with ValidationError.
        """
        with pytest.raises(ValidationError):
            validate_tool_call("live12_transport_set_tempo", {"tempo": float("nan")})

    def test_mixer_set_non_integer_send_key_crash_gap(self):
        """
        Hardened Test (Gap 6.3): live12_mixer_set parses return track label 'return_a'
        to send index 0 without crashing.
        """
        class MockParam:
            def __init__(self):
                self.value = 0.0

        class MockMixer:
            def __init__(self):
                self.sends = [MockParam(), MockParam()]

        class MockTrack:
            def __init__(self):
                self.mixer_device = MockMixer()

        class MockSong:
            def __init__(self):
                self.tracks = [MockTrack()]

        class MockCS:
            def song(self):
                return MockSong()

        cs = MockCS()
        song = cs.song()
        handlers = BridgeHandlers(cs)
        handlers.song = lambda: song
        res = handlers.live12_mixer_set(track_index=0, sends={"return_a": 0.5})
        assert "sends" in res
        assert res["sends"]["0"] == 0.5
        assert song.tracks[0].mixer_device.sends[0].value == 0.5
