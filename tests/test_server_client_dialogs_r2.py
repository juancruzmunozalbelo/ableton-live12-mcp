"""
Regression & Unit Tests for R2 Hardening (Server, Client, Dialogs, Schemas & Scripts)
======================================================================================
Strictly offline/mocked tests verifying every bug fix without mutating live Ableton Live.
"""

from __future__ import annotations

import importlib.util
import io
import json
import math
import os
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import wave
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
SCRIPTS_DIR = REPO_ROOT / "scripts"
MASTERCLASSES_SCRIPTS_DIR = REPO_ROOT / "masterclasses" / "scripts"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ableton_live12_mcp import client as client_mod  # noqa: E402
from ableton_live12_mcp import dialogs  # noqa: E402
from ableton_live12_mcp.client import (  # noqa: E402
    Live12Client,
    Live12ClientError,
    Live12RpcError,
    Live12TimeoutError,
    ToolResult,
)
from ableton_live12_mcp.server import McpServer, main as server_main  # noqa: E402
from ableton_live12_mcp.tools import (  # noqa: E402
    ALL_TOOLS,
    ValidationError,
    get_tool_catalog,
    validate_tool_call,
)
from ableton_live12_mcp.tools.validator import validate_value  # noqa: E402
from harness import Live12TestClient, MockAbletonBridge  # noqa: E402


def _load_module_from_path(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ==============================================================================
# 1. Server JSON-RPC 2.0, Stdio Framing & Signal Races
# ==============================================================================

class TestServerHardeningR2:
    def test_invalid_jsonrpc_and_method_even_without_id(self):
        srv = McpServer(mode="mock")
        resp1 = srv.dispatch_request({"method": "ping"})
        assert resp1 is not None
        assert resp1["id"] is None
        assert resp1["error"]["code"] == -32600

        resp2 = srv.dispatch_request({"jsonrpc": "2.0"})
        assert resp2 is not None
        assert resp2["id"] is None
        assert resp2["error"]["code"] == -32600

        resp3 = srv.dispatch_request({"jsonrpc": "1.0", "id": 42, "method": "ping"})
        assert resp3 is not None
        assert resp3["id"] == 42
        assert resp3["error"]["code"] == -32600

        resp4 = srv.dispatch_request({"jsonrpc": "2.0", "id": 7, "method": ""})
        assert resp4 is not None
        assert resp4["id"] == 7
        assert resp4["error"]["code"] == -32600

    @pytest.mark.parametrize("bad_id", [True, False, {}, [1, 2], float("nan")])
    def test_rejects_invalid_jsonrpc_id_types(self, bad_id: Any):
        srv = McpServer(mode="mock")
        resp = srv.dispatch_request({"jsonrpc": "2.0", "id": bad_id, "method": "ping"})
        assert resp is not None
        assert resp["id"] is None
        assert resp["error"]["code"] == -32600

    def test_notifications_with_id_are_not_swallowed(self):
        srv = McpServer(mode="mock")
        # Valid notification (no id) sets initialized and returns None
        assert srv.dispatch_request({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None
        assert srv.initialized is True

        # With id present, notifications/* is treated as a request and returns error
        resp = srv.dispatch_request({"jsonrpc": "2.0", "id": 99, "method": "notifications/initialized"})
        assert resp is not None
        assert resp["id"] == 99
        assert resp["error"]["code"] == -32601

    def test_content_length_framing_fd_pipelined_utf8_and_textio(self):
        srv = McpServer(mode="mock")

        # 1. StringIO (TextIO fallback) with Content-Length & multi-byte UTF-8
        req1 = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}, ensure_ascii=False).encode("utf-8")
        req2 = json.dumps({
            "jsonrpc": "2.0",
            "id": "ñ",
            "method": "initialize",
            "params": {"clientInfo": {"name": "café 🎹"}},
        }, ensure_ascii=False).encode("utf-8")
        stream_data = (
            f"Content-Length: {len(req1)}\r\nContent-Type: application/vscode-jsonrpc; charset=utf-8\r\n\r\n"
            + req1.decode("utf-8")
            + f"Content-Length: {len(req2)}\r\n\r\n"
            + req2.decode("utf-8")
        )
        out_s = io.StringIO()
        srv.run(stdin=io.StringIO(stream_data), stdout=out_s)
        raw_out = out_s.getvalue()
        assert raw_out.startswith("Content-Length:")
        assert '"id":1' in raw_out
        assert '"id":"\\u00f1"' in raw_out or '"id":"ñ"' in raw_out

        # 2. Real os.pipe() (stdin_fd path) with chunked pipelined Content-Length + NDJSON mix
        r_fd, w_fd = os.pipe()
        os_stdout = io.StringIO()

        def _feed():
            frame1 = f"Content-Length: {len(req1)}\r\n\r\n".encode("utf-8") + req1
            frame2 = b'{"jsonrpc":"2.0","id":2,"method":"ping"}\n'
            os.write(w_fd, frame1[:12])
            time.sleep(0.02)
            os.write(w_fd, frame1[12:] + frame2)
            os.close(w_fd)

        feeder = threading.Thread(target=_feed, daemon=True)
        feeder.start()
        with os.fdopen(r_fd, "r", encoding="utf-8", buffering=1) as pipe_in:
            srv2 = McpServer(mode="mock")
            srv2.run(stdin=pipe_in, stdout=os_stdout)
        feeder.join(timeout=2.0)

        fd_out = os_stdout.getvalue()
        assert "Content-Length:" in fd_out
        assert '{"jsonrpc":"2.0","id":2,"result":{}}\n' in fd_out

    def test_stop_before_run_exits_immediately(self):
        srv = McpServer(mode="mock")
        srv.stop()
        r_fd, w_fd = os.pipe()
        try:
            with os.fdopen(r_fd, "r", encoding="utf-8") as pipe_in:
                out = io.StringIO()
                t0 = time.monotonic()
                srv.run(stdin=pipe_in, stdout=out)
                assert time.monotonic() - t0 < 0.5
        finally:
            os.close(w_fd)

    def test_stdin_buffer_limit_on_oversized_frame(self):
        r_fd, w_fd = os.pipe()
        out = io.StringIO()
        srv = McpServer(mode="mock")

        def _write_huge():
            chunk = b"x" * (1024 * 1024)
            try:
                for _ in range(11):
                    os.write(w_fd, chunk)
            except BrokenPipeError:
                pass
            finally:
                try:
                    os.close(w_fd)
                except OSError:
                    pass

        t = threading.Thread(target=_write_huge, daemon=True)
        t.start()
        with os.fdopen(r_fd, "r", encoding="utf-8") as pipe_in:
            srv.run(stdin=pipe_in, stdout=out)
        t.join(timeout=5.0)
        assert "-32600" in out.getvalue()

    def test_cli_mock_and_live_mutually_exclusive(self):
        with pytest.raises(SystemExit) as exc_info:
            server_main(["--mock", "--live"])
        assert exc_info.value.code == 2

    def test_export_audio_validates_render_settings_in_mock_mode(self, tmp_path):
        srv = McpServer(mode="mock")
        bad_res = srv.execute_tool(
            "live12_os_export_audio",
            {
                "destination_wav_path": str(tmp_path / "out.wav"),
                "render_settings": {"sample_rate": 12345, "unknown": True},
            },
        )
        assert bad_res.is_error is True
        assert "ValidationError" in json.dumps(bad_res.raw)


# ==============================================================================
# 2. Client Protocol, Port, Timeout & Fallback Hardening
# ==============================================================================

def _start_oneshot_tcp_server(handler):
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.bind(("127.0.0.1", 0))
    srv.listen(4)
    port = srv.getsockname()[1]
    stop_flag = threading.Event()

    def _serve():
        while not stop_flag.is_set():
            srv.settimeout(0.1)
            try:
                conn, _ = srv.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            with conn:
                handler(conn)

    th = threading.Thread(target=_serve, daemon=True)
    th.start()
    return srv, port, stop_flag, th


class TestClientHardeningR2:
    @pytest.mark.parametrize(
        "raw_line",
        [
            b'{"jsonrpc":"2.0","result":{"ok":true}}\n',
            b'{"jsonrpc":"2.0","id":true,"result":{"ok":true}}\n',
            b'{"jsonrpc":"2.0","id":"1","result":{"ok":true}}\n',
            b'{"jsonrpc":"2.0","id":null,"error":{"code":-32601,"message":"Not found"}}\n',
        ],
    )
    def test_rejects_missing_or_mismatched_id_types(self, raw_line: bytes):
        def _handler(conn):
            conn.recv(4096)
            conn.sendall(raw_line)

        srv, port, stop_flag, th = _start_oneshot_tcp_server(_handler)
        try:
            cli = Live12Client(host="127.0.0.1", port=port, timeout=2.0)
            with pytest.raises(Live12ClientError):
                cli.call("live12_song_get_state")
        finally:
            stop_flag.set()
            srv.close()
            th.join(timeout=1.0)

    def test_allows_parse_error_null_id_and_handles_weird_error_shapes(self):
        responses = iter([
            b'{"jsonrpc":"2.0","id":null,"error":{"code":-32700,"message":"Parse error"}}\n',
            b'{"jsonrpc":"2.0","id":2,"error":null,"result":{"tempo":128.0}}\n',
            b'{"jsonrpc":"2.0","id":3,"error":"string_error"}\n',
            b'\n\r\n{"jsonrpc":"2.0","id":4,"result":{"pong":true}}\n',
        ])

        def _handler(conn):
            conn.recv(4096)
            conn.sendall(next(responses))

        srv, port, stop_flag, th = _start_oneshot_tcp_server(_handler)
        try:
            cli = Live12Client(host="127.0.0.1", port=port, timeout=2.0)
            with pytest.raises(Live12RpcError) as exc1:
                cli.call("m1")
            assert exc1.value.code == -32700

            assert cli.call("m2") == {"tempo": 128.0}

            with pytest.raises(Live12RpcError) as exc3:
                cli.call("m3")
            assert "string_error" in exc3.value.message

            assert cli.call("m4") == {"pong": True}
        finally:
            stop_flag.set()
            srv.close()
            th.join(timeout=1.0)

    def test_preserves_port_zero_and_guards_invalid_env_port(self, monkeypatch, tmp_path):
        disc = tmp_path / "missing_disc.json"
        cli_zero = Live12Client(port=0, discovery_path=str(disc))
        assert cli_zero.port == 0

        monkeypatch.setenv("ABLETON_BRIDGE_PORT", "0")
        cli_env_zero = Live12Client(discovery_path=str(disc))
        assert cli_env_zero.port == 0

        monkeypatch.setenv("ABLETON_BRIDGE_PORT", "not_a_number")
        cli_bad_env = Live12Client(discovery_path=str(disc))
        assert cli_bad_env.port == client_mod.DEFAULT_PORT

    def test_stale_discovery_falls_back_to_default_port(self, monkeypatch, tmp_path):
        def _handler(conn):
            req = json.loads(conn.recv(4096).decode("utf-8"))
            conn.sendall((json.dumps({"jsonrpc": "2.0", "id": req["id"], "result": {"fallback": True}}) + "\n").encode("utf-8"))

        srv, live_port, stop_flag, th = _start_oneshot_tcp_server(_handler)
        # Unused closed port in stale discovery file
        dead_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        dead_sock.bind(("127.0.0.1", 0))
        dead_port = dead_sock.getsockname()[1]
        dead_sock.close()

        disc = tmp_path / "disc.json"
        disc.write_text(json.dumps({"host": "127.0.0.1", "port": dead_port, "pid": os.getpid()}), encoding="utf-8")

        monkeypatch.setattr(client_mod, "DEFAULT_PORT", live_port)
        try:
            cli = Live12Client(discovery_path=str(disc), timeout=2.0)
            assert cli.port == dead_port
            assert cli.call("live12_song_get_state") == {"fallback": True}
            assert cli.port == live_port
        finally:
            stop_flag.set()
            srv.close()
            th.join(timeout=1.0)

    def test_total_deadline_and_max_response_bytes(self, monkeypatch):
        def _trickle(conn):
            conn.recv(4096)
            for _ in range(15):
                try:
                    conn.sendall(b"x")
                    time.sleep(0.05)
                except OSError:
                    break

        srv, port, stop_flag, th = _start_oneshot_tcp_server(_trickle)
        try:
            cli = Live12Client(host="127.0.0.1", port=port, timeout=0.18)
            t0 = time.monotonic()
            with pytest.raises(Live12TimeoutError):
                cli.call("slow")
            assert time.monotonic() - t0 < 0.6
        finally:
            stop_flag.set()
            srv.close()
            th.join(timeout=1.0)

        def _huge(conn):
            conn.recv(4096)
            conn.sendall(b'{"jsonrpc":"2.0","id":1,"result":"' + b"a" * 2048 + b'"}\n')

        srv2, port2, stop_flag2, th2 = _start_oneshot_tcp_server(_huge)
        monkeypatch.setattr(client_mod, "MAX_RESPONSE_BYTES", 512)
        try:
            cli2 = Live12Client(host="127.0.0.1", port=port2, timeout=2.0)
            with pytest.raises(Live12ClientError, match="exceeded"):
                cli2.call("huge")
        finally:
            stop_flag2.set()
            srv2.close()
            th2.join(timeout=1.0)


# ==============================================================================
# 3. Dialogs & AppleScript Hardening
# ==============================================================================

class TestDialogsHardeningR2:
    def test_validate_render_settings_all_keys_and_rejections(self):
        ok = dialogs._validate_render_settings({
            "sample_rate": 48000,
            "bit_depth": 24,
            "dither_type": "POW-r 1",
            "render_start": 4.0,
            "render_length": 16.0,
            "normalize": False,
            "rendered_track": "Master",
        })
        assert ok["sample_rate"] == 48000
        assert ok["normalize"] is False

        for bad in (
            {"extra": 1},
            {"sample_rate": True},
            {"sample_rate": 12345},
            {"bit_depth": 8},
            {"render_start": -1.0},
            {"render_start": float("nan")},
            {"render_length": 0.0},
            {"dither_type": "   "},
            {"normalize": "yes"},
            {"rendered_track": ""},
        ):
            with pytest.raises(dialogs.ValidationError):
                dialogs._validate_render_settings(bad)

    def test_export_audio_reports_unapplied_render_settings_and_handles_short_timeout(self, tmp_path):
        wav_path = tmp_path / "bounce.wav"
        fake_wav = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x02\x00\x44\xac\x00\x00\x10\xb1\x02\x00\x04\x00\x10\x00data\x00\x00\x00\x00"

        def _fake_osascript(script: str, args=None, timeout_sec=10.0):
            assert "Enregistrer" in script and "Sichern" in script
            wav_path.write_bytes(fake_wav)
            return True, "triggered|applied=", ""

        with patch.object(dialogs, "get_live_running_status", return_value=(True, None)), \
             patch.object(dialogs, "run_applescript", side_effect=_fake_osascript):
            res = dialogs.export_audio(
                str(wav_path),
                render_settings={"sample_rate": 48000, "bit_depth": 24, "normalize": True},
                timeout_sec=0.1,
            )

        assert res["exported"] is True
        assert res["applied_render_settings"] == {}
        assert res["unapplied_render_settings"] == {"sample_rate": 48000, "bit_depth": 24, "normalize": True}
        assert "warning" in res

    def test_accessibility_pgrep_error_and_dismiss_helpers(self):
        # Accessibility uses UI elements enabled via osascript stdin
        mock_proc_acc = MagicMock(returncode=0, stdout="true\n", stderr="")
        with patch("ableton_live12_mcp.dialogs.subprocess.run", return_value=mock_proc_acc) as mock_run:
            granted, err = dialogs.get_accessibility_permission_status()
            assert granted is True and err is None
            assert mock_run.call_args.args[0] == ["osascript", "-"]
            assert "UI elements enabled" in mock_run.call_args.kwargs["input"]

        # pgrep -x Live & ValueError guard on System Events fallback
        mock_pgrep_miss = MagicMock(returncode=1, stdout="", stderr="")
        mock_osa_bad = MagicMock(returncode=0, stdout="not_an_int\n", stderr="")
        with patch("ableton_live12_mcp.dialogs.subprocess.run", side_effect=[mock_pgrep_miss, mock_osa_bad]) as mock_run2:
            running, err2 = dialogs.get_live_running_status()
            assert mock_run2.call_args_list[0].args[0] == ["pgrep", "-x", "Live"]
            assert running is False
            assert err2 is not None

        # -1719 mapped to ApplicationNotRunningError
        mock_1719 = MagicMock(returncode=1, stdout="", stderr="execution error: System Events got an error: Can't get process. (-1719)")
        with patch("ableton_live12_mcp.dialogs.subprocess.run", return_value=mock_1719):
            with pytest.raises(dialogs.ApplicationNotRunningError):
                dialogs.run_applescript("return 1")

        # inspect_os_dialogs unnamed / AXDialog counting
        with patch.object(dialogs, "get_live_running_status", return_value=(True, None)), \
             patch.object(dialogs, "run_applescript", return_value=(True, "2\nSave", "")) as mock_insp:
            insp = dialogs.inspect_os_dialogs()
            assert insp["open_sheet_count"] == 2
            assert insp["dialog_titles"] == ["Save"]
            insp_script = mock_insp.call_args.args[0]
            assert "missing value" in insp_script and "AXDialog" in insp_script

        # dismiss_os_dialog sets frontmost to true
        with patch.object(dialogs, "get_live_running_status", return_value=(True, None)), \
             patch.object(dialogs, "run_applescript", return_value=(True, "DISMISSED", "")) as mock_osa:
            dialogs.dismiss_os_dialog()
            sent_script = mock_osa.call_args.args[0]
            assert "set frontmost to true" in sent_script
            assert sent_script.index("set frontmost to true") < sent_script.index("key code 53")

    @pytest.mark.skipif(not shutil.which("osacompile"), reason="macOS osacompile not available")
    def test_all_embedded_applescripts_compile_with_osacompile(self):
        scripts = [
            dialogs._APPLESCRIPT_SAVE_PANEL_HELPERS + '\non run argv\nreturn "ok"\nend run',
            'tell application "System Events" to get UI elements enabled',
        ]
        captured: List[str] = []

        with tempfile.TemporaryDirectory() as td:
            open_als = os.path.join(td, "open.als")
            save_als = os.path.join(td, "saved.als")
            wav_path = os.path.join(td, "test.wav")
            Path(open_als).write_bytes(b"X" * 200)
            wav_hdr = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x02\x00\x44\xac\x00\x00\x10\xb1\x02\x00\x04\x00\x10\x00data\x00\x00\x00\x00"

            def _capture_run(script: str, args=None, timeout_sec=10.0):
                captured.append(script)
                if "DISMISSED" in script:
                    return True, "DISMISSED", ""
                if "sheetCount" in script:
                    return True, "0\n", ""
                if "triggered|applied=" in script:
                    Path(wav_path).write_bytes(wav_hdr)
                    return True, "triggered|applied=", ""
                if save_als.endswith(str(args[1])) if args and len(args) > 1 else False:
                    Path(save_als).write_bytes(b"X" * 200)
                return True, "triggered", ""

            def _fake_subprocess_run(cmd, *args, **kwargs):
                if isinstance(cmd, list) and cmd and "open" in os.path.basename(cmd[0]):
                    return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
                return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

            with patch.object(dialogs, "get_live_running_status", return_value=(True, None)), \
                 patch.object(dialogs, "run_applescript", side_effect=_capture_run), \
                 patch.object(dialogs.subprocess, "run", side_effect=_fake_subprocess_run):
                dialogs.save_set(save_als, timeout_sec=1.0, overwrite=True)
                dialogs.open_set(open_als, timeout_sec=1.0, discard_unsaved=True)
                dialogs.export_audio(wav_path, timeout_sec=1.0)
                dialogs.inspect_os_dialogs()
                dialogs.dismiss_os_dialog()

        assert len(captured) == 5
        for scpt_src in scripts + captured:
            fd, tmp_scpt = tempfile.mkstemp(suffix=".scpt")
            os.close(fd)
            try:
                res = subprocess.run(
                    ["osacompile", "-o", tmp_scpt, "-"],
                    input=scpt_src,
                    text=True,
                    capture_output=True,
                    timeout=10.0,
                )
                assert res.returncode == 0, f"osacompile failed: {res.stderr}\nScript:\n{scpt_src[:400]}"
            finally:
                if os.path.exists(tmp_scpt):
                    os.unlink(tmp_scpt)


# ==============================================================================
# 4. Validator, Tool Catalog & Harness Parity
# ==============================================================================

class TestSchemasValidatorAndHarnessR2:
    def test_catalog_extension_filtering_and_strict_additional_properties(self):
        assert len(get_tool_catalog(include_extensions=True)) == 77
        core = get_tool_catalog(include_extensions=False)
        assert len(core) == 76
        assert all(t["name"] != "live12_take_lane_create_audio_clip" for t in core)

        for tool in ALL_TOOLS:
            assert tool["inputSchema"].get("additionalProperties") is False, tool["name"]

        with pytest.raises(ValidationError, match="unrecognized property"):
            validate_tool_call("live12_transport_play", {"unexpected_bogus_key": 1})

    def test_validator_draft07_type_lists_and_non_finite_strings(self):
        schema = {"type": ["string", "integer"], "minLength": 2, "minimum": 10}
        validate_value(schema, "ab", "p")
        validate_value(schema, 12, "p")
        with pytest.raises(ValidationError):
            validate_value(schema, "a", "p")
        with pytest.raises(ValidationError):
            validate_value(schema, 5, "p")
        with pytest.raises(ValidationError):
            validate_value(schema, True, "p")

        for bad_s in ("NaN", "Infinity", "-Infinity", "nan", "-inf"):
            with pytest.raises(ValidationError):
                validate_tool_call("live12_lom_set", {"target_path": "song", "property_name": "x", "value": bad_s})
            with pytest.raises(ValidationError):
                validate_tool_call("live12_lom_call", {"target_path": "song", "method_name": "m", "args": [bad_s]})

    def test_harness_note_id_zero_warp_parity_and_safe_live_teardown(self, tmp_path):
        bridge = MockAbletonBridge()
        bridge.execute_tool("live12_track_create", {"type": "midi"})
        bridge.execute_tool("live12_clip_create", {"track_index": 0, "slot_index": 0, "length_beats": 4.0})
        add_res = bridge.execute_tool("live12_clip_add_notes", {
            "track_index": 0,
            "slot_index": 0,
            "notes": [{"pitch": 60, "start_time": 0.0, "duration": 1.0, "velocity": 100.0}],
        })
        assert not add_res.is_error, add_res.raw
        assert len(add_res.raw["note_ids"]) == 1
        # Force note_id == 0 to verify falsy ID handling
        bridge.tracks[0].clip_slots[0].clip.notes[0].note_id = 0
        mod_res = bridge.execute_tool("live12_clip_modify_notes", {
            "track_index": 0,
            "slot_index": 0,
            "note_modifications": [{"note_id": 0, "new_pitch": 64, "new_start_time": 0.5}],
        })
        assert mod_res.raw["modified_count"] == 1
        assert bridge.tracks[0].clip_slots[0].clip.notes[0].pitch == 64
        assert bridge.tracks[0].clip_slots[0].clip.notes[0].start_time == 0.5

        warp = bridge.execute_tool("live12_audio_clip_set_warp", {
            "track_index": 0,
            "slot_index": 0,
            "warp_mode": "complex pro",
            "gain": 0.75,
        })
        assert warp.raw["warp_mode"] == "Complex Pro"
        assert warp.raw["gain"] == 0.75

        exp = bridge.execute_tool("live12_os_export_audio", {
            "destination_wav_path": str(tmp_path / "m.wav"),
            "render_settings": {"sample_rate": 48000},
            "timeout_sec": 5.0,
        })
        assert not exp.is_error
        assert exp.raw["applied_render_settings"] == {}
        assert exp.raw["unapplied_render_settings"] == {"sample_rate": 48000}

        # Live teardown preserves pre-existing user tracks and cue points
        fake_live = MagicMock()
        def _fake_rpc(tool, args):
            if tool == "live12_song_get_state":
                return ToolResult(False, [{"type": "text", "text": json.dumps({
                    "tempo": 135.0, "signature_numerator": 4, "signature_denominator": 4, "root_note": 7, "scale_name": "Phrygian"
                })}])
            if tool == "live12_cue_point_control" and args.get("action") == "list":
                return ToolResult(False, [{"type": "text", "text": json.dumps({
                    "cue_points": [
                        {"index": 0, "name": "Intro Drop", "time": 16.0},
                        {"index": 1, "name": "__agy_test_marker", "time": 32.0},
                    ]
                })}])
            if tool == "live12_lom_get" and args.get("property_name") == "tracks":
                return ToolResult(False, [{"type": "text", "text": json.dumps({
                    "value": [{"name": "User Kick"}, {"name": "__agy_test_123_bass"}]
                })}])
            if tool == "live12_lom_get" and args.get("property_name") == "scenes":
                return ToolResult(False, [{"type": "text", "text": json.dumps({
                    "value": [{"name": "User Scene"}]
                })}])
            return ToolResult(False, [{"type": "text", "text": json.dumps({"ok": True})}])

        fake_live.call_rpc.side_effect = _fake_rpc
        with patch("harness.LiveTcpClient", return_value=fake_live):
            client = Live12TestClient(mode="live")
            client.teardown()

        deleted_tracks = [c.args[1]["track_index"] for c in fake_live.call_rpc.call_args_list if c.args[0] == "live12_track_delete"]
        assert deleted_tracks == [1]
        cue_times_set = [
            c.args[1]["value"]
            for c in fake_live.call_rpc.call_args_list
            if c.args[0] == "live12_lom_set" and c.args[1].get("property_name") == "current_song_time"
        ]
        assert 16.0 not in cue_times_set
        assert 32.0 in cue_times_set


# ==============================================================================
# 5. Scripts & builder_base Regressions
# ==============================================================================

class TestScriptsAndBuilderBaseR2:
    def test_register_mcp_null_safe_and_symlink_preserved(self, tmp_path):
        reg_mod = _load_module_from_path("register_mcp_r2", SCRIPTS_DIR / "register_mcp.py")
        assert not hasattr(reg_mod, "PREFERRED_PYTHON")

        cfg = tmp_path / "mcp_config.json"
        cfg.write_text('{"mcpServers": null}', encoding="utf-8")
        expected = reg_mod.build_server_config(sys.executable, REPO_ROOT)
        ok, reason, _ = reg_mod.check_registration(cfg, expected)
        assert ok is False and reason
        assert reg_mod.unregister(cfg)["status"] == "not_registered"

        cfg.write_text('{"mcpServers": {"ableton-live12": {"command": "x", "args": [], "cwd": ".", "env": null}}}', encoding="utf-8")
        ok2, reason2, _ = reg_mod.check_registration(cfg, expected)
        assert ok2 is False and reason2

        # Preserve symlink path without resolving away venv wrapper
        target_bin = tmp_path / "real_py"
        target_bin.write_text("#!/bin/sh\n", encoding="utf-8")
        sym_bin = tmp_path / "venv_py"
        sym_bin.symlink_to(target_bin)
        assert reg_mod.resolve_python_executable(str(sym_bin)) == str(sym_bin)

    def test_builder_base_reset_wav_save_export(self, tmp_path):
        bb = _load_module_from_path("builder_base_r2", MASTERCLASSES_SCRIPTS_DIR / "builder_base.py")

        # 1. clean_session_reset aborts cleanly if delete returns is_error
        fake_client = MagicMock()
        def _fail_delete(tool_name, args=None):
            if tool_name == "live12_song_get_state":
                return ToolResult(False, [{"type": "text", "text": json.dumps({"tracks_count": 3})}])
            if tool_name == "live12_track_delete":
                return ToolResult(True, [{"type": "text", "text": json.dumps({"error": "cannot delete"})}])
            return ToolResult(False, [{"type": "text", "text": json.dumps({"ok": True})}])
        fake_client.call_tool.side_effect = _fail_delete
        with pytest.raises(RuntimeError, match="deleting track"):
            bb.clean_session_reset(fake_client)

        # 2. verify_pcm_wav_energy 8-bit unsigned and 32-bit signed PCM
        wav8 = tmp_path / "test8.wav"
        with wave.open(str(wav8), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(1)
            wf.setframerate(44100)
            # Half-scale square wave around 128: [255, 1, ...] -> ~ -0.0 dBFS
            wf.writeframes(bytes([255, 1] * 2000))
        res8 = bb.verify_pcm_wav_energy(str(wav8), min_duration_sec=0.05)
        assert res8["bit_depth"] == 8 and res8["valid"] is True

        wav32 = tmp_path / "test32.wav"
        with wave.open(str(wav32), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(4)
            wf.setframerate(44100)
            samples = [int(0.5 * 2147483647), int(-0.5 * 2147483647)] * 2000
            wf.writeframes(struct.pack(f"<{len(samples)}i", *samples))
        res32 = bb.verify_pcm_wav_energy(str(wav32), min_duration_sec=0.05)
        assert res32["bit_depth"] == 32 and res32["valid"] is True
        assert -7.0 < res32["rms_dbfs"] < -5.5

        # 3. save_live_set fails explicitly when osascript returns non-zero
        with patch.object(bb.subprocess, "run", return_value=MagicMock(returncode=1, stderr="osascript err", stdout="")):
            with pytest.raises(RuntimeError, match="osascript failed"):
                bb.save_live_set(MagicMock(), str(tmp_path / "fail.als"), timeout_sec=1.0)

        # 4. export_audio_bounce handles case-variant .WAV without SameFileError/ffmpeg crash
        wav_upper = tmp_path / "bounce_mix.WAV"
        wav_lower = tmp_path / "bounce_mix.wav"
        wav_upper.write_bytes(b"RIFF" + b"\x00" * 70000)
        fake_c2 = MagicMock()
        fake_c2.call_tool.return_value = ToolResult(False, [{"type": "text", "text": json.dumps({"ok": True})}])
        with patch.object(bb.subprocess, "run", return_value=MagicMock(returncode=0, stderr="", stdout="")) as mock_sub:
            with patch.object(bb.time, "sleep", return_value=None):
                exp = bb.export_audio_bounce(fake_c2, str(wav_lower), timeout_sec=5.0)
        assert exp["exported"] is True
        # Only osascript was invoked; ffmpeg was NOT run on samefile .WAV
        assert mock_sub.call_count == 1

    def test_inspect_live_set_and_measure_track_levels(self, capsys):
        insp = _load_module_from_path("inspect_r2", SCRIPTS_DIR / "inspect_live_set.py")
        fake_c = MagicMock()
        def _fake_call(tool, args):
            prop = args.get("property_name")
            if args.get("target_path") == "song":
                if prop == "loop_length":
                    return {"value": 16.0}
                if prop == "loop_start":
                    return {"value": 4.0}
                if prop == "root_note":
                    return {"value": 7}
                if prop == "tracks":
                    return {"value": [{}]}
                return {"value": "Demo"}
            return {"value": None}
        fake_c.call.side_effect = _fake_call
        snap = insp.snapshot(fake_c)
        assert snap["song"]["loop_end"] == 20.0
        assert snap["song"]["scale_root"] == 7
        assert len(snap["tracks"]) == 1

        # Verify None fields format safely in main()
        with patch.object(insp, "snapshot", return_value=snap), \
             patch.object(sys, "argv", ["inspect_live_set.py"]):
            assert insp.main() == 0
        out = capsys.readouterr().out
        assert "[ 0]" in out

        mtl = _load_module_from_path("mtl_r2", SCRIPTS_DIR / "measure_track_levels.py")
        assert math.isclose(mtl._linear_to_dbfs(0.5), -6.02, abs_tol=0.05)
        assert mtl._linear_to_dbfs(0.0) == -120.0

        # Ensure transport_stop always runs even if polling fails
        fake_c2 = MagicMock()
        def _call_err(tool, args=None):
            if tool == "live12_transport_play":
                return {}
            if tool == "live12_lom_set":
                raise RuntimeError("boom during seek")
            return {"value": None}
        fake_c2.call.side_effect = _call_err
        with patch.object(mtl, "Live12Client", return_value=fake_c2), \
             patch.object(sys, "argv", ["measure_track_levels.py", "--seconds", "0.1", "--settle", "0.0"]):
            with pytest.raises(RuntimeError, match="boom"):
                mtl.main()
        called_tools = [c.args[0] for c in fake_c2.call.call_args_list]
        assert "live12_transport_stop" in called_tools
