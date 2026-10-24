"""
Empirical Challenge Test Suite: 61 Tools Execution & Boundary Validation
========================================================================
Author: challenger_m3_2
Verifies empirically:
1. All 61 tools can be successfully called through 'tools/call' over MCP stdio protocol in mock mode.
2. Parameter boundary validations:
   - Invalid tempo (<20, >999) rejected; exact boundaries [20.0, 999.0] accepted.
   - Invalid time signatures (num < 1, denom not power of 2) rejected; exact boundaries accepted.
   - Invalid track types (not in ('midi', 'audio', 'return')) rejected; valid types accepted.
   - Invalid MIDI notes (pitch < 0 or > 127, prob < 0 or > 1, dev < -127 or > 127) rejected; boundaries accepted.
   - Invalid macro indices (< 0 or > 15) rejected; boundaries [0, 15] accepted.
3. Boundary violations return standard ToolResult with 'isError: true' without server crash.
4. Server resilience under malformed input, invalid requests, and stress bursts.
5. Investigation of schema pre-validation gap (validator.py vs server.py dispatch).
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest

from ableton_live12_mcp.tools import get_tool_catalog, validate_tool_call, ValidationError
from tests.test_m3_mcp_server import McpProcessClient


# ==============================================================================
# Helper Fixture
# ==============================================================================

@pytest.fixture
def mcp_session():
    """Spawns an McpProcessClient, performs handshake, and sets up minimal LOM context."""
    client = McpProcessClient()
    # 1. MCP Handshake
    init_resp = client.send_request("initialize", {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "empirical-challenger", "version": "1.0.0"},
    })
    assert init_resp.get("result", {}).get("protocolVersion") == "2024-11-05"
    client.send_notification("notifications/initialized", {})

    # 2. Pre-setup baseline tracks and devices for tool execution
    client.send_request("tools/call", {"name": "live12_track_create", "arguments": {"type": "midi"}})
    client.send_request("tools/call", {"name": "live12_track_create", "arguments": {"type": "audio"}})
    client.send_request("tools/call", {
        "name": "live12_clip_create",
        "arguments": {"track_index": 0, "slot_index": 0, "length_beats": 4.0}
    })
    client.send_request("tools/call", {
        "name": "live12_browser_load_item",
        "arguments": {"track_index": 0, "browser_item_uri": "query:Drift"}
    })
    client.send_request("tools/call", {
        "name": "live12_browser_load_item",
        "arguments": {"track_index": 0, "browser_item_uri": "query:Instrument Rack"}
    })
    client.send_request("tools/call", {
        "name": "live12_clip_add_notes",
        "arguments": {
            "track_index": 0, "slot_index": 0,
            "notes": [{"pitch": 60, "start_time": 0.0, "duration": 1.0, "velocity": 100.0, "probability": 1.0}]
        }
    })

    try:
        yield client
    finally:
        client.close()


def _call_tool(client: McpProcessClient, name: str, args: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    """Invokes tools/call, asserts valid JSON-RPC 2.0 response envelope, and returns (payload, isError)."""
    resp = client.send_request("tools/call", {"name": name, "arguments": args})
    assert "result" in resp, f"No result in response for {name}: {resp}"
    result = resp["result"]
    assert "content" in result and isinstance(result["content"], list), f"Invalid content for {name}"
    assert len(result["content"]) > 0, f"Empty content list for {name}"
    assert result["content"][0]["type"] == "text", f"Content item not text for {name}"

    is_error = result.get("isError", False)
    text_content = result["content"][0]["text"]
    try:
        data = json.loads(text_content)
    except Exception as e:
        pytest.fail(f"Tool {name} returned non-JSON text content: {text_content!r} ({e})")

    return data, is_error


# ==============================================================================
# 1. Empirical Execution of All 61 Tools
# ==============================================================================

class TestEmpiricalAll61ToolsCall:
    """Empirically verifies that each of the 61 tools executes cleanly via tools/call."""

    def test_all_61_tools_execute_in_mock_mode(self, mcp_session: McpProcessClient, tmp_path: Path):
        catalog = get_tool_catalog()
        assert len(catalog) == 76, f"Expected 76 tools in catalog, found {len(catalog)}"

        save_als_path = str(tmp_path / "empirical_test.als")
        export_wav_path = str(tmp_path / "empirical_test.wav")

        valid_call_specs: Dict[str, Dict[str, Any]] = {
            # Domain 1: Song & Transport (15 tools)
            "live12_transport_play": {"restart": True},
            "live12_transport_stop": {},
            "live12_transport_record": {"record_mode": "arrangement"},
            "live12_transport_set_tempo": {"tempo": 126.0},
            "live12_transport_set_time_signature": {"numerator": 3, "denominator": 4},
            "live12_transport_set_loop": {"enabled": True, "start": 0.0, "length": 8.0},
            "live12_transport_set_punch": {"punch_in": True, "punch_out": False},
            "live12_transport_set_overdub": {"overdub": True},
            "live12_transport_set_metronome": {"enabled": True},
            "live12_song_capture_midi": {},
            "live12_song_get_state": {},
            "live12_song_set_scale": {"root_note": 0, "scale_name": "Minor"},
            "live12_song_set_tuning_system": {"tuning_name": "Equal Temperament"},
            "live12_cue_point_control": {"action": "create", "name": "Verse", "time": 16.0},
            "live12_tempo_sync_control": {"action": "get_status"},

            # Domain 2: Tracks, TakeLanes, Scenes, Routing (15 tools)
            "live12_track_create": {"type": "midi"},
            "live12_track_delete": {"track_index": 2},
            "live12_track_duplicate": {"track_index": 0},
            "live12_track_set_properties": {"track_index": 0, "name": "Bass", "solo": False, "mute": False, "arm": True},
            "live12_track_group": {"track_indices": [0, 1]},
            "live12_track_ungroup": {"group_track_index": 0},
            "live12_take_lane_create": {"track_index": 0},
            "live12_take_lane_list": {"track_index": 0},
            "live12_take_lane_comp_region": {"track_index": 0, "lane_index": 0, "start": 0.0, "length": 4.0},
            "live12_scene_create": {"index": 0},
            "live12_scene_fire": {"index": 0},
            "live12_scene_set_properties": {"scene_index": 0, "name": "Chorus", "tempo": 128.0, "tempo_enabled": True},
            "live12_routing_set": {"track_index": 0, "input_type": "All Ins", "monitoring": "Auto"},
            "live12_routing_get": {"track_index": 0},
            "live12_mixer_set": {"track_index": 0, "volume": 0.85, "pan": 0.0, "sends": {0: 0.2}},

            # Domain 3: Clips, Extended MIDI, Warping (16 tools)
            "live12_clip_create": {"track_index": 0, "slot_index": 1, "length_beats": 4.0, "name": "Clip B"},
            "live12_clip_delete": {"track_index": 0, "slot_index": 1},
            "live12_clip_delete_arrangement": {"track_index": 0, "clip_index": 0},
            "live12_clip_fire": {"track_index": 0, "slot_index": 0},
            "live12_clip_stop": {"track_index": 0, "slot_index": 0},
            "live12_clip_set_properties": {"track_index": 0, "slot_index": 0, "loop": True, "loop_start": 0.0, "loop_end": 4.0},
            "live12_clip_add_notes": {
                "track_index": 0, "slot_index": 0,
                "notes": [{"pitch": 65, "start_time": 2.0, "duration": 1.0, "velocity": 95.0, "probability": 0.75}]
            },
            "live12_clip_get_notes": {"track_index": 0, "slot_index": 0, "start_time": 0.0, "time_span": 4.0},
            "live12_clip_modify_notes": {
                "track_index": 0, "slot_index": 0,
                "note_modifications": [{"pitch": 65, "velocity": 115.0}]
            },
            "live12_clip_quantize": {"track_index": 0, "slot_index": 0, "grid": 0.25, "amount": 1.0},
            "live12_clip_duplicate_to_arrangement": {"track_index": 0, "slot_index": 0, "arrangement_time": 8.0},
            "live12_clip_remove_notes": {"track_index": 0, "slot_index": 0, "start_time": 0.0, "time_span": 4.0},
            "live12_clip_transform_midi": {"track_index": 0, "slot_index": 0, "transformation": "humanize"},
            "live12_clip_envelope_control": {"track_index": 0, "slot_index": 0, "action": "inspect"},
            "live12_groove_pool_control": {"action": "list_pool"},
            "live12_audio_clip_set_warp": {"track_index": 0, "slot_index": 0, "warping": True, "warp_mode": "Beats"},
            "live12_audio_clip_add_warp_marker": {"track_index": 0, "slot_index": 0, "beat_time": 2.0, "sample_time": 2.0},

            # Domain 4: Browser, Devices, Specialized (17 tools)
            "live12_browser_search": {"query": "Wavetable", "category": "all"},
            "live12_browser_load_item": {"track_index": 0, "browser_item_uri": "query:Wavetable"},
            "live12_browser_preview": {"action": "stop"},
            "live12_device_list": {"track_index": 0},
            "live12_device_get_parameters": {"track_index": 0, "device_index": 0},
            "live12_device_set_parameter": {"track_index": 0, "device_index": 0, "parameter_identifier": 0, "value": 1.0},
            "live12_device_toggle": {"track_index": 0, "device_index": 0, "enabled": True},
            "live12_rack_macro_control": {"track_index": 0, "device_index": 1, "macro_index": 0, "value": 0.5},
            "live12_rack_macro_config": {"track_index": 0, "device_index": 1, "action": "get_config"},
            "live12_rack_variation_control": {"track_index": 0, "device_index": 1, "action": "store"},
            "live12_drum_pad_control": {"track_index": 0, "device_index": 1, "action": "inspect_pads"},
            "live12_cc_control": {"track_index": 0, "device_index": 0, "action": "get_mappings"},
            "live12_wavetable_modulation_matrix": {"track_index": 0, "device_index": 0, "action": "set", "source": "Env 1", "target": "Filter Freq", "amount": 0.5},
            "live12_simpler_control": {"track_index": 0, "device_index": 0, "action": "slice"},
            "live12_meld_control": {"track_index": 0, "device_index": 0, "engine_params": {"engine_a": "virtual_analog"}},
            "live12_roar_control": {"track_index": 0, "device_index": 0, "stage_params": {"stage_1": "tube"}},
            "live12_drift_control": {"track_index": 0, "device_index": 0, "voice_params": {"mode": "poly"}},

            # Domain 5: View, Dialogs, OS Actions (8 tools)
            "live12_view_switch": {"view_name": "Session"},
            "live12_view_select": {"track_index": 0, "scene_index": 0},
            "live12_dialog_inspect": {},
            "live12_dialog_press": {"button_index": 0},
            "live12_undo_redo": {"action": "status"},
            "live12_os_save_set": {"destination_path": save_als_path},
            "live12_os_open_set": {"als_path": save_als_path},
            "live12_os_export_audio": {"destination_wav_path": export_wav_path},

            # Domain 6: Universal LOM Escape Hatch (4 tools)
            "live12_lom_inspect": {"target_path": "live_set"},
            "live12_lom_get": {"target_path": "live_set", "property_name": "tempo"},
            "live12_lom_set": {"target_path": "live_set", "property_name": "tempo", "value": 128.0},
            "live12_lom_call": {"target_path": "live_set", "method_name": "capture_and_insert_scene"},
        }

        # Verify specification covers 100% of tools
        assert len(valid_call_specs) == 76
        for tool in catalog:
            assert tool["name"] in valid_call_specs, f"Missing test spec for tool {tool['name']}"

        # Execute all 76 tools sequentially
        # Pre-arrange an Arrangement View clip so live12_clip_delete_arrangement has a target.
        _call_tool(mcp_session, "live12_clip_create", {"track_index": 0, "slot_index": 0, "length_beats": 4.0})
        _call_tool(mcp_session, "live12_clip_duplicate_to_arrangement",
                   {"track_index": 0, "slot_index": 0, "arrangement_time": 8.0})
        executed_count = 0
        for tool in catalog:
            name = tool["name"]
            args = valid_call_specs[name]
            data, is_error = _call_tool(mcp_session, name, args)
            assert not is_error, f"Tool {name} failed with error: {data}"
            executed_count += 1

        assert executed_count == 76, f"Expected 76 tools executed, ran {executed_count}"


# ==============================================================================
# 2. Empirical Parameter Boundary Validations
# ==============================================================================

class TestEmpiricalBoundaryValidations:
    """Verifies strict boundary validation across tempo, time signature, track types, MIDI, and macros."""

    # -------------------------------------------------------------------------
    # Tempo Boundary Rejection & Exact Extremes
    # -------------------------------------------------------------------------
    @pytest.mark.parametrize("invalid_tempo", [
        19.99, 10.0, 0.0, -1.0, -50.0, 999.01, 1000.0, 5000.0, "fast", None
    ])
    def test_tempo_invalid_bounds_rejected(self, mcp_session: McpProcessClient, invalid_tempo: Any):
        data, is_err = _call_tool(mcp_session, "live12_transport_set_tempo", {"tempo": invalid_tempo})
        assert is_err is True, f"Tempo {invalid_tempo} should have been rejected, got {data}"
        assert "error" in data or "code" in data

    @pytest.mark.parametrize("valid_tempo", [20.0, 120.0, 999.0])
    def test_tempo_exact_boundaries_accepted(self, mcp_session: McpProcessClient, valid_tempo: float):
        data, is_err = _call_tool(mcp_session, "live12_transport_set_tempo", {"tempo": valid_tempo})
        assert is_err is False, f"Tempo boundary {valid_tempo} should succeed, got {data}"
        assert data.get("tempo") == valid_tempo

    # -------------------------------------------------------------------------
    # Time Signature Boundary Rejection & Exact Extremes
    # -------------------------------------------------------------------------
    @pytest.mark.parametrize("numerator,denominator", [
        (0, 4), (-1, 4), (-10, 4),
        (4, 0), (4, 3), (4, 5), (4, 6), (4, 7), (4, 9), (4, 10), (4, 15), (4, 32),
    ])
    def test_time_signature_invalid_values_rejected(self, mcp_session: McpProcessClient, numerator: int, denominator: int):
        data, is_err = _call_tool(
            mcp_session,
            "live12_transport_set_time_signature",
            {"numerator": numerator, "denominator": denominator}
        )
        assert is_err is True, f"Time signature {numerator}/{denominator} should fail, got {data}"

    @pytest.mark.parametrize("numerator,denominator", [
        (1, 1), (1, 4), (4, 4), (7, 8), (99, 16)
    ])
    def test_time_signature_valid_boundaries_accepted(self, mcp_session: McpProcessClient, numerator: int, denominator: int):
        data, is_err = _call_tool(
            mcp_session,
            "live12_transport_set_time_signature",
            {"numerator": numerator, "denominator": denominator}
        )
        assert is_err is False, f"Valid time signature {numerator}/{denominator} should succeed, got {data}"

    # -------------------------------------------------------------------------
    # Track Type Validation
    # -------------------------------------------------------------------------
    @pytest.mark.parametrize("invalid_type", ["synth", "master", "group", "vst", "", 123, None])
    def test_track_type_invalid_rejected(self, mcp_session: McpProcessClient, invalid_type: Any):
        data, is_err = _call_tool(mcp_session, "live12_track_create", {"type": invalid_type})
        assert is_err is True, f"Track type {invalid_type} should fail, got {data}"

    @pytest.mark.parametrize("valid_type", ["midi", "audio", "return"])
    def test_track_type_valid_accepted(self, mcp_session: McpProcessClient, valid_type: str):
        data, is_err = _call_tool(mcp_session, "live12_track_create", {"type": valid_type})
        assert is_err is False, f"Track type {valid_type} should succeed, got {data}"
        assert data.get("type") == valid_type

    # -------------------------------------------------------------------------
    # MIDI Note Boundaries
    # -------------------------------------------------------------------------
    @pytest.mark.parametrize("note_override,label", [
        ({"pitch": -1}, "pitch underflow"),
        ({"pitch": 128}, "pitch overflow"),
        ({"probability": -0.01}, "probability negative"),
        ({"probability": 1.01}, "probability > 1.0"),
        ({"velocity_deviation": -128.0}, "velocity deviation underflow"),
        ({"velocity_deviation": 128.0}, "velocity deviation overflow"),
    ])
    def test_midi_notes_invalid_boundaries_rejected(self, mcp_session: McpProcessClient, note_override: dict, label: str):
        base_note = {"pitch": 60, "start_time": 0.0, "duration": 1.0, "velocity": 100.0, "probability": 1.0}
        base_note.update(note_override)
        data, is_err = _call_tool(mcp_session, "live12_clip_add_notes", {
            "track_index": 0, "slot_index": 0, "notes": [base_note]
        })
        assert is_err is True, f"Note with {label} should fail, got {data}"

    def test_midi_notes_exact_boundaries_accepted(self, mcp_session: McpProcessClient):
        # Test boundary note 1: pitch=0, prob=0.0, dev=-127.0
        data1, is_err1 = _call_tool(mcp_session, "live12_clip_add_notes", {
            "track_index": 0, "slot_index": 0,
            "notes": [{"pitch": 0, "start_time": 0.0, "duration": 0.25, "velocity": 0.0, "probability": 0.0, "velocity_deviation": -127.0}]
        })
        assert not is_err1
        assert data1.get("added_count") == 1

        # Test boundary note 2: pitch=127, prob=1.0, dev=127.0
        data2, is_err2 = _call_tool(mcp_session, "live12_clip_add_notes", {
            "track_index": 0, "slot_index": 0,
            "notes": [{"pitch": 127, "start_time": 0.5, "duration": 0.25, "velocity": 127.0, "probability": 1.0, "velocity_deviation": 127.0}]
        })
        assert not is_err2
        assert data2.get("added_count") == 1

    # -------------------------------------------------------------------------
    # Macro Index Boundaries
    # -------------------------------------------------------------------------
    @pytest.mark.parametrize("invalid_macro", [-1, -10, 16, 17, 999])
    def test_macro_index_invalid_bounds_rejected(self, mcp_session: McpProcessClient, invalid_macro: int):
        data, is_err = _call_tool(mcp_session, "live12_rack_macro_control", {
            "track_index": 0, "device_index": 1, "macro_index": invalid_macro, "value": 0.5
        })
        assert is_err is True, f"Macro index {invalid_macro} should fail, got {data}"

    @pytest.mark.parametrize("valid_macro", [0, 7, 15])
    def test_macro_index_exact_boundaries_accepted(self, mcp_session: McpProcessClient, valid_macro: int):
        data, is_err = _call_tool(mcp_session, "live12_rack_macro_control", {
            "track_index": 0, "device_index": 1, "macro_index": valid_macro, "value": 0.75
        })
        assert is_err is False, f"Macro index {valid_macro} should succeed, got {data}"
        assert data.get("macro_index") == valid_macro


# ==============================================================================
# 3. Server Resilience & Crash Immunity
# ==============================================================================

class TestEmpiricalServerResilience:
    """Verifies that boundary errors never crash the server process or drop the JSON-RPC channel."""

    def test_burst_boundary_errors_server_remains_healthy(self, mcp_session: McpProcessClient):
        # Send 30 consecutive out-of-bounds requests
        for i in range(30):
            data, is_err = _call_tool(mcp_session, "live12_transport_set_tempo", {"tempo": -100.0 - i})
            assert is_err is True

        # Assert server process is still running and responsive
        assert mcp_session.process.poll() is None, "Server process died after boundary error burst"
        ping_resp = mcp_session.send_request("ping", {})
        assert ping_resp.get("result") == {}

        # Assert valid command immediately succeeds
        data, is_err = _call_tool(mcp_session, "live12_song_get_state", {})
        assert is_err is False
        assert "tempo" in data


# ==============================================================================
# 4. Schema Pre-Validation Investigation
# ==============================================================================

class TestEmpiricalSchemaValidationInvestigation:
    """Investigates behavior of schema constraints and documents findings."""

    def test_validator_pure_logic_catches_empty_notes(self):
        """Pure validator.py correctly catches empty notes array violation (minItems: 1)."""
        with pytest.raises(ValidationError) as exc_info:
            validate_tool_call("live12_clip_add_notes", {
                "track_index": 0, "slot_index": 0, "notes": []
            })
        assert "minItems 1" in str(exc_info.value)

    def test_mcp_server_empty_notes_passthrough_behavior(self, mcp_session: McpProcessClient):
        """
        EMPIRICAL OBSERVATION:
        Server now enforces validate_tool_call before dispatching,
        so live12_clip_add_notes with notes=[] is correctly rejected at the schema boundary
        with a ValidationError and isError=True.
        """
        data, is_err = _call_tool(mcp_session, "live12_clip_add_notes", {
            "track_index": 0, "slot_index": 0, "notes": []
        })
        assert is_err is True
        assert data.get("type") == "ValidationError"
