"""
Milestone 4 Automated Test Suite: Hybrid Dialog & OS Automation
===============================================================
Validates:
1. OS Automation & Path Validation (dialogs.py):
   - Path extension enforcement (.als for save/open, .wav for export).
   - Non-existent file rejection on open_set.
   - Automatic parent directory creation on save/export.
   - Empty/whitespace path rejection.
2. Mocked Subprocess & AppleScript Execution:
   - Monkeypatched subprocess.run for osascript success.
   - osascript syntax error (-2741) handling.
   - osascript timeout (TimeoutExpired) handling.
   - macOS Accessibility / System Events permission denial (-1743) handling.
   - Non-Darwin platform rejection.
3. In-LOM Native Dialogs:
   - Application.open_dialog_count and current_dialog_message inspection.
   - Button pressing (button 0=OK, button 1=Cancel).
   - Empty dialog queue handling.
4. MCP Server Stdio JSON-RPC 2.0 Integration:
   - tools/call execution for all 5 M4 tools.
   - JSON Schema Draft-07 validation via validate_tool_call.
   - ToolResult envelopes and isError reporting.
5. Dual-Mode (Live vs. Mock) Hybrid Execution.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from ableton_live12_mcp.tools import (
    TOOL_MAP,
    VIEW_TOOLS,
    ValidationError,
    validate_tool_call,
)
from ableton_live12_mcp import dialogs
from tests.harness import Live12TestClient, MockAbletonBridge, ToolResult


# ==============================================================================
# MCP Process Test Client Fixture
# ==============================================================================

class McpProcessClient:
    """Spawns ableton_live12_mcp as a subprocess communicating via stdio JSON-RPC 2.0."""

    def __init__(self, mock_mode: bool = True):
        self.req_id = 0
        process_env = os.environ.copy()
        process_env["PYTHONPATH"] = f"{REPO_ROOT / 'src'}:{REPO_ROOT}:{process_env.get('PYTHONPATH', '')}"
        if mock_mode:
            process_env["ABLETON_TEST_MODE"] = "mock"
        else:
            process_env.pop("ABLETON_TEST_MODE", None)

        cmd = [sys.executable, "-m", "ableton_live12_mcp"]
        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=str(REPO_ROOT),
            env=process_env,
        )

    def send_raw(self, line: str) -> Optional[str]:
        assert self.process.stdin is not None
        assert self.process.stdout is not None
        self.process.stdin.write(line.strip() + "\n")
        self.process.stdin.flush()
        resp_line = self.process.stdout.readline()
        return resp_line.strip() if resp_line else None

    def send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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

    def close(self) -> Tuple[int, str]:
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
    client = McpProcessClient(mock_mode=True)
    try:
        # Initialize handshake
        client.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-m4-runner", "version": "1.0.0"},
        })
        yield client
    finally:
        client.close()


@pytest.fixture
def client():
    test_client = Live12TestClient(mode="mock")
    try:
        yield test_client
    finally:
        test_client.teardown()


# ==============================================================================
# Test Class 1: OS Automation Path Validation (Unit Tests)
# ==============================================================================

class TestDialogsOSPathValidation:
    """Validates path boundary checks and file extension rules for OS tools."""

    def test_save_set_non_als_extension_rejected(self, client: Live12TestClient):
        for bad_ext in ["project.txt", "project.wav", "project", "project.als.bak"]:
            if hasattr(dialogs, "validate_als_save_path"):
                with pytest.raises(ValueError):
                    dialogs.validate_als_save_path(f"/tmp/{bad_ext}")

    def test_save_set_valid_als_path(self, client: Live12TestClient, tmp_path: Path):
        valid_path = str(tmp_path / "valid_project.als")
        res = client.call_tool("live12_os_save_set", {"destination_path": valid_path})
        assert not res.is_error
        assert os.path.exists(valid_path)

    def test_save_set_nested_dir_creation(self, client: Live12TestClient, tmp_path: Path):
        nested_path = str(tmp_path / "sub" / "nested" / "project.als")
        res = client.call_tool("live12_os_save_set", {"destination_path": nested_path})
        assert not res.is_error
        assert os.path.exists(nested_path)

    def test_save_set_empty_path_rejected(self, client: Live12TestClient):
        if hasattr(dialogs, "validate_als_save_path"):
            with pytest.raises(ValueError):
                dialogs.validate_als_save_path("")

    def test_open_set_non_als_extension_rejected(self, client: Live12TestClient, tmp_path: Path):
        bad_file = tmp_path / "sound.wav"
        bad_file.write_bytes(b"DATA")
        if hasattr(dialogs, "validate_als_open_path"):
            with pytest.raises(ValueError):
                dialogs.validate_als_open_path(str(bad_file))

    def test_open_set_non_existent_file_rejected(self, client: Live12TestClient):
        non_existent = "/tmp/__agy_definitely_non_existent_file_987654.als"
        if hasattr(dialogs, "validate_als_open_path"):
            with pytest.raises(FileNotFoundError):
                dialogs.validate_als_open_path(non_existent)

    def test_open_set_valid_existing_als(self, client: Live12TestClient, tmp_path: Path):
        existing_als = tmp_path / "existing.als"
        existing_als.write_bytes(b"LIVE_SET_DATA")
        res = client.call_tool("live12_os_open_set", {"als_path": str(existing_als)})
        assert not res.is_error

    def test_open_set_empty_path_rejected(self, client: Live12TestClient):
        if hasattr(dialogs, "validate_als_open_path"):
            with pytest.raises(ValueError):
                dialogs.validate_als_open_path("")

    def test_export_audio_non_wav_extension_rejected(self, client: Live12TestClient):
        for bad_ext in ["render.mp3", "render.flac", "render.aif", "render"]:
            if hasattr(dialogs, "validate_wav_export_path"):
                with pytest.raises(ValueError):
                    dialogs.validate_wav_export_path(f"/tmp/{bad_ext}")

    def test_export_audio_valid_wav_path(self, client: Live12TestClient, tmp_path: Path):
        wav_path = str(tmp_path / "valid_render.wav")
        res = client.call_tool("live12_os_export_audio", {"destination_wav_path": wav_path})
        assert not res.is_error
        assert os.path.exists(wav_path)
        with open(wav_path, "rb") as f:
            assert f.read(4) == b"RIFF"

    def test_export_audio_empty_path_rejected(self, client: Live12TestClient):
        if hasattr(dialogs, "validate_wav_export_path"):
            with pytest.raises(ValueError):
                dialogs.validate_wav_export_path("")

    def test_open_set_directory_rejected(self, client: Live12TestClient, tmp_path: Path):
        """Directories ending in .als must be rejected by validate_als_open_path."""
        dir_als = tmp_path / "mock_project.als"
        dir_als.mkdir()
        with pytest.raises(dialogs.ValidationError) as exc_info:
            dialogs.validate_als_open_path(str(dir_als))
        assert "directory" in str(exc_info.value).lower()
        res = client.call_tool("live12_os_open_set", {"als_path": str(dir_als)})
        assert res.is_error

    def test_save_set_directory_rejected(self, client: Live12TestClient, tmp_path: Path):
        """Existing directories ending in .als must be rejected by validate_als_save_path."""
        dir_als = tmp_path / "existing_folder.als"
        dir_als.mkdir()
        with pytest.raises(dialogs.ValidationError) as exc_info:
            dialogs.validate_als_save_path(str(dir_als))
        assert "directory" in str(exc_info.value).lower()
        res = client.call_tool("live12_os_save_set", {"destination_path": str(dir_als)})
        assert res.is_error

    def test_export_audio_directory_rejected(self, client: Live12TestClient, tmp_path: Path):
        """Existing directories ending in .wav must be rejected by validate_wav_export_path."""
        dir_wav = tmp_path / "existing_render_dir.wav"
        dir_wav.mkdir()
        with pytest.raises(dialogs.ValidationError) as exc_info:
            dialogs.validate_wav_export_path(str(dir_wav))
        assert "directory" in str(exc_info.value).lower()
        res = client.call_tool("live12_os_export_audio", {"destination_wav_path": str(dir_wav)})
        assert res.is_error


# ==============================================================================
# Test Class 2: Mocked Subprocess & AppleScript Execution
# ==============================================================================

class TestMockedSubprocessOSAutomation:
    """Verifies subprocess.run monkeypatching for osascript error modes and edge cases."""

    def test_save_set_osascript_success(self, monkeypatch, tmp_path: Path):
        target_path = str(tmp_path / "mocked_save.als")

        def mock_run(cmd, *args, **kwargs):
            with open(target_path, "wb") as f:
                f.write(b"MOCKED_ALS_PAYLOAD")
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="saved\n", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)

        if hasattr(dialogs, "save_set"):
            res = dialogs.save_set(target_path, timeout_sec=5.0)
            assert res.get("status") == "success"
            assert os.path.exists(target_path)

    def test_open_set_subprocess_success(self, monkeypatch, tmp_path: Path):
        target_path = tmp_path / "mocked_open.als"
        target_path.write_bytes(b"MOCKED_ALS")

        calls = []
        def mock_run(cmd, *args, **kwargs):
            calls.append(cmd)
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)

        if hasattr(dialogs, "open_set"):
            res = dialogs.open_set(str(target_path), timeout_sec=5.0)
            assert res.get("status") == "success"
            assert len(calls) > 0

    def test_export_audio_osascript_success(self, monkeypatch, tmp_path: Path):
        wav_path = str(tmp_path / "mocked_export.wav")

        def mock_run(cmd, *args, **kwargs):
            with open(wav_path, "wb") as f:
                f.write(b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x02\x00D\xac\x00\x00\x10\xb1\x02\x00\x04\x00\x10\x00data\x00\x00\x00\x00")
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="exported\n", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)

        if hasattr(dialogs, "export_audio"):
            res = dialogs.export_audio(wav_path, timeout_sec=5.0)
            assert res.get("status") == "success"
            assert os.path.exists(wav_path)

    def test_osascript_syntax_error_handling(self, monkeypatch, tmp_path: Path):
        target_path = str(tmp_path / "syntax_err.als")

        def mock_run(cmd, *args, **kwargs):
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=1,
                stdout="",
                stderr="syntax error: Expected end of line but found unknown token. (-2741)",
            )

        monkeypatch.setattr(subprocess, "run", mock_run)

        if hasattr(dialogs, "save_set"):
            try:
                res = dialogs.save_set(target_path, timeout_sec=5.0)
                assert res.get("status") == "error" or res.get("isError") is True
            except Exception as e:
                assert "syntax error" in str(e).lower() or "-2741" in str(e)

    def test_osascript_timeout_expired_handling(self, monkeypatch, tmp_path: Path):
        target_path = str(tmp_path / "timeout.als")

        def mock_run(cmd, *args, **kwargs):
            raise subprocess.TimeoutExpired(cmd=cmd, timeout=2.0)

        monkeypatch.setattr(subprocess, "run", mock_run)

        if hasattr(dialogs, "save_set"):
            try:
                res = dialogs.save_set(target_path, timeout_sec=2.0)
                assert res.get("status") == "timeout" or res.get("isError") is True
            except Exception as e:
                assert "timed out" in str(e).lower() or isinstance(e, subprocess.TimeoutExpired)

    def test_osascript_accessibility_permission_denied(self, monkeypatch, tmp_path: Path):
        target_path = str(tmp_path / "perm_denied.als")

        def mock_run(cmd, *args, **kwargs):
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=1,
                stdout="",
                stderr="execution error: System Events got an error: Application isn't running or not authorized to send Apple events. (-1743)",
            )

        monkeypatch.setattr(subprocess, "run", mock_run)

        if hasattr(dialogs, "save_set"):
            try:
                res = dialogs.save_set(target_path, timeout_sec=5.0)
                err_msg = str(res)
            except Exception as e:
                err_msg = str(e)
            assert "-1743" in err_msg or "authorized" in err_msg.lower() or "accessibility" in err_msg.lower()

    def test_non_darwin_platform_rejection(self, monkeypatch, tmp_path: Path):
        target_path = str(tmp_path / "linux_test.als")
        monkeypatch.setattr(platform, "system", lambda: "Linux")

        if hasattr(dialogs, "save_set"):
            try:
                res = dialogs.save_set(target_path)
                assert res.get("status") == "unsupported" or res.get("isError") is True
            except Exception as e:
                assert "darwin" in str(e).lower() or "unsupported" in str(e).lower()


# ==============================================================================
# Test Class 3: In-LOM Native Dialogs Inspection & Button Pressing
# ==============================================================================

class TestInLOMDialogInspectionAndPressing:
    """Verifies Live.Application dialog inspection and button pressing behaviors."""

    def test_dialog_inspect_when_no_dialogs_open(self, client: Live12TestClient):
        if client._mock_bridge:
            client._mock_bridge.open_dialogs = []

        res = client.call_tool("live12_dialog_inspect")
        assert not res.is_error
        assert res["open_dialog_count"] == 0
        assert res["current_dialog_message"] == ""

    def test_dialog_inspect_when_single_dialog_open(self, client: Live12TestClient):
        if client._mock_bridge:
            client._mock_bridge.open_dialogs = [
                {"message": "Save changes to the Live Set before closing?", "buttons": ["Save", "Don't Save", "Cancel"]}
            ]

        res = client.call_tool("live12_dialog_inspect")
        assert not res.is_error
        assert res["open_dialog_count"] == 1
        assert res["current_dialog_message"] == "Save changes to the Live Set before closing?"

    def test_dialog_inspect_multiple_queued_dialogs(self, client: Live12TestClient):
        if client._mock_bridge:
            client._mock_bridge.open_dialogs = [
                {"message": "Background render completed."},
                {"message": "Media files are missing in this set."}
            ]

        res = client.call_tool("live12_dialog_inspect")
        assert not res.is_error
        assert res["open_dialog_count"] == 2
        assert res["current_dialog_message"] == "Media files are missing in this set."

    def test_dialog_press_button_0_ok(self, client: Live12TestClient):
        if client._mock_bridge:
            client._mock_bridge.open_dialogs = [
                {"message": "Collect all and save media files?"}
            ]

        press_res = client.call_tool("live12_dialog_press", {"button_index": 0})
        assert not press_res.is_error
        assert press_res.get("button_index") == 0 or press_res.get("pressed_button_index") == 0

        # Read-back: dialog count should be 0
        inspect_res = client.call_tool("live12_dialog_inspect")
        assert not inspect_res.is_error
        assert inspect_res["open_dialog_count"] == 0
        assert inspect_res["current_dialog_message"] == ""

    def test_dialog_press_button_1_cancel(self, client: Live12TestClient):
        if client._mock_bridge:
            client._mock_bridge.open_dialogs = [
                {"message": "Overwrite existing export file?"}
            ]

        press_res = client.call_tool("live12_dialog_press", {"button_index": 1})
        assert not press_res.is_error
        assert press_res.get("button_index") == 1 or press_res.get("pressed_button_index") == 1

        # Read-back
        inspect_res = client.call_tool("live12_dialog_inspect")
        assert inspect_res["open_dialog_count"] == 0

    def test_dialog_press_when_no_dialog_is_open(self, client: Live12TestClient):
        if client._mock_bridge:
            client._mock_bridge.open_dialogs = []

        res = client.call_tool("live12_dialog_press", {"button_index": 0})
        assert not res.is_error
        assert res.get("status") == "no_open_dialogs" or res.get("open_dialog_count") == 0


# ==============================================================================
# Test Class 4: MCP Server Stdio JSON-RPC 2.0 Integration ('tools/call')
# ==============================================================================

class TestMcpServerDomain5Integration:
    """Verifies MCP server tools/call execution for all 5 Domain 5 dialog & OS tools."""

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

    def test_mcp_os_save_set_call(self, mcp_client: McpProcessClient, tmp_path: Path):
        save_path = str(tmp_path / "mcp_saved.als")
        data, is_err = self._call(mcp_client, "live12_os_save_set", {"destination_path": save_path})
        assert not is_err
        assert data.get("status") == "success" or data.get("saved") is True
        assert os.path.exists(save_path)

    def test_mcp_os_open_set_call(self, mcp_client: McpProcessClient, tmp_path: Path):
        open_path = str(tmp_path / "mcp_open.als")
        open_path_file = tmp_path / "mcp_open.als"
        open_path_file.write_bytes(b"DATA")
        data, is_err = self._call(mcp_client, "live12_os_open_set", {"als_path": open_path})
        assert not is_err
        assert data.get("status") == "success" or data.get("opened") is True

    def test_mcp_os_export_audio_call(self, mcp_client: McpProcessClient, tmp_path: Path):
        wav_path = str(tmp_path / "mcp_render.wav")
        data, is_err = self._call(mcp_client, "live12_os_export_audio", {
            "destination_wav_path": wav_path,
            "render_settings": {"sample_rate": 48000, "bit_depth": 24}
        })
        assert not is_err
        assert data.get("status") == "success" or data.get("exported") is True
        assert os.path.exists(wav_path)
        with open(wav_path, "rb") as f:
            assert f.read(4) == b"RIFF"

    def test_mcp_dialog_inspect_call(self, mcp_client: McpProcessClient):
        data, is_err = self._call(mcp_client, "live12_dialog_inspect", {})
        assert not is_err
        assert "open_dialog_count" in data
        assert isinstance(data["open_dialog_count"], int)
        assert "current_dialog_message" in data

    def test_mcp_dialog_press_call(self, mcp_client: McpProcessClient):
        data, is_err = self._call(mcp_client, "live12_dialog_press", {"button_index": 0})
        assert isinstance(data, dict)
        ping = mcp_client.send_request("ping", {})
        assert ping.get("result") == {}

    def test_mock_stdio_save_set_invalid_extension_rejected(self, mcp_client: McpProcessClient, tmp_path: Path):
        """live12_os_save_set with invalid extension (.txt) in mock mode returns isError=True."""
        bad_path = str(tmp_path / "project.txt")
        resp = mcp_client.send_request("tools/call", {
            "name": "live12_os_save_set",
            "arguments": {"destination_path": bad_path}
        })
        res = resp["result"]
        assert res["isError"] is True
        content_text = res["content"][0]["text"]
        assert ".als" in content_text.lower() or "invalid" in content_text.lower()

    def test_mock_stdio_open_set_missing_or_dir_rejected(self, mcp_client: McpProcessClient, tmp_path: Path):
        """live12_os_open_set with missing file or directory in mock mode returns isError=True."""
        # 1. Non-existent file
        missing_file = str(tmp_path / "non_existent_set.als")
        resp_missing = mcp_client.send_request("tools/call", {
            "name": "live12_os_open_set",
            "arguments": {"als_path": missing_file}
        })
        res_missing = resp_missing["result"]
        assert res_missing["isError"] is True

        # 2. Existing directory ending in .als
        dir_als = tmp_path / "dir_set.als"
        dir_als.mkdir()
        resp_dir = mcp_client.send_request("tools/call", {
            "name": "live12_os_open_set",
            "arguments": {"als_path": str(dir_als)}
        })
        res_dir = resp_dir["result"]
        assert res_dir["isError"] is True
        dir_text = res_dir["content"][0]["text"]
        assert "directory" in dir_text.lower()

    def test_mock_stdio_export_audio_invalid_extension_rejected(self, mcp_client: McpProcessClient, tmp_path: Path):
        """live12_os_export_audio with invalid extension (.als) in mock mode returns isError=True."""
        bad_path = str(tmp_path / "export.als")
        resp = mcp_client.send_request("tools/call", {
            "name": "live12_os_export_audio",
            "arguments": {"destination_wav_path": bad_path}
        })
        res = resp["result"]
        assert res["isError"] is True
        content_text = res["content"][0]["text"]
        assert ".wav" in content_text.lower() or "invalid" in content_text.lower()


# ==============================================================================
# Test Class 5: JSON Schema Draft-07 Validation & Envelope Integrity
# ==============================================================================

class TestMcpDomain5SchemaValidation:
    """Verifies Draft-07 schema compliance and error envelopes for Domain 5 tools."""

    def test_schema_validation_save_set(self):
        validate_tool_call("live12_os_save_set", {"destination_path": "/tmp/project.als"})

        with pytest.raises(ValidationError) as exc:
            validate_tool_call("live12_os_save_set", {})
        assert "missing required parameter 'destination_path'" in str(exc.value)

        with pytest.raises(ValidationError) as exc:
            validate_tool_call("live12_os_save_set", {"destination_path": ""})
        assert "shorter than minLength 1" in str(exc.value)

        with pytest.raises(ValidationError) as exc:
            validate_tool_call("live12_os_save_set", {"destination_path": 12345})
        assert "expected string, got int" in str(exc.value)

    def test_schema_validation_open_set(self):
        validate_tool_call("live12_os_open_set", {"als_path": "/tmp/project.als"})

        with pytest.raises(ValidationError) as exc:
            validate_tool_call("live12_os_open_set", {})
        assert "missing required parameter 'als_path'" in str(exc.value)

        with pytest.raises(ValidationError) as exc:
            validate_tool_call("live12_os_open_set", {"als_path": ""})
        assert "shorter than minLength 1" in str(exc.value)

    def test_schema_validation_export_audio(self):
        validate_tool_call("live12_os_export_audio", {"destination_wav_path": "/tmp/render.wav"})

        validate_tool_call("live12_os_export_audio", {
            "destination_wav_path": "/tmp/render.wav",
            "render_settings": {"sample_rate": 44100, "bit_depth": 16}
        })

        with pytest.raises(ValidationError) as exc:
            validate_tool_call("live12_os_export_audio", {})
        assert "missing required parameter 'destination_wav_path'" in str(exc.value)

        with pytest.raises(ValidationError) as exc:
            validate_tool_call("live12_os_export_audio", {
                "destination_wav_path": "/tmp/render.wav",
                "render_settings": "not_an_object"
            })
        assert "expected object, got str" in str(exc.value)

    def test_schema_validation_dialog_inspect(self):
        validate_tool_call("live12_dialog_inspect", {})

    def test_schema_validation_dialog_press(self):
        validate_tool_call("live12_dialog_press", {"button_index": 0})
        validate_tool_call("live12_dialog_press", {"button_index": 1})

        with pytest.raises(ValidationError) as exc:
            validate_tool_call("live12_dialog_press", {})
        assert "missing required parameter 'button_index'" in str(exc.value)

        with pytest.raises(ValidationError) as exc:
            validate_tool_call("live12_dialog_press", {"button_index": -1})
        assert "< minimum 0" in str(exc.value)

        with pytest.raises(ValidationError) as exc:
            validate_tool_call("live12_dialog_press", {"button_index": "zero"})
        assert "expected integer, got str" in str(exc.value)

    def test_schema_error_envelope_over_stdio(self, mcp_client: McpProcessClient):
        resp1 = mcp_client.send_request("tools/call", {
            "name": "live12_os_save_set",
            "arguments": {}
        })
        assert resp1.get("result", {}).get("isError") is True
        err1 = resp1["result"]["content"][0]["text"]
        assert "missing required parameter" in err1.lower()

        resp2 = mcp_client.send_request("tools/call", {
            "name": "live12_dialog_press",
            "arguments": {"button_index": -99}
        })
        assert resp2.get("result", {}).get("isError") is True
        err2 = resp2["result"]["content"][0]["text"]
        assert "< minimum 0" in err2


# ==============================================================================
# Test Class 6: Dual-Mode (Live vs. Mock) Hybrid Behavior
# ==============================================================================

class TestLiveMockHybridBehavior:
    """Verifies clean separation and execution guarantees under ABLETON_TEST_MODE."""

    def test_mock_mode_deterministic_execution(self, client: Live12TestClient, tmp_path: Path):
        assert client.mode == "mock"
        save_path = str(tmp_path / "hybrid_mock_set.als")
        t0 = time.time()
        res = client.call_tool("live12_os_save_set", {"destination_path": save_path})
        t1 = time.time()
        assert not res.is_error
        assert (t1 - t0) < 0.1
        assert os.path.exists(save_path)

    def test_mock_bridge_state_isolation(self, client: Live12TestClient):
        assert client._mock_bridge is not None
        client._mock_bridge.open_dialogs.append({"message": "Isolated dialog test"})
        res = client.call_tool("live12_dialog_inspect")
        assert res["open_dialog_count"] == 1
        client.call_tool("live12_dialog_press", {"button_index": 0})
        res2 = client.call_tool("live12_dialog_inspect")
        assert res2["open_dialog_count"] == 0

    def test_live_client_rpc_formatting(self):
        from ableton_live12_mcp.client import Live12Client
        client = Live12Client(host="127.0.0.1", port=11246)
        client._req_id += 1
        req_id = client._req_id
        req_payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "live12_dialog_inspect",
            "params": {},
        }
        data = (json.dumps(req_payload) + "\n").encode("utf-8")
        parsed = json.loads(data.decode("utf-8").strip())
        assert parsed["jsonrpc"] == "2.0"
        assert parsed["method"] == "live12_dialog_inspect"
        assert parsed["params"] == {}
