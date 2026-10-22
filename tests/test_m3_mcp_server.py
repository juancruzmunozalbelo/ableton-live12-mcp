"""
Milestone 3 Automated Test Suite: MCP Server Protocol, 61 Tools & Antigravity Registration
==========================================================================================
Validates:
1. MCP Stdio Protocol Handshake:
   - 'initialize' returns protocolVersion 2024-11-05, serverInfo, and tools capabilities.
   - 'notifications/initialized' is accepted silently without response.
   - 'ping' returns empty result envelope.
2. Complete 61-Tool Catalog & Schema Integrity:
   - 'tools/list' returns all 61 tools.
   - Every inputSchema strictly conforms to JSON Schema Draft-07 (via Draft7Validator).
   - Tool names, descriptions, and parameter boundaries match LOM capabilities.
3. Multi-Domain Tool Execution ('tools/call'):
   - Exercises representative tools across all 6 domains.
   - Asserts ToolResult envelope structure (content with text JSON, isError boolean).
4. Error Handling:
   - Application/LOM errors return isError=True inside ToolResult without connection drop.
   - Protocol parse errors return JSON-RPC -32700.
   - Invalid requests return JSON-RPC -32600.
   - Method not found returns JSON-RPC -32601.
   - Out-of-bounds parameter rejection.
5. Registration Script Verification:
   - Programmatic execution of scripts/register_mcp.py (--check, --register, --unregister).
   - Idempotency, atomic file modification, and preservation of existing servers.
6. Process Lifecycle:
   - Clean shutdown upon EOF on stdin and SIGTERM.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest
from jsonschema import Draft7Validator

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from ableton_live12_mcp.tools import (
    TOOL_MAP,
    ValidationError,
    validate_argument_dict,
    validate_tool_call,
)

REGISTER_SCRIPT = REPO_ROOT / "scripts" / "register_mcp.py"


# ==============================================================================
# MCP Stdio Process Test Client
# ==============================================================================

class McpProcessClient:
    """Spawns ableton_live12_mcp as a subprocess communicating via stdio JSON-RPC 2.0."""

    def __init__(self, env: Optional[Dict[str, str]] = None, mock_mode: bool = True):
        self.req_id = 0
        process_env = os.environ.copy()
        process_env["PYTHONPATH"] = f"{REPO_ROOT / 'src'}:{REPO_ROOT}:{process_env.get('PYTHONPATH', '')}"
        if mock_mode:
            process_env["ABLETON_TEST_MODE"] = "mock"  # Offline deterministic fallback
        else:
            process_env.pop("ABLETON_TEST_MODE", None)
            process_env.pop("ABLETON_BRIDGE_HOST", None)
            process_env.pop("ABLETON_BRIDGE_PORT", None)
        if env:
            process_env.update(env)

        cmd = [sys.executable, "-m", "ableton_live12_mcp"]
        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # Line-buffered
            cwd=str(REPO_ROOT),
            env=process_env,
        )

    def send_raw(self, line: str) -> Optional[str]:
        """Writes line to stdin and reads single line response from stdout."""
        assert self.process.stdin is not None
        assert self.process.stdout is not None
        self.process.stdin.write(line.strip() + "\n")
        self.process.stdin.flush()
        resp_line = self.process.stdout.readline()
        return resp_line.strip() if resp_line else None

    def send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Sends a JSON-RPC 2.0 request and returns the parsed response dict."""
        self.req_id += 1
        req_id = self.req_id
        req = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params if params is not None else {},
        }
        raw_resp = self.send_raw(json.dumps(req))
        assert raw_resp, f"Empty response received for request {method}"
        resp = json.loads(raw_resp)
        assert resp.get("jsonrpc") == "2.0"
        assert resp.get("id") == req_id
        return resp

    def send_notification(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        """Sends a JSON-RPC 2.0 notification (no id) without expecting a response."""
        assert self.process.stdin is not None
        req = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params if params is not None else {},
        }
        self.process.stdin.write(json.dumps(req) + "\n")
        self.process.stdin.flush()

    def close(self) -> Tuple[int, str]:
        """Closes stdin, waits for process exit, and returns (exit_code, stderr)."""
        if self.process.poll() is None:
            if self.process.stdin:
                try:
                    self.process.stdin.close()
                except Exception:
                    pass
            try:
                self.process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=1.0)
        stderr_output = self.process.stderr.read() if self.process.stderr else ""
        return self.process.returncode, stderr_output


@pytest.fixture
def mcp_client():
    """Yields an active McpProcessClient and guarantees clean process teardown."""
    client = McpProcessClient()
    try:
        yield client
    finally:
        client.close()


# ==============================================================================
# Test Class 1: MCP Stdio Protocol Handshake & Core Methods
# ==============================================================================

class TestMcpProtocolHandshake:
    """Verifies MCP protocol initialization, ping, notifications, and version negotiation."""

    def test_initialize_handshake(self, mcp_client: McpProcessClient):
        resp = mcp_client.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "antigravity-test", "version": "1.0.0"},
        })
        assert "result" in resp
        result = resp["result"]
        assert result.get("protocolVersion") == "2024-11-05"
        assert "tools" in result.get("capabilities", {})
        assert result.get("serverInfo", {}).get("name") == "ableton-live12-mcp"
        assert result.get("serverInfo", {}).get("version") == "1.0.0"

    def test_initialized_notification_handled_silently(self, mcp_client: McpProcessClient):
        # 1. Initialize
        mcp_client.send_request("initialize", {"protocolVersion": "2024-11-05"})
        # 2. Notification (must not block or produce response)
        mcp_client.send_notification("notifications/initialized", {})
        # 3. Subsequent request succeeds immediately
        ping_resp = mcp_client.send_request("ping", {})
        assert ping_resp.get("result") == {}

    def test_ping(self, mcp_client: McpProcessClient):
        resp = mcp_client.send_request("ping", {})
        assert "result" in resp
        assert resp["result"] == {}


# ==============================================================================
# Test Class 2: Complete 61-Tool Catalog & JSON Schema Draft-07 Validation
# ==============================================================================

class TestMcpToolsList:
    """Verifies tools/list returns all 61 tools with valid Draft-07 schemas."""

    def test_tools_list_total_count(self, mcp_client: McpProcessClient):
        resp = mcp_client.send_request("tools/list", {})
        assert "result" in resp
        tools = resp["result"].get("tools", [])
        assert len(tools) == 75, f"Expected 75 tools, found {len(tools)}"

    def test_all_tools_pass_draft7_metaschema_validation(self, mcp_client: McpProcessClient):
        resp = mcp_client.send_request("tools/list", {})
        tools = resp["result"]["tools"]
        for tool in tools:
            name = tool.get("name")
            assert name and isinstance(name, str), f"Invalid tool name in {tool}"
            assert name.startswith("live12_"), f"Tool name '{name}' must start with 'live12_'"
            assert tool.get("description"), f"Tool '{name}' lacks description"

            schema = tool.get("inputSchema")
            assert schema, f"Tool '{name}' lacks inputSchema"
            assert schema.get("type") == "object", f"Tool '{name}' inputSchema must be type object"
            assert "properties" in schema, f"Tool '{name}' inputSchema lacks properties"

            # Strict Draft-07 schema validation
            Draft7Validator.check_schema(schema)

    def test_domain_distribution_exact_counts(self, mcp_client: McpProcessClient):
        resp = mcp_client.send_request("tools/list", {})
        tools = resp["result"]["tools"]
        names = {t["name"] for t in tools}
        assert len(names) == 75, "Found duplicate tool names"

        domain_tools = {
            "Domain 1: Song & Transport (15 tools)": [
                "live12_transport_play", "live12_transport_stop", "live12_transport_record",
                "live12_transport_set_tempo", "live12_transport_set_time_signature",
                "live12_transport_set_metronome", "live12_transport_set_loop",
                "live12_transport_set_punch", "live12_transport_set_overdub",
                "live12_song_capture_midi", "live12_song_get_state",
                "live12_song_set_scale", "live12_song_set_tuning_system",
                "live12_cue_point_control", "live12_tempo_sync_control",
            ],
            "Domain 2: Tracks, TakeLanes, Scenes, Routing (15 tools)": [
                "live12_track_create", "live12_track_delete", "live12_track_duplicate",
                "live12_track_set_properties", "live12_track_group", "live12_track_ungroup",
                "live12_take_lane_create", "live12_take_lane_list", "live12_take_lane_comp_region",
                "live12_scene_create", "live12_scene_fire", "live12_scene_set_properties",
                "live12_routing_set", "live12_routing_get", "live12_mixer_set",
            ],
            "Domain 3: Clips, Extended MIDI, Warping (16 tools)": [
                "live12_clip_create", "live12_clip_delete", "live12_clip_fire",
                "live12_clip_stop", "live12_clip_set_properties", "live12_clip_add_notes",
                "live12_clip_get_notes", "live12_clip_modify_notes", "live12_clip_quantize",
                "live12_clip_duplicate_to_arrangement", "live12_clip_remove_notes",
                "live12_clip_transform_midi", "live12_clip_envelope_control",
                "live12_groove_pool_control",
                "live12_audio_clip_set_warp", "live12_audio_clip_add_warp_marker",
            ],
            "Domain 4: Browser, Devices, Specialized (17 tools)": [
                "live12_browser_search", "live12_browser_load_item", "live12_browser_preview",
                "live12_device_list", "live12_device_get_parameters", "live12_device_set_parameter",
                "live12_device_toggle", "live12_rack_macro_control", "live12_rack_macro_config",
                "live12_rack_variation_control", "live12_drum_pad_control", "live12_cc_control",
                "live12_wavetable_modulation_matrix",
                "live12_simpler_control", "live12_meld_control", "live12_roar_control",
                "live12_drift_control",
            ],
            "Domain 5: View, Dialogs, OS Actions (8 tools)": [
                "live12_view_switch", "live12_view_select", "live12_dialog_inspect",
                "live12_dialog_press", "live12_undo_redo", "live12_os_save_set",
                "live12_os_open_set", "live12_os_export_audio",
            ],
            "Domain 6: Universal LOM Escape Hatch (4 tools)": [
                "live12_lom_inspect", "live12_lom_get", "live12_lom_set", "live12_lom_call",
            ],
        }

        # Check every expected tool exists in catalog
        missing_tools = []
        for domain, expected_list in domain_tools.items():
            for t_name in expected_list:
                if t_name not in names:
                    missing_tools.append(f"{domain} -> {t_name}")
        assert not missing_tools, f"Missing tools: {missing_tools}"


# ==============================================================================
# Test Class 3: Representative Tool Execution Across All 6 Domains ('tools/call')
# ==============================================================================

class TestMcpToolsCall:
    """Verifies tools/call execution and ToolResult formatting across representative domains."""

    def _call(self, client: McpProcessClient, name: str, args: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
        resp = client.send_request("tools/call", {"name": name, "arguments": args})
        assert "result" in resp
        result = resp["result"]
        assert "content" in result
        assert isinstance(result["content"], list)
        assert len(result["content"]) > 0
        assert result["content"][0]["type"] == "text"
        is_error = result.get("isError", False)
        payload = json.loads(result["content"][0]["text"])
        return payload, is_error

    def test_domain1_song_get_state_and_tempo(self, mcp_client: McpProcessClient):
        # Set tempo
        data, is_err = self._call(mcp_client, "live12_transport_set_tempo", {"tempo": 132.0})
        assert not is_err
        assert data.get("tempo") == 132.0

        # Read back
        state, is_err = self._call(mcp_client, "live12_song_get_state", {})
        assert not is_err
        assert state.get("tempo") == 132.0

    def test_domain2_track_create_and_properties(self, mcp_client: McpProcessClient):
        data, is_err = self._call(mcp_client, "live12_track_create", {"type": "midi"})
        assert not is_err
        t_idx = data.get("track_index")
        assert t_idx is not None

        prop_data, is_err = self._call(mcp_client, "live12_track_set_properties", {
            "track_index": t_idx,
            "name": "__test_m3_track",
            "solo": True,
        })
        assert not is_err
        assert prop_data.get("name") == "__test_m3_track"
        assert prop_data.get("solo") is True

    def test_domain3_clip_create_and_extended_midi(self, mcp_client: McpProcessClient):
        # Create track first so track 0 exists
        t_data, is_err = self._call(mcp_client, "live12_track_create", {"type": "midi"})
        assert not is_err

        # Create clip
        c_data, is_err = self._call(mcp_client, "live12_clip_create", {
            "track_index": 0, "slot_index": 0, "length_beats": 4.0
        })
        assert not is_err

        # Add notes with Live 12 probability and velocity deviation
        add_data, is_err = self._call(mcp_client, "live12_clip_add_notes", {
            "track_index": 0,
            "slot_index": 0,
            "notes": [
                {
                    "pitch": 60,
                    "start_time": 0.0,
                    "duration": 1.0,
                    "velocity": 100.0,
                    "probability": 0.85,
                    "velocity_deviation": -12.0,
                }
            ],
        })
        assert not is_err
        assert add_data.get("added_count") == 1

        # Read back notes
        notes_data, is_err = self._call(mcp_client, "live12_clip_get_notes", {
            "track_index": 0, "slot_index": 0
        })
        assert not is_err
        notes = notes_data.get("notes", [])
        assert len(notes) == 1
        assert notes[0]["pitch"] == 60
        assert abs(notes[0]["probability"] - 0.85) < 1e-4

    def test_domain4_browser_search_and_devices(self, mcp_client: McpProcessClient):
        search_data, is_err = self._call(mcp_client, "live12_browser_search", {"query": "Drift"})
        assert not is_err
        assert search_data.get("count", 0) >= 1

    def test_domain5_view_switch(self, mcp_client: McpProcessClient):
        view_data, is_err = self._call(mcp_client, "live12_view_switch", {"view_name": "Arranger"})
        assert not is_err
        assert view_data.get("active_view") == "Arranger" or view_data.get("current_view") == "Arranger"

    def test_domain6_universal_lom_escape_hatch(self, mcp_client: McpProcessClient):
        inspect_data, is_err = self._call(mcp_client, "live12_lom_inspect", {"target_path": "live_set"})
        assert not is_err
        assert "properties" in inspect_data
        assert "tempo" in inspect_data["properties"]


# ==============================================================================
# Test Class 4: Error Handling & JSON-RPC Protocol Resilience
# ==============================================================================

class TestMcpErrorHandling:
    """Verifies JSON-RPC error codes and isError=True LOM feedback."""

    def test_lom_runtime_error_returns_is_error_true(self, mcp_client: McpProcessClient):
        resp = mcp_client.send_request("tools/call", {
            "name": "live12_track_delete",
            "arguments": {"track_index": 99999},
        })
        assert "result" in resp
        result = resp["result"]
        assert result.get("isError") is True
        content_text = result["content"][0]["text"]
        assert "out of range" in content_text.lower() or "error" in content_text.lower()

    def test_unknown_tool_returns_is_error_or_rpc_error(self, mcp_client: McpProcessClient):
        resp = mcp_client.send_request("tools/call", {
            "name": "live12_nonexistent_tool_xyz",
            "arguments": {},
        })
        if "error" in resp:
            assert resp["error"]["code"] in (-32601, -32602)
        else:
            assert resp["result"].get("isError") is True

    def test_out_of_bounds_parameters_returns_is_error_true(self, mcp_client: McpProcessClient):
        resp = mcp_client.send_request("tools/call", {
            "name": "live12_transport_set_tempo",
            "arguments": {"tempo": 10.0},
        })
        assert "result" in resp
        assert resp["result"].get("isError") is True

    def test_malformed_json_returns_parse_error(self, mcp_client: McpProcessClient):
        raw_resp = mcp_client.send_raw("MALFORMED_JSON_STRING_XYZ\n")
        assert raw_resp
        resp = json.loads(raw_resp)
        assert resp.get("error", {}).get("code") == -32700

    def test_missing_method_returns_invalid_request(self, mcp_client: McpProcessClient):
        raw_resp = mcp_client.send_raw(json.dumps({"jsonrpc": "2.0", "id": 999}))
        assert raw_resp
        resp = json.loads(raw_resp)
        assert resp.get("error", {}).get("code") == -32600

    def test_unknown_protocol_method_returns_method_not_found(self, mcp_client: McpProcessClient):
        resp = mcp_client.send_request("unknown_protocol_method_xyz", {})
        assert resp.get("error", {}).get("code") == -32601

    def test_empty_jsonrpc_batch_returns_code_32600(self, mcp_client: McpProcessClient):
        """Verifies that sending an empty JSON-RPC batch '[]' returns code -32600 (JSON-RPC 2.0 §4.2)."""
        raw_resp = mcp_client.send_raw("[]\n")
        assert raw_resp, "Server returned empty/no response on empty batch '[]'"
        resp = json.loads(raw_resp)
        assert resp.get("jsonrpc") == "2.0"
        assert resp.get("id") is None
        assert "error" in resp
        assert resp["error"].get("code") == -32600
        msg = resp["error"].get("message", "").lower()
        assert "invalid request" in msg or "batch" in msg

    def test_server_handle_line_empty_batch(self):
        """Verifies McpServer.handle_line directly returns -32600 envelope for '[]'."""
        from ableton_live12_mcp.server import McpServer
        server = McpServer(mode="mock")
        resp = server.handle_line("[]")
        assert resp is not None
        assert resp.get("jsonrpc") == "2.0"
        assert resp.get("id") is None
        assert resp.get("error", {}).get("code") == -32600

    def test_schema_validation_rejection_over_stdio(self, mcp_client: McpProcessClient):
        """Verifies that invalid tool arguments are rejected by schema validation over stdio."""
        resp = mcp_client.send_request("tools/call", {
            "name": "live12_transport_set_tempo",
            "arguments": {"tempo": "not_a_valid_number"},
        })
        assert "result" in resp
        result = resp["result"]
        assert result.get("isError") is True
        content_text = result["content"][0]["text"]
        assert "expected number, got str" in content_text or "validation" in content_text.lower()


# ==============================================================================
# Test Class 5: Registration Script Verification ('scripts/register_mcp.py')
# ==============================================================================

class TestMcpRegistrationScript:
    """Verifies register_mcp.py execution, backup generation, and idempotency."""

    def test_registration_lifecycle_in_scratch_config(self, tmp_path: Path):
        fake_config = tmp_path / "mcp_config.json"
        # Seed initial config with existing third-party servers
        seed_data = {
            "mcpServers": {
                "mac-use": {"command": "mac-use-cmd", "args": []},
                "rea": {"command": "rea-cmd", "args": []},
            }
        }
        fake_config.write_text(json.dumps(seed_data, indent=2), encoding="utf-8")

        # 1. Probe check before registration (must exit 1)
        res_check1 = subprocess.run(
            [sys.executable, str(REGISTER_SCRIPT), "--config-path", str(fake_config), "--check", "--json"],
            capture_output=True,
            text=True,
        )
        assert res_check1.returncode == 1
        check1_data = json.loads(res_check1.stdout)
        assert check1_data["is_registered"] is False

        # 2. Register server (must exit 0)
        res_reg = subprocess.run(
            [sys.executable, str(REGISTER_SCRIPT), "--config-path", str(fake_config), "--register", "--json"],
            capture_output=True,
            text=True,
        )
        assert res_reg.returncode == 0
        reg_data = json.loads(res_reg.stdout)
        assert reg_data["status"] == "registered"

        # 3. Verify backup file was created
        backup_file = fake_config.with_suffix(".json.bak")
        assert backup_file.exists()
        bak_content = json.loads(backup_file.read_text(encoding="utf-8"))
        assert "ableton-live12" not in bak_content["mcpServers"]

        # 4. Verify config file content and preservation of existing servers
        modified_data = json.loads(fake_config.read_text(encoding="utf-8"))
        assert "mac-use" in modified_data["mcpServers"]
        assert "rea" in modified_data["mcpServers"]
        assert "ableton-live12" in modified_data["mcpServers"]
        entry = modified_data["mcpServers"]["ableton-live12"]
        assert entry["args"] == ["-m", "ableton_live12_mcp"]
        assert "env" in entry and "PYTHONPATH" in entry["env"]

        # 5. Probe check after registration (must exit 0)
        res_check2 = subprocess.run(
            [sys.executable, str(REGISTER_SCRIPT), "--config-path", str(fake_config), "--check", "--json"],
            capture_output=True,
            text=True,
        )
        assert res_check2.returncode == 0

        # 6. Idempotency test: registering a second time produces no errors and status=already_registered
        res_reg2 = subprocess.run(
            [sys.executable, str(REGISTER_SCRIPT), "--config-path", str(fake_config), "--register", "--json"],
            capture_output=True,
            text=True,
        )
        assert res_reg2.returncode == 0
        reg2_data = json.loads(res_reg2.stdout)
        assert reg2_data["status"] == "already_registered"

        # 7. Unregister server (must exit 0)
        res_unreg = subprocess.run(
            [sys.executable, str(REGISTER_SCRIPT), "--config-path", str(fake_config), "--unregister", "--json"],
            capture_output=True,
            text=True,
        )
        assert res_unreg.returncode == 0
        final_data = json.loads(fake_config.read_text(encoding="utf-8"))
        assert "ableton-live12" not in final_data["mcpServers"]
        assert "mac-use" in final_data["mcpServers"]


# ==============================================================================
# Test Class 6: Process Lifecycle & Clean Shutdown
# ==============================================================================

class TestMcpProcessLifecycle:
    """Verifies that the server cleanly terminates on EOF and POSIX signals."""

    def test_clean_shutdown_on_eof(self):
        client = McpProcessClient()
        exit_code, _ = client.close()
        assert exit_code == 0

    def test_clean_shutdown_on_sigterm(self):
        client = McpProcessClient()
        # Verify server is listening and signal handlers are attached
        resp = client.send_request("ping", {})
        assert resp.get("result") == {}

        client.process.send_signal(signal.SIGTERM)
        try:
            client.process.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            client.process.kill()
            pytest.fail("Server process failed to terminate upon SIGTERM within 2 seconds")
        assert client.process.returncode == 0

    def test_unmocked_production_startup(self):
        """Verifies server starts in default unmocked auto-mode without crashing with TypeError.

        Subprocess runs WITHOUT ABLETON_TEST_MODE='mock', probes bridge (falling back
        cleanly to offline mock when bridge is unreachable), responds cleanly to initialize
        and ping, and terminates cleanly with exit code 0 on EOF.
        """
        client = McpProcessClient(mock_mode=False)
        try:
            assert client.process.poll() is None, "Server process terminated prematurely on unmocked launch"

            # 1. Initialize request
            resp_init = client.send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "unmocked-prod-test", "version": "1.0.0"},
            })
            assert "result" in resp_init
            init_res = resp_init["result"]
            assert init_res.get("protocolVersion") == "2024-11-05"
            assert "tools" in init_res.get("capabilities", {})
            assert init_res.get("serverInfo", {}).get("name") == "ableton-live12-mcp"

            # 2. Ping request
            resp_ping = client.send_request("ping", {})
            assert "result" in resp_ping
            assert resp_ping["result"] == {}

            # 3. Clean EOF shutdown
            exit_code, stderr = client.close()
            assert exit_code == 0, f"Process exited with non-zero code {exit_code}: {stderr}"
            assert "TypeError" not in stderr, f"TypeError encountered during unmocked launch: {stderr}"
            assert "Traceback" not in stderr, f"Unexpected traceback in unmocked launch: {stderr}"
        finally:
            client.close()


# ==============================================================================
# Test Class 7: Schema Validator Unit Tests (validator.py)
# ==============================================================================

class TestToolValidator:
    """Dedicated unit tests for Draft-07 validator.py and validate_tool_call."""

    def test_validate_tool_call_valid_arguments(self):
        """Verifies that correctly typed arguments pass validation without error."""
        # Domain 1: Song / Transport
        validate_tool_call("live12_transport_set_tempo", {"tempo": 128.0})
        validate_tool_call("live12_transport_play", {})
        validate_tool_call("live12_song_get_state", {})

        # Domain 2: Tracks
        validate_tool_call("live12_track_create", {"type": "midi", "index": 0})
        validate_tool_call("live12_track_delete", {"track_index": 1})

        # Domain 3: Clips & Notes
        validate_tool_call("live12_clip_create", {
            "track_index": 0,
            "slot_index": 0,
            "length_beats": 4.0,
        })
        validate_tool_call("live12_clip_add_notes", {
            "track_index": 0,
            "slot_index": 0,
            "notes": [
                {
                    "pitch": 60,
                    "start_time": 0.0,
                    "duration": 1.0,
                    "velocity": 100.0,
                    "probability": 0.8,
                    "velocity_deviation": 5.0,
                }
            ],
        })

        # Domain 6: LOM Escape Hatch
        validate_tool_call("live12_lom_inspect", {"target_path": "live_set"})

    def test_validate_tool_call_missing_required_arguments(self):
        """Verifies that omitting required parameters raises ValidationError."""
        # live12_transport_set_tempo requires 'tempo'
        with pytest.raises(ValidationError) as exc:
            validate_tool_call("live12_transport_set_tempo", {})
        assert "missing required parameter 'tempo'" in str(exc.value)

        # live12_track_delete requires 'track_index'
        with pytest.raises(ValidationError) as exc:
            validate_tool_call("live12_track_delete", {})
        assert "missing required parameter 'track_index'" in str(exc.value)

        # live12_clip_create requires 'track_index' and 'slot_index'
        with pytest.raises(ValidationError) as exc:
            validate_tool_call("live12_clip_create", {"track_index": 0})
        assert "missing required parameter 'slot_index'" in str(exc.value)

        # live12_transport_set_time_signature requires 'numerator' and 'denominator'
        with pytest.raises(ValidationError) as exc:
            validate_tool_call("live12_transport_set_time_signature", {"numerator": 4})
        assert "missing required parameter 'denominator'" in str(exc.value)

    def test_validate_tool_call_out_of_bounds_numbers(self):
        """Verifies that numbers violating minimum/maximum/exclusiveMinimum raise ValidationError."""
        # Below minimum tempo (minimum: 20.0)
        with pytest.raises(ValidationError) as exc:
            validate_tool_call("live12_transport_set_tempo", {"tempo": 19.9})
        assert "< minimum 20.0" in str(exc.value)

        # Above maximum tempo (maximum: 999.0)
        with pytest.raises(ValidationError) as exc:
            validate_tool_call("live12_transport_set_tempo", {"tempo": 1000.0})
        assert "> maximum 999.0" in str(exc.value)

        # Negative track index (minimum: 0)
        with pytest.raises(ValidationError) as exc:
            validate_tool_call("live12_track_delete", {"track_index": -1})
        assert "< minimum 0" in str(exc.value)

        # MIDI note pitch out of bounds (minimum: 0, maximum: 127)
        with pytest.raises(ValidationError) as exc:
            validate_tool_call("live12_clip_add_notes", {
                "track_index": 0,
                "slot_index": 0,
                "notes": [{"pitch": 128, "start_time": 0.0, "duration": 1.0}],
            })
        assert "> maximum 127" in str(exc.value)

        # MIDI note duration non-positive (exclusiveMinimum: 0.0)
        with pytest.raises(ValidationError) as exc:
            validate_tool_call("live12_clip_add_notes", {
                "track_index": 0,
                "slot_index": 0,
                "notes": [{"pitch": 60, "start_time": 0.0, "duration": 0.0}],
            })
        assert "<= exclusiveMinimum 0.0" in str(exc.value)

    def test_validate_tool_call_invalid_enums(self):
        """Verifies that enum violations raise ValidationError."""
        # Invalid track type (allowed: 'midi', 'audio', 'return')
        with pytest.raises(ValidationError) as exc:
            validate_tool_call("live12_track_create", {"type": "vst_instrument"})
        assert "not in allowed enum" in str(exc.value)

        # Invalid time signature denominator (allowed: 1, 2, 4, 8, 16)
        with pytest.raises(ValidationError) as exc:
            validate_tool_call("live12_transport_set_time_signature", {
                "numerator": 3,
                "denominator": 7,
            })
        assert "not in allowed enum" in str(exc.value)

        # Invalid scale name in live12_song_set_scale
        with pytest.raises(ValidationError) as exc:
            validate_tool_call("live12_song_set_scale", {
                "root_note": 0,
                "scale_name": "TotallyFakeScaleName123",
            })
        assert "not in allowed enum" in str(exc.value)

    def test_validate_tool_call_additional_properties_false(self):
        """Verifies rejection of extra keys when additionalProperties is False.

        Tests both validate_argument_dict directly on Draft-07 schemas and
        validate_tool_call on a registered tool having additionalProperties: False.
        """
        # 1. Direct schema test via validate_argument_dict
        strict_schema = {
            "type": "object",
            "properties": {
                "tempo": {"type": "number", "minimum": 20.0, "maximum": 999.0},
            },
            "required": ["tempo"],
            "additionalProperties": False,
        }
        # Valid call passes
        validate_argument_dict(strict_schema, {"tempo": 120.0}, path="test_tool")

        # Extra disallowed property raises ValidationError
        with pytest.raises(ValidationError) as exc:
            validate_argument_dict(
                strict_schema,
                {"tempo": 120.0, "unexpected_param": "hello"},
                path="test_tool",
            )
        assert "additional" in str(exc.value).lower() or "unexpected" in str(exc.value).lower()

        # 2. validate_tool_call with a registered tool schema having additionalProperties: False
        dummy_tool = {
            "name": "__test_strict_tool",
            "description": "Test tool with strict additionalProperties",
            "inputSchema": strict_schema,
        }
        TOOL_MAP["__test_strict_tool"] = dummy_tool
        try:
            # Valid call passes
            validate_tool_call("__test_strict_tool", {"tempo": 130.0})

            # Extra property raises ValidationError
            with pytest.raises(ValidationError) as exc:
                validate_tool_call("__test_strict_tool", {
                    "tempo": 130.0,
                    "extra_junk": True,
                })
            assert "additional" in str(exc.value).lower() or "extra_junk" in str(exc.value).lower()
        finally:
            TOOL_MAP.pop("__test_strict_tool", None)

    def test_validate_tool_call_type_mismatches(self):
        """Verifies that type mismatches (string instead of number/int/bool/array) are rejected."""
        # Non-numeric tempo (string passed)
        with pytest.raises(ValidationError) as exc:
            validate_tool_call("live12_transport_set_tempo", {"tempo": "one-twenty"})
        assert "expected number, got str" in str(exc.value)

        # Boolean passed as integer (bool is subclass of int in Python)
        with pytest.raises(ValidationError) as exc:
            validate_tool_call("live12_track_delete", {"track_index": True})
        assert "expected integer, got bool" in str(exc.value)

        # Non-array notes
        with pytest.raises(ValidationError) as exc:
            validate_tool_call("live12_clip_add_notes", {
                "track_index": 0,
                "slot_index": 0,
                "notes": "not_an_array",
            })
        assert "expected array, got str" in str(exc.value)

    def test_validate_tool_call_unknown_tool_raises_validation_error(self):
        """Verifies that calling validate_tool_call with an unknown tool name raises ValidationError."""
        with pytest.raises(ValidationError) as exc:
            validate_tool_call("nonexistent_tool_xyz", {})
        assert "unknown tool" in str(exc.value).lower()


# ==============================================================================
# Test Class 8: Scale Enum Harmonization Parity
# ==============================================================================

class TestScaleHarmonizationParity:
    """Verifies that all scales in song_tools enum are accepted across all layers."""

    def test_all_catalog_scales_accepted_by_bridge_and_mock(self):
        from ableton_live12_mcp.tools import get_tool_by_name
        from live12_bridge.handlers import BridgeHandlers
        from tests.harness import MockAbletonBridge

        tool = get_tool_by_name("live12_song_set_scale")
        assert tool is not None
        scale_enums = tool["inputSchema"]["properties"]["scale_name"]["enum"]
        assert len(scale_enums) == 37

        mock_bridge = MockAbletonBridge()
        handlers = BridgeHandlers(None)

        for scale in scale_enums:
            # Test MockAbletonBridge
            res = mock_bridge.execute_tool("live12_song_set_scale", {"root_note": 0, "scale_name": scale})
            assert not res.is_error, f"Scale '{scale}' rejected by MockAbletonBridge: {res.content}"

            # Test BridgeHandlers
            h_res = handlers.live12_song_set_scale(0, scale)
            assert h_res["scale_name"] == scale

